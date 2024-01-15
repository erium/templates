import halerium_utilities as hu
import json
import os
from pathlib import Path
from .prettyprint import prettyprint as pprint, MessageType as mt
import re
import requests
from typing import List


class ConfigLogger:
    def __init__(self):
        self.log: dict = {'warnings': {}, 'errors': {}}

    def add(self, key: str, value: str, type_: str = "warnings"):
        if not type_ in self.log.keys():
            return "Log type not found. Please use either 'warnings' or 'errors'"

        if not key in self.log.get(type_):
            self.log.get(type_)[key] = value
        else:
            return "Key already exists."

    def get_log(self):
        return self.log

    def reset(self):
        self.log: dict = {'warnings': {}, 'errors': {}}


class Configuration:

    def __init__(self):
        self.polybot_board_path = Path("../polybot.board")
        self.board = hu.board.Board.from_json(self.polybot_board_path)
        self.navigator = hu.board.BoardNavigator(self.board)

        self.logger = ConfigLogger()

    def load(self) -> dict:
        """
        Reads the polybot.board and extracts parameters
        for a polybot instance

        Returns:
            dict: A dictionary with parameter names as keys and values as values.
        """

        navigator = self.navigator

        # get necessary cards
        cards = {
            "note": [],
            "setup": [],
            "bot": [],
            "vector-store-file": []
        }
        for card_id in navigator.cards:
            card_type = navigator.get_card_type(card_id)
            if card_type in cards:
                cards[card_type].append(card_id)

        config = {}

        # LLM setup cards (explicitely NO jupyter kernel setup cards)
        n_model_setup_cards = 0
        for card_id in cards.get("setup"):
            bot_type = navigator.get_bot_type(card_id)
            if bot_type != "jupyter-kernel" and n_model_setup_cards == 0:
                config["setup_card"] = navigator.cards[card_id].dict()
                system_message = navigator.get_setup_args(card_id).get("system_setup", "")
                config['model_version'] = bot_type
                config['system_message'] = system_message
                n_model_setup_cards += 1

            elif bot_type != "jupyter-kernel" and n_model_setup_cards > 0:
                self.logger.add('setup_cards',
                                'Multiple Bot Setup cards found. You can only set one. Taking the last Bot Setup card set.')

        # note cards
        for card_id in cards.get("note"):
            title = navigator.get_note_title(card_id)
            if title.lower() == "configuration":
                content = navigator.get_note_message(card_id)
                messages = content.split("\n")

                for message in messages:
                    key_value = message.split(":")
                    if len(key_value) == 2 and key_value[1]:
                        config[key_value[0]] = key_value[1].strip()
                    elif len(key_value) == 2 and not key_value[1]:
                        self.logger.add('note_card_missing_value',
                                        f"\"{message}\". Maybe you forgot to set the value? Ignoring argument.")
                    elif not len(key_value) == 2:
                        self.logger.add('note_card_argument_format',
                                        f"\"{message}\". Make sure to use the format: ARGUMENT_NAME: ARGUMENT_VALUE. Ignoring argument.")

        # find last prompt_card for chat entry
        prompt_chain = self._get_chain(config["setup_card"]["id"])
        card_id = prompt_chain[-1]
        card = self.board.get_card_by_id(card_id)
        config['initial_prompt_card'] = card.dict()
        prompt_input = navigator.get_prompt_input(card_id)
        prompt_output = navigator.get_prompt_output(card_id)
        config['initial_greeting_prompt'] = prompt_input
        config['initial_greeting_response'] = prompt_output

        # check if input and output are set. this is not allowed.
        if prompt_input != "" and prompt_output != "":
            self.logger.add('prompt_cards_initial_greeting',
                            "Prompt input and output set. You can only set one. Ignoring output.")
            config['initial_greeting_prompt'] = prompt_input
            config['initial_greeting_response'] = ""

        # vectorstore cards
        config['vectorstore_card_ids'] = []
        for card_id in cards.get("vector-store-file"):
            if navigator.connections_lookup[card_id]["context-output"]["source"]:
                config['vectorstore_card_ids'].append(card_id)
            else:
                self.logger.add('vectorstore_card', 'Found unconnected vectorstore card. Ignoring.')

        # add warnings and errors to board as cards
        self._add_logs_to_board(self.logger.get_log())

        return config

    def _get_chain(self, card_id: str, visited: set = None, chain: list = []) -> List[dict]:
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
        next_node_id = self._get_next_card(card_id)
        if next_node_id:
            self._get_chain(next_node_id, visited, chain)

        # return the chain
        return chain

    def _get_next_card(self, card_id: str):
        """
        Returns the id of the next prompt card in a chain.
        Only works with linear prompts, not with trees,
        because it will always take the first connection found.
        """

        navigator = self.navigator

        connection_ids = navigator.connections_lookup[card_id]["prompt-output"]["source"]

        if len(connection_ids) == 0:
            return None

        connection = navigator.connections[connection_ids[0]]

        next_id = connection.connections.target.id
        return next_id

    def _add_logs_to_board(self, log: dict):
        """
        Adds warnings and errors that occured during polybot configuration to the board as cards.

        Args:
            log (dict): The configuration log as obtained form the ConfigLogger class.
        """

        self._del_old_log_cards()

        warnings_string = "# Warnings\n"
        for k, v in log.get('warnings').items():
            warnings_string += f"**{k}**: {v}\n"

        w_card = self.board.create_card(
            type="note",
            position={"x": -660, "y": 170},
            size={"width": 860, "height": 400},
            type_specific=dict(
                message=warnings_string,
                color="note-color-7"
            )
        )

        errors_string = "# Errors\n"
        for k, v in log.get('errors').items():
            errors_string += f"**{k}**: {v}\n"

        e_card = self.board.create_card(
            type="note",
            position={"x": -660, "y": 580},
            size={"width": 860, "height": 400},
            type_specific=dict(
                content=errors_string,
                color="note-color-6"
            )
        )
        if warnings_string != "# Warnings\n":
            pprint("There are problems with your configuration. Please check the card.", msg_type=mt.WARNING)
            self.board.add_card(w_card)
            self.board.to_json(self.polybot_board_path)
        if errors_string != "# Errors\n":
            self.board.add_card(e_card)
            self.board.to_json(self.polybot_board_path)

    def _del_old_log_cards(self):
        """
        Deletes log cards added during a prior run.

        NOT IMPLEMENTED YET. HALERIUM_UTILITIES DOES NOT SUPPORT CARD REMOVAL YET.
        """
        pass
