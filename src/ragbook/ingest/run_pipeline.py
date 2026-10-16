from ragbook.ingest.images import extract_and_link_images
from ragbook.index.embed import build_index
from ragbook.ingest.chunk import chunk_data
from ragbook.ingest.clean import clean_extracted_data
from ragbook.ingest.extract import extract_chapter
import argparse
import yaml
import os
import sys

sys.path.append(os.path.abspath('src'))


def run_chapter_pipeline(pdf_path, config_path, chapter_key):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if chapter_key not in config['chapters']:
        raise ValueError(f"Chapter '{chapter_key}' not found in {config_path}")

    output_dir = config['chapters'][chapter_key].get(
        'output_dir', f"data/processed/{chapter_key}"
    )
    os.makedirs(output_dir, exist_ok=True)

    raw_json = os.path.join(output_dir, "raw_extracted.json")
    cleaned_json = os.path.join(output_dir, "cleaned_data.json")
    chunks_jsonl = os.path.join(output_dir, "chunks.jsonl")

    print(f"=== Running Pipeline for {chapter_key} -> {output_dir} ===")

    extract_chapter(pdf_path, config_path, chapter_key, raw_json)

    clean_extracted_data(raw_json, cleaned_json)

    chunk_data(cleaned_json, chunks_jsonl)

    build_index(chunks_jsonl, output_dir)

    extract_and_link_images(pdf_path, config_path, chapter_key, output_dir)

    print(f"=== Pipeline Complete for {chapter_key}! ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run RAG ingestion pipeline for a book chapter.")
    parser.add_argument("--pdf", default="data/file.pdf",
                        help="Path to input PDF")
    parser.add_argument(
        "--config", default="config/chapters.yaml", help="Path to chapters YAML")
    parser.add_argument("--chapter", default="chapter_6",
                        help="Chapter key in config/chapters.yaml")
    args = parser.parse_args()

    run_chapter_pipeline(args.pdf, args.config, args.chapter)
