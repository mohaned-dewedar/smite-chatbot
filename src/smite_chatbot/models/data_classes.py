from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "user", "assistant", "system"
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatResponse:
    content: str
    usage: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None

@dataclass
class Tokens:
    prompt: int
    completion: int
    total: int