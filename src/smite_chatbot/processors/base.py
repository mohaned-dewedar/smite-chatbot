from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Base document structure for all processed content."""
    id: str
    type: str
    name: str
    content: str
    metadata: Dict[str, Any]
    source_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert document to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class BaseProcessor(ABC):
    """Base class for all data processors."""
    
    def __init__(self, source_file: Path, output_dir: Path):
        self.source_file = Path(source_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.source_file.exists():
            raise FileNotFoundError(f"Source file not found: {self.source_file}")
    
    def load_source_data(self) -> Dict[str, Any]:
        """Load source JSON data."""
        try:
            with open(self.source_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {self.source_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load {self.source_file}: {e}")
            raise
    
    @abstractmethod
    def process(self) -> List[Document]:
        """Process source data into documents."""
        pass
    
    def save_documents(self, documents: List[Document], filename: str) -> Path:
        """Save documents to JSON file."""
        output_path = self.output_dir / filename
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump([doc.to_dict() for doc in documents], f, indent=2)
            
            logger.info(f"Saved {len(documents)} documents to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save documents to {output_path}: {e}")
            raise
    
    def run(self) -> List[Document]:
        """Execute the full processing pipeline."""
        logger.info(f"Processing {self.source_file}")
        documents = self.process()
        logger.info(f"Generated {len(documents)} documents")
        return documents


def generate_document_id(doc_type: str, name: str, **kwargs) -> str:
    """Generate a unique document ID."""
    parts = [doc_type, name.lower().replace(' ', '_')]
    for key, value in kwargs.items():
        if value:
            parts.append(f"{key}_{str(value).lower().replace(' ', '_')}")
    return "_".join(parts)


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    
    return text.strip().replace('\n', ' ').replace('\r', ' ')


def format_stats(stats: Dict[str, Any]) -> str:
    """Format stats dictionary into readable text."""
    if not stats:
        return ""
    
    formatted_parts = []
    for key, value in stats.items():
        if value and str(value).strip():
            clean_key = key.rstrip(':').strip()
            formatted_parts.append(f"{clean_key}: {value}")
    
    return ". ".join(formatted_parts)