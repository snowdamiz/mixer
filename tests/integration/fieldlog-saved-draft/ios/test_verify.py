"""Host controls for the readback CLI using authored, non-native evidence."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import UUID, uuid4

from verify import BUNDLE_ID, PHASES, SIGNED, bound_product

PIN = "9c14c70b5a2b8bd8b99b2b632fd5e67a590375e5"
RECEIPT = "verification/receipts/fieldlog-ios-selected-draft-bound-app-20261119.json"
SCRIPT = Path(__file__).resolve().with_name("verify.py")
JPEG = b"\xff\xd8\xff\x00\xff\xd9"  # Marker-bearing byte control, not a decodable image.


def put(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, sort_keys=True))


class ReadbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = TemporaryDirectory(prefix="fieldlog-ios-readback-tests-")
        cls.addClassCleanup(scratch.cleanup)
        cls.root = Path(scratch.name).resolve()
        cls.receipt = cls.root / "bound-build.json"
        cls.receipt.write_bytes(subprocess.check_output(
            ["git", "show", f"{PIN}:{RECEIPT}"], cwd=SCRIPT.parent,
        ))
        cls.product = bound_product(cls.receipt)

    def setUp(self):
        scratch = TemporaryDirectory(dir=self.root)
        self.addCleanup(scratch.cleanup)
        self.evidence = Path(scratch.name)
        first, second, unsaved, project, attachment = [str(uuid4()).upper() for _ in range(5)]
        self.filename = str(UUID(attachment)) + ".jpg"
        a = {"id": first, "projectID": project, "title": "Pump A", "note": "Original",
             "attachmentIDs": [attachment], "updatedAt": 1}
        b = {"id": second, "projectID": project, "title": "Pump B", "note": "Unchanged",
             "attachmentIDs": [], "updatedAt": 1}
        state = {"schema": 1, "id": str(uuid4()), "revision": 3, "createdAt": 1,
                 "projects": [{"id": project}], "tasks": [], "entries": [], "drafts": [a, b],
                 "outbox": [{"id": str(uuid4()), "recordID": project, "kind": "projectCreated", "revision": 1}],
                 "restoration": {"selectedProjectID": project, "openDraftID": first},
                 "attachments": [{"id": attachment, "filename": self.filename, "byteCount": len(JPEG)}]}
        self.journey = {"bundleID": BUNDLE_ID, "appSHA256": self.product["appExecutable"]["sha256"],
                        "firstDraftID": first, "secondDraftID": second, "unsavedDraftID": unsaved,
                        "offlineNote": "Edited offline", "phases": {}}
        notes = self.journey["phases"]
        for name in PHASES:
            selected = {"second": second, "unsaved": unsaved}.get(name, first)
            if name in {"second", "reselect-first"}:
                state["restoration"]["openDraftID"] = selected
                state["revision"] += 2
            self.capture(name, "before", state)
            notes[name] = {"selectedDraftID": selected}
            if name == "optional":
                a["followUpRequired"] = True
                state["revision"] += 1
            if name == "offline-edit":
                a.update(note=self.journey["offlineNote"], updatedAt=2)
                state["revision"] += 2
            self.capture(name, "after", state)
            if name in {"offline-edit", "cold-reopen"}:
                notes[name].update(originUnavailable=True, visibleNote=self.journey["offlineNote"],
                                   appPID=1001 if name == "offline-edit" else 1002)
            if name == "unsaved":
                notes[name]["refused"] = True
            if name in SIGNED:
                self.recovery(name, notes[name])
        self.write_journey()

    def capture(self, phase, side, state):
        directory = self.evidence / phase / side
        put(directory / "workspace.json", state)
        (directory / "photos").mkdir()
        (directory / "photos" / self.filename).write_bytes(JPEG)

    def recovery(self, phase, observed):
        sequence, photo, before, after = SIGNED[phase]
        offer = self.product["signedAssignments"][sequence - 1]
        payload = self.product["signedReleases"][offer["variant"]]["payload"]
        candidate = f"{sequence:064x}"
        launch = str(uuid4())
        observed.update(validation="Ready to save entry", photo=photo, followUpBefore=before,
                        followUpAfter=after, guestLaunchID=launch)
        put(self.evidence / phase / "recovery" / "state.json", {
            "fingerprint": self.product["runtimeFingerprint"], "installation": "host-control",
            "acceptedSequence": sequence, "pending": None, "staged": None, "attempt": None,
            "healthy": {"candidateID": candidate, "launchID": launch,
                        "completedMilestones": ["first_screen", "feature_started"]},
            "candidates": {candidate: {"sequence": sequence, "artifactSHA256": offer["artifactSHA256"],
                                         "payloadSHA256": payload["sha256"], "payloadBytes": payload["bytes"]}},
        })

    def write_journey(self):
        put(self.evidence / "journey.json", self.journey)

    def run_cli(self):
        return subprocess.run([sys.executable, "-B", SCRIPT, self.evidence, self.receipt],
                              capture_output=True, text=True, timeout=5, check=False)

    def reject(self, reason):
        result = self.run_cli()
        self.assertEqual(result.returncode, 1, result)
        self.assertIn(reason, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_complete_readback(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(json.loads(result.stdout)["checkpoints"]), set(PHASES))

    def test_rollback_changes_even_workspace_encoding(self):
        path = self.evidence / "rollback" / "after" / "workspace.json"
        path.write_bytes(path.read_bytes() + b"\n")
        self.reject("rollback: Read-only action changed workspace bytes")

    def test_optional_write_targets_wrong_draft(self):
        path = self.evidence / "optional" / "after" / "workspace.json"
        state = json.loads(path.read_bytes())
        a, b = state["drafts"]
        b["followUpRequired"] = a.pop("followUpRequired")
        put(path, state)
        self.reject("optional: Write changed the wrong draft")

    def test_offline_edit_loses_optional_flag(self):
        path = self.evidence / "offline-edit" / "after" / "workspace.json"
        state = json.loads(path.read_bytes())
        state["drafts"][0].pop("followUpRequired")
        put(path, state)
        self.reject("offline-edit: Write changed the wrong draft")

    def test_cold_photo_is_replaced_with_same_length(self):
        path = self.evidence / "cold-reopen" / "after" / "photos" / self.filename
        path.write_bytes(JPEG.replace(b"\x00", b"\x01"))
        self.reject("cold-reopen: Linked JPEG bytes changed")

    def test_cold_reopen_reuses_process(self):
        phases = self.journey["phases"]
        phases["cold-reopen"]["appPID"] = phases["offline-edit"]["appPID"]
        self.write_journey()
        self.reject("cold-reopen: Cold reopen reused the editing process")

    def test_unsaved_selection_is_accepted(self):
        self.journey["phases"]["unsaved"]["refused"] = False
        self.write_journey()
        self.reject("unsaved: Unsaved selection was accepted")

    def test_second_reuses_first_selection(self):
        self.journey["phases"]["second"]["selectedDraftID"] = self.journey["firstDraftID"]
        self.write_journey()
        self.reject("second: Native action targeted the wrong draft")

    def test_second_renders_first_draft_flag(self):
        self.journey["phases"]["second"]["followUpAfter"] = "Follow-up required"
        self.write_journey()
        self.reject("second: Wrong native validation, JPEG or follow-up observation")

    def test_cold_reopen_uses_baseline_instead_of_rollback(self):
        baseline = self.evidence / "baseline" / "recovery" / "state.json"
        (self.evidence / "cold-reopen" / "recovery" / "state.json").write_bytes(baseline.read_bytes())
        self.reject("cold-reopen: Wrong durable iOS release selection")

    def test_rollback_flag_dropped_between_checkpoints(self):
        directory = self.evidence / "rollback"
        for side in ("before", "after"):
            path = directory / side / "workspace.json"
            state = deepcopy(json.loads(path.read_bytes()))
            state["revision"] += 1
            state["drafts"][0].pop("followUpRequired")
            put(path, state)
        self.reject("rollback: Inter-phase navigation changed workspace data")


if __name__ == "__main__":
    unittest.main()
