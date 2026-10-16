import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class Retriever:
    def __init__(self, index_dir="data/processed/chapter_06"):
        self.index_dir = index_dir
        self.index_path = os.path.join(index_dir, "faiss_index.bin")
        self.metadata_path = os.path.join(index_dir, "metadata.json")

        self.model = SentenceTransformer('all-MiniLM-L6-v2')

        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            raise FileNotFoundError(f"Index not found at {self.index_path}")

        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            raise FileNotFoundError(
                f"Metadata not found at {self.metadata_path}")

    def search(self, query, top_k=3):
        query_vector = self.model.encode([query])
        query_vector = np.array(query_vector).astype('float32')

        distances, indices = self.index.search(query_vector, top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                chunk_data = self.metadata[idx].copy()
                chunk_data['score'] = float(distances[0][i])
                results.append(chunk_data)

        return results


if __name__ == "__main__":
    retriever = Retriever()
    res = retriever.search("What is an array?")
    print(json.dumps(res, indent=2))
