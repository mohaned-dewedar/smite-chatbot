from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)


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


class ChatBot(ABC):
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
    def _generate_response(self, messages: List[ChatMessage]) -> ChatResponse:
        """Generate response from the underlying LLM provider."""
        pass
    
    @abstractmethod
    def _prepare_messages(self, messages: List[ChatMessage]) -> Any:
        """Convert ChatMessage objects to provider-specific format."""
        pass
    
    def set_vector_store(self, vector_store):
        """Set the vector store for RAG capabilities."""
        self.vector_store = vector_store
        
    def retrieve_context(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant context from vector store."""
        if not self.vector_store:
            return []
            
        try:
            results = self.vector_store.similarity_search(query, k=k)
            return [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []
    
    def _build_rag_prompt(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Build a prompt that includes retrieved context."""
        if not context:
            return query
            
        context_text = "\n\n".join([
            f"Source: {ctx.get('metadata', {}).get('source', 'Unknown')}\n{ctx['content']}"
            for ctx in context
        ])
        
        return f"""Answer the following question using the provided context. If the context doesn't contain relevant information, say so clearly.

Context:
{context_text}

Question: {query}

Answer:"""
    
    def chat(self, message: str, use_rag: bool = True, system_prompt: Optional[str] = None) -> ChatResponse:
        """
        Main chat method that handles RAG integration and conversation flow.
        
        Args:
            message: User input message
            use_rag: Whether to use RAG for context retrieval
            system_prompt: Optional system prompt to set context
            
        Returns:
            ChatResponse with the assistant's reply
        """
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
            
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Handle RAG if enabled
        if use_rag and self.vector_store:
            context = self.retrieve_context(message)
            if context:
                rag_message = self._build_rag_prompt(message, context)
                user_msg = ChatMessage(role="user", content=rag_message)
            else:
                user_msg = ChatMessage(role="user", content=message)
                context = []
        else:
            user_msg = ChatMessage(role="user", content=message)
            context = []
            
        messages.append(user_msg)
        
        # Generate response
        response = self._generate_response(messages)
        
        # Add sources from RAG if available
        if context:
            response.sources = context
            
        # Update conversation history
        self.conversation_history.append(ChatMessage(role="user", content=message))
        self.conversation_history.append(ChatMessage(role="assistant", content=response.content))
        
        # Keep conversation history manageable
        max_history = self.config.get("max_conversation_history", 10)
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
            
        return response
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        
    def get_history(self) -> List[ChatMessage]:
        """Get current conversation history."""
        return self.conversation_history.copy()
        
    def save_conversation(self, filepath: str):
        """Save conversation history to file."""
        history_data = [
            {"role": msg.role, "content": msg.content, "metadata": msg.metadata}
            for msg in self.conversation_history
        ]
        with open(filepath, 'w') as f:
            json.dump(history_data, f, indent=2)
            
    def load_conversation(self, filepath: str):
        """Load conversation history from file."""
        with open(filepath, 'r') as f:
            history_data = json.load(f)
            
        self.conversation_history = [
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata")
            )
            for msg in history_data
        ]