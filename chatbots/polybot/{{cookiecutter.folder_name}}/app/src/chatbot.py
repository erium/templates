# infrastructure
import configparser
from datetime import datetime
from .environment import Environment
import halerium_utilities as hu
import httpx
import json
from pathlib import Path
import requests
from .prettyprint import prettyprint as pprint, MessageType as mt
import sseclient
import ssl
import uuid


class Chatbot:
    def __init__(
        self,
        config_global: configparser.ConfigParser,
        config_user: dict,
        env: Environment,
        username: str = "user",
        email: str = "none",
        ip: str = "none",
        session_id: str = "none",
    ):

        # store global configs
        self.config_global = config_global

        # store user configs
        self.config_user = config_user

        # load environment parameters and paths
        self.env = env
        self.prompt_server_url = self.env.get_prompt_server_url()
        self.chatlogs_dir = Path(self.config_global["paths"]["chatlogs_dir"])
        self.chatboards_dir = Path(self.config_global["paths"]["chatboards_dir"])

        # store session information
        self.session_start = datetime.now().strftime("%Y-%m-%d_%H_%M_%S_%f")
        self.session_id = session_id

        # store user and bot information
        self.botname = config_user.get("bot_name")
        self.personality = config_user.get("system_message")
        self.bot_knows_user = config_user.get("bot_knows_user").lower() == "true"
        self.username = username
        self.email = email
        self.ip = ip

        # set up model parameters
        self.model_version = self.config_user.get("model_version")

        # load vector storage
        self.vectorstore_ids = self.config_user.get("vectorstore_card_ids") or []
        
        # set up system prompt
        add_username = ""
        if self.bot_knows_user:
            add_username = f"\n\nDer Benutzer heißt: {self.username}.\n\n"

        self.system_prompt = self.personality + add_username
        pprint(f"Set bot personality to {self.personality}", msg_type=mt.INFO)
        pprint(f"Full system prompt: {self.system_prompt}", msg_type=mt.INFO)

        # store initial prompt/response
        self.initial_prompt = self.config_user.get("initial_greeting_prompt")
        self.initial_response = self.config_user.get("initial_greeting_response")

        # setup history for logging and chat
        self.is_initial_greeting = True
        self.board = hu.board.board.read_board("../polybot.board")
        self.current_prompt_card = self.config_user.get("initial_prompt_card")
        self.current_prompt_card_x = self.current_prompt_card.get("position")["x"]
        self.current_prompt_card_y = self.current_prompt_card.get("position")["y"]
        self.current_prompt_card_w = self.current_prompt_card.get("size")["width"]
        self.current_prompt_card_h = self.current_prompt_card.get("size")["height"]

        self.full_history = [
            {
                "username": self.username,
                "email": self.email,
                "ip": self.ip,
                "personality": self.personality,
            },
            {'role': 'system', 'content': self.system_prompt}
        ]

        if self.initial_prompt:
            self.shallow_history = [{'role': 'system', 'content': self.system_prompt}, 
                                    {'role': 'user', 'content': self.initial_prompt}]

            self.full_history.append({'role': 'user', 'content': self.initial_prompt})

        elif self.initial_response and not self.initial_prompt:
            self.shallow_history = [{'role': 'system', 'content': self.system_prompt}, 
                                    {'role': 'assistant', 'content': self.initial_response}]
            self.full_history.append({'role': 'assistant', 'content': self.initial_response})

    def write_chat_to_disk(self, return_file_name: bool = True):
        """
        Takes the chat history and writes it to disk.
        """
        # make sure chat logs directory exists
        if not Path(self.chatlogs_dir).exists():
            Path.mkdir(Path(self.chatlogs_dir))

        if not Path(self.chatboards_dir).exists():
            Path.mkdir(Path(self.chatboards_dir))

        # build filenames
        log_name = Path("_".join([self.session_start, self.session_id]) + ".json")
        log_name = self.chatlogs_dir / log_name

        board_name = Path("_".join([self.session_start, self.session_id]) + ".board")
        board_name = self.chatboards_dir / board_name

        try:
            hu.board.board.write_board(self.board, board_name)
        except Exception as e:
            print(f"Failed writing chat history to board {board_name}\nError: {e}")
        else:
            print(f"Wrote chat history to board {board_name}")

        try:
            with open(log_name, "w") as f:
                jsonChatHist = json.dump(self.full_history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed writing chat history to {log_name}\nError: {e}")
        else:
            print(f"Wrote chat history to {log_name}")
        
        if return_file_name:
            return f"{self.session_start}_{self.session_id}"

    async def evaluate(self, q: str = ""):
        """
        Evaluates user prompts via the prompt server

        Args:
            q (str): User prompt.

        Returns:
            str: Response.
        """
        url = f"{self.env.base_url}/api/tenants/{self.env.tenant}/projects/{self.env.workspace}/runners/{self.env.runner_id}/prompt"

        headers = {"halerium-runner-token": self.env.runner_token}

        outputs = []
        if not self.is_initial_greeting:
            self.current_prompt_card_x = self.current_prompt_card_x + self.current_prompt_card_w + 20

            new_prompt_card = {
                "id": str(uuid.uuid4()),
                "title": "",
                "type_specific": {
                    "message": "",
                    "assistant_type": "",
                    "system_setup": "",
                    "prompt_input": q,
                    "prompt_output": "",
                    "vector_store_file": "",
                    "vector_store_file_type": "",
                    "state": "initial",
                    "split_size": [16.6, 83.4],
                    "auto_size": True
                },
                "edge_connections": [],
                "type": "prompt-note",
                "position": {"x": self.current_prompt_card_x, "y": self.current_prompt_card_y},
                "size": {
                    "width": self.current_prompt_card_w,
                    "height": self.current_prompt_card_h
                },
                "color": "note-color-3",
                "attachments": {}
            }

            # add prompt card to board with user prompt
            hu.board.board.add_card_to_board(self.board, new_prompt_card)

            # register connections
            id_curr = self.current_prompt_card.get("id")
            id_new = new_prompt_card.get("id")
            prompt_edge_id = str(uuid.uuid4())
            for node in self.board.get("nodes"):
                if node.get("id") == id_new:
                    node.get("edge_connections").append({"id": prompt_edge_id, "connector": "prompt-input"})
                elif node.get("id") == id_curr:
                    node.get("edge_connections").append({"id": prompt_edge_id, "connector": "prompt-output"})
            self.board.get("edges").append({
                "id": prompt_edge_id,
                "type": "solid_line",
                "node_connections": [
                    id_curr, id_new
                ],
                "type_specific": {"annotation": "", "preventOutputCopy": False}
            })

            payload = {
            "board": self.board,
            "id": id_new,
            "tenant": self.env.tenant,
            "workspace": self.env.workspace
            }

            self.current_prompt_card = new_prompt_card
        
        else:
            # modify system prompt if bot_knows_user
            if self.bot_knows_user:
                for node in self.board.get("nodes"):
                    if node.get("id") == self.config_user.get("setup_card")["id"]:
                        node.get("type_specific")["system_setup"] = self.system_prompt

            self.is_initial_greeting = False
            payload = {
            "board": self.board,
            "id": self.current_prompt_card.get("id"),
            "tenant": self.env.tenant,
            "workspace": self.env.workspace
            }

        # prompt model
        try:
            pprint("Sending request to prompt server", msg_type=mt.INFO)
            ssl_context = ssl.create_default_context()
            timeout = httpx.Timeout(60.0, connect=60.0)
            n_chunk = 0
            full_message = ""

            # use the halerium prompt server for response generation
            async with httpx.AsyncClient(verify=ssl_context, timeout=None) as client:
                async with client.stream(
                    method="POST",
                    url=url,
                    json=payload,
                    headers=self.env.build_prompt_server_headers(),
                ) as response:
                    async for chunk in response.aiter_lines():
                        if "data: " in chunk:
                            content = json.loads(chunk[len("data: ") :])
                            n_chunk += 1
                            chunk = content.get("chunk")
                            completed = content.get("completed")
                            if chunk:
                                yield chunk
                                full_message += content.get("chunk")
                            elif completed:
                                yield completed

            # append chatbot reponse to the history
            self.shallow_history.append(
                {"role": "assistant", "content": full_message}
            )
            self.full_history.append(
                {"role": "assistant", "content": full_message}
            )
            for node in self.board.get("nodes"):
                if node.get("id") == self.current_prompt_card.get("id"):
                    node.get('type_specific')['prompt_output'] = full_message
                    break

        except httpx.TimeoutException as e:
            pprint(str(e), msg_type=mt.ERROR)
            yield f"I'm sorry, the model timed out. Please try again."

        except Exception as e:
            pprint(str(e), msg_type=mt.ERROR)
            yield f"I'm sorry, there has been an error: {e}"

