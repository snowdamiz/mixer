#!/usr/bin/env python3
"""Bind reviewed ordinary components without executing the shared hosted harness."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def read(name):
    return json.loads((ROOT / name).read_text())


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


sources = {}
bindings = {}


def check_manifest(manifest):
    for name, expected in manifest.items():
        assert sha(name) == expected, name
        sources[name] = expected


console_path = "verification/console-cookie-workspace-transport/attempts/20261025T151110812242Z/receipt.json"
console = read(console_path)
assert console["status"] == "passed"
check_manifest(console["sources"])
console_dir = str(Path(console_path).parent)
for label, command in zip(["node-version", "npm-version", "elixir-version", "typecheck", "tests", "build"], console["commands"], strict=True):
    assert command["exit_code"] == 0
    for stream in ["stdout", "stderr"]:
        name = f"{console_dir}/{label}.{stream}"
        assert sha(name) == command[f"{stream}_sha256"], name
        bindings[name] = sha(name)
console_tests = (ROOT / console_dir / "tests.stdout").read_text()
assert "# tests 112\n" in console_tests and "# fail 0\n" in console_tests and "# skipped 0\n" in console_tests

protocol_path = "verification/hosted-browser-auth-protocol/receipt.json"
protocol = read(protocol_path)
assert protocol["status"] == "passed"
assert protocol["selected_host_tests"] == {"total": 39, "failures": 0, "excluded": 0, "skipped": 0}
manifest = read(protocol["source_inputs"])
check_manifest(manifest["files"])
check_manifest(manifest["jason_beams"])
for command in protocol["commands"]:
    assert command["exit_code"] == 0
    for stream in ["stdout", "stderr"]:
        bindings[command[stream]] = sha(command[stream])
assert protocol["cleanup"]["owned_scratch_removed"]

review = read("verification/browser-auth-prerequisite-review/handoff.json")
for name, digest in review["artifacts"].items():
    assert sha(name) == digest, name
    bindings[name] = digest
independent = read(review["bound_review_receipt"])
assert independent["status"] == "passed" and independent["findings"] == []
check_manifest(independent["sources"])
assert independent["protocol_summary"] == {"total": 15, "failures": 0, "excluded": 0, "skipped": 0}
assert independent["transport_summary"] == ["# tests 15", "# pass 15", "# fail 0", "# skipped 0"]
assert independent["cleanup"]["owned_scratch_removed"]

contract_path = "verification/hosted-browser-session-storage-contract/receipt.json"
contract = read(contract_path)
assert contract["product_tests_executed"] is False
assert contract["document_checks"]["pending_implementation_cases"] == 18
context_changes = []
for item in contract["inputs"]:
    if item["path"] == "PLAN.md":
        if sha(item["path"]) != item["sha256"]:
            context_changes.append("PLAN.md was advanced after the design-only receipt; no contract/product input changed")
        continue
    check_manifest({item["path"]: item["sha256"]})

for asset in ["flick-128.webp", "favicon-32.png"]:
    assert sha(f"console/public/assets/{asset}") == sha(f"website/public/assets/{asset}")

ruby = '''d = YAML.load_file(".github/workflows/hosted.yml"); a = d.fetch("jobs").fetch("phoenix").fetch("steps").find { |s| s["name"] == "Browser auth protocol host checks" }; abort "unexpected environment" unless a["env"] == {"MIX_ENV" => "test"}; abort "unexpected commands" unless a["run"].lines.map(&:strip) == ["mix deps.compile jason", "python3 ../verification/hosted-browser-auth-protocol/run.py"]; puts "Selected protocol CI step parses with exact dependency/test commands"'''
argv = ["ruby", "-ryaml", "-e", ruby]
result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15)
for stream, value in [("stdout", result.stdout), ("stderr", result.stderr)]:
    (OUT / f"ci-yaml.{stream}").write_bytes(value)
assert result.returncode == 0

for name in [console_path, protocol_path, contract_path, review["bound_review_receipt"],
             "docs/console-cookie-workspace-transport.md", "docs/browser-auth-prerequisite-review.md",
             ".github/workflows/hosted.yml", str(Path(__file__).resolve().relative_to(ROOT))]:
    bindings[name] = sha(name)

packages = read("work-graph.json")["packages"]
gates = read("gates/ga.json")["gates"]
package_counts = dict(collections.Counter(row["state"] for row in packages))
gate_counts = dict(collections.Counter(row["status"] for row in gates))
receipt = {
    "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "accepted_local_prerequisites",
    "current_source_bindings": sources,
    "current_source_tree_sha256": hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
    "retained_evidence_bindings": bindings,
    "console_host_tests": 112, "protocol_host_tests": 39,
    "independent_transport_tests": 15, "independent_protocol_tests": 15,
    "counts_overlap_existing_suites": True,
    "storage_contract_pending_cases": 18,
    "context_changes": context_changes,
    "ci_step": {"argv": argv, "exit_code": result.returncode,
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
                "dependency_compile": "MIX_ENV=test mix deps.compile jason exited 0 locally without output; only this named dependency was requested"},
    "exploration_failure": "Python YAML check exited 1 because PyYAML is absent; Ruby standard-library YAML parse passes. No dependency installed.",
    "package_states": package_counts, "gate_states": gate_counts,
    "cleanup": "Producer/reviewer owned compilation and HTTP cleanup pass; no browser, capture, native or phone process started",
    "limits": ["No live login/session routes or production session adapter", "Provider exchange and OIDC verification pending", "Durable lifecycle SQL/vault unimplemented", "Mobile layout change has host build evidence only; visual review paused", "Current Phoenix CI directory transaction deadline remains unresolved", "No deployment, customer, FieldLog or GA acceptance"],
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "sources": len(sources), "evidence": len(bindings),
                  "packages": package_counts, "gates": gate_counts}))
