import json


def chunk_data(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        cleaned_pages = json.load(f)

    chunks = []
    current_heading = "Chapter 6 Introduction"

    for page in cleaned_pages:
        page_num = page["page_number"]
        current_chunk_text = ""

        for block in page["blocks"]:
            if len(block.split()) < 10 and not block.endswith('.'):
                current_heading = block
                if current_chunk_text:
                    chunks.append({
                        "text": current_chunk_text.strip(),
                        "page": page_num,
                        "heading": current_heading
                    })
                    current_chunk_text = ""
                continue

            current_chunk_text += block + " "

            if len(current_chunk_text.split()) > 150:
                chunks.append({
                    "text": current_chunk_text.strip(),
                    "page": page_num,
                    "heading": current_heading
                })
                current_chunk_text = ""

        if current_chunk_text.strip():
            chunks.append({
                "text": current_chunk_text.strip(),
                "page": page_num,
                "heading": current_heading
            })

    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

    print(f"Created {len(chunks)} chunks, saved to {output_file}")


if __name__ == "__main__":
    chunk_data(
        "data/processed/chapter_06/cleaned_data.json",
        "data/processed/chapter_06/chunks.jsonl"
    )
