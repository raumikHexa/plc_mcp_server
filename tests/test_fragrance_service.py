import pytest

from app.services.common import FragranceNotFoundError, InvalidQueryError
from app.services.fragrance_service import get_all_fragrances, get_fragrance_by_number, search_fragrances


def test_library_has_93_unique_fragrances() -> None:
    numbers = [f.number for f in get_all_fragrances()]
    assert len(numbers) == 93
    assert len(set(numbers)) == 93


def test_get_fragrance_by_number() -> None:
    allure = get_fragrance_by_number(1)
    assert allure.name == "Allure"
    assert allure.notes == ["Balsam Fir", "Pine", "Thyme"]
    assert allure.top_seller


def test_unknown_fragrance_number_raises() -> None:
    with pytest.raises(FragranceNotFoundError):
        get_fragrance_by_number(9999)


def test_inspired_by_is_extracted() -> None:
    assert get_fragrance_by_number(4).inspired_by == "BBW Midnight Blue Citrus"


def test_search_by_note() -> None:
    results = search_fragrances("vanilla")
    assert results and all("vanilla" in (f.name + f.notes_text).lower() for f in results)


def test_search_by_category() -> None:
    assert all("Woodsy" in f.categories for f in search_fragrances("woodsy"))


def test_search_top_sellers() -> None:
    assert all(f.top_seller for f in search_fragrances("top sellers"))


def test_search_by_number() -> None:
    assert search_fragrances("#10")[0].name == "Santal"


def test_search_rejects_empty_query() -> None:
    with pytest.raises(InvalidQueryError):
        search_fragrances("the")
