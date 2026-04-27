from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_LOCK = threading.Lock()

_HEADER = (
    "# MCP Tool Interaction Log\n\n"
    "Append-only record of every prompt received by the SmartTools MCP server\n"
    "and every response (or error) it returned. One file per UTC day.\n\n"
)


def _resolve_log_dir() -> Path:
    override = os.getenv("MCP_LOG_DIR", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "logs"


def _today_log_path() -> Path:
    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return log_dir / f"mcp_log_{today}.md"


def _ensure_header(path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.write_text(_HEADER, encoding="utf-8")


def _format_arguments(arguments: dict[str, Any]) -> str:
    if not arguments:
        return "_(no arguments)_\n"
    lines = []
    for key, value in arguments.items():
        rendered = json.dumps(value, ensure_ascii=False, default=str)
        lines.append(f"- `{key}`: `{rendered}`")
    return "\n".join(lines) + "\n"


def _format_json_block(payload: Any) -> str:
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return f"```json\n{body}\n```\n"


def log_interaction(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    response: Any | None = None,
    error: str | None = None,
) -> None:
    """Append a prompt/response (or prompt/error) entry to today's Markdown log."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    path = _today_log_path()

    parts = [
        f"## {timestamp} — `{tool_name}`\n",
        "### Prompt\n",
        _format_arguments(arguments),
    ]
    if error is not None:
        parts.extend(["\n### Error\n", f"```\n{error}\n```\n"])
    else:
        parts.extend(["\n### Response\n", _format_json_block(response)])
    parts.append("\n---\n\n")
    entry = "\n".join(parts)

    with _LOG_LOCK:
        _ensure_header(path)
        with path.open("a", encoding="utf-8") as f:
            f.write(entry)
