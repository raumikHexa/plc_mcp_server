"""Company information."""

from app.config import settings
from app.models import Company
from app.services.common import load_json

COMPANY_FILE = "company.json"


def get_company_info() -> Company:
    """Return the company profile from company.json."""
    return Company.model_validate(load_json(settings.data_dir / COMPANY_FILE))
