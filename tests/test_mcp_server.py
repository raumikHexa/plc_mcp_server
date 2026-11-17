"""MCP server tests using the SDK's in-memory client (no network or running server needed)."""

from typing import Any

import anyio
import pytest
from mcp.client import Client

from app.mcp_server.server import mcp, transport_security

EXPECTED_TOOLS = {
    "search_products",
    "get_product_details",
    "search_faqs",
    "get_company_info",
    "search_documents",
    "search_fragrances",
}


def call(tool: str, arguments: dict[str, Any] | None = None) -> Any:
    """Call a tool through a real MCP client session and return the raw result."""

    async def run() -> Any:
        async with Client(mcp) as client:
            return await client.call_tool(tool, arguments or {})

    return anyio.run(run)


def list_tools() -> list[Any]:
    async def run() -> list[Any]:
        async with Client(mcp) as client:
            return (await client.list_tools()).tools

    return anyio.run(run)


def test_exactly_the_six_expected_tools_are_exposed() -> None:
    assert {tool.name for tool in list_tools()} == EXPECTED_TOOLS


def test_every_tool_is_read_only_and_described() -> None:
    for tool in list_tools():
        assert tool.annotations.read_only_hint is True, tool.name
        assert tool.annotations.destructive_hint is False, tool.name
        assert tool.description and len(tool.description) > 50, tool.name


def test_no_tool_accepts_a_path_argument() -> None:
    for tool in list_tools():
        params = set(tool.input_schema.get("properties", {}))
        assert params <= {"query", "product_id"}, f"{tool.name} has unexpected params {params}"


def test_search_products_returns_structured_results() -> None:
    result = call("search_products", {"query": "matte black reed diffuser"})
    assert not result.is_error
    first = result.structured_content["result"][0]
    assert first["product_line"] == "Reed Diffuser"
    assert first["url"].startswith("https://privatelabelcandles.com/products/")


def test_get_product_details() -> None:
    result = call("get_product_details", {"product_id": "9-oz-jar"})
    assert result.structured_content["name"] == "9 oz Candle"


def test_unknown_product_gives_helpful_error_to_the_ai() -> None:
    result = call("get_product_details", {"product_id": "does-not-exist"})
    assert result.is_error
    assert "was not found" in result.content[0].text


def test_meaningless_query_gives_helpful_error() -> None:
    result = call("search_faqs", {"query": "the"})
    assert result.is_error
    assert "meaningful search keyword" in result.content[0].text


@pytest.mark.parametrize(
    ("tool", "query", "check"),
    [
        ("search_faqs", "rush service", lambda r: "rush" in r[0]["question"].lower()),
        ("search_fragrances", "vanilla", lambda r: len(r) > 0),
        ("search_documents", "rush expedite", lambda r: r[0]["filename"] == "company_profile.pdf"),
    ],
)
def test_search_tools(tool: str, query: str, check: Any) -> None:
    result = call(tool, {"query": query})
    assert not result.is_error
    assert check(result.structured_content["result"])


def test_get_company_info() -> None:
    result = call("get_company_info")
    assert result.structured_content["name"] == "Private Label Candles"


def test_transport_security_always_allows_localhost() -> None:
    security = transport_security()
    assert security.enable_dns_rebinding_protection
    assert "localhost:*" in security.allowed_hosts
