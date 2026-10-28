"""Read local private environment and start service; no values printed."""

from pathlib import Path
import os

if Path(".env").exists():
    for line in Path(".env").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)
from chatgpt_manim.server import main

main()
