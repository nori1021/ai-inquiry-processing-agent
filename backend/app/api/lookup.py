from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.lookup import (
    CompanyLookupResponse,
    SimilarDomainsResponse,
    UserLookupResponse,
    UsersByDomainResponse,
)
from app.tools.company_lookup import (
    find_similar_domains,
    get_company_by_domain,
    get_ldap_company,
)
from app.tools.gac_lookup import get_gac_user, get_gac_users_by_domain
from app.tools.ldap_lookup import get_ldap_user

router = APIRouter()


@router.get("/ldap/users", response_model=UserLookupResponse)
def lookup_ldap_user(email: str = Query(..., min_length=1)) -> UserLookupResponse:
    return get_ldap_user(email)


@router.get("/gac/users", response_model=UserLookupResponse)
def lookup_gac_user(email: str = Query(..., min_length=1)) -> UserLookupResponse:
    return get_gac_user(email)


@router.get("/ldap/companies/{company_id}", response_model=CompanyLookupResponse)
def lookup_ldap_company(company_id: str) -> CompanyLookupResponse:
    return get_ldap_company(company_id)


@router.get("/ldap/companies", response_model=CompanyLookupResponse)
def lookup_company_by_domain(
    domain: str = Query(..., min_length=1),
) -> CompanyLookupResponse:
    return get_company_by_domain(domain)


@router.get("/gac/users-by-domain", response_model=UsersByDomainResponse)
def lookup_gac_users_by_domain(
    domain: str = Query(..., min_length=1),
) -> UsersByDomainResponse:
    return get_gac_users_by_domain(domain)


@router.get("/domains/similar", response_model=SimilarDomainsResponse)
def lookup_similar_domains(
    domain: str = Query(..., min_length=1),
    threshold: Optional[float] = Query(None, ge=0, le=100),
) -> SimilarDomainsResponse:
    return find_similar_domains(domain, threshold=threshold)
