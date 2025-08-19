from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
from .data_classes import ChatMessage, ChatResponse, Tokens

logger = logging.getLogger(__name__)




class LLMWrapper(ABC):
    """
    Abstract base class for chatbots that can work with different LLM providers.
    Supports RAG integration with vector search capabilities.
    """
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.config = config or {}
        self.conversation_history: List[ChatMessage] = []
        self.vector_store = None
        
    @abstractmethod
    def generate(self, messages: List[ChatMessage]) -> ChatResponse:
        """Generate response from the underlying LLM provider."""
        pass