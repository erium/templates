from configparser import ConfigParser
from enum import Enum
import logging
import os
from pathlib import Path


class EnvSection(Enum):
    ENVIRONMENT = "environment"


class Environment:
    logger = logging.getLogger(__name__)

    @staticmethod
    def get_env_params():
        if Environment._is_local():
            cp = ConfigParser()
            cp.read(Path(__file__).resolve().parent / Path("../env.conf"))
            if EnvSection.ENVIRONMENT.value in cp.sections():
                args = {k: v for k, v in cp.items(section=EnvSection.ENVIRONMENT.value)}
                return args
            else:
                Environment.logger.error(
                    "No environment parameters found: Parameters have to be defined in env.conf for local use!"
                )
                return {}

        else:
            return dict(
                base_url=Environment.get_base_url(),
                tenant=Environment.get_tenant(),
                workspace=Environment.get_workspace(),
                runner_id=Environment.get_runner_id(),
                runner_token=Environment.get_runner_token(),
            )

    @staticmethod
    def _is_local() -> bool:
        """
        Returns True if the environment is local.

        Returns:
        bool: True if the environment is local.
        """
        return os.getenv("HALERIUM_BASE_URL") is None

    @staticmethod
    def get_base_url() -> str:
        """
        Returns the base URL for the environment.

        Returns:
        str: The base URL for the environment.
        """
        if Environment._is_local():
            return "127.0.0.1"
        else:
            return os.getenv("HALERIUM_BASE_URL")

    @staticmethod
    def get_tenant() -> str:
        """
        Returns the tenant key for the environment.

        Returns:
        str: The tenant key for the environment.
        """
        return os.getenv("HALERIUM_TENANT_KEY")

    @staticmethod
    def get_workspace() -> str:
        """
        Returns the project ID for the environment.

        Returns:
        str: The project ID for the environment.
        """
        return os.getenv("HALERIUM_PROJECT_ID")

    @staticmethod
    def get_runner_id() -> str:
        """
        Returns the runner ID for the environment.

        Returns:
        str: The runner ID for the environment.
        """
        return os.getenv("HALERIUM_ID")

    @staticmethod
    def get_runner_token() -> str:
        """
        Returns the runner token for the environment.

        Returns:
        str: The runner token for the environment.
        """
        return os.getenv("HALERIUM_TOKEN")

    @staticmethod
    def get_models_endpoint_url() -> str:
        """
        Returns the URL for the prompt server models endpoint.

        Returns:
        str: The prompt server URL for the models endpoint.
        """
        env_params = Environment.get_env_params()
        base_url = env_params["base_url"]
        tenant = env_params["tenant"]
        workspace = env_params["workspace"]
        runner_id = env_params["runner_id"]
        return f"{base_url}/api/tenants/{tenant}/projects/{workspace}/runners/{runner_id}/models"

    @staticmethod
    def get_agents_endpoint_url() -> str:
        """
        Returns the URL for the prompt server agents endpoint.

        Returns:
            str: The prompt server URL for the agents endpoint.
        """
        env_params = Environment.get_env_params()
        base_url = env_params["base_url"]
        tenant = env_params["tenant"]
        workspace = env_params["workspace"]
        runner_id = env_params["runner_id"]
        return f"{base_url}/api/tenants/{tenant}/projects/{workspace}/runners/{runner_id}/agents"

    @staticmethod
    def build_models_endpoint_payload(messages: list, model_id: str) -> dict:
        """
        Builds a payload for the prompt server's models endpoint.

        Args:
        messages (list): A list of messages to include in the payload.
        model_id (str): The ID of the model to use for the payload.

        Returns:
        dict: The payload for the prompt server.
        """
        env_params = Environment.get_env_params()
        tenant = env_params["tenant"]
        workspace = env_params["workspace"]
        if model_id == "whisper":
            return {
                "model_id": model_id,
                "body": {"audio": messages},
                "tenant": tenant,
                "workspace": workspace,
            }

        return {
            "model_id": model_id,
            "body": {"messages": messages},
            "tenant": tenant,
            "workspace": workspace,
        }

    @staticmethod
    def build_agents_endpoint_payload(board: dict, card_id: str) -> dict:
        """
        Builds a payload for the prompt server's agents endpoint.

        Args:
        messages (list): A list of messages to include in the payload.
        agent_id (str): The ID of the agent to use for the payload.

        Returns:
        dict: The payload for the prompt server.
        """
        return {
            "board": board,
            "id": card_id,
        }

    @staticmethod
    def build_embedding_payload(text_chunks: str, model_id: str) -> dict:
        """
        Builds a payload for the prompt server.

        Args:
        text (str): The text to embed.
        model_id (str): The ID of the model to use for the payload.

        Returns:
        dict: The payload for the prompt server.
        """
        env_params = Environment.get_env_params()
        tenant = env_params["tenant"]
        workspace = env_params["workspace"]
        return {
            "model_id": model_id,
            "body": {"text_chunks": text_chunks},
            "tenant": tenant,
            "workspace": workspace,
        }

    @staticmethod
    def build_prompt_server_headers() -> dict:
        """
        Builds headers for the prompt server (works for models and agents endpoint).

        Returns:
        dict: The headers for the prompt server.
        """
        env_params = Environment.get_env_params()
        runner_token = env_params["runner_token"]
        return {"halerium-runner-token": runner_token, "X-Accel-Buffering": "no"}

    @staticmethod
    def get_app_root_path(port: int | str) -> str:
        """
        Returns the root path for the app.

        Returns:
        str: The root path for the app.
        """
        env_params = Environment.get_env_params()
        runner_id = env_params["runner_id"]
        return f"/apps/{runner_id}/{str(port)}/" if not Environment._is_local() else ""

    @staticmethod
    def get_app_url(port: int | str = None) -> str:
        """
        Returns the app URL for the environment.

        Args:
        port (int | str, optional): The port to use for the URL. Defaults to None.

        Returns:
        str: The app URL for the environment.
        """
        env_params = Environment.get_env_params()
        base_url = env_params["base_url"]
        runner_id = env_params["runner_id"]
        if not Environment._is_local():
            return f'{base_url}/apps/{runner_id}{"/" + str(port) if port else "/"}'
        else:
            return f'127.0.0.1{":" + str(port) if port else ":8501"}'

    @staticmethod
    def get_websocket_url(port: int | str = None) -> str:
        """
        Returns the websocket URL for the environment.

        Args:
        port (int | str, optional): The port to use for the URL. Defaults to None.

        Returns:
        str: The websocket URL for the environment.
        """
        env_params = Environment.get_env_params()
        base_url = env_params["base_url"]
        runner_id = env_params["runner_id"]
        if not Environment._is_local():
            return f'ws{base_url.replace("https", "")}/apps/{runner_id}{"/" + str(port) + "/" if port else "/"}'
        else:
            return f'ws://127.0.0.1{":" + str(port) + "/" if port else ":8501/"}'
