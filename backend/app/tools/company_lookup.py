from __future__ import annotations

from typing import Optional

from rapidfuzz import fuzz

from app.config import get_settings
from app.schemas.lookup import (
    CompanyLookupResponse,
    CompanyRecord,
    DomainCandidate,
    LookupStatus,
    SimilarDomainsResponse,
)
from app.services.excel_loader import ExcelSourceStatus, load_dataframe
from app.services.normalization import normalize_domain

COMPANY_COLUMNS = ["CompanyID", "CompanyName", "EmailDomain", "Status"]


def _row_to_company(row: dict) -> CompanyRecord:
    return CompanyRecord(
        company_id=row["CompanyID"],
        company_name=row["CompanyName"],
        email_domain=row["EmailDomain"],
        status=row["Status"],
    )


def _load_companies():
    settings = get_settings()
    return load_dataframe(
        settings.ldap_companies_file,
        COMPANY_COLUMNS,
        cache_key="ldap_companies",
    )


def get_ldap_company(company_id: str) -> CompanyLookupResponse:
    """Exact CompanyID match (case-sensitive ID token)."""
    query = (company_id or "").strip()
    loaded = _load_companies()

    if loaded.status == ExcelSourceStatus.UNKNOWN or loaded.frame is None:
        return CompanyLookupResponse(
            status=LookupStatus.UNKNOWN,
            query=query,
            detail=loaded.detail or "LDAP companies source unavailable",
        )

    for _, row in loaded.frame.iterrows():
        if row["CompanyID"] == query:
            return CompanyLookupResponse(
                status=LookupStatus.FOUND,
                query=query,
                company=_row_to_company(row.to_dict()),
            )

    return CompanyLookupResponse(
        status=LookupStatus.NOT_REGISTERED,
        query=query,
        detail="No LDAP company with this CompanyID",
    )


def get_company_by_domain(domain: str) -> CompanyLookupResponse:
    """Exact case-insensitive EmailDomain match."""
    query = normalize_domain(domain)
    loaded = _load_companies()

    if loaded.status == ExcelSourceStatus.UNKNOWN or loaded.frame is None:
        return CompanyLookupResponse(
            status=LookupStatus.UNKNOWN,
            query=query,
            detail=loaded.detail or "LDAP companies source unavailable",
        )

    for _, row in loaded.frame.iterrows():
        if normalize_domain(row["EmailDomain"]) == query:
            return CompanyLookupResponse(
                status=LookupStatus.FOUND,
                query=query,
                company=_row_to_company(row.to_dict()),
            )

    return CompanyLookupResponse(
        status=LookupStatus.NOT_REGISTERED,
        query=query,
        detail="No LDAP company with this email domain",
    )


def find_similar_domains(
    domain: str,
    threshold: Optional[float] = None,
) -> SimilarDomainsResponse:
    """
    RapidFuzz similarity against known company domains.
    Returns candidates only — never auto-accepted as same company.
    Exact matches are excluded (use get_company_by_domain).
    """
    settings = get_settings()
    query = normalize_domain(domain)
    effective_threshold = (
        float(threshold) if threshold is not None else float(settings.similarity_threshold)
    )
    loaded = _load_companies()

    if loaded.status == ExcelSourceStatus.UNKNOWN or loaded.frame is None:
        return SimilarDomainsResponse(
            status=LookupStatus.UNKNOWN,
            query=query,
            threshold=effective_threshold,
            detail=loaded.detail or "LDAP companies source unavailable",
        )

    candidates: list[DomainCandidate] = []
    for _, row in loaded.frame.iterrows():
        known = normalize_domain(row["EmailDomain"])
        if not known or known == query:
            continue
        score = float(fuzz.ratio(query, known))
        if score >= effective_threshold:
            candidates.append(
                DomainCandidate(
                    domain=known,
                    company_id=row["CompanyID"],
                    company_name=row["CompanyName"],
                    score=score,
                )
            )

    candidates.sort(key=lambda c: c.score, reverse=True)

    if not candidates:
        return SimilarDomainsResponse(
            status=LookupStatus.NOT_REGISTERED,
            query=query,
            threshold=effective_threshold,
            candidates=[],
            detail="No similar domain candidates above threshold",
        )

    return SimilarDomainsResponse(
        status=LookupStatus.FOUND,
        query=query,
        threshold=effective_threshold,
        candidates=candidates,
    )
