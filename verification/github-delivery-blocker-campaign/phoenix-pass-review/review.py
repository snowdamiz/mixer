#!/usr/bin/env python3
"""Independently review retained exact-commit CI evidence; never run the product."""
import datetime
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
EXTRACTED = ROOT / "selected"
SHA = "cc350d3303ca71c5d57e87846f6a61304b658fa7"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def git(*args, input=None):
    result = subprocess.run(["git", *args], input=input, cwd=REPO,
                            capture_output=True, timeout=15)
    assert result.returncode == 0, "Read-only git command failed: " + args[0]
    return result.stdout


zip_manifest = load(ROOT / "zip-manifest.json")
assert (ROOT / "artifact.zip").stat().st_size == 868414 < 8 * 1024 * 1024
assert digest((ROOT / "artifact.zip").read_bytes()) == "9585303f3e0391724ad434f4dde5e3fce89f194fd37ef0fb50bc07b0cb927627"
with zipfile.ZipFile(ROOT / "artifact.zip") as archive:
    entries = archive.infolist()
    assert sum(entry.file_size for entry in entries) <= 64 * 1024 * 1024
    names = set()
    for entry in entries:
        path = Path(entry.filename)
        assert not path.is_absolute() and ".." not in path.parts and "\\" not in entry.filename
        assert entry.filename not in names and not stat.S_ISLNK(entry.external_attr >> 16)
        assert not entry.flag_bits & 1
        names.add(entry.filename)
        data = archive.read(entry)
        assert (EXTRACTED / entry.filename).read_bytes() == data
    assert names == {entry["path"] for entry in zip_manifest["entries"]}
for entry in zip_manifest["entries"]:
    path = EXTRACTED / entry["path"]
    assert path.stat().st_size == entry["bytes"] and digest(path.read_bytes()) == entry["sha256"]

foundation = EXTRACTED / "_temp/phoenix-foundation"
protocol = next(EXTRACTED.glob("mixer/mixer/verification/hosted-browser-auth-protocol/attempts/*/receipt.json"))
storage = next(EXTRACTED.glob("mixer/mixer/verification/hosted-browser-session-storage/attempts/*/receipt.json"))
migration = next(EXTRACTED.glob("_temp/browser-migrations/*/receipt.json"))
f, p, s, m = map(load, (foundation / "receipt.json", protocol, storage, migration))
archive_sources, archive_manifest = {}, []
with tarfile.open(foundation / "source.tar.gz", "r:gz") as archive:
    members = archive.getmembers()
    assert sum(member.size for member in members) <= 64 * 1024 * 1024
    names = set()
    for member in members:
        path = Path(member.name)
        assert not path.is_absolute() and ".." not in path.parts and "\\" not in member.name
        assert member.name == str(path) and not member.name.startswith("./")
        assert member.name not in names and (member.isfile() or member.isdir())
        names.add(member.name)
        if member.isfile():
            data = archive.extractfile(member).read()
            archive_sources[member.name] = digest(data)
            archive_manifest.append({"path": member.name, "bytes": len(data), "sha256": digest(data)})
assert archive_sources == f["inputs"] and len(archive_sources) == 181
assert digest((foundation / "source.tar.gz").read_bytes()) == f["source_archive_sha256"]
save("source-archive-manifest.json", {
    "validation": "No traversal/backslash/duplicate/link/special member; expanded total <=64MiB; archive not executed or extracted.",
    "file_count": len(archive_manifest), "expanded_bytes": sum(row["bytes"] for row in archive_manifest),
    "sha256": f["source_archive_sha256"], "entries": archive_manifest,
})
protocol_inputs = load(protocol.parent / "source-inputs.json")
storage_inputs = load(storage.parent / "source-manifest.json")
maps = {"foundation": f["inputs"], "protocol": protocol_inputs["files"],
        "storage": storage_inputs["sources"], "migration": m["sources"]}

workflow_bytes = git("show", SHA + ":.github/workflows/hosted.yml")
assert workflow_bytes == (ROOT / "phoenix-workflow-at-run.yml").read_bytes()
workflow = workflow_bytes.decode()
prior = git("show", "0b99469dfbeb06ac53ad0223bd070a35f2a6a700:.github/workflows/hosted.yml").decode()
delta = list(difflib.ndiff(prior.splitlines(), workflow.splitlines()))
added, removed = [line[2:] for line in delta if line.startswith("+ ")], [line[2:] for line in delta if line.startswith("- ")]
assert not added and not removed
assert digest(workflow_bytes) == "cc0890f161e03fddc6fcf7435b125412fd26d11fad0dfdb297c3b9df83e31031"
assert "sparse-checkout-cone-mode: false" in workflow
sparse_block = workflow.split("          sparse-checkout: |\n", 1)[1].split("      - uses:", 1)[0]
patterns = [line.strip() for line in sparse_block.splitlines() if line.strip()]
assert len(patterns) == 16 and all(path.startswith("/") for path in patterns)
selected_args = [path.strip("/") for path in patterns]
tree_rows = git("ls-tree", "-r", "-l", "-z", SHA, "--", *selected_args).split(b"\0")
selected = {}
for row in tree_rows:
    if not row:
        continue
    header, path = row.split(b"\t", 1)
    mode, kind, oid, size = header.decode().split()
    assert kind == "blob"
    selected[path.decode()] = {"git_blob": oid, "bytes": int(size), "mode": mode}
required = set().union(*(set(value) for value in maps.values()))
required.update({
    "console/package.json", "console/package-lock.json", "console/src/api/workspace-client.ts",
    "console/src/api/workspace-transport.ts", "console/src/domain/workspace-directory.ts",
    "verification/hosted-customer-workspace-http-integration/node-client-driver.mjs",
    "verification/hosted-customer-artifact-event/golden_event.hex",
    "verification/hosted-customer-artifact-event/golden_hashes.txt",
})
assert required == set(selected) and len(selected) == 194
batch_paths = sorted(selected)
batch = git("cat-file", "--batch", input="".join(f"{SHA}:{path}\n" for path in batch_paths).encode())
offset = 0
expected = {}
for path in batch_paths:
    end = batch.index(b"\n", offset)
    oid, kind, size = batch[offset:end].decode().split()
    assert kind == "blob"
    size = int(size)
    data = batch[end + 1:end + 1 + size]
    assert batch[end + 1 + size:end + 2 + size] == b"\n"
    expected[path] = digest(data)
    selected[path]["sha256"] = expected[path]
    offset = end + 2 + size
assert offset == len(batch)
bindings = {}
for label, source_map in maps.items():
    mismatches = [path for path, value in source_map.items() if value != expected[path]]
    assert not mismatches
    bindings[label] = {"files": len(source_map), "all_match_exact_commit": True,
        "source_tree_sha256": digest(json.dumps(source_map, sort_keys=True, separators=(",", ":")).encode())}
assert f["source_tree_sha256"] == bindings["foundation"]["source_tree_sha256"]
assert p["source_tree_sha256"] == protocol_inputs["tree_sha256"] == bindings["protocol"]["source_tree_sha256"]
assert digest((storage.parent / "source-manifest.json").read_bytes()) == s["source_manifest_sha256"]
assert (storage.parent / "source-manifest.json").read_bytes() == (storage.parent / "source-manifest-after.json").read_bytes()
assert m["source_tree_sha256"] == bindings["migration"]["source_tree_sha256"]
for path, value in m["sources"].items():
    assert digest((migration.parent / "inputs" / path).read_bytes()) == value
assert p["source_revision"] == s["head"] == m["source_revision"] == SHA
assert (foundation / "revision.log").read_text().strip() == SHA
assert digest((ROOT / "test-local-at-run.py").read_bytes()) == expected["hosted/scripts/test-local.py"]
root_selection = load(REPO / "verification/github-delivery-identity-network-transfer/phoenix-review/root-source-selection.json")
assert digest(workflow_bytes) == root_selection["candidate"]["sha256"]
assert len(selected) == root_selection["selected_at_baseline"]["files"]

log_bindings = {}
for label, receipt, directory in [("foundation", f, foundation), ("migration", m, migration.parent)]:
    bad = []
    if label == "foundation":
        for command in receipt["commands"]:
            path = directory / command["log"]
            if not path.is_file() or digest(path.read_bytes()) != command["sha256"]:
                bad.append(command["log"])
    else:
        for command in receipt["commands"]:
            for suffix in ["stdout", "stderr"]:
                path = directory / (command["name"] + "." + suffix)
                if not path.is_file() or digest(path.read_bytes()) != command[suffix + "_sha256"]:
                    bad.append(path.name)
        for name, value in receipt["outputs_sha256"].items():
            assert digest((directory / name).read_bytes()) == value
    assert not bad
    log_bindings[label] = {"commands": len(receipt["commands"]), "command_log_hash_mismatches": bad}
assert [(c["label"], c["exit_code"]) for c in f["commands"] if c["exit_code"]] == [("release-missing-config", 1)]
assert all(c["exit_code"] == 0 and not c["timed_out"] for c in m["commands"])
assert all(c["exit_code"] == 0 and not c["timed_out"] for c in s["commands"])
assert all(c["exit_code"] == 0 for c in p["commands"])
for command in p["commands"]:
    for key in ["stdout", "stderr"]:
        assert (EXTRACTED / "mixer/mixer" / command[key]).is_file()
log_bindings["protocol_storage"] = {
    "protocol_commands": len(p["commands"]), "storage_commands": len(s["commands"]),
    "all_commands_zero_exit": True,
    "scope": "Receipts lack per-log hashes; exact output bytes remain bound by verified ZIP and zip-manifest.json.",
}

tests = (foundation / "tests.log").read_text()
test_lines = tests.split("\n")
assert "Result: 697 passed, 2 skipped" in tests
assert f["status"] == "passed" and f["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
assert s["focused_tests_passed"] and s["source_unchanged"] and m["success"] and m["source_unchanged"]
assert p["selected_host_tests"] == {"total": 45, "failures": 0, "excluded": 0, "skipped": 0}
method_entries, completed, skipped = [], [], []
module = None
wire = []
for number, line in enumerate(test_lines, 1):
    match = re.match(r"([A-Z][A-Za-z0-9_.]+) \[test/", line)
    if match:
        module = match.group(1)
    if line.lstrip().startswith("* test"):
        row = {"line": number, "module": module, "message": line.split("HTTP2_WIRE_RECEIPT")[0].strip()}
        method_entries.append(row)
        if re.search(r"\([\d.]+ms\) \[L#\d+\]", line):
            completed.append(row)
        if "(skipped)" in line:
            skipped.append(row)
    if "HTTP2_WIRE_RECEIPT " in line:
        value = json.loads(line.split("HTTP2_WIRE_RECEIPT ", 1)[1])
        assert value["passed"] and value["cleanup"]["complete"]
        wire.append({"line": number, **value})
lifecycle_completed = [row for row in completed if re.search(r"\* test KOL0[1-9]", row["message"])]
assert len(lifecycle_completed) == 9
http2_completed = [row for row in completed if row["module"] == "MixerHosted.Billing.RawWebhookCaptureHTTP2Test"]
assert len(http2_completed) == 5 and len(wire) == 7
k07_completed = [row for row in completed if re.search(r"\* test K07[fgh] ", row["message"])]
assert len(k07_completed) == 3 and len(skipped) == 2
observations = []
for path in sorted((foundation / "identity-lifecycle").glob("*.json")):
    value = load(path)
    observations.append({"path": str(path.relative_to(EXTRACTED)), "sha256": digest(path.read_bytes()),
                         "case_id": value.get("case_id"), "cleanup": value.get("cleanup", value),
                         "cleanup_errors": value.get("cleanup_errors"), "observations": value.get("observations")})
assert len(observations) == 9
for row in observations:
    assert not row["cleanup_errors"]
    for key, value in row["cleanup"].items():
        if isinstance(value, bool):
            assert value
production_lines = (foundation / "release-test-exclusion.log").read_text().splitlines()
production_markers = [{"line": i + 1, "message": line} for i, line in enumerate(production_lines)
    if line.startswith("production_")]
assert any("production_transport_policy: passed; 4 production modules; test helpers absent; role inactive" in row["message"] for row in production_markers)
assert "invalid or missing hosted setting: MIXER_HOSTED_ROLE" in (foundation / "release-missing-config.log").read_text()
handshake_cleanup = load(foundation / "identity-metrics/handshake-cleanup.json")
crash_cleanup = load(foundation / "identity-metrics/crash-restart-cleanup.json")
assert handshake_cleanup["accepted"] == handshake_cleanup["closed"] == 5
assert handshake_cleanup["max_active"] == handshake_cleanup["closedBeforeReuse"] == 4
assert handshake_cleanup["localPortsClosedBeforeReuse"]
assert crash_cleanup["connections"] == 4
assert all(value for key, value in crash_cleanup.items() if isinstance(value, bool))
save("runtime-evidence.json", {
    "suite_result": {"passed": 697, "skipped": 2, "reported_failures": 0, "total_methods_in_result": 699},
    "suite_summary": [{"line": i + 1, "message": line} for i, line in enumerate(test_lines) if line.startswith(("Running ExUnit", "Finished in", "Result:"))],
    "skipped_methods": skipped, "lifecycle_completed_methods": lifecycle_completed,
    "http2_completed_methods": http2_completed, "http2_wire_cases": wire,
    "K07_f_g_h_completed": k07_completed, "lifecycle_observations": observations,
    "handshake_cleanup_observation": handshake_cleanup,
    "crash_restart_cleanup_observation": crash_cleanup,
    "production_policy_markers": production_markers,
    "lifecycle_limit": "Nine passing methods and named resource observations. Branch-specific observation booleans include false values; do not treat every field as a universal assertion or qualify deployed operation.",
})

job_lines = (ROOT / "job.log").read_text(encoding="utf-8-sig").split("\n")


def marker(needle):
    values = [(i + 1, line) for i, line in enumerate(job_lines) if needle in line]
    assert len(values) == 1, (needle, len(values))
    number, line = values[0]
    timestamp, message = line.split(" ", 1)
    return {"line": number, "timestamp": timestamp, "message": message}


def elapsed(first, last):
    parse = lambda row: datetime.datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
    return round((parse(last) - parse(first)).total_seconds(), 6)


checkout = marker("##[group]Run actions/checkout@v4")
node = marker("##[group]Run actions/setup-node@v4")
fetch = marker("##[group]Fetching the repository")
new_ref = marker("* [new ref]")
checkout_ref = marker("##[group]Checking out the ref")
switched = marker("Switched to a new branch 'main'")
suite_start = marker("##[group]Run python3 scripts/test-local.py")
suite_done = marker('{"status": "passed", "receipt":')
assert "--filter=blob:none" in "\n".join(job_lines)
assert "git config core.sparseCheckout true" in "\n".join(job_lines)
assert all(pattern in "\n".join(job_lines) for pattern in patterns)
terminations = [line for line in job_lines if "Terminate orphan process:" in line]
timing = {
    "checkout_action_start": checkout, "next_action_start": node,
    "checkout_action_upper_bound_seconds": elapsed(checkout, node),
    "fetch_start": fetch, "fetch_new_ref": new_ref, "fetch_observed_seconds": elapsed(fetch, new_ref),
    "worktree_checkout_start": checkout_ref, "worktree_switched_branch": switched,
    "worktree_checkout_observed_seconds": elapsed(checkout_ref, switched),
    "foundation_step_start": suite_start, "foundation_receipt_emitted": suite_done,
    "foundation_step_observed_seconds": elapsed(suite_start, suite_done),
    "configured_job_timeout_minutes": 15,
    "scope": "Single hosted Ubuntu runner observation. API lifecycle and individual action/setup times include scheduler/platform behavior; no future timing, cost, network transfer byte or latency guarantee.",
}
receipt_paths = sorted(str(path.relative_to(EXTRACTED)) for path in EXTRACTED.rglob("receipt.json"))
assert len(receipt_paths) == 4 and all("20261028" in path or path == "_temp/phoenix-foundation/receipt.json" for path in receipt_paths)
assert not any("/attempts/20261025" in entry["path"] for entry in zip_manifest["entries"])
run = load(ROOT / "run-metadata.json")
jobs = load(ROOT / "remote-metadata.json")["jobs"]["jobs"]
assert run["head_sha"] == SHA and run["status"] == "completed" and run["conclusion"] == "success"
assert len(jobs) == 1 and jobs[0]["id"] == 122998786324 and jobs[0]["conclusion"] == "success"
assert len(jobs[0]["steps"]) == 13 and all(step["conclusion"] == "success" for step in jobs[0]["steps"])
save("sparse-readset.json", {
    "source_revision": SHA, "workflow_sha256": digest(workflow_bytes),
    "exact_committed_workflow_matches_root_candidate": True,
    "workflow_added_lines": len(added), "workflow_deleted_lines": len(removed), "patterns": patterns,
    "selected_files": len(selected), "selected_logical_bytes": sum(row["bytes"] for row in selected.values()),
    "required_manifest_and_explicit_compile_driver_golden_readset_files": len(required),
    "required_readset_exactly_covered": True, "selected_manifest": selected,
    "observed_blob_filter": "blob:none", "observed_sparse_mode": "non-cone",
    "runner_checkout_bound_to_exact_commit": True,
    "retained_receipt_paths": receipt_paths, "historical_receipts_present": False,
    "limits": "Pinned tree/static readset plus successful runtime consumers and upload inventory; no comprehensive runner filesystem inventory. Applies to ordinary committed workflow only. Held UnitA workflow/readset and live dirty workflow are not accepted or mutated.",
})
collector = git("cat-file", "blob", SHA + ":hosted/scripts/test-identity-network.py").decode()
collector_ast = ast.parse(collector)
frozen = next(ast.literal_eval(node.value) for node in collector_ast.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "FROZEN_MANIFEST" for target in node.targets))
archived_rows = {row["path"]: {"bytes":row["bytes"], "sha256":row["sha256"]} for row in archive_manifest}
product = {path:archived_rows[path] for path in frozen}
assert product == frozen and len(product) == 177
assert digest(json.dumps(product,sort_keys=True,separators=(",", ":")).encode()) == "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e"
save("source-bindings.json", {"frozen_product_177_sha256": digest(json.dumps(product,sort_keys=True,separators=(",", ":")).encode()), "four_inputs_additional_to_frozen_product": {k:v for k,v in archived_rows.items() if k not in frozen},"source_revision": SHA, "source_tree": git("rev-parse", SHA + "^{tree}").decode().strip(),
    "git_version": git("--version").decode().strip(), "source_maps": bindings,
    "foundation_archive_matches_all_181_receipt_inputs": True,
    "source_unchanged_checks_recorded": {"foundation": "Collector sets passed only after before/after equality", "storage": s["source_unchanged"], "migration": m["source_unchanged"]},
    "migration_saved_inputs_match_manifest": True, "storage_manifest_receipt_hash_and_before_after_match": True})
save("log-bindings.json", log_bindings)
save("timing.json", timing)
summary = {
    "schema": 1, "status": "verified_exact_commit_ordinary_phoenix_host_ci_success",
    "reviewed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": SHA, "source_tree": git("rev-parse", SHA + "^{tree}").decode().strip(),
    "run_id": 40740023060, "job_id": 122998786324, "artifact_id": 12837969735,
    "artifact_sha256": digest((ROOT / "artifact.zip").read_bytes()),
    "artifact_zip_bytes": 868414, "artifact_files": len(zip_manifest["entries"]),
    "artifact_expanded_bytes": zip_manifest["expanded_bytes"],
    "suite_result": {"passed": 697, "skipped": 2, "reported_failures": 0},
    "source_bindings": bindings, "log_bindings": log_bindings, "timing": timing,
    "preceding_host_results": {"protocol": p["selected_host_tests"], "storage": "24 passed", "migration": load(migration.parent / "result.json")},
    "cleanup": {"foundation": f["cleanup"], "protocol": p["cleanup"], "storage": s["cleanup"], "migration": m["cleanup"],
        "nine_lifecycle_resource_cleanup_observations": True, "seven_http2_wire_cases_cleanup_complete": True,
        "runner_orphan_termination_events_logged": terminations,
        "limit": "Exact collector/fixture resource receipts; no blanket inventory or guarantee that every possible runner resource was absent."},
    "historical_receipts_present": False,
    "limits": [
        "Two skipped actual production public-DNS/TLS Linux-network methods remain skipped, not passes. Loopback/synthetic tests do not qualify configured providers, Neon, Cloudflare or deployment operation.",
        "Applies to exact ordinary committed workflow and host suite only. No held UnitA/frozen workflow or product acceptance; live dirty workflow was not read, staged or changed.",
        "No CI rerun/dispatch, product runtime, native runtime, UI, capture, local database/container, process inventory or writes outside this packet.",
        "No canonical product, Git/index/metadata or memory mutations. Source/metadata reads used exact committed objects.",
        "Connector versions not exposed; review Python/Git versions and command output hashes are retained.",
        "No physical device, customer, store, provider or GA acceptance is established.",
    ],
    "review_python": sys.version,
}
save("review.json", summary)
print(json.dumps({"status": summary["status"], "source_revision": SHA,
    "suite_result": summary["suite_result"], "foundation_source_files": len(archive_sources),
    "required_sparse_readset_files": len(required), "historical_receipts_present": False,
    "checkout_action_upper_bound_seconds": timing["checkout_action_upper_bound_seconds"]}, indent=2))
