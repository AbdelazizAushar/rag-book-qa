import json
import os

def clean_extracted_data(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_pages = json.load(f)

    cleaned_pages = []
    for page in raw_pages:
        cleaned_blocks = []
        for block in page.get("text_blocks", []):
            if len(block) >= 7 and block[6] == 0:
                text = block[4].strip()
                if text:
                    text = " ".join(text.split())
                    cleaned_blocks.append(text)
        
        cleaned_pages.append({
            "page_number": page["page_number"],
            "blocks": cleaned_blocks,
            "image_count": page.get("image_count", 0)
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_pages, f, indent=2, ensure_ascii=False)
    print(f"Cleaned data saved to {output_file}")

if __name__ == "__main__":
    clean_extracted_data(
        "data/processed/chapter_06/raw_extraction.json", 
        "data/processed/chapter_06/cleaned_data.json"
    )