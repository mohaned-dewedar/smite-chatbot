#!/usr/bin/env python3
"""
Quick test script to verify storage system works correctly.
"""

from pathlib import Path
from src.smite_chatbot.storage.hybrid_store import HybridDocumentStore

def test_storage():
    """Test various storage operations."""
    
    # Initialize storage
    storage = HybridDocumentStore(Path("./storage"))
    
    print("=== STORAGE SYSTEM TEST ===\n")
    
    # Get stats
    stats = storage.get_stats()
    print("📊 STORAGE STATS:")
    print(f"Database documents: {stats['database']['total_documents']}")
    print(f"Vector store documents: {stats['vector_store']['total_documents']}")
    print(f"Stores in sync: {stats['sync_status']['in_sync']}")
    print(f"Document types: {stats['database']['by_type']}")
    print()
    
    # Test semantic search
    print("🔍 SEMANTIC SEARCH TESTS:")
    
    queries = [
        "Greek gods for solo lane",
        "Best items for lifesteal",
        "Achilles abilities",
        "Recent patch changes to Ares"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        results = storage.search(query, n_results=3, search_mode="hybrid")
        
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result['metadata']['name']} ({result['metadata']['type']}) - {result['similarity']:.3f}")
            print(f"     {result['content'][:80]}...")
    
    # Test structured search
    print("\n\n📋 STRUCTURED SEARCH TESTS:")
    
    # Get all Greek gods
    greek_gods = storage.database.search_documents(
        doc_type="god",
        metadata_filters={"pantheon": "Greek"},
        limit=5
    )
    print(f"\nGreek gods found: {len(greek_gods)}")
    for god in greek_gods[:3]:
        print(f"  - {god.name}: {god.metadata.get('role', 'Unknown role')}")
    
    # Get offensive items
    offensive_items = storage.database.search_documents(
        doc_type="item",
        metadata_filters={"category": "offensive"},
        limit=5
    )
    print(f"\nOffensive items found: {len(offensive_items)}")
    for item in offensive_items[:3]:
        print(f"  - {item.name}: {item.metadata.get('total_cost', 'Unknown cost')} gold")
    
    # Test similar documents
    print("\n🔗 SIMILARITY TEST:")
    similar = storage.get_similar_documents("god_achilles", n_results=3)
    print(f"\nDocuments similar to Achilles:")
    for result in similar:
        print(f"  - {result['metadata']['name']} ({result['metadata']['type']}) - {result['similarity']:.3f}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    test_storage()