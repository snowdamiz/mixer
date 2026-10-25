#!/usr/bin/env python3
"""Structural documentation checks only; never runtime/security admission."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
DOC = ROOT / "docs/hosted-browser-lifecycle-runtime-contract.md"
SCHEMA = ROOT / "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex"
INPUTS = [
    "AGENTS.md", "PLAN.md", "mixer-product-plan.md",
    "docs/hosted-browser-session-storage-contract.md",
    "docs/hosted-browser-session-integration.md",
    "docs/hosted-browser-session-storage.md",
    "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex",
    "hosted/lib/mixer_hosted/browser_auth/config.ex",
    "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
    "hosted/lib/mixer_hosted/browser_auth/vault.ex",
    "hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex",
    "hosted/lib/mixer_hosted/browser_auth/protocol.ex",
    "hosted/lib/mixer_hosted/identity/configured_verifier.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/identity/key_owner.ex",
    "hosted/lib/mixer_hosted/authorization.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/customer_workspace.ex",
    "hosted/lib/mixer_hosted/application.ex",
    "hosted/lib/mixer_hosted/repo.ex",
    "hosted/lib/mixer_hosted/runtime_config.ex",
    "hosted/lib/mixer_hosted_web/router.ex",
    "hosted/config/runtime.exs",
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs",
    "docs/hosted-browser-lifecycle-runtime-contract.md",
    str((BASE / "README.md").relative_to(ROOT)),
    str((BASE / "emit_baseline.exs").relative_to(ROOT)),
    str(Path(__file__).resolve().relative_to(ROOT)),
    str((BASE / "adversity-matrix.json").relative_to(ROOT)),
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sources() -> dict:
    return {name: sha((ROOT / name).read_bytes()) for name in sorted(INPUTS)}


def validate_signatures(document: str, manifest: dict) -> None:
    current = {
        name: value for name, value in manifest["functions"].items()
        if value["runtime_execute"]
    }
    if len(current) != 9 or len(manifest["functions"]) != 18:
        raise ValueError("baseline cardinality changed; coordinate contract version")
    lines = re.findall(r"^public\.(mixer_browser_\w+)\(([^\n]*)\) -> ([^\n]+)$", document, re.M)
    found = {name: (signature, result) for name, signature, result in lines}
    if len(lines) != len(found) or set(found) != set(current):
        raise ValueError("document baseline operation set mismatch")
    for name, item in current.items():
        expected_result = item["result"] + ("-or-NULL" if name == "mixer_browser_load" else "")
        if found[name] != (item["signature"], expected_result):
            raise ValueError("document typed signature/result drift: " + name)
        if sha(item["source"].encode()) != item["source_sha256"]:
            raise ValueError("source manifest hash mismatch")
        if item["settings"] != ["search_path=pg_catalog", "statement_timeout=5s", "lock_timeout=500ms", "idle_in_transaction_session_timeout=5s", "bytea_output=hex"]:
            raise ValueError("baseline settings changed")


def main() -> int:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    attempt = BASE / "attempts" / stamp
    attempt.mkdir(parents=True)
    commands = []

    def run(argv: list[str], label: str, timeout: int = 30) -> str:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=timeout)
        (attempt / (label + ".stdout")).write_bytes(result.stdout)
        (attempt / (label + ".stderr")).write_bytes(result.stderr)
        commands.append({"argv": argv, "cwd": str(ROOT), "timeout_seconds": timeout,
                         "exit_code": result.returncode,
                         "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr)})
        if result.returncode:
            raise RuntimeError("command failed: " + label)
        return result.stdout.decode()

    before = sources()
    receipt = {"version": 1, "kind": "documentation-contract-check", "scope": "offline ordinary StorageSchema inventory and document negative controls only", "attempt": stamp,
               "agent": {"model": "gpt-6.1-sol", "reasoning_effort": "xhigh", "context": "fresh bounded delegated task"},
               "commands": commands, "sources": before,
               "source_tree_digest": sha(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()),
               "runtime_adversity": "pending implementation", "no_native_capture_provider_database_or_production_process_started": True,
               "cleanup": "Elixir module exists only in terminated subprocess memory; no database, native or capture instance created"}
    try:
        receipt["head"] = run(["git", "rev-parse", "HEAD"], "head").strip()
        receipt["tools"] = {
            "python": sys.version,
            "elixir_path": shutil.which("elixir"),
            "elixir": run(["elixir", "--version"], "elixir-version").strip(),
            "git": run(["git", "--version"], "git-version").strip(),
        }
        raw = run(["elixir", str(BASE / "emit_baseline.exs"), str(SCHEMA)], "baseline")
        manifest = json.loads(raw)
        document = DOC.read_text()
        matrix = json.loads((BASE / "adversity-matrix.json").read_text())

        class ContractChecks(unittest.TestCase):
            def test_exact_baseline_signatures_and_sources(self):
                validate_signatures(document, manifest)
            def test_missing_operation_is_rejected(self):
                changed = document.replace("public.mixer_browser_load(bytea,bytea) -> jsonb-or-NULL", "removed")
                with self.assertRaises(ValueError): validate_signatures(changed, manifest)
            def test_changed_signature_is_rejected(self):
                changed = document.replace("public.mixer_browser_load(bytea,bytea)", "public.mixer_browser_load(text,bytea)")
                with self.assertRaises(ValueError): validate_signatures(changed, manifest)
            def test_extra_executable_helper_is_rejected(self):
                changed = json.loads(json.dumps(manifest))
                changed["functions"]["mixer_browser_unsafe_extra"] = next(iter(changed["functions"].values()))
                with self.assertRaises(ValueError): validate_signatures(document, changed)
            def test_body_hash_drift_is_rejected(self):
                changed = json.loads(json.dumps(manifest))
                changed["functions"]["mixer_browser_load"]["source"] += "unsafe drift"
                with self.assertRaises(ValueError): validate_signatures(document, changed)
            def test_setting_drift_is_rejected(self):
                changed = json.loads(json.dumps(manifest))
                changed["functions"]["mixer_browser_load"]["settings"] = []
                with self.assertRaises(ValueError): validate_signatures(document, changed)
            def test_matrix_has_unique_pending_cases_and_no_acceptance_claim(self):
                cases = matrix["cases"]
                self.assertGreaterEqual(len(cases), 30)
                self.assertEqual(len(cases), len({case["id"] for case in cases}))
                self.assertTrue(all(case["status"] == "pending_runtime_implementation" for case in cases))
                self.assertTrue(all(case["fixture"] and case["assertion"] and case["command_group"] for case in cases))
            def test_additive_seam_is_marked_proposed_with_six_keys(self):
                self.assertIn("proposal for the next separately reviewed prerequisite", document)
                self.assertIn("all six top-level keys/types", document)
                self.assertIn("Version-1 admission must reject the added surface", document)
                self.assertIn("Unknown exact identity binding remains", document)

        log = attempt / "checks.txt"
        with log.open("w") as output:
            result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ContractChecks))
        receipt["checks"] = {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "passed": result.wasSuccessful()}
        if not result.wasSuccessful():
            raise RuntimeError("documentation checks failed")
        run(["git", "diff", "--check", "--", "docs/hosted-browser-lifecycle-runtime-contract.md", "verification/hosted-browser-lifecycle-runtime-contract"], "diff-check")
        if sources() != before:
            raise RuntimeError("input changed during check")
        receipt["sources_unchanged"] = True
        (BASE / "baseline-catalog.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        receipt["baseline_catalog_sha256"] = sha((BASE / "baseline-catalog.json").read_bytes())
        receipt["status"] = "passed_documentation_only"
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["failure"] = str(exc)
    finally:
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        (BASE / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "attempt": str(attempt), "checks": receipt.get("checks")}, sort_keys=True))
    return 0 if receipt["status"] == "passed_documentation_only" else 1


if __name__ == "__main__":
    raise SystemExit(main())
