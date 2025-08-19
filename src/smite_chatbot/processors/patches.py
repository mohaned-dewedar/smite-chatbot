from typing import List, Dict, Any
import logging
from .base import BaseProcessor, Document, generate_document_id, clean_text

logger = logging.getLogger(__name__)


class PatchProcessor(BaseProcessor):
    """Processor for patch_details.json data."""
    
    def process(self) -> List[Document]:
        """Process patch data into patch and god change documents."""
        data = self.load_source_data()
        documents = []
        
        patches = data.get('patches', [])
        logger.info(f"Processing {len(patches)} patches")
        
        for patch_data in patches:
            try:
                # Create patch overview document
                patch_doc = self._create_patch_document(patch_data)
                documents.append(patch_doc)
                
                # Create individual god change documents
                change_docs = self._create_god_change_documents(patch_data)
                documents.extend(change_docs)
                
            except Exception as e:
                logger.error(f"Failed to process patch {patch_data.get('title', 'unknown')}: {e}")
                continue
        
        return documents
    
    def _create_patch_document(self, patch_data: Dict[str, Any]) -> Document:
        """Create a document for patch overview."""
        title = patch_data.get('title', '')
        url = patch_data.get('url', '')
        highlights = patch_data.get('highlights', [])
        god_balance = patch_data.get('god_balance', [])
        
        # Build content string
        content_parts = [title]
        
        # Add highlights if present
        if highlights:
            highlights_text = ". ".join(clean_text(highlight) for highlight in highlights)
            content_parts.append(f"Highlights: {highlights_text}")
        
        # Add summary of god changes
        if god_balance:
            gods_changed = [change.get('name', '') for change in god_balance if change.get('name')]
            if gods_changed:
                content_parts.append(f"Gods Changed: {', '.join(gods_changed)}")
        
        content = ". ".join(content_parts)
        
        # Create metadata
        metadata = {
            'patch_number': self._extract_patch_number(title),
            'gods_changed_count': len(god_balance),
            'has_highlights': bool(highlights),
            'gods_changed': [change.get('name', '') for change in god_balance if change.get('name')]
        }
        
        return Document(
            id=generate_document_id('patch', title),
            type='patch',
            name=title,
            content=content,
            metadata=metadata,
            source_url=url
        )
    
    def _create_god_change_documents(self, patch_data: Dict[str, Any]) -> List[Document]:
        """Create documents for individual god balance changes."""
        documents = []
        patch_title = patch_data.get('title', '')
        god_balance = patch_data.get('god_balance', [])
        
        for change_data in god_balance:
            try:
                change_doc = self._create_god_change_document(patch_title, change_data)
                documents.append(change_doc)
            except Exception as e:
                logger.error(f"Failed to process god change {change_data.get('name', 'unknown')} in {patch_title}: {e}")
                continue
        
        return documents
    
    def _create_god_change_document(self, patch_title: str, change_data: Dict[str, Any]) -> Document:
        """Create a document for a single god's balance changes."""
        god_name = change_data.get('name', '')
        change_title = change_data.get('title', '')
        changes = change_data.get('changes', [])
        
        # Build content string
        content_parts = [f"{god_name} changes in {patch_title}"]
        
        if change_title:
            # Extract change type from title (Buff, Nerf, etc.)
            change_type = self._extract_change_type(change_title)
            if change_type:
                content_parts.append(f"Change Type: {change_type}")
        
        # Add individual changes
        if changes:
            changes_text = ". ".join(clean_text(change) for change in changes)
            content_parts.append(f"Changes: {changes_text}")
        
        content = ". ".join(content_parts)
        
        # Create metadata
        metadata = {
            'god': god_name,
            'patch': patch_title,
            'patch_number': self._extract_patch_number(patch_title),
            'change_type': self._extract_change_type(change_title),
            'change_count': len(changes)
        }
        
        return Document(
            id=generate_document_id('god_change', god_name, patch=self._extract_patch_number(patch_title)),
            type='god_change',
            name=f"{god_name} - {patch_title}",
            content=content,
            metadata=metadata
        )
    
    def _extract_patch_number(self, title: str) -> str:
        """Extract patch number from title."""
        import re
        
        # Look for patterns like "Open Beta 16", "Update 1.2.3", etc.
        patterns = [
            r'open beta (\d+)',
            r'beta (\d+)',
            r'update ([\d.]+)',
            r'patch ([\d.]+)',
            r'version ([\d.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title.lower())
            if match:
                return match.group(1)
        
        return title  # Return full title if no pattern matches
    
    def _extract_change_type(self, change_title: str) -> str:
        """Extract change type (Buff, Nerf, etc.) from change title."""
        change_title_lower = change_title.lower()
        
        if 'buff' in change_title_lower:
            return 'Buff'
        elif 'nerf' in change_title_lower:
            return 'Nerf'
        elif 'fix' in change_title_lower:
            return 'Fix'
        elif 'shift' in change_title_lower:
            return 'Shift'
        elif 'rework' in change_title_lower:
            return 'Rework'
        else:
            return 'Adjustment'
    
    def run(self) -> List[Document]:
        """Execute processing and save documents."""
        documents = super().run()
        
        # Separate patch overviews and god changes
        patch_docs = [doc for doc in documents if doc.type == 'patch']
        change_docs = [doc for doc in documents if doc.type == 'god_change']
        
        # Save to separate files
        self.save_documents(patch_docs, 'patches_processed.json')
        self.save_documents(change_docs, 'god_changes_processed.json')
        self.save_documents(documents, 'patches_and_changes_processed.json')
        
        logger.info(f"Processed {len(patch_docs)} patches and {len(change_docs)} god changes")
        return documents