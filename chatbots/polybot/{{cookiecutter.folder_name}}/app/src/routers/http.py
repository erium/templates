from ..board_manager import BoardManager as BM
from ..chatbot import Chatbot
from ..db import DBSessions as DBS, DBBoard as DBB, DBGlobal as DBG
from datetime import datetime
from ..environment import Environment
from fastapi import (
    APIRouter,
    Form,
    Request,
)
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["api"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def root_get(request: Request):
    config = DBG.get_config()

    # check if intro should be skipped
    skip_intro = config.get("skip_intro") == 1
    if skip_intro:
        logger.debug("skipping login page: redirecting to chat.html")
        # pre-configure chatbot
        username = "User"
        useremail = "nan"
        userip = "nan"

        form_data = {
            "username": username,
            "useremail": useremail,
            "ip": userip,
        }

        return await root_post(request, **form_data)
    else:
        # intro text
        intro_wide = config.get("intro_wide")
        intro_narrow = config.get("intro_narrow")

        # get templates
        templates = Jinja2Templates(
            directory=Path(__file__).resolve().parent / Path("../../frontend/templates")
        )

        # get app.root_path
        root_path = Environment.get_app_root_path(config.get("port"))

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "botname": config.get("bot_name"),
                "intro_wide": intro_wide,
                "intro_narrow": intro_narrow,
                "form_post_url": root_path,
            },
        )


@router.post("/")
async def root_post(
    request: Request,
    username: str = Form(...),
    useremail: str = Form("nan"),
    ip: str = Form("nan"),
):
    """
    Serves the chat template with default values for a session without login.
    """
    logger.info("Serving chat.html")
    templates = Jinja2Templates(
        directory=Path(__file__).resolve().parent / Path("../../frontend/templates")
    )

    session_data = dict(
        username=username,
        useremail=useremail,
        userip=ip,
    )

    # add new session, board, and chatbot configuration to database
    session_id = DBS.add_session(**session_data)
    polybot_board_path = DBG.get_config().get("board_path")
    polybot_board = BM.get_board(path=polybot_board_path, as_dict=True)
    config = BM.extract_user_config(path=polybot_board_path)
    config["bot_name"] = DBG.get_config().get("bot_name")
    config["username"] = username
    DBB.add_board(session_id, polybot_board, config.get("current_bot_card_id"))
    Chatbot.setup(session_id, config)

    c = DBG.get_config()
    port = c.get("port")
    response = templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "timestamp": datetime.now().strftime("%Y.%m.%d, %H:%M:%S"),
            "botname": config.get("bot_name"),
            "initial_prompt": config.get("initial_prompt"),
            "initial_response": config.get("initial_response"),
            "username": username,
            "ws_text_url": Environment.get_websocket_url(port),
            "ws_audio_url": Environment.get_websocket_url(port),
            "app_url": Environment.get_app_url(port)
            if not Environment._is_local()
            else "/",
        },
    )

    # Store the session id in a cookie
    # , domain="chat.halerium.ai", secure=False, httponly=False
    response.set_cookie(key="chat_halerium_session_id", value=session_id)
    return response
