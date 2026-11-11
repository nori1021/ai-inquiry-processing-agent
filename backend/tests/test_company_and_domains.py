from __future__ import annotations

from app.config import get_settings
from app.schemas.lookup import LookupStatus
from app.services.excel_loader import clear_excel_cache
from app.tools.company_lookup import (
    find_similar_domains,
    get_company_by_domain,
    get_ldap_company,
)


def test_get_ldap_company_found():
    result = get_ldap_company("COMP001")
    assert result.status == LookupStatus.FOUND
    assert result.company is not None
    assert result.company.email_domain.lower() == "acme.com"


def test_get_ldap_company_not_registered():
    result = get_ldap_company("COMP999")
    assert result.status == LookupStatus.NOT_REGISTERED


def test_get_company_by_domain_exact_case_insensitive():
    result = get_company_by_domain("  @Acme.COM ")
    assert result.status == LookupStatus.FOUND
    assert result.company is not None
    assert result.company.company_id == "COMP001"


def test_get_company_by_domain_not_registered():
    result = get_company_by_domain("missing-domain.example")
    assert result.status == LookupStatus.NOT_REGISTERED


def test_find_similar_domains_candidates_only():
    # acme.com should surface acme.co as a candidate, not as verified same company
    result = find_similar_domains("acme.com", threshold=70)
    assert result.status == LookupStatus.FOUND
    assert result.candidates
    assert all(c.note == "candidate_only_never_auto_accepted" for c in result.candidates)
    domains = {c.domain for c in result.candidates}
    assert "acme.com" not in domains  # exact match excluded
    assert "acme.co" in domains


def test_find_similar_domains_respects_threshold():
    high = find_similar_domains("acme.com", threshold=99.9)
    # Very high threshold may yield no near-misses
    low = find_similar_domains("acme.com", threshold=50)
    assert low.status == LookupStatus.FOUND
    assert len(low.candidates) >= len(high.candidates)


def test_similar_domains_never_auto_same_company():
    result = find_similar_domains("acme.co", threshold=70)
    # Even with a strong candidate (acme.com), response is candidates-only
    for c in result.candidates:
        assert "never_auto" in c.note or c.note.startswith("candidate")


def test_missing_companies_excel_unknown(tmp_path, monkeypatch):
    missing = tmp_path / "no_companies.xlsx"
    monkeypatch.setenv("LDAP_COMPANIES_PATH", str(missing))
    get_settings.cache_clear()
    clear_excel_cache()

    result = get_company_by_domain("acme.com")
    assert result.status == LookupStatus.UNKNOWN
    similar = find_similar_domains("acme.com")
    assert similar.status == LookupStatus.UNKNOWN

    get_settings.cache_clear()
