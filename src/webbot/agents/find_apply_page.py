from __future__ import annotations
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from ..ai_search import get_openai_client
from ..apply_finder import duckduckgo_html_search, domain
from playwright.async_api import Page


class AgentPick(BaseModel):
    official_domain: Optional[str] = None
    careers_url: Optional[str] = None
    apply_url: Optional[str] = None
    confidence: Optional[float] = None
    rationale: Optional[str] = None


async def smart_find_apply_url(
    page: Page, *, company_name: str, job_title: str
) -> tuple[Optional[str], Dict[str, Any]]:
    """
    Use an LLM to choose the official domain, careers page, and best apply URL
    from DuckDuckGo candidates.

    Returns (best_url, trace) where trace contains the prompt/response and picks.
    """
    # Gather candidate URLs from multiple targeted queries
    queries = [
        f"{company_name} official site",
        f"{company_name} website",
        f"{company_name} careers",
        f"{company_name} jobs {job_title}",
        f"site:linkedin.com/company {company_name}",
    ]
    candidates: List[str] = []
    for q in queries:
        try:
            results = await duckduckgo_html_search(page, q, limit=10)
            for url in results:
                if url not in candidates:
                    candidates.append(url)
        except Exception:
            continue

    # Prepare prompt for the LLM
    client = get_openai_client()
    prompt = (
        "You are given a company name and a target job title. "
        "From the candidate URLs, identify: (1) the official company domain (e.g., example.com), "
        "(2) a careers page URL on the official domain if it exists, and (3) the best matching job apply URL for the given title.\n\n"
        f"Company: {company_name}\n"
        f"Target title: {job_title}\n\n"
        f"Candidates (URLs):\n" + "\n".join(candidates[:50]) + "\n\n"
        "Return a compact JSON object with keys: official_domain, careers_url, apply_url, confidence (0-1), rationale."
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise researcher. Prefer official first-party sites. "
                "If the company uses an ATS (Greenhouse/Lever/Ashby/Workable), you may return that apply URL if it is clearly for this company."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=messages,
        temperature=0.1,
        max_tokens=600,
    )

    raw_content = resp.choices[0].message.content or "{}"
    import json

    data = {}
    try:
        data = json.loads(raw_content)
    except Exception:
        data = {}
    pick = AgentPick.model_validate(data)

    trace = {
        "prompt": prompt,
        "response": raw_content,
        "picks": pick.model_dump(),
        "candidates_count": len(candidates),
    }

    # Final choice preference: apply_url, else careers_url
    best = pick.apply_url or pick.careers_url

    # Normalize official domain if present
    if pick.official_domain:
        try:
            _ = domain(pick.official_domain)
        except Exception:
            pass

    return best, trace
