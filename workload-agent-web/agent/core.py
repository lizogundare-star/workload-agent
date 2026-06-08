from __future__ import annotations
from datetime import datetime, timezone
import uuid
from datetime import datetime
from typing import Optional

import anthropic

from config import settings
from models import Task, Priority, Source, TaskStatus, RawAsanaTask, DailySummary
from agent.extractor import extract_tasks_from_email
from agent.prioritizer import apply_priority
from storage.db import upsert_task, get_all_tasks, get_all_rules, delete_tasks_by_source

_ai = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _asana_priority(task: RawAsanaTask):
    tags = [t.lower() for t in task.tags]
    if "urgent" in tags or "blocker" in tags:
        return Priority.HIGH, "Tagged urgent/blocker in Asana"
    if task.due_on:
        try:
           delta = datetime.fromisoformat(task.due_on).replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
            if delta.total_seconds() < 0:
                return Priority.HIGH, "Overdue"
            if delta.days == 0:
                return Priority.HIGH, "Due today"
            if delta.days <= 2:
                return Priority.MID, "Due in 2 days"
            if delta.days <= 7:
                return Priority.MID, "Due this week"
        except ValueError:
            pass
    return Priority.LOW, "No urgent signals"


async def _process_emails(source: Source, emails) -> list[Task]:
    tasks = []
    loop = asyncio.get_event_loop()
    for em in emails:
        extracted = await loop.run_in_executor(None, extract_tasks_from_email, em)
        for t in extracted:
            deadline = None
            if t.get("deadline"):
                try:
                    deadline = datetime.fromisoformat(t["deadline"])
                except ValueError:
                    pass
            try:
                priority = Priority(t.get("priority", "low"))
            except ValueError:
                priority = Priority.LOW
            tasks.append(Task(
                id=f"{source.value}_{em.id}_{uuid.uuid4().hex[:6]}",
                title=t.get("title", em.subject[:80]),
                description=t.get("description", ""),
                priority=priority,
                deadline=deadline,
                source=source,
                source_id=em.id,
                sender=f"{em.sender} <{em.sender_email}>",
                ai_reasoning=t.get("reasoning", ""),
            ))
    return tasks


def _process_asana(raw: list[RawAsanaTask]) -> list[Task]:
    tasks = []
    for r in raw:
        priority, reasoning = _asana_priority(r)
        deadline = None
        if r.due_on:
            try:
                deadline = datetime.fromisoformat(r.due_on + "T23:59:59")
            except ValueError:
                pass
        tasks.append(Task(
            id=f"asana_{r.gid}",
            title=r.name,
            description=r.notes,
            priority=priority,
            deadline=deadline,
            source=Source.ASANA,
            source_id=r.gid,
            project=r.project_name,
            ai_reasoning=reasoning,
        ))
    return tasks


async def sync_all(lookback_hours: Optional[int] = None) -> dict:
    from connectors.gmail_imap import fetch_recent_emails as gmail_fetch
    from connectors.outlook_imap import fetch_recent_emails as outlook_fetch
    from connectors.asana_connector import fetch_my_tasks

    rules = await get_all_rules()
    counts = {"gmail": 0, "outlook": 0, "asana": 0, "total": 0, "errors": []}

    for source, fetch_fn in [
        (Source.GMAIL, lambda: gmail_fetch(lookback_hours)),
        (Source.OUTLOOK, lambda: outlook_fetch(lookback_hours)),
    ]:
        try:
            await delete_tasks_by_source(source.value)
            loop = asyncio.get_event_loop()
            emails = await loop.run_in_executor(None, fetch_fn)
            tasks = await _process_emails(source, emails)
            for task in tasks:
                apply_priority(task, rules)
                await upsert_task(task)
            counts[source.value] = len(tasks)
        except Exception as e:
            import traceback
            msg = f"{source.value}: {e}"
            print(f"SYNC ERROR — {msg}")
            traceback.print_exc()
            counts["errors"].append(msg)

    try:
        await delete_tasks_by_source(Source.ASANA.value)
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, fetch_my_tasks)
        tasks = _process_asana(raw)
        for task in tasks:
            apply_priority(task, rules)
            await upsert_task(task)
        counts["asana"] = len(tasks)
    except Exception as e:
        import traceback
        msg = f"asana: {e}"
        print(f"SYNC ERROR — {msg}")
        traceback.print_exc()
        counts["errors"].append(msg)

    counts["total"] = counts["gmail"] + counts["outlook"] + counts["asana"]
    return counts


async def generate_summary() -> DailySummary:
    all_tasks = await get_all_tasks()
    active = [t for t in all_tasks if t.status != TaskStatus.COMPLETED]

    high = [t for t in active if t.priority == Priority.HIGH]
    mid  = [t for t in active if t.priority == Priority.MID]
    low  = [t for t in active if t.priority == Priority.LOW]

    task_text = "\n".join(
        f"[{t.priority.upper()}] {t.title} — due: {t.deadline.date() if t.deadline else 'none'} — {t.source.value}"
        for t in active[:40]
    ) or "No active tasks."

    resp = _ai.messages.create(
        model=settings.claude_model,
        max_tokens=400,
        messages=[{"role": "user", "content": f"""\
You are an executive assistant. Here is my current workload across two jobs:

{task_text}

Write a concise briefing (3-5 sentences) covering: what's most urgent today, \
any deadlines this week, and a clear focus recommendation. \
Be direct. No bullet points."""}],
    )

    return DailySummary(
        generated_at=datetime.utcnow(),
        high_count=len(high),
        mid_count=len(mid),
        low_count=len(low),
        total_count=len(active),
        narrative=resp.content[0].text.strip(),
        top_tasks=sorted(high, key=lambda t: t.deadline or datetime.max)[:5],
    )
