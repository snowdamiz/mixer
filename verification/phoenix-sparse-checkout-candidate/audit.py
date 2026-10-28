#!/usr/bin/env python3
"""Source-only checkout candidate; never modify the index or live workflow.

Reads committed blobs via Git, validates patterns with Git's read-only rule
matcher, and materializes only the selected source files inside this packet.
Does not run any hosted, npm, compiler, database, Docker, or native commands.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time


PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
ANALYSIS_BASE_REVISION = "756695fb9b0f6ec85d978202e2b3c586aa3db16f"
REVISION = sys.argv[1] if len(sys.argv) == 2 else ANALYSIS_BASE_REVISION
assert re.fullmatch(r"[0-9a-f]{40}", REVISION), "Use an explicit pinned commit"
HERE = PACKET if REVISION == ANALYSIS_BASE_REVISION else PACKET / "current-head"
HERE.mkdir(exist_ok=True)
WORKFLOW = ".github/workflows/hosted.yml"
EXPECTED_WORKFLOW_SHA256 = "5b242f70831c135d8b18845b992c78e8c85797ec45565e9b9e64cdd19d2edbf9"
EXPECTED_PROTECTED_SHA256 = "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57"
COMMANDS: list[dict] = []
STARTED = time.monotonic()
GIT_ENV_OVERRIDES = {"GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0",
                     "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(argv: list[str], data: bytes | None = None) -> bytes:
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=ROOT, env={**os.environ, **GIT_ENV_OVERRIDES},
                            input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=50, check=False)
    COMMANDS.append({"argv": argv, "cwd": str(ROOT), "started_at_utc": started,
                     "timeout_seconds": 50, "exit_code": result.returncode,
                     "stdin_bytes": len(data) if data else 0,
                     "stdin_sha256": sha(data) if data is not None else None,
                     "stdout_bytes": len(result.stdout), "stdout_sha256": sha(result.stdout),
                     "stderr": result.stderr.decode(errors="replace")})
    if result.returncode:
        raise RuntimeError(f"Command failed: {argv}: {result.stderr.decode(errors='replace')}")
    return result.stdout


def dump(name: str, value: object) -> None:
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def block_constants(path: str, names: tuple[str, ...], blobs: dict[str, bytes]) -> list[str]:
    """Read literal source lists, without importing or executing their runner."""
    tree = ast.parse(blobs[path].decode(), filename=path)
    assignments = {node.targets[0].id: node.value for node in tree.body
                   if isinstance(node, ast.Assign) and len(node.targets) == 1
                   and isinstance(node.targets[0], ast.Name)}
    return [value for name in names for value in ast.literal_eval(assignments[name])]


def main() -> None:
    protected_before = sha((ROOT / WORKFLOW).read_bytes())
    assert protected_before == EXPECTED_PROTECTED_SHA256, "Protected workflow changed; root must review"
    observed_head = run(["git", "rev-parse", "HEAD"]).decode().strip()
    head = run(["git", "rev-parse", f"{REVISION}^{{commit}}"]).decode().strip()
    assert head == REVISION
    tree_oid = run(["git", "rev-parse", f"{REVISION}^{{tree}}"]).decode().strip()
    git_version = run(["git", "--version"]).decode().strip()
    metadata = run(["git", "ls-tree", "-r", "-l", "-z", REVISION])
    entries = {}
    for raw in metadata.split(b"\0"):
        if not raw:
            continue
        header, name = raw.split(b"\t", 1)
        mode, kind, oid, size = header.decode().split()
        entries[name.decode()] = {"mode": mode, "kind": kind, "git_blob": oid,
                                   "bytes": int(size) if size != "-" else None}
    assert all(v["kind"] == "blob" for v in entries.values()), "Unexpected non-blob tracked entry"
    baseline = run(["git", "show", f"{REVISION}:{WORKFLOW}"])
    assert sha(baseline) == EXPECTED_WORKFLOW_SHA256
    (HERE / "hosted.yml.before").write_bytes(baseline)

    # Complete hosted/ is deliberate: test-local.py's manifest() and source tar
    # bind every file under this directory, including scripts not invoked by CI.
    extra_paths = [
        "AGENTS.md", "THIRD_PARTY.yml",
        "docs/hosted-browser-auth-protocol.md",
        "docs/hosted-browser-session-storage.md",
        "services/protocol/testdata/signed-release-v3.json",
        "services/protocol/testdata/release-v3-cases.json",
        "console/package.json", "console/package-lock.json",
        "console/src/api/workspace-client.ts",
        "console/src/api/workspace-transport.ts",
        "console/src/domain/workspace-directory.ts",
        "verification/hosted-browser-auth-protocol/run.py",
        "verification/hosted-customer-workspace-http-integration/node-client-driver.mjs",
        "verification/hosted-customer-artifact-event/golden_event.hex",
        "verification/hosted-customer-artifact-event/golden_hashes.txt",
    ]
    patterns = ["/hosted/"] + ["/" + name for name in extra_paths]
    pattern_bytes = ("\n".join(patterns) + "\n").encode()
    patterns_path = HERE / "sparse-patterns.txt"
    patterns_path.write_bytes(pattern_bytes)
    all_paths = sorted(entries)
    selected_output = run(["git", "sparse-checkout", "check-rules", "--no-cone", "-z",
                           "--rules-file", str(patterns_path)],
                          b"".join(name.encode() + b"\0" for name in all_paths))
    selected = selected_output.decode().rstrip("\0").split("\0")
    expected = sorted([name for name in all_paths if name.startswith("hosted/")] + extra_paths)
    assert selected == expected, "Git sparse-rule selection differs from exact proposed readset"
    assert all(entries[name]["mode"] in {"100644", "100755"} for name in selected)

    # Read bounded selected content only; the tracked-tree byte total is taken
    # entirely from Git's object metadata above, never from global disk scans.
    total_selected = sum(entries[name]["bytes"] for name in selected)
    assert total_selected < 8 * 1024 * 1024, "Selected source grew beyond bounded review budget"
    oids = list(dict.fromkeys(entries[name]["git_blob"] for name in selected))
    batch = run(["git", "cat-file", "--batch"], ("\n".join(oids) + "\n").encode())
    by_oid = {}
    offset = 0
    for expected_oid in oids:
        end = batch.index(b"\n", offset)
        oid, kind, size = batch[offset:end].decode().split()
        assert oid == expected_oid and kind == "blob"
        offset = end + 1
        data = batch[offset:offset + int(size)]
        assert len(data) == int(size) and batch[offset + int(size):offset + int(size) + 1] == b"\n"
        assert hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() == oid
        by_oid[oid] = data
        offset += int(size) + 1
    assert offset == len(batch)
    blobs = {name: by_oid[entries[name]["git_blob"]] for name in selected}
    source_root = HERE / "selected-tree"
    source_root.mkdir(exist_ok=True)
    for name, data in blobs.items():
        target = source_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(int(entries[name]["mode"], 8) & 0o777)
        assert sha(target.read_bytes()) == sha(data)
    assert sorted(str(path.relative_to(source_root)) for path in source_root.rglob("*")
                  if path.is_file()) == selected

    # The only workflow mutation is insertion of checkout inputs. Removing this
    # exact insertion must reconstruct every baseline byte, including commands,
    # action refs, env, timeout, artifact selection, and dependency versions.
    marker = b"      - uses: actions/checkout@v4\n"
    assert baseline.count(marker) == 1
    insertion = ("        with:\n          sparse-checkout-cone-mode: false\n"
                 "          sparse-checkout: |\n" +
                 "".join("            " + pattern + "\n" for pattern in patterns)).encode()
    candidate = baseline.replace(marker, marker + insertion, 1)
    assert candidate.replace(marker + insertion, marker, 1) == baseline
    assert candidate.count(b"      - uses:") == baseline.count(b"      - uses:")
    assert candidate.count(b"      - name:") == baseline.count(b"      - name:")
    (HERE / "hosted.yml.candidate").write_bytes(candidate)
    patch = "".join(difflib.unified_diff(baseline.decode().splitlines(keepends=True),
                                        candidate.decode().splitlines(keepends=True),
                                        fromfile="a/" + WORKFLOW, tofile="b/" + WORKFLOW))
    (HERE / "workflow.patch").write_text(patch)

    protocol_runner = "verification/hosted-browser-auth-protocol/run.py"
    protocol_paths = block_constants(protocol_runner, ("SOURCES", "TESTS", "EXTRA"), blobs)
    assert set(protocol_paths) <= set(selected)
    storage_runner = "hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py"
    migration_runner = "hosted/test/mixer_hosted/browser_auth/run_migration_fixture.py"
    assert 'REPO / "docs/hosted-browser-session-storage.md"' in blobs[storage_runner].decode()
    migration_names = block_constants(migration_runner, ("MIGRATIONS",), blobs)
    assert sorted(migration_names) == sorted(PurePosixPath(name).name for name in selected
                                            if name.startswith("hosted/priv/repo/migrations/"))
    test_local = blobs["hosted/scripts/test-local.py"].decode()
    assert 'for p in sorted(root.rglob("*"))' in test_local
    assert 'not {"_build", "deps", "__pycache__", "cover"}.intersection' in test_local
    assert 'for name in ("signed-release-v3.json", "release-v3-cases.json")' in test_local
    assert 'for name in before:' in test_local and 'recursive=False' in test_local
    # Reproduce this harness's tracked clean-source manifest selection, without
    # importing it or executing any build/test code. Generated _build/deps are
    # installed later by unchanged commands and are excluded by its predicate.
    excluded = {"_build", "deps", "__pycache__", "cover"}
    source_tar_names = sorted(name for name in selected if name.startswith("hosted/")
                              and PurePosixPath(name).name != "erl_crash.dump"
                              and not excluded.intersection(PurePosixPath(name).parts[1:]))
    source_tar_names += ["services/protocol/testdata/" + name for name in
                         ("signed-release-v3.json", "release-v3-cases.json")]
    source_inputs = {name: sha(blobs[name]) for name in source_tar_names}
    materialized_inputs = {name: sha((source_root / name).read_bytes()) for name in source_tar_names}
    assert source_inputs == materialized_inputs
    dump("test-local-source-inputs.json", source_inputs)

    # Determine relative TypeScript source imports and reexports from the three
    # statically inspected sources. Any new package/dynamic import requires
    # explicit re-audit; no TypeScript compiler or node package is executed.
    ts_root = "console/src/api/workspace-client.ts"
    pending = [ts_root]
    ts_edges = {}
    ts_closure = set()
    while pending:
        name = pending.pop()
        if name in ts_closure:
            continue
        ts_closure.add(name)
        source = blobs[name].decode()
        assert not re.search(r"\bimport\s*\(", source), "Dynamic import requires review"
        imports = re.findall(r"\bfrom\s+[\"']([^\"']+)[\"']", source)
        targets = []
        for module in imports:
            assert module.startswith("."), "New package import requires review"
            raw = PurePosixPath(name).parent / module
            parts = []
            for part in raw.parts:
                if part == "..":
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            target = str(PurePosixPath(*parts).with_suffix(".ts"))
            assert target in blobs, (name, target)
            targets.append(target)
            pending.append(target)
        ts_edges[name] = sorted(set(targets))
    assert ts_closure == {ts_root, "console/src/api/workspace-transport.ts",
                          "console/src/domain/workspace-directory.ts"}
    package = json.loads(blobs["console/package.json"])
    lock = json.loads(blobs["console/package-lock.json"])
    assert package["devDependencies"]["typescript"] == "5.9.3"
    assert lock["packages"]["node_modules/typescript"]["version"] == "5.9.3"
    assert package["dependencies"] == lock["packages"][""]["dependencies"]
    assert package["devDependencies"] == lock["packages"][""]["devDependencies"]
    assert not any(value.get("link") or str(value.get("resolved", "")).startswith("file:")
                   for value in lock["packages"].values())
    npm_configs = [name for name in all_paths if name in {".npmrc", "console/.npmrc"}]
    assert not npm_configs, "New npm config requires explicit checkout inclusion review"

    relation_manifests = {}
    for major in (16, 17):
        name = f"hosted/priv/browser_auth/relation_surface_v1_pg{major}.json"
        bindings = json.loads(blobs[name])["source_bindings"]
        tracked_bindings, generated_bindings = {}, {}
        for path, digest in bindings.items():
            if path in entries:
                assert path in blobs and sha(blobs[path]) == digest
                tracked_bindings[path] = digest
            else:
                assert path.startswith("hosted/deps/oban/"), path
                generated_bindings[path] = digest
        relation_manifests[str(major)] = {"tracked_source_bindings": tracked_bindings,
                                         "dependency_sources_after_mix_deps_get": generated_bindings}
    assert relation_manifests["16"] == relation_manifests["17"]

    probes = ["verification/hosted-browser-auth-protocol/attempts/old/tests.stdout",
              "verification/hosted-browser-session-storage/attempts/old/receipt.json",
              "verification/hosted-customer-artifact-event/run-1/receipt.json",
              "verification/hosted-customer-artifact-event/oracle.py",
              "console/src/api/browser-session-client.ts", "console/tsconfig.json",
              "docs/nested/hosted-browser-auth-protocol.md", "engine/raw-compiler.bin",
              "nested/hosted/lib/x.ex", "nested/AGENTS.md"]
    negative_output = run(["git", "sparse-checkout", "check-rules", "--no-cone", "-z",
                           "--rules-file", str(patterns_path)],
                          b"".join(name.encode() + b"\0" for name in probes))
    assert negative_output == b""
    missing_controls = {}
    for name in extra_paths:
        mutant = [pattern for pattern in patterns if pattern != "/" + name]
        mutant_path = HERE / "control-rules.txt"
        mutant_path.write_text("\n".join(mutant) + "\n")
        result = run(["git", "sparse-checkout", "check-rules", "--no-cone", "-z",
                      "--rules-file", str(mutant_path)], name.encode() + b"\0")
        assert result == b""
        missing_controls[name] = "omission excluded required file as expected"
    (HERE / "control-rules.txt").unlink()

    scope_groups = [
        {"selection": "hosted/ (all tracked files)", "why": "Full Mix lib/config/priv/test/support/test tree; .tool-versions; .formatter.exs; mix.exs/lock; test-local.py source manifest and replay tar", "files": [n for n in selected if n.startswith("hosted/")]},
        {"selection": "shared release fixtures", "why": "test-local.py hashes and archives both; ArtifactCBOR/ArtifactAdmission and authorization/storage tests read them", "files": [n for n in extra_paths if n.startswith("services/")]},
        {"selection": "browser protocol metadata", "why": "SOURCES + TESTS + EXTRA literal arrays in committed protocol runner; includes docs, AGENTS, THIRD_PARTY and runner", "files": protocol_paths},
        {"selection": "browser storage metadata", "why": "Committed run_storage_fixture.py source_paths includes this doc; all other selected sources and migrations lie under hosted/", "files": ["docs/hosted-browser-session-storage.md"]},
        {"selection": "workspace TypeScript client", "why": "Explicit file tsc invocation; its relative import/reexport closure; package pair for unchanged npm ci; copied node HTTP driver", "files": sorted(ts_closure) + ["console/package.json", "console/package-lock.json", "verification/hosted-customer-workspace-http-integration/node-client-driver.mjs"]},
        {"selection": "customer artifact golden fixtures", "why": "customer_artifact_event_test.exs @packet plus File.read! golden_event.hex and golden_hashes.txt", "files": [n for n in extra_paths if n.startswith("verification/hosted-customer-artifact-event/")]},
    ]
    required = set().union(*(set(group["files"]) for group in scope_groups))
    assert required == set(selected), (sorted(required - set(selected)), sorted(set(selected) - required))
    manifest = [{"path": name, **entries[name], "sha256": sha(blobs[name])} for name in selected]
    dump("selected-files.json", manifest)
    dump("readsets.json", {"groups": scope_groups, "typescript_import_edges": ts_edges,
                           "relation_manifest_bindings": relation_manifests,
                           "source_tar_selection": {"tracked_file_count": len(source_inputs),
                               "source_tree_sha256": sha(json.dumps(source_inputs, sort_keys=True, separators=(",", ":")).encode()),
                               "selection_equals_full_tracked_hosted_plus_two_shared_fixtures": True},
                           "generated_inputs": ["hosted/deps from unchanged mix deps.get --check-locked", "hosted/_build/test dependency BEAMs from unchanged mix deps.compile jason and mix deps.compile", "console/node_modules from unchanged npm ci --ignore-scripts --no-audit --no-fund", "$RUNNER_TEMP/workspace-client compiled outputs and driver from unchanged client step"],
                           "output_only_paths": ["verification/hosted-browser-auth-protocol/attempts/", "verification/hosted-browser-session-storage/attempts/", "$RUNNER_TEMP/browser-migrations/", "$RUNNER_TEMP/phoenix-foundation/"],
                           "no_invocation_claim": "test-identity-network.py and test_identity_network_collector.py remain hashed source files in hosted/. The committed Phoenix workflow does not run them; no Unit A or Docker step was copied."})
    dump("controls.json", {"negative_probes": probes, "all_negative_probes_excluded": True,
                           "single_required_file_omissions": missing_controls,
                           "workflow_bytes_reconstructed_after_removing_checkout_inputs": True,
                           "new_commands_steps_timeouts_env_dependencies_or_action_refs": False})
    excerpt_needles = {
        "hosted/scripts/test-local.py": ["def manifest", "for p in sorted(root.rglob", 'for name in ("signed-release', "tarfile.open", "for name in before", 'run("release-build"', 'run("release-test-exclusion"', 'test_argv ='],
        protocol_runner: ["SOURCES =", "TESTS =", "EXTRA =", "manifest =", "dependencies ="],
        storage_runner: ["source_paths =", 'REPO / "docs/', "dependency_dirs =", "legacy =", "BASE ="],
        migration_runner: ["MODULES =", "MIGRATIONS =", "DEPS =", "SPEC =", "ASSERTIONS =", "sources =", "sources +=", "assert set(MIGRATIONS)"],
        "hosted/mix.exs": ["elixirc_paths:", "test_ignore_filters:", "aliases:", "defp elixirc_paths"],
        "hosted/.formatter.exs": ["inputs:"],
        "hosted/test/mixer_hosted/audit/customer_artifact_event_test.exs": ["@packet", 'Path.join("golden'],
        "hosted/test/mixer_hosted/protocol/artifact_admission_test.exs": ["@fixtures", "@fixture", "@corpus"],
        "hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex": ["@resources", '"source_bindings"', "for {relative", "File.read!"],
        "hosted/lib/mixer_hosted/browser_auth/activation_preparation_schema.ex": ["@decoder_source", "File.read!"],
        "hosted/lib/mixer_hosted/browser_auth/catalog_manifest_v2.ex": ["@source_pins", "source =", "File.read!"],
        "hosted/test/mixer_hosted_web/customer_workspace_http_integration_test.exs": ['System.cmd("node"', 'MIXER_WORKSPACE_HTTP_NODE_DRIVER'],
    }
    source_excerpts = {}
    for name, needles in excerpt_needles.items():
        lines = blobs[name].decode().splitlines()
        source_excerpts[name] = [{"line": index, "text": line}
                                 for index, line in enumerate(lines, 1)
                                 if any(needle in line for needle in needles)]
        assert source_excerpts[name]
    dump("source-read-points.json", source_excerpts)
    largest_omitted = sorted((({"path": name, **entry} for name, entry in entries.items()
                               if name not in selected)), key=lambda row: row["bytes"], reverse=True)[:20]
    # Retain the blob IDs/digests and the reproduced source-input manifest. The
    # selected materialization is disposable validation data, not another checkout.
    shutil.rmtree(source_root)
    assert not source_root.exists()
    protected_after = sha((ROOT / WORKFLOW).read_bytes())
    assert protected_after == protected_before
    tracked_bytes = sum(entry["bytes"] for entry in entries.values())
    unique_tracked = {entry["git_blob"]: entry["bytes"] for entry in entries.values()}
    unique_selected = {entries[name]["git_blob"]: entries[name]["bytes"] for name in selected}
    receipt = {"status": "passed_source_only", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
               "source_revision": head, "analysis_base_revision": ANALYSIS_BASE_REVISION,
               "observed_head_at_start": observed_head,
               "source_git_tree": tree_oid, "git_ls_tree_metadata_sha256": sha(metadata),
               "workflow_path": WORKFLOW, "committed_workflow_blob": entries[WORKFLOW]["git_blob"],
               "committed_workflow_sha256": sha(baseline), "candidate_workflow_sha256": sha(candidate),
               "patch_sha256": sha(patch.encode()), "sparse_patterns_sha256": sha(pattern_bytes),
               "audit_script_sha256": sha(Path(__file__).read_bytes()),
               "selected_manifest_sha256": sha(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()),
               "tool_versions": {"git": git_version, "python": sys.version},
               "measurement": {"basis": "Git ls-tree -r -l object metadata at exact revision; tracked blobs only; logical uncompressed bytes, not network/fetch/archive or on-disk allocation", "tracked_files": len(entries), "tracked_blob_bytes": tracked_bytes, "selected_files": len(selected), "selected_blob_bytes": total_selected, "omitted_files": len(entries) - len(selected), "omitted_blob_bytes": tracked_bytes - total_selected, "selected_byte_percent": round(100 * total_selected / tracked_bytes, 5), "unique_tracked_blobs": len(unique_tracked), "unique_tracked_blob_bytes": sum(unique_tracked.values()), "unique_selected_blobs": len(unique_selected), "unique_selected_blob_bytes": sum(unique_selected.values())},
               "largest_omitted_blobs": largest_omitted,
               "protected_live_workflow": {"expected_sha256": EXPECTED_PROTECTED_SHA256, "before_sha256": protected_before, "after_sha256": protected_after, "untouched": protected_before == protected_after, "contents_not_copied": True},
               "checks": {"git_canonical_sparse_rules": True, "selected_source_materialized_and_hashed_against_git": True, "complete_audited_committed_readset_retained": True, "full_hosted_source_tar_selection_retained": True, "tracked_relation_source_hashes_match": True, "production_release_and_test_exclusion_commands_unchanged_byte_for_byte": True, "all_noncheckout_workflow_bytes_unchanged": True, "required_file_omission_controls": len(missing_controls), "anchoring_and_unrelated_blob_controls": len(probes)},
               "execution_scope": "Read-only Git commands, stdlib parsing/hash/selected-source materialization inside this new packet only; no index/worktree registration, global metadata edits, install, compilation, test suite, Docker/database/native/UI/process probes, network, CI mutation, commit, or push.",
               "cleanup": {"owned_selected_source_materialization_removed": not source_root.exists(), "started_runtime_or_capture_processes": False},
               "pending": ["Root review and canonical workflow integration while preserving protected Unit A additions", "Fresh GitHub checkout/CI run after authorized integration", "Operational checkout timing/fetch/transfer measurement; no runtime speedup claim is made", "Re-audit selectors if committed workflow, source readsets, TypeScript imports or metadata readers change", "All native/browser/provider/customer and GA gates remain outside this source-only review"],
               "elapsed_seconds": round(time.monotonic() - STARTED, 3)}
    dump("receipt.json", receipt)
    dump("commands.json", {"audit_invocation": "python3 verification/phoenix-sparse-checkout-candidate/audit.py" + (" " + REVISION if REVISION != ANALYSIS_BASE_REVISION else ""), "git_environment_overrides": GIT_ENV_OVERRIDES, "git_commands": COMMANDS})
    print(json.dumps({"status": receipt["status"], "measurement": receipt["measurement"],
                      "protected_workflow_untouched": True, "elapsed_seconds": receipt["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
