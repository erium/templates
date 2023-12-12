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
from .src.configuration import Configuration
from .src.environment import Environment

# infrastructure
import argparse
import configparser
from datetime import datetime
import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from .src.prettyprint import prettyprint as print, MessageType as mt
import time
from typing import Annotated
import uuid

SESSIONS = {}

def main():
    # change to script directory
    file_path = os.path.abspath(__file__)
    dir_path = os.path.dirname(file_path)
    os.chdir(dir_path)

    # load global configs
    config_global = configparser.ConfigParser()
    config_global.read('config.conf')

    # load user configuration
    c = Configuration()
    config_user = c.load()
    model_intro = config_user.get('intro')
    model_version = config_user.get('model_version')
    bot_name = config_user.get('bot_name')
    is_public = config_user.get('public_hosting').lower() == 'true'

    # get environment parameters
    env = Environment()
    PORT = 8501
    if is_public:
        PORT = 8499

    # set environment routes
    APP_URL = env.get_app_url(port=PORT)
    WS_URL = env.get_websocket_url(port=PORT)


    class Data(BaseModel):
        username: str = Field(..., min_length=1, max_length=50)
        email: str = Field(..., min_length=6, max_length=50)
        ip: str = Field(..., min_length=8, max_length=50)

    print(
        f"App is running {'publicly' if is_public else 'privately'} at {APP_URL}",
        msg_type=mt.INFO,
    )

    # set up API
    app = FastAPI(debug=True)
    app.mount("/static", StaticFiles(directory=Path(config_global["paths"]["static"])), name="static")
    templates = Jinja2Templates(Path(config_global["paths"]["templates"]))
    app.root_path = f"/apps/{env.runner_id}/{PORT}/"

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """
        Serves the login template
        """
        intro_wide = (
            intro_narrow
        ) = model_intro
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "botname": bot_name,
                "intro_wide": intro_wide,
                "intro_narrow": intro_narrow,
                "form_post_url": app.root_path,
            },
        )

    @app.post("/", response_class=HTMLResponse)
    async def serve(
        request: Request,
        username: str = Form(...),
        useremail: str = Form("nan"),
        ip: str = Form("nan"),
    ):
        """
        POST method to collect user data.
        Userdata collected are Username, email, and ip address.

        Success with IP address may vary (depends on ipify.org, an external API)

        Serves the chat.html template
        """
        global SESSIONS
        # Generate a new session id
        session_id = str(uuid.uuid4())

        # set up customized chatbot
        chatbot = Chatbot(
            config_global=config_global,
            config_user=config_user,
            env=env,
            username=username,
            email=useremail,
            ip=ip,
            session_id=session_id,
        )

        # Store the session data
        SESSIONS[session_id] = {
            "username": username,
            "email": useremail,
            "ip": ip,
            "chatbot": chatbot,
            "personality": chatbot.system_prompt,
            "model_version": chatbot.model_version,
        }

        print(f"Received user data for session with ID: {session_id}")
        print(
            [
                f"{k}:" + " " * (14 - len(k)) + f"{v}"
                for k, v in SESSIONS[session_id].items()
                if not k == "chatbot"
            ],
            msg_type=mt.INFO,
        )
        greeting = ""
        async for token in chatbot.evaluate():
            if isinstance(token, str): # token is bool = True if completed
                greeting += token
        
        response = templates.TemplateResponse(
            "chat.html",
            {
                "request": request,
                "timestamp": datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
                "botname": bot_name,
                "greeting": greeting,
                "username": username,
                "ws_url": WS_URL,
                "app_url": APP_URL
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
            print("No Session ID provided. Closing websocket.", msg_type=mt.ERROR)
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
                msg_type=mt.ERROR,
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
                    f'Session {session_id} prompt @ {datetime.now().strftime("%Y-%m-%dT%H:%M:%S:%f")}',
                    msg_type=mt.INFO,
                )

                # prompt model and send tokens to frontend once they become available
                now = time.time()
                full_message = ""
                n_token = 0
                async for token in chatbot.evaluate(prompt):
                    if n_token == 0:
                        # begin message
                        await websocket.send_text("<sos>")
                    
                    if isinstance(token, bool):
                        # end message
                        await websocket.send_text("<eos>")
                    
                    elif isinstance(token, str):
                        # send token to frontend via websocket
                        await websocket.send_text(token)
                        # save token to full message
                        full_message += token
                        n_token += 1

                # generation time
                delta = time.time() - now

                print(
                    f'finished @ {datetime.now().strftime("%Y-%m-%dT%H:%M:%S:%f")}',
                    msg_type=mt.SUCCESS,
                )

                # timing information
                try:
                    print(
                        f"received and sent {n_token} token in {round(delta, 3)} s ({round(delta/n_token, 3)} s/token)",
                        msg_type=mt.INFO,
                    )
                except:
                    pass

        except WebSocketDisconnect:
            print(f"Session {session_id} terminated", msg_type=mt.INFO)
            chatbot.write_chat_to_disk(return_file_name=False)
            del SESSIONS[session_id]
            print(f"Remaining Sessions {SESSIONS}", msg_type=mt.INFO)
            # send chat log via email
            # postman = Postman(config_global)
            # postman.send(filename)

    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    # run server
    main()
