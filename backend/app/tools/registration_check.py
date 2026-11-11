from __future__ import annotations

from typing import Optional

from app.config import get_settings
from app.schemas.lookup import LookupStatus, UserRecord
from app.schemas.registration import (
    CombinedRegistrationCheckResponse,
    CombinedRegistrationState,
    RegistrationCheckResponse,
    RegistrationFlag,
)
from app.services.excel_loader import ExcelSourceStatus, load_dataframe
from app.services.normalization import normalize_email
from app.tools.gac_lookup import get_gac_user
from app.tools.ldap_lookup import get_ldap_user

USER_COLUMNS_LOCAL = ["UserID", "Email", "CompanyID", "CompanyName", "Status"]


def _require_identity(email: Optional[str], user_id: Optional[str]) -> None:
    if not (email and email.strip()) and not (user_id and user_id.strip()):
        raise ValueError("Provide email and/or user_id")


def _row_to_user(row: dict) -> UserRecord:
    return UserRecord(
        user_id=row["UserID"],
        email=row["Email"],
        company_id=row["CompanyID"],
        company_name=row["CompanyName"],
        status=row["Status"],
    )


def _lookup_by_user_id(source: str, user_id: str) -> RegistrationCheckResponse:
    """Exact UserID match on the same Excel files (no fuzzy matching)."""
    settings = get_settings()
    path = settings.ldap_users_file if source == "ldap" else settings.gac_users_file
    cache_key = "ldap_users" if source == "ldap" else "gac_users"
    loaded = load_dataframe(path, USER_COLUMNS_LOCAL, cache_key=cache_key)
    query_id = user_id.strip()

    if loaded.status == ExcelSourceStatus.UNKNOWN or loaded.frame is None:
        return RegistrationCheckResponse(
            source=source,
            registered=RegistrationFlag.UNKNOWN,
            query_user_id=query_id,
            lookup_status=LookupStatus.UNKNOWN.value,
            detail=loaded.detail or f"{source} source unavailable",
            errors=[loaded.detail or "source unavailable"],
        )

    for _, row in loaded.frame.iterrows():
        if str(row["UserID"]).strip() == query_id:
            user = _row_to_user(row.to_dict())
            return RegistrationCheckResponse(
                source=source,
                registered=RegistrationFlag.YES,
                query_user_id=query_id,
                query_email=normalize_email(user.email),
                user=user,
                company_id=user.company_id,
                company_name=user.company_name,
                account_status=user.status,
                lookup_status=LookupStatus.FOUND.value,
                detail=f"Exact UserID match in {source}",
            )

    return RegistrationCheckResponse(
        source=source,
        registered=RegistrationFlag.NO,
        query_user_id=query_id,
        lookup_status=LookupStatus.NOT_REGISTERED.value,
        detail=f"No {source} user with this UserID",
    )


def _from_email_lookup(source: str, email: str, user_id: Optional[str]) -> RegistrationCheckResponse:
    lookup = get_ldap_user(email) if source == "ldap" else get_gac_user(email)
    errors: list[str] = []

    if lookup.status == LookupStatus.UNKNOWN:
        return RegistrationCheckResponse(
            source=source,
            registered=RegistrationFlag.UNKNOWN,
            query_email=lookup.query,
            query_user_id=user_id.strip() if user_id else None,
            lookup_status=lookup.status.value,
            detail=lookup.detail,
            errors=[lookup.detail or "unknown source error"],
        )

    if lookup.status == LookupStatus.NOT_REGISTERED:
        # Optional: if user_id given, try exact id path (still not fuzzy)
        if user_id and user_id.strip():
            by_id = _lookup_by_user_id(source, user_id)
            if by_id.registered == RegistrationFlag.YES:
                by_id.errors.append(
                    "email not registered; user_id matched a different/alternate key"
                )
                return by_id
        return RegistrationCheckResponse(
            source=source,
            registered=RegistrationFlag.NO,
            query_email=lookup.query,
            query_user_id=user_id.strip() if user_id else None,
            lookup_status=lookup.status.value,
            detail=lookup.detail,
        )

    user = lookup.user
    assert user is not None
    if user_id and user_id.strip() and user.user_id != user_id.strip():
        errors.append(
            f"user_id mismatch: requested={user_id.strip()} found={user.user_id}"
        )

    return RegistrationCheckResponse(
        source=source,
        registered=RegistrationFlag.YES,
        query_email=lookup.query,
        query_user_id=user_id.strip() if user_id else None,
        user=user,
        company_id=user.company_id,
        company_name=user.company_name,
        account_status=user.status,
        lookup_status=lookup.status.value,
        detail=f"Registered in {source}",
        errors=errors,
    )


def check_ldap_registration(
    email: Optional[str] = None, user_id: Optional[str] = None
) -> RegistrationCheckResponse:
    """Demo/test tool: confirm LDAP registration via synthetic Excel (exact match only)."""
    _require_identity(email, user_id)
    if email and email.strip():
        return _from_email_lookup("ldap", email, user_id)
    return _lookup_by_user_id("ldap", user_id or "")


def check_gac_registration(
    email: Optional[str] = None, user_id: Optional[str] = None
) -> RegistrationCheckResponse:
    """Demo/test tool: confirm GAC registration via synthetic Excel (exact match only)."""
    _require_identity(email, user_id)
    if email and email.strip():
        return _from_email_lookup("gac", email, user_id)
    return _lookup_by_user_id("gac", user_id or "")


def check_ldap_gac_registration(
    email: Optional[str] = None, user_id: Optional[str] = None
) -> CombinedRegistrationCheckResponse:
    ldap = check_ldap_registration(email=email, user_id=user_id)
    gac = check_gac_registration(email=email, user_id=user_id)

    if (
        ldap.registered == RegistrationFlag.UNKNOWN
        or gac.registered == RegistrationFlag.UNKNOWN
    ):
        combined = CombinedRegistrationState.UNKNOWN
        detail = "One or both sources UNKNOWN (missing/unreadable Excel) — never treated as NOT_REGISTERED"
    elif (
        ldap.registered == RegistrationFlag.YES
        and gac.registered == RegistrationFlag.YES
    ):
        combined = CombinedRegistrationState.LDAP_AND_GAC
        detail = "Registered in both LDAP and GAC"
    elif ldap.registered == RegistrationFlag.YES:
        combined = CombinedRegistrationState.LDAP_ONLY
        detail = "Registered in LDAP only"
    elif gac.registered == RegistrationFlag.YES:
        combined = CombinedRegistrationState.GAC_ONLY
        detail = "Registered in GAC only"
    else:
        combined = CombinedRegistrationState.NEITHER
        detail = "Not registered in LDAP or GAC"

    return CombinedRegistrationCheckResponse(
        query_email=normalize_email(email) if email else None,
        query_user_id=user_id.strip() if user_id else None,
        combined_state=combined,
        ldap=ldap,
        gac=gac,
        detail=detail,
    )
