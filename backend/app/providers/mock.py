from app.providers.approval import MockApprovalProvider


class MockEmailProvider:
    name = "mock"

    def send(self, to: str, subject: str, body: str) -> str:
        # Email always requires explicit human approval — never auto-send.
        # Phase 4 will perform Graph send only after AWAITING_EMAIL_APPROVAL is approved.
        return "blocked_pending_human_approval"


# Backward-compatible alias
__all__ = ["MockApprovalProvider", "MockEmailProvider"]
