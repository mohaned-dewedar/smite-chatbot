import logging
from pathlib import Path
from typing import List, Optional
import argparse
from datetime import datetime

from .gods import GodsProcessor
from .items import ItemsProcessor
from .patches import PatchProcessor
from .base import Document

logger = logging.getLogger(__name__)


class DataProcessingOrchestrator:
    """Orchestrates data processing from scraped JSON to processed documents."""
    
    def __init__(self, data_dir: Path, output_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir)
        self.output_dir = output_dir or (self.data_dir / "processed")
        
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging for the processing session."""
        log_file = self.output_dir / f"processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        logger.info(f"Starting data processing session")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Output directory: {self.output_dir}")
    
    def process_all(self) -> List[Document]:
        """Process all available data files."""
        all_documents = []
        
        # Process gods data
        gods_file = self.data_dir / "gods.json"
        if gods_file.exists():
            logger.info("Processing gods data...")
            try:
                processor = GodsProcessor(gods_file, self.output_dir)
                documents = processor.run()
                all_documents.extend(documents)
                logger.info(f"✓ Gods processing completed: {len(documents)} documents")
            except Exception as e:
                logger.error(f"✗ Gods processing failed: {e}")
        else:
            logger.warning(f"Gods file not found: {gods_file}")
        
        # Process items data
        items_file = self.data_dir / "items.json"
        if items_file.exists():
            logger.info("Processing items data...")
            try:
                processor = ItemsProcessor(items_file, self.output_dir)
                documents = processor.run()
                all_documents.extend(documents)
                logger.info(f"✓ Items processing completed: {len(documents)} documents")
            except Exception as e:
                logger.error(f"✗ Items processing failed: {e}")
        else:
            logger.warning(f"Items file not found: {items_file}")
        
        # Process patch data
        patches_file = self.data_dir / "patch_details.json"
        if patches_file.exists():
            logger.info("Processing patches data...")
            try:
                processor = PatchProcessor(patches_file, self.output_dir)
                documents = processor.run()
                all_documents.extend(documents)
                logger.info(f"✓ Patches processing completed: {len(documents)} documents")
            except Exception as e:
                logger.error(f"✗ Patches processing failed: {e}")
        else:
            logger.warning(f"Patches file not found: {patches_file}")
        
        # Save combined output
        if all_documents:
            combined_file = self.output_dir / "all_documents.json"
            try:
                import json
                with open(combined_file, 'w', encoding='utf-8') as f:
                    json.dump([doc.to_dict() for doc in all_documents], f, indent=2)
                logger.info(f"✓ Saved {len(all_documents)} total documents to {combined_file}")
            except Exception as e:
                logger.error(f"✗ Failed to save combined documents: {e}")
        
        return all_documents
    
    def process_specific(self, data_type: str) -> List[Document]:
        """Process a specific data type."""
        documents = []
        
        if data_type.lower() == 'gods':
            file_path = self.data_dir / "gods.json"
            processor_class = GodsProcessor
        elif data_type.lower() == 'items':
            file_path = self.data_dir / "items.json" 
            processor_class = ItemsProcessor
        elif data_type.lower() == 'patches':
            file_path = self.data_dir / "patch_details.json"
            processor_class = PatchProcessor
        else:
            logger.error(f"Unknown data type: {data_type}")
            return documents
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return documents
        
        try:
            processor = processor_class(file_path, self.output_dir)
            documents = processor.run()
            logger.info(f"✓ {data_type.title()} processing completed: {len(documents)} documents")
        except Exception as e:
            logger.error(f"✗ {data_type.title()} processing failed: {e}")
        
        return documents
    
    def get_processing_summary(self) -> dict:
        """Get summary of processed data."""
        summary = {
            'output_directory': str(self.output_dir),
            'files_created': [],
            'total_documents': 0
        }
        
        # Check for output files
        output_files = list(self.output_dir.glob('*_processed.json'))
        output_files.extend(self.output_dir.glob('all_documents.json'))
        
        for file_path in output_files:
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    doc_count = len(data) if isinstance(data, list) else 0
                    
                summary['files_created'].append({
                    'file': file_path.name,
                    'documents': doc_count
                })
                
                if 'all_documents' not in file_path.name:
                    summary['total_documents'] += doc_count
                    
            except Exception as e:
                logger.error(f"Failed to read summary from {file_path}: {e}")
        
        return summary


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Process SMITE 2 scraped data')
    parser.add_argument('data_dir', help='Directory containing scraped JSON files')
    parser.add_argument('--output', '-o', help='Output directory (default: data_dir/processed)')
    parser.add_argument('--type', '-t', choices=['gods', 'items', 'patches'], 
                       help='Process specific data type only')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create orchestrator
        output_dir = Path(args.output) if args.output else None
        orchestrator = DataProcessingOrchestrator(args.data_dir, output_dir)
        
        # Process data
        if args.type:
            documents = orchestrator.process_specific(args.type)
        else:
            documents = orchestrator.process_all()
        
        # Print summary
        summary = orchestrator.get_processing_summary()
        print(f"\n{'='*50}")
        print("PROCESSING SUMMARY")
        print(f"{'='*50}")
        print(f"Output directory: {summary['output_directory']}")
        print(f"Total documents: {summary['total_documents']}")
        print("\nFiles created:")
        for file_info in summary['files_created']:
            print(f"  - {file_info['file']}: {file_info['documents']} documents")
        
        logger.info("Data processing completed successfully!")
        
    except Exception as e:
        logger.error(f"Data processing failed: {e}")
        raise


if __name__ == '__main__':
    main()