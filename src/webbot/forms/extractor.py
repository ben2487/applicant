from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import re

from playwright.async_api import Page

from .schema import FormSchema, FormSection, FormField, Locator, Validity
from .snapshot_loader import scan_snapshot_for_selector, load_snapshot_as_page, load_snapshot_manifest


def _guess_field_type(input_type: Optional[str], tag: str, role: Optional[str]) -> str:
    if tag == "textarea":
        return "textarea"
    if tag == "select":
        return "select"
    if tag == "input":
        t = (input_type or "text").lower()
        if t in {"text", "email", "tel", "number", "date", "file", "checkbox", "radio", "password"}:
            return t
        return "text"
    if role == "combobox":
        return "combobox"
    return "custom"


async def _extract_fields_from_page(page: Page) -> List[FormField]:
    # Collect candidate inputs with minimal attributes for locators/heuristics
    elements = await page.evaluate(
        """
        () => {
          const nodes = Array.from(document.querySelectorAll('input, textarea, select, [role="combobox"], [contenteditable="true"]'));
          const results = [];
          for (const el of nodes) {
            const tag = el.tagName.toLowerCase();
            const type = (el.getAttribute('type') || '').toLowerCase();
            if (tag === 'input' && type === 'hidden') continue;
            const id = el.id || null;
            const name = el.getAttribute('name') || null;
            const placeholder = el.getAttribute('placeholder') || null;
            const ariaLabel = el.getAttribute('aria-label') || null;
            const ariaLabelledBy = el.getAttribute('aria-labelledby') || null;
            const required = el.hasAttribute('required') || el.getAttribute('aria-required') === 'true';
            const role = el.getAttribute('role') || null;
            const labelFor = id ? document.querySelector(`label[for="${id}"]`) : null;
            let label = labelFor ? labelFor.innerText.trim() : null;
            if (!label && el.closest('label')) {
              label = el.closest('label').innerText.trim();
            }
            if (!label && ariaLabel) label = ariaLabel;
            const style = window.getComputedStyle(el);
            const bounding = el.getBoundingClientRect();
            const visible = (
              style && style.visibility !== 'hidden' && style.display !== 'none' &&
              bounding.width > 0 && bounding.height > 0
            );
            results.push({
              tag,
              type,
              id,
              name,
              placeholder,
              ariaLabel,
              ariaLabelledBy,
              required,
              role,
              label,
              visible,
              bbox: {x: bounding.x, y: bounding.y, w: bounding.width, h: bounding.height},
              classes: el.className || null,
              hasDnd: false
            });
          }
          return results;
        }
        """
    )
    fields: List[FormField] = []
    for idx, e in enumerate(elements):
        if not e.get("visible"):
            # Always keep file inputs even if not visible; many ATS hide them behind custom UIs
            if not (e.get("tag") == "input" and (e.get("type") or "").lower() == "file"):
                continue
        ftype = _guess_field_type(e.get("type"), e.get("tag"), e.get("role"))
        loc = Locator()
        if e.get("id"):
            loc.css = f"#{e['id']}"
        elif e.get("name"):
            loc.css = f"[name=\"{e['name']}\"]"
        else:
            # fallback: nth-of-type by tag
            loc.nth = f"{e.get('tag')}[{idx}]"
        meta: Dict[str, Any] = {
            "ariaLabel": e.get("ariaLabel"),
            "bbox": e.get("bbox"),
            "classes": e.get("classes"),
            "hasDnd": e.get("hasDnd", False),
            "visible": e.get("visible", False),
        }
        field = FormField(
            field_id=f"field_{idx}",
            name=e.get("name"),
            label=e.get("label"),
            placeholder=e.get("placeholder"),
            type=ftype,
            required=bool(e.get("required")),
            options=[],
            locators=loc,
            meta=meta,
        )
        fields.append(field)
    return fields


async def _detect_upload_signal(page: Page) -> bool:
    return await page.evaluate(
        """
        () => {
          const fileInputs = document.querySelectorAll('input[type="file"]');
          if (fileInputs && fileInputs.length > 0) return true;
          const nodes = Array.from(document.querySelectorAll('button, [role="button"], label, a, div, p, span, h1, h2, h3'));
          const texts = nodes.map(e => (e.innerText || '').toLowerCase()).filter(Boolean);
          const hasUploadish = texts.some(t => /(upload|attach|choose file|select file)/.test(t));
          const hasResumeish = texts.some(t => /(resume|cv)/.test(t));
          if (hasUploadish && hasResumeish) return true;
          const autofill = texts.some(t => /autofill/.test(t));
          return hasUploadish && autofill;
        }
        """
    )


async def _detect_submit_application_signal(page: Page) -> bool:
    return await page.evaluate(
        """
        () => {
          const texts = Array.from(document.querySelectorAll('button, [role="button"], a, div'))
            .map(e => (e.innerText || '').toLowerCase()).filter(Boolean);
          return texts.some(t => /submit\s+application/.test(t));
        }
        """
    )


async def extract_form_schema_from_page(page: Page, url: Optional[str] = None) -> FormSchema:
    fields = await _extract_fields_from_page(page)
    # Synthesize a file field if upload signal present but no visible file input found
    has_any_file = any(f.type == "file" for f in fields)
    if not has_any_file:
        try:
            signal = await _detect_upload_signal(page)
        except Exception:
            signal = False
        if signal:
            fields.append(
                FormField(
                    field_id="upload_0",
                    name=None,
                    label="Resume Upload",
                    placeholder=None,
                    type="file",
                    required=False,
                    options=[],
                    locators=Locator(),
                    meta={"synthetic": True, "visible": True},
                )
            )
    # Simple sectioning: one flat section for now
    section = FormSection(title=None, fields=fields)

    # Validity (live): prefer visible signals; allow upload text signals
    visible_fields = [f for f in fields if f.meta.get("visible", False)]
    file_like_visible = sum(1 for f in visible_fields if f.type == "file" or f.meta.get("hasDnd"))
    try:
        upload_signal = await _detect_upload_signal(page)
        submit_signal = await _detect_submit_application_signal(page)
    except Exception:
        upload_signal = False
        submit_signal = False
    common_personal = 0
    for f in visible_fields:
        name_l = (f.name or "").lower()
        label_l = (f.label or "").lower()
        placeholder_l = (f.placeholder or "").lower()
        hay = " ".join([name_l, label_l, placeholder_l])
        if (
            re.search(r"\bemail\b", hay)
            or re.search(r"\bphone|tel\b", hay)
            or ("first" in hay and "name" in hay)
            or ("last" in hay and "name" in hay)
        ):
            common_personal += 1
    file_like_any = file_like_visible > 0 or any(f.type == "file" for f in fields) or upload_signal
    is_valid = file_like_any and (common_personal >= 1 or submit_signal) and len(visible_fields) >= 3
    conf = min(1.0, 0.4 + 0.2 * (1 if file_like_any else 0) + 0.1 * common_personal + 0.02 * len(visible_fields)) if is_valid else 0.2

    schema = FormSchema(
        url=url,
        ats=None,
        sections=[section],
        validity=Validity(is_valid_job_application_form=is_valid, confidence=round(conf, 2)),
    )
    return schema


async def extract_form_schema_from_snapshot_dir(directory: Path) -> FormSchema:
    # Load main DOM, then iterate saved frame DOMs and aggregate fields
    ctx, page, manifest = await load_snapshot_as_page(directory)
    try:
        all_fields: List[FormField] = []
        upload_signal_any = False
        submit_signal_any = False
        # main page
        all_fields.extend(await _extract_fields_from_page(page))
        try:
            if await _detect_upload_signal(page):
                upload_signal_any = True
            if await _detect_submit_application_signal(page):
                submit_signal_any = True
        except Exception:
            pass

        # iterate frames by loading their DOM HTML into the same page context
        for fr in manifest.frames:
            dom_path = fr.get("dom_path") or fr.get("path")
            if not dom_path:
                continue
            dom_file = (directory / dom_path)
            if not dom_file.exists():
                continue
            try:
                html = dom_file.read_text(encoding="utf-8")
            except Exception:
                continue
            await page.set_content(html, wait_until="domcontentloaded")
            all_fields.extend(await _extract_fields_from_page(page))
            try:
                if await _detect_upload_signal(page):
                    upload_signal_any = True
                if await _detect_submit_application_signal(page):
                    submit_signal_any = True
            except Exception:
                pass

        # Build schema and compute validity (prefer visible signals)
        section = FormSection(title=None, fields=all_fields)
        visible_fields = [f for f in all_fields if f.meta.get("visible", False)]
        file_like_visible = sum(1 for f in visible_fields if f.type == "file" or f.meta.get("hasDnd"))
        common_personal = 0
        for f in visible_fields:
            name_l = (f.name or "").lower()
            label_l = (f.label or "").lower()
            placeholder_l = (f.placeholder or "").lower()
            hay = " ".join([name_l, label_l, placeholder_l])
            if (
                re.search(r"\bemail\b", hay)
                or re.search(r"\bphone|tel\b", hay)
                or ("first" in hay and "name" in hay)
                or ("last" in hay and "name" in hay)
            ):
                common_personal += 1
        # Use any upload signal across DOMs and accept hidden file inputs
        file_like_any = (
            file_like_visible > 0
            or any(f.type == "file" for f in all_fields)
            or upload_signal_any
        )
        is_valid = file_like_any and (common_personal >= 1 or submit_signal_any) and len(visible_fields) >= 3
        conf = min(1.0, 0.4 + 0.2 * file_like_visible + 0.1 * common_personal + 0.02 * len(visible_fields)) if is_valid else 0.2

        return FormSchema(
            url=manifest.url,
            ats=None,
            sections=[section],
            validity=Validity(is_valid_job_application_form=is_valid, confidence=round(conf, 2)),
        )
    finally:
        await ctx.close()


