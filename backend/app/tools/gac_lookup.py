from __future__ import annotations

from app.config import get_settings
from app.schemas.lookup import (
    LookupStatus,
    UserLookupResponse,
    UserRecord,
    UsersByDomainResponse,
)
from app.services.excel_loader import ExcelSourceStatus, load_dataframe
from app.services.normalization import email_domain, normalize_domain, normalize_email

USER_COLUMNS = ["UserID", "Email", "CompanyID", "CompanyName", "Status"]


def _row_to_user(row: dict) -> UserRecord:
    return UserRecord(
        user_id=row["UserID"],
        email=row["Email"],
        company_id=row["CompanyID"],
        company_name=row["CompanyName"],
        status=row["Status"],
    )


def get_gac_user(email: str) -> UserLookupResponse:
    """Exact case-insensitive email match against GAC users Excel."""
    query = normalize_email(email)
    settings = get_settings()
    loaded = load_dataframe(
        settings.gac_users_file,
        USER_COLUMNS,
        cache_key="gac_users",
    )

    if loaded.status == ExcelSourceStatus.UNKNOWN or loaded.frame is None:
        return UserLookupResponse(
            status=LookupStatus.UNKNOWN,
            query=query,
            detail=loaded.detail or "GAC users source unavailable",
        )

    for _, row in loaded.frame.iterrows():
        if normalize_email(row["Email"]) == query:
            return UserLookupResponse(
                status=LookupStatus.FOUND,
                query=query,
                user=_row_to_user(row.to_dict()),
            )

    return UserLookupResponse(
        status=LookupStatus.NOT_REGISTERED,
        query=query,
        detail="No GAC user with this email",
    )


def get_gac_users_by_domain(domain: str) -> UsersByDomainResponse:
    """Return all GAC users whose email domain equals the normalized domain."""
    query = normalize_domain(domain)
    settings = get_settings()
    loaded = load_dataframe(
        settings.gac_users_file,
        USER_COLUMNS,
        cache_key="gac_users",
    )

    if loaded.status == ExcelSourceStatus.UNKNOWN or loaded.frame is None:
        return UsersByDomainResponse(
            status=LookupStatus.UNKNOWN,
            query=query,
            detail=loaded.detail or "GAC users source unavailable",
        )

    users = [
        _row_to_user(row.to_dict())
        for _, row in loaded.frame.iterrows()
        if email_domain(row["Email"]) == query
    ]

    if not users:
        return UsersByDomainResponse(
            status=LookupStatus.NOT_REGISTERED,
            query=query,
            users=[],
            detail="No GAC users for this domain",
        )

    return UsersByDomainResponse(status=LookupStatus.FOUND, query=query, users=users)
