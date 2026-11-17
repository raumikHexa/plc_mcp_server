"""Tests for the cleaning rules in scripts/import_catalogue.py (no network needed)."""

import pytest

from scripts.import_catalogue import clean_product_name, html_to_text, parse_fragrance_title


@pytest.mark.parametrize(
    ("title", "collection", "expected"),
    [
        ("9 OZ. CANDLE", "jars", "9 oz Candle"),
        ("Unlabeled | Rs | Clear Bottle | (50 Units - $11.50 Each)", "unlabeled-room-sprays",
         "Unlabeled Room Spray – Clear Bottle"),
        ("Unlabeled | Reed Diff. | Premium | (36 Pcs @ $14.75 Each)", "unlabeled-reed-diffuser",
         "Unlabeled Reed Diffuser – Premium"),
        ("1 Case (27 Units) - $15.25 Per Unit", "unbranded-candles", "Unlabeled 9 oz Candles – 1 Case (27 Units)"),
        ("Hand soap by gallon (2 gallons at @ $61 each)", "professional-use-by-gallon", "Hand Soap by the Gallon"),
    ],
)
def test_clean_product_name(title: str, collection: str, expected: str) -> None:
    assert clean_product_name(title, collection) == expected


def test_parse_fragrance_title_full() -> None:
    parsed = parse_fragrance_title("#4 Belize - Exotic Tropical Fruit & Juicy Citrus (Inspired by BBW Midnight Blue Citrus)")
    assert parsed["number"] == 4
    assert parsed["name"] == "Belize"
    assert parsed["notes"] == ["Exotic Tropical Fruit", "Juicy Citrus"]
    assert parsed["inspired_by"] == "BBW Midnight Blue Citrus"


def test_parse_fragrance_title_new_marker_and_no_space_dash() -> None:
    assert parse_fragrance_title("#82 Golden - Amber, Musk & Vanilla  *NEW*")["is_new"] is True
    assert parse_fragrance_title("#20 Havana- Cuban Vanilla")["name"] == "Havana"


def test_parse_fragrance_title_without_notes() -> None:
    parsed = parse_fragrance_title("#3 Baby Powder")
    assert (parsed["name"], parsed["notes"]) == ("Baby Powder", [])


def test_html_to_text_decodes_double_escaped_entities() -> None:
    assert html_to_text("<p>Labels&amp;nbsp;sold separately.</p>") == "Labels sold separately."
