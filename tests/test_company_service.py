from app.services.company_service import get_company_info


def test_get_company_info_has_required_fields() -> None:
    company = get_company_info()
    assert company.name
    assert company.description
    assert company.industry
    assert company.website.startswith("https://")
    assert company.contact.email
    assert "Pendant Lights" in company.product_categories
