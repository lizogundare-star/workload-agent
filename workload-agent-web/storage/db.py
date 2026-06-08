from __future__ import annotations
import aiosqlite
from datetime import datetime, timezone
from typing import Optional
from models import Task, PriorityRule
from config import settings

DB = settings.db_path

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    data TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
"""


async def init_db():
    async with aiosqlite.connect(DB) as db:
        for stmt in CREATE_SQL.strip().split(";"):
            if stmt.strip():
                await db.execute(stmt)
        await db.commit()


async def upsert_task(task: Task):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO tasks (id, source, data, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
            (task.id, task.source.value, task.model_dump_json(), task.updated_at.isoformat()),
        )
        await db.commit()


async def get_all_tasks() -> list[Task]:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT data FROM tasks ORDER BY updated_at DESC") as cur:
            rows = await cur.fetchall()
    return [Task.model_validate_json(r[0]) for r in rows]


async def get_task(task_id: str) -> Optional[Task]:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT data FROM tasks WHERE id=?", (task_id,)) as cur:
            row = await cur.fetchone()
    return Task.model_validate_json(row[0]) if row else None


async def update_task(task: Task):
    task.updated_at = datetime.now(timezone.utc)
    await upsert_task(task)


async def delete_tasks_by_source(source: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM tasks WHERE source=?", (source,))
        await db.commit()


async def save_rule(rule: PriorityRule):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO rules (id, data) VALUES (?,?)",
            (rule.id, rule.model_dump_json()),
        )
        await db.commit()


async def get_all_rules() -> list[PriorityRule]:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT data FROM rules") as cur:
            rows = await cur.fetchall()
    return [PriorityRule.model_validate_json(r[0]) for r in rows]


async def delete_rule(rule_id: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM rules WHERE id=?", (rule_id,))
        await db.commit()
