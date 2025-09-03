from __future__ import annotations
from .config import load_settings
from openai import OpenAI
from .tracing import json_blob


class OpenAIConfigError(RuntimeError): ...


def get_openai_client() -> OpenAI:
    s = load_settings()
    if not s.openai_api_key:
        raise OpenAIConfigError(
            "Missing OPENAI_API_KEY. Create a .env at repo root with OPENAI_API_KEY=sk-..."
        )
    client = OpenAI(api_key=s.openai_api_key)
    # Lightweight validation
    try:
        _ = client.models.list()
    except Exception as e:
        raise OpenAIConfigError(
            "OPENAI_API_KEY appears invalid or not authorized. "
            "Check the key and billing."
        ) from e
    return client


def generate_search_queries(
    company: str, title: str, company_domain: str | None
) -> list[str]:
    """
    Use a simple heuristic plus an LLM refinement for robust queries.
    """
    seeds = []
    if company_domain:
        seeds += [
            f"site:{company_domain} careers",
            f"site:{company_domain} jobs",
            f"site:{company_domain} {title}",
        ]
    seeds += [f"{company} careers", f"{company} jobs {title}"]
    try:
        client = get_openai_client()
        prompt = (
            "Generate 3–5 concise search queries to find the official company careers or job listing "
            "for the given company and role. Prefer site: filters if a company domain is provided. "
            f"Company: {company}\nTitle: {title}\nDomain: {company_domain or '(unknown)'}"
        )
        json_blob("LLM", "TRACE", "search_queries_prompt", {"prompt": prompt})
        cmpl = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Return only search queries, one per line.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = cmpl.choices[0].message.content or ""
        json_blob("LLM", "TRACE", "search_queries_response", {"response": content})
        lines = content.splitlines()
        refined = [line.strip("-• \t") for line in lines if line.strip()]
        return list(dict.fromkeys(seeds + refined))  # dedupe, preserve order
    except Exception:
        return seeds
