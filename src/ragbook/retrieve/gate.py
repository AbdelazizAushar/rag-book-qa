GATE_THRESHOLD = 1.1


def check_relevance(retrieved_chunks, threshold=GATE_THRESHOLD):
    if not retrieved_chunks:
        return False
    return retrieved_chunks[0]["score"] <= threshold