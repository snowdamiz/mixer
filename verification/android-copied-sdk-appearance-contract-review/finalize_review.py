#!/usr/bin/env python3
"""Seal only this review's owned outputs; never run producer/product harnesses."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import platform
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = ROOT / "docs/android-copied-sdk-appearance-contract-review.md"
PIN = json.loads((HERE / "pin-report.json").read_text())
PRODUCER = "verification/android-copied-sdk-appearance-contract"
SOURCE = HERE / "inputs" / PRODUCER / "source-inputs"


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


seal = json.loads((HERE / "inputs" / PRODUCER / "seal.json").read_text())
assert identity(HERE / "inputs" / PRODUCER / "seal.json")["sha256"] == PIN["source_seal_sha256"]
assert len(seal["files"]) == 87
for path, expected in seal["files"].items():
    assert identity(HERE / "inputs" / path) == expected, path
    assert identity(ROOT / path) == expected, ("producer frozen input changed", path)
assert sum(x["bytes"] for x in seal["files"].values()) == 971695
probe = json.loads((HERE / "probe-result.json").read_text())
assert probe["all_42_match_frozen_packaging_source_manifest"]
assert all(x["absent"] for x in json.loads((HERE / "cleanup.json").read_text()))
assert all(x["exit_code"] == 0 for x in json.loads((HERE / "commands.json").read_text()))
for path in [DOC, HERE / "review_probe.py", HERE / "finalize_review.py"]:
    text = path.read_text()
    assert text.endswith("\n"), ("missing final newline", path)
    assert all(line == line.rstrip() for line in text.splitlines()), ("trailing whitespace", path)
    if path.suffix == ".py":
        ast.parse(text, filename=str(path))

references = {
    "sdk/Package.swift": [[1, 26]],
    "cli/Package.swift": [[1, 16]],
    "cli/Sources/MixerBuild/ProjectGenerator.swift": [[12, 66], [239, 258]],
    "cli/Sources/MixerBuild/Configuration.swift": [[81, 115]],
    "cli/Sources/MixerBuild/AndroidProject.swift": [[28, 148], [163, 196]],
    "cli/Sources/MixerBuild/Resources/android-build.py": [[66, 84], [124, 151], [251, 278], [325, 377]],
    "cli/Sources/MixerCLI/main.swift": [[77, 85], [94, 98]],
    "native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift": [[1, 70]],
    "native/android/app/src/dev/mixer/android/UiPacket.java": [[16, 25]],
    "native/android/app/src/dev/mixer/android/MixerActivity.java": [[9, 16]],
    "native/android/bridge/mixer_android_v2.h": [[10, 47]],
    "native/android/contracts/android-profile-v1.json": [[1, 21]],
    "mixer-product-plan.md": [[332, 342], [404, 417], [602, 606], [677, 681], [859, 859]],
}
index = {}
for path, ranges in references.items():
    lines = (SOURCE / path).read_text().splitlines()
    index[path] = {"source_identity": identity(SOURCE / path),
                   "excerpts": [{"start": start, "end": min(end, len(lines)),
                                  "lines": [{"line": n, "text": lines[n-1]}
                                            for n in range(start, min(end, len(lines)) + 1)]}
                                 for start, end in ranges]}
(HERE / "source-review-index.json").write_text(json.dumps(index, indent=2) + "\n")

check = subprocess.run(["git", "diff", "--check", "--", str(DOC.relative_to(ROOT)), str(HERE.relative_to(ROOT))],
                       cwd=ROOT, capture_output=True)
(HERE / "diff-check.stdout").write_bytes(check.stdout)
(HERE / "diff-check.stderr").write_bytes(check.stderr)
assert check.returncode == 0
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
findings = [
    {"id": "R1", "priority": "P1", "status": "required-before-root-selection",
     "summary": "Version-specific SDK manifests can redirect the Core/UI graph while the proposed exact map remains equal.",
     "evidence": "host-probe/*-dump-package.stdout and probe-result.json", "probe_executed": True},
    {"id": "R2", "priority": "P2", "status": "required-before-root-selection",
     "summary": "Swift CLI build entrypoints must admit before generic SDK/adapter hashing and tools, as the direct driver will.",
     "evidence": "Frozen ProjectGenerator.swift:239-258 and AndroidProject.swift:118-124", "probe_executed": False},
    {"id": "R3", "priority": "P2", "status": "required-before-root-selection",
     "summary": "Specify and test rendered staged driver inspection versus lazy profile decoding for the raw template.",
     "evidence": "Frozen AndroidProject.swift:70-102 and ProjectGenerator.swift:44-47", "probe_executed": False},
]
receipt = {
    "schema": "mixer.independent-contract-review.receipt.v1", "recorded_utc": now,
    "status": "contract-revisions-required-awaiting-root-selection",
    "source_revision": PIN["source_revision"], "proposal_sha256": PIN["proposal_sha256"],
    "producer_seal_sha256": PIN["source_seal_sha256"], "producer_members_verified": 87,
    "producer_bytes_verified": 971695, "all_producer_members_still_equal": True,
    "review_doc": identity(DOC), "findings": findings,
    "executed": [
        {"argv": ["python3", "-B", "verification/android-copied-sdk-appearance-contract-review/review_probe.py"],
         "cwd": str(ROOT), "exit_code": 0, "stdout": identity(HERE / "review-probe.stdout"),
         "stderr": identity(HERE / "review-probe.stderr"),
         "scope": "Own independent frozen-data and host-only manifest-selection probe; internal commands in commands.json."},
        {"argv": ["python3", "-B", "verification/android-copied-sdk-appearance-contract-review/finalize_review.py"],
         "cwd": str(ROOT), "scope": "Own frozen member validation, source-reference index, scoped diff check and review seal."},
        {"argv": ["git", "diff", "--check", "--", str(DOC.relative_to(ROOT)), str(HERE.relative_to(ROOT))],
         "cwd": str(ROOT), "exit_code": check.returncode,
         "stdout": identity(HERE / "diff-check.stdout"), "stderr": identity(HERE / "diff-check.stderr")},
    ],
    "tool_versions": {"python": platform.python_version(),
                      "git": subprocess.check_output(["git", "--version"], text=True).strip(),
                      "swift": (HERE / "host-probe/swift-version.stdout").read_text().strip()},
    "source_review_index": "source-review-index.json", "command_details": "commands.json",
    "owned_source_checks": "Markdown/Python final newline and trailing whitespace checked directly, including untracked files; both reviewer scripts parsed with Python ast.parse.",
    "additional_context": "supplemental-manifest.json; contracts/ui-v1.json is separately pinned, outside the producer seal.",
    "host_compiler_execution": "Two host SwiftPM manifest evaluations; no product module compilation or execution.",
    "whole_build_or_APK_created": False, "native_runtime_or_capture_started": False,
    "process_discovery": False, "producer_harness_imported_or_executed": False,
    "product_files_changed": False, "implementation_selected": False, "implementation_accepted": False,
    "public_V2_accepted": False, "GA_qualified": False, "committed_or_pushed": False,
    "cleanup": "Owned host probe cache/config/security/scratch/module-cache directories absent; exact fixtures retained. No owned background process or native instance remains.",
    "pending": ["Root selection of corrected contract after separate packaging implementation review",
                "Bounded implementation and copied-consumer Swift/Java API/wire tests",
                "Target ABI/runtime/lifecycle and OS/resource/font/accessibility/design/input qualification",
                "Public V2 routing and installed capture/environment integration",
                "Immutable signed CLI/SDK distribution, provenance and separate-repository FieldLog consumption",
                "Physical matrix and release/store/operational/GA gates"],
    "scope": "Independent frozen-source contract review and bounded host manifest-selection evidence only. No implementation or release acceptance.",
}
(HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
handoff = {"schema": 1, "recorded_utc": now, "status": receipt["status"],
           "proposal_sha256": PIN["proposal_sha256"], "producer_seal_sha256": PIN["source_seal_sha256"],
           "review_doc": {"path": str(DOC.relative_to(ROOT)), **identity(DOC)},
           "receipt": {"path": str((HERE / "receipt.json").relative_to(ROOT)), **identity(HERE / "receipt.json")},
           "findings": findings, "implementation_selected": False, "implementation_accepted": False,
           "GA_qualified": False, "native_runtime_or_capture_started": False,
           "recommendation": "Root may select the corrected narrow development source-pair contract after R1/R2/R3 are explicit and separate packaging review is accepted."}
(HERE / "handoff.json").write_text(json.dumps(handoff, indent=2) + "\n")
files = {str(DOC.relative_to(ROOT)): identity(DOC)}
for path in sorted(HERE.rglob("*")):
    if path.is_file() and path != HERE / "seal.json":
        assert not path.is_symlink()
        files[str(path.relative_to(ROOT))] = identity(path)
canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
sealed = {"schema": "mixer.independent-contract-review.seal.v1", "files": files,
          "files_map_sha256": hashlib.sha256(canonical).hexdigest(),
          "scope": "Exact repository-relative owned review members; excludes this self-referential seal only."}
(HERE / "seal.json").write_text(json.dumps(sealed, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": receipt["status"], "review_doc": identity(DOC),
                  "seal": identity(HERE / "seal.json"), "members": len(files),
                  "bytes": sum(x["bytes"] for x in files.values()),
                  "findings": [x["id"] for x in findings]}, indent=2))
