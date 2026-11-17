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

## Run the MCP server

```powershell
python -m app.mcp_server.server
```

Endpoint: `http://127.0.0.1:8001/mcp` (Streamable HTTP, stateless). Tools, all read-only:

| Tool | Purpose |
|---|---|
| `search_products(query)` | Products by name, line, size, options, description |
| `get_product_details(product_id)` | Full record for one product |
| `search_faqs(query)` | FAQ answers (lead times, ordering, customization, returns) |
| `get_company_info()` | Company profile and contact details |
| `search_documents(query)` | Passages from TXT/PDF files, with filename and page |
| `search_fragrances(query)` | Fragrance library by name, notes, family, top seller, number |

To expose it through a tunnel, add the tunnel's hostname to `MCP_ALLOWED_HOSTS`
in `.env`; requests with any other `Host` header are rejected (HTTP 421).

## Logs

Each server writes to the console and to a rotating text file in `logs/`
(`mcp_server.log`, `api.log`), configured by `LOG_*` keys in `.env`.
Every MCP tool call is one line under the `app.tool_calls` logger:

```
2026-11-17 17:44:36 INFO    app.tool_calls: tool=search_products args={"query": "matte black reed diffuser"} status=ok results=5 top=[...] duration_ms=1.5
2026-11-17 17:44:36 WARNING app.tool_calls: tool=get_product_details args={"product_id": "nope"} status=error error="Product 'nope' was not found." duration_ms=0.3
```

Show only tool calls: `Select-String "app.tool_calls" logs\mcp_server.log`

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
