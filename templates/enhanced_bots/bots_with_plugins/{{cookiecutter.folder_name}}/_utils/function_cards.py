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

                        f_args[f_names[i]] = f_args[f_names[i]] | {
                            arg_name: {'type': arg_type, 'description': arg_desc}} if f_args.get(
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

    def _generate_function_cards(self) -> list:
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

            card = hu.board.Board.create_card(
                type="note",
                position={"x": 10, "y": 10 + i * 44},
                size={"width": 300, "height": 34},
                type_specific=dict(
                    title=f"Function: {fname}",
                    message=json.dumps(content, indent=4),
                    color="note-color-3",
                    auto_size=False,
                )
            )

            i += 1

            cards.append(card)

        return cards

    def _generate_setup_card(self, n_cards: int, bot_type: str = "chat-gpt-40",
                             system_setup: str = "Du bist ein hilfsbereiter Assistent") -> dict:
        """
        Generates a bot card for the Halerium "Coding with Agents" template.

        Args:
            bot_type (str, optional): Bot type. Can be chat-gpt-35 or chat-gpt-40. Defaults to "chat-gpt-40".
            system_setup (str, optional): System message. Defaults to "Du bist ein hilfsbereiter Assistent".

        Returns:
            node: The setup card
        """
        self.setup_card_y = 10 + n_cards * 44

        setup_card = hu.board.Board.create_card(
            type="setup",
            position={"x": 320, "y": self.setup_card_y},
            size={"width": 280, "height": 210},
            type_specific=dict(
                bot_type=bot_type,
                setup_args={"system_setup": system_setup},
            )
        )

        return setup_card

    def _generate_initial_bot_card(self):

        bot_card = hu.board.Board.create_card(
            type="bot",
            position={"x": 630, "y": self.setup_card_y},
            size={"width": 520, "height": 320},
            type_specific=dict(
                prompt_input="Start a Python Kernel.",
            )
        )

        return bot_card

    def _make_connections(self) -> None:
        """
        Modifies the board to add connections between the note cards and the bot card.
        """

        board = self.board

        # gather ids
        function_cards = self.function_cards
        setup_card = self.setup_card
        bot_card = self.bot_card

        # make connections between function cards and setup card
        for card in function_cards:
            conn = board.create_connection(
                type="solid_arrow",
                connections={
                    "source": {"id": card.id, "connector": "note-right"},
                    "target": {"id": setup_card.id, "connector": "context-input"}
                }
            )
            board.add_connection(conn)

        # make connection between setup and bot
        board.add_connection(
            board.create_connection(
                type="prompt_line",
                connections={
                    "source": {"id": setup_card.id, "connector": "prompt-output"},
                    "target": {"id": bot_card.id, "connector": "prompt-input"}
                }
            )
        )

    def generate_board(self, content: str, export: bool = False, filename: str = 'board'):
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
        self.function_cards: list = self._generate_function_cards()
        self.setup_card: dict = self._generate_setup_card(len(self.function_cards))
        self.bot_card: dict = self._generate_initial_bot_card()

        self.board = hu.board.Board()
        for card in self.function_cards + [self.setup_card, self.bot_card]:
            self.board.add_card(card)

        # connect the cards
        self._make_connections()

        if export:
            timestamp = datetime.now().strftime("%Y%m%d_%H-%M-%S")
            path_to_board = Path(self.path, f'{timestamp}_{filename}.board')

            if not Path(self.path).exists():
                Path(self.path).mkdir(parents=True, exist_ok=True)

            self.board.to_json(path_to_board)

            print(f'Board exported as {timestamp}_{filename}.board')

        else:
            return self.board


if __name__ == "__main__":
    # create boards
    runner_id = os.getenv('HALERIUM_ID')
    fd = FunctionData(path='service.py')
    fc = FunctionCards(path='boards', port=8498)

    # generate board
    parsed_content = fd.get_function_data()
    board = fc.generate_board(content=parsed_content, export=True)
