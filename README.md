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
pytest
```

## Configuration

Settings are read from environment variables (see `app/config.py`):
`DATA_DIR`, `DOCUMENTS_DIR`, `API_HOST`, `API_PORT`, `MCP_HOST`, `MCP_PORT`, `MAX_RESULTS`.
