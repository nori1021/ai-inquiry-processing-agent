from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LookupStatus(str, Enum):
    FOUND = "FOUND"
    NOT_REGISTERED = "NOT_REGISTERED"
    UNKNOWN = "UNKNOWN"


class UserRecord(BaseModel):
    user_id: str
    email: str
    company_id: str
    company_name: str
    status: str


class CompanyRecord(BaseModel):
    company_id: str
    company_name: str
    email_domain: str
    status: str


class UserLookupResponse(BaseModel):
    status: LookupStatus
    query: str
    user: Optional[UserRecord] = None
    detail: Optional[str] = None


class CompanyLookupResponse(BaseModel):
    status: LookupStatus
    query: str
    company: Optional[CompanyRecord] = None
    detail: Optional[str] = None


class UsersByDomainResponse(BaseModel):
    status: LookupStatus
    query: str
    users: list[UserRecord] = Field(default_factory=list)
    detail: Optional[str] = None


class DomainCandidate(BaseModel):
    domain: str
    company_id: str
    company_name: str
    score: float
    note: str = "candidate_only_never_auto_accepted"


class SimilarDomainsResponse(BaseModel):
    status: LookupStatus
    query: str
    threshold: float
    candidates: list[DomainCandidate] = Field(default_factory=list)
    detail: Optional[str] = None
