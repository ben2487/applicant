from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import platform
import os


@dataclass
class BrowserProfile:
    name: str  # "Person 1" / custom label
    dir_name: str  # "Default", "Profile 1", ...
    user_data_root: Path  # root dir that contains profile folders
    path: Path  # user_data_root / dir_name
    email: str | None = None
    is_default: bool = False


def _candidate_roots() -> list[Path]:
    sys = platform.system()
    home = Path.home()
    roots: list[Path] = []
    if sys == "Darwin":  # macOS
        roots += [home / "Library/Application Support/Google/Chrome"]
    elif sys == "Windows":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            roots += [Path(local) / r"Google/Chrome/User Data"]
    else:  # Linux / other
        roots += [home / ".config/google-chrome", home / ".config/chromium"]
    return [r for r in roots if r.exists()]


def discover_browser_profiles() -> list[BrowserProfile]:
    found: list[BrowserProfile] = []
    for root in _candidate_roots():
        local_state = root / "Local State"
        if not local_state.exists():
            continue
        try:
            data = json.loads(local_state.read_text(encoding="utf-8"))
        except Exception:
            continue
        info_cache = (data.get("profile") or {}).get("info_cache") or {}
        last_used = (data.get("profile") or {}).get("last_used")  # e.g. "Default"
        for dir_name, meta in info_cache.items():
            name = meta.get("name") or dir_name
            email = (
                meta.get("gaia_name")
                or meta.get("user_name")
                or meta.get("gaia_given_name")
                or meta.get("gaia_email")
            )
            prof = BrowserProfile(
                name=name,
                dir_name=dir_name,
                user_data_root=root,
                path=root / dir_name,
                email=email,
                is_default=(dir_name == "Default" or dir_name == last_used),
            )
            found.append(prof)
    return found


def find_browser_profile_by_name_or_dir(q: str) -> BrowserProfile | None:
    qnorm = q.strip().lower()
    for p in discover_browser_profiles():
        if p.dir_name.lower() == qnorm or p.name.lower() == qnorm:
            return p
    return None
