import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from ragbook.retrieve.retriever import Retriever
from ragbook.retrieve.gate import check_relevance
from ragbook.generate.prompts import SYSTEM_PROMPT, format_context

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

class AnswerGenerator:
    def __init__(self, index_dir):
        self.retriever = Retriever(index_dir)

    def generate_answer(self, question):
        retrieved_chunks = self.retriever.search(question, top_k=3)

        is_relevant = check_relevance(retrieved_chunks)
        
        images = set()
        sources = set()
        for chunk in retrieved_chunks:
            for img in chunk.get('images', []):
                images.add(img)
            sources.add(chunk['page'])

        if not is_relevant:
            return {
                "answer": "I can't find the answer to that in this chapter of the book. Maybe we can look at topics like variables or arrays instead!",
                "sources": [],
                "images": []
            }

        context_text = format_context(retrieved_chunks)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}
        ]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="openrouter/free",
                    messages=messages,
                    temperature=0.1, 
                )
                answer_text = response.choices[0].message.content
                
                return {
                    "answer": answer_text,
                    "sources": list(sources),
                    "images": list(images),
                    "chunks": retrieved_chunks
                }
            except Exception as e:
                if attempt == max_retries - 1:
                    return {
                        "answer": f"Oops! I had trouble connecting to my brain. Error: {str(e)}",
                        "sources": [],
                        "images": []
                    }
                time.sleep(2 ** attempt) 

if __name__ == "__main__":
    generator = AnswerGenerator("data/processed/chapter_06")
    result = generator.generate_answer("What is an array?")
    print("\n--- Answer ---")
    print(result["answer"])
    print("\n--- Sources ---")
    print(result["sources"])
    print("\n--- Images ---")
    print(result["images"])