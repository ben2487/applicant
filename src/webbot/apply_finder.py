from __future__ import annotations
import tldextract
from playwright.async_api import Page
from .config import repo_root
from .ai_search import generate_search_queries


def load_do_not_apply_domains() -> set[str]:
    path = repo_root() / "data" / "do-not-apply.txt"
    domains: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            domains.add(s.lower())
    return domains


def domain(host_or_url: str) -> str:
    ext = tldextract.extract(host_or_url)
    base = ".".join([p for p in [ext.domain, ext.suffix] if p])
    return base.lower()


async def find_company_homepage_from_job_page(page: Page) -> str | None:
    # Heuristic: collect all external links and pick a likely company root domain
    anchors = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    if not anchors:
        return None
    job_host = domain(page.url)
    dna = load_do_not_apply_domains()
    candidates: dict[str, int] = {}
    for href in anchors:
        try:
            d = domain(href)
        except Exception:
            continue
        if not d or d == job_host or d in dna:
            continue
        candidates[d] = candidates.get(d, 0) + 1
    if not candidates:
        return None
    # Pick the most frequent external domain as the "company site".
    winner = max(candidates.items(), key=lambda kv: kv[1])[0]
    return f"https://{winner}"


async def duckduckgo_html_search(page: Page, query: str, limit: int = 10) -> list[str]:
    url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
    await page.goto(url, wait_until="domcontentloaded")
    # Selector stable for the "HTML" (lite) version:
    links = await page.eval_on_selector_all(
        "a.result__a", "els => els.map(e => e.href)"
    )
    return links[:limit] if links else []


async def find_apply_url(
    page: Page, company_name: str, job_title: str, company_domain: str | None
) -> str | None:
    queries = generate_search_queries(company_name, job_title, company_domain)
    for q in queries:
        results = await duckduckgo_html_search(page, q, limit=10)
        # Prefer links on the official domain if we know it, otherwise look for typical ATS providers
        ats_hints = (
            "greenhouse.io",
            "boards.greenhouse.io",
            "lever.co",
            "jobs.ashbyhq.com",
            "workable.com",
        )
        for r in results:
            d = domain(r)
            if company_domain and d == company_domain:
                return r
        for r in results:
            if any(h in r for h in ats_hints):
                return r
    return None
