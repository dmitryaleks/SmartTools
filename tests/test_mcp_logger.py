from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from mcp_server import mcp_logger


def _today_filename() -> str:
    return f"mcp_log_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"


def test_log_interaction_writes_prompt_and_response(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MCP_LOG_DIR", str(tmp_path))

    mcp_logger.log_interaction(
        tool_name="analyze_japanese_stock",
        arguments={"stock_code": "7203", "days": 30},
        response={"stock_code": "7203", "summary": "demo"},
    )

    log_path = tmp_path / _today_filename()
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "# MCP Tool Interaction Log" in content
    assert "analyze_japanese_stock" in content
    assert "### Prompt" in content
    assert '`stock_code`: `"7203"`' in content
    assert "### Response" in content
    assert '"summary": "demo"' in content


def test_log_interaction_records_errors(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MCP_LOG_DIR", str(tmp_path))

    mcp_logger.log_interaction(
        tool_name="analyze_japanese_stock",
        arguments={"stock_code": "7203", "days": 999},
        error="ValueError: days must be in 1..365",
    )

    content = (tmp_path / _today_filename()).read_text(encoding="utf-8")
    assert "### Error" in content
    assert "days must be in 1..365" in content
    assert "### Response" not in content


def test_log_interaction_appends_multiple_entries(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MCP_LOG_DIR", str(tmp_path))

    for code in ("7203", "9984"):
        mcp_logger.log_interaction(
            tool_name="analyze_japanese_stock",
            arguments={"stock_code": code, "days": 30},
            response={"stock_code": code},
        )

    content = (tmp_path / _today_filename()).read_text(encoding="utf-8")
    assert content.count("## ") >= 2
    assert "7203" in content and "9984" in content
    assert content.count("# MCP Tool Interaction Log") == 1
