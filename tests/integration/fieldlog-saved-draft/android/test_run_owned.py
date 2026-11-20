"""Inert process-custody controls for the Android rebuild runner."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


RUNNER = Path(__file__).with_name("run-owned.py")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def inert_rebuild(output, scenario):
    # The control owns and reaps this separate session even when it withholds
    # evidence from the wrapper. UNKNOWN cases leave no live test resources.
    with subprocess.Popen(["/usr/bin/true"], start_new_session=True) as child:
        pgid = child.pid
        child.wait()
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        pass
    else:
        raise RuntimeError("Inert nested group did not close")

    work = output / "work"
    work.mkdir(parents=True)
    (work / "retained.txt").write_text("owned inert input", encoding="utf-8")
    if scenario == "no-terminal":
        return 0
    write_json(work / "prepared/.fieldlog-build/commands.json",
               [{"label": "create", "exitCode": 0, "ownedGroupAbsent": True, "pgid": pgid}])
    context = work / "tmp/mixer-command-receipts-inert"
    for name, command in (("swift", ["swift", "--version"]),
                          ("inspect", ["python3", "/inert/android-build.py", "inspect"])):
        write_json(context / f"command-{name}/receipt.json",
                   {"schema": "mixer.owned-command.2", "state": "TERMINAL",
                    "command": command, "exitCode": 0, "terminalCustody": True,
                    "directChildReaped": True, "ownedGroupAbsent": True,
                    "stdoutEOF": True, "stderrEOF": True, "descriptorsClosed": True})
    if scenario == "cli-hold":
        write_json(context / "command-swift/HOLD.json", {"state": "UNKNOWN"})

    for target, linker in (("android", ["android-linker-version"]),
                           ("host", ["apple-sdk", "apple-clang-path", "apple-linker-version"])):
        names = ["rust-sysroot", "rustc-version", "cargo-version", "llvm-nm-version",
                 *linker, "cargo-build", "archive-symbols"]
        rows = [{"name": name, "exit_code": 0, "problem": None} for name in names]
        directory = work / f"{target}-engine"
        if target == "host" and scenario == "missing-host":
            continue
        if target == "android" and scenario == "unknown-vm":
            rows[-1]["problem"] = "process group still present"
        write_json(directory / "receipt.json", {
            "schema_version": 1, "target_selector": target, "completed_utc": "1990-01-01T00:00:00+00:00",
            "source_revision": "5dea19db36610e312b51918b384364ba590b6ef8",
            "builder_sha256": "cbae2f5f02b1d8a468a331a71f31e9c4fad1957d16142db0d4e3d0ad2e6fa010",
            "commands": rows, "library": {"sha256": "a" * 64},
        })
        if target == "android" and scenario == "failed-vm":
            write_json(directory / "failure.json", {"incomplete": True})
    return 9 if scenario in {"known-failure", "missing-host"} else 0


class RunOwnedTest(unittest.TestCase):
    def run_control(self, scenario, expected_exit, expected_outer_exit, unresolved=()):
        with tempfile.TemporaryDirectory(prefix="fieldlog-custody-inert.") as scratch:
            receipt = Path(scratch) / "custody.json"
            output = Path(scratch) / "rebuild"
            result = subprocess.run(
                [sys.executable, "-B", str(RUNNER), str(receipt), "10", str(output),
                 "--", sys.executable, "-B", __file__, "--inert-rebuild", str(output), scenario],
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, expected_exit, result.stderr)
            record = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(record["exit"], expected_outer_exit)
            self.assertEqual(record["outerTerminalCustody"], "reaped_and_group_absent")
            self.assertEqual(record["terminalCustody"], "UNKNOWN" if unresolved else "TERMINAL")
            nested = record["nestedCustody"]
            self.assertEqual({key for key, row in nested.items() if row["state"] == "UNKNOWN"}, set(unresolved))
            for key in unresolved:
                self.assertTrue(nested[key]["reason"])
            if unresolved:
                self.assertIn("UNKNOWN custody", result.stderr)
            else:
                self.assertEqual(nested["androidVM"]["verifiedCommandGroups"], 7)
                self.assertEqual(nested["hostVM"]["verifiedCommandGroups"], 9)
            self.assertEqual((output / "work/retained.txt").read_text(encoding="utf-8"), "owned inert input")

    def test_all_terminal(self):
        self.run_control("known", 0, 0)

    def test_terminal_propagates_recipe_failure(self):
        self.run_control("known-failure", 9, 9)

    def test_unresolved_vm_after_successful_outer_exit(self):
        self.run_control("unknown-vm", 74, 0, ("androidVM",))

    def test_failure_marker_overrides_vm_completion(self):
        self.run_control("failed-vm", 74, 0, ("androidVM",))

    def test_hold_overrides_mixer_create_completion(self):
        self.run_control("cli-hold", 74, 0, ("mixerCreateTools",))

    def test_missing_vm_after_failed_outer_exit(self):
        self.run_control("missing-host", 74, 9, ("hostVM",))

    def test_no_terminal_evidence_after_successful_outer_exit(self):
        self.run_control("no-terminal", 74, 0, ("preparedProject", "mixerCreateTools", "androidVM", "hostVM"))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--inert-rebuild"]:
        sys.exit(inert_rebuild(Path(sys.argv[2]), sys.argv[3]))
    unittest.main()
