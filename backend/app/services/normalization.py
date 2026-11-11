def normalize_email(email: str) -> str:
    """Strip and lower-case the full address. No fuzzy matching."""
    return (email or "").strip().lower()


def normalize_domain(domain: str) -> str:
    """Strip, remove a single leading '@', lower-case."""
    value = (domain or "").strip().lower()
    if value.startswith("@"):
        value = value[1:]
    return value.strip()


def email_domain(email: str) -> str:
    normalized = normalize_email(email)
    if "@" not in normalized:
        return ""
    return normalize_domain(normalized.rsplit("@", 1)[-1])
