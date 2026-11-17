"""MCP server exposing Private Label Candles' public knowledge to AI assistants.

Run with:  python -m app.mcp_server.server
Endpoint:  http://127.0.0.1:8001/mcp   (Streamable HTTP transport)

Design rules:
- Every tool only calls a function from app/services. No business logic here.
- Every tool is read-only and takes search words or IDs, never file paths.
- Service errors become ToolError, so the AI sees a helpful message instead of
  a generic "Error executing tool".
"""

import logging
import sys
from collections.abc import Callable
from typing import Annotated, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import ToolAnnotations
from pydantic import Field

from app.config import settings
from app.models import Company, DocumentMatch, Faq, Fragrance, Product
from app.services import company_service, document_service, faq_service, fragrance_service, product_service
from app.services.common import ServiceError

logger = logging.getLogger(__name__)

T = TypeVar("T")

mcp = MCPServer(
    name="private-label-candles",
    title="Private Label Candles Knowledge",
    website_url="https://privatelabelcandles.com",
    instructions=(
        "Public information about Private Label Candles (PLC), a Central Florida manufacturer of "
        "private label and unlabeled candles, reed diffusers, room sprays, body care and fragrance "
        "products for businesses. Use search_products / get_product_details for products, prices and "
        "options; search_fragrances for scents; search_faqs for lead times, ordering, customization "
        "and policies; get_company_info for contact details; search_documents for longer documents. "
        "Prices are in USD and dated (prices_as_of); mention that prices may have changed and share the "
        "product URL. If nothing is found, say so rather than guessing, and suggest contacting PLC."
    ),
)

# Shared by all tools: they only read data, never change anything, and give the
# same answer for the same input. Lets AI clients run them without extra prompts.
READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

Query = Annotated[str, Field(description="Search keywords, e.g. 'matte black reed diffuser'", min_length=1, max_length=200)]


def _call(func: Callable[..., T], *args: object) -> T:
    """Run a service function, turning expected service errors into ToolError for the AI."""
    try:
        return func(*args)
    except ServiceError as exc:
        raise ToolError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(title="Search products", annotations=READ_ONLY)
def search_products(query: Query) -> list[Product]:
    """Search the product catalogue: candles (jar sizes and colours), unlabeled candles by the case,
    reed diffusers, room sprays, body lotion/wash, mini samples and bulk liquids by the gallon.

    Matches product name, product line, size, option values (colours, caps, pumps) and description.
    Returns the best matches first with prices (USD, dated), pack quantity, options and product URL.
    Use get_product_details with a returned `id` for one product's full record.
    """
    return _call(product_service.search_products, query)


@mcp.tool(title="Get product details", annotations=READ_ONLY)
def get_product_details(
    product_id: Annotated[str, Field(description="Product ID from search_products, e.g. '9-oz-jar'", max_length=100)],
) -> Product:
    """Get the full record for one product by its ID (as returned by search_products):
    size, pack quantity, unit and order price, all options, description, status and URL."""
    return _call(product_service.get_product_by_id, product_id)


@mcp.tool(title="Search FAQs", annotations=READ_ONLY)
def search_faqs(query: Query) -> list[Faq]:
    """Search the official FAQ for questions about how PLC works: private label process, lead times,
    rush/expedite service, minimum orders, order changes, the 3D product designer, label design,
    custom scents, own packaging, and the return/refund policy. Returns the most relevant answers first."""
    return _call(faq_service.search_faqs, query)


@mcp.tool(title="Get company information", annotations=READ_ONLY)
def get_company_info() -> Company:
    """Get Private Label Candles' company profile: description, location, founding year, website,
    phone, emails, business hours, product categories, industries served, services and standard lead time."""
    return _call(company_service.get_company_info)


@mcp.tool(title="Search documents", annotations=READ_ONLY)
def search_documents(query: Query) -> list[DocumentMatch]:
    """Search the text of company documents (PDF and TXT, e.g. product catalogue, company profile,
    fragrance guide). Returns matching passages with the document filename and page number.
    Use this for detail that may only appear in documents; prefer the other tools for structured data."""
    return _call(document_service.search_documents, query)


@mcp.tool(title="Search fragrances", annotations=READ_ONLY)
def search_fragrances(query: Query) -> list[Fragrance]:
    """Search the fragrance library (93 scents usable in candles, diffusers, sprays, etc.) by
    fragrance name, scent notes (e.g. 'vanilla', 'sandalwood'), scent family (Floral, Woodsy, Citrus,
    Gourmand, Fresh, Musk, Masculine, Feminine, Unisex, Holiday ...), 'top seller', 'new', or number ('#10')."""
    return _call(fragrance_service.search_fragrances, query)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def transport_security() -> TransportSecuritySettings:
    """Allow localhost plus any public hostnames from MCP_ALLOWED_HOSTS (e.g. a devtunnel).

    The SDK rejects requests whose Host header is not on this list (protection
    against DNS-rebinding attacks), so a tunnel hostname must be added here.
    """
    local_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    local_origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    extra = list(settings.mcp_allowed_hosts)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=local_hosts + extra,
        allowed_origins=local_origins + [f"https://{host}" for host in extra],
    )


def main() -> None:
    # Logs go to stderr so they never mix with protocol output.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")
    logger.info("MCP server on http://%s:%s/mcp", settings.mcp_host, settings.mcp_port)
    if settings.mcp_allowed_hosts:
        logger.info("Extra allowed hosts: %s", ", ".join(settings.mcp_allowed_hosts))
    mcp.run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
        stateless_http=True,  # each request is independent: simpler behind tunnels/load balancers
        transport_security=transport_security(),
    )


if __name__ == "__main__":
    main()
