import json
import math
import re
from collections import Counter

PAGE_NUMBER = re.compile(r"^\d{1,4}$")
ARROWS = re.compile(r"[‹›]")
SPACED = re.compile(r"(?:\b[A-Z]{1,2}\b\s*,?\s*){4,}")
LEADING_PAGE_NO = re.compile(r"^\d{1,3}\s+(?=[A-Z][a-z])")
HEADER_ZONE = 3


def _normalize(text):
    return re.sub(r"\d+", "#", text.lower())


def clean_extracted_data(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        raw_pages = json.load(f)

    pages = []
    for page in raw_pages:
        blocks = []
        text_blocks = [b for b in page.get(
            "text_blocks", []) if len(b) >= 7 and b[6] == 0]
        for i, block in enumerate(text_blocks):
            text = " ".join(block[4].split())
            if not text or ARROWS.search(text):
                continue
            text = " ".join(SPACED.sub(" ", text).split())
            if i < HEADER_ZONE:
                text = LEADING_PAGE_NO.sub("", text)
            if not text or PAGE_NUMBER.match(text):
                continue
            blocks.append(text)
        pages.append((page, blocks))

    counts = Counter()
    for _, blocks in pages:
        counts.update({_normalize(b) for b in blocks if len(b.split()) <= 8})
    min_repeats = max(3, math.ceil(0.4 * len(pages)))
    repeated = {t for t, c in counts.items() if c >= min_repeats}

    cleaned_pages = []
    for page, blocks in pages:
        kept = [b for b in blocks if _normalize(b) not in repeated]
        cleaned_pages.append({
            "page_number": page["page_number"],
            "blocks": kept,
            "image_count": page.get("image_count", 0),
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_pages, f, indent=2, ensure_ascii=False)
    print(f"Cleaned data saved to {output_file}")
    if repeated:
        print("Repeated header/footer patterns removed:", sorted(repeated))
