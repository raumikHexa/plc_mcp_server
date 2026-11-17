"""Product catalogue: list, look up by ID and keyword search."""

from app.config import settings
from app.models import Product
from app.services.common import ProductNotFoundError, load_json, query_terms, score_fields

PRODUCTS_FILE = "products.json"

# How much a match in each field counts. Name matters most, description least.
NAME_WEIGHT = 5
CATEGORY_WEIGHT = 3
MATERIAL_WEIGHT = 3
DESCRIPTION_WEIGHT = 1


def get_all_products() -> list[Product]:
    """Return every product in the catalogue."""
    raw = load_json(settings.data_dir / PRODUCTS_FILE)
    return [Product.model_validate(item) for item in raw]


def get_product_by_id(product_id: str) -> Product:
    """Return one product by ID (case-insensitive). Raises ProductNotFoundError."""
    wanted = product_id.strip().upper()
    for product in get_all_products():
        if product.id.upper() == wanted:
            return product
    raise ProductNotFoundError(product_id)


def search_products(query: str, limit: int | None = None) -> list[Product]:
    """Search by name, category, material or description; best matches first.

    Raises InvalidQueryError if the query has no searchable words.
    """
    terms = query_terms(query)
    limit = limit or settings.max_results

    scored: list[tuple[int, Product]] = []
    for product in get_all_products():
        score = score_fields(
            terms,
            [
                (product.name, NAME_WEIGHT),
                (product.category, CATEGORY_WEIGHT),
                (" ".join(product.materials + product.finishes), MATERIAL_WEIGHT),
                (product.description, DESCRIPTION_WEIGHT),
            ],
        )
        if score > 0:
            scored.append((score, product))

    # Highest score first; Python's sort is stable so ties keep catalogue order.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [product for _, product in scored[:limit]]
