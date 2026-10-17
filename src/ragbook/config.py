import os
import yaml


def load_chapter(config_path, chapter_key):
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if chapter_key not in config["chapters"]:
        raise ValueError(f"Chapter '{chapter_key}' not found in {config_path}")
    info = dict(config["chapters"][chapter_key])
    info.setdefault(
        "output_dir", os.path.join(
            "data", "processed", f"chapter_{info['id']:02d}")
    )
    return info
