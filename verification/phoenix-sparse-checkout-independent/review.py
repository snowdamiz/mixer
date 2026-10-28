#!/usr/bin/env python3
"""Independent source-only sparse checkout audit; never executes product sources."""
from __future__ import annotations

import ast
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "verification/phoenix-sparse-checkout-candidate"
REVISION = "c450ed48d14df1f2cf1140dd3f8807890a8fe9d0"
EXPECTED_PATCH = "08d4c36835d46199c3ac9852356060f81045bd525616d91b3d2dd717eec5cd44"
PROTECTED = {
    ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
    "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}
START = time.monotonic()
COMMANDS = []
ENV = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0",
           GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1")


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(name: str, value) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(*args: str, stdin: bytes = b"") -> bytes:
    remaining = 50 - (time.monotonic() - START)
    if remaining <= 0:
        raise TimeoutError("whole audit exceeded its 50-second source-only budget")
    argv = ["git", "--no-optional-locks", *args]
    before = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, env=ENV, input=stdin,
                            capture_output=True, timeout=remaining, check=False)
    COMMANDS.append({"argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
                     "elapsed_seconds": round(time.monotonic() - before, 6),
                     "stdin_bytes": len(stdin), "stdin_sha256": sha(stdin),
                     "stdout_bytes": len(result.stdout), "stdout_sha256": sha(result.stdout),
                     "stderr": result.stderr.decode(errors="replace"),
                     "timeout_seconds": round(remaining, 3)})
    if result.returncode:
        raise RuntimeError(f"Read-only Git command failed: {argv}")
    return result.stdout


def fixed_strings(source: bytes, assignments: tuple[str, ...]) -> dict[str, list[str]]:
    """Decode literal data from Python AST, without importing or evaluating source."""
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in assignments:
                result[name] = ast.literal_eval(node.value)
    return result


def normalize_relative(parent: str, relative: str) -> str:
    parts = list(PurePosixPath(parent).parts)
    for part in PurePosixPath(relative).parts:
        if part == "..":
            parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


protected_before = {p: sha((ROOT / p).read_bytes()) for p in PROTECTED}
assert protected_before == PROTECTED, protected_before
manifest_bytes = (CANDIDATE / "packet-manifest.sha256").read_bytes()
packet_members = []
for line in manifest_bytes.decode().splitlines():
    digest, name = line.split("  ", 1)
    assert not name.startswith("/") and ".." not in PurePosixPath(name).parts
    actual = sha((CANDIDATE / name).read_bytes())
    assert actual == digest, name
    packet_members.append({"path": name, "sha256": actual})
assert len(packet_members) == 29
patch = (CANDIDATE / "workflow.patch").read_bytes()
assert sha(patch) == EXPECTED_PATCH
assert patch == (CANDIDATE / "current-head/workflow.patch").read_bytes()
patterns = (CANDIDATE / "sparse-patterns.txt").read_bytes()
assert patterns == (CANDIDATE / "current-head/sparse-patterns.txt").read_bytes()
workflow = git("show", REVISION + ":.github/workflows/hosted.yml")
candidate = (CANDIDATE / "hosted.yml.candidate").read_bytes()
assert workflow == (CANDIDATE / "hosted.yml.before").read_bytes()
assert workflow == (CANDIDATE / "current-head/hosted.yml.before").read_bytes()
assert candidate == (CANDIDATE / "current-head/hosted.yml.candidate").read_bytes()
inserted = (b"        with:\n          sparse-checkout-cone-mode: false\n          sparse-checkout: |\n"
            + b"".join(b"            " + line + b"\n" for line in patterns.splitlines()))
anchor = b"      - uses: actions/checkout@v4\n"
assert workflow.count(anchor) == 1
assert candidate == workflow.replace(anchor, anchor + inserted, 1)
assert candidate.replace(inserted, b"", 1) == workflow
derived_patch = "".join(difflib.unified_diff(workflow.decode().splitlines(True),
                                          candidate.decode().splitlines(True),
                                          fromfile="a/.github/workflows/hosted.yml",
                                          tofile="b/.github/workflows/hosted.yml")).encode()
assert derived_patch == patch
assert len(inserted.splitlines()) == 19
tree = git("rev-parse", REVISION + "^{tree}").decode().strip()
observed_head = git("rev-parse", "HEAD").decode().strip()
version = git("--version").decode().strip()
metadata = git("ls-tree", "-r", "-l", "-z", REVISION)
entries = {}
for entry in metadata.split(b"\0"):
    if not entry:
        continue
    prefix, path = entry.split(b"\t", 1)
    mode, kind, oid, size = prefix.split()
    assert kind == b"blob", (kind, path)
    entries[path.decode()] = {"path": path.decode(), "mode": mode.decode(), "git_blob": oid.decode(),
                              "bytes": int(size)}
names = b"".join(p.encode() + b"\0" for p in entries)
selected_raw = git("sparse-checkout", "check-rules", "--no-cone", "-z", "--rules-file",
                   str(CANDIDATE / "sparse-patterns.txt"), stdin=names)
selected = sorted(p.decode() for p in selected_raw.split(b"\0") if p)
manual = sorted(p for p in entries if any(p.startswith(rule[1:]) if rule.endswith("/")
                                        else p == rule[1:] for rule in patterns.decode().splitlines()))
assert selected == manual
assert len(selected) == 194 and sum(entries[p]["bytes"] for p in selected) == 4723119
assert all(entries[p]["mode"] in ("100644", "100755") for p in selected)
batch = git("cat-file", "--batch", stdin=b"".join(entries[p]["git_blob"].encode() + b"\n" for p in selected))
sources = {}
offset = 0
for p in selected:
    end = batch.index(b"\n", offset)
    oid, kind, size_text = batch[offset:end].split()
    size = int(size_text)
    data = batch[end + 1:end + 1 + size]
    assert kind == b"blob" and oid.decode() == entries[p]["git_blob"] and size == entries[p]["bytes"]
    assert hashlib.sha1(b"blob " + str(size).encode() + b"\0" + data).hexdigest() == oid.decode()
    assert batch[end + 1 + size:end + 2 + size] == b"\n"
    sources[p] = data
    entries[p]["sha256"] = sha(data)
    offset = end + 2 + size
assert offset == len(batch)
hosted = sorted(p for p in entries if p.startswith("hosted/"))
assert len(hosted) == 179 and set(hosted) <= set(selected)
assert not any({"deps", "_build", "__pycache__", "cover"} & set(PurePosixPath(p).parts[1:])
               or PurePosixPath(p).name == "erl_crash.dump" for p in hosted)
shared = ["services/protocol/testdata/signed-release-v3.json", "services/protocol/testdata/release-v3-cases.json"]
tar_inputs = {p: entries[p]["sha256"] for p in sorted(hosted + shared)}
assert len(tar_inputs) == 181
assert tar_inputs == json.loads((CANDIDATE / "current-head/test-local-source-inputs.json").read_text())

protocol_runner = "verification/hosted-browser-auth-protocol/run.py"
protocol_lists = fixed_strings(sources[protocol_runner], ("SOURCES", "TESTS", "EXTRA"))
protocol_files = sum(protocol_lists.values(), [])
assert len(protocol_files) == 14 and set(protocol_files) <= set(selected)

storage_runner = "hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py"
storage_files = ["hosted/" + p for p in [
    "lib/mixer_hosted/browser_auth/storage_schema.ex", "lib/mixer_hosted/browser_auth/vault.ex",
    "lib/mixer_hosted/browser_auth/stored_snapshot.ex", "test/mixer_hosted/browser_auth/storage_fixture.exs",
    "test/mixer_hosted/browser_auth/storage_spec.exs", "mix.exs", "mix.lock",
    "priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs",
    "priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs",
    "priv/repo/migrations/20261025000007_add_browser_sessions.exs",
]] + [storage_runner, "docs/hosted-browser-session-storage.md"]
assert len(storage_files) == 13 and set(storage_files) <= set(selected)
migration_runner = "hosted/test/mixer_hosted/browser_auth/run_migration_fixture.py"
migration_lists = fixed_strings(sources[migration_runner], ("MIGRATIONS", "DEPS", "SPEC"))
assert len(migration_lists["MIGRATIONS"]) == 10
assert sorted("hosted/priv/repo/migrations/" + p for p in migration_lists["MIGRATIONS"]) == sorted(
    p for p in hosted if p.startswith("hosted/priv/repo/migrations/"))

closure = set()
edges = {}
queue = ["console/src/api/workspace-client.ts"]
while queue:
    p = queue.pop()
    if p in closure:
        continue
    closure.add(p)
    text = sources[p].decode()
    imports = re.findall(r'(?:import|export)\s+(?:type\s+)?[^;\n]*?\bfrom\s+[\"\']([^\"\']+)', text)
    assert not re.search(r'\b(?:import|require)\s*\(', text)
    resolved = set()
    for path in imports:
        assert path.startswith(".") and path.endswith(".js"), (p, path)
        target = normalize_relative(str(PurePosixPath(p).parent), path[:-3] + ".ts")
        assert target in selected, (p, target)
        resolved.add(target)
        queue.append(target)
    edges[p] = sorted(resolved)
assert closure == {"console/src/api/workspace-client.ts", "console/src/api/workspace-transport.ts",
                   "console/src/domain/workspace-directory.ts"}
lock = json.loads(sources["console/package-lock.json"])
local_packages = [p for p, value in lock["packages"].items() if value.get("link") or
                  str(value.get("resolved", "")).startswith(("file:", "link:", "workspace:"))]
assert not local_packages
assert not ({".npmrc", "console/.npmrc", "npm-shrinkwrap.json", "console/npm-shrinkwrap.json"} & entries.keys())

relations = {}
for major in (16, 17):
    p = f"hosted/priv/browser_auth/relation_surface_v1_pg{major}.json"
    manifest = json.loads(sources[p])
    def find_maps(value):
        if isinstance(value, dict):
            if value and all(isinstance(k, str) and isinstance(v, str) and len(v) == 64 for k, v in value.items()):
                yield value
            for child in value.values():
                yield from find_maps(child)
        elif isinstance(value, list):
            for child in value:
                yield from find_maps(child)
    path_hashes = {}
    for mapping in find_maps(manifest):
        path_hashes.update({k:v for k,v in mapping.items() if k.startswith("hosted/")})
    assert len(path_hashes) == 29, (major, len(path_hashes))
    tracked = {p:d for p,d in path_hashes.items() if p in entries}
    installed = {p:d for p,d in path_hashes.items() if p not in entries}
    assert len(tracked) == 13 and len(installed) == 16
    assert all(p.startswith("hosted/deps/oban/") for p in installed)
    assert all(entries[p]["sha256"] == d and p in selected for p,d in tracked.items())
    relations[str(major)] = {"tracked_source_bindings": tracked, "dependency_install_bindings": installed}

catalog_path = "hosted/lib/mixer_hosted/browser_auth/catalog_manifest_v2.ex"
catalog_pins = dict(re.findall(r'"([^"/]+\.ex)"\s*=>\s*"([0-9a-f]{64})"', sources[catalog_path].decode()))
assert len(catalog_pins) == 4
for name, expected in catalog_pins.items():
    assert entries["hosted/lib/mixer_hosted/browser_auth/" + name]["sha256"] == expected
for major, value in relations.items():
    assert relations["16"] == value

goldens = ["verification/hosted-customer-artifact-event/golden_event.hex",
           "verification/hosted-customer-artifact-event/golden_hashes.txt"]
driver = "verification/hosted-customer-workspace-http-integration/node-client-driver.mjs"
derived = set(hosted + shared + protocol_files + storage_files + list(closure) + goldens +
              [driver, "console/package.json", "console/package-lock.json"])
assert derived == set(selected), (derived - set(selected), set(selected) - derived)
assert {p:entries[p]["sha256"] for p in selected} == {
    p["path"]:p["sha256"] for p in json.loads((CANDIDATE / "current-head/selected-files.json").read_text())}

read_pattern = re.compile(r'File\.(?:read|read!|stream|open|ls|exists|regular|dir|stat)|Path\.(?:expand|join|wildcard)|Code\.(?:require_file|compile_file|eval_file)|:file\.|System\.cmd|read_bytes|read_text|rglob|tarfile|manifest|source_paths|SOURCES|TESTS|EXTRA|MIGRATIONS|import_config')
read_points = []
for p, data in sources.items():
    if not p.endswith((".ex", ".exs", ".py", ".ts", ".mjs")):
        continue
    # The two network collectors are bound by the full-hosted manifest/tar, but
    # neither is invoked by the pinned workflow or the default test-local script.
    inactive = p in {"hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py"}
    for line, text in enumerate(data.decode().splitlines(), 1):
        if read_pattern.search(text):
            read_points.append({"path": p, "line": line, "text": text,
                                "execution_class": "manifest_and_tar_input_only" if inactive else "reviewed_source_read_or_output_site"})

controls = {
    "omitted_historical_attempts": ["verification/hosted-browser-auth-protocol/attempts/old/tests.stdout",
                                    "verification/hosted-browser-session-storage/attempts/old/receipt.json"],
    "omitted_unrelated_or_future_expansion": ["console/src/api/browser-session-client.ts", "console/tsconfig.json",
        "docs/hosted-browser-callback-ci.md", "docs/hosted-browser-callback-storage.md",
        "verification/hosted-browser-callback-storage/receipt.json", "somewhere/hosted/file.ex"],
}
control_input = b"".join(p.encode() + b"\0" for paths in controls.values() for p in paths)
assert git("sparse-checkout", "check-rules", "--no-cone", "-z", "--rules-file",
           str(CANDIDATE / "sparse-patterns.txt"), stdin=control_input) == b""
protected_after = {p: sha((ROOT / p).read_bytes()) for p in PROTECTED}
assert protected_after == protected_before

span_map = {
    ".github/workflows/hosted.yml": [(1, 86)],
    "hosted/scripts/test-local.py": [(79, 117), (137, 192), (237, 244), (259, 270)],
    protocol_runner: [(15, 33), (40, 54), (75, 81), (85, 103)],
    storage_runner: [(16, 66), (117, 123), (135, 150)],
    migration_runner: [(16, 41), (90, 112), (123, 143)],
    "hosted/mix.exs": [(4, 41)], "hosted/.formatter.exs": [(1, 3)],
    "hosted/config/config.exs": [(1, 13)], "hosted/config/runtime.exs": [(1, 12)],
    "hosted/.tool-versions": [(1, 2)],
    "hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex": [(1, 29)],
    catalog_path: [(11, 24)],
    "hosted/lib/mixer_hosted/browser_auth/activation_preparation_schema.ex": [(24, 26)],
    "hosted/test/mixer_hosted/audit/customer_artifact_event_test.exs": [(22, 22), (173, 195)],
    "hosted/test/mixer_hosted/protocol/artifact_admission_test.exs": [(1, 20), (94, 96)],
    "hosted/test/mixer_hosted/protocol/artifact_cbor_test.exs": [(6, 6), (76, 80)],
    "hosted/test/support/identity_tls_fixture.ex": [(8, 20), (110, 125)],
    "hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs": [(35, 49)],
    "hosted/test/mixer_hosted_web/customer_workspace_http_integration_test.exs": [(868, 883)],
    "console/src/api/workspace-client.ts": [(1, 7)],
    "console/src/api/workspace-transport.ts": [(1, 1)],
    "console/src/domain/workspace-directory.ts": [(1, 14)],
    "console/package.json": [(1, 25)], driver: [(1, 3)],
}
spans = []
for p, ranges in span_map.items():
    data = workflow if p == ".github/workflows/hosted.yml" else sources[p]
    lines = data.decode().splitlines()
    for start, end in ranges:
        spans.append({"path":p, "revision":REVISION, "file_sha256":sha(data), "start":start,
                      "end":min(end,len(lines)), "lines":lines[start-1:end]})
hold_evidence = []
for rel in ["verification/console-session-and-checkout-root-review/identity-network-implementation-selection.json",
            "verification/console-session-and-checkout-root-review/identity-network-source-acceptance.json"]:
    data = (ROOT / rel).read_bytes()
    value = json.loads(data)
    hold_evidence.append({"path":rel, "sha256":sha(data), "status":value["status"],
                          "scope":value.get("scope"),
                          "runtime_isolation_or_product_tests_accepted":value.get("runtime_isolation_or_product_tests_accepted"),
                          "native_UI_device_local_custody_UnitA_and_GA_holds_unchanged":value.get("native_UI_device_local_custody_UnitA_and_GA_holds_unchanged"),
                          "protected_dirty_files_excluded":value.get("protected_dirty_files_excluded")})
assert hold_evidence[0]["scope"].endswith("no local custody or UnitA acceptance.")
assert hold_evidence[1]["runtime_isolation_or_product_tests_accepted"] is False
assert hold_evidence[1]["native_UI_device_local_custody_UnitA_and_GA_holds_unchanged"] is True
for rel, start, end in [("PLAN.md", 12, 20), ("STATUS.md", 1, 9)]:
    data = (ROOT / rel).read_bytes()
    spans.append({"path":rel,"file_sha256":sha(data),"basis":"observed live checkpoint, not candidate source",
                  "start":start,"end":end,"lines":data.decode().splitlines()[start-1:end]})
write_json("source-spans.json", spans)
write_json("held-scope-evidence.json", hold_evidence)
write_json("selected-files.json", [entries[p] for p in selected])
write_json("test-local-manifest-and-tar.json", tar_inputs)
write_json("source-read-points.json", read_points)
write_json("packet-custody.json", {"manifest_sha256":sha(manifest_bytes), "members":packet_members})
write_json("readset.json", {"whole_hosted":hosted, "shared_protocol":shared, "protocol_collector":protocol_files,
    "storage_collector":storage_files, "migration_literals":migration_lists, "typescript_import_edges":edges,
    "typescript_package_install_inputs":["console/package.json", "console/package-lock.json"],
    "driver":driver, "goldens":goldens, "relation_manifests":relations, "browser_catalog_source_pins":catalog_pins,
    "generated_inputs":["hosted/deps from mix deps.get --check-locked", "hosted/_build from unchanged compilation",
       "console/node_modules from npm ci --ignore-scripts --no-audit --no-fund", "$RUNNER_TEMP/workspace-client from explicit tsc and cp"],
    "outputs":["verification/hosted-browser-auth-protocol/attempts/<stamp>/ and receipt.json",
       "verification/hosted-browser-session-storage/attempts/<stamp>/ and latest.json",
       "$RUNNER_TEMP/browser-migrations/<stamp>/", "$RUNNER_TEMP/phoenix-foundation/"], "exclusion_controls":controls})
write_json("commands.json", {"invocation":f"python3 {Path(__file__).relative_to(ROOT)}",
    "environment_overrides":{k:ENV[k] for k in ("GIT_NO_LAZY_FETCH", "GIT_TERMINAL_PROMPT", "GIT_OPTIONAL_LOCKS", "GIT_NO_REPLACE_OBJECTS")},
    "commands":COMMANDS,
    "pre_audit_discovery_limitation":"Initial source discovery included git status --short without disabling optional locks; it may refresh index stat metadata. No explicit index/Git mutation was issued. All commands in this audit disable optional locks and lazy fetching."})
write_json("receipt.json", {"status":"passed_source_only", "recorded_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision":REVISION, "source_git_tree":tree, "observed_head":observed_head,
    "review_script_sha256":sha(Path(__file__).read_bytes()), "workflow_sha256":sha(workflow),
    "candidate_workflow_sha256":sha(candidate), "patch_sha256":sha(patch), "sparse_patterns_sha256":sha(patterns),
    "candidate_manifest_sha256":sha(manifest_bytes), "candidate_manifest_members":len(packet_members),
    "tools":{"git":version,"python":sys.version}, "elapsed_seconds":round(time.monotonic()-START,6),
    "source_only_budget_seconds":50, "all_subprocesses_readonly_git":True,
    "selection":{"files":len(selected),"logical_bytes":sum(entries[p]["bytes"] for p in selected),
       "whole_hosted_files":len(hosted),"manifest_and_tar_files":len(tar_inputs),
       "tracked_files":len(entries),"tracked_logical_bytes":sum(p["bytes"] for p in entries.values()),
       "basis":"Pinned Git tree blob metadata; logical per-path bytes, not pack, transfer, disk, elapsed checkout or CI result"},
    "checks":{"candidate_packet_hashes_match":True,"exact_committed_workflow_reconstructed_after_input_removal":True,
       "only_19_checkout_input_lines_added":True,"all_other_workflow_bytes_unchanged":True,
       "canonical_git_sparse_rules_match_independent_selection":True,"selected_blob_id_and_sha256_validated_in_memory":True,
       "independently_derived_readset_equals_selection":True,"test_local_manifest_and_tar_members_identical":True,
       "tracked_pg16_and_pg17_relation_bindings_match":True,"browser_catalog_source_pins_match":True,
       "no_local_package_or_repo_npmrc_input":True,"existing_UnitA_and_local_custody_holds_preserved":True},
    "protected_live_files":{"before":protected_before,"after":protected_after,"preserved":True,"contents_not_copied":True},
    "cleanup":{"source_materialization_created":False,"native_capture_runtime_or_database_started":False,
       "network_dependency_install_or_workflow_run":False,"owned_output_directory_only":True},
    "limits":["Source review only; actual GitHub checkout/action behavior and Phoenix CI remain pending",
       "No measured speed, fetch, transfer, pack or allocation improvement",
       "actions/checkout@v4 remains floating as in baseline; remote action implementation was not inspected",
       "Held Unit A work and dirty live workflow/store are outside the committed candidate qualification",
       "New external reads, TypeScript imports or workflow steps require readset review",
       "No native, physical-phone, provider, production, customer or GA qualification"]})
print(json.dumps({"status":"passed_source_only", "files":len(selected), "logical_bytes":sum(entries[p]["bytes"] for p in selected),
                  "elapsed_seconds":round(time.monotonic()-START,3), "output":str(OUT / "receipt.json")}))
