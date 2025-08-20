import streamlit as st
from pathlib import Path
import logging
import os
import sys

# Add src to path to enable absolute imports
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from smite_chatbot.models.chatbot import ChatBot
from smite_chatbot.models.openai_chatbot import OpenAIChatBot
from smite_chatbot.storage.hybrid_store import HybridDocumentStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_chatbot() -> ChatBot:
    """Initialize the chatbot with enhanced vector database"""
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("🔐 OpenAI API key not found! Please set OPENAI_API_KEY environment variable.")
        st.stop()
    
    # Initialize components
    try:
        # Use the enhanced HybridDocumentStore
        storage_dir = Path("storage")
        if not storage_dir.exists():
            st.error("❌ Storage directory not found! Please run data population first.")
            st.stop()
        
        hybrid_store = HybridDocumentStore(storage_dir)
        
        # Initialize OpenAI chatbot with OpenAI-specific config
        openai_config = {
            "temperature": st.session_state.get("temperature", 0.7),
            "max_tokens": st.session_state.get("max_tokens", 512),
        }
        
        openai_llm = OpenAIChatBot(
            model_name=st.session_state.get("model_name", "gpt-4o-mini"),
            api_key=api_key
        )
        openai_llm.update_config(**openai_config)
        
        # Create chatbot config (separate from OpenAI config)
        chatbot_config = {
            "max_conversation_history": 10
        }
        
        # Create chatbot with enhanced vector store
        chatbot = ChatBot(
            llm_model=openai_llm,
            config=chatbot_config,
            vector_store=hybrid_store,
            memory=False  # Default to no memory
        )
        
        return chatbot
        
    except Exception as e:
        st.error(f"❌ Error initializing chatbot: {str(e)}")
        logger.error(f"Chatbot initialization error: {e}")
        st.stop()

def display_message(role: str, content: str, sources: list = None):
    """Display a chat message with optional sources"""
    
    with st.chat_message(role):
        st.write(content)
        
        # Show sources if available
        if sources and len(sources) > 0:
            with st.expander(f"📚 Sources ({len(sources)})", expanded=False):
                for i, source in enumerate(sources, 1):
                    metadata = source.get('metadata', {})
                    name = metadata.get('name', 'Unknown')
                    doc_type = metadata.get('type', 'Unknown')
                    similarity = source.get('similarity', 0)
                    search_type = source.get('search_type', 'unknown')
                    
                    st.markdown(f"**{i}. {name}** ({doc_type})")
                    st.markdown(f"*Similarity: {similarity:.3f} | Search: {search_type}*")
                    
                    # Show content preview
                    content_preview = source['content'][:300]
                    if len(source['content']) > 300:
                        content_preview += "..."
                    st.markdown(f"> {content_preview}")
                    st.markdown("---")

def main():
    """Main Streamlit app"""
    
    st.set_page_config(
        page_title="SMITE 2 Chatbot",
        page_icon="⚔️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("⚔️ SMITE 2 Chatbot")
    st.markdown("*Ask me anything about SMITE 2 gods, items, abilities, and patches!*")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "chatbot" not in st.session_state:
        with st.spinner("🔄 Initializing chatbot with enhanced vector database..."):
            st.session_state.chatbot = initialize_chatbot()
        st.success("✅ Chatbot ready!")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Model configuration
        model_name = st.selectbox(
            "Model",
            ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            index=0
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Higher values make responses more creative"
        )
        
        max_tokens = st.slider(
            "Max Tokens",
            min_value=100,
            max_value=1000,
            value=512,
            step=50,
            help="Maximum length of response"
        )
        
        # Search configuration
        st.subheader("🔍 Search Settings")
        
        search_mode = st.selectbox(
            "Search Mode",
            ["hybrid", "semantic", "structured"],
            index=0,
            help="Hybrid combines both semantic and structured search"
        )
        
        n_results = st.slider(
            "Sources per Query",
            min_value=1,
            max_value=10,
            value=3,
            help="Number of sources to retrieve for each query"
        )
        
        use_rag = st.checkbox("Enable RAG", value=True, help="Use vector database for context")
        
        use_memory = st.checkbox("Enable Memory", value=False, help="Remember conversation history")
        
        # Update session state if settings changed
        if (st.session_state.get("model_name") != model_name or
            st.session_state.get("temperature") != temperature or
            st.session_state.get("max_tokens") != max_tokens or
            st.session_state.get("use_memory") != use_memory):
            
            st.session_state.model_name = model_name
            st.session_state.temperature = temperature  
            st.session_state.max_tokens = max_tokens
            st.session_state.use_memory = use_memory
            
            # Update chatbot configuration
            if hasattr(st.session_state, "chatbot"):
                st.session_state.chatbot.llm.update_config(
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                # Update memory setting
                st.session_state.chatbot.memory_enabled = use_memory
        
        # Database stats
        if hasattr(st.session_state, "chatbot"):
            with st.expander("📊 Database Stats"):
                try:
                    stats = st.session_state.chatbot.vector_store.get_stats()
                    db_stats = stats.get('database', {})
                    vector_stats = stats.get('vector_store', {})
                    
                    st.metric("Total Documents", db_stats.get('total_documents', 0))
                    st.metric("God Documents", db_stats.get('by_type', {}).get('god', 0))
                    st.metric("Ability Documents", db_stats.get('by_type', {}).get('ability', 0))
                    st.metric("Item Documents", db_stats.get('by_type', {}).get('item', 0))
                    st.metric("God Changes", db_stats.get('by_type', {}).get('god_change', 0))
                    st.metric("Patch Documents", db_stats.get('by_type', {}).get('patch', 0))
                    st.metric("Vector Documents", vector_stats.get('total_documents', 0))
                except Exception as e:
                    st.error(f"Error loading stats: {e}")
        
        # Clear conversation
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            if hasattr(st.session_state, "chatbot"):
                st.session_state.chatbot.conversation_history.clear()
            st.rerun()
        
        # Memory status indicator
        if hasattr(st.session_state, "chatbot") and st.session_state.chatbot.memory_enabled:
            st.info("💭 Memory enabled - conversation history will be remembered")
        else:
            st.info("🔄 Memory disabled - each message is independent")
    
    # Display conversation history
    for message in st.session_state.messages:
        display_message(
            message["role"], 
            message["content"], 
            message.get("sources")
        )
    
    # Chat input
    if prompt := st.chat_input("Ask about SMITE 2..."):
        
        # Add user message to conversation
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt
        })
        display_message("user", prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    # Generate response using chatbot
                    response = st.session_state.chatbot.chat(
                        message=prompt,
                        use_rag=use_rag,
                        search_mode=search_mode,
                        n_results=n_results,
                        system_prompt = """You are a SMITE 2 expert. Use only the provided context about gods, abilities, items, and patches. 
If the context lacks an answer, say so and offer general guidance. Be concise and exact.

Abilities data format in context:
- Sections appear as: Passive, Basic Attack, 1st Ability, 2nd Ability, 3rd Ability, Ultimate.
- Common fields: Notes, Cost, Cooldown, Range (meters), Radius (meters), Damage/Base Damage, Bonus Damage, Damage Per Shot, Scaling, Duration, Slow/Cripple values, Chance/Drop Chance, Buff Duration, Attack Speed.
- Ignore any “Ability Video” lines.

Interpretation rules:
- Per-level arrays map left→right to ranks 1–5. Example: “35/55/75/95/115” = ranks 1..5. Each ability has 5 ranks.
- If a value is “0/10/10/10/10/10%”, treat rank 1 as 0 and ranks 2–5 as given.
- “Scaling” percentages multiply the named stat(s). Example: “100% Strength + 20% Intelligence” = 1.00*Strength + 0.20*Intelligence.
- “Damage Per Shot” entries describe intra-ability sequencing (e.g., shot 1/2/3 of an ultimate), not ranks, unless the line itself has five rank values.
- Durations are seconds. Ranges and radii are meters.
- Toggle abilities consume resources per Basic Attack if stated.
- Mechanics in Notes (pierces, walls, haste, cripple, respawn ammo, arrow generation/pickups, cooldown reduction per pickup, etc.) are binding.

Answering rules:
- When asked for numbers at a rank, use the rank-specific base/bonus values plus listed scaling. Do not invent mitigation, items, or hidden modifiers.
- Show simple math when computing: Final = Base_at_rank + Σ(stat*scaling%).
- If rank or stats are missing, ask for them or state the dependency briefly.
- Quote only fields present in context. Do not infer unseen values.
- Use short tables for per-rank outputs when helpful.

Style:
- Be concise, factual, and unit-aware.
- If information is absent, say “Not in context.” and give high-level guidance."""
                    )
                    # Display response
                    st.write(response.content)
                    
                    # Display sources if available
                    if response.sources and len(response.sources) > 0:
                        with st.expander(f"📚 Sources ({len(response.sources)})", expanded=False):
                            for i, source in enumerate(response.sources, 1):
                                metadata = source.get('metadata', {})
                                name = metadata.get('name', 'Unknown')
                                doc_type = metadata.get('type', 'Unknown')
                                similarity = source.get('similarity', 0)
                                search_type = source.get('search_type', 'unknown')
                                
                                st.markdown(f"**{i}. {name}** ({doc_type})")
                                st.markdown(f"*Similarity: {similarity:.3f} | Search: {search_type}*")
                                
                                # Show content preview
                                content_preview = source['content'][:300]
                                if len(source['content']) > 300:
                                    content_preview += "..."
                                st.markdown(f"> {content_preview}")
                                st.markdown("---")
                    
                    # Add assistant response to conversation
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.content,
                        "sources": response.sources
                    })
                    
                except Exception as e:
                    error_msg = f"❌ Error generating response: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Response generation error: {e}")
                    
                    # Add error to conversation
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })

if __name__ == "__main__":
    main()