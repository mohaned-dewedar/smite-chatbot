from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self,model=None):
        self.model = model or self._get_default_model()
    def _get_default_model(self)
            model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            return lambda texts: model.encode(texts, show_progress_bar=False, convert_to_numpy=True)

    def embed(self,docs):

if __name__ == '__main__':

    pass