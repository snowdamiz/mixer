#!/usr/bin/env python3
"""Verify the exact isolated app-private tree copied by root after XCTest."""
import base64
import json
from pathlib import Path
import sys

from prepare import digest

def verify(build, container):
    def load(path):
        return json.loads(path.read_text())

    def require(value, description):
        if not value:
            raise ValueError(description)

    fixtures = build / "signed"
    state_file = container / "recovery/state.json"
    workspace_file = container / "workspace/workspace.json"
    state = load(state_file)
    host = load(fixtures / "host.json")
    require(state["fingerprint"] == host["runtime"] and state["host"] == host, "Installed host mismatch")
    require(state["acceptedSequence"] == 3 and state["installation"] == "fieldlog-ios-local"
            and state["channel"] == "beta", "Unexpected durable update selection")
    require(all(state[key] is None for key in ("pending", "staged", "attempt"))
            and not state["failures"] and not state["quarantine"], "Unresolved update state")
    observed = {}
    for key, name, sequence in [("healthy", "baseline", 3), ("previousHealthy", "reviewed", 2)]:
        health = state[key]
        require(set(health["completedMilestones"]) == {"feature_started", "first_screen"}
                and health["observationSeconds"] == 1, f"Missing native health for {key}")
        candidate = state["candidates"][health["candidateID"]]
        assignment = load(fixtures / f"sequence-{sequence}.assignment.json")
        manifest = load(fixtures / f"{name}.manifest.json")
        payload = fixtures / f"{name}.wasm"
        checksum = digest(payload)
        require(candidate["sequence"] == sequence and candidate["payloadSHA256"] == checksum
                and candidate["payloadBytes"] == payload.stat().st_size
                and candidate["artifactSHA256"] == assignment["assignment"]["artifact_sha256"],
                f"Unexpected durable candidate for {key}")
        require(json.loads(base64.b64decode(candidate["signedAssignment"], validate=True)) == assignment
                and json.loads(base64.b64decode(candidate["signedManifest"], validate=True)) == manifest,
                f"Signed wire envelope mismatch for {key}")
        require(digest(container / "recovery" / f"{checksum}.payload") == checksum,
                f"Persisted payload mismatch for {key}")
        observed[key] = {"candidate": health["candidateID"], "launch": health["launchID"], "sequence": sequence,
                         "artifactSHA256": candidate["artifactSHA256"], "payloadSHA256": checksum,
                         "milestones": health["completedMilestones"]}
    workspace = load(workspace_file)
    [task] = workspace["tasks"]
    [project] = workspace["projects"]
    outbox = workspace["outbox"]
    require(workspace["schema"] == 1 and workspace["revision"] == 6 and task["completed"] is True
            and task["projectID"] == project["id"] and task["title"] == "Inspect pump", "Workspace state did not survive the release sequence")
    require([change["revision"] for change in outbox] == [1, 1, 2, 3, 4, 5, 6]
            and len({change["id"] for change in outbox}) == 7, "Unexpected workspace outbox revisions")
    require([(change["kind"], change["recordID"]) for change in outbox]
            == [("projectCreated", project["id"])] + [("taskSaved", task["id"])] * 6,
            "Workspace outbox changed record identity")
    return {
        "runtimeFingerprint": host["runtime"], "acceptedSequence": 3,
        "recoverySHA256": digest(state_file), **observed,
        "workspaceSHA256": digest(workspace_file), "workspaceRevision": workspace["revision"],
        "taskID": task["id"], "taskTitle": task["title"], "outboxEntries": len(outbox),
    }

if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
