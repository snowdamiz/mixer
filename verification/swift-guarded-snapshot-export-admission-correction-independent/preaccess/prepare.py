"""Prepare independent F1/F2 criteria before active candidate access.

Only the explicit frozen inputs below are read. This does not run old wrappers,
the original compiler/model suites, or any active producer/encoder implementation.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ACCEPTED = ROOT / "verification/swift-guarded-snapshot-export-preparation/inputs/accepted-source/vm"
MANIFEST = ROOT / "verification/swift-guarded-snapshot-export-preparation/inputs/source-manifest.json"
DESIGN = ROOT / "verification/swift-guarded-snapshot-export-admission-design"
PREVIOUS = ROOT / "verification/swift-guarded-snapshot-export-admission-independent/actual-review"
SELECTION = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-export-admission-correction-selection.json"
RUSTC = pathlib.Path("/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc")
EXPECTED_SELECTION = "df99aba0e0abe8cdb5a635a3ad77a058f972c907af1d604f1879da25506676ff"
EXPECTED_TREE = "9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb"
EXPECTED_MANIFEST = "f17270c23f09cef85bf1aa5254f94e0355d11678702a876f00ac8520b7d186f3"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_members(base, manifest, expected_members):
    assert len(manifest["members"]) == expected_members
    seen = set()
    for member in manifest["members"]:
        relative = pathlib.PurePosixPath(member["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert member["path"] not in seen
        seen.add(member["path"])
        path = base / relative
        assert not path.is_symlink()
        assert path.stat().st_size == member["bytes"], member["path"]
        assert sha(path) == member["sha256"], member["path"]
    # This normalized commitment is explicitly this review's format; it is not
    # assumed to equal an upstream manifest's differently serialized tree hash.
    commitment = hashlib.sha256()
    for member in sorted(manifest["members"], key=lambda item: item["path"]):
        commitment.update((member["path"] + "\0" + str(member["bytes"]) + "\0"
                           + member["sha256"] + "\n").encode())
    return {"members_verified": len(seen),
            "bytes_verified": sum(item["bytes"] for item in manifest["members"]),
            "manifest_tree_sha256": manifest["tree_sha256"],
            "independent_path_size_hash_commitment": commitment.hexdigest()}


def custody():
    assert sha(SELECTION) == EXPECTED_SELECTION
    inputs = []
    for base, expected, count in [
        (DESIGN, "b60d1ba0790076b35b6df30dd8df407486f89144e6914f40d2d0d55e4e20e1f5", 70),
        (PREVIOUS, "4356c1f7b8adde46dca0b661171d9ad935773a3ecfe47ac153581b2fb4a3e896", 35),
    ]:
        assert sha(base / "seal.json") == expected
        manifest = json.loads((base / "seal.json").read_text())
        inputs.append({"path": str(base.relative_to(ROOT)), "seal_sha256": expected,
                       **verify_members(base, manifest, count)})
    assert sha(MANIFEST) == EXPECTED_MANIFEST
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["tree_sha256"] == EXPECTED_TREE
    inputs.append({"path": str(ACCEPTED.relative_to(ROOT)),
                   "source_manifest_sha256": sha(MANIFEST),
                   **verify_members(ACCEPTED, manifest, 144)})
    return {"at": now(), "selection_sha256": sha(SELECTION), "inputs": inputs,
            "active_correction_accessed": False, "active_encoder_accessed": False,
            "input_verification_does_not_replay_original_commands": True}


def source_excerpts():
    ranges = {
        "src/experimental_swift_reactor/control.rs": [
            (379, 422, "existing source-authored adoption cleanup places and sole RuntimeControl fields"),
            (610, 710, "actual original admission order, final check, error cleanup, success return"),
            (891, 948, "actual stop/failure install and first-failure preservation"),
            (1160, 1218, "actual storage drop before phase retirement validation"),
            (1734, 1805, "actual cleanup observation and original single-floor finish"),
        ],
        "src/experimental_swift_reactor/cache/initial_profile_v1.rs": [
            (12, 48, "exact accepted scalar/guard and original eight outcomes"),
            (125, 176, "actual wrapper order and sole guard"),
        ],
    }
    excerpts = []
    for relative, groups in ranges.items():
        path = ACCEPTED / relative
        lines = path.read_text().splitlines(keepends=True)
        for start, end, fact in groups:
            excerpt = "".join(lines[start - 1:end])
            excerpts.append({"path": relative, "source_sha256": sha(path),
                             "start": start, "end": end, "purpose": fact,
                             "excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
                             "text": excerpt})
    dump(HERE / "source-excerpts.json", {"source_tree_sha256": EXPECTED_TREE,
                                        "scope": "source anchors, not execution or release authorization",
                                        "excerpts": excerpts})


def exact_item(text, marker):
    start = text.index(marker)
    opening = text.index("{", start)
    # These two selected items have only field types and balanced braces; no
    # source classifier is used to authorize an OTA or runtime admission.
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1], text[:start].count("\n") + 1
    raise AssertionError(marker)


def generate_sources():
    relative = "src/experimental_swift_reactor/cache/initial_profile_v1.rs"
    text = (ACCEPTED / relative).read_text()
    scalar, scalar_line = exact_item(text, "#[repr(C)]\nstruct InitialProfileScalarsV1")
    guard, guard_line = exact_item(text, "struct InitialProfileBorrowV1<'a>")
    definitions = scalar + "\n" + guard + "\n"
    copied = []
    for name, value, start in [("InitialProfileScalarsV1", scalar, scalar_line),
                               ("InitialProfileBorrowV1", guard, guard_line)]:
        copied.append({"name": name, "source": relative, "source_sha256": sha(ACCEPTED / relative),
                       "start": start, "end": start + value.count("\n"),
                       "exact_item_sha256": hashlib.sha256(value.encode()).hexdigest()})
    generated = []
    for body, output in [("ownership-control-body.rs", "ownership-control.rs"),
                         ("option-fallback-negative-body.rs", "option-fallback-negative.rs")]:
        destination = HERE / output
        destination.write_text("#![allow(dead_code)]\n" + definitions + (HERE / body).read_text())
        generated.append({"path": output, "sha256": sha(destination),
                          "body": body, "body_sha256": sha(HERE / body)})
    dump(HERE / "copied-definition-manifest.json", {
        "source_tree_sha256": EXPECTED_TREE, "exact_copied_items": copied,
        "generated": generated,
        "components_are_opaque_standins": ["RuntimeControl", "SwiftFunctionCache", "AccountedWasi"],
        "scope": "Rust refusal/view lifetime relation only; not actual Mixer composition"})


def error_codes(stderr):
    codes = []
    for line in stderr.decode(errors="replace").splitlines():
        try:
            diagnostic = json.loads(line)
        except json.JSONDecodeError:
            continue
        if diagnostic.get("level") == "error" and diagnostic.get("code"):
            codes.append(diagnostic["code"]["code"])
    return codes


def main():
    if (HERE / "seal.json").exists():
        raise SystemExit("Preaccess is already frozen; create later review in candidate-review only")
    dump(HERE / "input-custody-before.json", custody())
    source_excerpts()
    generate_sources()
    records = []

    def run(name, argv, *, accepted_returncode=0, expected_codes=None, source=None):
        folder = HERE / "commands" / name
        folder.mkdir(parents=True, exist_ok=False)
        started = now()
        tick = time.monotonic()
        completed = subprocess.run([str(arg) for arg in argv], cwd=ROOT,
                                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        (folder / "stdout").write_bytes(completed.stdout)
        (folder / "stderr").write_bytes(completed.stderr)
        codes = error_codes(completed.stderr)
        passed = completed.returncode == accepted_returncode
        if expected_codes is not None:
            passed = passed and set(codes) == set(expected_codes)
        receipt = {"schema": 1, "started": started, "ended": now(),
                   "duration_seconds": time.monotonic() - tick,
                   "argv": [str(arg) for arg in argv], "cwd": str(ROOT),
                   "returncode": completed.returncode, "expected_returncode": accepted_returncode,
                   "error_codes": codes, "expected_error_codes": expected_codes,
                   "expectation_met": passed, "accepted_source_tree_sha256": EXPECTED_TREE,
                   "runner_sha256": sha(pathlib.Path(__file__)),
                   "stdout_sha256": sha(folder / "stdout"), "stderr_sha256": sha(folder / "stderr"),
                   "scope": "preaccess custody/tool version or reduced Rust ownership control only"}
        if source:
            receipt["source"] = {"path": str(source.relative_to(HERE)), "sha256": sha(source)}
        dump(folder / "receipt.json", receipt)
        records.append({"name": name, "receipt_sha256": sha(folder / "receipt.json"),
                        "expectation_met": passed})
        assert passed, name
        return completed.stdout.decode(errors="replace")

    python_version = run("python-version", [sys.executable, "--version"]).strip()
    rustc_version = run("rustc-version", [RUSTC, "-vV"]).strip()
    revision = run("git-revision", ["git", "rev-parse", "HEAD"]).strip()
    scratch_name = None
    try:
        with tempfile.TemporaryDirectory(prefix="tiny-ownership-", dir=HERE) as directory:
            scratch = pathlib.Path(directory)
            scratch_name = str(scratch.relative_to(HERE))
            for name, opt in [("debug", "0"), ("optimized", "3")]:
                common = [RUSTC, "--edition=2021", "--target", "aarch64-apple-darwin",
                          "--error-format=json", "-C", "overflow-checks=yes", "-C", f"opt-level={opt}"]
                positive = HERE / "ownership-control.rs"
                binary = scratch / f"{name}-positive"
                run(f"{name}-positive-compile", [*common, "--test", positive, "-o", binary], source=positive)
                run(f"{name}-positive-run", [binary, "--nocapture"], source=positive)
                run(f"{name}-live-view-negative", [*common, "--test", "--cfg", "live_view_negative",
                                                 positive, "-o", scratch / f"{name}-live-view"],
                    accepted_returncode=1, expected_codes=["E0505"], source=positive)
                negative = HERE / "option-fallback-negative.rs"
                run(f"{name}-option-fallback-negative", [*common, "--crate-type=lib", "--emit=metadata",
                                                       negative, "-o", scratch / f"{name}-fallback.rmeta"],
                    accepted_returncode=1, expected_codes=["E0502"], source=negative)
    finally:
        dump(HERE / "cleanup.json", {"at": now(), "scratch": scratch_name,
                                     "scratch_removed": scratch_name is not None and not (HERE / scratch_name).exists(),
                                     "all_subprocesses_completed": True,
                                     "native_ui_capture_process_inventory_started": False})
    dump(HERE / "input-custody-after.json", custody())
    dump(HERE / "receipt.json", {
        "schema": 1, "at": now(), "status": "preaccess-criteria-and-targeted-language-controls-complete",
        "source_revision_context": revision, "accepted_source_tree_sha256": EXPECTED_TREE,
        "selection_sha256": EXPECTED_SELECTION, "python_version": python_version,
        "rustc_version": rustc_version, "commands": records,
        "positive_runtime_tests": 4, "negative_compile_controls": 4,
        "prior_suites_replayed": False, "actual_new_admission_executed": False,
        "actual_wrapper_or_exporter_executed": False, "candidate_accessed": False,
        "active_encoder_accessed": False, "source_place_or_floor_accepted": False,
        "operational_grant_accepted": False, "ga_gates_verified": 0,
        "limitations": ["F1 remains a source-backed acceptance plan awaiting the actual frozen correction",
                        "F2 controls use exact accepted scalar/guard definitions and opaque component stand-ins",
                        "The positive sum owner is one feasibility direction, not selected product design",
                        "No native/device/simulator/emulator/UI/capture/process inventory or frozen wrapper replay"],
        "next": "Freeze preaccess; await root release; review frozen candidate in sibling candidate-review only"})
    members = []
    for path in sorted(HERE.rglob("*")):
        assert not path.is_symlink()
        if path.is_file() and path.name != "seal.json":
            members.append({"path": str(path.relative_to(HERE)), "bytes": path.stat().st_size,
                            "sha256": sha(path)})
    tree = hashlib.sha256()
    for member in members:
        tree.update((member["path"] + "\0" + str(member["bytes"]) + "\0"
                     + member["sha256"] + "\n").encode())
    dump(HERE / "seal.json", {"schema": 1, "at": now(), "member_count": len(members),
                              "bytes": sum(member["bytes"] for member in members), "members": members,
                              "tree_sha256": tree.hexdigest(),
                              "scope": "Preaccess independent F1/F2 criteria and reduced refusal/view language controls only"})
    print(json.dumps({"seal_sha256": sha(HERE / "seal.json"), "member_count": len(members),
                      "bytes": sum(member["bytes"] for member in members),
                      "positive_runtime_tests": 4, "negative_compile_controls": 4}, indent=2))


if __name__ == "__main__":
    main()
