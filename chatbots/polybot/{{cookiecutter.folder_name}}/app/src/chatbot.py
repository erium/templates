# data handling, context finding, LLM
from .vectorstore import PromptServerEmbeddings
import chromadb

# infrastructure
import configparser
from datetime import datetime
from .environment import Environment
import httpx
import json
from pathlib import Path
import requests
from .prettyprint import prettyprint as pprint, MessageType as mt
import sseclient
import ssl


class Chatbot:
    def __init__(
        self,
        custom_db: chromadb.Client = None,
        username: str = "user",
        email: str = "none",
        ip: str = "none",
        botname: str = "Halerium",
        session_id: str = "none",
        personality: str = "",
    ):
        # load configs
        configs = configparser.ConfigParser()
        configs.read("config.conf")
        
        self.local = configs["app"]["local"] == "True"

        args = {}
        if self.local:
            args = {
                "base_url": "https://pro.halerium.ai",
                "tenant": "erium",
                "workspace": "64d22ad1c3c95e001224f120",
                "runner_id": "655f1775be762e001242e0c1",
                "runner_token": "ea2a4383-1ea4-45b0-918f-054b2792ffb2",
            }

        # load environment parameters
        self.env = Environment(local=self.local, args=args)
        self.prompt_server_url = self.env.get_prompt_server_url()

        # store session information
        self.session_start = datetime.now().strftime("%Y-%m-%d_%H_%M_%S_%ms")
        self.session_id = session_id

        # store user and bot information
        self.botname = botname
        self.persona_dir = configs["paths"]["persona_dir"]
        self.personality = personality
        self.username = username
        self.email = email
        self.ip = ip
        self.chatlogs_dir = configs["paths"]["chatlogs_dir"]

        # set up model parameters
        self.model_version = configs["model"]["version"]
        self.temperature = float(configs["model"]["temperature"])

        # set up system prompt
        self.system_prompt = self.load_personality()
        pprint(f"Set bot personality to {self.personality}", type=mt.INFO)

        # setup history for logging and chat
        self.full_history = [
            {
                "username": self.username,
                "email": self.email,
                "ip": self.ip,
                "personality": self.personality,
            },
            self.system_prompt,
        ]
        self.shallow_history = [self.system_prompt]

        # load vector storage
        self.vs_dir = configs["paths"]["vs_dir"]
        self.embedding_function = PromptServerEmbeddings()

        # load persistent vector storage if it exists
        if Path(self.vs_dir).exists():
            client = chromadb.PersistentClient(path=self.vs_dir)
            self.vectordb = client.get_collection(
                name="default",
                embedding_function=self.embedding_function,
            )
            pprint(f"Loaded vector database from {self.vs_dir}.", type=mt.INFO)
        elif not Path(self.vs_dir).exists():
            pprint(f'No vector database found at "{self.vs_dir}"', type=mt.WARNING)
            self.vectordb = None

    def load_personality(self):
        """
        Loads the bot personality requested by the user and returns its system prompt.
        """
        with open(self.persona_dir, "r") as f:
            return {
                "role": "system",
                "content": f"\nDu heißt {self.botname}.\n\n"
                + json.load(f)["personalities"][self.personality]
                + f"\nDer Benutzer heißt {self.username}",
            }

    def write_chat_to_disk(self, return_file_name: bool = True):
        """
        Takes the chat history and writes it to disk.
        """
        # make sure chat logs directory exists
        if not Path(self.chatlogs_dir).exists():
            Path.mkdir(Path(self.chatlogs_dir))

        # build filename
        log_name = Path("_".join([self.session_start, self.session_id]) + ".json")
        log_name = self.chatlogs_dir / log_name

        try:
            with open(log_name, "w") as f:
                jsonChatHist = json.dumps(
                    self.full_history, indent=4, ensure_ascii=False
                )
                f.write(jsonChatHist)
        except Exception as e:
            pprint(
                f"Failed writing chat history to {log_name}",
                f"Error: {e}",
                type=mt.WARNING,
            )
        else:
            pprint(f"Wrote chat history to {log_name}", type=mt.INFO)
            if return_file_name:
                return f"{self.session_start}_{self.session_id}"

    def generate_context(self, q: str):
        """
        Performs a context search

        Args:
            q (str): user query.

        Returns:
            str: cleaned context.
        """
        # extract context
        if self.vectordb:
            context = self.vectordb.query(query_texts=q, n_results=5)
            pprint("Successfully extracted context from VectorStorage", type=mt.INFO)

            # make sure some context was found
            if not len(context) > 0:
                pprint("No context was found.", type=mt.WARNING)

            clean_context = [d for d in context["documents"]]
            print(clean_context)

            return clean_context
        
        else:
            pprint("No vectorstorage to pull context from.", type=mt.WARNING)
            return ""

    def build_prompt(self, q: str, c: str):
        """
        Takes query and context and returns a prompt.
        """
        return {
            "role": "user",
            "content": f"""
        REFERENZTEXT: {c}

        ---
        ANFRAGE: {q}

        ---
        ANTWORT:
        """,
        }

    def shorten_prompt(self, p: list) -> list:
        """
        Checks the full prompt's length. If it exceeds chunken length set in self.max_chunkens,
        "forgets" part of the earlier history.

        Args:
            p (list): The prompt that is sent to the model

        Returns:
            list: Modified prompt
        """
        #! Not yet implemented
        return p

    async def get_response(self, q: str):
        """
        Looks for most relevant chunks in vector storage and prompts OpenAI's GPT3.5.
        Returns chunkens as they are generated.

        Args:
            q (str): User prompt.

        Returns:
            str: Response.
        """
        # generate context
        clean_context = self.generate_context(q)

        # build prompt
        shallow_prompt = self.build_prompt(q, "")  # prompt w/o context
        full_prompt = self.build_prompt(q, clean_context)  # prompt w/ context

        # build chat_history and log_history
        # add prompt w/o context to shallow_history
        self.shallow_history.append(shallow_prompt)
        # add prompt w/ context to full history
        self.full_history.append(full_prompt)

        # the previous 5 prompts w/o context and responses plus the current prompt w/ context
        semi_shallow_history = self.shallow_history[-5:] + [full_prompt]

        # prompt model
        try:
            pprint("Sending prompt to prompt server", type=mt.INFO)

            ssl_context = ssl.create_default_context()
            timeout = httpx.Timeout(60.0, connect=60.0)
            n_chunk = 0
            # use the halerium prompt server for response generation
            async with httpx.AsyncClient(verify=ssl_context, timeout=timeout) as client:
                async with client.stream(
                    method="POST",
                    url=self.prompt_server_url,
                    json=self.env.build_prompt_server_payload(
                        semi_shallow_history, self.model_version
                    ),
                    headers=self.env.build_prompt_server_headers(),
                ) as response:
                    async for chunk in response.aiter_lines():
                        if "data: " in chunk:
                            yield json.loads(chunk[len("data: ") :]).get("chunk")
                            n_chunk += 1
                            pprint(
                                f'Received chunk {n_chunk} @ {datetime.now().strftime("%Y-%m-%d_%H_%M_%S_%ms")}',
                                type=mt.INFO,
                                end="\r",
                            )

        except httpx.TimeoutException as e:
            pprint(str(e), type=mt.ERROR)
            yield f"I'm sorry, the model timed out. Please try again."

        except Exception as e:
            pprint(str(e), type=mt.ERROR)
            yield f"I'm sorry, there has been an error: {e}"

    def trigger_initial_prompt(self) -> str:
        # use the halerium prompt server
        response = requests.post(
            url=self.prompt_server_url,
            json=self.env.build_prompt_server_payload(
                self.shallow_history
                + [{"role": "user", "content": f"Hallo! Ich bin {self.username}"}],
                self.model_version,
            ),
            headers=self.env.build_prompt_server_headers(),
            stream=True,
        )

        # listen for SSE
        greeting = ""
        client = sseclient.SSEClient(response)
        for event in client.events():
            if event.event == "chunk":
                try:
                    greeting += json.loads(event.data).get("chunk")
                except json.JSONDecodeError as e:
                    greeting = e
        return greeting


if __name__ == "__main__":
    model = Chatbot()
