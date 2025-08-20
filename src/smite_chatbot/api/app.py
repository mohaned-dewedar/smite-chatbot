import time
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    ChatRequest, ChatResponse, HealthResponse, StatsResponse, 
    ErrorResponse, Source, SearchMode
)
from ..models.chatbot import ChatBot
from ..models.openai_chatbot import OpenAIChatBot
from ..storage.hybrid_store import HybridDocumentStore

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
app_state = {
    "chatbot": None,
    "start_time": None,
    "initialized": False
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting SMITE 2 Chatbot API...")
    app_state["start_time"] = time.time()
    
    try:
        # Initialize chatbot
        await initialize_chatbot()
        app_state["initialized"] = True
        logger.info("✅ SMITE 2 Chatbot API ready!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chatbot: {e}")
        app_state["initialized"] = False
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down SMITE 2 Chatbot API...")

# Create FastAPI app
app = FastAPI(
    title="SMITE 2 Chatbot API",
    description="API for SMITE 2 game knowledge with RAG-powered responses",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def initialize_chatbot():
    """Initialize the chatbot components"""
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    # Initialize storage
    storage_dir = Path("storage")
    if not storage_dir.exists():
        raise FileNotFoundError("Storage directory not found. Run data population first.")
    
    hybrid_store = HybridDocumentStore(storage_dir)
    
    # Initialize OpenAI chatbot
    openai_llm = OpenAIChatBot(
        model_name="gpt-4o-mini",
        api_key=api_key
    )
    
    # Configure with defaults
    openai_llm.update_config(
        temperature=0.7,
        max_tokens=512
    )
    
    # Create chatbot
    chatbot_config = {
        "max_conversation_history": 10
    }
    
    chatbot = ChatBot(
        llm_model=openai_llm,
        config=chatbot_config,
        vector_store=hybrid_store,
        memory=False  # Default to no memory for API
    )
    
    app_state["chatbot"] = chatbot
    logger.info("🤖 Chatbot initialized successfully")

def get_chatbot() -> ChatBot:
    """Dependency to get initialized chatbot"""
    if not app_state["initialized"] or app_state["chatbot"] is None:
        raise HTTPException(
            status_code=503,
            detail="Chatbot not initialized. Check service health."
        )
    return app_state["chatbot"]

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).dict()
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        chatbot = app_state.get("chatbot")
        database_connected = False
        vector_store_connected = False
        
        if chatbot and chatbot.vector_store:
            try:
                stats = chatbot.vector_store.get_stats()
                database_connected = stats.get("database", {}).get("total_documents", 0) > 0
                vector_store_connected = stats.get("vector_store", {}).get("total_documents", 0) > 0
            except Exception as e:
                logger.warning(f"Error checking store status: {e}")
        
        return HealthResponse(
            status="healthy" if app_state["initialized"] else "initializing",
            version="1.0.0",
            database_connected=database_connected,
            vector_store_connected=vector_store_connected
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/stats", response_model=StatsResponse)
async def get_stats(chatbot: ChatBot = Depends(get_chatbot)):
    """Get database and service statistics"""
    try:
        stats = chatbot.vector_store.get_stats()
        db_stats = stats.get("database", {})
        vector_stats = stats.get("vector_store", {})
        
        uptime = time.time() - app_state["start_time"] if app_state["start_time"] else 0
        
        return StatsResponse(
            total_documents=db_stats.get("total_documents", 0),
            documents_by_type=db_stats.get("by_type", {}),
            vector_documents=vector_stats.get("total_documents", 0),
            database_size_mb=db_stats.get("database_size_mb", 0.0),
            uptime_seconds=uptime
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve stats")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, chatbot: ChatBot = Depends(get_chatbot)):
    """Chat endpoint with RAG-powered responses"""
    start_time = time.time()
    
    try:
        # Update chatbot config if overrides provided
        if request.temperature is not None or request.max_tokens is not None:
            config_updates = {}
            if request.temperature is not None:
                config_updates["temperature"] = request.temperature
            if request.max_tokens is not None:
                config_updates["max_tokens"] = request.max_tokens
            
            chatbot.llm.update_config(**config_updates)
        
        # Generate response
        system_prompt = """You are a SMITE 2 expert. Use only the provided context about gods, abilities, items, and patches. 
If the context lacks an answer, say so and offer general guidance. Be concise and exact.

Abilities data format in context:
- Sections appear as: Passive, Basic Attack, 1st Ability, 2nd Ability, 3rd Ability, Ultimate.
- Common fields: Notes, Cost, Cooldown, Range (meters), Radius (meters), Damage/Base Damage, Bonus Damage, Damage Per Shot, Scaling, Duration, Slow/Cripple values, Chance/Drop Chance, Buff Duration, Attack Speed.
- Ignore any "Ability Video" lines.

Interpretation rules:
- Per-level arrays map left→right to ranks 1–5. Example: "35/55/75/95/115" = ranks 1..5. Each ability has 5 ranks.
- If a value is "0/10/10/10/10/10%", treat rank 1 as 0 and ranks 2–5 as given.
- "Scaling" percentages multiply the named stat(s). Example: "100% Strength + 20% Intelligence" = 1.00*Strength + 0.20*Intelligence.
- "Damage Per Shot" entries describe intra-ability sequencing (e.g., shot 1/2/3 of an ultimate), not ranks, unless the line itself has five rank values.
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
- If information is absent, say "Not in context." and give high-level guidance."""
        
        response = chatbot.chat(
            message=request.message,
            use_rag=request.use_rag,
            search_mode=request.search_mode.value,
            n_results=request.n_results,
            system_prompt=system_prompt
        )
        
        # Convert sources to API format
        sources = []
        if response.sources:
            for source in response.sources:
                sources.append(Source(
                    id=source.get("id", "unknown"),
                    content=source["content"],
                    metadata=source.get("metadata", {}),
                    similarity=source.get("similarity", 0.0),
                    search_type=source.get("search_type", "unknown")
                ))
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            response=response.content,
            sources=sources,
            model=response.model,
            usage=response.usage,
            search_mode=request.search_mode.value,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )

@app.get("/search-modes")
async def get_search_modes():
    """Get available search modes"""
    return {
        "search_modes": [mode.value for mode in SearchMode],
        "descriptions": {
            "hybrid": "Combines semantic and structured search (recommended)",
            "semantic": "Vector similarity search only",
            "structured": "Database keyword search only"
        }
    }