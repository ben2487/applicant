from __future__ import annotations
from playwright.async_api import Page


async def extract_visible_text(page: Page) -> str:
    # Inner text of <body> is usually OK for a first pass.
    txt = await page.inner_text("body")
    # Squash extra whitespace
    return "\n".join(line.strip() for line in txt.splitlines() if line.strip())
