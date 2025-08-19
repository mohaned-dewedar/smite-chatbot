from typing import Any, Dict, List, Optional
import os
from openai import OpenAI
import logging
from abc import  abstractmethod
from .llm_wrapper import LLMWrapper
from .data_classes import Tokens ,ChatMessage, ChatResponse
logger = logging.getLogger(__name__)


class OpenAIChatBot(LLMWrapper):
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
            "max_tokens": 200,
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
    def generate(self, messages: List[ChatMessage], **cfg: Any) -> ChatResponse:
        cfg = {**self.config, **cfg}
        messages_dict = self._prepare_messages(messages)
        try:
            r = self.client.chat.completions.create(model=self.model_name, messages=messages_dict, **cfg)
            choice = r.choices[0]

            return ChatResponse(
                content=choice.message.content or "",
                usage={
                    "prompt_tokens": r.usage.prompt_tokens,
                    "completion_tokens": r.usage.completion_tokens,
                    "total_tokens": r.usage.total_tokens,
                },
                model=r.model,
            )
            
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return ChatResponse(
                content=f"I apologize, but I encountered an error while processing your request: {str(e)}",
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

if __name__ == "__main__":
    # Example usage
    try:
        chatbot = OpenAIChatBot(model_name="gpt-4o-mini")
        response = chatbot.generate([
            ChatMessage(role="user", content="What is the capital of France?")
        ])
        print(response.content)
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set OPENAI_API_KEY environment variable")