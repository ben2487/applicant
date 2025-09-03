from __future__ import annotations

from typing import Dict, Any, List, Optional

from .schema import FormSchema, FormField
from ..ai_search import get_openai_client
from ..tracing import json_blob, event


def _build_fields_brief(schema: FormSchema) -> List[Dict[str, Any]]:
    brief: List[Dict[str, Any]] = []
    for section in schema.sections:
        for f in section.fields:
            brief.append(
                {
                    "field_id": f.field_id,
                    "type": f.type,
                    "label": f.label,
                    "placeholder": f.placeholder,
                    "name": f.name,
                    "required": bool(f.required),
                    "options": list(f.options or []),
                }
            )
    return brief


def _compose_prompt(
    *,
    fields_brief: List[Dict[str, Any]],
    resume_text: str,
    job_context: Optional[str],
    ignore_optional: bool,
) -> str:
    lines: List[str] = []
    lines.append(
        "You are given a parsed job application form structure and a candidate resume.\n"
        "Return answers for the fields as a compact JSON object with the shape:\n"
        "{\n  \"answers\": { \"<field_id>\": <value> },\n  \"unanswerable\": [<field_id>...]\n}\n\n"
        "Rules:\n"
        "- Only return JSON. No commentary outside JSON.\n"
        "- For checkboxes/radios, use string 'true' or 'false'.\n"
        "- For dates, prefer 'YYYY-MM-DD' if a date is needed.\n"
        "- For selects/comboboxes, prefer one of the provided options; if none provided, infer a concise value.\n"
        "- Do not fabricate unknown facts; if not answerable, omit from answers and list in unanswerable.\n"
    )
    if ignore_optional:
        lines.append("- Ignore optional fields unless trivial (name/email/phone).\n")
    else:
        lines.append("- Optional fields may be answered when high-confidence.\n")
    lines.append("")
    lines.append("[Form Fields]\n")
    for f in fields_brief:
        opts = ", ".join(f.get("options") or [])
        lines.append(
            f"- id={f['field_id']} | type={f['type']} | required={f['required']} | "
            f"label={f.get('label') or ''} | placeholder={f.get('placeholder') or ''} | options=[{opts}]"
        )
    lines.append("")
    if job_context:
        lines.append("[Job Context]\n")
        lines.append(job_context.strip())
        lines.append("")
    lines.append("[Resume]\n")
    lines.append(resume_text.strip())
    lines.append("")
    lines.append(
        "Return only valid JSON object with keys 'answers' and 'unanswerable'."
    )
    return "\n".join(lines)


def generate_answers(
    schema: FormSchema,
    *,
    resume_text: str,
    job_context: Optional[str] = None,
    ignore_optional: bool = True,
    model: str = "gpt-4o",
) -> FormSchema:
    """
    Populate FormSchema fields' meta["answer"] using an LLM, based on the provided
    resume text and optional job context. Returns the same schema object with
    answers filled where applicable.
    """
    fields_brief = _build_fields_brief(schema)

    # Safety trims: cap resume and context size to keep prompts reasonable
    max_chars = 12000
    resume_short = (resume_text or "")[:max_chars]
    job_short = (job_context or "")[:6000]

    prompt = _compose_prompt(
        fields_brief=fields_brief,
        resume_text=resume_short,
        job_context=job_short or None,
        ignore_optional=ignore_optional,
    )

    client = get_openai_client()
    # Log prompt
    json_blob("LLM", "DEBUG", "form_answer_prompt", {"model": model, "prompt": prompt})
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise application-filling assistant. Return strictly JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=900,
    )

    raw = resp.choices[0].message.content or "{}"
    # Log raw response
    json_blob("LLM", "DEBUG", "form_answer_response", {"model": model, "response": raw})
    import json

    data: Dict[str, Any]
    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    answers: Dict[str, Any] = {}
    if isinstance(data, dict):
        maybe = data.get("answers")
        if isinstance(maybe, dict):
            answers = maybe

    # Fill into schema
    answer_count = 0
    for section in schema.sections:
        for f in section.fields:
            if f.field_id in answers:
                val = answers[f.field_id]
                # Normalize booleanish to expected string for checkboxes/radios
                if f.type in {"checkbox", "radio"}:
                    sval = str(val).strip().lower()
                    f.meta["answer"] = "true" if sval in {"1", "true", "yes", "on"} else "false"
                else:
                    f.meta["answer"] = str(val)
                answer_count += 1

    # Attach a minimal summary into schema validity meta for debugging
    try:
        if hasattr(schema, "validity") and schema.validity and isinstance(schema.validity.meta, dict):
            schema.validity.meta["llm_answered_fields"] = answer_count
    except Exception:
        pass

    event("LLM", "INFO", "form_answers_summary", answered_fields=answer_count)

    return schema


