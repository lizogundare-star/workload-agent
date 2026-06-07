from __future__ import annotations
import json
from datetime import datetime
import anthropic
from config import settings
from models import RawEmail

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM = """\
You extract actionable tasks from emails. For each task return:
- title: under 10 words
- description: what needs doing
- priority: "high", "mid", or "low"
- deadline: ISO datetime string if mentioned/inferable, else null
- reasoning: 1 sentence on why this priority

HIGH = urgent, due today/tomorrow, from management/clients, blocking
MID = due this week, normal work items
LOW = FYI, future, nice-to-have

If no actionable tasks, return {"tasks": []}.
Return ONLY valid JSON: {"tasks": [{...}]}"""


def extract_tasks_from_email(email: RawEmail, today: datetime = None) -> list[dict]:
    today_str = (today or datetime.utcnow()).strftime("%A, %B %d, %Y")
    prompt = f"""Today is {today_str}.

From: {email.sender} <{email.sender_email}>
Subject: {email.subject}
Received: {email.received_at.strftime("%Y-%m-%d %H:%M UTC")}

{email.body_snippet}

Extract actionable tasks."""

    resp = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text).get("tasks", [])
    except json.JSONDecodeError:
        return []
