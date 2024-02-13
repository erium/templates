from .chatbot_roles import ChatbotRoles
from enum import Enum
from halerium_utilities.board.board import Board
from halerium_utilities.board.schemas import Node
from halerium_utilities.board.navigator import BoardNavigator
import io
import json
import logging
from pathlib import Path
from typing import List


class CardSettings(Enum):
    """
    Enum class for card settings.
    """

    WIDTH = 520
    HEIGHT = 320
    MARGIN = 20


class BoardManager:
    logger = logging.getLogger(__name__)

    @staticmethod
    def get_board(
        path: Path,
        as_dict: bool = False,
    ) -> Board | dict:
        """
        Returns the polybot.board either as Board or as dictionary.

        Args:
            path (Path): The absolute path to the board that should be used as template.
            as_dict (bool, optional): Returns the board as dict if true, else Board. Defaults to False.

        Returns:
            Board | dict: Board or dict object of the loaded Halerium board.
        """
        try:
            with open(path, "r") as f:
                board = Board.from_json(f)
        except FileNotFoundError:
            BoardManager.logger.error(f"Board file {path} not found.")
        else:
            BoardManager.logger.debug("loaded board file")
            return board if not as_dict else board.to_dict()

    @staticmethod
    def _new_conversation_card(message: str, current_card: Node) -> Node:
        current_card_pos = current_card.position

        new_card = Board.create_card(
            type="bot",
            size={
                "width": CardSettings.WIDTH.value,
                "height": CardSettings.HEIGHT.value,
            },
            position={
                "x": current_card_pos.x
                + CardSettings.WIDTH.value
                + CardSettings.MARGIN.value,
                "y": current_card_pos.y,
            },
            type_specific={
                "prompt_input": message,
                "prompt_output": "",
            },
        )

        return new_card

    @staticmethod
    def update_board(
        board: dict, current_card_id: str, role: str, message: str, attachment: str = ""
    ) -> dict:
        with io.StringIO(json.dumps(board)) as board_io:
            board: Board = Board.from_json(board_io)

        current_card = board.get_card_by_id(current_card_id)

        # if role is user, add user_prompt a new card
        if role == ChatbotRoles.USER.value:
            new_card = BoardManager._new_conversation_card(message, current_card)

            BoardManager.logger.debug(f"Current card id: {current_card_id}")
            BoardManager.logger.debug(f"New card id: {new_card.id}")

            # add new card with connections
            board.add_card(new_card)
            edge = board.create_connection(
                type="prompt_line",
                connections={
                    "source": {"id": current_card.id, "connector": "prompt-output"},
                    "target": {"id": new_card.id, "connector": "prompt-input"},
                },
            )
            BoardManager.logger.debug(f"New edge: {edge}")

            board.add_connection(edge)

            BoardManager.logger.debug("Added new conversation card with user prompt.")
            return dict(board=board.to_dict(), new_card_id=new_card.id)

        elif role == ChatbotRoles.ASSISTANT.value:
            # if role is assistant, update prompt_output
            current_card.type_specific.prompt_output = message

            BoardManager.logger.debug(
                "Updated current conversation card with bot response."
            )

            # if there is an attachment (images), add the attachment to the card
            if attachment:
                BoardManager.logger.debug("Adding attachment to card.")
                current_card.type_specific.attachments = {
                    "output_image.png": {"image/png": attachment}
                }
                BoardManager.logger.debug("Added attachment to card.")

            return {"board": board.to_dict(), "new_card_id": current_card.id}

        elif role == ChatbotRoles.SYSTEM.value:
            # if role is system, update the setup card's system message
            nav = BoardNavigator(board)
            setup_card_id = nav.get_setup_card_id(current_card_id)
            setup_card = board.get_card_by_id(setup_card_id)
            setup_card.type_specific.setup_args["system_setup"] += message

            BoardManager.logger.debug("Updated setup card's system message")
            return dict(board=board.to_dict(), new_card_id=current_card.id)

    @staticmethod
    def extract_user_config(path: Path = None, board: Board = None):
        """
        Extracts the user configuration from the board.
        """
        if not board and path:
            board = BoardManager.get_board(path)

        navigator = BoardNavigator(board)

        # get all cards
        cards = {"note": [], "setup": [], "bot": [], "vector_store_file": []}
        for card_id in navigator.cards:
            card_type = navigator.get_card_type(card_id)
            if card_type in cards:
                cards[card_type].append(card_id)

        # get setup message
        setup_card_id = ""
        setup_message = ""
        setup_model = ""
        n_setup_cards = 0
        for card in cards.get("setup"):
            if navigator.get_bot_type(card) != "jupyter-kernel":
                setup_card = board.get_card_by_id(card)
                setup_card_id = card
                setup_message = setup_card.type_specific.setup_args["system_setup"]
                setup_model = navigator.get_bot_type(card)
                n_setup_cards += 1

        if n_setup_cards > 1:
            BoardManager.logger.error(
                "Polybot ConfigurationError: Only one LLM setup card is allowed."
            )
            raise ValueError(
                "Polybot ConfigurationError: Only one LLM setup card is allowed."
            )

        # get configuration parameters
        params = {}
        for card in cards.get("note"):
            title = navigator.get_note_title(card)

            if title.lower() == "configuration":
                content = navigator.get_note_message(card)
                messages = content.split("\n")

                # remove empty messages (can happen when there's a trailing \n)
                messages = [m for m in messages if m]

                for message in messages:
                    key_value = message.split(":")
                    if len(key_value) == 2 and key_value[1]:
                        params[key_value[0]] = key_value[1].strip()
                    elif len(key_value) == 2 and not key_value[1]:
                        BoardManager.logger.warning(
                            f"Note card missing value: {message}"
                        )
                    elif not len(key_value) == 2:
                        BoardManager.logger.warning(
                            f"Note card argument format not correct: '{message}'. Arguments should be in the format: ARGUMENT_NAME: ARGUMENT_VALUE"
                        )

        # get last bot card in prompt chain starting with the setup card
        current_bot_card_id = BoardManager._get_chain(card_id=setup_card_id, path=path)[
            -1
        ]

        # extract prompt in- and output
        initial_prompt_input = navigator.get_prompt_input(current_bot_card_id)
        initial_prompt_output = navigator.get_prompt_output(current_bot_card_id)

        # build parameter dictionary

        configuration = {
            **params,
            "setup_card_id": setup_card_id,
            "setup_message": setup_message,
            "setup_model": setup_model,
            "current_bot_card_id": current_bot_card_id,
            "initial_prompt": initial_prompt_input,
            "initial_response": initial_prompt_output,
        }

        return configuration

    @staticmethod
    def _get_chain(
        path: Path, card_id: str, visited: set = None, chain: list = []
    ) -> List[dict]:
        """
        Args:
            card_id (str): Card ID of the first card in a chain
        Returns:
            list: List of card dictionaries (the prompt chain)
        """
        if not visited:
            visited = set()
            chain = []

        if card_id in visited:
            return

        # mark current node as visited
        visited.add(card_id)

        # add to chain
        chain.append(card_id)

        # recursively step over connected nodes
        next_node_id = BoardManager._get_next_card(card_id, path)
        if next_node_id:
            BoardManager._get_chain(path, next_node_id, visited, chain)

        # return the chain
        return chain

    @staticmethod
    def _get_next_card(card_id: str, path: Path) -> str | None:
        """
        Returns the id of the next prompt card in a chain.
        Only works with linear prompts, not with trees,
        because it will always take the first connection found.
        """
        board = BoardManager.get_board(path=path)
        navigator = BoardNavigator(board)
        connection_ids = navigator.connections_lookup[card_id]["prompt-output"][
            "source"
        ]
        if len(connection_ids) == 0:
            return None

        connection = navigator.connections[connection_ids[0]]
        next_id = connection.connections.target.id
        return next_id

    @staticmethod
    def export_as_json(board: dict, name: str = ""):
        """
        Exports the board as json.
        """
        try:
            with open(f"test{name}.board", "w") as f:
                json.dump(board, f)
        except Exception as e:
            BoardManager.logger.error(f"Error exporting board: {e}")
