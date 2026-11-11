"""Generate synthetic LDAP/GAC Excel sample files for local demos."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"


def main() -> None:
    SAMPLE.mkdir(parents=True, exist_ok=True)

    companies = pd.DataFrame(
        [
            {
                "CompanyID": "COMP001",
                "CompanyName": "Acme Corporation",
                "EmailDomain": "acme.com",
                "Status": "Active",
            },
            {
                "CompanyID": "COMP002",
                "CompanyName": "Globex Industries",
                "EmailDomain": "globex.com",
                "Status": "Active",
            },
            {
                "CompanyID": "COMP003",
                "CompanyName": "Initech LLC",
                "EmailDomain": "initech.co.jp",
                "Status": "Active",
            },
            {
                "CompanyID": "COMP004",
                "CompanyName": "Umbrella Japan",
                "EmailDomain": "umbrella-jp.com",
                "Status": "Active",
            },
            {
                "CompanyID": "COMP005",
                "CompanyName": "Soylent Corp",
                "EmailDomain": "soylent.io",
                "Status": "Inactive",
            },
            # Near-miss domain for similarity tests (acme.com vs acme.co)
            {
                "CompanyID": "COMP006",
                "CompanyName": "Acme Holdings",
                "EmailDomain": "acme.co",
                "Status": "Active",
            },
        ]
    )

    ldap_users = pd.DataFrame(
        [
            {
                "UserID": "U1001",
                "Email": "alice@acme.com",
                "CompanyID": "COMP001",
                "CompanyName": "Acme Corporation",
                "Status": "Active",
            },
            {
                "UserID": "U1002",
                "Email": "bob.smith@globex.com",
                "CompanyID": "COMP002",
                "CompanyName": "Globex Industries",
                "Status": "Active",
            },
            {
                "UserID": "U1003",
                "Email": "carol@initech.co.jp",
                "CompanyID": "COMP003",
                "CompanyName": "Initech LLC",
                "Status": "Active",
            },
            {
                "UserID": "U1004",
                "Email": "dave@umbrella-jp.com",
                "CompanyID": "COMP004",
                "CompanyName": "Umbrella Japan",
                "Status": "Inactive",
            },
            {
                "UserID": "U1005",
                "Email": "eve@soylent.io",
                "CompanyID": "COMP005",
                "CompanyName": "Soylent Corp",
                "Status": "Active",
            },
        ]
    )

    gac_users = pd.DataFrame(
        [
            {
                "UserID": "G2001",
                "Email": "alice@acme.com",
                "CompanyID": "COMP001",
                "CompanyName": "Acme Corporation",
                "Status": "Active",
            },
            {
                "UserID": "G2002",
                "Email": "frank@acme.com",
                "CompanyID": "COMP001",
                "CompanyName": "Acme Corporation",
                "Status": "Active",
            },
            {
                "UserID": "G2003",
                "Email": "grace@globex.com",
                "CompanyID": "COMP002",
                "CompanyName": "Globex Industries",
                "Status": "Active",
            },
            {
                "UserID": "G2004",
                "Email": "heidi@initech.co.jp",
                "CompanyID": "COMP003",
                "CompanyName": "Initech LLC",
                "Status": "Active",
            },
            {
                "UserID": "G2005",
                "Email": "ivan@unknown-partner.example",
                "CompanyID": "EXT001",
                "CompanyName": "External Partner",
                "Status": "Active",
            },
        ]
    )

    companies.to_excel(SAMPLE / "ldap_companies.xlsx", index=False)
    ldap_users.to_excel(SAMPLE / "ldap_users.xlsx", index=False)
    gac_users.to_excel(SAMPLE / "gac_users.xlsx", index=False)
    print(f"Wrote sample Excel files to {SAMPLE}")


if __name__ == "__main__":
    main()
