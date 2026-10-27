#!/usr/bin/env python3
"""Fresh bounded independent review; never execute producer orchestration."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PRE = HERE.parent
ROOT = PRE.parent.parent
CANDIDATE = PRE.parent / "swift-guarded-snapshot-export-admission-design"
BASE = PRE.parent / "swift-guarded-snapshot-export-preparation/inputs/accepted-source/vm"
RUSTC = "/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def llvm_words(path):
    definition = path.read_text().strip()
    encoded = definition.split('c"', 1)[1].split('"', 1)[0]
    raw, position = bytearray(), 0
    while position < len(encoded):
        if encoded[position] == "\\":
            raw.append(int(encoded[position+1:position+3], 16))
            position += 3
        else:
            raw.append(ord(encoded[position]))
            position += 1
    assert len(raw) % 8 == 0
    return [int.from_bytes(raw[index:index+8], "little") for index in range(0, len(raw), 8)]


def review_source_and_layout():
    expected_shell = [1720,8,1096,8,1096,8,16,8,2232,8,2232,8,5648,8,29256,8,3416,8]
    expected_profile = [1,1,1168,8,136,8,16,8,8,8,2936,8,8536,8,5936,8]
    rows = []
    for folder in ["compile-debug", "compile-optimized", "compile-unit-layout",
                   "profile-layout-debug", "profile-layout-optimized", "profile-layout-unit"]:
        layout = CANDIDATE / "commands" / folder / "layout-llvm.txt"
        words = llvm_words(layout)
        expected = expected_shell if folder.startswith("compile-") else list(expected_profile)
        if folder == "profile-layout-unit":
            expected[-2] = 5984
        assert words == expected, (folder, words)
        receipt = json.loads((layout.parent / "receipt.json").read_text())
        assert receipt["exit_code"] == 0 and receipt["child_reaped"]
        for stream in ["stdout", "stderr"]:
            assert sha(layout.parent / stream) == receipt[stream + "_sha256"]
        rows.append({"folder": folder, "layout_sha256": sha(layout), "layout_words": words,
                     "compiler_argv": receipt["argv"], "independently_decoded": True,
                     "newly_recompiled": False})
    variants = {
        "compile-source-manifest.json": {
            "src/experimental_swift_reactor/control.rs": "control_append.rs",
            "src/experimental_swift_reactor/cache/initial_profile_v1.rs": "initial_append.rs",
            "src/experimental_wasi/accounted.rs": "wasi_append.rs",
        },
        "profile-compile-source-manifest.json": {
            "src/experimental_swift_reactor/control.rs": "profile_append.rs",
        },
    }
    manifests = []
    for name, additions in variants.items():
        manifest = json.loads((CANDIDATE / name).read_text())
        assert len(manifest["members"]) == 144
        for row in manifest["members"]:
            data = (BASE / row["path"]).read_bytes()
            if row["path"] in additions:
                data += b"\n" + (CANDIDATE / "prototype" / additions[row["path"]]).read_bytes()
            assert len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"], row["path"]
        manifests.append({"path": name, "sha256": sha(CANDIDATE / name), "independently_reconstructed_members": 144})
    report = {"recorded_layouts": rows, "recorded_source_manifests": manifests,
              "limits": "Six recorded compiler constants decoded and 288 source preimages reconstructed without recompiling full Mixer; complete live source-place/floor/scope admission remains unimplemented"}
    dump(HERE / "layout-source-review.json", report)


def main():
    commands = []
    source_inputs = {path.name: sha(path) for path in HERE.iterdir() if path.suffix in [".py", ".rs"]}
    source_inputs["producer-seal"] = sha(CANDIDATE / "seal.json")
    source_inputs["pre-release-seal"] = sha(PRE / "pre-release-seal.json")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    def command(name, argv, cwd, expected_codes=None):
        folder = HERE / "commands" / name
        folder.mkdir(parents=True)
        started = datetime.datetime.now(datetime.timezone.utc)
        process = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=45)
        for stream in ["stdout", "stderr"]:
            (folder / stream).write_bytes(getattr(process, stream))
        codes = []
        if expected_codes is not None:
            for line in process.stderr.decode().splitlines():
                diagnostic = json.loads(line)
                if diagnostic.get("level") == "error" and diagnostic.get("code"):
                    codes.append(diagnostic["code"]["code"])
            passed = process.returncode != 0 and codes == expected_codes
        else:
            passed = process.returncode == 0
        receipt = {"name": name, "argv": argv, "cwd": str(cwd), "source_inputs": source_inputs,
                   "started": started.isoformat(), "ended": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "exit_code": process.returncode, "error_codes": codes, "expectation_met": passed,
                   "stdout_sha256": sha(folder / "stdout"), "stderr_sha256": sha(folder / "stderr"),
                   "scope": "independent finite Python controls or tiny lifetime-only native compiler snippet; no full Mixer compile or actual-source wrapper behavior"}
        dump(folder / "receipt.json", receipt)
        commands.append({"name": name, "receipt_sha256": sha(folder / "receipt.json"), "expectation_met": passed})
        print(json.dumps({"name": name, "exit_code": process.returncode, "error_codes": codes, "expectation_met": passed}))
    review_source_and_layout()
    command("python-version", [sys.executable, "--version"], HERE)
    command("rustc-version", [RUSTC, "--version", "--verbose"], HERE)
    command("carry-independent25", [sys.executable, "-m", "unittest", "-v", "test_controls"], PRE)
    command("fresh-frozen5", [sys.executable, "-m", "unittest", "-v", "test_frozen_design"], HERE)
    with tempfile.TemporaryDirectory(prefix="lifetime-only-", dir=HERE) as folder:
        for mode, optimization in [("debug", "0"), ("optimized", "3")]:
            for case, errors in [("direct-phase-guard", ["E0502"]), ("phase-reborrow-feasibility", None)]:
                argv = [RUSTC, "--crate-type", "lib", "--edition=2021", "--emit", "metadata", "--error-format=json",
                        "-C", "opt-level=" + optimization, str(HERE / (case + ".rs")), "-o", str(Path(folder) / (case + ".rmeta"))]
                command(mode + "-" + case, argv, HERE, errors)
    passed = all(row["expectation_met"] for row in commands)
    dump(HERE / "receipt.json", {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "fresh-independent-controls-pass-findings-require-design-revision" if passed else "independent-control-expectation-failed",
        "commands": commands, "all_expectations_met": passed,
        "python_methods_passed": 30, "tiny_lifetime_compiles": 4,
        "recorded_layout_contexts_independently_decoded": 6,
        "full_Mixer_compiler_or_original_orchestration_executed": False,
        "cleanup": {"owned_compiler_scratch_removed": not bool(list(HERE.glob("lifetime-only-*"))),
                    "no_pycache": not bool(list(HERE.rglob("__pycache__"))),
                    "host_alias_temporary_files": "removed by bounded pre-release controls", "persistent_processes_started": False},
        "canonical_or_producer_files_changed": False, "GA_gates_verified": 0,
        "limits": ["Lifetime cases use opaque stand-ins and test signature composition only", "No actual scope/core/phase integration exists in producer", "Recorded layout constants are prototype layouts, not complete source floors", "Native/device/simulator/emulator/UI/capture/process inventories paused"],
    })
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
