from __future__ import annotations

import json
import os
from typing import Any

from anthropic import Anthropic

from .market_data import OHLCVSnapshot, fetch_recent_ohlcv
from .schema import StockAnalysisResult

ANALYST_MODEL = os.getenv("ANALYST_MODEL", "claude-opus-4-7")

SYSTEM_PROMPT = """You are a senior equity analyst covering Japanese stocks listed on the Tokyo Stock Exchange.
Given recent OHLCV history and a forecast horizon, produce a base / bull / bear price scenario for the
end of the horizon. Be quantitative: cite the last close, then justify each scenario from observable
patterns in the supplied history (trend, volatility, volume). Probabilities must sum to 1.0.
Bear price must be below base, base below bull. Keep each rationale under 600 characters.
Always emit your final answer through the `submit_analysis` tool — never as plain text."""

SUBMIT_TOOL_SCHEMA: dict[str, Any] = {
    "name": "submit_analysis",
    "description": "Return the final structured stock analysis to the caller.",
    "input_schema": {
        "type": "object",
        "required": ["summary", "base", "bull", "bear"],
        "properties": {
            "summary": {"type": "string", "minLength": 20, "maxLength": 2000},
            "base": {"$ref": "#/$defs/scenario"},
            "bull": {"$ref": "#/$defs/scenario"},
            "bear": {"$ref": "#/$defs/scenario"},
        },
        "$defs": {
            "scenario": {
                "type": "object",
                "required": ["price", "probability", "rationale"],
                "properties": {
                    "price": {"type": "number", "exclusiveMinimum": 0},
                    "probability": {"type": "number", "minimum": 0, "maximum": 1},
                    "rationale": {"type": "string", "minLength": 10, "maxLength": 800},
                },
            }
        },
    },
}


def _build_user_prompt(snapshot: OHLCVSnapshot, days: int) -> str:
    return (
        f"Stock code: {snapshot.code} (TSE)\n"
        f"As-of date: {snapshot.as_of.isoformat()}\n"
        f"Last close: JPY {snapshot.last_close:.2f}\n"
        f"Forecast horizon: {days} trading-day(s) from as-of\n\n"
        "Recent OHLCV (CSV):\n"
        "```csv\n"
        f"{snapshot.history_csv}"
        "```\n\n"
        "Produce base / bull / bear projected prices (JPY) at the horizon, each with a probability "
        "(summing to 1.0) and a short rationale grounded in the data above. Then call `submit_analysis`."
    )


def analyze(code: str, days: int, *, client: Anthropic | None = None) -> StockAnalysisResult:
    snapshot = fetch_recent_ohlcv(code)
    client = client or Anthropic()

    response = client.messages.create(
        model=ANALYST_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[SUBMIT_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_analysis"},
        messages=[{"role": "user", "content": _build_user_prompt(snapshot, days)}],
    )

    tool_block = next(
        (b for b in response.content if getattr(b, "type", None) == "tool_use"),
        None,
    )
    if tool_block is None:
        raise RuntimeError(
            "Analyst model did not call submit_analysis. "
            f"Stop reason: {response.stop_reason}"
        )

    payload = tool_block.input if isinstance(tool_block.input, dict) else json.loads(tool_block.input)
    return StockAnalysisResult(
        stock_code=snapshot.code,
        horizon_days=days,
        as_of=snapshot.as_of,
        last_close=snapshot.last_close,
        summary=payload["summary"],
        base=payload["base"],
        bull=payload["bull"],
        bear=payload["bear"],
    )
