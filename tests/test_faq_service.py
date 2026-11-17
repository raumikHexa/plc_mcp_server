import pytest

from app.services.common import InvalidQueryError
from app.services.faq_service import get_all_faqs, search_faqs


def test_all_site_sections_imported() -> None:
    categories = {faq.category for faq in get_all_faqs()}
    assert categories == {
        "General",
        "Lead Times",
        "Ordering",
        "3D Product Designer",
        "Customization & Design",
        "Return Policy",
    }


def test_duplicate_questions_removed() -> None:
    questions = [faq.question.lower() for faq in get_all_faqs()]
    assert len(questions) == len(set(questions))


def test_faq_is_source_of_truth_for_lead_time() -> None:
    answer = search_faqs("lead time full orders")[0].answer
    assert "6-8 weeks" in answer


@pytest.mark.parametrize(
    ("query", "expected_question_start"),
    [
        ("Do you offer rush service?", "Do you offer rush services"),
        ("what is private label", "What is private label manufacturing"),
        ("can I create a custom scent", "Can I create a custom scent"),
        ("logo upload problem", "It isn't letting me upload my logo"),
        ("refunds", "No returns or refunds"),
    ],
)
def test_search_returns_most_relevant_faq_first(query: str, expected_question_start: str) -> None:
    assert search_faqs(query)[0].question.startswith(expected_question_start)


def test_search_no_match_returns_empty_list() -> None:
    assert search_faqs("zebra") == []


def test_search_rejects_empty_query() -> None:
    with pytest.raises(InvalidQueryError):
        search_faqs("  ")
