from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class SearchMode(str, Enum):
    """Available search modes for RAG retrieval"""
    hybrid = "hybrid"
    semantic = "semantic"
    structured = "structured"

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User message/question", min_length=1, max_length=2000)
    use_rag: bool = Field(True, description="Whether to use RAG for context retrieval")
    search_mode: SearchMode = Field(SearchMode.hybrid, description="Search mode for RAG retrieval")
    n_results: int = Field(3, description="Number of sources to retrieve", ge=1, le=10)
    temperature: Optional[float] = Field(None, description="Override temperature for this request", ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, description="Override max tokens for this request", ge=50, le=1000)

class Source(BaseModel):
    """Source document information"""
    id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Source content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    similarity: float = Field(..., description="Similarity score")
    search_type: str = Field(..., description="Type of search that found this source")

class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="Chat response content")
    sources: List[Source] = Field(default_factory=list, description="Sources used for RAG")
    model: Optional[str] = Field(None, description="Model used for generation")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")
    search_mode: str = Field(..., description="Search mode used")
    processing_time: float = Field(..., description="Processing time in seconds")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    database_connected: bool = Field(..., description="Database connection status")
    vector_store_connected: bool = Field(..., description="Vector store connection status")

class StatsResponse(BaseModel):
    """Database statistics response"""
    total_documents: int = Field(..., description="Total number of documents")
    documents_by_type: Dict[str, int] = Field(..., description="Document counts by type")
    vector_documents: int = Field(..., description="Documents in vector store")
    database_size_mb: float = Field(..., description="Database size in MB")
    uptime_seconds: float = Field(..., description="API uptime in seconds")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")