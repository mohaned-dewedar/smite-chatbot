import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
import torch
from sentence_transformers import SentenceTransformer

from ..processors.base import Document

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB vector store for document embeddings."""
    
    def __init__(
        self, 
        persist_directory: Path, 
        collection_name: str = "smite_documents",
        embedding_model: str = "BAAI/bge-large-en-v1.5"
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model with GPU support
        logger.info(f"Loading embedding model: {embedding_model}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        self.embedding_model = SentenceTransformer(
            embedding_model,
            device=device
        )
        self.embedding_model_name = embedding_model
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "SMITE 2 game data embeddings"}
        )
        
        logger.info(f"Vector store initialized at {persist_directory}")
        logger.info(f"Collection '{collection_name}' ready with {self.collection.count()} documents")
    
    def add_document(self, document: Document) -> bool:
        """Add a single document to the vector store."""
        try:
            # Generate embedding with appropriate prefix for model
            text = self._prepare_text_for_embedding(document.content, is_query=False)
            embedding = self.embedding_model.encode(text).tolist()
            
            # Prepare metadata (ChromaDB requires string values)
            metadata = self._prepare_metadata(document)
            
            # Add to collection
            self.collection.add(
                ids=[document.id],
                documents=[document.content],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document {document.id}: {e}")
            return False
    
    def add_documents(self, documents: List[Document]) -> Tuple[int, int]:
        """Add multiple documents to the vector store."""
        if not documents:
            return 0, 0
        
        success_count = 0
        batch_size = 100  # Process in batches for better performance
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            try:
                # Prepare batch data
                ids = [doc.id for doc in batch]
                contents = [doc.content for doc in batch]
                metadatas = [self._prepare_metadata(doc) for doc in batch]
                
                # Generate embeddings for batch with appropriate prefixes
                prepared_contents = [self._prepare_text_for_embedding(content, is_query=False) for content in contents]
                embeddings = self.embedding_model.encode(prepared_contents).tolist()
                
                # Add batch to collection
                self.collection.add(
                    ids=ids,
                    documents=contents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                
                success_count += len(batch)
                logger.info(f"Added batch {i//batch_size + 1}: {len(batch)} documents")
                
            except Exception as e:
                logger.error(f"Failed to add batch {i//batch_size + 1}: {e}")
                continue
        
        logger.info(f"Added {success_count}/{len(documents)} documents to vector store")
        return success_count, len(documents)
    
    def search(
        self,
        query: str,
        n_results: int = 10,
        doc_type: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        try:
            # Generate query embedding with appropriate prefix
            prepared_query = self._prepare_text_for_embedding(query, is_query=True)
            query_embedding = self.embedding_model.encode(prepared_query).tolist()
            
            # Prepare where clause for filtering
            where_clause = {}
            if doc_type:
                where_clause["type"] = doc_type
            
            if metadata_filters:
                for key, value in metadata_filters.items():
                    where_clause[key] = str(value)  # ChromaDB requires string values
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i],
                    'similarity': 1 - results['distances'][0][i]  # Convert distance to similarity
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def search_by_document_type(
        self,
        query: str,
        doc_type: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search within a specific document type."""
        return self.search(query, n_results, doc_type=doc_type)
    
    def get_similar_documents(
        self,
        document_id: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find documents similar to a given document."""
        try:
            # Get the document
            doc_result = self.collection.get(
                ids=[document_id],
                include=["documents"]
            )
            
            if not doc_result['documents']:
                return []
            
            # Use the document content as query
            content = doc_result['documents'][0]
            return self.search(content, n_results)
            
        except Exception as e:
            logger.error(f"Failed to find similar documents for {document_id}: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        try:
            total_count = self.collection.count()
            
            # Get sample documents to analyze metadata
            sample_results = self.collection.get(
                limit=min(100, total_count),
                include=["metadatas"]
            )
            
            # Count by type
            type_counts = {}
            if sample_results['metadatas']:
                for metadata in sample_results['metadatas']:
                    doc_type = metadata.get('type', 'unknown')
                    type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            return {
                'total_documents': total_count,
                'collection_name': self.collection_name,
                'persist_directory': str(self.persist_directory),
                'embedding_model': self.embedding_model.get_sentence_embedding_dimension(),
                'sample_type_distribution': type_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get vector store stats: {e}")
            return {}
    
    def _prepare_text_for_embedding(self, text: str, is_query: bool = False) -> str:
        """Prepare text with appropriate prefixes for different embedding models."""
        # E5 models need prefixes
        if "e5-" in self.embedding_model_name.lower():
            if is_query:
                return f"query: {text}"
            else:
                return f"passage: {text}"
        
        # Nomic models need prefixes  
        elif "nomic" in self.embedding_model_name.lower():
            if is_query:
                return f"search_query: {text}"
            else:
                return f"search_document: {text}"
        
        # BGE models need prefixes
        elif "bge" in self.embedding_model_name.lower():
            if is_query:
                return f"Represent this sentence for searching relevant passages: {text}"
            else:
                return text
        
        # Other models (MiniLM, etc.) don't need prefixes
        return text
    
    def delete_by_type(self, doc_type: str) -> int:
        """Delete all documents of a specific type."""
        try:
            # Get documents of this type
            results = self.collection.get(
                where={"type": doc_type},
                include=["documents"]
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                deleted_count = len(results['ids'])
                logger.info(f"Deleted {deleted_count} documents of type {doc_type}")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to delete documents of type {doc_type}: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Clear all documents from the vector store."""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "SMITE 2 game data embeddings"}
            )
            logger.info("Cleared all documents from vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            return False
    
    def _prepare_metadata(self, document: Document) -> Dict[str, str]:
        """Prepare metadata for ChromaDB (requires string values)."""
        metadata = {
            'type': document.type,
            'name': document.name,
        }
        
        # Add source URL if available
        if document.source_url:
            metadata['source_url'] = document.source_url
        
        # Add document metadata as strings
        for key, value in document.metadata.items():
            if value is not None:
                metadata[key] = str(value)
        
        return metadata
    
    def hybrid_search(
        self,
        query: str,
        n_results: int = 10,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Enhanced search combining semantic similarity with metadata filtering."""
        try:
            # First, do semantic search
            semantic_results = self.search(
                query=query,
                n_results=n_results * 2,  # Get more results for filtering
                metadata_filters=metadata_filters
            )
            
            # Apply additional scoring based on metadata relevance
            for result in semantic_results:
                base_score = result['similarity']
                
                # Boost score for exact name matches
                if query.lower() in result['metadata'].get('name', '').lower():
                    result['similarity'] = min(1.0, base_score * 1.2)
                
                # Boost score for relevant document types based on query
                if any(keyword in query.lower() for keyword in ['god', 'character', 'hero']):
                    if result['metadata'].get('type') == 'god':
                        result['similarity'] = min(1.0, base_score * 1.1)
                elif any(keyword in query.lower() for keyword in ['item', 'equipment', 'build']):
                    if result['metadata'].get('type') == 'item':
                        result['similarity'] = min(1.0, base_score * 1.1)
                elif any(keyword in query.lower() for keyword in ['ability', 'skill', 'spell']):
                    if result['metadata'].get('type') == 'ability':
                        result['similarity'] = min(1.0, base_score * 1.1)
            
            # Re-sort by adjusted similarity and limit results
            semantic_results.sort(key=lambda x: x['similarity'], reverse=True)
            return semantic_results[:n_results]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []