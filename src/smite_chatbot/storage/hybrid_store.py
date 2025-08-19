import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .database import DocumentDatabase
from .vector_store import VectorStore
from ..processors.base import Document

logger = logging.getLogger(__name__)


class HybridDocumentStore:
    """Combines SQLite database and ChromaDB vector store for optimal document retrieval."""
    
    def __init__(
        self,
        storage_dir: Path,
        collection_name: str = "smite_documents",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize both stores
        self.database = DocumentDatabase(self.storage_dir / "documents.db")
        self.vector_store = VectorStore(
            persist_directory=self.storage_dir / "vectors",
            collection_name=collection_name,
            embedding_model=embedding_model
        )
        
        logger.info(f"Hybrid document store initialized at {storage_dir}")
    
    def add_document(self, document: Document) -> bool:
        """Add document to both database and vector store."""
        db_success = self.database.insert_document(document)
        vector_success = self.vector_store.add_document(document)
        
        if db_success and vector_success:
            logger.debug(f"Successfully added document {document.id}")
            return True
        else:
            logger.error(f"Failed to add document {document.id} (DB: {db_success}, Vector: {vector_success})")
            return False
    
    def add_documents(self, documents: List[Document]) -> Tuple[int, int]:
        """Add multiple documents to both stores."""
        logger.info(f"Adding {len(documents)} documents to hybrid store")
        
        # Add to database
        db_success, db_total = self.database.insert_documents(documents)
        logger.info(f"Database: {db_success}/{db_total} documents added")
        
        # Add to vector store
        vector_success, vector_total = self.vector_store.add_documents(documents)
        logger.info(f"Vector store: {vector_success}/{vector_total} documents added")
        
        # Return minimum success count (both stores must succeed)
        min_success = min(db_success, vector_success)
        return min_success, len(documents)
    
    def search(
        self,
        query: str,
        n_results: int = 10,
        doc_type: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        search_mode: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        Search documents using different modes:
        - 'semantic': Vector similarity search only
        - 'structured': Database search only
        - 'hybrid': Combined approach (recommended)
        """
        
        if search_mode == "semantic":
            return self._semantic_search(query, n_results, doc_type, metadata_filters)
        elif search_mode == "structured":
            return self._structured_search(query, n_results, doc_type, metadata_filters)
        else:  # hybrid
            return self._hybrid_search(query, n_results, doc_type, metadata_filters)
    
    def _semantic_search(
        self,
        query: str,
        n_results: int,
        doc_type: Optional[str],
        metadata_filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Pure vector similarity search."""
        return self.vector_store.search(query, n_results, doc_type, metadata_filters)
    
    def _structured_search(
        self,
        query: str,
        n_results: int,
        doc_type: Optional[str],
        metadata_filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Pure database search with text matching."""
        documents = self.database.search_documents(
            doc_type=doc_type,
            name_contains=query,
            metadata_filters=metadata_filters,
            limit=n_results
        )
        
        # Convert to consistent format
        return [{
            'id': doc.id,
            'content': doc.content,
            'metadata': {**doc.metadata, 'type': doc.type, 'name': doc.name},
            'similarity': 1.0,  # Perfect match for structured search
            'search_type': 'structured'
        } for doc in documents]
    
    def _hybrid_search(
        self,
        query: str,
        n_results: int,
        doc_type: Optional[str],
        metadata_filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Combined semantic + structured search with intelligent merging."""
        
        # Get semantic results
        semantic_results = self.vector_store.hybrid_search(
            query=query,
            n_results=n_results,
            metadata_filters=metadata_filters
        )
        
        # Get structured results for exact name matches
        structured_results = self._structured_search(
            query, n_results // 2, doc_type, metadata_filters
        )
        
        # Merge and deduplicate results
        seen_ids = set()
        merged_results = []
        
        # Prioritize structured results (exact matches)
        for result in structured_results:
            if result['id'] not in seen_ids:
                result['search_type'] = 'structured'
                merged_results.append(result)
                seen_ids.add(result['id'])
        
        # Add semantic results
        for result in semantic_results:
            if result['id'] not in seen_ids:
                result['search_type'] = 'semantic'
                merged_results.append(result)
                seen_ids.add(result['id'])
        
        # Sort by relevance (structured first, then by similarity)
        merged_results.sort(key=lambda x: (
            0 if x['search_type'] == 'structured' else 1,
            -x['similarity']
        ))
        
        return merged_results[:n_results]
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID from database."""
        return self.database.get_document(doc_id)
    
    def get_documents_by_type(self, doc_type: str, limit: Optional[int] = None) -> List[Document]:
        """Get all documents of a specific type."""
        return self.database.get_documents_by_type(doc_type, limit)
    
    def get_similar_documents(self, document_id: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Find documents similar to a given document."""
        return self.vector_store.get_similar_documents(document_id, n_results)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from both stores."""
        db_stats = self.database.get_stats()
        vector_stats = self.vector_store.get_stats()
        
        return {
            'storage_directory': str(self.storage_dir),
            'database': db_stats,
            'vector_store': vector_stats,
            'sync_status': {
                'db_docs': db_stats.get('total_documents', 0),
                'vector_docs': vector_stats.get('total_documents', 0),
                'in_sync': db_stats.get('total_documents') == vector_stats.get('total_documents')
            }
        }
    
    def delete_by_type(self, doc_type: str) -> Tuple[int, int]:
        """Delete all documents of a specific type from both stores."""
        db_deleted = self.database.delete_documents_by_type(doc_type)
        vector_deleted = self.vector_store.delete_by_type(doc_type)
        
        logger.info(f"Deleted {db_deleted} from database, {vector_deleted} from vector store")
        return db_deleted, vector_deleted
    
    def clear_all(self) -> bool:
        """Clear all documents from both stores."""
        db_cleared = self.database.clear_all()
        vector_cleared = self.vector_store.clear_all()
        
        success = db_cleared and vector_cleared
        logger.info(f"Clear all: Database={db_cleared}, VectorStore={vector_cleared}")
        return success
    
    def sync_stores(self) -> Dict[str, Any]:
        """Ensure both stores have the same documents."""
        logger.info("Starting store synchronization")
        
        # Get all documents from database
        all_docs = []
        for doc_type in ['god', 'ability', 'item', 'patch', 'god_change']:
            docs = self.database.get_documents_by_type(doc_type)
            all_docs.extend(docs)
        
        if not all_docs:
            return {'status': 'no_documents', 'synced_count': 0}
        
        # Clear vector store and re-add all documents
        self.vector_store.clear_all()
        success_count, total_count = self.vector_store.add_documents(all_docs)
        
        sync_result = {
            'status': 'completed' if success_count == total_count else 'partial',
            'synced_count': success_count,
            'total_count': total_count,
            'success_rate': success_count / total_count if total_count > 0 else 0
        }
        
        logger.info(f"Sync completed: {success_count}/{total_count} documents")
        return sync_result
    
    def recommend_documents(
        self,
        query: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Advanced recommendation system combining search with user preferences."""
        
        # Start with hybrid search
        results = self._hybrid_search(query, n_results * 2, None, None)
        
        # Apply preference-based scoring if provided
        if user_preferences:
            for result in results:
                base_score = result['similarity']
                metadata = result['metadata']
                
                # Boost based on user preferences
                if 'preferred_pantheons' in user_preferences:
                    pantheon = metadata.get('pantheon', '').lower()
                    if pantheon in [p.lower() for p in user_preferences['preferred_pantheons']]:
                        result['similarity'] = min(1.0, base_score * 1.15)
                
                if 'preferred_roles' in user_preferences:
                    role = metadata.get('role', '').lower()
                    if role in [r.lower() for r in user_preferences['preferred_roles']]:
                        result['similarity'] = min(1.0, base_score * 1.1)
                
                if 'difficulty_preference' in user_preferences:
                    # Could add difficulty metadata to documents in the future
                    pass
        
        # Re-sort and limit
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:n_results]