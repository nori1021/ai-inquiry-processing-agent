from __future__ import annotations

from app.config import get_settings
from app.schemas.lookup import LookupStatus, UserLookupResponse, UserRecord
from app.services.excel_loader import ExcelSourceStatus, load_dataframe
from app.services.normalization import normalize_email

USER_COLUMNS = ["UserID", "Email", "CompanyID", "CompanyName", "Status"]


def _row_to_user(row: dict) -> UserRecord:
    return UserRecord(
        user_id=row["UserID"],
        email=row["Email"],
        company_id=row["CompanyID"],
        company_name=row["CompanyName"],
        status=row["Status"],
    )


def get_ldap_user(email: str) -> UserLookupResponse:
    """Exact case-insensitive email match against LDAP users Excel."""
    query = normalize_email(email)
    settings = get_settings()
    loaded = load_dataframe(
        settings.ldap_users_file,
        USER_COLUMNS,
        cache_key="ldap_users",
    )

    if loaded.status == ExcelSourceStatus.UNKNOWN or loaded.frame is None:
        return UserLookupResponse(
            status=LookupStatus.UNKNOWN,
            query=query,
            detail=loaded.detail or "LDAP users source unavailable",
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
        detail="No LDAP user with this email",
    )
