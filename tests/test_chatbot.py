import pytest
from unittest.mock import Mock, patch
import os
from src.smite_chatbot.models.chatbot import ChatBot, ChatMessage, ChatResponse
from src.smite_chatbot.models.openai_chatbot import OpenAIChatBot


class MockChatBot(ChatBot):
    """Mock implementation for testing base class functionality."""
    
    def _prepare_messages(self, messages):
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def _generate_response(self, messages):
        return ChatResponse(
            content="Mock response",
            model="mock-model",
            usage={"total_tokens": 100}
        )


def test_chatbot_base_functionality():
    """Test basic ChatBot functionality."""
    chatbot = MockChatBot("mock-model")
    
    # Test basic chat without RAG
    response = chatbot.chat("Hello", use_rag=False)
    assert response.content == "Mock response"
    assert len(chatbot.conversation_history) == 2  # user + assistant
    
    # Test conversation history
    history = chatbot.get_history()
    assert history[0].role == "user"
    assert history[0].content == "Hello"
    assert history[1].role == "assistant"
    assert history[1].content == "Mock response"
    
    # Test clear history
    chatbot.clear_history()
    assert len(chatbot.conversation_history) == 0


def test_chatbot_with_vector_store():
    """Test ChatBot with mock vector store."""
    chatbot = MockChatBot("mock-model")
    
    # Mock vector store
    mock_vector_store = Mock()
    mock_doc = Mock()
    mock_doc.page_content = "Mocked context about SMITE"
    mock_doc.metadata = {"source": "wiki"}
    mock_vector_store.similarity_search.return_value = [mock_doc]
    
    chatbot.set_vector_store(mock_vector_store)
    
    # Test RAG functionality
    response = chatbot.chat("Tell me about SMITE", use_rag=True)
    
    # Verify vector store was called
    mock_vector_store.similarity_search.assert_called_once()
    assert response.content == "Mock response"


@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
def test_openai_chatbot_initialization():
    """Test OpenAI ChatBot initialization."""
    with patch('src.smite_chatbot.models.openai_chatbot.OpenAI') as mock_openai:
        chatbot = OpenAIChatBot(model_name="gpt-3.5-turbo")
        assert chatbot.model_name == "gpt-3.5-turbo"
        assert chatbot.api_key == "test-key"
        mock_openai.assert_called_once_with(api_key="test-key")


def test_openai_chatbot_no_api_key():
    """Test OpenAI ChatBot raises error without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            OpenAIChatBot()


@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
def test_openai_chatbot_message_preparation():
    """Test message format conversion for OpenAI."""
    with patch('src.smite_chatbot.models.openai_chatbot.OpenAI'):
        chatbot = OpenAIChatBot()
        
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!")
        ]
        
        prepared = chatbot._prepare_messages(messages)
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        assert prepared == expected


@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
def test_openai_chatbot_config_update():
    """Test configuration updates."""
    with patch('src.smite_chatbot.models.openai_chatbot.OpenAI'):
        chatbot = OpenAIChatBot()
        
        # Test temperature setting
        chatbot.set_temperature(0.5)
        assert chatbot.config["temperature"] == 0.5
        
        # Test max tokens setting
        chatbot.set_max_tokens(500)
        assert chatbot.config["max_tokens"] == 500
        
        # Test invalid temperature
        with pytest.raises(ValueError):
            chatbot.set_temperature(-1)
            
        # Test invalid max tokens
        with pytest.raises(ValueError):
            chatbot.set_max_tokens(0)