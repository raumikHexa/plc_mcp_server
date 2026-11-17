"""One place that sets up logging for every entry point (MCP server, REST API, scripts).

Each process writes to:
  - the console (stderr), and
  - a rotating text file: <LOG_DIR>/<name>.log  (e.g. logs/mcp_server.log)

Rotation: when the file reaches LOG_MAX_MB it is renamed to <name>.log.1
(older ones shift to .2, .3 ...) and a fresh file starts. Only LOG_BACKUP_COUNT
old files are kept, so logs can never fill the disk.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(name: str, *, log_dir: Path | None = None) -> Path:
    """Send all log records to the console and to <log_dir>/<name>.log. Returns the file path.

    `force=True` replaces any handlers installed earlier, e.g. by the MCP SDK,
    which configures its own logging when MCPServer is created.
    """
    directory = log_dir or settings.log_dir
    directory.mkdir(parents=True, exist_ok=True)
    log_file = directory / f"{name}.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.log_max_mb * 1024 * 1024,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    console_handler = logging.StreamHandler(sys.stderr)  # never stdout: keeps protocol output clean

    logging.basicConfig(
        level=settings.log_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[console_handler, file_handler],
        force=True,
    )
    # Uvicorn started with log_config=None leaves its loggers without handlers,
    # so their records (startup, HTTP access lines) propagate to ours.
    for uvicorn_logger in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(uvicorn_logger).handlers.clear()
        logging.getLogger(uvicorn_logger).propagate = True

    return log_file
