#!/usr/bin/env python3
"""Reconcile one root-owned XCTest dispatch and result with origin traffic and app state."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID

HERE = Path(__file__).resolve().parent
PHASES = ("baseline", "revoked-artifact", "revoked-assignment", "offline", "replacement")
HEALTH = {"feature_started", "first_screen"}
SELECTOR = "ChecklistJourney/testDevelopmentKeyRotation"
DISPATCH_SELECTOR = "FieldLogUITests/" + SELECTOR

def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)

def read(path):
    return json.loads(path.read_bytes())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_dispatch(command, owned_udid):
    require(isinstance(command, list) and all(isinstance(arg, str) for arg in command) and
            command[:2] in (["xcodebuild", "test-without-building"], ["/usr/bin/xcodebuild", "test-without-building"]),
            "Expected the actual xcodebuild dispatch argv")
    require([arg for arg in command if arg.startswith("-only-testing")] == ["-only-testing:" + DISPATCH_SELECTOR] and
            not any(arg.startswith("-skip-testing") for arg in command), "Wrong XCTest dispatch selector")
    destination = f"platform=iOS Simulator,id={str(owned_udid).upper()}"
    require(command.count("-destination") == 1 and
            command[command.index("-destination") + 1:][:1] == [destination], "Wrong XCTest dispatch device")

def verify_traffic(origin, fixture, artifact_digests, installation):
    phases = [phase for phase in PHASES if phase != "offline"]
    routes = ("updates", "artifact")
    traffic = origin["traffic"]
    require([(row["phase"], row["route"]) for row in traffic] ==
            [(phase, route) for phase in phases for route in routes],
            "Expected an offer and artifact download in every online phase")
    transitions = {row["phase"]: row for row in origin["phases"]}
    for phase, offset in zip(phases, range(0, len(traffic), len(routes))):
        folder = fixture / phase
        artifact = artifact_digests[phase]
        payload = (folder / "payload.wasm").read_bytes()
        payload_digest = hashlib.sha256(payload).hexdigest()
        sequence = 1 if phase == "baseline" else 2
        responses = {
            "updates": {"signed_assignment": read(folder / "assignment.json"),
                        "artifact_url": f"/v3/artifacts/{artifact}?organization=mixer-local&project=fieldlog"},
            "artifact": {"signed_manifest": read(folder / "signed-manifest.json"),
                         "payload": base64.b64encode(payload).decode()},
        }
        expected = {route: hashlib.sha256(json.dumps(body, separators=(",", ":")).encode()).hexdigest()
                    for route, body in responses.items()}
        metadata = {"artifact": artifact, "sequence": sequence, "payloadSHA256": payload_digest}
        require(transitions[phase]["offers"] == [
            {"platform": "ios", **metadata, "responseDigests": expected}
        ], f"Wrong fixture response digests for {phase}")
        for event in traffic[offset:offset + len(routes)]:
            require(event["installation"] == installation and
                    all(event[key] == value for key, value in metadata.items()) and
                    event.get("responseSHA256") == expected[event["route"]],
                    f"Incorrect signed {event['route']} response for {phase}")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path,
                        help="contains test-command.json, summary.json, attachments, origin and workspace copy")
    parser.add_argument("owned_udid", type=UUID)
    args = parser.parse_args()
    evidence = args.evidence.resolve(strict=True)
    fixture = HERE / "fixture"
    signing = read(fixture / "signing.json")
    verify_dispatch(read(evidence / "test-command.json"), args.owned_udid)
    summary = read(evidence / "summary.json")
    require([summary[k] for k in ("totalTestCount", "passedTests", "failedTests", "skippedTests")] == [1, 1, 0, 0],
            "Expected exactly one passing XCTest")
    attachments = evidence / "attachments"
    runs = read(attachments / "manifest.json")
    require(len(runs) == 1 and runs[0]["testIdentifier"].removesuffix("()") == SELECTOR, "Wrong XCTest selector")

    def attachment(label):
        matching = [a for a in runs[0]["attachments"] if a["suggestedHumanReadableName"].startswith(label + "_")]
        require(len(matching) == 1, f"Expected one attachment for {label}")
        item, = matching
        require(UUID(item["deviceId"]) == args.owned_udid and not item["isAssociatedWithFailure"], "Wrong device or failed attachment")
        filename = item["exportedFileName"]
        require(Path(filename).name == filename, "Invalid attachment filename")
        path = attachments / filename
        require(not path.is_symlink() and path.is_file() and path.stat().st_size < 65_536, "Invalid attachment file")
        return path.read_text().strip()

    folder = attachment("workspace-folder")
    require(re.fullmatch(r"FieldLogUITest-[0-9a-f-]{36}", folder), "Invalid synthetic workspace folder")
    isolation = str(UUID(folder.removeprefix("FieldLogUITest-")))
    rows = {phase: json.loads(attachment("rotation-" + phase)) for phase in PHASES}
    first, last = rows["baseline"], rows["replacement"]
    original, rotated = first["rotation"], last["rotation"]
    origin = read(evidence / "origin/origin-receipt.json")
    transitions = origin["phases"]
    require(origin["completed"] and [row["phase"] for row in transitions] == [*PHASES, "complete"] and
            set(origin["closure"]) == {"control", "data"} and
            all(all(proof.values()) for proof in origin["closure"].values()) and
            all(transitions[3]["closure"].values()), "Origin lifecycle was incomplete")

    install = original["installation"]
    require(str(UUID(install)) == install and install not in {isolation, first["workspaceID"].lower()} and
            install == origin["installation"], "Installation does not match the dedicated AppStorage and origin identity")
    expected_errors = {"revoked-artifact": "v3.signature.authority",
                       "revoked-assignment": "v3.signature.authority", "offline": "offline"}
    for phase, row in rows.items():
        details = row["rotation"]
        require(row["sequence"] == (2 if phase == "replacement" else 1) and row["partialBytes"] == 0,
                f"Incorrect high-water or partial spool in {phase}")
        for field in ("workspaceID", "taskID", "projectID", "workspaceSHA256", "revision", "outbox", "taskBytes", "lastChangeID"):
            require(row[field] == first[field], f"Workspace {field} changed in {phase}")
        require(details.get("deliveryError") == expected_errors.get(phase) and details["installation"] == install and
                details["healthLaunch"] == row["launch"] and len(details["milestones"]) == 2 and
                set(details["milestones"]) == HEALTH, f"Unexpected admission or health in {phase}")
        if phase != "replacement":
            require(row["candidate"] == first["candidate"] and details["candidates"] == [first["candidate"]] and
                    details.get("previous") is None and details["artifact"] == signing["artifactDigests"]["baseline"],
                    f"Baseline inventory changed in {phase}")
    require(len({row["launch"] for row in rows.values()}) == len(PHASES), "Launch identifiers were reused")
    require(all(rows[phase]["rotation"]["process"] == original["process"] for phase in PHASES[:3]) and
            rows["offline"]["rotation"]["process"] != original["process"] and
            rows["offline"]["rotation"]["process"] == rotated["process"], "Cold launch or same-process replacement was unobserved")
    require(last["candidate"] != first["candidate"] and rotated["previous"] == first["candidate"] and
            rotated["candidates"] == sorted([first["candidate"], last["candidate"]]) and
            rotated["artifact"] == last["launchedArtifactSHA256"] == signing["artifactDigests"]["replacement"],
            "Replacement inventory differs")

    verify_traffic(origin, fixture, signing["artifactDigests"], install)

    copy = evidence / folder
    workspace_file = copy / "workspace.json"
    workspace = read(workspace_file)
    state_file = copy / "signed-checklist/recovery/state.json"
    state = read(state_file)
    task, = workspace["tasks"]
    project, = workspace["projects"]
    require(workspace["id"] == first["workspaceID"] and sha(workspace_file) == first["workspaceSHA256"] and
            workspace["revision"] == first["revision"] == 2 and project["title"] == "Checklist workshop" and
            project["id"] == task["projectID"] == first["projectID"] and task["id"] == first["taskID"] and
            task == json.loads(base64.b64decode(first["taskBytes"], validate=True)) and
            task["title"] == "Inspect pump" and task["responsible"] == "Night shift" and task["completed"] is False and
            [row["kind"] for row in workspace["outbox"]] == ["projectCreated", "taskSaved"] and
            [row["recordID"] for row in workspace["outbox"]] == [project["id"], task["id"]], "Copied workspace differs")
    require(state["acceptedSequence"] == 2 and state["installation"] == install and
            state["fingerprint"] == signing["runtime"] and
            state["pending"] is None and state["staged"] is None and state["attempt"] is None and
            set(state["candidates"]) == {first["candidate"], last["candidate"]} and
            not (copy / "signed-checklist/artifact.partial").exists(), "Unexpected final durable recovery state")
    for phase, checkpoint, health_field in (("baseline", first, "previousHealthy"), ("replacement", last, "healthy")):
        record = state[health_field]
        candidate = checkpoint["candidate"]
        observed = rows["offline"] if phase == "baseline" else last
        require(record["candidateID"] == candidate and record["launchID"] == observed["launch"] and
                set(record["completedMilestones"]) == HEALTH and record["observationSeconds"] == 1,
                f"Stored {phase} health differs")
        artifact = state["candidates"][candidate]
        payload_hash = sha(fixture / phase / "payload.wasm")
        installed_payload = state_file.parent / (payload_hash + ".payload")
        require(sha(installed_payload) == payload_hash and installed_payload.stat().st_size == artifact["payloadBytes"],
                f"Stored {phase} payload bytes differ")
        require(artifact["artifactSHA256"] == signing["artifactDigests"][phase] and
                artifact["payloadSHA256"] == checkpoint["rotation"]["payload"] == sha(fixture / phase / "payload.wasm") and
                artifact["sequence"] == checkpoint["sequence"] and
                json.loads(base64.b64decode(artifact["signedManifest"], validate=True)) == read(fixture / phase / "signed-manifest.json") and
                json.loads(base64.b64decode(artifact["signedAssignment"], validate=True)) == read(fixture / phase / "assignment.json"),
                f"Stored {phase} signed bytes differ")
    print(json.dumps({"status": "native-evidence-reconciled", "ownedUDID": str(args.owned_udid).upper(),
                      "runtime": signing["runtime"], "installation": install, "sequence": 2,
                      "workspaceSHA256": sha(workspace_file), "stateSHA256": sha(state_file),
                      "baseline": first["candidate"], "replacement": last["candidate"]}, indent=2))

if __name__ == "__main__":
    main()
