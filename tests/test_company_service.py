from app.services.company_service import get_company_info


def test_get_company_info_has_required_fields() -> None:
    company = get_company_info()
    assert company.name == "Private Label Candles"
    assert company.description
    assert company.industry
    assert company.website == "https://privatelabelcandles.com"
    assert company.contact.email == "customerservice@privatelabelcandles.com"
    assert company.contact.phone
    assert company.product_categories


def test_lead_time_matches_faq() -> None:
    assert "6-8 weeks" in (get_company_info().standard_lead_time or "")
