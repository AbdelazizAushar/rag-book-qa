import os
import time

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, OpenAI

from ragbook.generate.prompts import NOT_FOUND_ANSWER, SYSTEM_PROMPT, format_context
from ragbook.retrieve.gate import check_relevance
from ragbook.retrieve.retriever import TOP_K, Retriever

load_dotenv()

BASE_URL = "https://openrouter.ai/api/v1"
REQUEST_TIMEOUT = 45.0 
MAX_ATTEMPTS = 3
TEMPERATURE = 0.1
MAX_TOKENS = 400


class _EmptyResponse(Exception):
    """OpenRouter sometimes answers HTTP 200 with no choices."""


def _is_retryable(exc):
    if isinstance(exc, (APIConnectionError, _EmptyResponse)): 
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in (408, 409, 429) or exc.status_code >= 500
    return False 


def _friendly_error(exc):
    status = getattr(exc, "status_code", None)
    if status in (401, 403):
        return ("I can't reach my AI helper because the API key was rejected. "
                "Please check OPENROUTER_API_KEY in the .env file.")
    if status == 404:
        return ("The AI model I was asked to use was not found. "
                "Please check OPENROUTER_MODEL in the .env file.")
    if status == 429:
        return "The free AI model is very busy right now. Please wait a minute and try again."
    if isinstance(exc, APIConnectionError):
        return "I couldn't reach the AI service. Please check the internet connection and try again."
    return "Something went wrong while I was thinking. Please try again."


class AnswerGenerator:
    def __init__(self, index_dir, page_offset=0):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        self.model = os.environ.get("OPENROUTER_MODEL")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key.")
        if not self.model:
            raise RuntimeError(
                "OPENROUTER_MODEL is not set. Add it to your .env file (see .env.example).")
        self.client = OpenAI(base_url=BASE_URL, api_key=api_key,
                             timeout=REQUEST_TIMEOUT, max_retries=0)
        self.retriever = Retriever(index_dir)
        self.page_offset = page_offset 

    def _with_printed_pages(self, chunks):
        out = []
        for chunk in chunks:
            chunk = dict(chunk)
            chunk["printed_page"] = chunk["page"] - self.page_offset
            out.append(chunk)
        return out

    @staticmethod
    def _result(status, answer, chunks, sources=None, images=None):
        return {"status": status, "answer": answer, "sources": sources or [],
                "images": images or [], "chunks": chunks}

    def _ask_llm(self, messages):
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages,
                    temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
                if not response.choices:
                    raise _EmptyResponse()
                text = (response.choices[0].message.content or "").strip()
                if not text:
                    raise _EmptyResponse()
                return text
            except Exception as exc:
                if not _is_retryable(exc) or attempt == MAX_ATTEMPTS - 1:
                    raise
                time.sleep(2 ** attempt)

    def generate_answer(self, question):
        try:
            chunks = self._with_printed_pages(
                self.retriever.search(question, top_k=TOP_K))
        except Exception as exc:
            return self._result("error", f"I couldn't search the book: {exc}", [])

        if not check_relevance(chunks):
            return self._result("refused_by_gate", NOT_FOUND_ANSWER, chunks)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": f"Context:\n{format_context(chunks)}\n\nQuestion: {question}"},
        ]
        try:
            text = self._ask_llm(messages)
        except Exception as exc:
            return self._result("error", _friendly_error(exc), chunks)

        if text.startswith(NOT_FOUND_ANSWER):
            return self._result("refused_by_model", text, chunks)

        sources = sorted({c["printed_page"] for c in chunks})
        images = list(dict.fromkeys(
            img for c in chunks for img in c.get("images", [])))
        return self._result("answered", text, chunks, sources, images)


if __name__ == "__main__":
    import sys

    import yaml

    chapter = sys.argv[1] if len(sys.argv) > 1 else "chapter_6"
    question = sys.argv[2] if len(sys.argv) > 2 else "What is an array?"
    with open("config/chapters.yaml", encoding="utf-8") as f:
        info = yaml.safe_load(f)["chapters"][chapter]
    generator = AnswerGenerator(info["output_dir"], info.get("page_offset", 0))
    result = generator.generate_answer(question)
    print(f"\n--- Status: {result['status']} ---")
    print(result["answer"])
    print("\n--- Sources (printed pages) ---")
    print(result["sources"])
    print("\n--- Images ---")
    print(result["images"])