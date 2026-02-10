"""Email ingestion stub – processes incoming emails into submissions."""

from __future__ import annotations

import email
import uuid
from email import policy
from typing import Any

__all__ = ["process_incoming_email"]


async def process_incoming_email(raw_email: str | bytes) -> dict[str, Any]:
    """Parse a raw email and create a submission record.

    This is a stub implementation. In production, this would:
    1. Parse the MIME message
    2. Extract sender / subject / attachments
    3. Match to an existing case via subject or reference
    4. Create a Submission + SubmissionDocument in DB
    5. Trigger extraction
    """
    if isinstance(raw_email, str):
        raw_email = raw_email.encode("utf-8")

    msg = email.message_from_bytes(raw_email, policy=policy.default)
    sender = msg.get("From", "unknown")
    subject = msg.get("Subject", "")

    attachments: list[dict] = []
    for part in msg.walk():
        content_disposition = part.get("Content-Disposition", "")
        if "attachment" in content_disposition:
            filename = part.get_filename() or f"attachment_{uuid.uuid4().hex[:8]}"
            attachments.append({"filename": filename, "size": len(part.get_payload(decode=True) or b"")})

    return {
        "sender": sender,
        "subject": subject,
        "attachments": attachments,
        "status": "stub_not_persisted",
    }
