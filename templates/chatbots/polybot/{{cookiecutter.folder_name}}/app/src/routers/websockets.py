# api
import asyncio
from ..audio_processor import AudioProcessor
from ..chatbot import Chatbot
from datetime import datetime
from ..db import DBSessions as DBS, DBOperations as DBO, DBBoard as DBB
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Query,
    status,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from halerium_utilities.board import Board
import io
import json
import logging
from pathlib import Path
import time
from typing import Annotated

router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
    responses={404: {"description": "Not found"}},
)


async def get_session_id(
    websocket: WebSocket,
    session: Annotated[str | None, Cookie()] = None,
    token: Annotated[str | None, Query()] = None,
):
    """
    Checks websocket connection for sessionID token.
    If none, raises an exception and rejects the connection.

    Args:
        websocket (WebSocket): New websocket connection
        session (Annotated[str  |  None, Cookie, optional): Expected session token. Defaults to None.
        token (Annotated[str  |  None, Query, optional): Expected session token. Defaults to None.

    Raises:
        WebSocketException: If no token or session was found.

    Returns:
        str: Session id
    """
    logger = logging.getLogger(__name__)
    if session is None and token is None:
        logger.error("No Session ID provided. Closing websocket.")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return session or token


@router.websocket("/text")
async def text_messages(
    websocket: WebSocket, session_id: Annotated[str, Depends(get_session_id)]
):
    """
    Websocket connection for the chat function. Waits for a prompt and then queries the chatbot.
    Output function is a generator to allow for token-wise "streaming".
    """
    logger = logging.getLogger(__name__)
    if not DBS.is_active_session(session_id):
        logger.error(
            f"Session ID {str(session_id)} not found in active sessions. Closing websocket."
        )
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    else:
        await websocket.accept()
        await asyncio.sleep(0)

    try:
        while True:
            # get prompt and timestamp
            prompt = await websocket.receive_text()
            if prompt == f"ping, {session_id}":
                await websocket.send_text("<pong>")
                continue

            logger.info(
                f'Session {session_id} prompt @ {datetime.now().strftime("%Y-%m-%dT%H:%M:%S:%f")}',
            )

            is_initial_prompt = False
            if prompt.startswith(f"<INITIAL>, {session_id}\n\n"):
                is_initial_prompt = True

            prompt = prompt.replace(f"<INITIAL>, {session_id}\n\n", "")

            # prompt model and send tokens to frontend once they become available
            now = time.time()
            full_message = ""
            n_token = 0
            async for token in Chatbot.evaluate(
                session_id, prompt, initial=is_initial_prompt
            ):
                if n_token == 0:
                    # begin message
                    await websocket.send_text("<sos>")

                if isinstance(token, bool):
                    # end message
                    await websocket.send_text("<eos>")

                    # text2speech
                    # logger.info("Generating audio...")
                    # voice = chatbot.text_to_speech(full_message)
                    # await websocket.send_bytes(voice)

                elif isinstance(token, str):
                    # send token to frontend via websocket
                    await websocket.send_text(token)
                    # save token to full message
                    full_message += token
                    n_token += 1

            # generation time
            delta = time.time() - now

            logger.info(f'finished @ {datetime.now().strftime("%Y-%m-%dT%H:%M:%S:%f")}')

            # timing information
            try:
                logger.debug(
                    f"received and sent {n_token} token in {round(delta, 3)} s ({round(delta/n_token, 3)} s/token)"
                )
            except:
                pass

    except WebSocketDisconnect:
        logger.info(f"Session {session_id} terminated")

        Path.mkdir(
            Path(__file__).resolve().parent / Path("../../../chat_logs"),
            exist_ok=True,
            parents=True,
        )
        Path.mkdir(
            Path(__file__).resolve().parent / Path("../../../chat_boards"),
            exist_ok=True,
            parents=True,
        )

        chat_log = Chatbot.build_chat_log(session_id)
        chat_board = DBB.get_board(session_id)

        with io.StringIO(json.dumps(chat_board)) as f:
            chat_board = Board.from_json(f)

        now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S_%f")
        with open(
            Path(__file__).resolve().parent
            / Path(f"../../../chat_logs/{now}_{session_id}.json"),
            "w",
        ) as f:
            json.dump(chat_log, f, indent=4, ensure_ascii=False)

        with open(
            Path(__file__).resolve().parent
            / Path(f"../../../chat_boards/{now}_{session_id}.board"),
            "w",
        ) as f:
            chat_board.to_json(f)

        DBO.delete_user_data(session_id)
        logger.info(f"Remaining Sessions {DBS.get_active_session_ids()}")

    except RuntimeError:
        pass


@router.websocket("/voice")
async def audio_messages(
    websocket: WebSocket, session_id: Annotated[str, Depends(get_session_id)]
):
    """
    Websocket connection for the audio stream.
    """
    logger = logging.getLogger(__name__)

    if not DBS.is_active_session(session_id):
        logger.error(
            f"Session ID {str(session_id)} not found in active sessions. Closing websocket."
        )
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    else:
        await websocket.accept()
        await asyncio.sleep(0)

    try:
        total_bytes = 0

        while True:
            # receive data
            data = await websocket.receive()

            # start/stop recording
            if "text" in data:
                message = json.loads(data.get("text"))

                if message["type"] == "audio-start":
                    samplerate = message["samplerate"]
                    audio_processor = AudioProcessor(int(samplerate), session_id)
                    logger.debug(f"User started recording. Samplerate: {samplerate}")

                elif message["type"] == "audio-end":
                    logger.debug("Stopped recording")
                    filename = audio_processor.export_mp3()
                    logger.debug(f"Received filename: {filename}")
                    try:
                        transcript = ""
                        async for token in Chatbot.transcribe_audio(filename):
                            if isinstance(token, str):
                                transcript += token
                                await websocket.send_text(token)
                            elif isinstance(token, bool):
                                continue  # boolean is a status update
                        logger.debug(f"Transcript: {transcript}")
                    except Exception as e:
                        logger.error(f"Error transcribing voice message: {e}")
                        await websocket.send_text("Error transcribing voice message")
                        continue
                    else:
                        # send transcript to frontend
                        # await websocket.send_text(transcript)
                        continue

            # receive audio data
            elif "bytes" in data:
                if audio_processor and audio_processor.is_recording:
                    audio_chunk = data.get("bytes")
                    total_bytes += len(audio_chunk)
                    audio_processor.add_chunk(audio_chunk)

    except WebSocketDisconnect:
        if audio_processor:
            _ = audio_processor.export_mp3()

    except RuntimeError:
        pass
