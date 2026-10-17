# D:\FYP\FORGE-1\backend\services\gemini_service.py
import logging
from typing import List, Any
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.core.config import settings

logger = logging.getLogger("forge.services.gemini")


class GeminiService:
    def __init__(self):
        self.primary_llm = ChatGoogleGenerativeAI(
            model=settings.CHAT_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=settings.MODEL_TEMPERATURE,
            max_retries=1
        )
        self.fallback_llm = ChatGoogleGenerativeAI(
            model=settings.FALLBACK_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=settings.MODEL_TEMPERATURE,
            max_retries=1
        )
        # Setup fallback chain
        self.llm = self.primary_llm.with_fallbacks([self.fallback_llm])
        logger.info(
            f"GeminiService initialized with primary: {settings.CHAT_MODEL}, fallback: {settings.FALLBACK_MODEL}"
        )

    def generate_response(self, messages: List[BaseMessage]) -> str:
        """
        Invokes Gemini with provided messages and returns clean extracted text.
        """
        response = self.llm.invoke(messages)
        return self._extract_content(response.content)

    @staticmethod
    def _extract_content(content: Any) -> str:
        """
        Normalizes LangChain Gemini AIMessage content across formats.
        """
        if isinstance(content, str):
            return content.strip()
        elif isinstance(content, list):
            text_blocks = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    text_blocks.append(block["text"])
                elif isinstance(block, str):
                    text_blocks.append(block)
                else:
                    text_blocks.append(str(block))
            return "".join(text_blocks).strip()
        return str(content).strip()


# Singleton instance
gemini_service = GeminiService()
