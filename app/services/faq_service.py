"""Frequently asked questions: list and keyword search."""

from app.config import settings
from app.models import Faq
from app.services.common import load_json, query_terms, score_fields

FAQS_FILE = "faqs.json"

QUESTION_WEIGHT = 3
TAGS_WEIGHT = 3
CATEGORY_WEIGHT = 2
ANSWER_WEIGHT = 1


def get_all_faqs() -> list[Faq]:
    """Return every FAQ."""
    raw = load_json(settings.data_dir / FAQS_FILE)
    return [Faq.model_validate(item) for item in raw]


def search_faqs(query: str, limit: int | None = None) -> list[Faq]:
    """Return the FAQs most relevant to the query, best match first.

    Raises InvalidQueryError if the query has no searchable words.
    """
    terms = query_terms(query)
    limit = limit or settings.max_results

    scored: list[tuple[int, Faq]] = []
    for faq in get_all_faqs():
        score = score_fields(
            terms,
            [
                (faq.question, QUESTION_WEIGHT),
                (" ".join(faq.tags), TAGS_WEIGHT),
                (faq.category, CATEGORY_WEIGHT),
                (faq.answer, ANSWER_WEIGHT),
            ],
        )
        if score > 0:
            scored.append((score, faq))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [faq for _, faq in scored[:limit]]
