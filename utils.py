# app/utils.py
import re

def safe_filename(name: str) -> str:
    """Convert string to safe filename."""
    name = name.strip()
    name = re.sub(r"[^A-Za-z0-9 _-]+", "", name)
    name = re.sub(r"\s+", "_", name)
    return name or "resume"