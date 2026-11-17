"""Keyword search over TXT and PDF documents in the documents folder.

How it works:
1. Every .txt / .pdf file directly inside the documents folder is read once:
   TXT as plain text, PDF page by page with pypdf.
2. Each page is split into small passages ("chunks") of roughly CHUNK_CHARS.
3. The chunks are kept in an in-memory cache keyed by file, and only rebuilt
   when that file's modification time or size changes.
4. A search scores every chunk by how many query words it contains and returns
   the best passages with their filename and page number.

Security: only files *directly* inside the configured folder with an allowed
extension are ever read. Callers pass search words, never paths.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.config import settings
from app.models import DocumentMatch
from app.services.common import DataFileError, query_terms, tokenize

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".pdf"}
CHUNK_CHARS = 500  # target passage size; small enough to be a precise answer
FILENAME_BONUS = 2  # extra points per query word found in the file name


@dataclass(frozen=True)
class Chunk:
    filename: str
    page: int | None
    text: str
    words: tuple[str, ...]  # normalized words, used for scoring


# path -> ((mtime, size), chunks)
_cache: dict[Path, tuple[tuple[float, int], list[Chunk]]] = {}


# ---------------------------------------------------------------------------
# Reading files
# ---------------------------------------------------------------------------


def _read_pages(path: Path) -> list[tuple[int | None, str]]:
    """Return [(page_number, text)]. TXT files are one page with number None."""
    if path.suffix.lower() == ".txt":
        return [(None, path.read_text(encoding="utf-8", errors="replace"))]
    reader = PdfReader(path)
    return [(number, page.extract_text() or "") for number, page in enumerate(reader.pages, start=1)]


def _split_into_chunks(text: str) -> list[str]:
    """Split text into passages: by blank lines, then long blocks into ~CHUNK_CHARS windows.

    Windows overlap by one line so a sentence on a window boundary is not lost.
    PDF text usually has no blank lines, so a whole PDF page arrives as one block.
    """
    chunks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        window: list[str] = []
        for line in lines:
            if window and sum(len(w) for w in window) + len(line) > CHUNK_CHARS:
                chunks.append("\n".join(window))
                window = window[-1:]  # one-line overlap
            window.append(line)
        if window and (not chunks or "\n".join(window) not in chunks[-1]):
            chunks.append("\n".join(window))
    return chunks


def _words(text: str) -> tuple[str, ...]:
    """Normalized words in order (with repeats), for frequency scoring."""
    return tuple(w for raw in re.findall(r"[a-z0-9]+", text.lower()) for w in tokenize(raw))


def _load_file(path: Path) -> list[Chunk]:
    stat = path.stat()
    signature = (stat.st_mtime, stat.st_size)
    cached = _cache.get(path)
    if cached and cached[0] == signature:
        return cached[1]

    logger.info("Indexing document %s", path.name)
    chunks = [
        Chunk(path.name, page, chunk_text, _words(chunk_text))
        for page, page_text in _read_pages(path)
        for chunk_text in _split_into_chunks(page_text)
    ]
    _cache[path] = (signature, chunks)
    return chunks


def _document_paths(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise DataFileError(f"Documents folder not found: {directory.name}")
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS)


def _all_chunks(directory: Path) -> list[Chunk]:
    paths = _document_paths(directory)
    # Forget files that were deleted since the last search.
    for stale in set(_cache) - set(paths):
        if stale.parent == directory:
            del _cache[stale]

    chunks: list[Chunk] = []
    for path in paths:
        try:
            chunks.extend(_load_file(path))
        except Exception as exc:  # a corrupt/encrypted file must not break search for the others
            logger.warning("Skipping unreadable document %s: %s", path.name, exc)
    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_documents(*, directory: Path | None = None) -> list[str]:
    """Return the names of the searchable documents."""
    return [p.name for p in _document_paths(directory or settings.documents_dir)]


def search_documents(query: str, limit: int | None = None, *, directory: Path | None = None) -> list[DocumentMatch]:
    """Return the passages that best match the query, with filename and page.

    Scoring: 10 points per distinct query word found in the passage, plus 1 per
    extra occurrence (so passages focused on the topic rank higher), plus a small
    bonus if the word is in the file name.
    `directory` exists for tests; normal callers always use the configured folder.
    Raises InvalidQueryError if the query has no searchable words.
    """
    terms = query_terms(query)
    limit = limit or settings.max_results

    matches: list[DocumentMatch] = []
    for chunk in _all_chunks(directory or settings.documents_dir):
        found = [w for w in chunk.words if w in terms]
        if not found:
            continue
        distinct = set(found)
        score = 10 * len(distinct) + (len(found) - len(distinct))
        score += FILENAME_BONUS * len(terms & tokenize(Path(chunk.filename).stem.replace("_", " ")))
        matches.append(DocumentMatch(filename=chunk.filename, page=chunk.page, snippet=chunk.text, score=score))

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:limit]
