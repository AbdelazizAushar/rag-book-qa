import pymupdf
import yaml
import os
import json


def extract_chapter(pdf_path, config_path, chapter_key):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    chapter_info = config['chapters'][chapter_key]
    start_page = chapter_info['start_page'] - 1
    end_page = chapter_info['end_page'] - 1

    output_dir = f"data/processed/chapter_{chapter_info['id']:02d}"
    os.makedirs(output_dir, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    raw_pages = []

    for page_num in range(start_page, end_page + 1):
        if page_num >= len(doc):
            break

        page = doc[page_num]

        text_blocks = page.get_text("blocks")

        images = page.get_images(full=True)

        raw_pages.append({
            "page_number": page_num + 1,
            "text_blocks": text_blocks,
            "image_count": len(images)
        })

    output_file = os.path.join(output_dir, "raw_extraction.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(raw_pages, f, indent=2, ensure_ascii=False)

    print(
        f"Extraction complete! Saved raw data for {len(raw_pages)} pages to {output_file}")


if __name__ == "__main__":
    extract_chapter("data/file.pdf", "config/chapters.yaml", "chapter_6")
