#!/usr/bin/env python3
"""Inert controls for the localized verifier and a freshly staged packet."""

import base64
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys
import tempfile
from uuid import UUID

import identity_binding as identity

HERE = Path(__file__).resolve().parent
spec = spec_from_file_location("readback", HERE / "verify-readback.py")
readback = module_from_spec(spec)
spec.loader.exec_module(readback)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


def encoded(value):
    return base64.b64encode(json.dumps(value).encode()).decode()


def uid(number):
    return str(UUID(int=number)).upper()


def refuse(check, message):
    try:
        check()
    except ValueError as error:
        if message in str(error):
            return str(error)
        raise
    raise RuntimeError("Accepted a deliberately invalid input: " + message)


def make_evidence(root):
    fixture, evidence = root / "fixture", root / "evidence"
    owned = UUID(uid(1))
    installation = uid(2).lower()
    runtime = "1" * 64
    folder = "FieldLogUITest-" + uid(3).lower()
    work = evidence / folder
    project = {"id": uid(5), "title": "Checklist workshop"}
    before = {"id": uid(6), "projectID": uid(5), "title": readback.TITLE, "responsible": "Night shift",
              "position": 0, "completed": False, "updatedAt": 100}
    saved = before | {"completed": True, "updatedAt": 200}
    outbox_kinds = ["projectCreated", "taskSaved", "taskSaved"]
    outbox = [{"id": uid(7 + i), "kind": kind, "recordID": target, "revision": i + 1}
              for i, (kind, target) in enumerate(zip(outbox_kinds, [uid(5), uid(6), uid(6)]))]
    workspace = {"id": uid(4), "revision": 3, "projects": [project], "tasks": [saved], "outbox": outbox}
    write(work / "workspace.json", workspace)
    before_sha = "2" * 64
    saved_sha = identity.digest(work / "workspace.json")
    signing = {"runtime": runtime, "artifactDigests": {"baseline": "3" * 64, "replacement": "4" * 64}}
    write(fixture / "signing.json", signing)
    baseline_id, reviewed_id = ("5" * 64, "6" * 64)
    recovery = work / "signed-checklist/recovery"
    recovery.mkdir(parents=True)
    candidates = {}
    for seq, (phase, variant, candidate) in enumerate(zip(
        readback.PHASES, ("baseline", "reviewed"), (baseline_id, reviewed_id)
    ), start=1):
        source = fixture / phase
        payload = ("inert-" + phase).encode()
        payload_sha = readback.sha256(payload).hexdigest()
        artifact = signing["artifactDigests"][phase]
        assignment = {"assignment": {"sequence": seq, "artifact_sha256": artifact}, "signature": "inert"}
        manifest = {"manifest": {"release_id": "fieldlog-localized-" + variant,
                                "payload_sha256": payload_sha}, "signature": "inert"}
        write(source / "assignment.json", assignment)
        write(source / "signed-manifest.json", manifest)
        (source / "payload.wasm").write_bytes(payload)
        (recovery / (payload_sha + ".payload")).write_bytes(payload)
        candidates[candidate] = {"candidateID": candidate, "sequence": seq, "artifactSHA256": artifact,
                                 "payloadSHA256": payload_sha, "payloadBytes": len(payload),
                                 "signedManifest": encoded(manifest), "signedAssignment": encoded(assignment)}
    offers = readback.offers_for(fixture, signing)
    attachments = evidence / "attachments"
    records = []

    def attach(label, value):
        filename = f"item-{len(records)}"
        path = attachments / filename
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value))
        records.append({"suggestedHumanReadableName": label + "_exported", "exportedFileName": filename,
                        "deviceId": str(owned), "isAssociatedWithFailure": False})
        return path

    def health(candidate, launch):
        return {"candidateID": candidate, "launchID": uid(launch), "observationSeconds": 1,
                "completedMilestones": sorted(readback.HEALTH)}

    state = {"acceptedSequence": 2, "installation": installation, "fingerprint": runtime,
             "staged": None, "attempt": None, "pending": None, "candidates": candidates,
             "healthy": health(reviewed_id, 17), "previousHealthy": health(baseline_id, 13)}
    state_path = recovery / "state.json"
    write(state_path, state)
    attach("workspace-folder", folder)
    retirement = attach("retired-checklist", {"launch": uid(17).lower(), "rowID": "checklist-task-" + uid(6).lower(),
                                "label": readback.TITLE + ", completed"})
    checkpoints = {}
    for index, name in enumerate((*readback.BASELINE, *readback.REVIEWED)):
        first = index < 3
        committed = index >= 5
        artifact = offers["baseline" if first else "replacement"]
        launch = uid([11, 12, 13, 14, 14, 14, 15, 16, 17][index])
        process = [21, 22, 23, 23, 23, 23, 24, 25, 26][index]
        status, action = readback.LABELS[name]
        row = {"workspaceID": uid(4), "taskID": uid(6), "projectID": uid(5),
               "revision": 3 if committed else 2, "taskBytes": encoded(saved if committed else before),
               "workspaceSHA256": saved_sha if committed else before_sha, "outbox": 3 if committed else 2,
               "outboxKinds": outbox_kinds if committed else outbox_kinds[:2],
               "outboxIDs": [event["id"] for event in outbox[:3 if committed else 2]],
               "lastChangeRecord": uid(6), "lastChangeID": uid(9 if committed else 8),
               "launch": launch, "sequence": artifact["sequence"], "partialBytes": 0,
               "candidate": baseline_id if first else reviewed_id, "rightToLeft": not name.endswith("-ltr"),
               "textSize": "large" if index in (0, 1, 6, 7) else "accessibility5",
               "launchedArtifactSHA256": artifact["artifact"] if index in (0, 3, 4, 5) else None,
               "rotation": {"installation": installation, "process": process, "healthLaunch": launch,
                            "candidates": [baseline_id] if first else [baseline_id, reviewed_id],
                            "previous": None if first else baseline_id, "milestones": sorted(readback.HEALTH),
                            "deliveryError": "offline" if index == 8 else None,
                            "artifact": artifact["artifact"], "payload": artifact["payloadSHA256"]}}
        checkpoints[name] = attach(name, row)
        attach(name + "-status", status)
        for role, label in (("title", readback.TITLE), ("action", action)):
            attach(f"{name}-{role}-bounds", "viewport=(0, 0, 100, 100) element=(1, 1, 50, 20) label=" + label)
            attach(f"{name}-{role}", "inert screenshot placeholder")

    origin = {"completed": True, "installation": installation, "traffic": [], "phases": [],
              "closure": {"control": readback.CLOSED}}
    for phase in readback.PHASES:
        transition = {"phase": phase, "verified": True}
        if phase in offers:
            offer = offers[phase]
            transition["offers"] = [offer]
            for route in ("updates", "artifact", "updates", "updates"):
                origin["traffic"].append({"phase": phase, "route": route, "installation": installation,
                                          "responseSHA256": offer["responseDigests"][route],
                                          **{k: offer[k] for k in ("artifact", "sequence", "payloadSHA256")}})
        if phase == "offline":
            transition["closure"] = readback.CLOSED
        origin["phases"].append(transition)
        attach("origin-" + phase, transition)
    command = ["xcodebuild", "test-without-building", "-only-testing:FieldLogUITests/" + readback.SELECTOR,
               "-destination", f"platform=iOS Simulator,id={str(owned).upper()}"]
    write(attachments / "manifest.json", [{"testIdentifier": readback.SELECTOR + "()", "attachments": records}])
    write(evidence / "summary.json", dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0))
    write(evidence / "test-command.json", command)
    write(evidence / "origin/origin-receipt.json", origin)
    return evidence, fixture, owned, checkpoints, state_path, work / "workspace.json", retirement


def changed(path, change, verify, message):
    original = path.read_bytes()
    try:
        value = json.loads(original)
        change(value)
        write(path, value)
        return refuse(verify, message)
    finally:
        path.write_bytes(original)


def readback_controls(root):
    evidence, fixture, owned, checkpoints, state, workspace, retirement = make_evidence(root)
    def check():
        return readback.reconcile(evidence, fixture, owned)
    origin = evidence / "origin/origin-receipt.json"
    result = check()
    refusals = [
        changed(evidence / "test-command.json", lambda value: value.__setitem__(
            2, "-only-testing:FieldLogUITests/ChecklistJourney/testDevelopmentKeyRotation"), check, "dispatch selector"),
        changed(origin, lambda value: value["traffic"][0].update(responseSHA256="7" * 64), check, "Wrong served baseline updates"),
        changed(origin, lambda value: value["traffic"][1].update(responseSHA256="7" * 64), check, "Wrong served baseline artifact"),
        changed(origin, lambda value: value["traffic"].pop(5), check, "served artifact once in replacement"),
        changed(origin, lambda value: value["phases"][2]["closure"].update(threadJoined=False), check, "closure differ"),
        changed(origin, lambda value: value["closure"].clear(), check, "closure differ"),
        changed(checkpoints["awaiting-confirmation"], lambda value: value.update(revision=3), check, "workspace revision"),
        changed(workspace, lambda value: value["outbox"][-1].update(recordID=uid(90)), check, "appended taskSaved"),
        changed(state, lambda value: value["healthy"].update(launchID=uid(16)), check, "durable replacement health"),
        changed(state, lambda value: value.update(attempt={"launchID": uid(17)}), check, "after retirement"),
        changed(retirement, lambda value: value.update(rowID="checklist-task-" + uid(90)), check, "same completed task"),
    ]
    check()
    return {"acceptedInertRevision": result["revision"], "refused": refusals}


def identity_controls(packet, root):
    from prepare import ROTATION, ROTATION_SOURCE_DIGESTS, tracked_json
    actual = identity.verify(packet)
    fixture = root / "fake-signed-fixture"
    roots = fixture / "Installed/roots.json"
    write(roots, {"inert": True})
    preimage = packet / "templates/Installed/identity.json"
    installed = fixture / "Installed/identity.json"
    descriptor = readback.read(preimage)
    descriptor["build"]["trust_roots_sha256"] = identity.digest(roots)
    write(installed, descriptor)
    def check():
        return identity.verify(packet, fixture)
    check()
    inherited = tracked_json(f"{ROTATION}/templates/Installed/identity.json")["build"]
    refusals = [changed(installed, lambda value: value["build"].update({key: inherited[key]}),
                        check, "Signed fixture identity differs")
                for key in ROTATION_SOURCE_DIGESTS]
    refusals.append(changed(preimage, lambda value: value["build"].update(ROTATION_SOURCE_DIGESTS),
                            check, "Changed localized identity template"))
    source = packet.parent / "source/fieldlog/ios/FieldLog/SignedChecklist.swift"
    original = source.read_bytes()
    try:
        source.write_bytes(original + b"\n// inert source mutation\n")
        refusals.append(refuse(check, "does not match the staged source inventories"))
    finally:
        source.write_bytes(original)
    check()
    return {"sourceDigests": actual, "refused": refusals}


if __name__ == "__main__":
    packet = Path(sys.argv[1]).resolve(strict=True)
    with tempfile.TemporaryDirectory(dir=packet.parent) as temp:
        root = Path(temp)
        print(json.dumps({"readback": readback_controls(root), "identity": identity_controls(packet, root)}, indent=2))
