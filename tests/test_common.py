import os
from pathlib import Path

import pytest

from app.services.common import DataFileError, load_json, tokenize


def test_missing_file_raises_data_file_error(tmp_path: Path) -> None:
    with pytest.raises(DataFileError, match="not found"):
        load_json(tmp_path / "missing.json")


def test_invalid_json_raises_data_file_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(DataFileError, match="Invalid JSON"):
        load_json(bad)


def test_cache_reloads_when_file_changes(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text('{"v": 1}', encoding="utf-8")
    assert load_json(path) == {"v": 1}

    path.write_text('{"v": 2}', encoding="utf-8")
    # Force a different modification time so the change is always detected.
    stat = path.stat()
    os.utime(path, (stat.st_atime, stat.st_mtime + 5))
    assert load_json(path) == {"v": 2}


def test_tokenize_drops_stop_words_and_plurals() -> None:
    assert tokenize("What are the Pendant Lights?") == {"pendant", "light"}
