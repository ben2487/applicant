from __future__ import annotations
import base64
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from eliot import start_action as _eliot_start_action, log_message as _eliot_log_message, to_file as _eliot_to_file


# Logging levels (simple numeric ordering)
LEVELS: Dict[str, int] = {"TRACE": 5, "DEBUG": 10, "INFO": 20}


@dataclass
class TraceConfig:
    run_id: str
    log_path: Path
    min_level: int
    enabled: bool = True
    llm_log_raw: bool = True
    common_fields: Dict[str, Any] | None = None


_CONFIG: Optional[TraceConfig] = None


def _now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def init_tracing(*, run_name: str, log_path: Path, min_level: str = "INFO", llm_log_raw: bool = True, common_fields: Dict[str, Any] | None = None) -> TraceConfig:
    """
    Initialize Eliot to write JSONL to log_path and set global config.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # open in append-binary to_file wants a file-like
    f = open(log_path, "ab")
    _eliot_to_file(f)
    cfg = TraceConfig(
        run_id=f"{run_name}-{int(time.time())}",
        log_path=log_path,
        min_level=LEVELS.get(min_level.upper(), LEVELS["INFO"]),
        enabled=True,
        llm_log_raw=llm_log_raw,
        common_fields=common_fields or {},
    )
    global _CONFIG
    _CONFIG = cfg
    event("RUN", "INFO", "trace_initialized", run_name=run_name, log_path=str(log_path))
    return cfg


def _should(level: str) -> bool:
    if not _CONFIG or not _CONFIG.enabled:
        return False
    return LEVELS.get(level.upper(), LEVELS["INFO"]) >= _CONFIG.min_level


def event(category: str, level: str, message_type: str, /, **fields: Any) -> None:
    if not _should(level):
        return
    body: Dict[str, Any] = {
        "category": category,
        "level": level,
        "ts": _now_ts(),
        "message_type": message_type,
    }
    if _CONFIG and _CONFIG.common_fields:
        body.update(_CONFIG.common_fields)
        body["run_id"] = _CONFIG.run_id
    body.update(fields)
    _eliot_log_message(**body)


def json_blob(category: str, level: str, name: str, payload: Any) -> None:
    if not _should(level):
        return
    try:
        pretty = json.dumps(payload, indent=2, ensure_ascii=False)
    except Exception:
        pretty = str(payload)
    event(category, level, "json", name=name, text=pretty)


def image(category: str, level: str, name: str, data_bytes: bytes, mime: str = "image/png") -> None:
    if not _should(level):
        return
    b64 = base64.b64encode(data_bytes).decode("ascii")
    data_uri = f"data:{mime};base64,{b64}"
    event(category, level, "image", name=name, data_uri=data_uri)


def text(category: str, level: str, name: str, text_value: str) -> None:
    if not _should(level):
        return
    event(category, level, "text", name=name, text=text_value)


class _ConsoleTee:
    def __init__(self, stream_name: str, original):
        self._name = stream_name
        self._orig = original
        self._buf = []

    def write(self, s: str):
        # Ensure text type
        if isinstance(s, (bytes, bytearray)):
            try:
                s = s.decode("utf-8", "replace")  # type: ignore[assignment]
            except Exception:
                s = str(s)
        try:
            self._orig.write(s)
        except Exception:
            pass
        # buffer by lines to avoid flooding
        self._buf.append(s)
        if "\n" in s:
            # coerce all items to str just in case
            joined = "".join(str(part) for part in self._buf)
            self._buf.clear()
            # split into lines and log each non-empty
            for line in joined.splitlines():
                if line.strip():
                    event("CONSOLE", "INFO", "console", stream=self._name, text=line)

    def flush(self):
        try:
            self._orig.flush()
        except Exception:
            pass


def enable_console_capture() -> None:
    """Mirror all stdout/stderr into tracing as CONSOLE events in real time."""
    import sys
    try:
        if not hasattr(sys.stdout, "_is_tracing_tee"):
            tee_out = _ConsoleTee("stdout", sys.stdout)
            tee_out._is_tracing_tee = True  # type: ignore[attr-defined]
            sys.stdout = tee_out  # type: ignore[assignment]
        if not hasattr(sys.stderr, "_is_tracing_tee"):
            tee_err = _ConsoleTee("stderr", sys.stderr)
            tee_err._is_tracing_tee = True  # type: ignore[attr-defined]
            sys.stderr = tee_err  # type: ignore[assignment]
    except Exception:
        # Non-fatal if console capture fails
        pass


@contextmanager
def action(action_type: str, *, category: str, **fields: Any):
    extra: Dict[str, Any] = {"category": category}
    if _CONFIG and _CONFIG.common_fields:
        extra.update(_CONFIG.common_fields)
        extra["run_id"] = _CONFIG.run_id
    extra.update(fields)
    with _eliot_start_action(action_type=action_type, **extra):
        yield


def generate_html_report(log_path: Path, out_html: Path) -> None:
    """
    Convert Eliot JSONL into a single-file collapsible HTML report.
    This is intentionally simple: uses task_level depth for indentation.
    """
    lines: list[dict] = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            lines.append(obj)

    def escape(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    html_parts: list[str] = []
    html_parts.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
    html_parts.append("<title>Trace Report</title>")
    html_parts.append(
        "<style>"
        "body{font-family:Segoe UI,system-ui,Arial,sans-serif;margin:0;padding:0 12px;}"
        ".msg{margin:2px 0;display:flex;gap:6px;align-items:baseline;}"
        ".time{color:#666;margin-right:6px;min-width:140px;display:inline-block;}"
        ".cat{font-weight:600;margin-right:6px;min-width:90px;display:inline-block;}"
        ".lvl{font-size:11px;border-radius:4px;padding:1px 6px;margin-right:6px;min-width:54px;display:inline-block;text-align:center;}"
        ".lvl.INFO{background:#e8f5e9;color:#2e7d32;} .lvl.DEBUG{background:#e3f2fd;color:#1565c0;} .lvl.TRACE{background:#f3e5f5;color:#6a1b9a;}"
        "details{margin-left: 12px;}"
        "pre{background:#0b1021;color:#e6edf3;padding:8px;border-radius:6px;overflow:auto;}"
        "img{max-width:100%;border:1px solid #ddd;border-radius:6px;}"
        ".console-text{font-family:ui-monospace, SFMono-Regular, Menlo, monospace;white-space:pre;display:inline-block;}"
        "</style>"
    )
    html_parts.append(
        "<script>function cls(tag){var el=document.getElementById(tag);if(el){el.open=!el.open}}</script>"
    )
    html_parts.append("</head><body>")
    html_parts.append(f"<h2>Trace Report</h2><div class='msg'>Source: {escape(str(log_path))}</div>")

    # Render entries with nesting by task_level length
    prev_depth = 0
    stack_open = 0
    for obj in lines:
        depth = 0
        try:
            tl = obj.get("task_level")
            if isinstance(tl, list):
                depth = max(0, len(tl) - 1)
        except Exception:
            depth = 0

        while stack_open > depth:
            html_parts.append("</details>")
            stack_open -= 1

        cat = escape(str(obj.get("category", obj.get("message_type", obj.get("action_type", "LOG")))))
        lvl = escape(str(obj.get("level", "INFO")))
        ts = escape(str(obj.get("ts", "")))

        if "action_type" in obj and obj.get("action_status") == "started":
            at = escape(str(obj.get("action_type")))
            summ = escape(json.dumps({k: v for k, v in obj.items() if k not in {"task_level","action_type","action_status","task_uuid"}}, ensure_ascii=False))
            html_parts.append(
                f"<details open><summary><span class='time'>{ts}</span><span class='lvl {lvl}'>{lvl}</span><span class='cat'>{cat}</span> action: <b>{at}</b></summary><div class='block'>"
            )
            stack_open += 1
            continue

        if obj.get("message_type") == "image" and obj.get("data_uri"):
            name = escape(str(obj.get("name", "screenshot")))
            html_parts.append(
                f"<div class='msg'><span class='time'>{ts}</span><span class='lvl {lvl}'>{lvl}</span><span class='cat'>{cat}</span> <b>{name}</b><br/><img src='{obj.get('data_uri')}'/></div>"
            )
            continue

        # Pretty-print textual payload when present (JSON, text, console, etc.)
        if "text" in obj and isinstance(obj["text"], str):
            payload_text = obj["text"]
            if cat == "CONSOLE":
                # Single line with console text to preserve ASCII art alignment
                html_parts.append(
                    f"<div class='msg'><span class='time'>{ts}</span><span class='lvl {lvl}'>{lvl}</span><span class='cat'>{cat}</span><span class='console-text'>{escape(payload_text)}</span></div>"
                )
            else:
                html_parts.append(
                    f"<div class='msg'><span class='time'>{ts}</span><span class='lvl {lvl}'>{lvl}</span><span class='cat'>{cat}</span></div><pre>{escape(payload_text)}</pre>"
                )
            continue

        # Fallback: compact key subset
        summary = {k: v for k, v in obj.items() if k in {"message_type","name","url","selector","detail","stream","text"}}
        if summary:
            payload = escape(json.dumps(summary, ensure_ascii=False))
        else:
            payload = escape(json.dumps(obj, ensure_ascii=False)[:2000])
        html_parts.append(
            f"<div class='msg'><span class='time'>{ts}</span><span class='lvl {lvl}'>{lvl}</span><span class='cat'>{cat}</span> {payload}</div>"
        )

    while stack_open > 0:
        html_parts.append("</details>")
        stack_open -= 1

    html_parts.append("</body></html>")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text("".join(html_parts), encoding="utf-8")


