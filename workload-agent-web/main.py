from __future__ import annotations
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from config import settings
from models import (
    DailySummary, Priority, PriorityRule, PriorityRuleCreate,
    Task, TaskPriorityOverride, TaskStatus,
)
from storage.db import (
    delete_rule, get_all_rules, get_all_tasks, get_task,
    init_db, save_rule, update_task,
)
from agent.core import generate_summary, sync_all

app = FastAPI(title="Workload Agent API", docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

bearer = HTTPBearer(auto_error=False)


@app.on_event("startup")
async def startup():
    await init_db()


def verify(creds: Optional[HTTPAuthorizationCredentials] = Security(bearer)):
    if not creds or creds.credentials != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(static_dir / "index.html")


@app.get("/api/tasks", response_model=list[Task])
async def list_tasks(
    priority: Optional[Priority] = None,
    source: Optional[str] = None,
    task_status: Optional[TaskStatus] = Query(None, alias="status"),
    _: bool = Depends(verify),
):
    tasks = await get_all_tasks()
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    if source:
        tasks = [t for t in tasks if t.source.value == source]
    if task_status:
        tasks = [t for t in tasks if t.status == task_status]
    rank = {Priority.HIGH: 0, Priority.MID: 1, Priority.LOW: 2}

    def sort_key(t):
        if t.deadline is None:
            d = datetime.max
        else:
            d = t.deadline.replace(tzinfo=None) if t.deadline.tzinfo else t.deadline
        return (rank[t.priority], d)

    tasks.sort(key=sort_key)
    return tasks


@app.get("/api/tasks/{task_id}", response_model=Task)
async def get_single_task(task_id: str, _: bool = Depends(verify)):
    task = await get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@app.patch("/api/tasks/{task_id}/priority", response_model=Task)
async def override_priority(task_id: str, body: TaskPriorityOverride, _: bool = Depends(verify)):
    task = await get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    task.priority = body.priority
    task.rule_triggered = "manual override"
    await update_task(task)
    return task


@app.patch("/api/tasks/{task_id}/status", response_model=Task)
async def set_status(
    task_id: str,
    new_status: TaskStatus = Query(...),
    _: bool = Depends(verify),
):
    task = await get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    task.status = new_status
    await update_task(task)
    return task


@app.post("/api/refresh")
async def refresh(
    lookback_hours: Optional[int] = None,
    _: bool = Depends(verify),
):
    counts = await sync_all(lookback_hours)
    return {"status": "ok", "synced": counts}


@app.get("/api/summary", response_model=DailySummary)
async def daily_summary(_: bool = Depends(verify)):
    return await generate_summary()


@app.get("/api/rules", response_model=list[PriorityRule])
async def list_rules(_: bool = Depends(verify)):
    return await get_all_rules()


@app.post("/api/rules", response_model=PriorityRule, status_code=201)
async def create_rule(body: PriorityRuleCreate, _: bool = Depends(verify)):
    rule = PriorityRule(id=uuid.uuid4().hex, **body.model_dump())
    await save_rule(rule)
    return rule


@app.delete("/api/rules/{rule_id}", status_code=204)
async def remove_rule(rule_id: str, _: bool = Depends(verify)):
    await delete_rule(rule_id)


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}
