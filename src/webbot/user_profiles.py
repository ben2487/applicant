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
    # Future: other API keys, tokens, etc.


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


def discover_user_profiles() -> list[UserProfile]:
    """Discover all available user profiles."""
    root = get_user_profiles_root()
    if not root.exists():
        return []
    
    profiles = []
    for item in root.iterdir():
        if item.is_dir():
            profile_name = item.name
            secrets_file = item / "secrets.json"
            secrets = UserSecrets()
            
            if secrets_file.exists():
                try:
                    with open(secrets_file, 'r') as f:
                        secrets_data = json.load(f)
                        secrets = UserSecrets(**secrets_data)
                except Exception:
                    # If secrets file is corrupted, use empty secrets
                    pass
            
            profile = UserProfile(
                name=profile_name,
                path=item,
                secrets=secrets
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
    secrets_file = profile_path / "secrets.json"
    with open(secrets_file, 'w') as f:
        json.dump(secrets.model_dump(), f, indent=2)
    
    return UserProfile(
        name=name,
        path=profile_path,
        secrets=secrets
    )


def update_user_secrets(profile: UserProfile, secrets: UserSecrets) -> None:
    """Update the secrets for a user profile."""
    secrets_file = profile.path / "secrets.json"
    with open(secrets_file, 'w') as f:
        json.dump(secrets.model_dump(), f, indent=2)
    profile.secrets = secrets


def get_user_profile_path(profile_name: str) -> Path:
    """Get the path for a user profile, creating it if it doesn't exist."""
    profile = find_user_profile_by_name(profile_name)
    if profile:
        return profile.path
    
    # Create the profile if it doesn't exist
    profile = create_user_profile(profile_name)
    return profile.path

