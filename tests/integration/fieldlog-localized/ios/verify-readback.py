#!/usr/bin/env python3
"""Reconcile one localized XCTest with its signed traffic and retired workspace."""

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import re
from uuid import UUID

from identity_binding import digest, require

HERE = Path(__file__).resolve().parent
SELECTOR = "ChecklistJourney/testSignedLocalizedChecklist"
PHASES = ("baseline", "replacement", "offline", "complete")
BASELINE = ("baseline-ltr", "baseline-rtl", "baseline-large-rtl")
REVIEWED = ("reviewed-large-rtl", "awaiting-confirmation", "completed",
            "reviewed-rtl", "reviewed-ltr", "offline-cold-reopen")
SAVED = REVIEWED[2:]
HEALTH = {"feature_started", "first_screen"}
CLOSED = dict(socketClosed=True, threadJoined=True, connectionRefused=True)
TITLE = "فحص المضخة 07"
LABELS = {
    **dict.fromkeys(BASELINE, ("مفتوحة", "إكمال المهمة")),
    REVIEWED[0]: ("الفحص قيد التنفيذ", "وضع علامة مكتملة"),
    REVIEWED[1]: ("الفحص بانتظار التأكيد", "تأكيد إكمال الفحص"),
    **dict.fromkeys(SAVED, ("اكتمل الفحص", "إعادة فتح الفحص")),
}


def read(path):
    return json.loads(path.read_bytes())


def decoded(data):
    return json.loads(base64.b64decode(data, validate=True))


def uuid(value):
    return str(UUID(value))


def verify_dispatch(command, owned_udid):
    require(isinstance(command, list) and all(isinstance(arg, str) for arg in command) and
            command[:2] in (["xcodebuild", "test-without-building"], ["/usr/bin/xcodebuild", "test-without-building"]),
            "Expected the actual xcodebuild dispatch argv")
    require([arg for arg in command if arg.startswith("-only-testing")] == ["-only-testing:FieldLogUITests/" + SELECTOR]
            and not any(arg.startswith("-skip-testing") for arg in command), "Wrong localized dispatch selector")
    destination = f"platform=iOS Simulator,id={str(owned_udid).upper()}"
    require(command.count("-destination") == 1 and
            command[command.index("-destination") + 1:][:1] == [destination], "Wrong XCTest dispatch device")


def attachment_reader(evidence, owned_udid):
    summary = read(evidence / "summary.json")
    require([summary[k] for k in ("totalTestCount", "passedTests", "failedTests", "skippedTests")] == [1, 1, 0, 0],
            "Expected exactly one passing XCTest")
    attachments = evidence / "attachments"
    runs = read(attachments / "manifest.json")
    require(len(runs) == 1 and runs[0]["testIdentifier"].removesuffix("()") == SELECTOR, "Wrong XCTest selector")
    used = set()

    def attachment(label, *, screenshot=False):
        matches = [item for item in runs[0]["attachments"]
                   if item["suggestedHumanReadableName"].startswith(label + "_")]
        require(len(matches) == 1, f"Expected one attachment for {label}")
        item, = matches
        require(UUID(item["deviceId"]) == owned_udid and not item["isAssociatedWithFailure"],
                f"Wrong device or failed attachment for {label}")
        filename = item["exportedFileName"]
        require(Path(filename).name == filename and filename not in used, "Invalid or reused attachment filename")
        used.add(filename)
        path = attachments / filename
        limit = 64 * 1024 * 1024 if screenshot else 65_536
        require(not path.is_symlink() and path.is_file() and 0 < path.stat().st_size < limit,
                f"Missing or invalid attachment for {label}")
        if not screenshot:
            return path.read_text().strip()

    return attachment


def offers_for(fixture, signing):
    offers = {}
    for phase, sequence, variant in (("baseline", 1, "baseline"), ("replacement", 2, "reviewed")):
        folder = fixture / phase
        artifact = signing["artifactDigests"][phase]
        payload = (folder / "payload.wasm").read_bytes()
        assignment = read(folder / "assignment.json")
        manifest = read(folder / "signed-manifest.json")
        payload_sha = sha256(payload).hexdigest()
        require(re.fullmatch(r"[0-9a-f]{64}", artifact) and assignment["assignment"]["artifact_sha256"] == artifact
                and assignment["assignment"]["sequence"] == sequence
                and manifest["manifest"]["release_id"] == f"fieldlog-localized-{variant}"
                and manifest["manifest"]["payload_sha256"] == payload_sha,
                f"Wrong signed fixture material for {phase}")
        responses = {
            "updates": {"signed_assignment": assignment,
                        "artifact_url": f"/v3/artifacts/{artifact}?organization=mixer-local&project=fieldlog"},
            "artifact": {"signed_manifest": manifest, "payload": base64.b64encode(payload).decode()},
        }
        offers[phase] = {
            "platform": "ios", "artifact": artifact, "payloadSHA256": payload_sha, "sequence": sequence,
            "responseDigests": {route: sha256(json.dumps(body, separators=(",", ":")).encode()).hexdigest()
                                for route, body in responses.items()},
        }
    require(offers["baseline"]["artifact"] != offers["replacement"]["artifact"] and
            offers["baseline"]["payloadSHA256"] != offers["replacement"]["payloadSHA256"],
            "Expected two distinct localized releases")
    return offers


def verify_origin(origin, offers, install, attachment):
    expected = [
        {"phase": phase, "verified": True, **details}
        for phase, details in (
            ("baseline", {"offers": [offers["baseline"]]}),
            ("replacement", {"offers": [offers["replacement"]]}),
            ("offline", {"closure": CLOSED}),
            ("complete", {}),
        )
    ]
    require(origin["completed"] is True and origin["phases"] == expected and origin["installation"] == install and
            origin["closure"] == {"control": CLOSED}, "Origin phases or offline data / final control closure differ")
    for transition in expected:
        require(json.loads(attachment("origin-" + transition["phase"])) == transition,
                f"XCTest observed a different {transition['phase']} response")

    traffic = origin["traffic"]
    ordered = []
    for phase in PHASES[:2]:
        events = [event for event in traffic if event["phase"] == phase]
        routes = [event["route"] for event in events]
        require(routes.count("artifact") == 1, f"Expected a served artifact once in {phase}")
        transfer = routes.index("artifact")
        require(transfer >= 1 and routes[:transfer] == ["updates"] * transfer and
                len(routes) >= transfer + 3 and routes[transfer + 1:] == ["updates"] * (len(routes) - transfer - 1),
                f"Expected a served offer before the artifact and offer-only online relaunches in {phase}")
        offer = offers[phase]
        for event in events:
            require(event["installation"] == install and
                    all(event[k] == offer[k] for k in ("artifact", "payloadSHA256", "sequence")) and
                    event["responseSHA256"] == offer["responseDigests"][event["route"]],
                    f"Wrong served {phase} {event['route']} response")
        ordered.extend(events)
    require(traffic == ordered, "Offline or out-of-order signed traffic")


def verify_checkpoints(rows, offers, attachment):
    first, saved, cold = (rows[name] for name in (BASELINE[0], SAVED[0], SAVED[-1]))
    install = first["rotation"]["installation"]
    require(uuid(install) == install and uuid(first["workspaceID"]) != install, "Wrong installation identity")
    baseline, replacement = first["candidate"], saved["candidate"]
    require(all(re.fullmatch(r"[0-9a-f]{64}", item) for item in (baseline, replacement))
            and baseline != replacement, "Expected distinct recovery candidates")
    initial_kinds = ["projectCreated", "taskSaved"]
    baseline_ids = first["outboxIDs"]
    for name, row in rows.items():
        after_save = name in SAVED
        old_release = name in BASELINE
        reference = saved if after_save else first
        offer = offers["baseline" if old_release else "replacement"]
        local = row["rotation"]
        for key in ("workspaceID", "taskID", "projectID", "workspaceSHA256", "taskBytes", "outboxIDs",
                    "lastChangeID", "lastChangeRecord"):
            require(row[key] == reference[key], f"Unexpected committed {key} in {name}")
        uuid(row["launch"])
        require(re.fullmatch(r"[0-9a-f]{64}", row["workspaceSHA256"]) and
                row["lastChangeRecord"] == first["taskID"] and row["lastChangeID"] == row["outboxIDs"][-1] and
                row["revision"] == (3 if after_save else 2) and row["outbox"] == len(row["outboxIDs"]) ==
                (3 if after_save else 2) and len(set(map(uuid, row["outboxIDs"]))) == row["outbox"] and
                row["outboxKinds"] == (initial_kinds + ["taskSaved"] if after_save else initial_kinds),
                f"Wrong workspace revision or outbox in {name}")
        require(row["rightToLeft"] is (not name.endswith("-ltr")) and
                row["textSize"] == ("large" if name in (BASELINE[0], BASELINE[1], *REVIEWED[3:5]) else "accessibility5"),
                f"Wrong sheet layout in {name}")
        require(row["candidate"] == (baseline if old_release else replacement) and row["sequence"] == offer["sequence"] and
                local["candidates"] == ([baseline] if old_release else sorted([baseline, replacement])) and
                local.get("previous") == (None if old_release else baseline) and local["installation"] == install and
                type(local["process"]) is int and local["process"] > 0 and local["healthLaunch"] == row["launch"] and
                sorted(local["milestones"]) == sorted(HEALTH) and local["artifact"] == offer["artifact"] and
                local["payload"] == offer["payloadSHA256"] and
                local.get("deliveryError") == ("offline" if name == SAVED[-1] else None) and row["partialBytes"] == 0 and
                row.get("launchedArtifactSHA256") == (
                    offer["artifact"] if name in (BASELINE[0], *REVIEWED[:3]) else None
                ), f"Wrong release, health or spool in {name}")
        status, action = LABELS[name]
        require(attachment(name + "-status") == status, f"Wrong {name} guest status")
        for kind, label in (("title", TITLE), ("action", action)):
            expect = attachment(f"{name}-{kind}-bounds")
            require(expect.startswith("viewport=") and " element=" in expect and expect.endswith(" label=" + label),
                    f"Wrong {name} {kind} bounds attachment")
            attachment(f"{name}-{kind}", screenshot=True)

    require(saved["outboxIDs"][:-1] == baseline_ids and
            saved["workspaceSHA256"] != first["workspaceSHA256"], "Expected one new save and new committed bytes")
    before, after = decoded(first["taskBytes"]), decoded(saved["taskBytes"])
    require(before["id"] == first["taskID"] and before["projectID"] == first["projectID"] and
            before["title"] == TITLE and before["responsible"] == "Night shift" and before["position"] == 0 and
            before["completed"] is False and after["completed"] is True and
            type(before["updatedAt"]) in (int, float) and type(after["updatedAt"]) in (int, float) and
            after["updatedAt"] >= before["updatedAt"] and
            after == before | {"completed": True, "updatedAt": after["updatedAt"]},
            "Completion changed unexpected task fields")
    uuid(first["taskID"])
    uuid(first["projectID"])
    starts = [rows[name] for name in (*BASELINE, REVIEWED[0], *REVIEWED[3:])]
    cold_starts = [rows[name] for name in (*BASELINE, *REVIEWED[3:])]
    previous_process = rows[BASELINE[-1]]["rotation"]["process"]
    updated = rows[REVIEWED[0]]
    require(len({uuid(row["launch"]) for row in starts}) == len(starts) and
            updated["rotation"]["process"] == previous_process and
            all(rows[name]["launch"] == updated["launch"] and rows[name]["rotation"]["process"] == previous_process
                for name in REVIEWED[1:3]) and
            all(a["rotation"]["process"] != b["rotation"]["process"] for a, b in zip(cold_starts, cold_starts[1:])),
            "Fresh processes or the same-process replacement, review and save were unobserved")
    require(json.loads(attachment("retired-checklist")) == {
        "launch": uuid(cold["launch"]), "rowID": "checklist-task-" + uuid(cold["taskID"]),
        "label": TITLE + ", completed",
    }, "Done did not return to the same completed task after cold reopen")
    return install


def verify_workspace(copy, first, cold):
    path = copy / "workspace.json"
    workspace = read(path)
    project, = workspace["projects"]
    task, = workspace["tasks"]
    outbox = workspace["outbox"]
    require(workspace["id"] == first["workspaceID"] and workspace["revision"] == cold["revision"] == 3 and
            project["title"] == "Checklist workshop" and project["id"] == first["projectID"] and
            task == decoded(cold["taskBytes"]) and task["completed"] is True and digest(path) == cold["workspaceSHA256"] and
            [event["id"] for event in outbox] == cold["outboxIDs"] and
            [event["kind"] for event in outbox] == ["projectCreated", "taskSaved", "taskSaved"] and
            [event["recordID"] for event in outbox] == [project["id"], task["id"], task["id"]] and
            [event["revision"] for event in outbox] == [1, 2, 3], "Copied workspace or appended taskSaved differs")
    return digest(path)


def verify_recovery(copy, fixture, signing, last_baseline, cold):
    checklist = copy / "signed-checklist"
    path = checklist / "recovery/state.json"
    state = read(path)
    require(state["acceptedSequence"] == 2 and state["installation"] == cold["rotation"]["installation"] and
            state["fingerprint"] == signing["runtime"] and
            all(state[key] is None for key in ("pending", "staged", "attempt")) and
            set(state["candidates"]) == {last_baseline["candidate"], cold["candidate"]} and
            not (checklist / "artifact.partial").exists() and not list(path.parent.glob("*.payload.part")),
            "Wrong durable recovery state after retirement")
    for phase, point, field in (("baseline", last_baseline, "previousHealthy"), ("replacement", cold, "healthy")):
        candidate = point["candidate"]
        health = state[field]
        require(health["candidateID"] == candidate and health["launchID"] == point["launch"] and
                sorted(health["completedMilestones"]) == sorted(HEALTH) and health["observationSeconds"] == 1,
                f"Wrong durable {phase} health")
        artifact = state["candidates"][candidate]
        folder = fixture / phase
        payload_sha = digest(folder / "payload.wasm")
        installed_payload = path.parent / (payload_sha + ".payload")
        require(artifact["candidateID"] == candidate and artifact["sequence"] == point["sequence"] and
                artifact["artifactSHA256"] == point["rotation"]["artifact"] == signing["artifactDigests"][phase] and
                artifact["payloadSHA256"] == point["rotation"]["payload"] == payload_sha and
                digest(installed_payload) == payload_sha and
                installed_payload.stat().st_size == artifact["payloadBytes"] == (folder / "payload.wasm").stat().st_size and
                decoded(artifact["signedManifest"]) == read(folder / "signed-manifest.json") and
                decoded(artifact["signedAssignment"]) == read(folder / "assignment.json"),
                f"Wrong durable {phase} signed release or payload")
    return digest(path)


def reconcile(evidence, fixture, owned_udid):
    signing = read(fixture / "signing.json")
    verify_dispatch(read(evidence / "test-command.json"), owned_udid)
    attachment = attachment_reader(evidence, owned_udid)
    folder = attachment("workspace-folder")
    require(re.fullmatch(r"FieldLogUITest-[0-9a-f-]{36}", folder), "Wrong synthetic workspace folder")
    isolation = uuid(folder.removeprefix("FieldLogUITest-"))
    rows = {name: json.loads(attachment(name)) for name in (*BASELINE, *REVIEWED)}
    offers = offers_for(fixture, signing)
    install = verify_checkpoints(rows, offers, attachment)
    first, cold = rows[BASELINE[0]], rows[SAVED[-1]]
    require(install != isolation and uuid(first["workspaceID"]) != isolation, "Workspace and installation must be isolated")
    verify_origin(read(evidence / "origin/origin-receipt.json"), offers, install, attachment)
    copy = evidence / folder
    workspace_sha = verify_workspace(copy, first, cold)
    state_sha = verify_recovery(copy, fixture, signing, rows[BASELINE[-1]], cold)
    return {"status": "localized-native-evidence-reconciled", "ownedUDID": str(owned_udid).upper(),
            "runtime": signing["runtime"], "installation": install, "sequence": 2, "revision": 3,
            "taskID": first["taskID"], "workspaceSHA256": workspace_sha, "stateSHA256": state_sha}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path,
                        help="contains test-command.json, summary.json, attachments, origin and workspace copy")
    parser.add_argument("owned_udid", type=UUID)
    args = parser.parse_args()
    try:
        result = reconcile(args.evidence.resolve(strict=True), HERE / "fixture", args.owned_udid)
    except (KeyError, TypeError, ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
