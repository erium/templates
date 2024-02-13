# infrastructure
import base64
from .chatbot_roles import ChatbotRoles
from datetime import datetime
from .db import (
    DBGlobal as DBG,
    DBHistory as DBH,
    DBBoard as DBB,
    DBChatbotConfig as DBC,
    DBSessions as DBS,
)
from .environment import Environment
import httpx
import json
import logging
from pathlib import Path
import ssl


class Chatbot:
    logger = logging.getLogger(__name__)

    @staticmethod
    def setup(session_id: str, session_data: dict):
        """
        Sets up the chatbot for a new session by adding the configuration to the db,
        and changing the system message in the db if necessary.
        """
        session_id,
        model = session_data.get("setup_model")
        botname = session_data.get("bot_name")
        personality = session_data.get("setup_message")
        username = session_data.get("username")
        today = datetime.now().strftime("%Y-%m-%d")

        DBC.add(session_id, model, botname, personality)

        DBB.update_board(
            session_id,
            ChatbotRoles.SYSTEM.value,
            f"\n\nDein Name ist: {botname}.\n\nHeute ist der {today}.",
        )

        if username:
            DBB.update_board(
                session_id,
                ChatbotRoles.SYSTEM.value,
                f"\n\nDein Gesprächspartner heißt {username}.",
            )

    @staticmethod
    async def evaluate(session_id: str, user_prompt: str, initial: bool = False) -> str:
        """
        Evaluates user prompts via the prompt server

        Args:
            user_prompt (str): User prompt.

        Returns:
            str: Response.
        """
        Chatbot.logger.debug(f"Evaluating prompt for session {session_id}")
        Chatbot.logger.debug(f"Is initial message: {initial}")

        # append chatbot reponse to the history and the board
        # but only if this is not the initial prompt (otherwise it is already on the board)
        DBH.add_history_item(session_id, ChatbotRoles.USER.value, user_prompt)
        if not initial:
            DBB.update_board(session_id, ChatbotRoles.USER.value, user_prompt)

        # prompt model
        try:
            ssl_context = ssl.create_default_context()
            timeout = httpx.Timeout(60.0, connect=60.0)
            n_chunk = 0
            full_message = ""
            base64img = ""

            # use the halerium prompt server for response generation
            endpoint = Environment.get_agents_endpoint_url()
            payload = Environment.build_agents_endpoint_payload(
                DBB.get_board(session_id), DBB.get_current_card_id(session_id)
            )
            headers = Environment.build_prompt_server_headers()

            async with httpx.AsyncClient(verify=ssl_context, timeout=timeout) as client:
                async with client.stream(
                    method="POST", url=endpoint, json=payload, headers=headers
                ) as response:
                    async for chunk in response.aiter_lines():
                        if "data: " in chunk:
                            content = json.loads(chunk[len("data: ") :])
                            n_chunk += 1
                            chunk = content.get("chunk")
                            attachment = content.get("attachment")
                            completed = content.get("completed")
                            if chunk and not str(chunk).startswith(
                                "![output_image.png](attachment:"
                            ):
                                Chatbot.logger.debug(f"yielding text chunk: {chunk}")
                                yield chunk
                                full_message += content.get("chunk")
                            elif attachment:
                                Chatbot.logger.debug("yielding image attachment")
                                base64img = attachment
                                yield f"IMAGE_ATTACHMENT:{attachment}"
                                full_message = (
                                    "![output_image.png](attachment:output_image.png)"
                                )
                            elif completed:
                                Chatbot.logger.debug(
                                    f"yielding status update: {completed}"
                                )
                                yield completed

            # append chatbot reponse to the history and the board
            DBH.add_history_item(session_id, ChatbotRoles.ASSISTANT.value, full_message)
            DBB.update_board(
                session_id, ChatbotRoles.ASSISTANT.value, full_message, base64img
            )

        except httpx.TimeoutException as e:
            Chatbot.logger.error(f"The model timed out: {e}")
            yield f"I'm sorry, the model timed out. Please try again."

        except Exception as e:
            Chatbot.logger.error(f"There has been an error evaluating a prompt: {e}")
            yield f"I'm sorry, there has been an error: {e}"

    @staticmethod
    async def transcribe_audio(path) -> str:
        """
        Sends an audio file to the OpenAI API for transcription.

        Args:
            path (str): Path to the audio file.

        Returns:
            str: The transcript.
        """
        try:
            ssl_context = ssl.create_default_context()
            timeout = httpx.Timeout(60.0, connect=60.0)
            n_chunk = 0
            audio_b64 = base64.b64encode(open(path, "rb").read()).decode("utf-8")

            # use the halerium prompt server for response generation
            endpoint = Environment.get_models_endpoint_url()
            headers = Environment.build_prompt_server_headers()
            payload = Environment.build_models_endpoint_payload(audio_b64, "whisper")

            async with httpx.AsyncClient(verify=ssl_context, timeout=timeout) as client:
                async with client.stream(
                    method="POST", url=endpoint, json=payload, headers=headers
                ) as response:
                    async for chunk in response.aiter_lines():
                        Chatbot.logger.debug(f"transcript: {chunk}")
                        if "data: " in chunk:
                            content = json.loads(chunk[len("data: ") :])
                            n_chunk += 1
                            chunk = content.get("chunk")
                            completed = content.get("completed")
                            if chunk:
                                Chatbot.logger.debug(f"yielding transcript: {chunk}")
                                yield chunk
                            elif completed:
                                Chatbot.logger.debug(
                                    f"yielding status update: {completed}"
                                )
                                if content.get("error"):
                                    Chatbot.logger.error(
                                        f"There has been an error transcribing an audio file: {content.get('error')}"
                                    )
                                    yield f"I'm sorry, there has been an error transcribing your recording!"
                                yield completed

        except Exception as e:
            Chatbot.logger.error(
                f"There has been an error transcribing an audio file: {e}"
            )
            yield f"I'm sorry, there has been an error transcribing your recording!"
        else:
            # if transcription has been successful, delete the mp3
            is_debugging_session = DBG.get_config().get("debug_mode") == 1
            if not is_debugging_session:
                Path.unlink(Path(path))
            else:
                Chatbot.logger.debug(f"debugging session, not deleting {path}")

    # @staticmethod
    # def text_to_speech(msg: str, model: str = "tts-1", voice: str = "alloy"):
    #     """
    #     Converts text to speech and saves it to disk.

    #     Args:
    #         msg (str): The text to convert to speech.
    #         model (str, optional): The model used (tts-1 or tts-1-hd). Defaults to "tts-1".
    #         voice (str, optional): The voice used (alloy, echo, fable, onyx, nova, shimmer). Defaults to "alloy".
    #     """
    #     cp = ConfigParser()
    #     config = cp.read(Path(__file__).resolve().parent / Path("../../config.conf"))
    #     try:
    #         openai_client = openai.OpenAI(api_key=config["openai"]["api_key"])
    #         response = openai_client.audio.speech.create(
    #             model=model,
    #             voice=voice,
    #             input=msg,
    #         )
    #     except Exception as e:
    #         Chatbot.logger.error(
    #             f"There has been an error converting text to speech: {e}"
    #         )
    #         return f"I'm sorry, there has been an error converting my answer to speech!"
    #     else:
    #         Chatbot.logger.debug("Converted text to speech.")
    #         return response.read()

    @staticmethod
    def build_chat_log(session_id: str) -> dict:
        """
        Create a chat log file for the current session.

        Args:
            session_id (str): The ID of the current session.
        """
        # get data from db
        user_data = DBS.get_session_data(session_id)
        chat_history = DBH.get_history(session_id)

        # create chat log
        if user_data and chat_history:
            return {"user_data": user_data, "chat_history": chat_history}

        return {"user_data": None, "chat_history": None}
