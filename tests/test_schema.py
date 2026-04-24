from datetime import date

import pytest
from pydantic import ValidationError

from mcp_server.schema import Scenario, StockAnalysisResult


def _make(base_p=0.55, bull_p=0.25, bear_p=0.20, bear_price=2600.0, base_price=2900.0, bull_price=3150.0):
    return StockAnalysisResult(
        stock_code="7203",
        horizon_days=30,
        as_of=date(2026, 4, 24),
        last_close=2845.5,
        summary="Toyota faces FX headwinds from a stronger yen.",
        base=Scenario(price=base_price, probability=base_p, rationale="Base case rationale here."),
        bull=Scenario(price=bull_price, probability=bull_p, rationale="Bull case rationale here."),
        bear=Scenario(price=bear_price, probability=bear_p, rationale="Bear case rationale here."),
    )


def test_happy_path():
    r = _make()
    assert r.base.probability + r.bull.probability + r.bear.probability == pytest.approx(1.0)


def test_probabilities_must_sum_to_one():
    with pytest.raises(ValidationError):
        _make(base_p=0.4, bull_p=0.4, bear_p=0.4)


def test_price_ordering_enforced():
    with pytest.raises(ValidationError):
        _make(bear_price=3200.0)  # bear above bull


def test_stock_code_must_be_digits():
    with pytest.raises(ValidationError):
        StockAnalysisResult(
            stock_code="ABCD",
            horizon_days=30,
            as_of=date(2026, 4, 24),
            last_close=100.0,
            summary="Twenty characters at least here.",
            base=Scenario(price=100, probability=0.5, rationale="rationale text"),
            bull=Scenario(price=120, probability=0.3, rationale="rationale text"),
            bear=Scenario(price=80, probability=0.2, rationale="rationale text"),
        )
