import chromadb
from chromadb.config import Settings

class VectorStore:
    def __init__(self, collection_name="my_collection"):
        self.client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=".chromadb"))
        self.collection_name = collection_name
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        try:
            return self.client.get_collection(self.collection_name)
        except:
            return self.client.create_collection(self.collection_name)

    def add_documents(self, docs, ids):
        self.collection.add(documents=docs, ids=ids)

    def query(self, text, k=2):
        return self.collection.query(query_texts=[text], n_results=k)
