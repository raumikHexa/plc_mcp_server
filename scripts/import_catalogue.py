"""Import the Private Label Candles catalogue from its public website.

Two separate steps, so the website is only contacted when you choose to:

  python -m scripts.import_catalogue download   # fetch raw source files into app/data/raw (slow, polite)
  python -m scripts.import_catalogue build      # convert raw files -> clean app/data/*.json

`build` never touches the network: it can be re-run any time (e.g. after
changing a cleaning rule) and always produces the same output from the same
raw files. Uses only the Python standard library.
"""

import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from app.config import settings
from app.models import Faq, Fragrance, Product

SITE = "https://privatelabelcandles.com"
RAW_DIR = settings.data_dir / "raw"
SHOPIFY_DIR = RAW_DIR / "shopify"
PAGES_DIR = RAW_DIR / "pages"
META_FILE = RAW_DIR / "_meta.json"

# Shopify collection handle -> human-readable collection name.
COLLECTIONS: dict[str, str] = {
    "jars": "Private Label Candle Jars",
    "unbranded-candles": "Unlabeled Candles",
    "unlabeled-reed-diffuser": "Unlabeled Reed Diffusers",
    "unlabeled-room-sprays": "Unlabeled Room Sprays",
    "unlabeled-body-lotion": "Unlabeled Body Lotion & Body Wash",
    "mini-samples": "Mini Samples",
    "professional-use-by-gallon": "Professional Use by the Gallon",
}
PAGES = ["faq", "fragrance-library"]

USER_AGENT = "Mozilla/5.0 (compatible; catalogue-prototype)"
DELAY_SECONDS = 8  # pause between requests; the site rate-limits fast clients


# ---------------------------------------------------------------------------
# Step 1: download
# ---------------------------------------------------------------------------


def _fetch(url: str, attempts: int = 3) -> bytes:
    """GET a URL, waiting and retrying when the site answers 429 Too Many Requests."""
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == attempts:
                raise
            wait = int(exc.headers.get("Retry-After", "60")) + 5
            print(f"  429 rate limited, waiting {wait}s ...")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def download() -> None:
    SHOPIFY_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

    targets = [(f"{SITE}/collections/{c}/products.json?limit=250", SHOPIFY_DIR / f"{c}.json") for c in COLLECTIONS]
    targets += [(f"{SITE}/pages/{p}", PAGES_DIR / f"{p}.html") for p in PAGES]

    for i, (url, path) in enumerate(targets):
        if i:
            time.sleep(DELAY_SECONDS)
        print(f"GET {url}")
        path.write_bytes(_fetch(url))

    META_FILE.write_text(
        json.dumps(
            {
                "source_site": SITE,
                "downloaded_at": date.today().isoformat(),
                "note": "Raw, unedited snapshots of public pages. Do not edit by hand; "
                "regenerate with `python -m scripts.import_catalogue download`.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Saved {len(targets)} files to {RAW_DIR}")


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def html_to_text(raw_html: str) -> str:
    """Strip tags, decode entities (twice: the site double-escapes some) and tidy whitespace."""
    text = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", raw_html or "")
    text = re.sub(r"<li[^>]*>", "- ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(html.unescape(text)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def smart_title(text: str) -> str:
    """Title-case text only if it is SHOUTED IN CAPS; leave mixed case alone."""
    return text.title() if text.isupper() else text


def normalize_oz(text: str) -> str:
    """'9 OZ.' / '16 Oz.' / '9OZ' -> '9 oz'."""
    return re.sub(r"(\d+(?:\.\d+)?)\s*oz\.?", r"\1 oz", text, flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# Step 2a: products
# ---------------------------------------------------------------------------

PACK_RE = re.compile(r"(\d+)\s*(pcs|units|gallons)", re.IGNORECASE)
UNIT_PRICE_RE = re.compile(r"\$\s*([\d.]+)\s*(?:each|per unit|per gallon)", re.IGNORECASE)
SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:fl\.?\s*)?oz", re.IGNORECASE)
# Pack/price details in brackets, e.g. "(50 Units - $11.50 Each)", "(2 gallons at @ $61 each)"
PACK_BRACKET_RE = re.compile(r"\s*\(\s*\d+\s*(?:pcs|units|gallons)[^)]*\$[^)]*\)", re.IGNORECASE)
PER_UNIT_SUFFIX_RE = re.compile(r"\s*-\s*\$[\d.]+\s*per unit\s*$", re.IGNORECASE)
QTY_SUFFIX_RE = re.compile(r"\s*\(qty:?\s*\d+\)\s*$", re.IGNORECASE)


def clean_product_name(title: str, collection: str) -> str:
    name = PER_UNIT_SUFFIX_RE.sub("", PACK_BRACKET_RE.sub("", title)).strip()
    # Fix SHOUTED titles first ("9 OZ. CANDLE" -> "9 Oz. Candle"), then units ("9 oz Candle").
    name = normalize_oz(smart_title(name))

    if "|" in name:  # e.g. "Unlabeled | Rs | Clear Bottle"
        parts = [p.strip() for p in name.split("|") if p.strip()]
        parts = [{"Rs": "Room Spray", "Reed Diff.": "Reed Diffuser"}.get(p, p) for p in parts]
        name = " ".join(parts[:2]) + (" – " + " ".join(parts[2:]) if len(parts) > 2 else "")
    if collection == "unbranded-candles":  # titles there are just "1 Case (27 Units)" etc.
        name = "Unlabeled 9 oz Candles – " + re.sub(r"\s+", " ", name)
    if collection == "professional-use-by-gallon":
        name = re.sub(r"\s+by\s+gallon", " by the Gallon", name, flags=re.IGNORECASE)
        # "Hand soap by the Gallon" -> "Hand Soap by the Gallon"
        name = " ".join(w if w in ("by", "the") else w[0].upper() + w[1:] for w in name.split())
    return name


def detect_product_line(name: str, collection: str) -> str:
    lowered = name.lower()
    if collection == "mini-samples":
        return "Sample"
    if collection == "professional-use-by-gallon":
        return "Bulk Liquid"
    if "reed stick" in lowered:
        return "Reed Diffuser Accessory"
    for keyword, line in [("reed diffuser", "Reed Diffuser"), ("room spray", "Room Spray"),
                          ("body wash", "Body Wash"), ("body lotion", "Body Lotion")]:
        if keyword in lowered:
            return line
    return "Candle"


def clean_options(product: dict[str, Any], collection: str) -> dict[str, list[str]]:
    options: dict[str, list[str]] = {}
    for position, option in enumerate(product["options"]):
        name = option["name"].strip().rstrip(":").strip()
        values = [smart_title(QTY_SUFFIX_RE.sub("", v).strip()) for v in option["values"]]
        if name == "Title" and values == ["Default Title"]:
            continue  # Shopify placeholder for "no options"
        if collection == "jars" and position == 0:
            name = "Jar Color"  # the site names this option after the product, e.g. "9OZ CANDLE"
        if "warning" in name.lower() and not any(
            re.search(r"warning|standard|custom", v, re.IGNORECASE) for v in values
        ):
            # Site data error: bottle colours listed under a "Bottom Warning Label" option.
            name = "Bottle Color"
        options[name] = values
    return options


def clean_description(body_html: str) -> str:
    text = html_to_text(body_html)
    # Drop navigation-only filler that has no meaning outside the website.
    lines = [line for line in text.splitlines() if not re.match(r"click above", line, re.IGNORECASE)]
    return "\n".join(lines)


def build_product(product: dict[str, Any], collection: str, as_of: str) -> Product:
    title = product["title"]
    description = clean_description(product.get("body_html") or "")
    prices = [float(v["price"]) for v in product["variants"]]

    pack = PACK_RE.search(title)
    pack_quantity, pack_unit = (int(pack.group(1)), pack.group(2).lower()) if pack else (1, "unit")
    unit_match = UNIT_PRICE_RE.search(title)
    unit_price = float(unit_match.group(1)) if unit_match else (min(prices) if pack_quantity == 1 else None)

    size_match = SIZE_RE.search(title) or SIZE_RE.search(description)
    size = f"{size_match.group(1)} oz" if size_match else None

    tags = [t.lower() for t in product.get("tags", [])]
    if "coming soon" in tags:
        status = "coming_soon"
    elif not any(v.get("available", True) for v in product["variants"]):
        status = "unavailable"
    else:
        status = "available"

    name = clean_product_name(title, collection)
    images = product.get("images") or []
    return Product(
        id=product["handle"],
        name=name,
        product_line=detect_product_line(name, collection),
        collection=COLLECTIONS[collection],
        size=size,
        pack_quantity=pack_quantity,
        pack_unit=pack_unit,
        unit_price=unit_price,
        price_min=min(prices),
        price_max=max(prices),
        prices_as_of=as_of,
        options=clean_options(product, collection),
        description=description,
        status=status,
        url=f"{SITE}/products/{product['handle']}",
        image_url=images[0]["src"] if images else None,
    )


def build_products(as_of: str) -> list[Product]:
    products: dict[str, Product] = {}
    for collection in COLLECTIONS:
        raw = json.loads((SHOPIFY_DIR / f"{collection}.json").read_text(encoding="utf-8"))
        for item in raw["products"]:
            products.setdefault(item["handle"], build_product(item, collection, as_of))
    return list(products.values())


# ---------------------------------------------------------------------------
# Step 2b: FAQs
# ---------------------------------------------------------------------------

FAQ_TOKEN_RE = re.compile(
    r'collapsible-section-heading">\s*(?P<section>.*?)\s*</h3>'
    r'|accordion__title[^>]*>\s*(?P<question>.*?)\s*</h3>'
    r'.*?class="accordion__content[^"]*"[^>]*>(?P<answer>.*?)</div>\s*</details>',
    re.DOTALL,
)
SECTION_NAMES = {"Leadtimes": "Lead Times"}


def build_faqs() -> list[Faq]:
    page = (PAGES_DIR / "faq.html").read_text(encoding="utf-8", errors="replace")
    faqs: list[Faq] = []
    seen_questions: set[str] = set()
    section: str | None = None

    for match in FAQ_TOKEN_RE.finditer(page):
        if match.group("section"):
            section = html.unescape(match.group("section")).strip()
            continue
        if section is None:  # accordions before the first FAQ section are not FAQs
            continue
        question = html_to_text(match.group("question"))
        key = question.lower()
        if key in seen_questions:  # the site repeats some questions
            continue
        seen_questions.add(key)
        faqs.append(
            Faq(
                id=f"FAQ-{len(faqs) + 1:03d}",
                category=SECTION_NAMES.get(section, section),
                question=question,
                answer=html_to_text(match.group("answer")),
            )
        )
    return faqs


# ---------------------------------------------------------------------------
# Step 2c: fragrances
# ---------------------------------------------------------------------------

FRAGRANCE_BLOCK_RE = re.compile(r'data-title="([^"]*)"\s+data-fragrances=\'(.*?)\'', re.DOTALL)
FRAGRANCE_TITLE_RE = re.compile(r"#(?P<number>\d+)\s+(?P<rest>.+)")
NEW_MARKER_RE = re.compile(r"\*\s*NEW\s*\*?", re.IGNORECASE)
INSPIRED_RE = re.compile(r"\(\s*inspired by\s+(?P<inspired>[^)]*)\)", re.IGNORECASE)
OTHER_BRACKET_RE = re.compile(r"\((?P<remark>[^)]*)\)")


def parse_fragrance_title(title: str) -> dict[str, Any]:
    """'#4 Belize - Exotic Fruit & Citrus (Inspired by X) *NEW*' -> structured fields."""
    match = FRAGRANCE_TITLE_RE.match(title.strip())
    if not match:
        raise ValueError(f"Unexpected fragrance title: {title!r}")
    rest = match.group("rest")

    is_new = bool(NEW_MARKER_RE.search(rest))
    rest = NEW_MARKER_RE.sub("", rest)
    inspired = INSPIRED_RE.search(rest)
    rest = INSPIRED_RE.sub("", rest)
    remarks = [m.group("remark").strip() for m in OTHER_BRACKET_RE.finditer(rest)]
    rest = OTHER_BRACKET_RE.sub("", rest)

    # "Name - notes" (the site sometimes writes "Name- notes"); some scents have no notes.
    parts = re.split(r"\s*-\s+|\s+-\s*", rest, maxsplit=1)
    name = parts[0]
    notes_text = parts[1].strip() if len(parts) > 1 else ""
    notes = [n.strip() for n in re.split(r",|&|\band\b", notes_text) if n.strip()]
    return {
        "number": int(match.group("number")),
        "name": name.strip(),
        "notes": notes,
        "notes_text": notes_text,
        "is_new": is_new,
        "inspired_by": inspired.group("inspired").strip() if inspired else None,
        "remarks": "; ".join(remarks) or None,
    }


def build_fragrances() -> list[Fragrance]:
    page = (PAGES_DIR / "fragrance-library.html").read_text(encoding="utf-8", errors="replace")
    by_handle: dict[str, dict[str, Any]] = {}
    categories: dict[str, set[str]] = {}

    for category, raw_json in FRAGRANCE_BLOCK_RE.findall(page):
        items = json.loads(re.sub(r",\s*\]$", "]", raw_json.strip()))  # tolerate a trailing comma
        for item in items:
            by_handle.setdefault(item["handle"], item)
            if category != "All Categories":
                categories.setdefault(item["handle"], set()).add(category)

    fragrances = []
    for handle, item in by_handle.items():
        cats = categories.get(handle, set())
        fragrances.append(
            Fragrance(
                **parse_fragrance_title(item["title"]),
                categories=sorted(cats - {"Top Sellers"}),
                top_seller="Top Sellers" in cats,
                url=f"{SITE}/products/{handle}",
            )
        )
    return sorted(fragrances, key=lambda f: f.number)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _write(name: str, items: list[Any]) -> None:
    path = settings.data_dir / name
    data = [item.model_dump(exclude_none=False) for item in items]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(items):3d} records -> {path.relative_to(settings.data_dir.parent.parent)}")


def build() -> None:
    as_of = json.loads(META_FILE.read_text(encoding="utf-8"))["downloaded_at"]
    _write("products.json", build_products(as_of))
    _write("faqs.json", build_faqs())
    _write("fragrances.json", build_fragrances())


if __name__ == "__main__":
    commands = {"download": download, "build": build}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print(__doc__)
        sys.exit(1)
    commands[sys.argv[1]]()
