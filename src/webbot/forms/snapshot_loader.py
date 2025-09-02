from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

from playwright.async_api import async_playwright, BrowserContext, Page


@dataclass
class SnapshotManifest:
    base_dir: Path
    url: str
    page_html: Path
    page_dom_html: Optional[Path]
    screenshot: Optional[Path]
    frames: List[Dict[str, Any]]


def load_snapshot_manifest(directory: Path) -> SnapshotManifest:
    manifest_path = directory / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return SnapshotManifest(
        base_dir=directory,
        url=data.get("url", ""),
        page_html=directory / data.get("page_html", "page.html"),
        page_dom_html=(directory / data["page_dom_html"]) if data.get("page_dom_html") else None,
        screenshot=(directory / data["screenshot"]) if data.get("screenshot") else None,
        frames=data.get("frames", []),
    )


async def load_snapshot_as_page(directory: Path) -> tuple[BrowserContext, Page, SnapshotManifest]:
    """
    Launch a temporary headless browser and load the main snapshot HTML file.
    Returns (context, page, manifest). Caller must close the context.
    """
    manifest = load_snapshot_manifest(directory)

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    ctx = await browser.new_context(java_script_enabled=False)
    page = await ctx.new_page()
    # Load static DOM HTML content to avoid JS mutations
    html_text = (manifest.page_dom_html or manifest.page_html).read_text(encoding="utf-8")
    await page.set_content(html_text, wait_until="domcontentloaded")
    return ctx, page, manifest


async def scan_snapshot_for_selector(directory: Path, selector: str) -> int:
    """
    Load the main page and each saved frame HTML into a headless page and count total matches.
    This avoids cross-origin issues with remote iframes when viewing snapshot offline.
    """
    manifest = load_snapshot_manifest(directory)
    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(java_script_enabled=False)
        page = await ctx.new_page()
        total = 0
        # scan main page (prefer dom html)
        html_text = (manifest.page_dom_html or manifest.page_html).read_text(encoding="utf-8")
        await page.set_content(html_text, wait_until="domcontentloaded")
        try:
            total += await page.locator(selector).count()
        except Exception:
            pass
        # scan each saved frame file
        for fr in manifest.frames:
            # prefer DOM file when present
            p = directory / (fr.get("dom_path") or fr.get("path", ""))
            if not p.exists():
                continue
            try:
                frag = p.read_text(encoding="utf-8")
            except Exception:
                continue
            await page.set_content(frag, wait_until="domcontentloaded")
            try:
                total += await page.locator(selector).count()
            except Exception:
                pass
        await ctx.close()
        return total
    finally:
        await pw.stop()


