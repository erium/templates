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
        with open(self.polybot_board_path, "r") as f:
            self.board = json.load(f)

        self.logger = ConfigLogger()

    def load(self) -> dict:
        """
        Reads the polybot.board and extracts parameters
        for a polybot instance

        Returns:
            dict: A dictionary with parameter names as keys and values as values.
        """

        # get necessary cards
        note_cards = self._get_cards_of_type("note")
        setup_cards = self._get_cards_of_type("assistant-setup-note")
        prompt_cards = self._get_cards_of_type("prompt-note")
        vector_cards = self._get_cards_of_type("vectorstore-note")

        cards = {
            "note_cards": note_cards,
            "setup_cards": setup_cards, 
            "prompt_cards": prompt_cards,
            "vector_cards": vector_cards
        }

        config = {}

        # LLM setup cards (explicitely NO jupyter kernel setup cards)
        n_model_setup_cards = 0
        for card in cards.get("setup_cards"):
            if card.get("type_specific")["assistant_type"] != "jupyter-kernel" and n_model_setup_cards == 0:
                config["setup_card"] = card
                model_version = card['type_specific']['assistant_type']
                system_message = card['type_specific']['system_setup']
                config['model_version'] = model_version
                config['system_message'] = system_message
                n_model_setup_cards += 1

            elif card.get("type_specific")["assistant_type"] != "jupyter-kernel" and n_model_setup_cards > 0:
                self.logger.add('setup_cards', 'Multiple Bot Setup cards found. You can only set one. Taking the last Bot Setup card set.')

        # note cards
        for card in cards.get("note_cards"):
            title = card["title"]
            if title.lower() == "configuration":
                content = card["type_specific"]["message"]
                messages = content.split("\n")

                for message in messages:
                    key_value = message.split(":")
                    if len(key_value) == 2 and key_value[1]:
                        config[key_value[0]] = key_value[1].strip()
                    elif len(key_value) == 2 and not key_value[1]:
                        self.logger.add('note_card_missing_value', f"\"{message}\". Maybe you forgot to set the value? Ignoring argument.")
                    elif not len(key_value) == 2:
                        self.logger.add('note_card_argument_format', f"\"{message}\". Make sure to use the format: ARGUMENT_NAME: ARGUMENT_VALUE. Ignoring argument.")
        

        # find last prompt_card for chat entry
        prompt_chain = self._get_chain(config["setup_card"]["id"])
        for card in cards.get("prompt_cards"):
            if card.get("id") == prompt_chain[-1]:
                config['initial_prompt_card'] = card
                config['initial_greeting_prompt'] = card['type_specific']['prompt_input']
                config['initial_greeting_response'] = card['type_specific']['prompt_output']

                # check if input and output are set. this is not allowed.
                if card['type_specific']['prompt_input'] != "" and card['type_specific']['prompt_output'] != "":
                    self.logger.add('prompt_cards_initial_greeting', "Prompt input and output set. You can only set one. Ignoring output.")
                    config['initial_greeting_prompt'] = card['type_specific']['prompt_input']
                    config['initial_greeting_response'] = ""

        # vectorstore cards
        config['vectorstore_card_ids'] = []
        for i, card in enumerate(cards.get("vector_cards")):
            if self._get_type_of_connected_card(card['id']):
                config['vectorstore_card_ids'].append(card['id'])
            else:
                self.logger.add('vectorstore_card', 'Found unconnected vectorstore card. Ignoring.')
            

        # add warnings and errors to board as cards
        self._add_logs_to_board(self.logger.get_log())

        return config

    def _get_cards_of_type(self, card_type: str = "") -> List[dict]:
        """
        Args:
            card_type (str): Type of cards to be returned (e.g. "note", "assistant_setup_note", ...)

        Returns:
            list: a list of Halerium Board cards of a specific type.
        """
        cards = self.board.get("nodes")

        note_cards = []
        if cards:
            if card_type:
                note_cards = [card for card in cards if card.get("type") == card_type]
            else:
                return cards
                
        return note_cards
    
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

        # find connection ID of current card
        for node in self.board.get("nodes"):
            connection_id = ""
            if node.get("id") == card_id:
                for connection in node.get("edge_connections"):
                    if connection.get("connector") == "prompt-output":
                        connection_id = connection.get("id")
                        break
                break
        
        # look for connected card in connection id
        for edge in self.board.get("edges"):
            if edge.get("id") == connection_id:
                for connected_card_id in edge.get("node_connections"):
                    if not connected_card_id == card_id:
                        return connected_card_id

    def _get_type_of_connected_card(self, card_id: str):
        """
        Get the type of the connected card
        """
        node_ids = []
        for edge in self.board['edges']:
            if card_id in edge['node_connections']:
                node_ids = edge['node_connections']
                break
        
        if len(node_ids) == 0:
            return None

        for card in self.board['nodes']:
            if card['id'] in node_ids and card['id'] != card_id:
                return card['type_specific'].get('assistant_type')


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

        w_card = hu.board.board.create_card(
            title="",
            content=warnings_string,
            position={"x": -660, "y": 170},
            size={"width": 860, "height": 400},
            color="note-color-7"
        )

        errors_string = "# Errors\n"
        for k, v in log.get('errors').items():
            errors_string += f"**{k}**: {v}\n"

        e_card = hu.board.board.create_card(
            title="",
            content=errors_string,
            position={"x": -660, "y": 580},
            size={"width": 860, "height": 400},
            color="note-color-6"
        )
        if warnings_string != "# Warnings\n":
            pprint("There are problems with your configuration. Please check the card.", msg_type=mt.WARNING)
            hu.board.board.add_card_to_board(board=self.polybot_board_path, card=w_card)
        if errors_string != "# Errors\n":
            hu.board.board.add_card_to_board(board=self.polybot_board_path, card=e_card)

    def _del_old_log_cards(self):
        """
        Deletes log cards added during a prior run.

        NOT IMPLEMENTED YET. HALERIUM_UTILITIES DOES NOT SUPPORT CARD REMOVAL YET.
        """
        pass
