from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel


class UserSecrets(BaseModel):
    """User-specific secrets configuration."""
    google_drive_credentials: Optional[Dict[str, Any]] = None
    google_drive_user: Optional[str] = None  # human-readable Google account email/name


class UserSettings(BaseModel):
    """User-specific non-secret settings."""
    human_name: str = "Ben Mowery"
    google_drive_resume_path: str = "My Drive/J/Resume"


@dataclass
class UserProfile:
    name: str
    path: Path
    secrets: UserSecrets


def get_user_profiles_root() -> Path:
    """Get the root directory for user profiles."""
    # Use project root directory (parent of src/)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "user_profiles"


def _secrets_path(profile_path: Path) -> Path:
    return profile_path / "secrets.json"


def _settings_path(profile_path: Path) -> Path:
    return profile_path / "settings.json"


def _load_secrets_from_path(profile_path: Path) -> UserSecrets:
    secrets_file = _secrets_path(profile_path)
    if secrets_file.exists():
        try:
            with open(secrets_file, 'r') as f:
                data = json.load(f)
                return UserSecrets(**data)
        except Exception:
            pass
    return UserSecrets()


def _load_settings_from_path(profile_path: Path) -> UserSettings:
    settings_file = _settings_path(profile_path)
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                data = json.load(f)
                return UserSettings(**data)
        except Exception:
            pass
    # Create defaults if missing
    settings = UserSettings()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_file, 'w') as f:
        json.dump(settings.model_dump(), f, indent=2)
    return settings


def discover_user_profiles() -> list[UserProfile]:
    """Discover all available user profiles."""
    root = get_user_profiles_root()
    if not root.exists():
        return []
    
    profiles = []
    for item in root.iterdir():
        if item.is_dir():
            secrets = _load_secrets_from_path(item)
            profile = UserProfile(
                name=item.name,
                path=item,
                secrets=secrets,
            )
            profiles.append(profile)
    
    return profiles


def find_user_profile_by_name(name: str) -> Optional[UserProfile]:
    """Find a user profile by name."""
    name_norm = name.strip().lower()
    for profile in discover_user_profiles():
        if profile.name.lower() == name_norm:
            return profile
    return None


def create_user_profile(name: str) -> UserProfile:
    """Create a new user profile."""
    root = get_user_profiles_root()
    profile_path = root / name
    
    if profile_path.exists():
        raise ValueError(f"User profile '{name}' already exists")
    
    # Create profile directory
    profile_path.mkdir(parents=True, exist_ok=True)
    
    # Create initial secrets file
    secrets = UserSecrets()
    with open(_secrets_path(profile_path), 'w') as f:
        json.dump(secrets.model_dump(), f, indent=2)

    # Create initial settings file with defaults
    _load_settings_from_path(profile_path)
    
    return UserProfile(
        name=name,
        path=profile_path,
        secrets=secrets
    )


def update_user_secrets(profile: UserProfile, secrets: UserSecrets) -> None:
    """Update the secrets for a user profile."""
    secrets_file = _secrets_path(profile.path)
    with open(secrets_file, 'w') as f:
        json.dump(secrets.model_dump(), f, indent=2)
    profile.secrets = secrets


def load_user_settings(profile: UserProfile) -> UserSettings:
    return _load_settings_from_path(profile.path)


def save_user_settings(profile: UserProfile, settings: UserSettings) -> None:
    settings_file = _settings_path(profile.path)
    with open(settings_file, 'w') as f:
        json.dump(settings.model_dump(), f, indent=2)


def get_user_profile_path(profile_name: str) -> Path:
    """Get the path for a user profile, creating it if it doesn't exist."""
    profile = find_user_profile_by_name(profile_name)
    if profile:
        return profile.path
    
    # Create the profile if it doesn't exist
    profile = create_user_profile(profile_name)
    return profile.path

