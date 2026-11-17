import os
from pathlib import Path

import pytest

from app.services import document_service
from app.services.common import DataFileError, InvalidQueryError
from app.services.document_service import list_documents, search_documents
from scripts.make_sample_documents import write_pdf


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    """A temporary documents folder with one TXT and one two-page PDF."""
    (tmp_path / "care_guide.txt").write_text(
        "Candle care\nTrim the wick to 1/4 inch before every burn.\n\n"
        "Storage\nKeep candles away from direct sunlight.",
        encoding="utf-8",
    )
    write_pdf(tmp_path / "specs.pdf", "Specs", ["Page one is about reed diffusers."] + [""] * 60
              + ["Page two mentions soy wax and cotton wicks."])
    return tmp_path


def test_lists_only_supported_files(docs: Path) -> None:
    (docs / "notes.docx").write_text("ignored")
    (docs / "sub").mkdir()
    (docs / "sub" / "hidden.txt").write_text("subfolders are never read")
    assert list_documents(directory=docs) == ["care_guide.txt", "specs.pdf"]


def test_txt_search_returns_passage_and_filename(docs: Path) -> None:
    [best, *_] = search_documents("trim wick", directory=docs)
    assert best.filename == "care_guide.txt"
    assert best.page is None
    assert "1/4 inch" in best.snippet
    assert "sunlight" not in best.snippet  # paragraphs are separate passages


def test_pdf_search_reports_correct_page(docs: Path) -> None:
    [best, *_] = search_documents("soy wax", directory=docs)
    assert (best.filename, best.page) == ("specs.pdf", 2)


def test_subfolder_files_are_never_searched(docs: Path) -> None:
    (docs / "sub").mkdir()
    (docs / "sub" / "secret.txt").write_text("zebra")
    assert search_documents("zebra", directory=docs) == []


def test_corrupt_pdf_is_skipped_not_fatal(docs: Path) -> None:
    (docs / "broken.pdf").write_bytes(b"this is not a pdf")
    assert search_documents("sunlight", directory=docs)[0].filename == "care_guide.txt"


def test_cache_picks_up_changed_and_deleted_files(docs: Path) -> None:
    guide = docs / "care_guide.txt"
    assert search_documents("sunlight", directory=docs)

    guide.write_text("Now about lavender only.", encoding="utf-8")
    stat = guide.stat()
    os.utime(guide, (stat.st_atime, stat.st_mtime + 5))
    assert search_documents("sunlight", directory=docs) == []
    assert search_documents("lavender", directory=docs)

    guide.unlink()
    assert search_documents("lavender", directory=docs) == []
    assert guide not in document_service._cache


def test_missing_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(DataFileError):
        search_documents("candle", directory=tmp_path / "nope")


def test_empty_query_rejected(docs: Path) -> None:
    with pytest.raises(InvalidQueryError):
        search_documents("the", directory=docs)


def test_sample_documents_are_searchable() -> None:
    """The generated sample documents in app/documents work end to end."""
    assert set(list_documents()) >= {"product_catalogue.pdf", "company_profile.pdf", "fragrance_guide.txt"}
    [best, *_] = search_documents("rush expedite")
    assert best.filename == "company_profile.pdf"
    assert "3-4 weeks" in best.snippet
