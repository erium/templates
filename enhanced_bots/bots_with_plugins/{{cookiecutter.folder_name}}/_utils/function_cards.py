from datetime import datetime
import halerium_utilities as hu
import json
import os
from pathlib import Path
import uuid


class FunctionData:

    def __init__(self, path: str = 'service.py'):
        self.path = path

    def _read_text_file(self, path: str = 'service.py'):
        """
        Reads the content of a text file.

        Args:
            path (str, optional): Path to webservice file. Defaults to 'service.py'.

        Returns:
            str: The content of the file.
        """
        with open(path, 'r') as file:
            return file.read()

    def _parse_content(self, content: str) -> dict:
        """
        Parses the content of a service.py file and returns a dictionary of functions.
        Functions need to start with "def" and not contain "self".
        Functions also need to have a description in the form of a docstring.
        Docstring needs to have "Args:" and "Returns:" paragraphs.
        """
        # split content into chunks of functions
        functions_ = content.split('def')

        # remove empty functions_
        functions_ = [func for func in functions_ if func]

        # remove imports
        functions_ = [func for func in functions_ if 'import' not in func]

        # trim whitespaces
        functions_ = [func.strip() for func in functions_]

        # remove class functions
        functions_ = [func for func in functions_ if 'self' not in func]

        # get function names
        f_names = [func.split('():')[0] for func in functions_]

        # get function descriptions
        f_descs = []
        try:
            descs_raw = [func.split('"""')[1] for func in functions_]

            # remove line breaks and whitespaces
            for desc in descs_raw:
                desc = desc.replace('\n', ' ').strip().split()
                desc = ' '.join(desc)
                f_descs.append(desc)

        except IndexError as e:
            print(f'Error: Description missing in function')
            raise e

        # get function arguments from doc strings. They have to start with "Args:\n" and end with "Returns:\n"
        f_args = {}
        try:
            for i, func in enumerate(functions_):
                if 'Args:' in func and 'Returns:' in func:
                    # extract function arguments
                    args_raw = func.split('Args:')[1].split(
                        'Returns:')[0].split('\n')

                    # remove empty lines and whitespaces
                    args_raw = [arg.strip() for arg in args_raw if arg.strip()]

                    # format of args:
                    # arg (type): description
                    for arg in args_raw:
                        arg_name = arg.split('(')[0].strip()
                        arg_type = arg.split('(')[1].split(')')[0].strip()
                        arg_desc = arg.split(':')[1].strip()

                        # clean arg_type
                        if arg_type == 'int':
                            arg_type = 'number'
                        elif arg_type == 'str' or arg_type == 'any':
                            arg_type = 'string'
                        elif arg_type == 'list':
                            arg_type = 'array'

                        f_args[f_names[i]] = f_args[f_names[i]] | {arg_name: {'type': arg_type, 'description': arg_desc}} if f_args.get(
                            f_names[i]) else {arg_name: {'type': arg_type, 'description': arg_desc}}

        except Exception as e:
            print(f'Error: Failed to parse Args from function')
            raise e

        # create dictionary
        function_data = {f_names[i]: {
            'name': f_names[i],
            'desc': f_descs[i],
            'args': f_args.get(f_names[i])} for i in range(len(f_names))}

        return function_data

    def get_function_data(self):
        self.content = self._read_text_file()
        return self._parse_content(self.content)


class FunctionCards:

    def __init__(self, runner_id: str = os.getenv('HALERIUM_ID'), port: int = 8498, path: str = 'boards'):
        self.runner_id = runner_id
        self.port = port
        self.path = path

    def _generate_note_cards(self) -> list:
        """
        Generates function cards for the Halerium "Coding with Agents" template.

        Returns:
            list: A list of function cards.
        """
        cards = []
        i = 0
        for fname, fdata in self.functions.items():
            content = {
                "endpoint": {
                    "url": f"{os.getenv('HALERIUM_BASE_URL')}/apps/{self.runner_id}/{str(self.port)}/{fname}"
                },
                "function": {
                    "name": fname,
                    "description": fdata['desc'],
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }

            # check if this function has args, if so, add them to the content at key "properties"
            if fdata['args']:
                content['function']['parameters']['properties'] = fdata['args']
                content['function']['parameters']['required'] = list(
                    fdata['args'].keys())

            card = hu.board.board.create_card(
                title=f"Function: {fname}",
                content=json.dumps(content, indent=4),
                position={"x": 10, "y": 10 + i * 44},
                size={"width": 300, "height": 250},
                color="note-color-3",
            )

            i += 1

            # add other keys to card["type_specific"]
            card["type_specific"]["assistant_type"] = ""
            card["type_specific"]["system_setup"] = ""
            card["type_specific"]["prompt_input"] = ""
            card["type_specific"]["prompt_output"] = ""
            card["type_specific"]["vector_store_file"] = ""
            card["type_specific"]["vector_store_file_type"] = ""
            card["type_specific"]["state"] = "initial"
            card["type_specific"]["split_size"] = [16.6, 83.4]
            card["type_specific"]["auto_size"] = False

            # add other keys to card
            card["edge_connections"] = []
            card["type"] = "note"
            card["attachments"] = {}
            card["collapsed"] = True
            card["collapsed_size"] = {"width": 300, "height": 34}

            cards.append(card)

        return cards

    def _generate_bot_card(self, n_cards: int, bot_type: str = "chat-gpt-40", system_setup: str = "Du bist ein hilfsbereiter Assistent") -> dict:
        """
        Generates a bot card for the Halerium "Coding with Agents" template.

        Args:
            n_cards (int): Number of previously generated note cards.
            bot_type (str, optional): Bot type. Can be chat-gpt-35 or chat-gpt-40. Defaults to "chat-gpt-40".
            system_setup (str, optional): System message. Defaults to "Du bist ein hilfsbereiter Assistent".

        Returns:
            str: _description_
        """
        self.bot_card_y = 10 + n_cards * 44

        bot_card = {
            "id": str(uuid.uuid4()),
            "title": "",
            "type_specific": {
                "message": "",
                "assistant_type": bot_type,
                "system_setup": system_setup,
                "prompt_input": "Start a Python Kernel.",
                "prompt_output": "",
                "vector_store_file": "",
                "vector_store_file_type": "",
                "state": "initial",
                "split_size": [16.6, 83.4],
                "auto_size": True
            },
            "edge_connections": [],
            "type": "assistant-setup-note",
            "position": {"x": 320, "y": self.bot_card_y},
            "size": {"width": 280, "height": 210},
            "color": "note-color-3",
            "attachments": {}
        }

        return bot_card

    def _generate_initial_chat_card(self):

        chat_card = {
            "id": str(uuid.uuid4()),
            "title": "",
            "type_specific": {
                "message": "",
                "assistant_type": "",
                "system_setup": "",
                "prompt_input": "Start a Python Kernel.",
                "prompt_output": "",
                "vector_store_file": "",
                "vector_store_file_type": "",
                "state": "initial",
                "split_size": [16.6, 83.4],
                "auto_size": True
            },
            "edge_connections": [],
            "type": "prompt-note",
            "position": {"x": 630, "y": self.bot_card_y},
            "size": {
                "width": 520,
                "height": 320
            },
            "color": "note-color-3",
            "attachments": {}
        }

        return chat_card

    def _generate_unconnected_board(self, cards: list) -> dict:
        """
        Generates a board for the Halerium "Coding with Agents" template.

        Args:
            cards (list): List of cards.

        Returns:
            dict: The board.
        """

        board = hu.board.board.create_board()

        for card in cards:
            hu.board.board.add_card_to_board(
                board=board,
                card=card
            )

        return board

    def _generate_connections(self, board: dict) -> dict:
        """
        Modifies the board to add connections between the note cards and the bot card.

        Args:
            board (dict): The board without connections.

        Returns:
            dict: The board with connections.
        """

        # register connection between bot card and note cards
        bot_card_connections = {}
        for i, card in enumerate(board["nodes"]):
            if card['type'] == 'note':
                cuuid = str(uuid.uuid4())
                bot_card_connections[i] = {
                    'cuuid': cuuid, 'from': card['id']}
                card['edge_connections'].append(
                    {"id": cuuid, "connector": "right"})

            if card['type'] == 'prompt-note':
                cuuid = str(uuid.uuid4())
                bot_card_connections[i] = {
                    'cuuid': cuuid, 'to': card['id']}
                card['edge_connections'].append(
                    {"id": cuuid, "connector": "prompt-input"})

        # register connection with bot card
        bot_card_id = ''
        for i, card in enumerate(board["nodes"]):
            if card['type'] == 'assistant-setup-note':
                bot_card_id = card['id']
                for bcc in bot_card_connections.values():
                    # if incoming connection to bot card
                    if bcc.get('from'):
                        card['edge_connections'].append(
                            {"id": bcc['cuuid'], "connector": "context-input"})
                    # if outgoing connection from bot card
                    elif bcc.get('to'):
                        card['edge_connections'].append(
                            {"id": bcc['cuuid'], "connector": "prompt-output"})

        # register connection with board
        for bcc in bot_card_connections.values():
            # incoming connections to bot card
            if bcc.get('from'):
                board['edges'].append(
                    {"id": bcc['cuuid'], "type": "solid_arrow", "node_connections": [bcc['from'], bot_card_id], "type_specific": {"annotation": ""}})
            # outgoing connections from bot card
            elif bcc.get('to'):
                board['edges'].append(
                    {"id": bcc['cuuid'], "type": "solid_line", "node_connections": [bot_card_id, bcc['to']], "type_specific": {"annotation": "", "preventOutputCopy": False}})

        return board

    def generate_board(self, content: str, export: bool = False, filename: str = 'board') -> dict:
        """
        Generates a board for the Halerium "Coding with Agents" template,
        with note cards for each function and a connected bot card.

        When export is set to True, the board is exported as a JSON file.
        Otherwise, the board is returned as a dictionary.

        Args:
            export (bool, optional): If set to true, will write board to JSON file. Else, returns board as dict. Defaults to False.
            filename (str, optional): Filename of the board. Defaults to 'YYYYMMDD_hh-mm-ss_board'.

        Returns:
            dict: A connected Halerium board.
        """

        # generate cards, and unconnected board
        self.functions = content
        self.cards: list = self._generate_note_cards()
        self.bot_card: dict = self._generate_bot_card(len(self.cards))
        self.chat_card: dict = self._generate_initial_chat_card()
        self.cards.append(self.bot_card)
        self.cards.append(self.chat_card)
        self.board: dict = self._generate_unconnected_board(self.cards)

        # connect the cards
        self.connected_board: dict = self._generate_connections(self.board)

        if export:
            timestamp = datetime.now().strftime("%Y%m%d_%H-%M-%S")
            path_to_board = Path(self.path, f'{timestamp}_{filename}.board')

            if not Path(self.path).exists():
                Path(self.path).mkdir(parents=True, exist_ok=True)

            with open(path_to_board, 'w') as f:
                json.dump(self.connected_board, f,
                          indent=4, ensure_ascii=False)

            print(f'Board exported as {timestamp}_{filename}.board')

        else:
            return self.connected_board


if __name__ == "__main__":
    # create boards
    runner_id = os.getenv('HALERIUM_ID')
    fd = FunctionData(path='service.py')
    fc = FunctionCards(path='boards', port=8498)

    # generate board
    parsed_content = fd.get_function_data()
    board = fc.generate_board(content=parsed_content, export=True)
