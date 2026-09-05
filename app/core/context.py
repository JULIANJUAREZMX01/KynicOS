"""Agent execution context and state management"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Context for agent execution."""

    session_id: str
    user_id: str
    channel: str  # "telegram", "whatsapp", "mcp", etc.
    messages: List[Message] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    files: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def room_number(self) -> Optional[str]:
        """Return the guest room from durable context state, if present."""
        return self.state.get("room_number")

    @room_number.setter
    def room_number(self, value: Optional[str]) -> None:
        if value is None:
            self.state.pop("room_number", None)
        else:
            self.state["room_number"] = value

    @property
    def guest_name(self) -> Optional[str]:
        """Return the guest name from durable context state, if present."""
        return self.state.get("guest_name")

    @guest_name.setter
    def guest_name(self, value: Optional[str]) -> None:
        if value is None:
            self.state.pop("guest_name", None)
        else:
            self.state["guest_name"] = value

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Add a message to the context, preserving optional metadata/timestamp."""
        msg = Message(
            role=role,
            content=content,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata or {},
        )
        self.messages.append(msg)

    def add_file(self, path: str) -> None:
        """Register a local attachment made available to the agent."""
        if path and path not in self.files:
            self.files.append(path)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "channel": self.channel,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in self.messages
            ],
            "state": self.state,
            "files": self.files,
            "started_at": self.started_at.isoformat(),
        }
