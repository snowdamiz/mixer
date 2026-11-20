#!/usr/bin/env python3
"""Check FieldLog iOS §22.2.4 disk snapshots against native observations."""

import argparse
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import UUID

BOUND_BUILD_SHA256 = "65713f8c3de099e946b8baa1221cbc3b5611d6587811078472b40ecfff6d08a9"
BUNDLE_ID = "dev.mixer.fieldlog"
SELECTOR = "FieldLogUITests/FieldLogSignedDraftTests/testSignedOptionalFieldSurvivesRollbackAndOrdinarySave"
READY = "Ready to save entry"
LINKED = "JPEG linked"
REQUIRED = "Follow-up required"
UNSET = "Follow-up unset"

# All signed phases use the sequences in the bound iOS product, including the
# corrected release at 2 and its later read-only rollback offer at 4.
SIGNED = {
    "baseline": (1, LINKED, None, None),
    "corrected": (2, LINKED, None, None),
    "optional": (3, LINKED, UNSET, REQUIRED),
    "rollback": (4, LINKED, None, None),
    "cold-reopen": (4, LINKED, None, None),
    "reupgrade": (5, LINKED, REQUIRED, REQUIRED),
    "second": (5, "No photo shown", UNSET, UNSET),
    "reselect-first": (5, LINKED, REQUIRED, REQUIRED),
}
PHASES = (
    "baseline", "corrected", "optional", "rollback", "offline-edit",
    "cold-reopen", "reupgrade", "unsaved", "second", "reselect-first",
)


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def read_file(path, limit):
    require(path.resolve(strict=True) == path and path.is_file(), f"Expected a regular file at {path}")
    with path.open("rb") as source:
        data = source.read(limit + 1)
    require(len(data) <= limit, f"Oversized evidence file {path}")
    return data


def read_json(path):
    return decode_json(read_file(path, 1_048_576))


def decode_json(data):
    def unique_object(pairs):
        result = dict(pairs)
        require(len(result) == len(pairs), "Duplicate JSON field")
        return result

    return json.loads(data, object_pairs_hook=unique_object)


@dataclass(frozen=True)
class Snapshot:
    bytes_digest: str
    jpeg_digest: str
    workspace: dict


def snapshot(directory, first, second):
    data = read_file(directory / "workspace.json", 1_048_576)
    state = decode_json(data)
    UUID(state["id"])
    require(type(state["revision"]) is int and 0 < state["revision"] < 2**64
            and type(state["schema"]) is int and state["schema"] == 1,
            "Invalid workspace schema or revision")
    require(len(state["drafts"]) == 2 and not state["entries"], "Expected two saved drafts and no entries")
    a, b = (draft(state, record_id) for record_id in (first, second))
    require(all(item.get("followUpRequired") is None or type(item["followUpRequired"]) is bool for item in (a, b)),
            "Invalid optional flag encoding")
    [project] = state["projects"]
    UUID(project["id"])
    require(a["projectID"] == b["projectID"] == project["id"] and a["title"] and b["title"]
            and a["title"] != b["title"], "Expected two distinct draft titles in the same project")
    [attachment] = state["attachments"]
    require(a["attachmentIDs"] == [attachment["id"]] and b["attachmentIDs"] == [],
            "Wrong draft owns the JPEG")
    filename = str(UUID(attachment["id"])) + ".jpg"
    require(attachment["filename"] == filename, "Wrong stored JPEG filename")
    photos = directory / "photos"
    require(photos.resolve(strict=True) == photos and {p.name for p in photos.iterdir()} == {filename},
            "Expected exactly the linked file in photos")
    jpeg = read_file(photos / filename, 6_291_456)
    require(len(jpeg) == attachment["byteCount"] and jpeg.startswith(b"\xff\xd8\xff") and jpeg.endswith(b"\xff\xd9"),
            "Invalid linked JPEG markers or size")
    return Snapshot(sha256(data).hexdigest(), sha256(jpeg).hexdigest(), state)


def draft(state, record_id):
    matches = [item for item in state["drafts"] if UUID(item["id"]) == record_id]
    require(len(matches) == 1, f"Expected one saved draft {record_id}")
    return matches[0]


def compare_navigation(previous, current, first, second):
    if previous.bytes_digest == current.bytes_digest:
        return
    expected = deepcopy(previous.workspace)
    target = current.workspace["restoration"].get("openDraftID")
    require(target is None or UUID(target) in {first, second}, "Navigation restored an unrelated draft")
    if "openDraftID" in current.workspace["restoration"]:
        expected["restoration"]["openDraftID"] = target
    else:
        expected["restoration"].pop("openDraftID", None)
    require(current.workspace["revision"] > expected["revision"], "Navigation changed bytes without a new revision")
    expected["revision"] = current.workspace["revision"]
    require(current.workspace == expected, "Inter-phase navigation changed workspace data")


def compare_action(phase, first, before, after, offline_note):
    if phase not in {"optional", "offline-edit"}:
        require(before.bytes_digest == after.bytes_digest, "Read-only action changed workspace bytes")
        return
    expected = deepcopy(before.workspace)
    target = draft(expected, first)
    if phase == "optional":
        require(target.get("followUpRequired") is None, "Expected the optional field to begin unset")
        target["followUpRequired"] = True
        expected["revision"] += 1
    else:
        edited = draft(after.workspace, first)
        require(target["note"] != offline_note and after.workspace["revision"] > expected["revision"],
                "Ordinary draft edit did not advance the saved note and revision")
        target.update(note=offline_note, updatedAt=edited["updatedAt"])
        expected["revision"] = after.workspace["revision"]
    require(after.workspace == expected, "Write changed the wrong draft or altered data outside the expected edit")


def bound_product(path):
    data = read_file(path, 65_536)
    require(sha256(data).hexdigest() == BOUND_BUILD_SHA256, "Wrong pinned iOS bound-build receipt")
    receipt = json.loads(data)
    require(receipt["product"]["bundleID"] == BUNDLE_ID, "Wrong bound bundle")
    product = receipt["simulatorRetry"]["product"]
    require(product["testProduct"]["selector"] == SELECTOR, "Wrong bound XCTest selector")
    return product


def signed_phase(name, observed, directory, product):
    sequence, photo, before, after = SIGNED[name]
    offer = product["signedAssignments"][sequence - 1]
    release = product["signedReleases"][offer["variant"]]
    state = read_json(directory / "recovery" / "state.json")
    health = state["healthy"]
    candidate = state["candidates"][health["candidateID"]]
    require(state["fingerprint"] == product["runtimeFingerprint"]
            and state["acceptedSequence"] == candidate["sequence"] == offer["sequence"] == sequence
            and candidate["artifactSHA256"] == offer["artifactSHA256"]
            and candidate["payloadSHA256"] == release["payload"]["sha256"]
            and candidate["payloadBytes"] == release["payload"]["bytes"], "Wrong durable iOS release selection")
    require(UUID(health["launchID"]) == UUID(observed["guestLaunchID"])
            and sorted(health["completedMilestones"]) == ["feature_started", "first_screen"]
            and all(state[key] is None for key in ("pending", "staged", "attempt")),
            "Native observation does not match settled guest health")
    require(observed["validation"] == READY and observed["photo"] == photo
            and observed["followUpBefore"] == before and observed["followUpAfter"] == after,
            "Wrong native validation, JPEG or follow-up observation")
    return state["installation"], health["candidateID"]


def verify(root, product):
    run = read_json(root / "journey.json")
    require(run["bundleID"] == BUNDLE_ID and run["appSHA256"] == product["appExecutable"]["sha256"],
            "Wrong installed iOS app identity")
    first, second, unsaved = (UUID(run[key]) for key in ("firstDraftID", "secondDraftID", "unsavedDraftID"))
    require(len({first, second, unsaved}) == 3, "Expected three distinct selection identities")
    note = run["offlineNote"]
    require(isinstance(note, str) and note.strip(), "Expected the recorded offline note")
    observations = run["phases"]
    require(set(observations) == set(PHASES), "Expected every checkpoint exactly once")
    previous = None
    installations = set()
    candidates = {}
    jpeg_digest = None
    checkpoints = {}
    for name in PHASES:
        try:
            observed = observations[name]
            selected = {"second": second, "unsaved": unsaved}.get(name, first)
            require(UUID(observed["selectedDraftID"]) == selected, "Native action targeted the wrong draft")
            directory = root / name
            before, after = (snapshot(directory / side, first, second) for side in ("before", "after"))
            if previous is None:
                jpeg_digest = before.jpeg_digest
            else:
                compare_navigation(previous, before, first, second)
            require(before.jpeg_digest == after.jpeg_digest == jpeg_digest, "Linked JPEG bytes changed")
            compare_action(name, first, before, after, note)
            require(draft(after.workspace, second).get("followUpRequired") is None, "Second draft inherited the first flag")
            if name == "unsaved":
                require(observed["refused"] is True, "Unsaved selection was accepted")
            if name in {"cold-reopen", "offline-edit"}:
                require(observed["originUnavailable"] is True and type(observed["appPID"]) is int
                        and observed["appPID"] > 0 and observed["visibleNote"] == note,
                        "Missing offline or edited-note observation")
            if name == "cold-reopen":
                require(observed["appPID"] != observations["offline-edit"]["appPID"], "Cold reopen reused the editing process")
            if name in SIGNED:
                installation, candidate = signed_phase(name, observed, directory, product)
                require(isinstance(installation, str) and installation, "Missing iOS installation identity")
                installations.add(installation)
                candidates[name] = candidate
            previous = after
            checkpoints[name] = {"revision": after.workspace["revision"], "workspaceSHA256": after.bytes_digest}
        except (AttributeError, KeyError, OSError, TypeError, ValueError) as error:
            raise ValueError(f"{name}: {error}") from error
    require(len(installations) == 1, "Signed phases used different iOS installations")
    require(candidates["cold-reopen"] == candidates["rollback"]
            and UUID(observations["cold-reopen"]["guestLaunchID"]) != UUID(observations["rollback"]["guestLaunchID"]),
            "Cold reopen did not restart the retained rollback candidate")
    require(candidates["reupgrade"] == candidates["second"] == candidates["reselect-first"],
            "Draft isolation was not observed under the same re-upgrade candidate")
    return {"status": "readback-matches", "workspaceID": previous.workspace["id"],
            "firstDraftID": str(first), "secondDraftID": str(second), "jpegSHA256": jpeg_digest,
            "checkpoints": checkpoints}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("bound_build_receipt", type=Path)
    args = parser.parse_args()
    try:
        report = verify(args.evidence.resolve(strict=True), bound_product(args.bound_build_receipt.resolve(strict=True)))
    except (AttributeError, KeyError, OSError, TypeError, ValueError) as error:
        print(f"FieldLog iOS readback failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
