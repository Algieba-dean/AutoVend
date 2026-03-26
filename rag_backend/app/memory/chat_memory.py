"""
Chat memory management using LlamaIndex ChatMemoryBuffer.

Provides per-session conversation history with configurable token limits.
"""

import logging
from typing import Dict, List

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.memory import ChatMemoryBuffer

logger = logging.getLogger(__name__)

# Default token limit for memory buffer
DEFAULT_TOKEN_LIMIT = 3000


class ChatMemoryManager:
    """
    Manages per-session chat memory buffers.

    Each session gets its own ChatMemoryBuffer that maintains
    conversation history within a token limit.
    """

    def __init__(self, token_limit: int = DEFAULT_TOKEN_LIMIT):
        self._sessions: Dict[str, ChatMemoryBuffer] = {}
        self._token_limit = token_limit

    def get_or_create(self, session_id: str) -> ChatMemoryBuffer:
        """Get existing memory buffer or create a new one for the session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ChatMemoryBuffer.from_defaults(
                token_limit=self._token_limit,
            )
            logger.info(f"Created new memory buffer for session {session_id}")
        return self._sessions[session_id]

    def add_message(
        self, session_id: str, role: MessageRole, content: str
    ) -> None:
        """Add a message to the session's memory buffer."""
        memory = self.get_or_create(session_id)
        memory.put(ChatMessage(role=role, content=content))

    def add_user_message(self, session_id: str, content: str) -> None:
        """Convenience: add a user message."""
        self.add_message(session_id, MessageRole.USER, content)

    def add_assistant_message(self, session_id: str, content: str) -> None:
        """Convenience: add an assistant message."""
        self.add_message(session_id, MessageRole.ASSISTANT, content)

    def get_history(self, session_id: str) -> List[ChatMessage]:
        """Get the chat history for a session."""
        memory = self.get_or_create(session_id)
        return memory.get_all()

    def get_history_as_text(self, session_id: str) -> str:
        """Get the chat history formatted as text for prompt injection."""
        history = self.get_history(session_id)
        lines = []
        for msg in history:
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        """Clear a session's memory buffer."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Cleared memory for session {session_id}")

    def has_session(self, session_id: str) -> bool:
        """Check if a session exists."""
        return session_id in self._sessions

    @property
    def active_sessions(self) -> List[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())
