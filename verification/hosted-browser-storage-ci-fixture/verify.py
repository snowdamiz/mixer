#!/usr/bin/env python3
"""Verify retained selected evidence and bind the current bounded delivery."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


checks = []
commands = [
    ("source-whitespace", ["git", "diff", "--check", "--", "hosted/test/mixer_hosted/browser_auth/storage_spec.exs"]),
    ("source-format", ["elixir", "-e", 'f="hosted/test/mixer_hosted/browser_auth/storage_spec.exs"; text=File.read!(f); formatted=IO.iodata_to_binary(Code.format_string!(text)); if String.trim_trailing(text)!=formatted, do: System.halt(1)']),
]
for name, argv in commands:
    process = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    (BASE / (name + ".stdout")).write_bytes(process.stdout)
    (BASE / (name + ".stderr")).write_bytes(process.stderr)
    checks.append({"name": name, "argv": argv, "exit_code": process.returncode,
                   "timeout_seconds": 30, "stdout": name + ".stdout", "stderr": name + ".stderr"})
    assert process.returncode == 0, name

for name in ["run.py", "verify.py"]:
    ast.parse((BASE / name).read_text())
checks.append({"name": "collector-and-verifier-python-syntax", "method": "ast.parse", "passed": True})
delivery = ["hosted/test/mixer_hosted/browser_auth/storage_spec.exs",
            "docs/hosted-browser-storage-ci-fixture.md"]
delivery += ["verification/hosted-browser-storage-ci-fixture/" + name
             for name in ["run.py", "plan_probe.exs", "verify.py"]]
for rel in delivery:
    assert all(line.rstrip() == line for line in (ROOT / rel).read_text().splitlines()), rel
checks.append({"name": "delivery-trailing-whitespace", "passed": True})

results = []
for label, expected in [("baseline", 23), ("fixed", 24)]:
    paths = sorted((BASE / "attempts").glob(label + "-*"))
    assert paths
    for out in paths:
        receipt = json.loads((out / "receipt.json").read_text())
        assert receipt["collection_complete"] and receipt["success"] and all(receipt["cleanup"].values())
        assert receipt["tests"] == {"total": expected, "failures": 0, "skipped": 0, "excluded": 0}
        for rel, digest in receipt["source_sha256"].items():
            assert sha(out / "inputs" / rel) == digest, rel
        for rel, digest in receipt["outputs_sha256"].items():
            assert sha(out / rel) == digest, rel
        if label == "fixed" and out == paths[-1]:
            for rel, digest in receipt["source_sha256"].items():
                assert sha(ROOT / rel) == digest, rel
        results.append({"label": label, "receipt": str((out / "receipt.json").relative_to(ROOT)),
                        "receipt_sha256": sha(out / "receipt.json"), "tests": receipt["tests"],
                        "source_tree_sha256": receipt["source_tree_sha256"],
                        "source_unchanged_during_run": not receipt["source_changes_during_run"],
                        "cleanup": receipt["cleanup"]})

ci = json.loads((BASE / "ci-failure/source-manifest.json").read_text())
baseline = json.loads((BASE / "attempts/baseline-20261025T164833.502555Z-7750f0cc/receipt.json").read_text())
assert ci["sources"][delivery[0]] == baseline["source_sha256"][delivery[0]]
binding = json.loads((BASE / "ci-failure-binding.json").read_text())
for rel, digest in binding["files_sha256"].items():
    assert sha(BASE / rel) == digest, rel
checks.append({"name": "original-spec-and-retained-failure-CI-integrity", "passed": True})

receipt = {
    "schema": 1, "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "command": ["python3", "verification/hosted-browser-storage-ci-fixture/verify.py"],
    "accepted_local_selected_result": results[-1], "retained_results": results, "checks": checks,
    "pending": ["Independent root review", "Exact-push Ubuntu Phoenix CI and broad hosted suite",
                "Browser/native runtime/capture paused", "Provider/customer/FieldLog/GA qualification"],
    "limitations": ["Failed Ubuntu CI 5s timeout not reproduced locally",
                    "Sequential one-row local plans establish JIT overhead and policy mismatch, not precise failed-CI phase attribution"],
    "owned_paths": [delivery[0], delivery[1], "verification/hosted-browser-storage-ci-fixture/"],
    "scope": "Selected explicit-source PostgreSQL16 host fixture development only; no product/session/schema/workflow/default-budget change; no broad app/frozen/native/provider/production action",
    "current_delivery_sha256": {rel: sha(ROOT / rel) for rel in delivery},
    "ci_failure_binding_sha256": sha(BASE / "ci-failure-binding.json"),
}
(BASE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"checks_passed": len(checks), "retained_attempts": len(results),
                  "fixed": results[-1]["tests"], "cleanup": results[-1]["cleanup"]}))
