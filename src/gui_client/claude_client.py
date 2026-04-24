from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

CLIENT_MODEL = os.getenv("CLIENT_MODEL", "claude-opus-4-7")
MCP_BETA_HEADER = "mcp-client-2025-04-04"


def _system_prompt() -> str:
    return (
        "You are a routing agent. The user will give you a Japanese stock code "
        "(4-digit TSE number) and a forecast horizon in days. You MUST call the "
        "`analyze_japanese_stock` MCP tool exactly once with those exact inputs, "
        "then return the tool's JSON response verbatim as your final assistant message. "
        "Do not add commentary, do not reformat — output the raw JSON object only."
    )


def request_analysis(stock_code: str, days: int) -> dict[str, Any]:
    public_url = os.environ["PUBLIC_MCP_URL"]
    bearer = os.environ["MCP_BEARER_TOKEN"]

    client = Anthropic()
    response = client.beta.messages.create(
        model=CLIENT_MODEL,
        max_tokens=2048,
        system=_system_prompt(),
        mcp_servers=[
            {
                "type": "url",
                "url": public_url,
                "name": "smarttools",
                "authorization_token": bearer,
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Stock code: {stock_code}\n"
                    f"Horizon: {days} days\n\n"
                    "Call analyze_japanese_stock and return its JSON."
                ),
            }
        ],
        betas=[MCP_BETA_HEADER],
    )

    for block in reversed(response.content):
        if getattr(block, "type", None) == "text":
            text = block.text.strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
        if getattr(block, "type", None) == "mcp_tool_result":
            for item in getattr(block, "content", []) or []:
                if getattr(item, "type", None) == "text":
                    try:
                        return json.loads(item.text)
                    except json.JSONDecodeError:
                        continue

    raise RuntimeError(
        f"No JSON payload found in Claude's response. stop_reason={response.stop_reason}"
    )
