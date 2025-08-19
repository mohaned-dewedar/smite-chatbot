#!/usr/bin/env python3
"""
Example usage of the ChatBot system with different providers and RAG integration.
"""

import os
from src.smite_chatbot.models import OpenAIChatBot
from src.smite_chatbot.storage.vector_store import VectorStore


def basic_openai_example():
    """Basic OpenAI ChatBot usage example."""
    print("=== Basic OpenAI ChatBot Example ===")
    
    # Initialize OpenAI ChatBot
    # Make sure to set your OPENAI_API_KEY environment variable
    try:
        chatbot = OpenAIChatBot(
            model_name="gpt-4o-mini",
            config={
                "temperature": 0.7,
                "max_tokens": 200
            }
        )
        
        # Simple conversation
        response = chatbot.chat("Hello! Can you explain what SMITE is?", use_rag=False)
        print(f"User: Hello! Can you explain what SMITE is?")
        print(f"Assistant: {response.content}")
        print(f"Usage: {response.usage}")
        
        # Follow-up question
        response = chatbot.chat("What are the main roles in SMITE?", use_rag=False)
        print(f"\nUser: What are the main roles in SMITE?")
        print(f"Assistant: {response.content}")
        
        # Show conversation history
        print(f"\nConversation history length: {len(chatbot.get_history())}")
        
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your OPENAI_API_KEY environment variable to run this example.")


def rag_enabled_example():
    """Example with RAG integration."""
    print("\n=== RAG-Enabled ChatBot Example ===")
    
    try:
        chatbot = OpenAIChatBot(model_name="gpt-4o-mini")
        
        # Note: This is a mock example - in real usage you would load your actual vector store
        # from your SMITE data that was scraped and processed
        print("In a real scenario, you would:")
        print("1. Load your vector store with SMITE game data")
        print("2. Set it on the chatbot with: chatbot.set_vector_store(vector_store)")
        print("3. Then chat with RAG enabled:")
        
        # Mock showing what the interaction would look like
        print("\nUser: Tell me about Anubis's abilities")
        print("Assistant: [Would retrieve relevant context about Anubis from vector store]")
        print("Based on the game data, Anubis is a magical damage god with abilities like...")
        
    except ValueError as e:
        print(f"Error: {e}")


def configuration_example():
    """Example showing configuration options."""
    print("\n=== Configuration Example ===")
    
    try:
        chatbot = OpenAIChatBot(
            model_name="gpt-4o-mini",
            config={
                "temperature": 0.3,  # More focused responses
                "max_tokens": 150,   # Shorter responses
                "max_conversation_history": 6  # Keep only last 3 exchanges
            }
        )
        
        # Update configuration at runtime
        chatbot.set_temperature(0.8)
        chatbot.set_max_tokens(100)
        
        print("ChatBot configured with:")
        print(f"- Model: {chatbot.model_name}")
        print(f"- Temperature: {chatbot.config['temperature']}")
        print(f"- Max tokens: {chatbot.config['max_tokens']}")
        print(f"- History limit: {chatbot.config['max_conversation_history']}")
        
    except ValueError as e:
        print(f"Error: {e}")


def conversation_management_example():
    """Example showing conversation management features."""
    print("\n=== Conversation Management Example ===")
    
    try:
        chatbot = OpenAIChatBot(model_name="gpt-4o-mini")
        
        # Have a conversation
        chatbot.chat("Hello", use_rag=False)
        chatbot.chat("What is SMITE?", use_rag=False)
        
        print(f"Conversation length: {len(chatbot.get_history())}")
        
        # Save conversation
        chatbot.save_conversation("/tmp/smite_chat_example.json")
        print("Conversation saved to /tmp/smite_chat_example.json")
        
        # Clear and load
        chatbot.clear_history()
        print(f"After clear: {len(chatbot.get_history())}")
        
        chatbot.load_conversation("/tmp/smite_chat_example.json")
        print(f"After load: {len(chatbot.get_history())}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("SMITE ChatBot Examples")
    print("=" * 50)
    
    basic_openai_example()
    rag_enabled_example()
    configuration_example()
    conversation_management_example()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nNext steps:")
    print("1. Set up your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
    print("2. Run the scraper to collect SMITE data: uv run smite-scraper")
    print("3. Process and populate vector store with your data")
    print("4. Integrate the ChatBot into your Streamlit app")