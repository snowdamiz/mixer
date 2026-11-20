#!/usr/bin/env python3
"""Verify the saved-task snapshots from the installed localization replay."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid

TITLE = "فحص المضخة 07"
UNCHANGED = (
    "baseline-ltr", "baseline-rtl", "baseline-large",
    "reviewed-ltr", "reviewed-rtl", "reviewed-large", "review-pending",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_snapshot(directory, checkpoint):
    raw = (directory / f"workspace-{checkpoint}.json").read_bytes()
    return raw, json.loads(raw)


def check_initial(workspace):
    require(type(workspace["schema"]) is int and workspace["schema"] == 1
            and type(workspace["revision"]) is int,
            "unexpected workspace schema or revision")
    require(len(workspace["projects"]) == len(workspace["tasks"]) == 1,
            "the fixture needs one saved project and task")
    project = workspace["projects"][0]
    task = workspace["tasks"][0]
    require(task["projectID"] == project["id"] and task["title"] == TITLE
            and task["completed"] is False,
            "the saved fixture task must start open in its original project")
    seed_events = workspace["outbox"]
    require(any(event["kind"] == "taskSaved" and event["recordID"] == task["id"]
                for event in seed_events), "no ordinary task save in the starting outbox")
    return task


def check_transition(before, after, completed):
    task = before["tasks"][0]
    require(len(after["outbox"]) == len(before["outbox"]) + 1,
            "task edit must append one outbox row")
    event = after["outbox"][-1]
    revision = before["revision"] + 1
    event_id = uuid.UUID(event["id"])
    require(event["kind"] == "taskSaved" and event["recordID"] == task["id"]
            and event["revision"] == revision
            and all(uuid.UUID(prior["id"]) != event_id for prior in before["outbox"]),
            "appended outbox row differs from the selected task or its committed revision")
    require(len(after["tasks"]) == 1 and after["tasks"][0]["completed"] is completed,
            "the installed action did not commit the expected task state")
    expected = {
        **before,
        "revision": revision,
        "tasks": [{**task, "completed": completed, "updatedAt": after["tasks"][0]["updatedAt"]}],
        "outbox": [*before["outbox"], event],
    }
    require(after == expected, "the installed action changed other workspace fields or prior outbox rows")


def verify(directory):
    seed_raw, seed = read_snapshot(directory, "seed")
    task = check_initial(seed)
    hashes = {"seed": digest(seed_raw)}
    for checkpoint in UNCHANGED:
        raw, _ = read_snapshot(directory, checkpoint)
        require(raw == seed_raw, f"{checkpoint} mutated the saved workspace")
        hashes[checkpoint] = digest(raw)

    prior = seed
    snapshots = [seed]
    for checkpoint, completed in (("completed", True), ("reopened", False)):
        raw, snapshot = read_snapshot(directory, checkpoint)
        check_transition(prior, snapshot, completed)
        offline = checkpoint + "-offline"
        reopened, _ = read_snapshot(directory, offline)
        require(reopened == raw, f"{offline} differed after cold launch")
        hashes[checkpoint] = hashes[offline] = digest(raw)
        snapshots.append(snapshot)
        prior = snapshot

    return {
        "taskID": task["id"],
        "projectID": task["projectID"],
        "workspaceRevisions": [snapshot["revision"] for snapshot in snapshots],
        "outboxCounts": [len(snapshot["outbox"]) for snapshot in snapshots],
        "snapshotsSHA256": hashes,
    }


def main():
    checkpoints = ("seed", *UNCHANGED, "completed", "completed-offline", "reopened", "reopened-offline")
    parser = argparse.ArgumentParser(
        description=__doc__, epilog="Save each checkpoint as workspace-<checkpoint>.json. "
        "Required checkpoints are " + ", ".join(checkpoints) + ".",
    )
    parser.add_argument("directory", type=Path, help="directory of copied on-device workspace snapshots")
    args = parser.parse_args()
    try:
        result = verify(args.directory)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"Localized workspace readback refused: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
