from typing import List, Dict, Any
import logging
import re
from .base import BaseProcessor, Document, generate_document_id, clean_text

logger = logging.getLogger(__name__)


class ItemsProcessor(BaseProcessor):
    """Processor for items.json data."""
    
    def process(self) -> List[Document]:
        """Process items data, filtering out wiki metadata and keeping actual items."""
        data = self.load_source_data()
        documents = []
        
        items = data.get('items', [])
        logger.info(f"Processing {len(items)} item entries")
        
        for item_data in items:
            try:
                # Filter out non-item content
                if not self._is_actual_item(item_data):
                    continue
                
                # Create item document
                item_doc = self._create_item_document(item_data)
                documents.append(item_doc)
                
            except Exception as e:
                logger.error(f"Failed to process item {item_data.get('name', 'unknown')}: {e}")
                continue
        
        logger.info(f"Filtered to {len(documents)} actual items")
        return documents
    
    def _is_actual_item(self, item_data: Dict[str, Any]) -> bool:
        """Determine if this is an actual game item vs wiki metadata."""
        name = item_data.get('name', '')
        url = item_data.get('url', '')
        stats = item_data.get('stats', {})
        descriptions = item_data.get('descriptions', [])
        
        # Skip obvious non-items
        skip_patterns = [
            r'editing.*section', r'category:', r'template:', r'file:',
            r'user:', r'talk:', r'help:', r'special:', r'media:'
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, name.lower()) or re.search(pattern, url.lower()):
                return False
        
        # Skip if it's just general game information
        if name.lower() in ['smite 2', 'items', 'game modes', 'gods']:
            return False
        
        # Must have either meaningful stats or item-specific information
        has_item_stats = any(key for key in stats.keys() 
                           if any(indicator in key.lower() 
                                for indicator in ['cost', 'tier', 'stats', 'passive', 'active']))
        
        has_item_description = any(desc for desc in descriptions 
                                 if len(desc) > 50 and 
                                 any(indicator in desc.lower() 
                                   for indicator in ['damage', 'health', 'protection', 'ability', 'passive']))
        
        return has_item_stats or has_item_description
    
    def _create_item_document(self, item_data: Dict[str, Any]) -> Document:
        """Create a document for an item."""
        name = item_data.get('name', '')
        url = item_data.get('url', '')
        stats = item_data.get('stats', {})
        descriptions = item_data.get('descriptions', [])
        
        # Build content string
        content_parts = [name]
        
        # Add item type and tier info
        item_type = stats.get('Item Type:', '')
        if item_type:
            content_parts.append(f"Type: {item_type}")
        
        # Add cost information
        cost_info = self._extract_cost_info(stats)
        if cost_info:
            content_parts.append(cost_info)
        
        # Add stats
        item_stats = self._extract_item_stats(stats)
        if item_stats:
            content_parts.append(f"Stats: {item_stats}")
        
        # Add passive/active effects
        effects = self._extract_effects(stats)
        if effects:
            content_parts.append(effects)
        
        # Add descriptions
        clean_descriptions = [clean_text(desc) for desc in descriptions if desc and len(desc.strip()) > 10]
        if clean_descriptions:
            content_parts.append(f"Description: {' '.join(clean_descriptions[:2])}")  # Limit to 2 descriptions
        
        content = ". ".join(content_parts)
        
        # Create metadata
        metadata = self._create_item_metadata(stats, item_type)
        
        return Document(
            id=generate_document_id('item', name),
            type='item',
            name=name,
            content=content,
            metadata=metadata,
            source_url=url
        )
    
    def _extract_cost_info(self, stats: Dict[str, Any]) -> str:
        """Extract cost information from stats."""
        cost_parts = []
        
        if cost := stats.get('Cost:'):
            cost_parts.append(f"Cost: {cost}")
        
        if total_cost := stats.get('Total Cost:'):
            cost_parts.append(f"Total Cost: {total_cost}")
        
        return ". ".join(cost_parts)
    
    def _extract_item_stats(self, stats: Dict[str, Any]) -> str:
        """Extract item stats (not effects)."""
        stats_value = stats.get('Stats:', '')
        if stats_value:
            return stats_value
        return ""
    
    def _extract_effects(self, stats: Dict[str, Any]) -> str:
        """Extract passive and active effects."""
        effects = []
        
        if passive := stats.get('Passive Effect:'):
            effects.append(f"Passive: {clean_text(passive)}")
        
        if active := stats.get('Active Effect:'):
            effects.append(f"Active: {clean_text(active)}")
        
        return ". ".join(effects)
    
    def _create_item_metadata(self, stats: Dict[str, Any], item_type: str) -> Dict[str, Any]:
        """Create metadata for item."""
        metadata = {}
        
        if item_type:
            metadata['item_type'] = item_type
            
            # Extract tier information
            if 'tier' in item_type.lower():
                tier_match = re.search(r'tier (\d+)', item_type.lower())
                if tier_match:
                    metadata['tier'] = int(tier_match.group(1))
            
            # Extract category
            if 'offensive' in item_type.lower():
                metadata['category'] = 'offensive'
            elif 'defensive' in item_type.lower():
                metadata['category'] = 'defensive'
            elif 'hybrid' in item_type.lower():
                metadata['category'] = 'hybrid'
            elif 'starter' in item_type.lower():
                metadata['category'] = 'starter'
        
        # Extract cost as integer if possible
        if cost_str := stats.get('Total Cost:'):
            try:
                metadata['total_cost'] = int(cost_str)
            except (ValueError, TypeError):
                pass
        
        # Check for specific stat types
        stats_str = stats.get('Stats:', '').lower()
        if stats_str:
            if 'intelligence' in stats_str:
                metadata['has_intelligence'] = True
            if 'strength' in stats_str:
                metadata['has_strength'] = True
            if 'lifesteal' in stats_str:
                metadata['has_lifesteal'] = True
            if 'protection' in stats_str:
                metadata['has_protection'] = True
        
        # Check for effects
        metadata['has_passive'] = bool(stats.get('Passive Effect:'))
        metadata['has_active'] = bool(stats.get('Active Effect:'))
        
        return metadata
    
    def run(self) -> List[Document]:
        """Execute processing and save documents."""
        documents = super().run()
        self.save_documents(documents, 'items_processed.json')
        
        logger.info(f"Processed {len(documents)} items")
        return documents