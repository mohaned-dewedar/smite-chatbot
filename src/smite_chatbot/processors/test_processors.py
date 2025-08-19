"""
Simple test to verify processors work correctly.
Run this with: uv run python -m smite_chatbot.processors.test_processors
"""

from pathlib import Path
from .orchestrator import DataProcessingOrchestrator


def test_processors():
    """Test processors with latest scraped data."""
    # Find latest scraped data
    data_root = Path(__file__).parent.parent.parent.parent / "data"
    scrape_dirs = [d for d in data_root.glob("scrape-*") if d.is_dir()]
    
    if not scrape_dirs:
        print("No scraped data directories found!")
        return
    
    latest_dir = max(scrape_dirs, key=lambda x: x.name)
    print(f"Using data from: {latest_dir}")
    
    # Process data
    orchestrator = DataProcessingOrchestrator(latest_dir)
    documents = orchestrator.process_all()
    
    # Verify results
    print(f"\nProcessed {len(documents)} total documents")
    
    # Count by type
    doc_types = {}
    for doc in documents:
        doc_type = doc.type
        doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
    
    print("\nDocument breakdown:")
    for doc_type, count in doc_types.items():
        print(f"  {doc_type}: {count}")
    
    # Sample some documents
    print("\nSample documents:")
    for doc_type in ['god', 'ability', 'item', 'patch']:
        sample_docs = [d for d in documents if d.type == doc_type][:2]
        if sample_docs:
            print(f"\n{doc_type.upper()} examples:")
            for doc in sample_docs:
                print(f"  - {doc.name}: {doc.content[:100]}...")
    
    print(f"\n✅ Test completed successfully!")
    print(f"Output saved to: {orchestrator.output_dir}")


if __name__ == "__main__":
    test_processors()