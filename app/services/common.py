"""Helpers shared by all services: errors, cached JSON loading and keyword scoring.

Kept in one place so product, FAQ (and later document) search behave the same
way and no logic is copy-pasted between services.
"""

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ServiceError(Exception):
    """Base class for all errors raised by the service layer."""


class DataFileError(ServiceError):
    """A data file is missing or contains invalid JSON."""


class NotFoundError(ServiceError):
    """A requested item does not exist."""


class ProductNotFoundError(NotFoundError):
    def __init__(self, product_id: str) -> None:
        super().__init__(f"Product '{product_id}' was not found.")
        self.product_id = product_id


class InvalidQueryError(ServiceError):
    """A search query is empty or contains no searchable words."""


# ---------------------------------------------------------------------------
# Cached JSON loading
# ---------------------------------------------------------------------------

# path -> (last-modified time, parsed JSON)
_json_cache: dict[Path, tuple[float, Any]] = {}


def load_json(path: Path) -> Any:
    """Read a JSON file, reusing the in-memory copy unless the file has changed.

    The file's modification time (mtime) is checked on every call; that is a
    very cheap operation compared with re-reading and parsing the file.
    """
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        raise DataFileError(f"Data file not found: {path.name}") from None

    cached = _json_cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataFileError(f"Invalid JSON in {path.name}: {exc}") from None

    _json_cache[path] = (mtime, data)
    return data


# ---------------------------------------------------------------------------
# Keyword search helpers
# ---------------------------------------------------------------------------

# Common words that carry no meaning for search ("what is the warranty" -> "warranty")
STOP_WORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it me my of on or "
    "our the this to what when where which who why will with you your".split()
)


def _normalize(word: str) -> str:
    """Very light stemming so 'pendants' matches 'pendant' and 'lights' matches 'light'."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokenize(text: str) -> set[str]:
    """Split text into a set of lower-case, normalized words without stop words."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_normalize(w) for w in words if w not in STOP_WORDS}


def query_terms(query: str) -> set[str]:
    """Tokenize a user query, rejecting queries with nothing searchable."""
    terms = tokenize(query)
    if not terms:
        raise InvalidQueryError("Please provide at least one meaningful search keyword.")
    return terms


def score_fields(terms: set[str], weighted_fields: list[tuple[str, int]]) -> int:
    """Score an item: for each field, add its weight once per query term it contains.

    Example: query "brass pendant" against Peak Pendant
      name "Peak Pendant" (weight 5) contains "pendant"        -> +5
      materials "Brushed Brass Opal Glass" (weight 3) has "brass" -> +3
    """
    score = 0
    for text, weight in weighted_fields:
        score += weight * len(terms & tokenize(text))
    return score
