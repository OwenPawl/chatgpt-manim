"""Create private local credentials without printing them or overwriting existing config."""

from pathlib import Path
import os, secrets

p = Path(".env")
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as f:
    f.write(
        "MANIM_BASE_URL=http://127.0.0.1:8787\nMANIM_API_KEY="
        + secrets.token_urlsafe(36)
        + "\nMANIM_SIGNING_KEY="
        + secrets.token_urlsafe(36)
        + "\n"
    )
print("Created .env with mode 0600. No secrets printed.")
