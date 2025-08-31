from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os


class Settings(BaseModel):
    openai_api_key: str | None = None


def repo_root() -> Path:
    # Walk up from this file until we see a pyproject.toml or .git
    p = Path(__file__).resolve()
    for ancestor in [p, *p.parents]:
        if (ancestor / "pyproject.toml").exists() or (ancestor / ".git").exists():
            return ancestor
    return Path.cwd()


def load_settings() -> Settings:
    # Prefer a .env at the repo root
    env_path = repo_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    return Settings(openai_api_key=os.getenv("OPENAI_API_KEY"))
