from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import re
import time

from .user_profiles import (
    UserProfile,
    UserSecrets,
    UserSettings,
    load_user_settings,
    update_user_secrets,
)

# NOTE: We avoid importing Google client libs until needed to keep optional dependency light.


class GoogleDriveNotLinkedError(RuntimeError): ...


def google_drive_login(profile: UserProfile) -> None:
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

    # Expect a credentials file client_secret.json in the profile dir if using OAuth client
    # Alternatively, we can store previously saved token in secrets.json
    client_secret_path = profile.path / "client_secret.json"

    creds: Optional[Credentials] = None
    # Perform an OAuth local flow
    if not client_secret_path.exists():
        raise RuntimeError(
            f"Missing OAuth client file: {client_secret_path}. Place your Google OAuth client JSON here."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
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


def refresh_resumes(profile: UserProfile) -> None:
    """Sync resumes from Google Drive to local user profile directory.

    - Reads settings.json for human_name and google_drive_resume_path
    - Lists Google Docs in the folder matching [AP]* and containing 'Resume' and human_name
    - Prints found items + modified date
    - Maintains resumes.json with modification times
    - Downloads PDF and TXT for new/updated items into [profile]/resume_pdf/<base>/
    - Removes local copies for items no longer present
    """
    service = _drive_service_from_secrets(profile)
    settings = load_user_settings(profile)
    human_name = settings.human_name
    resume_path = settings.google_drive_resume_path

    # Resolve the folder by path components
    # This is a simple resolver that walks by name.
    def find_folder_id_by_path(path_str: str) -> Optional[str]:
        parts = [p for p in path_str.split("/") if p and p != "."]
        parent_id = None
        for idx, part in enumerate(parts):
            # Query folders matching name under given parent
            q = ["mimeType = 'application/vnd.google-apps.folder'", f"name = '{part}'"]
            if parent_id:
                q.append(f"'{parent_id}' in parents")
            res = service.files().list(q=" and ".join(q), spaces="drive", fields="files(id,name)").execute()
            files = res.get("files", [])
            if not files:
                return None
            # Pick the first matching name
            parent_id = files[0]["id"]
        return parent_id

    folder_id = find_folder_id_by_path(resume_path)
    if not folder_id:
        print(f"❌ Resume folder not found: {resume_path}")
        return

    # List Google Docs in folder matching our criteria
    query = (
        f"'{folder_id}' in parents and "
        "mimeType = 'application/vnd.google-apps.document'"
    )
    fields = "files(id,name,modifiedTime)"
    res = service.files().list(q=query, fields=fields, orderBy="modifiedTime desc").execute()
    items = res.get("files", [])

    # Filters
    def matches(name: str) -> bool:
        if not name.startswith("[AP]"):
            return False
        hay = name.lower()
        return ("resume" in hay) and (human_name.lower() in hay)

    matched = [f for f in items if matches(f.get("name", ""))]

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
                # Remove the directory for that resume
                prev_base = prev.get("base_name") or prev.get("name") or ""
                dir_path = base_out_dir / prev_base
                if dir_path.exists():
                    for p in dir_path.iterdir():
                        p.unlink(missing_ok=True)
                    dir_path.rmdir()
            except Exception:
                pass

    _write_json(index_path, updated_index)
