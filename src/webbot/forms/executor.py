from __future__ import annotations
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from playwright.async_api import Page

from .schema import FormSchema, FormField


@dataclass
class ExecutionOptions:
    scroll_padding: int = 200
    wait_after_upload_ms: int = 6000


async def _scroll_into_view(page: Page, selector: str, padding: int) -> None:
    try:
        loc = page.locator(selector)
        if await loc.count() > 0:
            await loc.first.scroll_into_view_if_needed()
            # minor manual scroll padding
            await page.evaluate("p => window.scrollBy(0, p)", padding)
    except Exception:
        pass


def _pick_resume_pdf(profile_root: Path) -> Optional[Path]:
    # Search for any resume.pdf under user_profiles/*/resume_pdf/**/resume.pdf
    candidates: List[Path] = list(profile_root.glob("**/resume_pdf/**/resume.pdf"))
    if not candidates:
        return None
    return random.choice(candidates)


async def _upload_resume(page: Page, schema: FormSchema, resume_pdf: Path, opts: ExecutionOptions) -> bool:
    # Try visible file inputs first
    try:
        print(f"[executor] Attempting resume upload: {resume_pdf}")
        file_inputs = page.locator('input[type="file"]')
        if await file_inputs.count() > 0:
            # prefer the first visible; else first
            for i in range(await file_inputs.count()):
                el = file_inputs.nth(i)
                try:
                    if await el.is_visible():
                        await el.set_input_files(str(resume_pdf))
                        await page.wait_for_timeout(opts.wait_after_upload_ms)
                        print("[executor] Resume upload completed (visible input).")
                        return True
                except Exception:
                    continue
            # fallback: set on first element
            try:
                await file_inputs.first.set_input_files(str(resume_pdf))
                await page.wait_for_timeout(opts.wait_after_upload_ms)
                print("[executor] Resume upload completed (first input).")
                return True
            except Exception:
                pass
    except Exception:
        pass

    # Heuristic: click common "Upload" buttons to trigger hidden input
    for sel in [
        "button:has-text('Upload file')",
        "button:has-text('Upload File')",
        "button:has-text('Upload Resume')",
        "label:has-text('Upload')",
    ]:
        try:
            loc = page.locator(sel)
            if await loc.count() > 0:
                await _scroll_into_view(page, sel, opts.scroll_padding)
                await loc.first.click()
                # After click, try again to set file input
                try:
                    file_inputs = page.locator('input[type="file"]')
                    if await file_inputs.count() > 0:
                        await file_inputs.first.set_input_files(str(resume_pdf))
                        await page.wait_for_timeout(opts.wait_after_upload_ms)
                        print("[executor] Resume upload completed (after clicking upload button).")
                        return True
                except Exception:
                    pass
        except Exception:
            continue
    return False


async def _fill_field(page: Page, field: FormField, value: str, opts: ExecutionOptions) -> None:
    sel = field.locators.css or None
    if not sel:
        # Fallbacks by label/placeholder when CSS is missing
        label_txt = (field.label or "").strip()
        placeholder_txt = (field.placeholder or "").strip()
        if label_txt:
            try:
                loc = page.get_by_label(label_txt)
                await loc.first.scroll_into_view_if_needed()
                if field.type in {"text", "email", "tel", "number", "date", "textarea"}:
                    print(f"[executor] [fallback-label] Filling: {label_txt} -> {value}")
                    await loc.fill(value)
                    return
            except Exception:
                pass
        if placeholder_txt:
            try:
                loc = page.get_by_placeholder(placeholder_txt)
                await loc.first.scroll_into_view_if_needed()
                if field.type in {"text", "email", "tel", "number", "date", "textarea"}:
                    print(f"[executor] [fallback-placeholder] Filling: {placeholder_txt} -> {value}")
                    await loc.fill(value)
                    return
            except Exception:
                pass
        return
    try:
        # Wait for the selector to appear post-render/autofill
        try:
            await page.wait_for_selector(sel, timeout=5000)
        except Exception:
            pass
        await _scroll_into_view(page, sel, opts.scroll_padding)
        loc = page.locator(sel)
        cnt = await loc.count()
        if cnt == 0:
            # Fallback by label
            label_txt = (field.label or "").strip()
            placeholder_txt = (field.placeholder or "").strip()
            if label_txt:
                try:
                    loc = page.get_by_label(label_txt)
                    cnt = await loc.count()
                except Exception:
                    pass
            if cnt == 0 and placeholder_txt:
                try:
                    loc = page.get_by_placeholder(placeholder_txt)
                    cnt = await loc.count()
                except Exception:
                    pass
        if cnt == 0:
            print(f"[executor] [fill] No element found for selector '{sel}' label='{field.label}' placeholder='{field.placeholder}'")
            return
        if field.type in {"text", "email", "tel", "number", "date"}:
            print(f"[executor] [fill] Using selector '{sel}' -> {value}")
            await loc.first.fill(value)
        elif field.type == "textarea":
            print(f"[executor] [fill] Using selector (textarea) '{sel}' -> {value}")
            await loc.first.fill(value)
        elif field.type == "select":
            try:
                print(f"[executor] [select] '{sel}' -> {value}")
                await loc.first.select_option(value)
            except Exception:
                await loc.first.click()
        elif field.type == "checkbox":
            target_truthy = value.lower() in {"1", "true", "yes", "on"}
            if not target_truthy:
                return
            label_txt = (field.label or field.name or "").strip()
            print(f"[executor] Selecting checkbox: {label_txt}")
            # Prefer clicking the control (labels/wrappers often toggle custom checkboxes)
            try:
                if await loc.count() > 0:
                    await loc.first.click()
                    return
            except Exception:
                pass
            # Try role-based checkbox by accessible name
            if label_txt:
                try:
                    role_loc = page.get_by_role("checkbox", name=re.compile(rf"^{re.escape(label_txt)}$", re.I))
                    if await role_loc.count() > 0:
                        await role_loc.first.scroll_into_view_if_needed()
                        await role_loc.first.click()
                        return
                except Exception:
                    pass
                # Try label association
                try:
                    lab_loc = page.get_by_label(label_txt)
                    if await lab_loc.count() > 0:
                        await lab_loc.first.scroll_into_view_if_needed()
                        await lab_loc.first.click()
                        return
                except Exception:
                    pass
                # Fallback: click element containing the text
                try:
                    txt_loc = page.get_by_text(label_txt, exact=True)
                    if await txt_loc.count() > 0:
                        await txt_loc.first.scroll_into_view_if_needed()
                        await txt_loc.first.click()
                        return
                except Exception:
                    pass
            # Fallback: if it's a real input, ensure checked state
            try:
                current = await loc.first.is_checked()
                if not current:
                    await loc.first.check()
            except Exception:
                return
        elif field.type == "radio":
            await loc.first.click()
        else:
            # attempt generic type
            await loc.first.fill(value)
    except Exception:
        return


async def execute_fill_plan(page: Page, schema_with_answers: FormSchema, profile_root: Path, *, wait_seconds: int = 60) -> None:
    opts = ExecutionOptions()
    print("[executor] Form loaded; starting execution")
    # 1) Upload resume first to trigger autofill
    resume = _pick_resume_pdf(profile_root)
    if resume:
        await _upload_resume(page, schema_with_answers, resume, opts)
        # Give autofill a bit more time to propagate values and render
        await page.wait_for_timeout(2000)

    # 2) Fill remaining fields; if field has existing value from autofill, do not override
    for section in schema_with_answers.sections:
        for f in section.fields:
            answer = f.meta.get("answer") if isinstance(f.meta, dict) else None
            if not answer:
                continue
            # Skip upload fields (handled)
            if f.type == "file":
                continue
            # Check if already populated
            sel = f.locators.css or None
            if not sel:
                print(f"[executor] No selector for field: {(f.label or f.name or f.field_id)}; trying label fallback")
            try:
                # Determine pre-populated differently by type
                prepopulated = False
                if f.type in {"text", "email", "tel", "number", "date", "textarea"}:
                    if sel:
                        loc = page.locator(sel)
                        if await loc.count() > 0:
                            try:
                                val = await loc.first.input_value()
                                prepopulated = bool(val and val.strip())
                                if prepopulated:
                                    print(f"[executor] Skipping pre-populated text: {(f.label or f.name or f.field_id)} -> '{val}'")
                            except Exception:
                                prepopulated = False
                elif f.type in {"checkbox", "radio"}:
                    if sel:
                        loc = page.locator(sel)
                        if await loc.count() > 0:
                            try:
                                state = await loc.first.is_checked()
                                prepopulated = bool(state)
                                if prepopulated:
                                    print(f"[executor] Skipping pre-checked: {(f.label or f.name or f.field_id)}")
                            except Exception:
                                prepopulated = False
                if prepopulated:
                    continue
                if f.type in {"text", "email", "tel", "number", "date", "textarea"}:
                    print(f"[executor] Filling {field.type}: {(f.label or f.name or f.field_id)} -> {answer}")
                await _fill_field(page, f, str(answer), opts)
            except Exception as e:
                print(f"[executor] Failed to fill field: {(f.label or f.name or f.field_id)} | error={e}")
                continue

    # 3) Leave browser open for manual review
    await page.wait_for_timeout(wait_seconds * 1000)


