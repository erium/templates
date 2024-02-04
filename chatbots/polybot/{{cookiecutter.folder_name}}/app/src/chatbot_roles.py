from enum import Enum


class ChatbotRoles(Enum):
    """
    Enum class for chatbot roles "system", "assistant" and "user".
    """

    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
