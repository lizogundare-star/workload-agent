from __future__ import annotations
import asana
from asana.rest import ApiException
from config import settings
from models import RawAsanaTask


def _client():
    configuration = asana.Configuration()
    configuration.access_token = settings.asana_access_token
    return asana.ApiClient(configuration)


def fetch_my_tasks() -> list[RawAsanaTask]:
    if not settings.asana_access_token:
        return []

    with _client() as client:
        tasks_api = asana.TasksApi(client)
        users_api = asana.UsersApi(client)

        try:
            me = users_api.get_user("me", opts={})
            user_gid = me["gid"]
        except ApiException as e:
            raise RuntimeError(f"Asana auth failed: {e}") from e

        opts = {
            "opt_fields": "gid,name,notes,due_on,memberships.project.name,tags.name,completed",
            "completed_since": "now",
        }

        try:
            task_list = tasks_api.get_tasks_for_user(
                user_gid,
                workspace=settings.asana_workspace_gid,
                opts=opts,
            )
        except ApiException as e:
            raise RuntimeError(f"Asana task fetch failed: {e}") from e

        results: list[RawAsanaTask] = []
        for task in task_list:
            memberships = task.get("memberships") or []
            project_name = None
            if memberships:
                project_name = (memberships[0].get("project") or {}).get("name")

            tags = [t["name"] for t in (task.get("tags") or []) if t.get("name")]

            results.append(RawAsanaTask(
                gid=task["gid"],
                name=task.get("name", ""),
                notes=(task.get("notes") or "")[:500],
                due_on=task.get("due_on"),
                project_name=project_name,
                completed=task.get("completed", False),
                tags=tags,
            ))

        return results


def list_workspaces() -> list[dict]:
    with _client() as client:
        api = asana.WorkspacesApi(client)
        return list(api.get_workspaces(opts={}))
