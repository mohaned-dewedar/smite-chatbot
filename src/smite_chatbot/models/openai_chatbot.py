from typing import Any, Dict, List, Optional
import os
from openai import OpenAI
import logging

from .chatbot import ChatBot, ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


class OpenAIChatBot(ChatBot):
    """
    OpenAI implementation of the ChatBot base class.
    Supports GPT models via OpenAI API.
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(model_name, config)
        
        # Initialize OpenAI client
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
            
        self.client = OpenAI(api_key=self.api_key)
        
        # Default configuration
        self.default_config = {
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }
        self.config = {**self.default_config, **self.config}
        
    def _prepare_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Convert ChatMessage objects to OpenAI format."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
    
    def _generate_response(self, messages: List[ChatMessage]) -> ChatResponse:
        """Generate response using OpenAI API."""
        try:
            openai_messages = self._prepare_messages(messages)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                temperature=self.config.get("temperature", 0.7),
                max_tokens=self.config.get("max_tokens", 1000),
                top_p=self.config.get("top_p", 1.0),
                frequency_penalty=self.config.get("frequency_penalty", 0.0),
                presence_penalty=self.config.get("presence_penalty", 0.0),
            )
            
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
            return ChatResponse(
                content=content,
                usage=usage,
                model=response.model
            )
            
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return ChatResponse(
                content=f"I apologize, but I encountered an error while processing your request: {str(e)}",
                usage=None,
                model=self.model_name
            )
    
    def update_config(self, **kwargs):
        """Update configuration parameters."""
        self.config.update(kwargs)
        
    def set_temperature(self, temperature: float):
        """Set temperature for response generation."""
        if not 0 <= temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        self.config["temperature"] = temperature
        
    def set_max_tokens(self, max_tokens: int):
        """Set maximum tokens for response generation."""
        if max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        self.config["max_tokens"] = max_tokens