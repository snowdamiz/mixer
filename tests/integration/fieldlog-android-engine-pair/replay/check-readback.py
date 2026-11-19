#!/usr/bin/env python3
"""Check copies captured from the owned Android installation during the upgrade."""
import hashlib
import json
from pathlib import Path
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def check(test, reason):
    if not test:
        raise ValueError(reason)


def read_json(path):
    return json.loads(path.read_bytes())


def installation(path):
    values = ET.parse(path).findall("string[@name='installation']")
    check(len(values) == 1 and values[0].text, "missing unique installation ID")
    return str(uuid.UUID(values[0].text))


def main(work):
    pair = read_json(ROOT / "package-result.json")["cases"]
    prior = (work / "workspace-before.json").read_bytes()
    current = (work / "workspace-after.json").read_bytes()
    check(prior == current, "workspace changed during upgrade or checklist read")
    workspace = json.loads(prior)
    check(isinstance(workspace, dict) and workspace.get("tasks"), "workspace has no saved task")
    install = installation(work / "install-before.xml")
    check(install == installation(work / "install-after.xml"), "installation ID changed")
    prior_journal = (work / "old-before.json").read_bytes()
    check(prior_journal == (work / "old-after.json").read_bytes(), "old runtime journal changed")
    observations = {}
    for label in ("old", "new"):
        journal = read_json(work / f"{label}-after.json")
        expected = pair[label]
        runtime = expected["host"]["runtime"]
        check(journal["fingerprint"] == journal["host"]["runtime"] == runtime, f"{label}: wrong runtime")
        check(journal["channel"] == "beta" and journal["installation"] == install, f"{label}: wrong cohort")
        sequence = expected["sequence"]
        check(journal["acceptedSequence"] == sequence, f"{label}: wrong durable cursor")
        healthy = journal["healthy"]
        candidate = journal["candidates"][healthy["candidateID"]]
        check(candidate["sequence"] == sequence
              and candidate["artifactSHA256"] == expected["artifactSHA256"]
              and candidate["payloadSHA256"] == expected["guestSHA256"], f"{label}: wrong healthy candidate")
        check({"first_screen", "feature_started"} <= set(healthy["completedMilestones"]), f"{label}: missing health milestones")
        observations[label] = {"runtime": runtime, "sequence": sequence,
                               "artifactSHA256": candidate["artifactSHA256"],
                               "payloadSHA256": candidate["payloadSHA256"]}
    print(json.dumps({"installation": install, "workspaceSHA256": hashlib.sha256(prior).hexdigest(),
                      "workspaceRevision": workspace["revision"], "cohorts": observations}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: check-readback.py OWNED_EVIDENCE_DIR")
    main(Path(sys.argv[1]))
