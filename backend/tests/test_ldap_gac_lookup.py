from __future__ import annotations

from app.config import get_settings
from app.schemas.lookup import LookupStatus
from app.services.excel_loader import clear_excel_cache
from app.tools.gac_lookup import get_gac_user, get_gac_users_by_domain
from app.tools.ldap_lookup import get_ldap_user


def test_ldap_user_found():
    result = get_ldap_user("alice@acme.com")
    assert result.status == LookupStatus.FOUND
    assert result.user is not None
    assert result.user.user_id == "U1001"
    assert result.user.company_id == "COMP001"


def test_ldap_user_case_insensitive_email_match():
    result = get_ldap_user("  Alice@Acme.COM ")
    assert result.status == LookupStatus.FOUND
    assert result.user is not None
    assert result.user.email.lower() == "alice@acme.com"


def test_ldap_user_not_registered():
    result = get_ldap_user("nobody@acme.com")
    assert result.status == LookupStatus.NOT_REGISTERED
    assert result.user is None


def test_ldap_user_no_fuzzy_match():
    # Near-miss email must NOT match alice@acme.com
    result = get_ldap_user("alicee@acme.com")
    assert result.status == LookupStatus.NOT_REGISTERED
    result2 = get_ldap_user("alice@acme.co")
    assert result2.status == LookupStatus.NOT_REGISTERED


def test_gac_user_found_and_case_insensitive():
    result = get_gac_user("FRANK@ACME.COM")
    assert result.status == LookupStatus.FOUND
    assert result.user is not None
    assert result.user.user_id == "G2002"


def test_gac_user_not_registered():
    result = get_gac_user("missing@globex.com")
    assert result.status == LookupStatus.NOT_REGISTERED


def test_gac_users_by_domain():
    result = get_gac_users_by_domain("acme.com")
    assert result.status == LookupStatus.FOUND
    emails = {u.email.lower() for u in result.users}
    assert "alice@acme.com" in emails
    assert "frank@acme.com" in emails


def test_gac_users_by_domain_not_registered():
    result = get_gac_users_by_domain("no-such-domain.test")
    assert result.status == LookupStatus.NOT_REGISTERED
    assert result.users == []


def test_missing_excel_returns_unknown_not_not_registered(tmp_path, monkeypatch):
    missing = tmp_path / "missing_ldap.xlsx"
    monkeypatch.setenv("LDAP_USERS_PATH", str(missing))
    get_settings.cache_clear()
    clear_excel_cache()

    result = get_ldap_user("alice@acme.com")
    assert result.status == LookupStatus.UNKNOWN
    assert result.status != LookupStatus.NOT_REGISTERED

    get_settings.cache_clear()


def test_unreadable_excel_returns_unknown(tmp_path, monkeypatch):
    bad = tmp_path / "corrupt.xlsx"
    bad.write_text("this is not an excel file", encoding="utf-8")
    monkeypatch.setenv("LDAP_USERS_PATH", str(bad))
    get_settings.cache_clear()
    clear_excel_cache()

    result = get_ldap_user("alice@acme.com")
    assert result.status == LookupStatus.UNKNOWN

    get_settings.cache_clear()
