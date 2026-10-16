import pymupdf as fitz
import yaml
import json
import os


def extract_and_link_images(pdf_path, config_path, chapter_key, processed_dir):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    chapter_info = config['chapters'][chapter_key]
    start_page = chapter_info['start_page'] - 1
    end_page = chapter_info['end_page'] - 1

    images_dir = os.path.join(processed_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    page_images_map = {}

    print("Extracting images...")
    for page_num in range(start_page, end_page + 1):
        if page_num >= len(doc):
            break

        page = doc[page_num]
        actual_page_num = page_num + 1
        page_images_map[actual_page_num] = []

        image_list = page.get_images(full=True)
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            image_filename = f"page_{actual_page_num}_img_{img_index + 1}.{image_ext}"
            image_path = os.path.join(images_dir, image_filename)

            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)

            page_images_map[actual_page_num].append(f"images/{image_filename}")

    metadata_path = os.path.join(processed_dir, "metadata.json")
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    for chunk in metadata:
        chunk_page = chunk.get("page")
        chunk["images"] = page_images_map.get(chunk_page, [])

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    manifest = {
        "chapter_id": chapter_info['id'],
        "title": chapter_info['title'],
        "status": "ingested",
        "total_chunks": len(metadata),
        "total_images": sum(len(imgs) for imgs in page_images_map.values())
    }
    with open(os.path.join(processed_dir, "manifest.json"), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Extracted {manifest['total_images']} images.")
    print("Metadata updated and manifest.json created.")


if __name__ == "__main__":
    extract_and_link_images(
        "data/file.pdf",
        "config/chapters.yaml",
        "chapter_6",
        "data/processed/chapter_06"
    )
