import json
import math
import re
from collections import Counter

PAGE_NUMBER = re.compile(r"^\d{1,4}$")


def _normalize(text):
    return re.sub(r"\d+", "#", text.lower())


def clean_extracted_data(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        raw_pages = json.load(f)

    pages = []
    for page in raw_pages:
        blocks = []
        for block in page.get("text_blocks", []):
            if len(block) >= 7 and block[6] == 0:
                text = " ".join(block[4].split())
                if text:
                    blocks.append(text)
        pages.append((page, blocks))

    counts = Counter()
    for _, blocks in pages:
        counts.update({_normalize(b) for b in blocks if len(b.split()) <= 8})
    min_repeats = max(3, math.ceil(0.4 * len(pages)))
    repeated = {t for t, c in counts.items() if c >= min_repeats}

    cleaned_pages = []
    removed = 0
    for page, blocks in pages:
        kept = [b for b in blocks
                if not PAGE_NUMBER.match(b) and _normalize(b) not in repeated]
        removed += len(blocks) - len(kept)
        cleaned_pages.append({
            "page_number": page["page_number"],
            "blocks": kept,
            "image_count": page.get("image_count", 0),
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_pages, f, indent=2, ensure_ascii=False)
    print(f"Cleaned data saved to {output_file} (removed {removed} header/footer/page-number blocks)")
    if repeated:
        print("Repeated header/footer patterns removed:", sorted(repeated))