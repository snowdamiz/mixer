#!/usr/bin/env python3
"""Prepare the exact reviewed local customer-artifact checkpoint."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "9662eda186e3beee084f92ac25c4116c92f2cebc"
selected = {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add(name, expected=None):
    path = ROOT / name
    assert path.resolve().is_relative_to(ROOT) and not path.is_symlink(), name
    assert stat.S_ISREG(path.stat().st_mode) and path.stat().st_size < 100_000_000, name
    assert "__pycache__" not in path.parts
    assert not any(part in name for part in ["hosted-catalog-inspector", "hosted-authority-driver", "outbound-worker-transport-v2"])
    actual = digest(path)
    if expected:
        assert actual == expected, name
    selected[name] = {"sha256": actual, "bytes": path.stat().st_size}


assert not (OUT / "selection.json").exists()
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == BASE
assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT).strip()
remote = subprocess.check_output(["git", "ls-remote", "origin", "refs/heads/main"], cwd=ROOT, text=True)
assert remote.strip().split() == [BASE, "refs/heads/main"]
acceptance_dir = ROOT / "verification/hosted-customer-artifact-root-acceptance/attempt-2"
acceptance = json.loads((acceptance_dir / "acceptance.json").read_text())
assert acceptance["status"] == "accepted-local-customer-artifact-composition"
assert acceptance["current_combined_methods"] == 97 and acceptance["migration_count"] == 7
assert digest(acceptance_dir / "bindings.json") == acceptance["bindings_sha256"]
for name, expected in json.loads((acceptance_dir / "bindings.json").read_text()).items():
    add(name, expected)
ci = json.loads((ROOT / "verification/hosted-customer-artifact-ci/run-3/receipt.json").read_text())
assert len(ci["inputs"]) == 45
for name, expected in ci["inputs"].items():
    add(name, expected)
for name in [
    "hosted/lib/mixer_hosted/audit/customer_artifact_event.ex",
    "hosted/test/mixer_hosted/audit/customer_artifact_event_test.exs",
    "hosted/lib/mixer_hosted/authorization/artifact_read.ex",
    "hosted/test/mixer_hosted/authorization/artifact_read_test.exs",
    "hosted/lib/mixer_hosted/customer_artifacts.ex",
    "hosted/test/mixer_hosted/customer_artifacts_test.exs",
    "hosted/lib/mixer_hosted/customer_artifacts/schema.ex",
    "hosted/lib/mixer_hosted/customer_artifacts/postgres_storage.ex",
    "hosted/lib/mixer_hosted/customer_artifacts/topology.ex",
    "hosted/test/mixer_hosted/customer_artifacts/postgres_storage_test.exs",
    "hosted/priv/repo/migrations/20261025000005_add_customer_artifact_storage.exs",
]:
    add(name)
for folder in [
    "hosted-customer-artifact-event", "hosted-customer-artifact-event-review",
    "hosted-customer-artifact-read-scope", "hosted-customer-artifact-read-review",
    "hosted-customer-artifact-storage", "hosted-customer-artifact-storage-review",
    "hosted-customer-artifact-facade", "hosted-customer-artifact-facade-review",
    "hosted-customer-artifact-ci", "hosted-customer-artifact-root-acceptance", "github-ci-9662eda1",
]:
    for path in sorted((ROOT / "verification" / folder).rglob("*")):
        if path.is_file():
            add(str(path.relative_to(ROOT)))
for suffix in ["event", "event-review", "read-scope", "read-review", "storage", "storage-review",
               "facade", "facade-review", "integration", "transaction-contract"]:
    add("docs/hosted-customer-artifact-" + suffix + ".md")
for name in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]:
    add(name)
for name in ["commit.stdout", "commit.stderr", "push.stdout", "push.stderr", "delivery-receipt.json",
             "ci-initial.json", "ci-initial.stderr", "ci-initial-receipt.json"]:
    add("verification/github-delivery-authorized-transaction/" + name)
for name, group, state, count in [("work-graph.json", "packages", "state", 18), ("gates/ga.json", "gates", "status", 38)]:
    before = json.loads(subprocess.check_output(["git", "show", BASE + ":" + name], cwd=ROOT))
    after = json.loads((ROOT / name).read_text())
    assert len(after[group]) == count
    assert [(x["id"], x[state], x.get("reviewer")) for x in before[group]] == [(x["id"], x[state], x.get("reviewer")) for x in after[group]]
prior_ci = json.loads((ROOT / "verification/github-ci-9662eda1/observation-1/receipt.json").read_text())
assert prior_ci["sourceRevision"] == BASE
assert all(x["status"] == "completed" and x["conclusion"] == "success" for x in prior_ci["workflows"])
assert all(j["skippedSteps"] == 0 for x in prior_ci["workflows"] for j in x["jobs"])
for name, prefix in [("verification/console-build-overview-root-review/final-source-manifest.json", ""),
                     ("verification/swift-cost-retention-candidate/live-baseline-source-manifest.json", "vm/")]:
    binding = json.loads((ROOT / name).read_text())
    for path, expected in binding.get("files", binding).items():
        assert digest(ROOT / (prefix + path)) == expected
policy = subprocess.run(["python3", "scripts/check-policy.py"], cwd=ROOT, capture_output=True, timeout=90)
(OUT / "policy.stdout").write_bytes(policy.stdout)
(OUT / "policy.stderr").write_bytes(policy.stderr)
assert policy.returncode == 0 and json.loads(policy.stdout)["status"] == "passed"
(OUT / "policy-receipt.json").write_text(json.dumps({
    "argv": ["python3", "scripts/check-policy.py"], "exitCode": 0,
    "sourceRevision": BASE, "scope": "manifest-and-gate-guardrail-only",
    "scriptSHA256": digest(ROOT / "scripts/check-policy.py"),
    "stdoutSHA256": digest(OUT / "policy.stdout"), "stderrSHA256": digest(OUT / "policy.stderr"),
    "python": subprocess.check_output(["python3", "--version"], text=True).strip()
}, indent=2) + "\n")
for name in ["prepare.py", "stage.py", "policy.stdout", "policy.stderr", "policy-receipt.json"]:
    add(str((OUT / name).relative_to(ROOT)))
manifest = {
    "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "baseRevision": BASE, "files": dict(sorted(selected.items())),
    "scope": "Reviewed local customer artifact upload, private read, v2 audit and principal-bound retries; CI fixtures, seven-migration integration and independent evidence. No HTTP, provider, native or GA acceptance.",
    "retainedDependencyBytes": "Includes the independent staged-read review's copied pinned general-purpose BEAM dependency inputs, intentionally retained as evidence.",
    "previousCI": "Both 9662eda1 workflows passed with zero skipped steps.",
    "statesAndReviewersUnchanged": True
}
(OUT / "selection.json").write_text(json.dumps(manifest, indent=2) + "\n")
paths = sorted([*selected, str((OUT / "selection.json").relative_to(ROOT))])
(OUT / "paths.nul").write_bytes(b"".join(os.fsencode(x) + b"\0" for x in paths))
print(json.dumps({"selectedFiles": len(paths), "selectedBytes": sum(x["bytes"] for x in selected.values()), "gateStatesUnchanged": True}))
