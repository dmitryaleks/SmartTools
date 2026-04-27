from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .analyst import analyze
from .mcp_logger import log_interaction
from .schema import StockAnalysisResult


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _build_security_settings() -> TransportSecuritySettings:
    """Allow localhost + the public tunnel host (read from PUBLIC_MCP_URL)."""
    allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    allowed_origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]

    public_url = os.getenv("PUBLIC_MCP_URL", "").strip()
    if public_url:
        parsed = urlparse(public_url)
        if parsed.hostname:
            allowed_hosts.append(parsed.hostname)
            allowed_hosts.append(f"{parsed.hostname}:*")
            allowed_origins.append(f"{parsed.scheme}://{parsed.hostname}")
            allowed_origins.append(f"{parsed.scheme}://{parsed.hostname}:*")

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


mcp = FastMCP("smarttools-jp-analyst", transport_security=_build_security_settings())


@mcp.tool()
def analyze_japanese_stock(stock_code: str, days: int) -> dict:
    """Analyze a Tokyo Stock Exchange listed stock and return base/bull/bear price scenarios.

    Args:
        stock_code: 4-digit TSE code (e.g. "7203" for Toyota).
        days: Forecast horizon in trading days (1..365).

    Returns:
        StockAnalysisResult JSON: summary + {base,bull,bear}{price,probability,rationale}.
    """
    arguments = {"stock_code": stock_code, "days": days}
    try:
        if days <= 0 or days > 365:
            raise ValueError("days must be in 1..365")
        result: StockAnalysisResult = analyze(stock_code, days)
        response = result.model_dump(mode="json")
    except Exception as exc:
        log_interaction(
            tool_name="analyze_japanese_stock",
            arguments=arguments,
            error=f"{type(exc).__name__}: {exc}",
        )
        raise
    log_interaction(
        tool_name="analyze_japanese_stock",
        arguments=arguments,
        response=response,
    )
    return response


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, expected_token: str | None) -> None:
        super().__init__(app)
        self.expected_token = expected_token

    async def dispatch(self, request: Request, call_next):
        if not self.expected_token:
            return await call_next(request)
        header = request.headers.get("authorization", "")
        if header != f"Bearer {self.expected_token}":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def main() -> None:
    port = int(os.getenv("MCP_PORT", "8765"))
    token = os.getenv("MCP_BEARER_TOKEN") or None
    if not token:
        print("WARNING: MCP_BEARER_TOKEN is empty — server will accept ALL requests.")

    app = mcp.streamable_http_app()
    app.user_middleware.insert(0, Middleware(BearerAuthMiddleware, expected_token=token))
    app.middleware_stack = app.build_middleware_stack()

    print(f"Starting smarttools-jp-analyst MCP server on http://127.0.0.1:{port}/mcp")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
