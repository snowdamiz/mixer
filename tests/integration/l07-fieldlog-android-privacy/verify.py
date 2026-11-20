#!/usr/bin/env python3
"""Verify the installed updater privacy observation from owned Android captures."""

import argparse
import json
from pathlib import Path
import re
import runpy
from types import SimpleNamespace
from xml.etree import ElementTree

from observe import admit_packet, digest, marker_hits, markers


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(path):
    return json.loads(path.read_bytes())


def verify(packet, captures):
    tenant, target, envelopes = admit_packet(packet)
    fixture = markers(packet)
    delivery = packet / "delivery-android"
    seed = (delivery / "Installed/calculation-seed.json").read_bytes()
    proof = runpy.run_path(str(Path(__file__).resolve().parents[1] / "fieldlog-task-calculation/android-readback.py"))
    baseline = read(delivery / "sequence-1.assignment.json")["assignment"]
    first = read(captures / "delivery/live.json")
    expected = SimpleNamespace(runtime=target["runtime"], installation=first["installation"], sequence=1,
                               artifact=baseline["artifact_sha256"],
                               payload=digest((delivery / "baseline.wasm").read_bytes()))
    app = {}
    for phase in ("delivery", "failure"):
        folder = captures / phase
        live, health_sha = proof["read_state"](folder / "live.json")
        candidate, launch = proof["check_live"](live, expected)
        retired, retired_sha = proof["read_state"](folder / "retired.json")
        proof["check_retired"](live, retired, candidate)
        scope = {key: value for key, value in target.items() if key not in {"channel", "runtime"}}
        require(live["host"]["scope"] == scope, "Wrong workspace scope in recovery")
        label = ("Signed checklist" if phase == "delivery" else "Using saved checklist release") + " | Sequence 1"
        require(any(node.get("text") == label and node.get("package") == "dev.fieldlog.generatedr90.calculation"
                    for node in ElementTree.parse(folder / "screen.xml").iter("node")),
                f"Expected installed release label at {phase}")
        require((folder / "workspace.json").read_bytes() == seed, "Fixture workspace changed")
        require(read(folder / "network.json") == {"-4": True, "-6": True}, "Default route remained reachable")
        pid = int((folder / "process").read_bytes())
        log = (folder / "app.log").read_bytes()
        timed = re.findall(rb"(?m)^\d\d-\d\d \d\d:\d\d:\d\d\.\d+\s+(\d+)\s+\d+\s+[A-Z]\s+", log)
        trace_rows = [line for line in log.splitlines() if b"FieldLogCalcTrace" in line]
        require(timed and trace_rows and all(int(value) == pid for value in timed),
                f"Missing Android trace or wrong process at {phase}")
        require(not marker_hits(log, fixture), f"Fixture workspace marker in app log at {phase}")
        app[phase] = {"pid": pid, "candidate": candidate, "launchID": launch,
                      "liveSHA256": health_sha, "retiredSHA256": retired_sha,
                      "logSHA256": digest(log), "logBytes": len(log), "appLogEntries": len(timed),
                      "traceRows": len(trace_rows)}

    require(app["delivery"]["candidate"] == app["failure"]["candidate"]
            and app["delivery"]["launchID"] != app["failure"]["launchID"]
            and app["delivery"]["pid"] != app["failure"]["pid"], "Expected cold fallback to the same candidate")
    rows = [json.loads(line) for line in (captures / "requests.jsonl").read_text().splitlines()]
    observed = [(x["phase"], x["requestKind"], x["status"]) for x in rows]
    require(observed == [("delivery", "offer", 200), ("delivery", "artifact", 200),
                         ("failure", "offer", 200), ("failure", "artifact", 503)],
            "Unexpected request sequence at the owned origin")
    installation = digest(expected.installation.encode())
    responses = (envelopes[1][1], envelopes[1][2], envelopes[2][1], b"")
    for row, response in zip(rows, responses, strict=True):
        require(row["method"] == "GET" and row["bodyless"] and not row["credentialHeaders"] and not row["markerHits"],
                "Unexpected request data or credential at the owned origin")
        require(row["responseSHA256"] == digest(response), "Wrong response bytes")
        if row["requestKind"] == "offer":
            require(row["queryKeys"] == sorted([*target, "installation"])
                    and row["installationSHA256"] == installation, "Offer exceeded the app-scoped query contract")
        else:
            require(row["queryKeys"] == sorted(tenant), "Artifact query exceeded the tenant scope")
    return {"runtime": target["runtime"], "installationSHA256": installation, "workspaceSHA256": digest(seed),
            "checkedMarkerLabels": sorted(fixture), "app": app, "sampledRequests": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("captures", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.packet, args.captures), indent=2))
