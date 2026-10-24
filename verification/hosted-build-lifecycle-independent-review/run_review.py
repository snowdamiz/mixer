#!/usr/bin/env python3
"""Verify the producer seal and run only standalone pure Elixir review controls."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SEAL = ROOT / "verification/hosted-build-lifecycle/handoff-manifest.json"
EXPECTED_SEAL = "15f20b5a536876be48acdfa36d155b15b74b4b66c4fddbec9eb56846c6f4779e"
SOURCE_PATHS = [
    "hosted/lib/mixer_hosted/builds/lifecycle.ex",
    "hosted/test/mixer_hosted/builds/lifecycle_test.exs",
    "docs/hosted-build-lifecycle.md",
]
ELIXIR = "/opt/homebrew/bin/elixir"
ENV = dict(os.environ, ERL_FLAGS="+S 2:2")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def tree_digest(values):
    wire = b"".join(p.encode() + b"\0" + h.encode() + b"\n" for p, h in sorted(values.items()))
    return hashlib.sha256(wire).hexdigest()


def run(label, command, timeout=120):
    start = time.monotonic()
    try:
        result = subprocess.run(command, cwd=ROOT, env=ENV, capture_output=True, timeout=timeout)
        stdout, stderr, code, timed_out = result.stdout, result.stderr, result.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, timed_out = error.stdout or b"", error.stderr or b"", None, True
    metadata = {
        "command": command,
        "cwd": str(ROOT),
        "environment_override": {"ERL_FLAGS": "+S 2:2"},
        "timeout_seconds": timeout,
        "elapsed_seconds": time.monotonic() - start,
        "exit_code": code,
        "timed_out": timed_out,
        "stdout_file": f"commands/{label}.stdout",
        "stderr_file": f"commands/{label}.stderr",
    }
    out = HERE / "commands"
    out.mkdir(exist_ok=True)
    (out / f"{label}.stdout").write_bytes(stdout)
    (out / f"{label}.stderr").write_bytes(stderr)
    save(out / f"{label}.json", metadata)
    return {**metadata, "stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace")}


def main():
    assert sha(SEAL) == EXPECTED_SEAL, "producer seal mismatch; no test may execute"
    manifest = json.loads(SEAL.read_text())
    assert manifest["source_test_doc_frozen_for_independent_review"] is True
    audit = {}
    for name, expected in manifest["files"].items():
        relative = Path(name)
        assert not relative.is_absolute() and ".." not in relative.parts
        path = ROOT / relative
        observed = {"sha256": sha(path), "size_bytes": path.stat().st_size}
        assert observed == expected, f"producer file mismatch: {name}"
        audit[name] = observed

    snapshot = HERE / "accepted-source"
    source_hashes = {}
    for name in SOURCE_PATHS:
        content = (ROOT / name).read_bytes()
        destination = snapshot / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == content, "refusing to replace an accepted snapshot"
        else:
            destination.write_bytes(content)
        source_hashes[name] = sha(destination)

    (HERE / "producer-handoff-manifest.json").write_bytes(SEAL.read_bytes())
    save(HERE / "source-acceptance.json", {
        "schema": "mixer.hosted-build-lifecycle.independent-source-acceptance.v1",
        "accepted_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "producer_seal_sha256": EXPECTED_SEAL,
        "producer_files_verified": audit,
        "snapshot_sha256": source_hashes,
        "snapshot_tree_sha256": tree_digest(source_hashes),
        "tested_source_tree_sha256": tree_digest({p: source_hashes[p] for p in SOURCE_PATHS[:2]}),
        "scope": "Producer final seal accepted before any test run; copied only the sealed module, test and contract document",
    })

    revision = run("source-revision", ["git", "rev-parse", "HEAD"], 10)
    toolchain = run("toolchain", [ELIXIR, "--version"], 10)
    precise_versions = run("precise-versions", [
        ELIXIR, "-e",
        'IO.puts("elixir=" <> System.version()); IO.puts("otp=" <> File.read!(Path.join([to_string(:code.root_dir()), "releases", to_string(:erlang.system_info(:otp_release)), "OTP_VERSION"])))',
    ], 10)
    source = str((snapshot / SOURCE_PATHS[0]).relative_to(ROOT))
    producer_test = str((snapshot / SOURCE_PATHS[1]).relative_to(ROOT))
    controls = str((HERE / "controls_test.exs").relative_to(ROOT))
    input_hashes = {
        source: sha(ROOT / source),
        producer_test: sha(ROOT / producer_test),
        controls: sha(ROOT / controls),
        str(Path(__file__).resolve().relative_to(ROOT)): sha(Path(__file__).resolve()),
    }

    producer = run("producer-suite", [ELIXIR, "-r", source, "-e", f'ExUnit.start(); Code.require_file("{producer_test}")'])
    independent = run("independent-controls", [ELIXIR, "-r", source, "-e", f'ExUnit.start(seed: 0, trace: true); Code.require_file("{controls}")'])
    unchanged = all(sha(ROOT / name) == value["sha256"] for name, value in audit.items())
    snapshot_unchanged = all(sha(ROOT / name) == value for name, value in input_hashes.items())

    def counts(result):
        match = re.search(r"(\d+) tests?, (\d+) failures?", result["stdout"])
        if match:
            return {"tests": int(match[1]), "failures": int(match[2])}
        match = re.search(r"Result:\s*(\d+) passed(?:,\s*(\d+) failed)?", result["stdout"])
        return {"tests": int(match[1]) + int(match[2] or 0), "failures": int(match[2] or 0)} if match else None

    passed = all(item["exit_code"] == 0 for item in [revision, toolchain, precise_versions, producer, independent])
    passed = passed and unchanged and snapshot_unchanged and sha(SEAL) == EXPECTED_SEAL
    passed = passed and counts(producer) == {"tests": 21, "failures": 0}
    passed = passed and counts(independent) == {"tests": 10, "failures": 0}
    results = {
        "schema": "mixer.hosted-build-lifecycle.independent-review-results.v1",
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "result": "pure_review_passed_root_acceptance_pending" if passed else "review_failed",
        "source_revision": revision["stdout"].strip(),
        "host": platform.uname()._asdict(),
        "python": sys.version,
        "producer_seal_sha256": EXPECTED_SEAL,
        "tested_source_tree_sha256": tree_digest({p: source_hashes[p] for p in SOURCE_PATHS[:2]}),
        "input_sha256": input_hashes,
        "input_tree_sha256": tree_digest(input_hashes),
        "toolchain": toolchain,
        "precise_versions": precise_versions,
        "producer_suite": {**producer, "counts": counts(producer)},
        "independent_controls": {**independent, "counts": counts(independent)},
        "all_producer_handoff_files_unchanged_after_review": unchanged,
        "snapshot_and_review_inputs_unchanged_during_tests": snapshot_unchanged,
        "scope": "Darwin arm64 host-only pure in-memory Elixir lifecycle decisions. Standalone elixir only; no Mix, test_helper, application, database, network, provider, native harness or frozen authority lane.",
        "trusted_build_boundary": "Build is trusted in-memory application state. Synthetic event-ledger and fence bounds are arithmetic/boundedness controls only; no untrusted hydration, auth, durable CAS or distributed lock acceptance.",
        "cleanup": {"native_instances_created": 0, "containers_created": 0, "persistent_services_started": 0, "other_project_processes_changed": False},
        "not_verified": [
            "HTTP, tenant and worker authentication/authorization",
            "durable event/request uniqueness, CAS, Ecto.Multi/Oban atomic commit",
            "dispatch, actual worker termination, orphan rescue and global quotas",
            "provider/network/isolation/resource operation",
            "source/toolchain/dependency resolution and native compilation",
            "artifact content, provenance truth, publication and tenant access",
            "signing, stores, releases, charging and reconciliation",
            "W12, hosted, G22, physical-phone or GA acceptance",
        ],
    }
    save(HERE / "results.json", results)
    print(json.dumps({
        "result": results["result"],
        "producer_suite": counts(producer),
        "independent_controls": counts(independent),
        "tested_source_tree_sha256": results["tested_source_tree_sha256"],
        "producer_handoff_unchanged": unchanged,
        "snapshot_inputs_unchanged": snapshot_unchanged,
    }, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
