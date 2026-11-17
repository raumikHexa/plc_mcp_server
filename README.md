# AI Knowledge Server

A local prototype that exposes a fictional decorative lighting company's public
information (products, FAQs, company info, documents) through:

- a **FastAPI REST API** (port 8000), and
- an **MCP server** over Streamable HTTP (port 8001), usable as a custom connector
  in Claude / ChatGPT once exposed via an HTTPS tunnel.

Both share the same service layer in `app/services/`.

## Setup (Windows, Python 3.11)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

## Run the REST API

```powershell
python -m app.main
```

Then open http://127.0.0.1:8000/health or the Swagger UI at http://127.0.0.1:8000/docs.

## Run tests

```powershell
python -m pytest -q
```

Always run venv tools through `python -m ...` (e.g. `python -m pytest`, `python -m uvicorn`).
On machines with Windows Application Control / Smart App Control, the unsigned
`.exe` launchers in `.venv\Scripts\` (like `pytest.exe`) can be blocked, while
`python.exe` is allowed.

## Data: importing the catalogue

Product, FAQ and fragrance data come from the public website of Private Label
Candles (privatelabelcandles.com), in two steps:

```powershell
python -m scripts.import_catalogue download   # fetch raw files into app/data/raw (slow, rate-limit friendly)
python -m scripts.import_catalogue build      # raw files -> app/data/products.json, faqs.json, fragrances.json
```

- `app/data/raw/` holds unedited snapshots (proof of source; `_meta.json` records the download date).
- `build` is offline and repeatable; cleaning rules live in `scripts/import_catalogue.py`.
- `app/data/company.json` is maintained by hand from the same pages.
- Prices carry a `prices_as_of` date; the FAQ is treated as the source of truth where pages disagree.

## Documents

Any `.txt` or `.pdf` file placed directly in `app/documents/` is searchable
(subfolders and other file types are ignored). Text is extracted once and cached
until the file changes.

The current files are **generated samples** built from the website data:

```powershell
python -m scripts.make_sample_documents   # product_catalogue.pdf, company_profile.pdf, fragrance_guide.txt
```

Replace them with official client documents when available.

## Configuration

Settings are loaded from a `.env` file in the project root (see `app/config.py`).
Create it from the template:

```powershell
Copy-Item .env.example .env
```

Available keys: `APP_NAME`, `DATA_DIR`, `DOCUMENTS_DIR`, `API_HOST`, `API_PORT`,
`MCP_HOST`, `MCP_PORT`, `MAX_RESULTS`. Values are read with python-dotenv;
missing keys fall back to defaults. `.env` is git-ignored.
