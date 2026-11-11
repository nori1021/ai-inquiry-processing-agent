from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.lookup import UserRecord


class RegistrationFlag(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class CombinedRegistrationState(str, Enum):
    LDAP_AND_GAC = "LDAP_AND_GAC"
    LDAP_ONLY = "LDAP_ONLY"
    GAC_ONLY = "GAC_ONLY"
    NEITHER = "NEITHER"
    UNKNOWN = "UNKNOWN"


class RegistrationCheckResponse(BaseModel):
    """Demo/test-oriented registration check result."""

    source: str  # ldap | gac
    registered: RegistrationFlag
    query_email: Optional[str] = None
    query_user_id: Optional[str] = None
    user: Optional[UserRecord] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    account_status: Optional[str] = None
    lookup_status: str
    detail: Optional[str] = None
    errors: list[str] = Field(default_factory=list)


class CombinedRegistrationCheckResponse(BaseModel):
    query_email: Optional[str] = None
    query_user_id: Optional[str] = None
    combined_state: CombinedRegistrationState
    ldap: RegistrationCheckResponse
    gac: RegistrationCheckResponse
    detail: Optional[str] = None
