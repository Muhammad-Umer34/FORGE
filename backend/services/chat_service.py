# D:\FYP\FORGE-1\backend\services\chat_service.py
import uuid
import logging
from typing import Dict, List, Optional
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

from backend.core.prompts import SYSTEM_INSTRUCTION
from backend.models.chat import ChatIntent, ChatResponse
from backend.services.gemini_service import gemini_service

logger = logging.getLogger("forge.services.chat")


class ChatService:
    def __init__(self, max_history_turns: int = 10):
        self.max_history_turns = max_history_turns
        # In-memory session store: maps session_id -> list of BaseMessage
        self.session_histories: Dict[str, List[BaseMessage]] = {}

    def get_or_create_session(self, session_id: Optional[str]) -> str:
        active_id = session_id or f"session_{uuid.uuid4().hex[:10]}"
        if active_id not in self.session_histories:
            self.session_histories[active_id] = []
        return active_id

    def reset_session(self, session_id: str) -> bool:
        if session_id in self.session_histories:
            self.session_histories[session_id] = []
            logger.info(f"Session memory cleared for {session_id}")
            return True
        return False

    def detect_intent(self, text: str) -> ChatIntent:
        cleaned = text.lower().strip()
        greetings = [
            "hi", "hello", "hey", "salam", "assalam", "assalam o alaikum",
            "good morning", "good evening", "howdy", "sup"
        ]

        # Greeting check
        if any(cleaned.startswith(g) or cleaned == g for g in greetings) and len(cleaned.split()) <= 4:
            return ChatIntent.GREETING

        # Obvious out-of-scope check
        out_of_scope_keywords = [
            "weather", "president", "math", "capital of", "who is the prime minister",
            "system prompt", "who are you", "tell me a joke", "quantum physics", "calculus"
        ]
        if any(keyword in cleaned for keyword in out_of_scope_keywords) and not any(
            w in cleaned for w in ["website", "page", "app", "build", "design", "portfolio", "store", "shop"]
        ):
            return ChatIntent.OUT_OF_SCOPE

        # Website build intent
        return ChatIntent.WEBSITE_BUILD

    def process_message(self, user_message: str, session_id: Optional[str] = None) -> ChatResponse:
        active_session_id = self.get_or_create_session(session_id)
        history = self.session_histories[active_session_id]

        # Extract sliding history (up to max_history_turns)
        recent_history = history[-self.max_history_turns:] if len(history) > self.max_history_turns else history

        # Assemble full conversation messages
        prompt_messages: List[BaseMessage] = [
            SystemMessage(content=SYSTEM_INSTRUCTION),
            *recent_history,
            HumanMessage(content=user_message)
        ]

        try:
            ai_reply = gemini_service.generate_response(prompt_messages)

            # Record turn in session memory
            history.append(HumanMessage(content=user_message))
            history.append(AIMessage(content=ai_reply))

            detected_intent = self.detect_intent(user_message)
            turn_count = len(history) // 2

            return ChatResponse(
                session_id=active_session_id,
                reply=ai_reply,
                intent=detected_intent,
                turn_count=turn_count
            )

        except Exception as e:
            logger.error(f"Error processing chat message: {e}", exc_info=True)
            fallback_reply = (
                "I am FORGE, your AI website builder. I encountered a temporary connection issue. "
                "Please tell me what website you'd like to build!"
            )
            return ChatResponse(
                session_id=active_session_id,
                reply=fallback_reply,
                intent=ChatIntent.GREETING,
                turn_count=len(history) // 2
            )


# Singleton instance
chat_service = ChatService()
