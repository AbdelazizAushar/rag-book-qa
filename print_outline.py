import json

with open("data/processed/chapter_06/chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        print(c["page"], "|", c["heading"], "|", c["text"][:90].replace("\n", " "))