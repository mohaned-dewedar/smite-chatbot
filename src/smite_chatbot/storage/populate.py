import logging
import json
import argparse
from pathlib import Path
from typing import List
from datetime import datetime

from .hybrid_store import HybridDocumentStore
from ..processors.base import Document

logger = logging.getLogger(__name__)


class StoragePopulator:
    """Populates storage systems with processed documents."""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.hybrid_store = HybridDocumentStore(storage_dir)
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for population process."""
        log_file = self.storage_dir / f"population_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        logger.info(f"Storage population session started")
        logger.info(f"Storage directory: {self.storage_dir}")
    
    def load_documents_from_json(self, json_file: Path) -> List[Document]:
        """Load documents from processed JSON file."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            documents = []
            for doc_data in data:
                doc = Document(
                    id=doc_data['id'],
                    type=doc_data['type'],
                    name=doc_data['name'],
                    content=doc_data['content'],
                    metadata=doc_data['metadata'],
                    source_url=doc_data.get('source_url')
                )
                documents.append(doc)
            
            logger.info(f"Loaded {len(documents)} documents from {json_file}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to load documents from {json_file}: {e}")
            return []
    
    def populate_from_processed_data(self, processed_data_dir: Path) -> dict:
        """Populate storage from a directory of processed JSON files."""
        processed_data_dir = Path(processed_data_dir)
        
        if not processed_data_dir.exists():
            raise FileNotFoundError(f"Processed data directory not found: {processed_data_dir}")
        
        results = {
            'files_processed': [],
            'total_documents': 0,
            'successful_documents': 0,
            'errors': []
        }
        
        # Look for the main combined file first
        combined_file = processed_data_dir / "all_documents.json"
        if combined_file.exists():
            logger.info("Found combined document file, using that")
            documents = self.load_documents_from_json(combined_file)
            
            if documents:
                success_count, total_count = self.hybrid_store.add_documents(documents)
                results['files_processed'].append(combined_file.name)
                results['total_documents'] = total_count
                results['successful_documents'] = success_count
            
        else:
            # Process individual files
            json_files = list(processed_data_dir.glob("*_processed.json"))
            
            if not json_files:
                logger.warning(f"No processed JSON files found in {processed_data_dir}")
                return results
            
            logger.info(f"Found {len(json_files)} processed files to load")
            
            all_documents = []
            for json_file in json_files:
                logger.info(f"Processing {json_file.name}")
                documents = self.load_documents_from_json(json_file)
                all_documents.extend(documents)
                results['files_processed'].append(json_file.name)
            
            if all_documents:
                logger.info(f"Adding {len(all_documents)} total documents to storage")
                success_count, total_count = self.hybrid_store.add_documents(all_documents)
                results['total_documents'] = total_count
                results['successful_documents'] = success_count
        
        return results
    
    def populate_specific_type(self, processed_data_dir: Path, doc_type: str) -> dict:
        """Populate storage with documents of a specific type."""
        processed_data_dir = Path(processed_data_dir)
        
        # Map document types to expected filenames
        type_files = {
            'gods': ['gods_processed.json'],
            'abilities': ['abilities_processed.json'],
            'items': ['items_processed.json'],
            'patches': ['patches_processed.json'],
            'god_changes': ['god_changes_processed.json']
        }
        
        if doc_type not in type_files:
            raise ValueError(f"Unknown document type: {doc_type}")
        
        results = {
            'type': doc_type,
            'files_processed': [],
            'total_documents': 0,
            'successful_documents': 0
        }
        
        # Clear existing documents of this type
        logger.info(f"Clearing existing {doc_type} documents")
        self.hybrid_store.delete_by_type(doc_type)
        
        # Load new documents
        all_documents = []
        for filename in type_files[doc_type]:
            file_path = processed_data_dir / filename
            if file_path.exists():
                documents = self.load_documents_from_json(file_path)
                all_documents.extend(documents)
                results['files_processed'].append(filename)
        
        if all_documents:
            success_count, total_count = self.hybrid_store.add_documents(all_documents)
            results['total_documents'] = total_count
            results['successful_documents'] = success_count
        
        return results
    
    def get_population_stats(self) -> dict:
        """Get statistics about the populated storage."""
        return self.hybrid_store.get_stats()
    
    def verify_population(self) -> dict:
        """Verify that population was successful."""
        stats = self.hybrid_store.get_stats()
        
        verification = {
            'database_healthy': stats['database'].get('total_documents', 0) > 0,
            'vector_store_healthy': stats['vector_store'].get('total_documents', 0) > 0,
            'stores_in_sync': stats['sync_status'].get('in_sync', False),
            'total_documents': stats['database'].get('total_documents', 0),
            'document_types': stats['database'].get('by_type', {}),
            'recommendations': []
        }
        
        # Add recommendations
        if not verification['stores_in_sync']:
            verification['recommendations'].append("Run sync_stores() to synchronize databases")
        
        if verification['total_documents'] == 0:
            verification['recommendations'].append("No documents found - check processed data files")
        
        if verification['total_documents'] < 500:
            verification['recommendations'].append("Document count seems low - verify all data was processed")
        
        return verification


def main():
    """CLI entry point for populating storage."""
    parser = argparse.ArgumentParser(description='Populate SMITE 2 document storage')
    parser.add_argument('processed_data_dir', help='Directory containing processed JSON files')
    parser.add_argument('--storage-dir', '-s', help='Storage directory for databases', 
                       default='./storage')
    parser.add_argument('--type', '-t', 
                       choices=['gods', 'abilities', 'items', 'patches', 'god_changes'],
                       help='Populate specific document type only')
    parser.add_argument('--clear-all', action='store_true', 
                       help='Clear all existing data before populating')
    parser.add_argument('--verify', action='store_true', 
                       help='Verify population after completion')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create populator
        populator = StoragePopulator(Path(args.storage_dir))
        
        # Clear existing data if requested
        if args.clear_all:
            logger.info("Clearing all existing data")
            populator.hybrid_store.clear_all()
        
        # Populate storage
        if args.type:
            logger.info(f"Populating {args.type} documents only")
            results = populator.populate_specific_type(Path(args.processed_data_dir), args.type)
        else:
            logger.info("Populating all document types")
            results = populator.populate_from_processed_data(Path(args.processed_data_dir))
        
        # Print results
        print(f"\n{'='*60}")
        print("POPULATION RESULTS")
        print(f"{'='*60}")
        print(f"Files processed: {', '.join(results['files_processed'])}")
        print(f"Total documents: {results['total_documents']}")
        print(f"Successfully stored: {results['successful_documents']}")
        print(f"Success rate: {results['successful_documents']/results['total_documents']*100:.1f}%")
        
        # Get final stats
        stats = populator.get_population_stats()
        print(f"\nFinal storage stats:")
        print(f"Database documents: {stats['database'].get('total_documents', 0)}")
        print(f"Vector store documents: {stats['vector_store'].get('total_documents', 0)}")
        print(f"Stores in sync: {stats['sync_status'].get('in_sync', False)}")
        
        # Verify if requested
        if args.verify:
            print(f"\n{'='*60}")
            print("VERIFICATION RESULTS")
            print(f"{'='*60}")
            
            verification = populator.verify_population()
            print(f"Database healthy: {verification['database_healthy']}")
            print(f"Vector store healthy: {verification['vector_store_healthy']}")
            print(f"Stores synchronized: {verification['stores_in_sync']}")
            
            if verification['document_types']:
                print(f"\nDocument breakdown:")
                for doc_type, count in verification['document_types'].items():
                    print(f"  {doc_type}: {count}")
            
            if verification['recommendations']:
                print(f"\nRecommendations:")
                for rec in verification['recommendations']:
                    print(f"  - {rec}")
        
        logger.info("Population completed successfully!")
        
    except Exception as e:
        logger.error(f"Population failed: {e}")
        raise


if __name__ == '__main__':
    main()