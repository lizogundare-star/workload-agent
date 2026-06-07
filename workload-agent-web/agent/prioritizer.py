from __future__ import annotations
from datetime import datetime, timedelta
from models import Priority, PriorityRule, RuleConditionField, RuleOperator, Task


def _match(rule: PriorityRule, task: Task) -> bool:
    field_map = {
        RuleConditionField.SENDER_EMAIL: task.sender or "",
        RuleConditionField.SUBJECT: task.title,
        RuleConditionField.PROJECT: task.project or "",
        RuleConditionField.SOURCE: task.source.value,
    }
    value = field_map.get(rule.field, "").lower()
    target = rule.value.lower()
    if rule.operator == RuleOperator.CONTAINS:
        return target in value
    elif rule.operator == RuleOperator.EQUALS:
        return value == target
    elif rule.operator == RuleOperator.STARTS_WITH:
        return value.startswith(target)
    return False


def _deadline_bump(deadline: datetime | None) -> Priority | None:
    if not deadline:
        return None
    delta = deadline - datetime.utcnow()
    if delta.total_seconds() < 0:
        return Priority.HIGH
    if delta < timedelta(hours=24):
        return Priority.HIGH
    if delta < timedelta(days=3):
        return Priority.MID
    return None


def apply_priority(task: Task, rules: list[PriorityRule]) -> Task:
    # 1. User rules always win
    for rule in rules:
        if _match(rule, task):
            task.priority = rule.priority
            task.rule_triggered = rule.name
            return task
    # 2. Deadline heuristic can only upgrade, never downgrade
    bump = _deadline_bump(task.deadline)
    if bump:
        rank = {Priority.HIGH: 3, Priority.MID: 2, Priority.LOW: 1}
        if rank[bump] > rank[task.priority]:
            task.priority = bump
            task.ai_reasoning += f" (bumped to {bump.value} due to deadline)"
    return task
