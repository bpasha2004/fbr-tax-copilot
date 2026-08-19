from abc import ABC, abstractmethod


class AIProvider(ABC):
    """
    Abstract interface for all AI providers.
    Swap Ollama for Gemini by changing one config value.
    """

    @abstractmethod
    async def explain_tax_result(
        self,
        audit_record: dict,
        user_question: str,
        language: str = "english",
    ) -> dict:
        """
        Takes a verified audit record from the Rules Engine
        and explains it in plain language.
        Never calculates — only explains.
        """
