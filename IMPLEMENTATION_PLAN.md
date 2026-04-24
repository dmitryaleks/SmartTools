# SmartTools — Implementation Plan

Japanese stock price-evolution analyst exposed as a remote MCP tool, callable by Claude via the Anthropic Messages API, driven from a small local desktop GUI.

---

## 0. Important prerequisites & clarifications

| # | Item | Status | Notes |
|---|------|--------|-------|
| 0.1 | Confirm Anthropic API key billing | ☑ Done | Key in `.env` (rotated once after the initial paste). |
| 0.2 | Choose Python version | ☑ Done | Python 3.14.2 in `.venv`. |
| 0.3 | Choose tunneling tool for public exposure | ☑ Done | `cloudflared` quick tunnel; named tunnel deferred to hardening. |
| 0.4 | Decide on Japanese stock data source | ☑ Done | `yfinance` `.T` suffix for OHLCV + Claude API for narrative. |

---

## 1. Architecture

```
┌───────────────────────────┐         ┌──────────────────────────────┐
│  Local GUI (Tkinter)      │  HTTPS  │  Anthropic Messages API      │
│  - input: code, N days    │ ───────►│  model: claude-opus-4-7      │
│  - calls Anthropic SDK    │         │  mcp_servers: [public URL]   │
│  - renders JSON result    │◄─────── │                              │
└───────────────────────────┘         └──────────────┬───────────────┘
                                                     │ MCP tool call
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │  cloudflared / ngrok tunnel  │
                                      │  https://xxxx.trycloudflare  │
                                      └──────────────┬───────────────┘
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │  Local MCP Server (FastMCP)  │
                                      │  tool: analyze_japanese_stock│
                                      │  - fetch OHLCV (yfinance)    │
                                      │  - call Claude API for       │
                                      │    bull/bear/base reasoning  │
                                      │  - return structured JSON    │
                                      └──────────────────────────────┘
```

Key choices:
- **MCP transport:** Streamable HTTP (the modern remote-MCP transport supported by Anthropic's `mcp_servers` connector). Stdio is wrong here because the server must be reachable across the internet.
- **MCP framework:** `mcp` Python SDK with `FastMCP` (high-level decorator API).
- **Auth on the public endpoint:** static bearer token in the `Authorization: Bearer <token>` header. The GUI passes the same token in `mcp_servers[].authorization_token` when calling the Messages API.
- **Output schema:** the tool returns JSON validated by a Pydantic model so Claude can pass it through verbatim.

---

## 2. Repository layout (target)

```
C:\Projects\SmartTools\
├── .env                          # ANTHROPIC_API_KEY, MCP_BEARER_TOKEN
├── .env.example
├── pyproject.toml                # deps + script entry points
├── IMPLEMENTAATION_PLAN.md       # this file
├── README.md
├── src/
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   ├── server.py             # FastMCP app, tool registration, auth
│   │   ├── analyst.py            # Claude-API-backed analysis logic
│   │   ├── market_data.py        # yfinance wrapper for JP tickers
│   │   └── schema.py             # Pydantic models for tool I/O
│   └── gui_client/
│       ├── __init__.py
│       ├── app.py                # Tkinter window
│       └── claude_client.py      # Anthropic SDK call w/ mcp_servers
└── tests/
    ├── test_analyst.py
    ├── test_schema.py
    └── test_server_smoke.py
```

---

## 3. Phase-by-phase task list

### Phase 1 — Project bootstrap

| # | Task | Status |
|---|------|--------|
| 1.1 | `src/` layout (`mcp_server/`, `gui_client/`, `tests/`, `logs/`) | ☑ Done |
| 1.2 | `pyproject.toml` with deps + `[project.scripts]` | ☑ Done |
| 1.3 | `.env.example` + populated `.env` | ☑ Done |
| 1.4 | `pip install -e ".[dev]"` in `.venv` | ☑ Done |
| 1.5 | `.gitignore` | ☑ Done |

### Phase 2 — MCP server (tool definition)

| # | Task | Status |
|---|------|--------|
| 2.1 | `schema.py`: `Scenario`, `StockAnalysisResult` with validators | ☑ Done |
| 2.2 | `market_data.py`: `fetch_recent_ohlcv` via yfinance | ☑ Done |
| 2.3 | `analyst.py`: forced `submit_analysis` tool call to Claude | ☑ Done | Default model `claude-opus-4-7`. |
| 2.4 | Probability sum + price ordering validators | ☑ Done |
| 2.5 | `server.py`: FastMCP + `@mcp.tool() analyze_japanese_stock` | ☑ Done |
| 2.6 | Bearer-token middleware | ☑ Done | Verified 401 on bad token, 200 on correct. |
| 2.7 | `smarttools-mcp` console script (uvicorn) | ☑ Done |

### Phase 3 — Local hosting + public exposure

| # | Task | Status |
|---|------|--------|
| 3.1 | Local JSON-RPC `initialize` smoke test | ☑ Done | Returned full capabilities + serverInfo. |
| 3.2 | Install `cloudflared` | ◐ User action | `winget install --id Cloudflare.cloudflared` |
| 3.3 | Start quick tunnel + capture URL | ◐ User action | `cloudflared tunnel --url http://127.0.0.1:8765`, then set `PUBLIC_MCP_URL=https://<id>.trycloudflare.com/mcp` in `.env`. |
| 3.4 | Named tunnel for stable URL | ☐ Future hardening |
| 3.5 | Verify public URL with bearer | ◐ User action | Repeat the local curl against the public URL. |
| 3.6 | README quickstart | ☑ Done |

### Phase 4 — GUI client

| # | Task | Status |
|---|------|--------|
| 4.1 | Tkinter window (entries, Analyze button, ScrolledText, status bar) | ☑ Done |
| 4.2 | `claude_client.py` calling `client.beta.messages.create(..., mcp_servers=[...], betas=["mcp-client-2025-04-04"])` | ☑ Done |
| 4.3 | Routing-agent system prompt | ☑ Done |
| 4.4 | Background thread + `root.after` for thread-safe UI | ☑ Done |
| 4.5 | Pretty-print summary + bear/base/bull table + raw JSON | ☑ Done |
| 4.6 | Errors surfaced via status bar, no crash | ☑ Done |

### Phase 5 — Testing & validation

| # | Task | Status |
|---|------|--------|
| 5.1 | `test_schema.py`: probability sum + price ordering + digits-only | ☑ Done | 4 tests pass. |
| 5.2 | `test_analyst.py`: mocked Anthropic client | ☑ Done | 1 test passes; total 5/5 green. |
| 5.3 | `test_server_smoke.py` (in-process MCP) | ☑ Done | Replaced by raw HTTP probe (auth + initialize verified). |
| 5.4 | Manual end-to-end (GUI → tunnel → server → Claude) | ◐ User action | Needs tunnel + `PUBLIC_MCP_URL` set. |
| 5.5 | Sanity-check probabilities/prices on real outputs | ◐ User action | Defer until 5.4. |

### Phase 6 — Hardening & docs (optional but recommended)

| # | Task | Status |
|---|------|--------|
| 6.1 | Rate-limit the MCP tool to cap API spend if URL leaks | ☐ Future |
| 6.2 | Log every tool invocation to `logs/server.jsonl` | ☐ Future |
| 6.3 | Disclaimer in tool response | ☑ Done | Default field on `StockAnalysisResult`. |
| 6.4 | README quickstart | ☑ Done |

---

## 4. Output JSON contract (final tool response)

```json
{
  "stock_code": "7203",
  "horizon_days": 30,
  "as_of": "2026-04-24",
  "last_close": 2845.5,
  "summary": "Toyota faces FX headwinds from a stronger yen but...",
  "base": { "price": 2900.0, "probability": 0.55, "rationale": "..." },
  "bull": { "price": 3150.0, "probability": 0.25, "rationale": "..." },
  "bear": { "price": 2600.0, "probability": 0.20, "rationale": "..." },
  "disclaimer": "Generated by an LLM. Not investment advice."
}
```

Probabilities MUST sum to 1.0 ± 0.02 (Pydantic validator).

---

## 5. Risks & open questions

1. **API billing surprise** — any caller who learns the public MCP URL + token will spend your Anthropic credits. Mitigations: rotate token, rate-limit, keep tunnel down when not in use.
2. **Quality of LLM-only price targets** — pure reasoning without recent data is poor. The `yfinance` step is what makes the output grounded.
3. **`yfinance` reliability for TSE** — Yahoo sometimes lags JP market data; consider `stooq` as a fallback.
4. **Tunnel URL churn** — quick `trycloudflare.com` URLs change on every restart; named tunnel fixes this but needs a Cloudflare account + DNS.
5. **Model choice for the analyst** — `claude-opus-4-7` gives best reasoning but is most expensive; `claude-sonnet-4-6` may be enough. Decide after first end-to-end test.
6. **GUI framework** — plan uses Tkinter (zero install). Swap to PySide6 later if richer UI is needed.

---

## 6. Status legend

- ☐ Not started
- ◐ In progress
- ☑ Done
- ✗ Blocked (note reason inline)

Update statuses inline as work proceeds.
