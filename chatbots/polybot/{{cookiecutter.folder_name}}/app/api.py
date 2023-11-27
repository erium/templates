# api
import asyncio
from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Form,
    Query,
    Request,
    status,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_403_FORBIDDEN

# webserver
import uvicorn

# backend
from .src.email_service import Postman
from .src.chatbot import Chatbot
from .src import personality_loader as pl
from .src.environment import Environment

# infrastructure
import argparse
import configparser
from datetime import datetime
import json
import os
from pydantic import BaseModel, Field
from .src.prettyprint import prettyprint as print, MessageType as mt
import time
from typing import Annotated
import uuid

SESSIONS = {}

def main(public):
    # change to script directory
    file_path = os.path.abspath(__file__)
    dir_path = os.path.dirname(file_path)
    os.chdir(dir_path)

    # set up configparser
    configs = configparser.ConfigParser()
    configs.read("config.conf")

    # get environment parameters
    env = Environment()
    PORT = 0  # int(configs["app"]["port"])
    if public:
        PORT = 8499
    else:
        PORT = 8501

    APP_URL = env.get_app_url(port=PORT)
    WS_URL = env.get_websocket_url(port=PORT)

    # set up chat
    BOT_NAME = configs["app"]["bot_name"]

    # set up custom vector database
    CUSTOM_DB = None

    class Data(BaseModel):
        username: str = Field(..., min_length=1, max_length=50)
        email: str = Field(..., min_length=6, max_length=50)
        ip: str = Field(..., min_length=8, max_length=50)

    print(
        f"App is running {'publicly' if public else 'privately'} at {APP_URL}",
        type=mt.INFO,
    )

    # set up API
    app = FastAPI(debug=configs["app"]["debug"] == "True")
    app.mount(
        "/static", StaticFiles(directory=configs["paths"]["static"]), name="static"
    )
    templates = Jinja2Templates(configs["paths"]["templates"])
    app.root_path = f"/apps/{env.runner_id}/{PORT}/"

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """
        Serves the login template
        """
        personalities = pl.load_personalities(configs["paths"]["persona_dir"])
        botname = "P o l y B o t"
        intro_wide = (
            intro_narrow
        ) = "Nutzen Sie Halerium PolyBot für die individualisierte Informationsbeschaffung aus ausgewählten Dokumenten."
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "botname": botname,
                "intro_wide": intro_wide,
                "intro_narrow": intro_narrow,
                "p": personalities,
                "form_post_url": app.root_path,
            },
        )

    @app.post("/", response_class=HTMLResponse)
    async def serve(
        request: Request,
        username: str = Form(...),
        useremail: str = Form("nan"),
        ip: str = Form("nan"),
        personalityPicker: str = Form(...),
    ):
        """
        POST method to collect user data.
        Userdata collected are Username, email, and ip address.

        Success with IP address may vary (depends on ipify.org, an external API)
        """
        global SESSIONS
        # Generate a new session id
        session_id = str(uuid.uuid4())

        # set up customized chatbot
        chatbot = Chatbot(
            username=username,
            email=useremail,
            ip=ip,
            session_id=session_id,
            personality=personalityPicker,
            botname=BOT_NAME,
        )

        # Store the session data
        SESSIONS[session_id] = {
            "username": username,
            "email": useremail,
            "ip": ip,
            "chatbot": chatbot,
            "personality": personalityPicker,
            "model_version": chatbot.model_version,
        }

        print(f"Received user data for session with ID: {session_id}")
        print(
            [
                f"{k}:" + " " * (14 - len(k)) + f"{v}"
                for k, v in SESSIONS[session_id].items()
                if not k == "chatbot"
            ],
            type=mt.INFO,
        )
        greeting = chatbot.trigger_initial_prompt()
        response = templates.TemplateResponse(
            "chat.html",
            {
                "request": request,
                "timestamp": datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
                "botname": f"{BOT_NAME}",
                "greeting": greeting,
                "username": username,
                "ws_url": WS_URL,
            },
        )
        # Store the session id in a cookie
        # , domain="chat.halerium.ai", secure=False, httponly=False
        response.set_cookie(key="chat_halerium_session_id", value=session_id)
        return response

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
        if session is None and token is None:
            print("No Session ID provided. Closing websocket.", type=mt.ERROR)
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        return session or token

    @app.websocket("/prompt")
    async def bot_response(
        websocket: WebSocket, session_id: Annotated[str, Depends(get_session_id)]
    ):
        """
        Websocket connection for the chat function. Waits for a prompt and then queries the chatbot.
        Output function is a generator to allow for token-wise "streaming".
        """
        global SESSIONS

        if session_id not in SESSIONS:
            print(
                f"Session ID {str(session_id)} not found in active sessions. Closing websocket.",
                type=mt.ERROR,
            )
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        else:
            await websocket.accept()
            await asyncio.sleep(0)
            session_data = SESSIONS[session_id]
            chatbot = session_data["chatbot"]

        try:
            while True:
                # get prompt and timestamp
                prompt = await websocket.receive_text()
                if prompt == f"ping, {session_id}":
                    await websocket.send_text("<pong>")
                    continue

                print(
                    f'Received user prompt from {session_id} @ {datetime.now().strftime("%Y-%m-%d_%H_%M_%S_%ms")}',
                    type=mt.INFO,
                )

                # prompt model and send tokens to frontend once they become available
                now = time.time()
                full_message = ""
                n_token = 0
                async for token in chatbot.get_response(prompt):
                    if n_token == 0:
                        await websocket.send_text("<sos>")
                    # send token to frontend via websocket
                    await websocket.send_text(token)
                    # hack, to return control to the event loop:
                    # await asyncio.sleep(0)
                    # save token to full message
                    full_message += token
                    n_token += 1

                # end message
                await websocket.send_text("<eos>")
                # await asyncio.sleep(0)

                # append chatbot reponse to the history
                chatbot.shallow_history.append(
                    {"role": "assistant", "content": full_message}
                )
                chatbot.full_history.append(
                    {"role": "assistant", "content": full_message}
                )

                # # count responses
                # n_responses = sum([1 for i in chatbot.shallow_history if i['role'] == 'assistant'])
                # print([f'Number of responses: {n_responses}'], type=mt.INFO)

                # generation time
                delta = time.time() - now

                print(
                    f'Response for {session_id} finished @ {datetime.now().strftime("%Y-%m-%d_%H_%M_%S_%ms")}',
                    type=mt.SUCCESS,
                )

                # timing information
                try:
                    print(
                        f"Generation time: {n_token} token in {round(delta, 3)} s ({round(delta/n_token, 3)} s/token)",
                        type=mt.INFO,
                    )
                except:
                    pass

                # store history
                # filename = model.write_chat_to_disk(return_file_name = True)

                # # LIMIT TO 4 RESPONSES
                # if n_responses >= 4:
                #     await websocket.close()
                #     raise WebSocketDisconnect   # TODO: This is very unclean and needs to be changed eventually. I'm abusing this to always update the sessions and send the email

        except WebSocketDisconnect:
            print(f"Session {session_id} terminated. Deletion session.", type=mt.INFO)
            filename = chatbot.write_chat_to_disk(return_file_name=True)
            del SESSIONS[session_id]
            print(f"Remaining Sessions {SESSIONS}", type=mt.INFO)
            # send chat log via email
            postman = Postman()
            postman.send(filename)

    @app.post("/upload", response_class=HTMLResponse)
    async def upload(
        request: Request,
        file: UploadFile,
        session_id: Annotated[str, Depends(get_session_id)],
    ):
        """
        POST method to upload and prepare a PDF file
        When ready, serves the chatbot template with the chatbot set to use the custom vector storage
        """
        pass

    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    # run server
    parser = argparse.ArgumentParser(description="API Application")
    parser.add_argument(
        "--public",
        action="store_true",
        help="Run the app in public mode on port 8499 (default: False)",
    )
    args = parser.parse_args()
    main(public=args.public)

    # print(f'App is running at {APP_URL}', type=mt.INFO)
    # uvicorn.run('app.api:app', host="0.0.0.0", port=PORT,
    # reload=True)  # log_level="debug"
