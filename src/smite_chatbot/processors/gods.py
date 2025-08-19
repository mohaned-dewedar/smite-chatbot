from typing import List, Dict, Any
import logging
from .base import BaseProcessor, Document, generate_document_id, clean_text, format_stats

logger = logging.getLogger(__name__)


class GodsProcessor(BaseProcessor):
    """Processor for gods.json data."""
    
    def process(self) -> List[Document]:
        """Process gods data into god and ability documents."""
        data = self.load_source_data()
        documents = []
        
        gods = data.get('gods', [])
        logger.info(f"Processing {len(gods)} gods")
        
        for god_data in gods:
            try:
                # Create god document
                god_doc = self._create_god_document(god_data)
                documents.append(god_doc)
                
                # Create ability documents
                ability_docs = self._create_ability_documents(god_data)
                documents.extend(ability_docs)
                
            except Exception as e:
                logger.error(f"Failed to process god {god_data.get('name', 'unknown')}: {e}")
                continue
        
        return documents
    
    def _create_god_document(self, god_data: Dict[str, Any]) -> Document:
        """Create a document for a god's basic information."""
        name = god_data.get('name', '')
        info = god_data.get('info', {})
        url = god_data.get('url', '')
        
        # Build content string
        content_parts = [f"{name}"]
        
        if title := info.get('Title:'):
            content_parts.append(f"Title: {title}")
        
        if pantheon := info.get('Pantheon:'):
            content_parts.append(f"Pantheon: {pantheon}")
        
        if roles := info.get('Roles:'):
            content_parts.append(f"Role: {roles}")
        
        # Add stats
        stats_text = self._format_god_stats(info)
        if stats_text:
            content_parts.append(f"Stats: {stats_text}")
        
        # Add ability names for cross-referencing and better search
        abilities = god_data.get('abilities', [])
        if abilities:
            ability_names = [ability.get('name', '') for ability in abilities if ability.get('name')]
            # Find ultimate ability for special mention
            ultimate_abilities = [ability.get('name', '') for ability in abilities 
                                if ability.get('type', '').lower() == 'ultimate' and ability.get('name')]
            
            if ability_names:
                content_parts.append(f"Abilities: {', '.join(ability_names)}")
            
            if ultimate_abilities:
                ultimate_name = ultimate_abilities[0]  # Usually just one ultimate
                content_parts.append(f"Ultimate ability: {ultimate_name}")
        
        content = ". ".join(content_parts)
        
        # Create metadata
        metadata = {
            'pantheon': info.get('Pantheon:', '').strip(),
            'role': info.get('Roles:', '').strip(),
            'title': info.get('Title:', '').strip(),
            'release_date': info.get('Release date:', '').strip(),
            'voice_actor': info.get('Voice actor:', '').strip(),
            'ability_count': len(god_data.get('abilities', []))
        }
        
        # Remove empty metadata values
        metadata = {k: v for k, v in metadata.items() if v}
        
        return Document(
            id=generate_document_id('god', name),
            type='god',
            name=name,
            content=content,
            metadata=metadata,
            source_url=url
        )
    
    def _create_ability_documents(self, god_data: Dict[str, Any]) -> List[Document]:
        """Create documents for each of a god's abilities."""
        documents = []
        god_name = god_data.get('name', '')
        abilities = god_data.get('abilities', [])
        
        for ability in abilities:
            try:
                ability_doc = self._create_ability_document(god_name, ability)
                documents.append(ability_doc)
            except Exception as e:
                logger.error(f"Failed to process ability {ability.get('name', 'unknown')} for {god_name}: {e}")
                continue
        
        return documents
    
    def _create_ability_document(self, god_name: str, ability_data: Dict[str, Any]) -> Document:
        """Create a document for a single ability."""
        ability_name = ability_data.get('name', '')
        ability_type = ability_data.get('type', '')
        description = clean_text(ability_data.get('description', ''))
        stats = ability_data.get('stats', {})
        notes = clean_text(ability_data.get('notes', ''))
        
        # Build content string - include god name and semantic keywords for better searchability
        # Format: "Ability Name (God Name)" for better search matching
        content_parts = [f"{ability_name} ({god_name})"]
        
        if ability_type:
            # Add semantic keyword for ultimate abilities
            if ability_type.lower() == 'ultimate':
                content_parts.append(f"Type: {ability_type} - {god_name} ultimate ability")
            else:
                content_parts.append(f"Type: {ability_type}")
        
        if description:
            content_parts.append(f"Description: {description}")
        
        # Format stats
        stats_text = format_stats(stats)
        if stats_text:
            content_parts.append(f"Stats: {stats_text}")
        
        if notes:
            content_parts.append(f"Notes: {notes}")
        
        # Join content and ensure god name appears in searchable text
        content = ". ".join(content_parts)
        
        # Additional semantic enhancement for ultimate abilities
        if ability_type.lower() == 'ultimate':
            content = f"{content}. This is {god_name}'s ultimate ability."
        
        # Create metadata
        metadata = {
            'god': god_name,
            'ability_type': ability_type,
            'has_description': bool(description),
            'has_stats': bool(stats),
            'has_notes': bool(notes)
        }
        
        return Document(
            id=generate_document_id('ability', ability_name, god=god_name),
            type='ability',
            name=ability_name,
            content=content,
            metadata=metadata
        )
    
    def _format_god_stats(self, info: Dict[str, Any]) -> str:
        """Format god stats into readable text."""
        stat_keys = [
            'Health:', 'Health Regen:', 'Mana:', 'Mana Regen:',
            'Physical Pro.:', 'Magical Pro.:', 'Attack Speed:', 'Move Speed:'
        ]
        
        stats = {}
        for key in stat_keys:
            if value := info.get(key):
                clean_key = key.rstrip(':')
                stats[clean_key] = value
        
        return format_stats(stats)
    
    def run(self) -> List[Document]:
        """Execute processing and save documents."""
        documents = super().run()
        
        # Separate god and ability documents
        god_docs = [doc for doc in documents if doc.type == 'god']
        ability_docs = [doc for doc in documents if doc.type == 'ability']
        
        # Save to separate files
        self.save_documents(god_docs, 'gods_processed.json')
        self.save_documents(ability_docs, 'abilities_processed.json')
        self.save_documents(documents, 'gods_and_abilities_processed.json')
        
        logger.info(f"Processed {len(god_docs)} gods and {len(ability_docs)} abilities")
        return documents