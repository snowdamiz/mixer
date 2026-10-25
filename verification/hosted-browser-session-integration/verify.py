#!/usr/bin/env python3
"""Bind the reviewed development slices to current source and retained evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
bindings = {}
evidence = {}
commands = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    path = ROOT / path
    evidence[str(path.relative_to(ROOT))] = sha(path)
    return json.loads(path.read_text())


def current(mapping):
    for path, expected in mapping.items():
        if path.startswith(("hosted/", ".github/")):
            assert sha(ROOT / path) == expected, f"current source differs: {path}"
            bindings[path] = expected


def outputs(base, mapping):
    for name, expected in mapping.items():
        path = base / name
        assert sha(path) == expected, f"retained output differs: {path}"
        evidence[str(path.relative_to(ROOT))] = expected


def successful(result, total):
    assert result == {"total": total, "failures": 0, "skipped": 0, "excluded": 0}, result


def linked(path):
    top = read(path)
    target = ROOT / top["receipt"]
    assert sha(target) == top["receipt_sha256"]
    return top, read(top["receipt"]), target.parent


meta, meta_run, base = linked("verification/hosted-browser-config-text-review/acceptance.json")
assert meta["status"] == "passed" and meta_run["status"] == "passed"
successful(meta_run["selected_result"], 32)
current(meta_run["input_sha256"])
outputs(base, meta_run["output_sha256"])
assert meta_run["cleanup"]["owned_scratch_removed"]

jit = read("verification/hosted-workspace-jit-policy/run-4/receipt.json")
assert jit["success"] and all(jit["cleanup"].values())
assert sum(v["total"] for v in jit["suites"].values()) == 86
for result in jit["suites"].values():
    successful(result, result["total"])
current(jit["input_sha256"])
outputs(ROOT / "verification/hosted-workspace-jit-policy/run-4", jit["output_sha256"])
jit_review, jit_run, base = linked("verification/hosted-workspace-jit-review/review.json")
assert jit_review["live_unchanged"] and jit_run["success"]
successful(jit_review["tests"], 6)
assert all(jit_review["cleanup"].values())
current(jit_run["source_sha256"])
outputs(base, jit_run["outputs_sha256"])

sql_review, sql_run, base = linked("verification/hosted-browser-session-storage-correction-review/review.json")
assert sql_review["status"] == "passed" and sql_run["focused_tests_passed"]
assert sql_run["source_unchanged"] and all(sql_run["cleanup"].values())
successful(sql_review["selected_tests"], 6)
current(sql_review["tested_source_hashes"])
assert sha(ROOT / sql_review["output"]) == sql_review["output_sha256"]
evidence[sql_review["output"]] = sql_review["output_sha256"]

pg16, pg16_run, base = linked("verification/hosted-browser-storage-pg16/review.json")
successful(pg16["selected_result"], 23)
assert pg16_run["source_unchanged"] and pg16_run["dependency_beams_unchanged"]
assert all(pg16_run["cleanup"].values())
current(pg16_run["input_sha256"])
outputs(base, pg16_run["output_sha256"])

migration, migration_run, base = linked("verification/hosted-browser-migration-review/review.json")
assert migration["status"] == "passed" and migration_run["success"]
assert migration_run["source_unchanged"] and all(migration_run["cleanup"].values())
current(migration_run["sources"])
for command in migration_run["commands"]:
    outputs(base, {command["name"] + "." + stream: command[stream + "_sha256"] for stream in ["stdout", "stderr"]})

# The legacy producer PG17 result predates one removed final newline in its
# test file. Current exact-source PG16 and independent SQL runs above bind that
# final file. Do not pretend the older raw producer snapshot has changed.
old = read("verification/hosted-browser-session-storage/attempts/20261025T160530.884605Z-9652e649/source-manifest.json")
current({p: h for p, h in old["sources"].items() if p != "hosted/test/mixer_hosted/browser_auth/storage_spec.exs"})

expected = [
    ".github/workflows/hosted.yml",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/browser_auth/config.ex",
    "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex",
    "hosted/priv/repo/migrations/20261025000007_add_browser_sessions.exs",
    "hosted/test/foundation_integration_test.exs",
    "hosted/test/mixer_hosted/authorization/jit_policy_spec.exs",
] + ["hosted/test/mixer_hosted/browser_auth/" + name for name in [
    "config_test.exs", "configuration_digest_test.exs", "storage_fixture.exs",
    "storage_spec.exs", "run_storage_fixture.py", "migration_spec.exs", "run_migration_fixture.py",
]] + [f"hosted/test/mixer_hosted/builds/{name}_test.exs" for name in ["storage", "admission", "aggregate_admission", "coordinator"]]
assert not set(expected) - set(bindings), f"missing reviewed bindings: {set(expected)-set(bindings)}"


def run(name, argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True)
    (OUT / f"{name}.stdout").write_bytes(result.stdout)
    (OUT / f"{name}.stderr").write_bytes(result.stderr)
    commands.append({"argv": argv, "exit_code": result.returncode,
                     "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                     "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()})
    assert result.returncode == 0, name


run("python-version", ["python3", "--version"])
run("elixir-version", ["elixir", "--version"])
run("format", ["mix", "format", "--check-formatted", *[p for p in expected if p.endswith((".ex", ".exs"))]])
run("source-whitespace", ["git", "diff", "--check", "--", *expected, "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json", "docs/hosted-browser-session-integration.md"])
packages = json.loads((ROOT / "work-graph.json").read_text())
gates = json.loads((ROOT / "gates/ga.json").read_text())
assert [p["id"] for p in packages["packages"]] == [f"W{n:02}" for n in range(1, 19)]
assert [g["id"] for g in gates["gates"]] == [f"G{n:02}" for n in range(1, 39)]
assert not any(g["status"] == "passed" for g in gates["gates"])
assert packages["executionPause"]["status"] == "resumed"
assert packages["executionPause"]["nativeRuntimePauseStillActive"]
for p in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json", "docs/hosted-browser-session-integration.md"]:
    bindings[p] = sha(ROOT / p)
bindings[str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
receipt = {
    "schema": 1, "status": "accepted-local-components-ci-pending",
    "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "current_source_bindings": bindings,
    "source_tree_sha256": hashlib.sha256(json.dumps(bindings, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    "retained_evidence_bindings": evidence, "commands": commands,
    "tests": {"sql_pg16": 23, "sql_independent_pg17": 6, "config_combined": 32,
              "jit_producer_pg16": 86, "jit_independent_pg16": 6,
              "migration_independent_pg17": 1, "migration_source_checks": 13},
    "counts_overlap": True, "reviewed_changed_product_files": len(expected),
    "scope": "Reviewed inert SQL lifecycle, nine-migration integration, trusted Config text and transaction-local JIT. Exact live source/output bindings; no native/capture/phone/provider/production actions.",
    "cleanup": "All selected final receipts confirm owned database/container/scratch cleanup; this verification starts none.",
    "pending": ["Exact-push Ubuntu CI", "Lifecycle pool/key custody/current verifier/provider/OIDC owner join", "HTTP/console sessions", "Neon/provider/deployment/FieldLog/customer/GA qualification", "Native/capture paused; final physical matrix pending"]}
(OUT / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "current_source_bindings": len(bindings), "retained_evidence_bindings": len(evidence), "source_tree_sha256": receipt["source_tree_sha256"]}))
