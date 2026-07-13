import pytest

from internship_tracker.config import load_companies


def test_company_configuration_validation(tmp_path):
    path = tmp_path / "companies.yaml"
    path.write_text("companies:\n  - name: Example\n    enabled: true\n    careers_url: https://example.com/jobs\n    ats_provider: greenhouse\n    ats_account: example\n    search_terms: [marketing]\n    preferred_locations: [Austin]\n", encoding="utf-8")
    companies = load_companies(path)
    assert companies[0].name == "Example" and companies[0].ats_account == "example"


def test_duplicate_company_rejected(tmp_path):
    path = tmp_path / "companies.yaml"
    path.write_text("companies:\n  - {name: Same}\n  - {name: same}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"): load_companies(path)

