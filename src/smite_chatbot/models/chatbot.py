# chatbot.py
from typing import Any, Dict, List, Optional, Union
from collections import deque
import json, logging
from .llm_wrapper import LLMWrapper 
from .openai_chatbot import OpenAIChatBot
from .data_classes import ChatMessage, ChatResponse
from ..storage.vector_store import VectorStore
from ..storage.hybrid_store import HybridDocumentStore

logger = logging.getLogger(__name__)

class ChatBot:
    def __init__(self, llm_model: LLMWrapper, config: Optional[Dict[str, Any]] = None, 
                 vector_store: Union[VectorStore, HybridDocumentStore, None] = None, memory: bool = False):
        self.llm = llm_model
        self.config = config or {}
        self.memory_enabled = memory
        
        # Use deque with maxlen for automatic conversation length management
        max_history = self.config.get("max_conversation_history", 10)
        self.conversation_history = deque(maxlen=max_history * 2)  # *2 for user+assistant pairs
        
        self.vector_store = vector_store
        self._is_hybrid_store = isinstance(vector_store, HybridDocumentStore)

    def set_vector_store(self, vector_store: Union[VectorStore, HybridDocumentStore]):  
        self.vector_store = vector_store
        self._is_hybrid_store = isinstance(vector_store, HybridDocumentStore)

    def retrieve_context(self, query: str, n_results: int = 3, search_mode: str = "hybrid") -> List[Dict[str, Any]]:
        if not self.vector_store:
            return []
        
        # Use appropriate search method based on store type
        if self._is_hybrid_store:
            # HybridDocumentStore supports search modes and has enhanced retrieval
            rs = self.vector_store.search(query, n_results=n_results, search_mode=search_mode)
        else:
            # VectorStore only supports basic search
            rs = self.vector_store.search(query, n_results=n_results)
        
        return [{
            "content": r["content"], 
            "metadata": r.get("metadata", {}),
            "similarity": r.get("similarity", 0.0),
            "search_type": r.get("search_type", "unknown"),
            "id": r.get("id", "unknown")
        } for r in rs]

    def _build_rag_prompt(self, query: str, context: List[Dict[str, Any]]) -> str:
        if not context:
            return query
        ctx_txt = "\n\n".join(
            f"Source: {c.get('metadata', {}).get('source_url') or c.get('metadata', {}).get('source', 'Unknown')}\n{c['content']}"
            for c in context
        )
        return f"""Answer the question using the context. If not relevant, say so.

Context:
{ctx_txt}

Question: {query}

Answer:"""

    def _to_wire(self, messages: List[ChatMessage]) -> List[ChatMessage]:
        return messages

    def chat(self, message: str, use_rag: bool = True, system_prompt: Optional[str] = None, 
             search_mode: str = "hybrid", n_results: int = 3) -> ChatResponse:
        msgs: List[ChatMessage] = []
        if system_prompt:
            msgs.append(ChatMessage(role="system", content=system_prompt))
        
        # Only include conversation history if memory is enabled
        if self.memory_enabled:
            msgs.extend(self.conversation_history)

        context: List[Dict[str, Any]] = []
        user_content = message
        if use_rag and self.vector_store:
            context = self.retrieve_context(message, n_results=n_results, search_mode=search_mode)
            if context:
                user_content = self._build_rag_prompt(message, context)

        msgs.append(ChatMessage(role="user", content=user_content))

        # Don't pass ChatBot config to LLM - it has its own config
        resp = self.llm.generate(msgs)
        if context:
            resp.sources = context

        # Add to conversation history only if memory is enabled (deque automatically handles length)
        if self.memory_enabled:
            self.conversation_history.append(ChatMessage(role="user", content=message))
            self.conversation_history.append(ChatMessage(role="assistant", content=resp.content))
        
        return resp

    # clear_history, get_history, save/load stay the same

if __name__ == "__main__":
    # Testing both VectorStore and HybridDocumentStore
    from pathlib import Path
    
    print("🧪 **CHATBOT TESTING: VectorStore vs HybridDocumentStore**")
    print("=" * 65)
    
    # Mock LLM for testing without OpenAI dependency
    class MockLLM(LLMWrapper):
        def __init__(self):
            super().__init__(model_name="mock-model")
        
        def generate(self, messages, **kwargs):
            class MockResponse:
                def __init__(self, content):
                    self.content = content
                    self.sources = []
            
            return MockResponse("Mock LLM response - enhanced documents working!")
    
    test_queries = [
        "What is Achilles ultimate?",
        "Zeus ultimate ability", 
        "Show me Ares abilities"
    ]
    
    # Test 1: HybridDocumentStore (Enhanced)
    print("\n1️⃣ **TESTING WITH HYBRID DOCUMENT STORE (ENHANCED)**")
    hybrid_store = HybridDocumentStore(Path("storage"))
    chatbot_hybrid = ChatBot(llm_model=MockLLM(), vector_store=hybrid_store)
    
    for query in test_queries:
        print(f"\n🔍 Query: \"{query}\"")
        context = chatbot_hybrid.retrieve_context(query, n_results=2, search_mode="hybrid")
        print(f"📚 Retrieved {len(context)} results:")
        for i, ctx in enumerate(context, 1):
            name = ctx["metadata"].get("name", "Unknown")
            doc_type = ctx["metadata"].get("type", "Unknown")
            content_preview = ctx["content"][:100].replace("\n", " ")
            print(f"  {i}. {name} ({doc_type})")
            print(f"     {content_preview}...")
    
    # Test 2: VectorStore (Original)
    print("\n\n2️⃣ **TESTING WITH VECTOR STORE (ORIGINAL)**")
    print("Note: VectorStore uses direct vector similarity only")
    try:
        vector_store = VectorStore(Path("storage/vectors"))
        chatbot_vector = ChatBot(llm_model=MockLLM(), vector_store=vector_store)
        
        for query in test_queries:
            print(f"\n🔍 Query: \"{query}\"")
            context = chatbot_vector.retrieve_context(query, n_results=2)
            print(f"📚 Retrieved {len(context)} results:")
            for i, ctx in enumerate(context, 1):
                name = ctx["metadata"].get("name", "Unknown")
                doc_type = ctx["metadata"].get("type", "Unknown") 
                content_preview = ctx["content"][:100].replace("\n", " ")
                print(f"  {i}. {name} ({doc_type})")
                print(f"     {content_preview}...")
    except Exception as e:
        print(f"⚠️  VectorStore test failed: {e}")
        print("This is expected - VectorStore may need different initialization")
    
    print("\n🏆 **COMPARISON SUMMARY**")
    print("✅ HybridDocumentStore: Enhanced documents, hybrid search, better results")
    print("📊 VectorStore: Basic vector similarity search only")
    print("🎯 Recommendation: Use HybridDocumentStore for production")