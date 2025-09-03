from __future__ import annotations
from typing import Optional, Dict, Any, List
import json
import time

from ..ai_search import get_openai_client
from ..apply_finder import domain
from ..tracing import action, json_blob, event


def _build_prompt(company_name: str, job_title: str, extra_keywords: Optional[List[str]], disallowed: List[str], distilled_fragments: Optional[List[str]] = None) -> str:
    bullets = "\n".join(f"- {w}" for w in (extra_keywords or []))
    frags = "\n".join(f"- {f}" for f in (distilled_fragments or []))
    return (
        "You are given a company name and a target job title. Please identify: (1) the official company domain (e.g., example.com), "
        "(2) a careers page URL on the official domain if it exists, and (3) the best matching job apply URL for the given title.\n\n"
        f"Company: {company_name}\n"
        f"Target title: {job_title}\n"
        + (f"Extra keywords (optional):\n{bullets}\n\n" if bullets else "")
        + (f"Distilled fragments from the job posting (for better matching):\n{frags}\n\n" if frags else "")
        + f"Avoid returning apply URLs on these domains: {', '.join(disallowed)}. Prefer ATS-hosted pages (Ashby, Greenhouse, Lever, Workday).\n\n"
        "Return a compact JSON object with keys: official_domain, careers_url, apply_url, confidence (0-1), rationale."
    )


def _parse_json_from_messages(items: list[dict]) -> dict:
    for m in items:
        if m.get("role") == "assistant":
            parts = m.get("content") or []
            # OpenAI beta returns a list of content parts; each may have text
            for part in parts:
                text_obj = part.get("text") or {}
                val = text_obj.get("value")
                if isinstance(val, str) and val.strip():
                    try:
                        return json.loads(val)
                    except Exception:
                        continue
    return {}


def _violates_dna(url: Optional[str], disallowed: List[str]) -> bool:
    if not url:
        return False
    try:
        d = domain(url)
        return any(d.endswith(bad) or bad in d for bad in disallowed)
    except Exception:
        return False


async def agentic5beta_find_apply_url(
    *,
    company_name: str,
    job_title: str,
    extra_keywords: Optional[List[str]] = None,
    disallowed_domains: Optional[List[str]] = None,
    distilled_fragments: Optional[List[str]] = None,
    model: str = "gpt-4.1",
    poll_interval_s: float = 0.7,
    max_wait_s: float = 45.0,
) -> tuple[Optional[str], Dict[str, Any]]:
    """
    Use OpenAI Assistants Beta with the built-in web tool to perform real searches and return the best apply URL.
    This runs entirely server-side: we don't execute any local searches.
    """
    disallowed = disallowed_domains or []
    client = get_openai_client()

    prompt = _build_prompt(company_name, job_title, extra_keywords, disallowed, distilled_fragments)
    json_blob("LLM", "DEBUG", "agentic5beta_prompt", {"model": model, "prompt": prompt})

    with action("agentic5beta_setup", category="FIND_APPLY", company=company_name, title=job_title):
        assistant = client.beta.assistants.create(
            name="Job Search Agent",
            model=model,
            tools=[{"type": "web"}],  # relies on OpenAI web tool in Assistants API
        )
        thread = client.beta.threads.create(messages=[{"role": "user", "content": prompt}])
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
        json_blob("FIND_APPLY", "TRACE", "agentic5beta_run_started", {"assistant_id": assistant.id, "thread_id": thread.id, "run_id": run.id})

    # Poll until completion
    start = time.time()
    status = run.status
    with action("agentic5beta_run", category="FIND_APPLY", run_id=run.id):
        while status not in {"completed", "failed", "cancelled", "expired"}:
            time.sleep(poll_interval_s)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            status = run.status
            event("FIND_APPLY", "TRACE", "agentic5beta_status", status=status)
            if time.time() - start > max_wait_s:
                event("FIND_APPLY", "INFO", "agentic5beta_timeout", seconds=max_wait_s)
                break

        # Collect messages
        msgs = client.beta.threads.messages.list(thread_id=thread.id)
        # Convert to simple Python dicts
        items = [m.to_dict() if hasattr(m, "to_dict") else m for m in getattr(msgs, "data", [])]
        json_blob("FIND_APPLY", "TRACE", "agentic5beta_messages", items)
        data = _parse_json_from_messages(items)
        json_blob("LLM", "DEBUG", "agentic5beta_parsed", data)

    picks = {
        "official_domain": data.get("official_domain"),
        "careers_url": data.get("careers_url"),
        "apply_url": data.get("apply_url"),
    }
    trace = {"picks": picks, "raw": data}

    # Choose best respecting disallowed domains
    best = picks.get("apply_url") or picks.get("careers_url")
    if _violates_dna(best, disallowed):
        event("FIND_APPLY", "INFO", "agentic5beta_blocked_by_dna", chosen=best)
        best = None

    return best, trace


