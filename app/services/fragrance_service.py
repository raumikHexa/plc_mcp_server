"""Fragrance library: list, look up by number and keyword search."""

from app.config import settings
from app.models import Fragrance
from app.services.common import FragranceNotFoundError, load_json, query_terms, score_fields

FRAGRANCES_FILE = "fragrances.json"

NAME_WEIGHT = 5
NOTES_WEIGHT = 3  # e.g. "vanilla", "sandalwood"
CATEGORY_WEIGHT = 3  # e.g. "woodsy", "floral", "top seller"
OTHER_WEIGHT = 1  # inspired-by and remarks


def get_all_fragrances() -> list[Fragrance]:
    """Return the whole fragrance library, ordered by fragrance number."""
    raw = load_json(settings.data_dir / FRAGRANCES_FILE)
    return [Fragrance.model_validate(item) for item in raw]


def get_fragrance_by_number(number: int) -> Fragrance:
    """Return fragrance #number. Raises FragranceNotFoundError."""
    for fragrance in get_all_fragrances():
        if fragrance.number == number:
            return fragrance
    raise FragranceNotFoundError(number)


def search_fragrances(query: str, limit: int | None = None) -> list[Fragrance]:
    """Search by name, scent notes, scent family or 'top seller' / 'new'; best matches first.

    Raises InvalidQueryError if the query has no searchable words.
    """
    terms = query_terms(query)
    limit = limit or settings.max_results

    scored: list[tuple[int, Fragrance]] = []
    for fragrance in get_all_fragrances():
        labels = list(fragrance.categories)
        if fragrance.top_seller:
            labels.append("top seller bestseller popular")
        if fragrance.is_new:
            labels.append("new")
        score = score_fields(
            terms,
            [
                (fragrance.name, NAME_WEIGHT),
                (fragrance.notes_text, NOTES_WEIGHT),
                (" ".join(labels), CATEGORY_WEIGHT),
                (f"{fragrance.inspired_by or ''} {fragrance.remarks or ''}", OTHER_WEIGHT),
            ],
        )
        # A query like "#10" or "10" should find fragrance number 10 directly.
        if str(fragrance.number) in terms:
            score += NAME_WEIGHT * 2
        if score > 0:
            scored.append((score, fragrance))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [fragrance for _, fragrance in scored[:limit]]
