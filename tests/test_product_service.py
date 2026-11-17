import pytest

from app.services.common import InvalidQueryError, ProductNotFoundError
from app.services.product_service import get_all_products, get_product_by_id, search_products


def test_get_all_products_returns_three_pendants() -> None:
    names = [p.name for p in get_all_products()]
    assert names == ["Peak Pendant", "Balance Pendant", "Veer Pendant"]


def test_get_product_by_id_is_case_insensitive() -> None:
    assert get_product_by_id("pnd-002").name == "Balance Pendant"
    assert get_product_by_id("  PND-003 ").name == "Veer Pendant"


def test_get_product_by_unknown_id_raises() -> None:
    with pytest.raises(ProductNotFoundError, match="PND-999"):
        get_product_by_id("PND-999")


def test_search_by_name() -> None:
    assert search_products("veer")[0].id == "PND-003"


def test_search_by_material_ranks_best_match_first() -> None:
    results = search_products("oak")
    assert [p.id for p in results] == ["PND-002"]


def test_search_by_category_matches_all_pendants_and_plurals() -> None:
    assert len(search_products("pendant lights")) == 3


def test_search_by_description() -> None:
    assert search_products("kitchen island")[0].id == "PND-001"


def test_search_no_match_returns_empty_list() -> None:
    assert search_products("chandelier") == []


def test_search_respects_limit() -> None:
    assert len(search_products("pendant", limit=2)) == 2


@pytest.mark.parametrize("query", ["", "   ", "what is the"])
def test_search_rejects_queries_without_keywords(query: str) -> None:
    with pytest.raises(InvalidQueryError):
        search_products(query)
