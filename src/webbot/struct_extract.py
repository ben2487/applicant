from __future__ import annotations
from typing import List, Literal, Optional
from enum import Enum
import re
from pydantic import BaseModel, Field

from .extract import extract_visible_text
from .ai_search import get_openai_client, OpenAIConfigError


class AIMode(str, Enum):
    OPEN_AI = "openai"
    LLM_OFF = "llm_off"


class JobPostingExtract(BaseModel):
    is_job_posting: bool
    title: Optional[str] = None
    company_name: Optional[str] = None
    company_redacted: bool = False
    requirements: List[str] = Field(default_factory=list)
    work_mode: Literal["remote", "hybrid", "in_office", "unknown"] = "unknown"
    work_mode_notes: Optional[str] = None
    locations: List[str] = Field(default_factory=list)
    currencies_detected: List[str] = Field(default_factory=list)
    non_us_indicia: List[str] = Field(default_factory=list)


_PLATITUDES = [
    r"team player",
    r"fast[- ]?paced",
    r"dynamic environment",
    r"excellent communication",
    r"self[- ]?starter",
    r"problem[- ]?solver",
    r"leadership skills",
]

_TECH_HINTS = [
    "python", "java", "c++", "typescript", "react", "django", "flask",
    "node", "aws", "gcp", "azure", "kubernetes", "docker", "sql", "spark",
]

_CURRENCY_REGEX = re.compile(r"(CAD|C\$|₹|INR|£|GBP|EUR|€|AUD|NZD|SGD)")


def _normalize_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _detect_is_job(text: str) -> bool:
    hay = text.lower()
    hits = 0
    for kw in [
        "apply now", "apply", "requirements", "responsibilities", "qualifications",
        "full-time", "part-time", "job description", "benefits",
    ]:
        if kw in hay:
            hits += 1
    # Presence of currency + role words
    if _CURRENCY_REGEX.search(text):
        hits += 1
    for role_kw in ["engineer", "developer", "designer", "manager", "scientist", "analyst"]:
        if role_kw in hay:
            hits += 1
    return hits >= 2


def _extract_title(text: str) -> Optional[str]:
    lines = _normalize_lines(text)
    # Prefer first strong title-like line (short, capitalized words)
    for ln in lines[:15]:
        if len(ln) <= 120 and any(w[0:1].isupper() for w in ln.split()[:4]):
            # Avoid lines that look like navigation
            if not re.search(r"(menu|login|sign in|how it works)", ln, re.I):
                return ln
    return None


def _extract_company(text: str, title_maybe: Optional[str]) -> tuple[Optional[str], bool]:
    # From "{Role} at {Company}" pattern
    if title_maybe:
        m = re.search(r"\bat\s+([A-Z][\w&\- ]{1,60})$", title_maybe)
        if m:
            return m.group(1).strip(), False
    # From "About {Company}" section
    m2 = re.search(r"\bAbout\s+([A-Z][\w&\- ]{1,60})\b", text)
    if m2:
        return m2.group(1).strip(), False
    # Redacted indicators
    redacted = bool(re.search(r"confidential|stealth|client redacted", text, re.I))
    return None, redacted


def _extract_work_mode_and_notes(text: str) -> tuple[str, Optional[str]]:
    hay = text.lower()
    mode = "unknown"
    if "remote" in hay:
        mode = "remote"
    if re.search(r"hybrid|in[ -]?office|on[ -]?site", hay):
        mode = "hybrid" if "hybrid" in hay else ("in_office" if re.search(r"in[ -]?office|on[ -]?site", hay) else mode)
    # Notes: capture proximity/weekday hints
    notes = None
    m = re.search(r"within\s+\d+\s+miles|\b(tues|thu|wed|mon|fri)\w*\b|\b[2-4]\s+days\s+in\s+office", hay)
    if m:
        notes = m.group(0)
    return mode, notes


def _extract_locations(text: str) -> list[str]:
    # Simple heuristic: lines with keywords and capitalized words
    locs: list[str] = []
    for ln in _normalize_lines(text):
        if re.search(r"\b(location|office|hybrid in)\b", ln, re.I):
            # Extract proper-noun like chunks
            m = re.findall(r"[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*", ln)
            for tok in m:
                if len(tok) >= 3 and tok.lower() not in {"Location", "Office"}:
                    locs.append(tok)
    # Also detect explicit patterns like "Hybrid in Toronto"
    for m in re.finditer(r"Hybrid in\s+([A-Z][\w\- ]{2,40})", text):
        locs.append(m.group(1).strip())
    # Dedupe preserving order
    seen = set()
    out = []
    for x in locs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _extract_requirements(text: str) -> list[str]:
    reqs: list[str] = []
    lines = _normalize_lines(text)
    # Capture bullet-y lines or lines under requirement-like headings
    keep = False
    for ln in lines:
        if re.search(r"requirement|qualification|what you'?ll need|skills|must have", ln, re.I):
            keep = True
            continue
        if keep and not ln:
            keep = False
        is_bullet = bool(re.match(r"^[\-\*•]\s+", ln))
        if is_bullet or keep:
            cleaned = re.sub(r"^[\-\*•]\s+", "", ln).strip()
            if not cleaned:
                continue
            low = cleaned.lower()
            if any(re.search(p, low) for p in _PLATITUDES):
                continue
            if any(t in low for t in _TECH_HINTS) or re.search(r"\d+\+?\s*(years|yrs)", low):
                reqs.append(cleaned)
    # Fallback: collect top bullets regardless, then filter platitudes
    if not reqs:
        for ln in lines:
            if re.match(r"^[\-\*•]\s+", ln):
                cleaned = re.sub(r"^[\-\*•]\s+", "", ln).strip()
                low = cleaned.lower()
                if not any(re.search(p, low) for p in _PLATITUDES):
                    reqs.append(cleaned)
    return reqs[:20]


def _extract_currencies_and_indicia(text: str) -> tuple[list[str], list[str]]:
    currencies = sorted(set(m.group(1) for m in _CURRENCY_REGEX.finditer(text)))
    indicia: list[str] = []
    if any(c for c in currencies if c not in {"USD", "$"}):
        indicia.append("non-us-currency")
    for kw in ["eu only", "uk only", "visa sponsorship not", "must be based in", "canada", "global remote"]:
        if re.search(kw, text, re.I):
            indicia.append(kw)
    return currencies, list(dict.fromkeys(indicia))


def heuristic_extract(text: str, page_title: Optional[str]) -> JobPostingExtract:
    title = _extract_title(text) or page_title
    company_name, redacted = _extract_company(text, title)
    work_mode, notes = _extract_work_mode_and_notes(text)
    locations = _extract_locations(text)
    reqs = _extract_requirements(text)
    currencies, indicia = _extract_currencies_and_indicia(text)
    is_job = _detect_is_job(text)
    return JobPostingExtract(
        is_job_posting=is_job,
        title=title,
        company_name=company_name,
        company_redacted=redacted if company_name is None else False,
        requirements=reqs,
        work_mode=work_mode,
        work_mode_notes=notes,
        locations=locations,
        currencies_detected=currencies,
        non_us_indicia=indicia,
    )


def _llm_structured_extract(text: str, heuristic: JobPostingExtract) -> JobPostingExtract:
    client = get_openai_client()  # will raise if missing/invalid
    system = (
        "Extract strictly structured data about a job posting. "
        "If a field is unknown, use null or an empty list. Do not invent details."
    )
    schema = JobPostingExtract.model_json_schema()
    prompt = (
        "Return a compact JSON object with exactly these keys and types.\n\n"
        f"Schema: {schema}\n\n"
        "Heuristic candidates (may be incomplete, prefer page text if conflicting):\n"
        f"{heuristic.model_dump_json()}\n\n"
        "Page text (truncated if long):\n"
        f"{text[:15000]}"
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=800,
    )
    import json

    data = json.loads(resp.choices[0].message.content or "{}")
    return JobPostingExtract.model_validate(data)


async def parse_job_page(page, *, mode: AIMode = AIMode.OPEN_AI) -> JobPostingExtract:
    text = await extract_visible_text(page)
    title = await page.title()
    heur = heuristic_extract(text, title)
    if mode == AIMode.LLM_OFF:
        return heur
    # OPEN_AI mode
    return _llm_structured_extract(text, heur)
