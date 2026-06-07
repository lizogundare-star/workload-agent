"""
Gmail connector using IMAP + App Password.
No OAuth, no credentials file — just email + app password.

How to get a Gmail App Password:
  1. Go to myaccount.google.com → Security
  2. Turn on 2-Step Verification (if not already on)
  3. Search "App passwords" → create one for "Mail"
  4. Copy the 16-character password into GMAIL_APP_PASSWORD in Railway
"""
from __future__ import annotations
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta, timezone
import uuid

from config import settings
from models import RawEmail, Source


def _decode_str(value: str | bytes, charset: str = "utf-8") -> str:
    if isinstance(value, bytes):
        return value.decode(charset or "utf-8", errors="ignore")
    return value


def _decode_header(raw: str) -> str:
    parts = decode_header(raw or "")
    result = []
    for part, charset in parts:
        result.append(_decode_str(part, charset or "utf-8"))
    return " ".join(result)


def _get_body(msg) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="ignore"
                    )[:500]
                except Exception:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="ignore"
            )[:500]
        except Exception:
            pass
    return ""


def fetch_recent_emails(lookback_hours: int = None) -> list[RawEmail]:
    if not settings.gmail_address or not settings.gmail_app_password:
        return []

    hours = lookback_hours or settings.email_lookback_hours
    since = (datetime.utcnow() - timedelta(hours=hours)).strftime("%d-%b-%Y")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(settings.gmail_address, settings.gmail_app_password)
        mail.select("inbox")

        _, msg_ids = mail.search(None, f'SINCE {since} NOT KEYWORD "Junk"')
        ids = msg_ids[0].split()[-50:]  # cap at 50 most recent

        emails: list[RawEmail] = []
        for mid in reversed(ids):  # newest first
            _, data = mail.fetch(mid, "(RFC822)")
            if not data or not data[0]:
                continue

            msg = email.message_from_bytes(data[0][1])
            subject = _decode_header(msg.get("Subject", "(no subject)"))
            from_raw = _decode_header(msg.get("From", ""))
            date_str = msg.get("Date", "")

            # Parse sender
            if "<" in from_raw:
                name, addr = from_raw.rsplit("<", 1)
                sender_name = name.strip().strip('"')
                sender_email = addr.rstrip(">").strip().lower()
            else:
                sender_name = from_raw
                sender_email = from_raw.lower()

            # Parse date
            try:
                received_at = email.utils.parsedate_to_datetime(date_str)
                received_at = received_at.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                received_at = datetime.utcnow()

            body = _get_body(msg)

            emails.append(RawEmail(
                id=mid.decode(),
                source=Source.GMAIL,
                subject=subject,
                sender=sender_name or sender_email,
                sender_email=sender_email,
                body_snippet=body[:500],
                received_at=received_at,
            ))

        mail.logout()
        return emails

    except imaplib.IMAP4.error as e:
        raise RuntimeError(f"Gmail IMAP error: {e}") from e
