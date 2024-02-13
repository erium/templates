from .api import setup_api
import argparse
from .src.args import CLIArgs
from .src.board_manager import BoardManager as BM
from .src.db import DBOperations as DB, DBGlobal as DBG
from .src.environment import Environment
import logging
import logging.config
from .src.logging_formatter import ConsoleFormatter
import os
from pathlib import Path
import uvicorn


def main():
    """
    Collects the configuration, sets up logging and database, and starts the API.
    """
    # change to script directory
    file_path = os.path.abspath(__file__)
    dir_path = os.path.dirname(file_path)
    os.chdir(dir_path)

    # check if app was started with parameters
    # CLI args take precendece compared to board args!
    arg_parser = argparse.ArgumentParser(description="Polybot API")

    for arg in CLIArgs.args.values():
        names_or_flags = arg.pop("name_or_flags", [])
        arg_parser.add_argument(*names_or_flags, **arg)

    # parse cli and board arguments
    cli_args = arg_parser.parse_args()

    # check if there's a path argument and get the absolute path
    board_path = Path("../polybot.board").absolute().resolve()
    if cli_args.board:
        board_path = Path(cli_args.board).absolute().resolve()

    # configure all loggers
    setup_logging(default_level=cli_args.loglevel)
    # setup a logger
    logger = logging.getLogger(__name__)

    # log the configurations from cli and board
    logger.debug(f"cli_args: {cli_args}")
    board_args = BM.extract_user_config(board_path)
    logger.debug(f"board_args: {board_args}")

    # set the port
    port = 8501
    if cli_args.port:
        port = cli_args.port
    elif cli_args.public or str(board_args.get("public_hosting")).lower() == "true":
        port = 8499

    # set the skip login
    skip_login = (
        cli_args.skiplogin or str(board_args.get("skip_login")).lower() == "true"
    )

    # setup database
    DB.setup_database()

    # store the global configuration
    args = {
        "port": port,
        "skip_intro": skip_login,
        "intro_wide": cli_args.introtext
        if cli_args.introtext
        else board_args.get("intro"),
        "intro_narrow": cli_args.introtext
        if cli_args.introtext
        else board_args.get("intro"),
        "bot_name": cli_args.name if cli_args.name else board_args.get("bot_name"),
        "board_path": str(board_path),
        "debug_mode": int(1) if cli_args.debug else int(0),
    }
    DBG.set_config(**args)

    # create app
    app = setup_api(port=port, skip_login=skip_login, debug=True)

    # print out URL as convenience
    logger.info(f"{args['bot_name']} is running on {Environment.get_app_url(port)}")

    # run server
    uvicorn.run(app, host="0.0.0.0", port=port)


def setup_logging(default_level=logging.DEBUG):
    """
    Setup logging for the application.

    Args:
        default_level (int, optional): Sets the logging level. Defaults to logging.DEBUG (10).
    """
    # setup necessary paths
    Path.mkdir(Path(__file__).resolve().parent / "logs", exist_ok=True)

    logging_config = {
        "version": 1,
        "formatters": {
            "console": {
                "()": ConsoleFormatter,
                "format": "%(message)s (%(filename)s:%(lineno)d)",
            },
            "file": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": default_level,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "file",
                "level": logging.DEBUG,
                "filename": Path(__file__).resolve().parent
                / Path(f"logs/{__name__}.log"),
                "maxBytes": 1e6,
                "backupCount": 2,
            },
        },
        "loggers": {
            "": {  # Root Logger
                "handlers": ["console", "file"],
                "level": logging.DEBUG,
                "propagate": False,
            }
        },
    }

    logging.config.dictConfig(logging_config)


if __name__ == "__main__":
    main()
