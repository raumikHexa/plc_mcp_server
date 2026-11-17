import logging
from collections.abc import Iterator
from pathlib import Path

import anyio
import pytest
from mcp.client import Client

from app.logging_config import setup_logging
from app.mcp_server.server import mcp


@pytest.fixture
def restore_logging() -> Iterator[None]:
    """setup_logging replaces the root handlers; put pytest's back afterwards."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    yield
    for handler in root.handlers:
        handler.close()
    root.handlers, root.level = saved_handlers, saved_level


def call_tool(name: str, arguments: dict) -> None:
    async def run() -> None:
        async with Client(mcp) as client:
            await client.call_tool(name, arguments)

    anyio.run(run)


def test_setup_logging_writes_to_text_file(tmp_path: Path, restore_logging: None) -> None:
    log_file = setup_logging("unit_test", log_dir=tmp_path)
    logging.getLogger("app.example").info("hello log file")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_file == tmp_path / "unit_test.log"
    line = log_file.read_text(encoding="utf-8").strip()
    assert "INFO" in line and "app.example: hello log file" in line


def test_successful_tool_call_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.tool_calls"):
        call_tool("search_fragrances", {"query": "#10"})
    [record] = [r for r in caplog.records if r.name == "app.tool_calls"]
    message = record.getMessage()
    assert "tool=search_fragrances" in message
    assert '"query": "#10"' in message
    assert "status=ok" in message and "results=1" in message and "'#10'" in message
    assert "duration_ms=" in message


def test_failed_tool_call_is_logged_as_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.tool_calls"):
        call_tool("get_product_details", {"product_id": "nope"})
    [record] = [r for r in caplog.records if r.name == "app.tool_calls"]
    assert record.levelno == logging.WARNING
    assert "status=error" in record.getMessage() and "was not found" in record.getMessage()
