from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

from pydantic import BaseModel

from .ai_search import get_openai_client
from .user_profiles import UserProfile


class ResumeIndexItem(BaseModel):
    id: str
    name: str
    base_name: Optional[str] = None
    modifiedTime: Optional[str] = None
    pdf_path: Optional[str] = None
    txt_path: Optional[str] = None


class AlignmentResponse(BaseModel):
    chosen_resume_id: str
    chosen_resume_name: str
    confidence_label: str
    missing_summary: Optional[str] = None
    reasoning: Optional[str] = None


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _load_resume_index(profile: UserProfile) -> List[ResumeIndexItem]:
    index_path = profile.path / "resumes.json"
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        items = data.get("resumes", [])
        return [ResumeIndexItem(**itm) for itm in items if isinstance(itm, dict)]
    except Exception:
        return []


def _compose_alignment_prompt(job_description: str, resumes: List[tuple[ResumeIndexItem, str]]) -> str:
    lines: List[str] = []
    lines.append(
        "You are given a job description and a small set of candidate resumes.\n"
        "Choose the single resume that best aligns with the job description.\n"
        "Focus on technical alignment (role/title/domain/skills), not soft skills.\n"
        "Return a JSON object with keys: chosen_resume_id, chosen_resume_name, confidence_label, missing_summary, reasoning.\n"
        "- confidence_label must be one of: 'Perfect alignment', 'Strong alignment', 'Average alignment', 'Poorly aligned'.\n"
        "- If confidence_label is not 'Perfect alignment', include a brief missing_summary of key gaps.\n"
        "Be concise."
    )
    lines.append("")
    lines.append("[Job description]")
    lines.append(job_description)
    lines.append("")
    lines.append("[Resumes]")
    for idx, (meta, content) in enumerate(resumes, start=1):
        lines.append(f"RESUME {idx}:")
        lines.append(f"ID: {meta.id}")
        lines.append(f"NAME: {meta.name}")
        lines.append("CONTENT:")
        lines.append(content.strip())
        lines.append("")
    lines.append(
        "Return only a compact JSON object. Do not include any commentary outside of JSON."
    )
    return "\n".join(lines)


def select_best_resume_for_job_description(
    *, profile: UserProfile, job_description_text: str, model: str = "gpt-4o"
) -> Tuple[AlignmentResponse, Dict[str, Any]]:
    """Run an LLM comparison to pick the best-aligned resume.

    Returns (parsed_alignment, trace) where trace includes prompt and raw response.
    """
    # Load resumes and contents
    index_items = _load_resume_index(profile)
    resume_pairs: List[tuple[ResumeIndexItem, str]] = []
    for itm in index_items:
        if not itm.txt_path:
            continue
        txt = _read_text_file(Path(itm.txt_path))
        if txt.strip():
            resume_pairs.append((itm, txt))

    if not resume_pairs:
        raise RuntimeError("No resume texts found for this user.")

    # Compose prompt and call model
    prompt = _compose_alignment_prompt(job_description_text, resume_pairs)
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a precise recruiting assistant. Return strictly JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=600,
    )

    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    parsed = AlignmentResponse.model_validate(data)
    trace = {"prompt": prompt, "response": raw}
    return parsed, trace


def run_alignment_for_files(
    *, profile: UserProfile, job_desc_path: Path, model: str = "gpt-4o"
) -> Tuple[AlignmentResponse, Dict[str, Any]]:
    job_text = _read_text_file(job_desc_path)
    if not job_text.strip():
        raise RuntimeError(f"Job description file is empty or unreadable: {job_desc_path}")
    return select_best_resume_for_job_description(
        profile=profile, job_description_text=job_text, model=model
    )


