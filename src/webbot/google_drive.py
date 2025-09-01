from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import re
import os

from .user_profiles import (
    UserProfile,
    UserSecrets,
    UserSettings,
    load_user_settings,
    update_user_secrets,
)

# NOTE: We avoid importing Google client libs until needed to keep optional dependency light.


class GoogleDriveNotLinkedError(RuntimeError): ...


def _discover_client_secret_path(profile: UserProfile, client_secret_path: Optional[Path]) -> tuple[Optional[Path], Optional[dict]]:
    """Find a Google OAuth client configuration.

    Returns a tuple of (path, inline_json_dict). If inline_json_dict is not None, use it with
    InstalledAppFlow.from_client_config. If path is not None, use from_client_secrets_file.
    Search order:
    - explicit client_secret_path if provided
    - env GOOGLE_OAUTH_CLIENT_FILE
    - env GOOGLE_OAUTH_CLIENT_JSON (inline JSON)
    - user profile dir: <profile>/client_secret.json
    - project root: <repo>/client_secret.json
    - user config dir: ~/.config/webbot/client_secret.json
    """
    # 1) explicit
    if client_secret_path:
        p = Path(client_secret_path)
        if p.exists():
            return p, None
    # 2) env file
    env_file = os.environ.get("GOOGLE_OAUTH_CLIENT_FILE")
    if env_file:
        p = Path(env_file).expanduser()
        if p.exists():
            return p, None
    # 3) env inline json
    env_json = os.environ.get("GOOGLE_OAUTH_CLIENT_JSON")
    if env_json:
        try:
            data = json.loads(env_json)
            return None, data
        except Exception:
            pass
    # 4) profile dir
    prof_path = profile.path / "client_secret.json"
    if prof_path.exists():
        return prof_path, None
    # 5) repo root (parent of src)
    repo_root = Path(__file__).parent.parent.parent
    root_path = repo_root / "client_secret.json"
    if root_path.exists():
        return root_path, None
    # 6) ~/.config/webbot
    cfg_path = Path.home() / ".config/webbot/client_secret.json"
    if cfg_path.exists():
        return cfg_path, None
    return None, None


def google_drive_login(profile: UserProfile, client_secret_path: Optional[Path] = None) -> None:
    """Interactive login linking Google Drive to the given user profile.

    Stores credentials and google account identity (email) in secrets.json.
    Re-running will overwrite/update the stored credentials.
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
    except Exception as e:
        raise RuntimeError(
            "Google API libraries not installed. Add to pyproject and install: "
            "google-api-python-client, google-auth-httplib2, google-auth-oauthlib"
        ) from e

    # Scopes: read metadata and export docs
    SCOPES = [
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    # Discover client config
    secret_file, inline_config = _discover_client_secret_path(profile, client_secret_path)
    if not secret_file and not inline_config:
        raise RuntimeError(
            "No Google OAuth client credentials found. Provide with --client-secret, "
            "or set GOOGLE_OAUTH_CLIENT_FILE / GOOGLE_OAUTH_CLIENT_JSON, or place client_secret.json "
            "in the user profile dir, repo root, or ~/.config/webbot/."
        )

    if inline_config is not None:
        flow = InstalledAppFlow.from_client_config(inline_config, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)

    creds = flow.run_local_server(port=0)

    # Build drive service to fetch user info
    svc = build("drive", "v3", credentials=creds)
    about = svc.about().get(fields="user(displayName,emailAddress)").execute()
    email = (about.get("user") or {}).get("emailAddress")

    # Persist to secrets.json
    # Convert credentials to dict for persistence
    secrets = profile.secrets
    secrets.google_drive_user = email
    secrets.google_drive_credentials = {
        "token": creds.token,
        "refresh_token": getattr(creds, "refresh_token", None),
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
    }
    update_user_secrets(profile, secrets)


def _drive_service_from_secrets(profile: UserProfile):
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
    except Exception as e:
        raise RuntimeError(
            "Google API libraries not installed. Add to pyproject and install: "
            "google-api-python-client, google-auth-httplib2, google-auth-oauthlib"
        ) from e

    gd = profile.secrets.google_drive_credentials
    if not gd:
        raise GoogleDriveNotLinkedError(
            "Google Drive not linked for this profile. Run with --google-drive-login."
        )
    creds = Credentials(
        token=gd.get("token"),
        refresh_token=gd.get("refresh_token"),
        token_uri=gd.get("token_uri"),
        client_id=gd.get("client_id"),
        client_secret=gd.get("client_secret"),
        scopes=gd.get("scopes") or [],
    )
    return build("drive", "v3", credentials=creds)


def _ensure_dirs(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _export_google_doc_pdf(service, file_id: str, out_pdf: Path) -> None:
    from googleapiclient.http import MediaIoBaseDownload
    import io

    request = service.files().export_media(fileId=file_id, mimeType="application/pdf")
    _ensure_dirs(out_pdf.parent)
    with open(out_pdf, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()


def _export_google_doc_text(service, file_id: str, out_txt: Path) -> None:
    request = service.files().export(fileId=file_id, mimeType="text/plain")
    content = request.execute()
    _ensure_dirs(out_txt.parent)
    with open(out_txt, "wb") as f:
        if isinstance(content, bytes):
            f.write(content)
        else:
            f.write((content or "").encode("utf-8"))


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    _ensure_dirs(path.parent)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def refresh_resumes(profile: UserProfile) -> int:
    """Sync resumes from Google Drive to local user profile directory.

    Returns the number of matched resumes processed. Also updates the local
    resumes.json index and removes stale local copies.

    Strategy:
    - Read settings.json for human_name and google_drive_resume_path
    - Try to resolve the folder by path and list Google Docs in that folder
    - If the folder isn't found, fall back to a global Drive search
    - Filter for names starting with "[AP]", containing "Resume" and the human name (case-insensitive)
    - Download updated/new items to [profile]/resume_pdf/<base>/ as resume.pdf + resume.txt
    - Remove local copies for items no longer present
    """
    service = _drive_service_from_secrets(profile)
    settings = load_user_settings(profile)
    human_name = settings.human_name
    resume_path = settings.google_drive_resume_path

    def list_docs_in_folder(folder_id: str) -> list[dict]:
        query = (
            f"'{folder_id}' in parents and "
            "mimeType = 'application/vnd.google-apps.document' and trashed = false"
        )
        fields = "files(id,name,modifiedTime)"
        res = service.files().list(q=query, fields=fields, orderBy="modifiedTime desc").execute()
        return res.get("files", [])

    def list_docs_global() -> list[dict]:
        # Narrow with contains filters; final filtering done in Python for safety
        q = (
            "mimeType = 'application/vnd.google-apps.document' and "
            "trashed = false and "
            "name contains 'Resume'"
        )
        fields = "files(id,name,modifiedTime)"
        res = service.files().list(q=q, fields=fields, orderBy="modifiedTime desc").execute()
        return res.get("files", [])

    # Resolve the folder by path components; if missing, fallback to global search
    items: list[dict] = []
    def find_folder_id_by_path(path_str: str) -> Optional[str]:
        parts = [p for p in path_str.split("/") if p and p != "."]
        parent_id = None
        for part in parts:
            q = ["mimeType = 'application/vnd.google-apps.folder'", f"name = '{part}'"]
            if parent_id:
                q.append(f"'{parent_id}' in parents")
            res = service.files().list(q=" and ".join(q), spaces="drive", fields="files(id,name)").execute()
            files = res.get("files", [])
            if not files:
                return None
            parent_id = files[0]["id"]
        return parent_id

    folder_id = find_folder_id_by_path(resume_path)
    if folder_id:
        items = list_docs_in_folder(folder_id)
    else:
        print(f"❌ Resume folder not found: {resume_path}. Falling back to a global search...")
        items = list_docs_global()

    # Filters
    def matches(name: str) -> bool:
        if not name.startswith("[AP]"):
            return False
        hay = name.lower()
        return ("resume" in hay) and (human_name.lower() in hay)

    matched = [f for f in items if matches((f.get("name") or ""))]

    # Print found resumes
    for f in matched:
        print(f"- {f['name']}  (modified: {f.get('modifiedTime')})")

    # Load previous index
    index_path = profile.path / "resumes.json"
    index: Dict[str, Any] = _read_json(index_path)
    old_by_id = {r.get("id"): r for r in index.get("resumes", [])}

    # Prepare output dirs
    base_out_dir = profile.path / "resume_pdf"

    updated_index: Dict[str, Any] = {"resumes": []}
    current_ids = set()

    for f in matched:
        file_id = f.get("id")
        name = f.get("name") or "Untitled"
        modified = f.get("modifiedTime") or ""
        current_ids.add(file_id)

        # derive base name without [AP] prefix and trim spaces
        base_name = re.sub(r"^\[AP\]\s*", "", name).strip()
        out_dir = base_out_dir / base_name
        pdf_path = out_dir / "resume.pdf"
        txt_path = out_dir / "resume.txt"

        prev = old_by_id.get(file_id)
        needs_download = (not prev) or (prev.get("modifiedTime") != modified) or (not pdf_path.exists())

        if needs_download:
            _export_google_doc_pdf(service, file_id, pdf_path)
            _export_google_doc_text(service, file_id, txt_path)

        updated_index["resumes"].append({
            "id": file_id,
            "name": name,
            "base_name": base_name,
            "modifiedTime": modified,
            "pdf_path": str(pdf_path),
            "txt_path": str(txt_path),
        })

    # Remove local copies for items no longer present
    old_ids = set(old_by_id.keys())
    removed = old_ids - current_ids
    for rid in removed:
        prev = old_by_id.get(rid)
        if prev:
            try:
                prev_base = prev.get("base_name") or prev.get("name") or ""
                dir_path = base_out_dir / prev_base
                if dir_path.exists():
                    for p in dir_path.iterdir():
                        p.unlink(missing_ok=True)
                    dir_path.rmdir()
            except Exception:
                pass

    _write_json(index_path, updated_index)
    return len(matched)
