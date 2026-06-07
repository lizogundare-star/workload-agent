from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Priority(str, Enum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"


class Source(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    ASANA = "asana"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RawEmail(BaseModel):
    id: str
    source: Source
    subject: str
    sender: str
    sender_email: str
    body_snippet: str
    received_at: datetime


class RawAsanaTask(BaseModel):
    gid: str
    name: str
    notes: str = ""
    due_on: Optional[str] = None
    project_name: Optional[str] = None
    completed: bool = False
    tags: list[str] = Field(default_factory=list)


class Task(BaseModel):
    id: str
    title: str
    description: str
    priority: Priority
    status: TaskStatus = TaskStatus.PENDING
    deadline: Optional[datetime] = None
    source: Source
    source_id: str
    sender: Optional[str] = None
    project: Optional[str] = None
    ai_reasoning: str = ""
    rule_triggered: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RuleConditionField(str, Enum):
    SENDER_EMAIL = "sender_email"
    SUBJECT = "subject"
    PROJECT = "project"
    SOURCE = "source"


class RuleOperator(str, Enum):
    CONTAINS = "contains"
    EQUALS = "equals"
    STARTS_WITH = "starts_with"


class PriorityRule(BaseModel):
    id: str
    name: str
    field: RuleConditionField
    operator: RuleOperator
    value: str
    priority: Priority
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PriorityRuleCreate(BaseModel):
    name: str
    field: RuleConditionField
    operator: RuleOperator
    value: str
    priority: Priority


class TaskPriorityOverride(BaseModel):
    priority: Priority


class DailySummary(BaseModel):
    generated_at: datetime
    high_count: int
    mid_count: int
    low_count: int
    total_count: int
    narrative: str
    top_tasks: list[Task]
