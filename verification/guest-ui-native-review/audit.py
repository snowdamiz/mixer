#!/usr/bin/env python3
"""Independent native validate-only receipt audit and small retained-archive probe."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OWNER = ROOT / "verification/guest-ui-native"
ARCHIVE = ROOT / "vm/target/stream-validation-verification/release/libmixer_vm.a"
EXPECTED = {
    "verification/guest-ui-native/receipt.json": "96db9cca2bcf850cd5de54e59b1f96298a0645d1d4a6c13186d5e662e49c2e06",
    "verification/guest-ui-native/supplemental-receipt.json": "6332431cef0e815c3437e003ce9193194be72ac1da238449590cea6c56b85614",
    "vm/target/stream-validation-verification/release/libmixer_vm.a": "5358e39b9efb0561d185c4c22152df057a78a2ca43c582e7b5493e5877fe23e4",
}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    receipt = {"schema": 1, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "scope": "Independent macOS host review of native guest-UI validate-only source and retained selected Release archive.",
               "commands": [], "checked_hashes": {}, "limitations": [
                   "No native archive or giant full feature graph rebuilt in this review.",
                   "Owner Debug/Release/native-only/default tests and allocation counts are audited retained evidence, not independently rerun tests.",
                   "Public C probes establish host behavior only; no Swift/UI content, devices, publication, signing/store/customer or GA qualification.",
                   "Allocation instrumentation describes caller-thread requested sizes; it is not heap/RSS, OOM containment or device evidence.",
                   "Direct-object default/guest-only symbol checks do not establish rebuilt package archive symbol inventories.",
               ]}
    def verify(path, expected):
        path = Path(path)
        actual = sha(path)
        assert actual == expected, f"hash mismatch: {path}: {actual} != {expected}"
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        receipt["checked_hashes"][key] = actual
    for p, expected in EXPECTED.items():
        verify(ROOT/p, expected)
    main_receipt = json.loads((OWNER/"receipt.json").read_text())
    supplemental = json.loads((OWNER/"supplemental-receipt.json").read_text())
    gating = json.loads((OWNER/"symbol-gating.json").read_text())
    verify(OWNER/"source-manifest.json", main_receipt["source_manifest_sha256"])
    for path, expected in json.loads((OWNER/"source-manifest.json").read_text()).items():
        verify(ROOT/path, expected)
    for obj in [main_receipt, supplemental, gating]:
        assert obj["result"] == "passed"
        assert obj["source_manifest_sha256"] == main_receipt["source_manifest_sha256"]
        for c in obj["commands"]:
            assert c["exit_status"] == 0
            verify(ROOT/c["log"], c["log_sha256"])
    for artifact in main_receipt["artifacts"].values():
        verify(artifact["archive"], artifact["archive_sha256"])
        verify(artifact["binary"], artifact["binary_sha256"])
    for path, expected in main_receipt["preserved_contracts_and_headers"].items():
        verify(ROOT/path, expected)
    verify(ROOT/main_receipt["earlier_attempt"]["receipt"], main_receipt["earlier_attempt"]["sha256"])
    verify(OWNER/"fixture-manifest.json", supplemental["fixture_manifest_sha256"])
    fixture = json.loads((OWNER/"fixture-manifest.json").read_text())
    verify(ROOT/fixture["builder"], fixture["builder_sha256"])
    verify(OWNER/"capture_fixture.rs", fixture["capture_source_sha256"])
    for path in [OUT/"audit.py", OUT/"public_probe.c", ROOT/"AGENTS.md", ROOT/"docs/guest-ui-event-integration-design.md",
                 ROOT/"contracts/guest-ui-event-v1.json", OWNER/"symbol-gating.json"]:
        receipt["checked_hashes"][str(path.relative_to(ROOT))] = sha(path)
    totals = {}
    for profile in ["debug", "release"]:
        totals[profile] = {}
        for label, suffix, expected in [("combined_native", "rust-tests", 79),
                ("native_only_guest_ui", "native-only-focused", 6),
                ("default_regression", "default-regression", 49)]:
            output = (OWNER/(profile+"-"+suffix+".log")).read_text()
            count = sum(int(n) for n in re.findall(r"test result: ok\. (\d+) passed",output))
            assert count == expected, (profile,label,count)
            assert not re.search(r"test result: FAILED|[1-9]\d* failed",output)
            totals[profile][label] = count
    for name in ["mixer_vm_capability_guest_ui_validate_v1", "mixer_vm_capability_validate_v1"]:
        for profile in ["default", "guest-only"]:
            assert "_"+name not in (OWNER/(profile+"-symbol-gating.log")).read_text()
        for profile in ["debug", "release"]:
            assert "_"+name in (OWNER/(profile+"-symbols.log")).read_text()
    receipt["owner_test_totals_per_profile"] = totals
    receipt["owner_primary_source_revision"] = main_receipt["source_revision"]
    receipt["owner_source_manifest_sha256"] = main_receipt["source_manifest_sha256"]
    def run(label, argv):
        result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = OUT/(label+".log")
        log.write_bytes(result.stdout)
        receipt["commands"].append({"label": label, "argv": argv, "cwd": str(ROOT),
            "exit_status": result.returncode, "log": str(log.relative_to(ROOT)), "log_sha256": sha(log)})
        if result.returncode:
            print(result.stdout.decode(errors="replace"))
            receipt["result"] = "failed"
            (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
            raise SystemExit(result.returncode)
        return result.stdout.decode(errors="replace")
    receipt["source_revision"] = run("source-revision",["git","rev-parse","HEAD"]).strip()
    run("source-status",["git","status","--short"])
    run("native-diff",["git","diff","--","vm/src/capability_ffi/api.rs","vm/src/capability_ffi/exports.rs",
        "vm/src/capability_ffi/preflight.rs","vm/src/experimental_capability_guest/mod.rs"])
    run("clang-version",["clang","--version"])
    run("rustc-version",["/opt/homebrew/opt/rustup/bin/rustc","-Vv"])
    run("cargo-version",["/opt/homebrew/opt/rustup/bin/cargo","-V"])
    run("host-version",["uname","-a"])
    binary = OUT/"public-probe"
    run("public-probe-build",["clang","-std=c11","-Wall","-Wextra","-Werror","-I",str(ROOT/"vm/include"),
        str(OUT/"public_probe.c"),str(ARCHIVE),"-o",str(binary)])
    probe_output = run("public-probe-run",[str(binary)])
    symbols = run("public-probe-symbols",["nm","-gU",str(binary)])
    for name in ["mixer_vm_capability_guest_ui_validate_v1", "mixer_vm_capability_validate_v1", "mixer_vm_capability_session_create_v1"]:
        assert "_"+name in symbols
    receipt["artifacts"] = {"probe":str(binary.relative_to(ROOT)), "probe_sha256":sha(binary),
        "archive":str(ARCHIVE.relative_to(ROOT)), "archive_sha256":sha(ARCHIVE)}
    assert receipt["artifacts"]["archive_sha256"] == EXPECTED[str(ARCHIVE.relative_to(ROOT))]
    for path, expected in json.loads((OWNER/"source-manifest.json").read_text()).items():
        verify(ROOT/path, expected)
    receipt["completed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt["result"] = "passed"
    (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(probe_output.strip())
    print(f"audited {len(receipt['checked_hashes'])} exact source/evidence hashes; selected Release archive unchanged")

if __name__ == "__main__":
    main()
