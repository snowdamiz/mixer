#!/usr/bin/env python3
"""Check five FieldLog workspace copies captured by the root Android run."""
from hashlib import sha256
import json
from pathlib import Path
import sys

PROJECT = "22F02008-0000-4000-8000-000000000001"
DRAFT = "22F02008-0000-4000-8000-000000000003"
FIRST = "976F233C-3FFB-440E-BC18-10027556C27B"
BEFORE = "D8FD094D-6A4E-4B03-930E-1C4BEE0FB8A7"
TARGET = "91094B1F-51E9-42AD-9CF1-64055970E7CB"


def require(ok, message):
    if not ok:
        raise SystemExit(message)


def order(state):
    rows = sorted((row for row in state["tasks"] if row["projectID"] == PROJECT), key=lambda row: row["position"])
    require([row["position"] for row in rows] == [0, 1, 2], "Expected three contiguous positions")
    return [row["id"] for row in rows]


def main(paths):
    seed, baseline, before_move, after_move, rollback, offline = (Path(path).read_bytes() for path in paths)
    require(baseline == before_move == seed, "Initial or pre-action workspace differs from the installed seed")
    require(after_move == rollback == offline, "Rollback or offline launch changed the moved workspace")
    before, after = map(json.loads, (before_move, after_move))
    require(order(before) == [FIRST, BEFORE, TARGET] and order(after) == [FIRST, TARGET, BEFORE],
            "The target did not move before the adjacent task")
    require(after["revision"] == before["revision"] + 1
            and after["outbox"][:-1] == before["outbox"] and len(after["outbox"]) == len(before["outbox"]) + 1,
            "Expected exactly one revision and outbox increment")
    event = after["outbox"][-1]
    require(event["kind"] == "taskOrderChanged" and event["recordID"] == PROJECT
            and event["revision"] == after["revision"], "Expected the project task-order outbox entry")
    require({k: v for k, v in before.items() if k not in {"revision", "outbox", "tasks"}}
            == {k: v for k, v in after.items() if k not in {"revision", "outbox", "tasks"}}
            and after["restoration"]["openDraftID"] == DRAFT
            and sum(draft["id"] == DRAFT for draft in after["drafts"]) == 1, "Stored draft or other workspace data changed")
    before_rows = {row["id"]: row for row in before["tasks"]}
    after_rows = {row["id"]: row for row in after["tasks"]}
    require(len(before_rows) == len(before["tasks"]) == len(after_rows) == len(after["tasks"])
            and before_rows.keys() == after_rows.keys(), "Task identities changed")
    for task, old in before_rows.items():
        new = after_rows[task]
        changed = {"position", "updatedAt"} if old["projectID"] == PROJECT else set()
        require({k: v for k, v in old.items() if k not in changed}
                == {k: v for k, v in new.items() if k not in changed}, f"Task data changed for {task}")
    print(json.dumps({"target": TARGET, "adjacent": BEFORE, "beforeOrder": order(before),
                      "afterOrder": order(after), "openDraft": DRAFT, "revision": after["revision"],
                      "outbox": len(after["outbox"]), "workspaceSHA256": sha256(after_move).hexdigest()},
                     sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 7:
        raise SystemExit("Usage: verify-workspace.py SEED BASELINE PRE_MOVE POST_MOVE ROLLBACK OFFLINE")
    main(sys.argv[1:])
