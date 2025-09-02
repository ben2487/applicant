from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, Dict, List

from playwright.async_api import Page
import json


@dataclass
class SnapshotArtifact:
    out_dir: Path
    url: str
    html_path: Path
    screenshot_path: Optional[Path]
    frames: List[Dict[str, Any]]


async def _collect_frames(page: Page, out_dir: Path) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []

    async def walk(frame, idx_path: List[int]) -> None:
        try:
            url = frame.url
        except Exception:
            url = ""
        try:
            content = await frame.content()
        except Exception:
            content = ""
        try:
            dom_html = await frame.evaluate("document.documentElement.outerHTML")
        except Exception:
            dom_html = content or ""

        safe_name = "frame-" + "-".join(str(i) for i in idx_path)
        html_file = out_dir / f"{safe_name}.html"
        dom_file = out_dir / f"{safe_name}-dom.html"
        try:
            html_file.write_text(content, encoding="utf-8")
        except Exception:
            pass
        try:
            dom_file.write_text(dom_html, encoding="utf-8")
        except Exception:
            pass
        item: Dict[str, Any] = {
            "url": url,
            "path": html_file.name,
            "dom_path": dom_file.name,
            "html_len": len(content) if content else 0,
            "index_path": idx_path,
        }
        data.append(item)
        for i, child in enumerate(frame.child_frames):
            await walk(child, idx_path + [i])

    await walk(page.main_frame, [0])
    return data


async def snapshot_page(page: Page, out_dir: Path, *, with_screenshot: bool = True) -> SnapshotArtifact:
    out_dir.mkdir(parents=True, exist_ok=True)
    url = page.url

    html_path = out_dir / "page.html"
    try:
        html = await page.content()
    except Exception:
        html = ""
    try:
        dom_html = await page.evaluate("document.documentElement.outerHTML")
    except Exception:
        dom_html = html or ""
    html_path.write_text(html, encoding="utf-8")
    dom_html_path = out_dir / "dom.html"
    dom_html_path.write_text(dom_html, encoding="utf-8")

    screenshot_path: Optional[Path] = None
    if with_screenshot:
        screenshot_path = out_dir / "screenshot.png"
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception:
            screenshot_path = None

    frames = await _collect_frames(page, out_dir)
    manifest = {
        "url": url,
        "page_html": html_path.name,
        "page_dom_html": dom_html_path.name,
        "screenshot": screenshot_path.name if screenshot_path else None,
        "frames": frames,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return SnapshotArtifact(
        out_dir=out_dir,
        url=url,
        html_path=html_path,
        screenshot_path=screenshot_path,
        frames=frames,
    )


