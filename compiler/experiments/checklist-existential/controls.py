"""Inert controls for the exact checklist replay."""

import contextlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("checklist_replay", Path(__file__).with_name("replay.py"))
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)


class ReplayControls(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="mixer-checklist-controls-", dir=replay.SCRATCH_ROOT)
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.producer = replay.verify_original()[1]

    def campaign(self):
        scratch = self.root / "owner"
        scratch.mkdir()
        receipt = self.enterContext(
            replay.Receipt(self.root / "outer.json", {"commands": [], "cleanup": {"unknown": None}}))
        campaign = replay.Campaign(scratch, receipt, self.producer, self.root)
        return campaign, receipt

    def test_embedded_refusal_matches_source_location_kind_type_and_artifacts(self):
        swift = self.root / "existential-probe/ChecklistFormatter.swift"
        line = f"{swift}:47:32: {replay.EMBEDDED_ERROR}"
        observation = dict(compileExit=1, originalStderr=line, linkInvoked=False,
                           objectExistedBefore=False, wasmExistedBefore=False,
                           objectExistsAfter=False, wasmExistsAfter=False)
        replay.check_embedded_refusal(swift, observation)
        for changes in (
            dict(originalStderr=f"{swift}:47:32: error: unrelated failure"),
            dict(originalStderr=line.replace(":47:32:", ":47:31:")),
            dict(originalStderr=line.replace(str(swift), "/other/ChecklistFormatter.swift")),
            dict(originalStderr=line.replace("ChecklistFormatter'", "OtherFormatter'")),
            dict(originalStderr=line.replace("#EmbeddedRestrictions", "#OtherRestriction")),
            dict(originalStderr=f"unrelated note mentioning {line}"),
            dict(compileExit=0), dict(compileExit=2), dict(linkInvoked=True),
            dict(objectExistsAfter=True), dict(wasmExistsAfter=True),
            dict(objectExistedBefore=True), dict(wasmExistedBefore=True),
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replay.check_embedded_refusal(swift, observation | changes)

    def test_owned_cwd_excludes_actual_cargo_caller_configuration(self):
        campaign, receipt = self.campaign()
        cargo = replay.RUST / "cargo"
        replay.check_identity(cargo, self.producer["tools"]["cargo"], executable=True)
        manifest = campaign.scratch / "Cargo.toml"
        manifest.write_text('[package]\nname = "inert"\nversion = "0.1.0"\nedition = "2021"\n')
        (campaign.scratch / "src").mkdir()
        (campaign.scratch / "src/lib.rs").touch()
        (campaign.scratch / "Cargo.lock").write_text('version = 4\n\n[[package]]\nname = "inert"\nversion = "0.1.0"\n')
        caller = self.root / "caller"
        config = caller / ".cargo/config.toml"
        config.parent.mkdir(parents=True)
        config.write_text("deliberately invalid Cargo TOML\n")
        arguments = (cargo, "metadata", "--offline", "--locked", "--no-deps",
                     "--format-version=1", "--manifest-path", manifest)
        with contextlib.chdir(caller):
            with self.assertRaisesRegex(ValueError, "ambient Cargo configuration"):
                replay.check_cargo_ancestry(caller)
            # Run the inherited configuration control by choosing the caller as the owned cwd.
            prior = replay.Campaign(caller, receipt, self.producer, self.root)
            _, stderr, status = prior.run("ambient-control", *arguments, exits=(101,))
            self.assertEqual(status, 101)
            self.assertIn(str(config), stderr)
        with contextlib.chdir(caller):
            replay.check_cargo_ancestry(campaign.scratch)
            output, _, code = campaign.run("isolated-control", *arguments)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["packages"][0]["name"], "inert")
        self.assertTrue(all(row["custody"] == "direct-child-reaped/group-absent"
                            for row in receipt.data["commands"]))

    def test_wrong_fetched_commit_stops_before_local_checkout(self):
        campaign, _ = self.campaign()
        with patch.object(campaign, "run", side_effect=[("", "", 0), ("", "", 0), ("f" * 40 + "\n", "", 0)]) as run:
            with self.assertRaisesRegex(ValueError, "remote did not deliver"):
                campaign.materialize_source()
        self.assertEqual([entry.args[0] for entry in run.call_args_list],
                         ["init-isolated-worktree", "fetch-published-pin", "verify-published-pin"])
        self.assertEqual(run.call_args_list[1].args[-2:], (replay.PUBLIC, replay.PIN))

    def test_executable_hash_drift_stops_before_first_launch(self):
        campaign, _ = self.campaign()
        self.producer["tools"]["swift"]["sha256"] = "0" * 64
        with patch.object(campaign, "run") as run:
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                campaign.verify_sdk_and_tools()
        run.assert_not_called()

    def test_wrong_sdk_selection_stops_before_tool_version_launches(self):
        campaign, _ = self.campaign()
        with patch.object(campaign, "run", return_value=("/wrong/SDK\n", "", 0)) as run:
            with self.assertRaisesRegex(ValueError, "xcrun selected a different SDK"):
                campaign.verify_sdk_and_tools()
        run.assert_called_once_with("macos-sdk", replay.XCRUN, "--no-cache", "--sdk", "macosx", "--show-sdk-path")

    def test_occupied_receipt_cannot_be_clobbered_or_launch_a_command(self):
        path = self.root / "receipt.json"
        path.write_text("existing evidence")
        with patch.object(replay.os, "posix_spawn") as spawn, self.assertRaises(FileExistsError):
            replay.replay(path, self.root)
        self.assertEqual(path.read_text(), "existing evidence")
        self.assertEqual(list(self.root.iterdir()), [path])
        spawn.assert_not_called()

    def test_abrupt_interruption_leaves_durable_prelaunch_unknown(self):
        campaign, receipt = self.campaign()
        nested_receipt = self.root / "interrupted.json"
        campaign.run("inert-interrupt", sys.executable, "-I", "-B", Path(__file__).resolve(),
                     "--interrupt-prelaunch", self.root, nested_receipt, exits=(73,))
        self.assertEqual(receipt.data["commands"][0]["custody"], "direct-child-reaped/group-absent")
        persisted = json.loads(nested_receipt.read_text())
        journal = nested_receipt.with_suffix(".json.journal")
        self.assertEqual(json.loads(journal.read_text().splitlines()[-1]), persisted)
        self.assertEqual(persisted["status"], "running")
        self.assertEqual(persisted["cleanup"]["state"], "owned")
        self.assertFalse(persisted["cleanup"]["removed"])
        hold = persisted["cleanup"]["unknown"]
        self.assertEqual(hold, persisted["commands"][0])
        self.assertEqual((hold["label"], hold["stage"], hold["custody"]), ("intent", "prelaunch", "UNKNOWN"))
        self.assertEqual(hold["cwd"], persisted["cleanup"]["scratch"])
        self.assertNotIn("pidPgid", hold)


def interrupt_prelaunch(root, receipt):
    def execute(self):
        self.run("intent", "/usr/bin/false")

    # This branch never launches the named command. The outer test reaps this
    # interpreter and has exclusive ownership of the inert test scratch.
    with patch.object(replay, "SCRATCH_ROOT", root), patch.object(replay.Campaign, "execute", execute), \
            patch.object(replay.os, "posix_spawn", side_effect=lambda *args, **kwargs: os._exit(73)):
        replay.replay(receipt, root)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--interrupt-prelaunch"]:
        interrupt_prelaunch(*map(Path, sys.argv[2:]))
    else:
        unittest.main(verbosity=2)
