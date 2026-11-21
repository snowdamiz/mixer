"""Exercise refusal and publication without building a guest or VM."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


spec = spec_from_file_location("growth", Path(__file__).with_name("run.py"))
growth = module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(growth)
NO_RESULT = 4294967295


def scenario(startup, fill, retry, drain):
    session = [startup, fill, retry, drain, dict(closeStatus=0, retiredStartupStatus=3)]
    reopen = dict(sameRegistrySlot=True, newGeneration=True, retiredAfterReopenStatus=3,
                  identicalFreshFrame=True)
    rows = [dict(guestUiV1ValidationStatus=0), *session, reopen, *session]
    return "".join(json.dumps(row) + "\n" for row in rows)


def exact_frames():
    fields = ("phase", "pages", "fuel", "hostCalls", "enomem", "fillAttempts", "fillResult",
              "retryResult", "live", "checkedBeforeRelease", "survivorsChecked",
              "replacementChecked", "sameAddress", "freed", "growthAttempt", "growthCanaries", "highestBlockEnd")
    return [
        dict(zip(fields, values, strict=True)) for values in (
            (0, 1, 36, 0, 48, 0, NO_RESULT, NO_RESULT, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            (1, 2, 20233, 0, 48, 26, 48, NO_RESULT, 25, 0, 0, 0, 0, 0, 10, 9, 128320),
            (2, 2, 10950, 0, 48, 26, 48, 0, 25, 25, 24, 1, 1, 1, 10, 9, 128320),
            (3, 2, 12527, 0, 48, 26, 48, 0, 0, 25, 24, 1, 1, 26, 10, 9, 128320),
        )
    ]


class RunnerControls(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory(prefix="growth-inert-", dir=SCRATCH_PARENT)
        self.addCleanup(directory.cleanup)
        self.scratch = Path(directory.name) / "scratch"
        self.output = Path(directory.name) / "receipt.json"
        self.errors = io.StringIO()
        self.addCleanup(os.chdir, Path.cwd())

    def invoke(self):
        argv = ["run.py", "--checkout", str(CHECKOUT), "--scratch", str(self.scratch),
                "--output", str(self.output)]
        with patch.object(sys, "argv", argv), patch.object(growth.resource, "setrlimit"), \
                redirect_stderr(self.errors), redirect_stdout(io.StringIO()):
            return growth.main()

    def observe(self, stdout, stderr="", exit_code=0):
        def inert_campaign(_pinned, _output, run, receipt, *_):
            command = (
                f"import sys; sys.stdout.write({stdout!r}); sys.stderr.write({stderr!r}); "
                f"raise SystemExit({exit_code})"
            )
            own_command = run.command

            def invoke_host(label, _host, _wasm, *, bound):
                return own_command(label, sys.executable, "-I", "-c", command, bound=bound)

            with patch.object(run, "command", new=invoke_host):
                growth.observe_growth(run, "unused-host", "unused-wasm", receipt)

        with patch.object(growth, "campaign", side_effect=inert_campaign):
            code = self.invoke()
        self.assertFalse(self.scratch.exists())
        self.assertTrue(self.output.is_file(), self.errors.getvalue())
        receipt = json.loads(self.output.read_text())
        self.assertEqual(receipt["custody"]["reapedWithGroupAbsent"], 2)
        self.assertIsNone(receipt["custody"]["unknown"])
        return code, receipt

    def reject(self, frames):
        stdout = scenario(*frames)
        code, receipt = self.observe(stdout)
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "growth_observation_mismatch")
        self.assertEqual(receipt["growthObservedStdout"], stdout)
        self.assertTrue(receipt["firstFailure"])

    def test_exact_growth(self):
        stdout = scenario(*exact_frames())
        code, receipt = self.observe(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "observed_growth_at_cap_with_recovery")
        self.assertEqual(len(receipt["growthObservations"]), 12)

    def test_repeatable_different_address(self):
        frames = exact_frames()
        for frame in frames[2:]:
            frame["sameAddress"] = 0
        self.reject(frames)

    def test_repeatable_growth_on_second_allocation(self):
        frames = exact_frames()
        for frame in frames[1:]:
            frame.update(growthAttempt=2, growthCanaries=1)
        self.reject(frames)

    def test_repeatable_growth_on_failed_26th_allocation(self):
        frames = exact_frames()
        for frame in frames[1:]:
            frame.update(growthAttempt=26, growthCanaries=25)
        self.reject(frames)

    def test_repeatable_wrong_canary_count(self):
        frames = exact_frames()
        for frame in frames[1:]:
            frame.update(growthCanaries=8)
        self.reject(frames)

    def test_repeatable_wrong_enomem_attempt(self):
        frames = exact_frames()
        for frame in frames[1:]:
            frame.update(fillAttempts=25)
        frames[1].update(live=24)
        frames[2].update(live=24, checkedBeforeRelease=24, survivorsChecked=23)
        frames[3].update(checkedBeforeRelease=24, survivorsChecked=23, freed=25)
        self.reject(frames)

    def test_repeatable_no_growth(self):
        frames = exact_frames()
        for frame in frames[1:]:
            frame.update(pages=1, fillAttempts=10, growthAttempt=0, growthCanaries=0, highestBlockEnd=62784)
        frames[1].update(live=9)
        frames[2].update(live=9, checkedBeforeRelease=9, survivorsChecked=8)
        frames[3].update(checkedBeforeRelease=9, survivorsChecked=8, freed=10)
        self.reject(frames)

    def test_guest_ui_validation_refusal(self):
        stderr = "Guest UI V1 validation: inert control\n"
        code, receipt = self.observe("", stderr, 1)
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "guest_ui_v1_validation_refused")
        self.assertEqual(receipt["growthFailureOutput"], {"stdout": "", "stderr": stderr})
        self.assertIn("growth-ui-run exit 1", receipt["firstFailure"])

    def assert_preflight_refusal(self, evidence):
        with patch.object(growth, "load_helpers") as loader:
            self.assertEqual(self.invoke(), 1)
        loader.assert_not_called()
        refusal = json.loads(self.errors.getvalue())
        self.assertEqual(refusal["status"], "preflight_refused")
        self.assertIn(evidence, refusal["firstFailure"])
        self.assertEqual(refusal["reapedWithGroupAbsent"], 1)
        self.assertIsNone(refusal["unknown"])
        self.assertFalse(self.scratch.exists())
        self.assertFalse(self.output.exists())

    def test_head_mismatch_precedes_helper_loading(self):
        with patch.dict(growth.PIN, commit="0" * 40), patch.object(growth, "verified_inputs") as verify:
            self.assert_preflight_refusal("commit differs from pin")
        verify.assert_not_called()

    def test_transitive_helper_mismatch_precedes_helper_loading(self):
        original = Path.read_bytes

        def read_bytes(path):
            data = original(path)
            if path == CHECKOUT / "compiler/qualification_support.py":
                return data.replace(b"Bounded", b"Changed", 1)
            return data

        with patch.object(Path, "read_bytes", read_bytes):
            self.assert_preflight_refusal("source bytes differ: compiler/qualification_support.py")

    def test_baseline_helper_mismatch_precedes_helper_loading(self):
        original = Path.read_bytes

        def read_bytes(path):
            data = original(path)
            if path == CHECKOUT / growth.BASELINE / "run.py":
                return data.replace(b"Replay", b"Change", 1)
            return data

        with patch.object(Path, "read_bytes", read_bytes):
            self.assert_preflight_refusal(f"source bytes differ: {growth.BASELINE}/run.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--scratch-parent", required=True, type=Path)
    args, unittest_args = parser.parse_known_args()
    CHECKOUT = args.checkout.resolve(strict=True)
    SCRATCH_PARENT = args.scratch_parent.resolve(strict=True)
    unittest.main(argv=[sys.argv[0], *unittest_args])
