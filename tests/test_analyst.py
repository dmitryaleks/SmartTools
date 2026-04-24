from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from mcp_server import analyst
from mcp_server.market_data import OHLCVSnapshot


class _FakeAnthropic:
    def __init__(self):
        self.messages = self
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        tool_use = SimpleNamespace(
            type="tool_use",
            name="submit_analysis",
            input={
                "summary": "Stable trend with mild upside; volume steady.",
                "base": {"price": 2900.0, "probability": 0.55, "rationale": "Base rationale text."},
                "bull": {"price": 3150.0, "probability": 0.25, "rationale": "Bull rationale text."},
                "bear": {"price": 2600.0, "probability": 0.20, "rationale": "Bear rationale text."},
            },
        )
        return SimpleNamespace(content=[tool_use], stop_reason="tool_use")


def test_analyze_uses_submit_tool_and_builds_result():
    fake_snapshot = OHLCVSnapshot(
        code="7203",
        as_of=date(2026, 4, 24),
        last_close=2845.5,
        history_csv="Date,Open,High,Low,Close,Volume\n2026-04-23,2840,2850,2830,2845.5,1000\n",
    )

    fake = _FakeAnthropic()
    with patch.object(analyst, "fetch_recent_ohlcv", return_value=fake_snapshot):
        result = analyst.analyze("7203", 30, client=fake)

    assert result.stock_code == "7203"
    assert result.horizon_days == 30
    assert result.last_close == 2845.5
    assert result.bull.price > result.base.price > result.bear.price
    assert fake.last_kwargs["tool_choice"] == {"type": "tool", "name": "submit_analysis"}
