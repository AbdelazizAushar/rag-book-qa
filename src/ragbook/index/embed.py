import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

def build_index(chunks_file, output_dir):
    chunks = []
    with open(chunks_file, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))
            
    print(f"Loaded {len(chunks)} chunks.")

    print("Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    texts = [chunk['text'] for chunk in chunks]
    print("Generating embeddings...")
    embeddings = model.encode(texts, show_progress_bar=True)
    
    embeddings = np.array(embeddings).astype('float32')
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    faiss.write_index(index, os.path.join(output_dir, "faiss_index.bin"))
    
    with open(os.path.join(output_dir, "metadata.json"), 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
        
    print(f"Index built and saved to {output_dir}/faiss_index.bin")
    print(f"Metadata saved to {output_dir}/metadata.json")

if __name__ == "__main__":
    build_index(
        "data/processed/chapter_06/chunks.jsonl",
        "data/processed/chapter_06"
    )