import pytest

from app.services.common import InvalidQueryError, ProductNotFoundError
from app.services.product_service import get_all_products, get_product_by_id, search_products


def test_catalogue_has_all_imported_products() -> None:
    products = get_all_products()
    assert len(products) == 40
    assert len({p.id for p in products}) == 40  # IDs are unique


def test_every_product_has_price_date_and_link() -> None:
    for product in get_all_products():
        assert product.price_min <= product.price_max
        assert product.prices_as_of
        assert product.url.startswith("https://privatelabelcandles.com/products/")


def test_get_product_by_id_is_case_insensitive() -> None:
    product = get_product_by_id("  9-OZ-JAR ")
    assert product.name == "9 oz Candle"
    assert "Glossy White" in product.options["Jar Color"]


def test_get_product_by_unknown_id_raises() -> None:
    with pytest.raises(ProductNotFoundError, match="no-such-product"):
        get_product_by_id("no-such-product")


def test_pack_and_unit_price_parsed_from_title() -> None:
    spray = get_product_by_id("unlabeled-rs-clear-bottle-50-units")
    assert (spray.pack_quantity, spray.pack_unit, spray.unit_price) == (50, "units", 11.5)


def test_site_option_label_error_is_corrected() -> None:
    # On the website this option is mislabelled "Bottom Warning Label".
    spray = get_product_by_id("unlabeled-rs-matte-finish-50-units")
    assert "Bottle Color" in spray.options
    assert "Bottom Warning Label" not in spray.options


def test_coming_soon_products_are_flagged() -> None:
    assert get_product_by_id("45-oz-jar").status == "coming_soon"


@pytest.mark.parametrize(
    ("query", "expected_first"),
    [
        ("9 oz candle", "9-oz-jar"),
        ("perfume gallon", "perfume-by-gallon"),
        ("body lotion", "unlabeled-16-oz-body-lotion-32-pcs"),
    ],
)
def test_search_ranks_best_match_first(query: str, expected_first: str) -> None:
    assert search_products(query)[0].id == expected_first


def test_search_by_product_line() -> None:
    results = search_products("reed diffuser", limit=10)
    assert {p.product_line for p in results[:4]} == {"Reed Diffuser"}


def test_search_by_option_value() -> None:
    results = search_products("tiffany blue")
    assert results and all(
        any("Tiffany Blue" in v for values in p.options.values() for v in values) for p in results
    )


def test_search_no_match_returns_empty_list() -> None:
    assert search_products("chandelier") == []


def test_search_respects_limit() -> None:
    assert len(search_products("candle", limit=2)) == 2


@pytest.mark.parametrize("query", ["", "   ", "what is the"])
def test_search_rejects_queries_without_keywords(query: str) -> None:
    with pytest.raises(InvalidQueryError):
        search_products(query)
