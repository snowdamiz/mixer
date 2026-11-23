#!/usr/bin/env python3
"""Check the actual Simulator app's persisted workspace after the XCTest cold reopen."""
import hashlib
import json
from pathlib import Path
import sys
import uuid


def require(condition, message):
    if not condition:
        raise SystemExit(message)


if len(sys.argv) != 2:
    raise SystemExit("Usage: check-workspace.py WORKSPACE_JSON")

path = Path(sys.argv[1])
data = path.read_bytes()
workspace = json.loads(data)
project = "4C589BDE-5F6C-41F4-8ACB-E6099D0A1877"
date = 821692800
require(workspace["schema"] == 1 and workspace["revision"] == 2,
        "Expected only the project seed and one task commit")
uuid.UUID(workspace["id"])
require(workspace["projects"] == [{"id": project, "title": "Pump station", "site": "", "createdAt": date}],
        "Seed project changed")
require(workspace["restoration"] == {"selectedProjectID": project}, "Seed restoration changed")
require(all(workspace[name] == [] for name in ("attachments", "drafts", "entries")),
        "Unexpected persisted attachment, draft, or entry")
require(len(workspace["tasks"]) == 1, "Expected one task after cold reopen")
task, = workspace["tasks"]
uuid.UUID(task["id"])
require(task == {"id": task["id"], "projectID": project, "title": "Inspect pump P-17", "responsible": "",
                 "completed": False, "position": 0, "updatedAt": date},
        "Expected exact single-line task in the seeded project")
require(len(workspace["outbox"]) == 2, "Expected only the project and task outbox events")
seed, save = workspace["outbox"]
uuid.UUID(seed["id"])
uuid.UUID(save["id"])
require(seed == {"id": seed["id"], "kind": "projectCreated", "recordID": project,
                 "revision": 1, "createdAt": date},
        "Seed outbox event changed")
require(save == {"id": save["id"], "kind": "taskSaved", "recordID": task["id"],
                 "revision": 2, "createdAt": date} and save["id"] != seed["id"],
        "Expected one outbox event linked to the single-line task")
print(json.dumps({"revision": workspace["revision"], "title": task["title"], "taskCount": 1,
                  "linkedTaskOutboxEvents": 1, "workspaceSHA256": hashlib.sha256(data).hexdigest()}))
