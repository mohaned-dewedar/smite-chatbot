import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime

from ..processors.base import Document

logger = logging.getLogger(__name__)


class DocumentDatabase:
    """SQLite database for storing processed documents with metadata."""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSON,
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON documents(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON documents(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON documents(created_at)")
            
            # Create metadata indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_god 
                ON documents(json_extract(metadata, '$.god'))
                WHERE json_extract(metadata, '$.god') IS NOT NULL
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_pantheon 
                ON documents(json_extract(metadata, '$.pantheon'))
                WHERE json_extract(metadata, '$.pantheon') IS NOT NULL
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_role 
                ON documents(json_extract(metadata, '$.role'))
                WHERE json_extract(metadata, '$.role') IS NOT NULL
            """)
            
            conn.commit()
            
        logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def insert_document(self, document: Document) -> bool:
        """Insert a single document."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO documents 
                    (id, type, name, content, metadata, source_url, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    document.id,
                    document.type,
                    document.name,
                    document.content,
                    json.dumps(document.metadata),
                    document.source_url
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert document {document.id}: {e}")
            return False
    
    def insert_documents(self, documents: List[Document]) -> Tuple[int, int]:
        """Insert multiple documents. Returns (success_count, total_count)."""
        success_count = 0
        
        try:
            with self._get_connection() as conn:
                for document in documents:
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO documents 
                            (id, type, name, content, metadata, source_url, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (
                            document.id,
                            document.type,
                            document.name,
                            document.content,
                            json.dumps(document.metadata),
                            document.source_url
                        ))
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to insert document {document.id}: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Database transaction failed: {e}")
        
        logger.info(f"Inserted {success_count}/{len(documents)} documents")
        return success_count, len(documents)
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a single document by ID."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM documents WHERE id = ?", (doc_id,)
                ).fetchone()
                
                if row:
                    return self._row_to_document(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    def get_documents_by_type(self, doc_type: str, limit: Optional[int] = None) -> List[Document]:
        """Get all documents of a specific type."""
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM documents WHERE type = ? ORDER BY created_at"
                if limit:
                    query += f" LIMIT {limit}"
                
                rows = conn.execute(query, (doc_type,)).fetchall()
                return [self._row_to_document(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get documents by type {doc_type}: {e}")
            return []
    
    def search_documents(
        self, 
        doc_type: Optional[str] = None,
        name_contains: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Document]:
        """Search documents with various filters."""
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM documents WHERE 1=1"
                params = []
                
                if doc_type:
                    query += " AND type = ?"
                    params.append(doc_type)
                
                if name_contains:
                    query += " AND name LIKE ?"
                    params.append(f"%{name_contains}%")
                
                if metadata_filters:
                    for key, value in metadata_filters.items():
                        query += f" AND json_extract(metadata, '$.{key}') = ?"
                        params.append(value)
                
                query += " ORDER BY created_at"
                
                if limit:
                    query += f" LIMIT {limit}"
                
                rows = conn.execute(query, params).fetchall()
                return [self._row_to_document(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self._get_connection() as conn:
                # Total count
                total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
                
                # Count by type
                type_counts = {}
                rows = conn.execute("""
                    SELECT type, COUNT(*) as count 
                    FROM documents 
                    GROUP BY type 
                    ORDER BY count DESC
                """).fetchall()
                
                for row in rows:
                    type_counts[row[0]] = row[1]
                
                # Recent additions
                recent = conn.execute("""
                    SELECT COUNT(*) FROM documents 
                    WHERE created_at >= datetime('now', '-24 hours')
                """).fetchone()[0]
                
                return {
                    'total_documents': total,
                    'by_type': type_counts,
                    'added_last_24h': recent,
                    'database_path': str(self.db_path),
                    'database_size_mb': self.db_path.stat().st_size / (1024 * 1024)
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def _row_to_document(self, row: sqlite3.Row) -> Document:
        """Convert database row to Document object."""
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return Document(
            id=row['id'],
            type=row['type'],
            name=row['name'],
            content=row['content'],
            metadata=metadata,
            source_url=row['source_url']
        )
    
    def delete_documents_by_type(self, doc_type: str) -> int:
        """Delete all documents of a specific type. Returns count deleted."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM documents WHERE type = ?", (doc_type,))
                conn.commit()
                deleted_count = cursor.rowcount
                logger.info(f"Deleted {deleted_count} documents of type {doc_type}")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to delete documents of type {doc_type}: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Clear all documents from database."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM documents")
                conn.commit()
                logger.info("Cleared all documents from database")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False