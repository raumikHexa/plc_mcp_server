import pytest

from app.services.common import InvalidQueryError
from app.services.faq_service import get_all_faqs, search_faqs


def test_get_all_faqs_covers_required_topics() -> None:
    categories = {faq.category for faq in get_all_faqs()}
    assert {"Warranty", "Materials", "Customization", "Shipping", "Installation"} <= categories


@pytest.mark.parametrize(
    ("query", "expected_id"),
    [
        ("What is the warranty?", "FAQ-001"),
        ("which materials do you use", "FAQ-002"),
        ("can I get a bespoke size", "FAQ-003"),
        ("how long does delivery take", "FAQ-004"),
        ("do I need an electrician to install", "FAQ-005"),
        ("is it dimmable", "FAQ-006"),
    ],
)
def test_search_returns_most_relevant_faq_first(query: str, expected_id: str) -> None:
    assert search_faqs(query)[0].id == expected_id


def test_search_no_match_returns_empty_list() -> None:
    assert search_faqs("zebra") == []


def test_search_rejects_empty_query() -> None:
    with pytest.raises(InvalidQueryError):
        search_faqs("  ")
