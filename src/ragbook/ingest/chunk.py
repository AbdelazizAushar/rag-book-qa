import json
import re

MAX_WORDS = 150
MIN_WORDS = 30
MAX_HEADING_WORDS = 8
MAX_HEADING_CHARS = 80


def _n_words(text):
    return len(text.split())


def looks_like_heading(block):
    return (
        _n_words(block) <= MAX_HEADING_WORDS
        and len(block) <= MAX_HEADING_CHARS
        and not re.search(r"[.;,:]$", block)
    )


def chunk_data(input_file, output_file, default_heading="Introduction"):
    with open(input_file, "r", encoding="utf-8") as f:
        pages = json.load(f)

    chunks = []
    heading = default_heading

    def add_chunk(text, page_num, chunk_heading):
        text = text.strip()
        if text:
            chunks.append({"text": text, "page": page_num,
                          "heading": chunk_heading})

    for page in pages:
        page_num = page["page_number"]
        first_chunk_of_page = len(chunks)
        current = ""
        current_heading = heading

        for block in page["blocks"]:
            if looks_like_heading(block):
                if _n_words(current) >= MIN_WORDS:
                    add_chunk(current, page_num, current_heading)
                    current = ""
                    heading = current_heading = block
                elif not current:
                    heading = current_heading = block

            current += block + " "

            if _n_words(current) >= MAX_WORDS:
                add_chunk(current, page_num, current_heading)
                current = ""
                current_heading = heading

        if current.strip():
            if _n_words(current) < MIN_WORDS and len(chunks) > first_chunk_of_page:
                chunks[-1]["text"] += " " + current.strip()
            else:
                add_chunk(current, page_num, current_heading)

    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Created {len(chunks)} chunks, saved to {output_file}")
    return chunks
