"""
Outlook connector using IMAP.
Works with personal Microsoft accounts (outlook.com, hotmail.com)
and Microsoft 365 work accounts.

For Microsoft 365 work accounts, your IT admin may need to enable IMAP.
For personal accounts, IMAP is on by default.
"""
from __future__ import annotations
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta, timezone

from config import settings
from models import RawEmail, Source


def _decode_str(value: str | bytes, charset: str = "utf-8") -> str:
    if isinstance(value, bytes):
        return value.decode(charset or "utf-8", errors="ignore")
    return value


def _decode_header_str(raw: str) -> str:
    parts = decode_header(raw or "")
    return " ".join(_decode_str(p, c or "utf-8") for p, c in parts)


def _get_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
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
    if not settings.outlook_address or not settings.outlook_password:
        return []

    hours = lookback_hours or settings.email_lookback_hours
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%d-%b-%Y")

    # Try both IMAP servers (personal vs work accounts)
    # Note: Microsoft 365 work accounts using OAuth2/Modern Auth will not work
    # with basic password auth. If this is your account type, Outlook sync will
    # be skipped silently — Gmail and Asana will still sync normally.
    imap_hosts = ["imap-mail.outlook.com", "outlook.office365.com"]
    mail = None

    for host in imap_hosts:
        try:
            mail = imaplib.IMAP4_SSL(host)
            mail.login(settings.outlook_address, settings.outlook_password)
            break
        except imaplib.IMAP4.error:
            mail = None
            continue

    if mail is None:
        # Return empty list instead of raising — accounts using OAuth2/Modern Auth
        # cannot use basic password IMAP. Gmail and Asana will still sync.
        print("Outlook IMAP: skipping — account may require OAuth2/Modern Auth (basic password auth not supported)")
        return []

    mail.select("inbox")
    _, msg_ids = mail.search(None, f'SINCE {since}')
    ids = msg_ids[0].split()[-50:]

    emails: list[RawEmail] = []
    for mid in reversed(ids):
        _, data = mail.fetch(mid, "(RFC822)")
        if not data or not data[0]:
            continue

        msg = email.message_from_bytes(data[0][1])
        subject = _decode_header_str(msg.get("Subject", "(no subject)"))
        from_raw = _decode_header_str(msg.get("From", ""))
        date_str = msg.get("Date", "")

        if "<" in from_raw:
            name, addr = from_raw.rsplit("<", 1)
            sender_name = name.strip().strip('"')
            sender_email = addr.rstrip(">").strip().lower()
        else:
            sender_name = from_raw
            sender_email = from_raw.lower()

        try:
            received_at = email.utils.parsedate_to_datetime(date_str)
            received_at = received_at.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            received_at = datetime.now(timezone.utc).replace(tzinfo=None)

        emails.append(RawEmail(
            id=mid.decode(),
            source=Source.OUTLOOK,
            subject=subject,
            sender=sender_name or sender_email,
            sender_email=sender_email,
            body_snippet=_get_body(msg)[:500],
            received_at=received_at,
        ))

    mail.logout()
    return emails
