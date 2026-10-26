#!/usr/bin/env python3
"""Offline structural/behavioral controls for a proposal, not runner acceptance.

Ruby/Psych parses YAML; no third-party Python packages or compiler are used.
Behavior probes substitute inert Python recorders in an owned temporary tree.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NEW_JOB = "swift-cache-state-fixture"
FIXTURE = "verification/swift-cache-state-ci"
PARSER = "require 'json'; require 'psych'; puts JSON.generate(Psych.safe_load(File.read(ARGV[0]), aliases: false))"


def read_yaml(path: Path) -> dict:
    result = subprocess.run(
        ["ruby", "-e", PARSER, str(path)], check=True,
        capture_output=True, text=True, timeout=10,
    )
    return json.loads(result.stdout)


class WorkflowProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline_bytes = (HERE / "baseline.verify.yml").read_bytes()
        cls.proposal_bytes = (HERE / "proposed.verify.yml").read_bytes()
        cls.metadata = json.loads((HERE / "baseline.json").read_text())
        cls.baseline = read_yaml(HERE / "baseline.verify.yml")
        cls.proposal = read_yaml(HERE / "proposed.verify.yml")
        cls.job = cls.proposal["jobs"][NEW_JOB]
        cls.steps = cls.job["steps"]

    def test_baseline_bytes_are_bound(self) -> None:
        self.assertEqual(hashlib.sha256(self.baseline_bytes).hexdigest(), self.metadata["baseline_sha256"])
        self.assertEqual(len(self.baseline_bytes), self.metadata["baseline_bytes"])

    def test_canonical_workflow_is_unchanged_since_snapshot(self) -> None:
        self.assertEqual((ROOT / ".github/workflows/verify.yml").read_bytes(), self.baseline_bytes)

    def test_proposal_is_exact_baseline_followed_by_one_job(self) -> None:
        self.assertEqual(self.proposal_bytes, self.baseline_bytes + (HERE / "job.yml").read_bytes())

    def test_existing_five_jobs_and_forty_steps_are_parsed_identical(self) -> None:
        expected = self.metadata["existing_jobs"]
        self.assertEqual(list(self.baseline["jobs"]), expected)
        self.assertEqual(len(expected), 5)
        self.assertEqual(sum(len(job["steps"]) for job in self.baseline["jobs"].values()), 40)
        self.assertEqual(self.metadata["existing_step_count"], 40)
        for name in expected:
            self.assertEqual(self.proposal["jobs"][name], self.baseline["jobs"][name], name)

    def test_only_new_job_changes_parsed_workflow(self) -> None:
        reduced = copy.deepcopy(self.proposal)
        del reduced["jobs"][NEW_JOB]
        self.assertEqual(reduced, self.baseline)
        self.assertEqual(list(self.proposal["jobs"]), list(self.baseline["jobs"]) + [NEW_JOB])

    def test_independent_job_has_no_dependencies_retry_or_error_mask(self) -> None:
        self.assertEqual(set(self.job), {"runs-on", "timeout-minutes", "env", "steps"})
        self.assertEqual(len(self.steps), 5)
        for step in self.steps:
            self.assertNotIn("continue-on-error", step)
            self.assertNotIn("retry", step)
        self.assertTrue(all("if" not in step for step in self.steps[:-1]))

    def test_host_and_outer_job_bound(self) -> None:
        self.assertEqual(self.job["runs-on"], "macos-15")
        self.assertEqual(self.job["timeout-minutes"], 30)

    def test_no_automatic_installation_or_toolchain_override(self) -> None:
        self.assertEqual(self.job["env"], {"RUSTUP_AUTO_INSTALL": "0"})
        all_run = "\n".join(step.get("run", "") for step in self.steps)
        for forbidden in ("RUSTUP_TOOLCHAIN", "rustup install", "rustup update", "toolchain install", "+1.98", "+1.99", "cargo "):
            self.assertNotIn(forbidden, all_run)

    def test_shallow_sparse_checkout_has_only_exact_closed_directory(self) -> None:
        self.assertEqual(self.steps[0], {
            "uses": "actions/checkout@v4",
            "with": {
                "fetch-depth": 1,
                "sparse-checkout-cone-mode": False,
                "sparse-checkout": "/verification/swift-cache-state-ci/",
            },
        })

    def test_step_bounds_leave_runner_fixed_eleven_minute_allowance(self) -> None:
        self.assertEqual([step.get("timeout-minutes") for step in self.steps], [None, 2, 3, 12, 5])
        self.assertGreater(self.steps[3]["timeout-minutes"] * 60, 600 + 60)
        self.assertLess(sum(step.get("timeout-minutes", 0) for step in self.steps), self.job["timeout-minutes"])

    def test_run_steps_use_fail_fast_bash(self) -> None:
        for step in self.steps[1:4]:
            self.assertEqual(step["shell"], "bash")
            self.assertTrue(step["run"].startswith("set -euo pipefail\n"))
            checked = subprocess.run(["bash", "-n"], input=step["run"], text=True, capture_output=True, timeout=10)
            self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_full_runner_has_no_budget_filter_pack_or_expectation_override(self) -> None:
        script = self.steps[3]["run"]
        self.assertIn('MIXER_CACHE_RUSTC_LAUNCHER="$(command -v rustc)"', script)
        self.assertIn('--rustc "$MIXER_CACHE_RUSTC_LAUNCHER"', script)
        for forbidden in ("--budget", "--timeout", "--pack", "--manifest", "--filter", "--expect", "--allow", "--skip", "||", "set +e"):
            self.assertNotIn(forbidden, script)

    def test_preserve_complete_evidence_always_including_hidden_inputs(self) -> None:
        self.assertEqual(self.steps[4], {
            "name": "Preserve complete closed cache-state evidence",
            "if": "always()",
            "timeout-minutes": 5,
            "uses": "actions/upload-artifact@v4",
            "with": {
                "name": "swift-cache-state-fixture-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}",
                "retention-days": 14,
                "if-no-files-found": "warn",
                "include-hidden-files": True,
                "path": "${{ github.workspace }}/verification/swift-cache-state-ci/",
            },
        })

    def test_ignore_rules_cover_only_owned_outputs(self) -> None:
        self.assertEqual((HERE / "proposed.gitignore").read_text().splitlines(), ["/logs/", "/runs/"])

    def run_probe(self, target_step: int, *, program_exit: int = 0, prepare_twice: bool = False, missing_launcher: bool = False) -> tuple:
        with tempfile.TemporaryDirectory(prefix="workflow-probe-", dir=HERE) as raw:
            workspace = Path(raw)
            fixture = workspace / FIXTURE
            fixture.mkdir(parents=True)
            bin_dir = workspace / "bin"
            bin_dir.mkdir()
            launcher = bin_dir / "rustc"
            launcher.write_text("#!/bin/sh\nexit 99\n")
            launcher.chmod(0o700)
            recorder = '''import json, os, sys
from pathlib import Path
p = Path(__file__)
record = {"argv": sys.argv[1:], "auto_install": os.environ.get("RUSTUP_AUTO_INSTALL"), "toolchain": os.environ.get("RUSTUP_TOOLCHAIN")}
(p.parent / "logs" / (p.stem + ".invocation.json")).write_text(json.dumps(record))
print("workflow probe stdout")
print("workflow probe stderr", file=sys.stderr)
sys.exit(int(os.environ.get("WORKFLOW_PROBE_EXIT", "0")))
'''
            for name in ("test_runner.py", "check_cache_state.py"):
                (fixture / name).write_text(recorder)
            env = dict(os.environ)
            env.update({
                "GITHUB_WORKSPACE": str(workspace),
                "GITHUB_RUN_ID": "12345", "GITHUB_RUN_ATTEMPT": "2",
                "RUSTUP_AUTO_INSTALL": "0", "WORKFLOW_PROBE_EXIT": str(program_exit),
                "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
            })
            prepared = subprocess.run(["bash", "-c", self.steps[1]["run"]], cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            if missing_launcher:
                launcher.unlink()
                env["PATH"] = str(bin_dir)
            if prepare_twice:
                result = subprocess.run(["bash", "-c", self.steps[1]["run"]], cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
            else:
                result = subprocess.run(["/bin/bash", "-c", self.steps[target_step]["run"]], cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
            logs = {p.name: p.read_text() for p in (fixture / "logs").iterdir() if p.is_file()}
            dirs = sorted(p.name for p in fixture.iterdir() if p.is_dir())
            return result.returncode, logs, dirs, str(fixture), str(launcher), env.get("RUSTUP_TOOLCHAIN")

    def test_prepare_creates_only_fresh_owned_logs_and_runs(self) -> None:
        status, logs, dirs, *_ = self.run_probe(2)
        self.assertEqual(status, 0)
        self.assertEqual(dirs, ["logs", "runs"])
        self.assertIn(self.metadata["source_revision"], logs["host.stdout"])
        self.assertIn("Python ", logs["host.stdout"])

    def test_prepare_refuses_existing_output_directories(self) -> None:
        status, logs, dirs, *_ = self.run_probe(1, prepare_twice=True)
        self.assertNotEqual(status, 0)
        self.assertEqual(dirs, ["logs", "runs"])
        self.assertNotIn("test_runner.invocation.json", logs)

    def test_controls_run_whole_script_verbose_without_filters(self) -> None:
        status, logs, _, _, _, old_toolchain = self.run_probe(2)
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(logs["test_runner.invocation.json"]), {
            "argv": ["-v"], "auto_install": "0", "toolchain": old_toolchain,
        })
        self.assertEqual(logs["runner-controls.stdout"], "workflow probe stdout\n")
        self.assertEqual(logs["runner-controls.stderr"], "workflow probe stderr\n")

    def test_full_runner_receives_exact_existing_launcher_and_fresh_output(self) -> None:
        status, logs, _, fixture, launcher, old_toolchain = self.run_probe(3)
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(logs["check_cache_state.invocation.json"]), {
            "argv": ["--rustc", launcher, "--out", fixture + "/runs/ci-12345-2"],
            "auto_install": "0", "toolchain": old_toolchain,
        })
        self.assertEqual(logs["cache-state.stdout"], "workflow probe stdout\n")
        self.assertEqual(logs["cache-state.stderr"], "workflow probe stderr\n")

    def test_controls_failure_is_terminal_and_raw_logs_remain(self) -> None:
        status, logs, *_ = self.run_probe(2, program_exit=17)
        self.assertEqual(status, 17)
        self.assertEqual(logs["runner-controls.stderr"], "workflow probe stderr\n")
        self.assertNotIn("check_cache_state.invocation.json", logs)

    def test_runner_refusal_is_terminal_and_raw_logs_remain(self) -> None:
        status, logs, *_ = self.run_probe(3, program_exit=31)
        self.assertEqual(status, 31)
        self.assertEqual(logs["cache-state.stdout"], "workflow probe stdout\n")
        self.assertEqual(logs["cache-state.stderr"], "workflow probe stderr\n")

    def test_missing_launcher_fails_without_invoking_runner_or_fallback(self) -> None:
        status, logs, *_ = self.run_probe(3, missing_launcher=True)
        self.assertNotEqual(status, 0)
        self.assertNotIn("check_cache_state.invocation.json", logs)
        self.assertIn("cache-state.stdout", logs)
        self.assertIn("cache-state.stderr", logs)


if __name__ == "__main__":
    unittest.main()
