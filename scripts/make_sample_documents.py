"""Generate sample TXT/PDF documents from the imported website data.

  python -m scripts.make_sample_documents

These exist only so document search can be tested before the client supplies
real documents. Content is taken from app/data/*.json (real website data), so
nothing is invented. Replace the files in app/documents/ with official
documents whenever they are available.

PDFs are written with a tiny built-in writer (plain Helvetica text pages) so
no extra dependency is needed.
"""

import json
import textwrap
from collections import defaultdict
from pathlib import Path

from app.config import settings

GENERATED_NOTICE = (
    "NOTE: Generated on {date} from public data on privatelabelcandles.com for prototype "
    "testing only. Replace with the official client document."
)
WRAP_WIDTH = 92
LINES_PER_PAGE = 52

# Characters Helvetica's standard encoding cannot show -> plain equivalents.
ASCII_REPLACEMENTS = {"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "...", "•": "-"}


# ---------------------------------------------------------------------------
# Minimal PDF writer
# ---------------------------------------------------------------------------


def _pdf_escape(text: str) -> str:
    for src, dst in ASCII_REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = text.encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path: Path, title: str, lines: list[str]) -> int:
    """Write a simple text-only PDF. Returns the number of pages."""
    pages = [lines[i : i + LINES_PER_PAGE] for i in range(0, len(lines), LINES_PER_PAGE)] or [[]]

    def content_stream(page_lines: list[str], page_no: int) -> bytes:
        ops = ["BT", "/F2 14 Tf", "50 800 Td", f"({_pdf_escape(title)}) Tj", "/F1 10 Tf", "14 TL", "T*", "T*"]
        for line in page_lines:
            ops.append(f"({_pdf_escape(line)}) Tj T*" if line else "T*")
        ops += ["ET", "BT", "/F1 8 Tf", "50 30 Td", f"(Page {page_no} of {len(pages)}) Tj", "ET"]
        return "\n".join(ops).encode("latin-1")

    # Object numbers: 1 catalog, 2 page tree, 3-4 fonts, then (page, content) pairs.
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # page tree, filled in below once page numbers are known
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    page_refs = []
    for number, page_lines in enumerate(pages, start=1):
        stream = content_stream(page_lines, number)
        page_obj = len(objects) + 1
        page_refs.append(f"{page_obj} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {page_obj + 1} 0 R >>".encode()
        )
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(pages)} >>".encode()

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))
    return len(pages)


# ---------------------------------------------------------------------------
# Document content (built from app/data/*.json)
# ---------------------------------------------------------------------------


def _load(name: str) -> object:
    return json.loads((settings.data_dir / name).read_text(encoding="utf-8"))


def _para(text: str) -> list[str]:
    """Wrap a paragraph and follow it with a blank line (paragraph separator)."""
    lines: list[str] = []
    for source_line in text.splitlines() or [""]:
        lines += textwrap.wrap(source_line, WRAP_WIDTH) or [""]
    return lines + [""]


def product_catalogue_lines(as_of: str) -> list[str]:
    products = _load("products.json")
    by_line: dict[str, list[dict]] = defaultdict(list)
    for product in products:
        by_line[product["product_line"]].append(product)

    lines = _para(GENERATED_NOTICE.format(date=as_of))
    lines += _para(f"Prices in USD as of {as_of}. Prices and availability may change; see the website.")
    for product_line, items in by_line.items():
        lines += [f"== {product_line.upper()} ==", ""]
        for p in items:
            details = [f"Product: {p['name']} (ID: {p['id']})"]
            if p["size"]:
                details.append(f"Size: {p['size']}")
            pack = f"{p['pack_quantity']} {p['pack_unit']}"
            unit = f", ${p['unit_price']:.2f} each" if p["unit_price"] is not None else ""
            details.append(f"Order quantity: {pack}{unit}; order price ${p['price_min']:.2f}"
                           + (f" - ${p['price_max']:.2f}" if p["price_max"] != p["price_min"] else ""))
            if p["status"] != "available":
                details.append(f"Status: {p['status'].replace('_', ' ')}")
            for option, values in p["options"].items():
                details.append(f"{option}: {', '.join(values)}")
            if p["description"]:
                details.append(p["description"].replace("\n", " "))
            lines += _para("\n".join(details))
    return lines


def company_profile_lines(as_of: str) -> list[str]:
    company = _load("company.json")
    faqs = _load("faqs.json")
    contact = company["contact"]

    lines = _para(GENERATED_NOTICE.format(date=as_of))
    lines += ["== ABOUT ==", ""] + _para(company["description"])
    lines += _para(f"Founded: {company['founded']}. Headquarters: {company['headquarters']}. "
                   f"Industry: {company['industry']}.")
    lines += ["== CONTACT ==", ""]
    lines += _para(f"Phone: {contact['phone']}\nEmail: {contact['email']}\n"
                   f"Design questions: {contact['other_emails'].get('design', '-')}\n"
                   f"Business hours: {contact['business_hours']}\nWebsite: {company['website']}")
    lines += ["== INDUSTRIES SERVED ==", ""] + _para(", ".join(company["industries_served"]))
    lines += ["== SERVICES ==", ""] + _para("\n".join(f"- {s}" for s in company["services"]))
    lines += ["== LEAD TIMES AND POLICIES ==", ""]
    for faq in faqs:
        if faq["category"] in {"Lead Times", "Return Policy"}:
            lines += _para(f"{faq['question']}\n{faq['answer']}")
    return lines


def fragrance_guide_text(as_of: str) -> str:
    fragrances = _load("fragrances.json")
    families: dict[str, list[dict]] = defaultdict(list)
    for fragrance in fragrances:
        for family in fragrance["categories"]:
            families[family].append(fragrance)

    def describe(f: dict) -> str:
        notes = f": {f['notes_text']}" if f["notes_text"] else ""
        flags = [label for label, on in [("top seller", f["top_seller"]), ("new", f["is_new"])] if on]
        return f"  #{f['number']} {f['name']}{notes}" + (f" [{', '.join(flags)}]" if flags else "")

    parts = [
        "FRAGRANCE FAMILIES GUIDE",
        "",
        GENERATED_NOTICE.format(date=as_of),
        "",
        f"The library has {len(fragrances)} fragrances. Each can be chosen for candles, reed diffusers, "
        "room sprays and other products. A fragrance can belong to several families.",
        "",
    ]
    for family in sorted(families):
        items = families[family]
        parts += [f"{family.upper()} ({len(items)} fragrances)", *[describe(f) for f in items], ""]
    top = [f"#{f['number']} {f['name']}" for f in fragrances if f["top_seller"]]
    parts += ["TOP SELLERS", "  " + ", ".join(top), ""]
    return "\n".join(parts)


def main() -> None:
    as_of = json.loads((settings.data_dir / "raw" / "_meta.json").read_text(encoding="utf-8"))["downloaded_at"]
    out_dir = settings.documents_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = write_pdf(out_dir / "product_catalogue.pdf", "Private Label Candles - Product Catalogue",
                      product_catalogue_lines(as_of))
    print(f"Wrote product_catalogue.pdf ({pages} pages)")
    pages = write_pdf(out_dir / "company_profile.pdf", "Private Label Candles - Company Profile",
                      company_profile_lines(as_of))
    print(f"Wrote company_profile.pdf ({pages} pages)")
    (out_dir / "fragrance_guide.txt").write_text(fragrance_guide_text(as_of), encoding="utf-8")
    print("Wrote fragrance_guide.txt")


if __name__ == "__main__":
    main()
