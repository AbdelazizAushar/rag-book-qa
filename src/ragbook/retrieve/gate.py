def check_relevance(retrieved_chunks, threshold=1.5):
    if not retrieved_chunks:
        return False
        
    best_score = retrieved_chunks[0]['score']
    
    if best_score > threshold:
        return False
        
    return True