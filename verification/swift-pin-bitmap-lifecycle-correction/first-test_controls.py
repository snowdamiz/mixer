#!/usr/bin/env python3
"""Guarded source bindings and independent lifecycle charge arithmetic only."""
from offline_guard import install
install()

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
UPSTREAM = ROOT / "verification/swift-dense512-product-integration"
REL = "src/experimental_swift_reactor/lifecycle_tests.rs"


def row(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def closure(rows):
    return hashlib.sha256("".join(
        n + "\0" + rows[n]["sha256"] + "\n" for n in sorted(rows)
    ).encode()).hexdigest()


def load(name):
    return json.loads((HERE / name).read_text())


def region(text, name):
    start = text.index("fn " + name + "()")
    stop = text.find("\n#[test]", start)
    return text[start:] if stop == -1 else text[start:stop]


def cold(pin_charge, body_bytes, instructions):
    # The 108 non-pin credits and 13 resident-index credits are unchanged.
    return 108 + pin_charge + 2 * body_bytes + 3 * instructions + 13


def charge(used, amount, limit):
    # Mirrors only checked, non-replenishing scalar-meter semantics, not Rust execution.
    if used + amount > limit:
        return used, False
    return used + amount, True


def exact_boundary(limit):
    constructor = 29 + 64 + 1 + 512 + 192 + 512 * 8
    initialized, completed = charge(constructor, cold(5, 2, 1), limit)
    later, admitted = charge(initialized, 1, limit)
    return completed and initialized == limit and not admitted and later == initialized


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load("manifest.json")
        cls.bindings = load("baseline-bindings.json")
        cls.old = (HERE / "baseline/vm" / REL).read_text()
        cls.new = (HERE / "candidate/vm" / REL).read_text()
        cls.cache = (UPSTREAM / "candidate/vm/src/experimental_swift_reactor/cache.rs").read_text()
        cls.borrowed = (UPSTREAM / "candidate/vm/src/experimental/cache/borrowed.rs").read_text()

    def test_01_frozen_seals_and_every_member(self):
        for name, expected in self.bindings["frozenSeals"].items():
            path = ROOT / name
            self.assertEqual(row(path), expected)
            seal = json.loads(path.read_text())
            for member, binding in seal["files"].items():
                self.assertEqual(row(path.parent / member), {k: binding[k] for k in ("bytes", "sha256")})

    def test_02_baseline_and_prior_candidate_closures(self):
        m = self.manifest
        self.assertEqual(len(m["baselineFiles"]), 136)
        for name, expected in m["baselineFiles"].items():
            self.assertEqual(row(ROOT / "vm" / name), expected)
            prior = UPSTREAM / "candidate/vm" / name if name in m["overlayPaths"][:3] else ROOT / "vm" / name
            self.assertEqual(row(prior), m["priorCandidateFiles"][name])
        self.assertEqual(closure(m["baselineFiles"]), m["baselineTreeSHA256"])
        self.assertEqual(closure(m["priorCandidateFiles"]), m["priorCandidateTreeSHA256"])

    def test_03_fresh_candidate_closure_and_only_test_overlay(self):
        m = self.manifest
        self.assertEqual(m["newOverlayPaths"], [REL])
        self.assertEqual(len(m["overlayPaths"]), 4)
        self.assertEqual(set(m["candidateFiles"]), set(m["priorCandidateFiles"]))
        for name, expected in m["candidateFiles"].items():
            self.assertEqual(row(ROOT / m["materializationPaths"][name]), expected)
            if name != REL:
                self.assertEqual(expected, m["priorCandidateFiles"][name])
        self.assertEqual(closure(m["candidateFiles"]), m["candidateTreeSHA256"])
        self.assertNotEqual(m["candidateTreeSHA256"], m["priorCandidateTreeSHA256"])

    def test_04_actual_failure_is_preserved_and_source_bound(self):
        files = self.bindings["actualLocalOnlyFiles"]
        for name, expected in files.items():
            self.assertEqual(row(ROOT / name), expected)
        archive = next(expected for name, expected in files.items() if name.endswith("pin-bitmap.zip"))
        self.assertEqual(archive["sha256"], self.bindings["actualArtifact"]["sha256"])
        stdout = (ROOT / next(n for n in files if n.endswith("cargo-5.stdout"))).read_text()
        self.assertIn("left: 4894\n right: 4893", stdout)
        self.assertIn("actual operation did not complete", stdout)
        self.assertIn("465 passed; 2 failed; 0 ignored; 0 measured; 0 filtered out", stdout)
        actual = json.loads((ROOT / next(n for n in files if n.endswith("source-manifest.json"))).read_text())
        self.assertEqual(actual["candidateTreeSHA256"], self.manifest["priorCandidateTreeSHA256"])
        self.assertEqual(actual["files"], self.manifest["priorCandidateFiles"])

    def test_05_entire_original_workload_and_other_tests_unchanged(self):
        names = re.findall(r"#\[test\]\s*fn (\w+)", self.old)
        self.assertEqual(names, re.findall(r"#\[test\]\s*fn (\w+)", self.new))
        changed = {
            "swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage",
            "swift_lifecycle_sl14_later_work_cache_and_absolute_deadline_do_not_reset",
        }
        for name in names:
            if name not in changed:
                self.assertEqual(region(self.old, name), region(self.new, name))
        # The module encoder, 29 functions, guest bodies, helpers and hooks are identical.
        self.assertEqual(self.old[:self.old.index("#[test]")], self.new[:self.new.index("#[test]")])
        for name in changed:
            old, new = region(self.old, name), region(self.new, name)
            self.assertEqual(len(re.findall(r"\bassert(?:_eq)?!", old)), len(re.findall(r"\bassert(?:_eq)?!", new)))
            self.assertEqual(re.findall(r"Request::\w+", old), re.findall(r"Request::\w+", new))
            self.assertEqual(re.findall(r"\b(?:success|failed|retire)\(", old), re.findall(r"\b(?:success|failed|retire)\(", new))

    def test_06_constructor_and_selection_charge_mechanism(self):
        self.assertIn("self.control.work(1)?;\n        partial.free_pins = dense_allowed_pins(budget.active_pins);", self.cache)
        selection = self.cache[self.cache.index("    fn available_pin("):self.cache.index("    fn pin_published(")]
        self.assertIn("meter.work(3)?;", selection)
        self.assertIn("meter.work(2)?;", selection)
        self.assertLess(selection.index("meter.work(3)?;"), selection.index(".trailing_zeros()"))
        self.assertLess(selection.index("meter.work(2)?;"), selection.index("Ok(slot)"))
        self.assertIn("meter.work(1)?;\n            if record.nonce == 0 { return Ok(index); }", self.borrowed)
        self.assertIn("let pin_slot = M::available_pin", self.borrowed)
        self.assertIn("M::pin_published(&mut parts.scratch, pin_slot);", self.borrowed)

    def test_07_sl13_independent_delta_arithmetic(self):
        old_start = 29 + 64 + 512 + 192 + 512 * 8
        new_start = old_start + 1
        old_init = old_start + cold(1, 14, 6)
        new_init = new_start + cold(5, 14, 6)
        old_first = old_init + cold(1, 7, 3) + cold(2, 19, 9)
        new_first = new_init + cold(5, 7, 3) + cold(5, 19, 9)
        old_second = old_first + (1 + 1 + 6) + (1 + 2 + 6)
        new_second = new_first + 2 * (1 + 5 + 6)
        self.assertEqual([old_start, old_init, old_first, old_second], [4893, 5061, 5394, 5411])
        self.assertEqual([new_start, new_init, new_first, new_second], [4894, 5066, 5406, 5430])
        self.assertEqual([new_start-old_start, new_init-old_init, new_first-old_first, new_second-old_second], [1, 5, 12, 19])
        self.assertEqual([cold(5,14,6), cold(5,7,3), cold(5,19,9)], [172, 148, 192])
        fixture = region(self.new, "swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage")
        for value in ("5_066", "5_406", "5_430"):
            self.assertIn(value, fixture)
        self.assertIn("(1 + 5 + 6) + (1 + 5 + 6)", fixture)

    def test_08_sl14_exact_boundary_rejects_stale_and_slack_limits(self):
        self.assertEqual(cold(1, 2, 1), 129)
        self.assertEqual(cold(5, 2, 1), 133)
        self.assertEqual(4893 + cold(1, 2, 1), 5022)
        self.assertEqual(4894 + cold(5, 2, 1), 5027)
        self.assertFalse(charge(4894, 133, 5022)[1])
        self.assertTrue(exact_boundary(5027))
        for bad in (5022, 5026, 5028, 64_000_000):
            self.assertFalse(exact_boundary(bad))
        fixture = region(self.new, "swift_lifecycle_sl14_later_work_cache_and_absolute_deadline_do_not_reset")
        self.assertEqual(fixture.count("5_027"), 3)
        self.assertNotIn("5_022", fixture)
        self.assertIn("assert_eq!(f.at_failure.instructions, 1);", fixture)
        self.assertIn("Some(SwiftRunResource::CacheWork)", fixture)

    def test_09_cumulative_meter_no_refill_and_deadline_cases_preserved(self):
        used = 4894
        for amount, expected in ((172, 5066), (148+192, 5406), (24, 5430)):
            used, accepted = charge(used, amount, 64_000_000)
            self.assertTrue(accepted)
            self.assertEqual(used, expected)
        failed, accepted = charge(used, 1, used)
        self.assertFalse(accepted)
        self.assertEqual(failed, used)
        name = "swift_lifecycle_sl14_later_work_cache_and_absolute_deadline_do_not_reset"
        old, new = region(self.old, name), region(self.new, name)
        self.assertEqual(old[:old.index("    // Constructor")], new[:new.index("    // Constructor")])
        deadline = "    let prepared_deadline ="
        self.assertEqual(old[old.index(deadline):], new[new.index(deadline):])
        self.assertNotIn("test_replace_cache_work_limit", new)
        control = (ROOT / "vm/src/experimental_swift_reactor/control.rs").read_text()
        self.assertIn("used.checked_add(credits).filter(|next| *next <= limit)", control)
        self.assertIn("Work::Cache => self.cache_work = next", control)

    def test_10_all_17_defaults_and_runtime_envelope_byte_preserved(self):
        for name, expected in self.bindings["sourceDiagnosisInputs"].items():
            self.assertEqual(row(ROOT / name), expected)
        m = self.manifest
        for name in ("src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/lifecycle.rs", "src/experimental_swift_reactor/frame_operations.rs"):
            self.assertEqual(m["baselineFiles"][name], m["candidateFiles"][name])
        control = (ROOT / "vm/src/experimental_swift_reactor/control.rs").read_text()
        fields = control.split("pub struct SwiftRunBudget {", 1)[1].split("\n}", 1)[0]
        self.assertEqual(len(re.findall(r"pub \w+:", fields)), 17)
        for limit in ("cache_work: 64_000_000", "active_pins: 64", "frames: 64", "combined_bytes: 256 * MIB"):
            self.assertIn(limit, control)

    def test_11_original_host_cases_and_finite_caps_unchanged(self):
        plan = json.loads((UPSTREAM / "host-plan.json").read_text())
        commands = [plan["firstExecutable"], *plan["followupCommands"]]
        self.assertEqual(len(commands), 6)
        self.assertEqual([x["commandSeconds"] for x in commands], [300, 300, 180, 180, 600, 600])
        self.assertEqual(plan["firstExecutable"]["expectedFocusedMethods"], 7)
        self.assertEqual(plan["custody"]["maxWholeReactorAttempts"], 0)
        self.assertIs(plan["custody"]["retry"], False)
        self.assertIs(self.manifest["hostHarnessChanged"], False)
        self.assertIs(self.manifest["newDispatchSelected"], False)

    def test_12_guard_blocks_live_apis(self):
        import os
        import signal
        import socket
        import subprocess
        for call in (lambda: subprocess.Popen(["true"]), lambda: socket.socket(),
                     lambda: os.kill(1, 0), lambda: os.getpgid(1), lambda: os.waitpid(1, 0),
                     lambda: os.setsid(), lambda: signal.getsignal(signal.SIGTERM)):
            with self.assertRaisesRegex(AssertionError, "source-only correction"):
                call()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {
        "schema": 1, "scope": "guarded source closure and arithmetic controls; not actual Rust execution",
        "command": "python3 -B verification/swift-pin-bitmap-lifecycle-correction/test_controls.py",
        "pythonVersion": sys.version,
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "failed": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "guardInstalledBeforeImplementationImports": True,
        "realNestedProcessesSessionsGroupsSignalsWaitsSockets": 0,
        "actualRustRuns": 0, "nativeUICaptureRuns": 0,
        "candidateTreeSHA256": load("manifest.json")["candidateTreeSHA256"],
        "pending": ["Independent review", "Corrected actual Rust Debug and Release regressions", "Formatting and lint"],
    }
    (HERE / "pure-result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    sys.exit(not result.wasSuccessful())
