#!/usr/bin/env python3
"""Recompile actual presentation tests for the explicit local helper isolation fix.

This intentionally reuses the source-bound final-1 production activation module.
It writes only within this verification lane and never rebuilds the full reactor.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
LANE = Path(__file__).resolve().parent
RUN_NAME = sys.argv[1] if len(sys.argv) > 1 else "run-1"
assert RUN_NAME and all(c.isalnum() or c in "-_" for c in RUN_NAME), "Invalid run name"
LOGS = LANE / RUN_NAME
BUILD = LANE / ".build" / RUN_NAME
PRIOR = ROOT / "verification/common-presentation-lifetime/final-1/receipt.json"
WINDOW = "capability-activation/Tests/MixerCapabilityActivationTests/GuestUIPresentationWindowTests.swift"
EXPECTED_WINDOW = "e44f6a21b3fbd0417ae818328845e5121b2dcabe853504ba2c2d8fa6de8ea9fd"
DEVELOPER = "/Applications/Xcode.app/Contents/Developer"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def tree_digest(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    if BUILD.exists() or LOGS.exists():
        raise SystemExit("Refusing to overwrite an existing run; pass a fresh run name.")
    BUILD.mkdir(parents=True)
    LOGS.mkdir()
    prior = json.loads(PRIOR.read_text())
    retained_source = Path(prior["source"])
    dep_root = ROOT / "verification/guest-ui-teardown-window/.build/current-caaa005-1"
    current_manifest = {}
    retained_manifest = {}
    for path, expected in prior["source_files"].items():
        if path.startswith("capability-activation/Sources/"):
            assert digest(retained_source / path) == expected, path
            current_manifest[path] = expected
            retained_manifest[str(retained_source / path)] = expected
    workspace_production = {rel(p): digest(p) for p in (ROOT / "capability-activation/Sources").rglob("*.swift")}
    workspace_drift = {path: {"retained_sha256": current_manifest.get(path), "workspace_sha256": workspace_production.get(path)}
                       for path in sorted(set(workspace_production) | set(current_manifest))
                       if current_manifest.get(path) != workspace_production.get(path)}
    assert digest(ROOT / WINDOW) == EXPECTED_WINDOW, "Window repair source changed"
    frozen_window = BUILD / "source" / "GuestUIPresentationWindowTests.swift"
    frozen_window.parent.mkdir()
    shutil.copyfile(ROOT / WINDOW, frozen_window)
    assert digest(frozen_window) == EXPECTED_WINDOW
    current_manifest[WINDOW] = EXPECTED_WINDOW
    for path in [
        "capability-activation/Tests/MixerCapabilityActivationTests/GuestUIPresentationModelTests.swift",
        "verification/common-presentation-lifetime/TestMain.swift",
    ]:
        assert digest(retained_source / path) == prior["source_files"][path], path
        assert digest(ROOT / path) == prior["source_files"][path], path
        retained_manifest[str(retained_source / path)] = digest(retained_source / path)
        current_manifest[path] = digest(ROOT / path)
    dependency_manifest = {}
    for path, expected in prior["dependency_artifacts"].items():
        actual = digest(dep_root / path)
        assert actual == expected, path
        dependency_manifest[str(dep_root / path)] = actual
    dependency_receipt = ROOT / prior["dependency_receipt"]
    assert digest(dependency_receipt) == prior["dependency_receipt_sha256"]
    assert digest(prior["testing_macros"]["path"]) == prior["testing_macros"]["sha256"]
    retained_artifacts = {}
    for mode in ["debug", "release", "tsan"]:
        retained_artifacts[mode] = {}
        for path, expected in prior["artifacts"][mode].items():
            if path.endswith(".dylib") or path.endswith(".swiftmodule"):
                assert digest(path) == expected, path
                retained_artifacts[mode][path] = expected
        mode_dir = Path(next(p for p in prior["artifacts"][mode] if p.endswith(".dylib"))).parent
        for suffix in ["swiftdoc", "swiftsourceinfo"]:
            p = mode_dir / f"MixerCapabilityActivation.{suffix}"
            retained_artifacts[mode][str(p)] = digest(p)

    receipt = {
        "started_utc": utc(),
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "repair": "Explicit @MainActor on the existing nativeTree local helper only.",
        "window_source_sha256": EXPECTED_WINDOW,
        "frozen_window_source": str(frozen_window),
        "qualified_source_files": current_manifest,
        "qualified_source_tree_sha256": tree_digest(current_manifest),
        "workspace_production_source_files_at_start": workspace_production,
        "workspace_production_drift_at_start": workspace_drift,
        "retained_source_files": retained_manifest,
        "prior_receipt": rel(PRIOR),
        "prior_receipt_sha256": digest(PRIOR),
        "prior_revision": prior["revision"],
        "dependency_receipt": rel(dependency_receipt),
        "dependency_receipt_sha256": digest(dependency_receipt),
        "dependency_artifacts": dependency_manifest,
        "retained_artifacts": retained_artifacts,
        "testing_macros": prior["testing_macros"],
        "runner_sha256": digest(__file__),
        "commands": [],
        "results": {},
        "scope": "Actual existing GuestUIPresentationModelTests.swift and GuestUIPresentationWindowTests.swift compiled anew in Swift 6 language mode with warnings-as-errors against retained actual complete activation modules and real Swift/C/VM dependencies. Only the frozen repaired window test source replaces a prior test input. Debug, Release (-O), and TSan test executables run locally. Production module is reused byte-for-byte; TSan production instrumentation is exactly the retained final-1 scope and dependency objects remain uninstrumented. Concurrent workspace production edits are recorded but are not represented by the reused module or qualified here.",
        "pending": [
            "Pinned hosted Swift 6.2.4 revalidation after the fix remains pending.",
            "Visible native window opt-in test remains explicitly skipped; no positive display claim.",
            "No physical device discovery or runs; phones remain disconnected.",
            "No immutable published-package consumer, release, signing, store, customer, operational or GA qualification.",
        ],
        "prior_hosted_failure": {
            "receipt": "verification/github-ci-f19a18b/receipt.json",
            "receipt_sha256": digest(ROOT / "verification/github-ci-f19a18b/receipt.json"),
            "log": "verification/github-ci-f19a18b/swift.log",
            "log_sha256": digest(ROOT / "verification/github-ci-f19a18b/swift.log"),
            "revision": "f19a18bac08f61e906acab60dcf3779b36e02ded",
            "url": "https://github.com/snowdamiz/mixer/actions/runs/39995952880",
            "toolchain": "Apple Swift 6.2.4 (swiftlang-6.2.4.1.4 clang-1700.6.4.2)",
            "status": "failure retained; this local run does not replace the hosted result",
            "failure": "The unannotated helper accesses MainActor NSView.bounds, window, isHiddenOrHasHiddenAncestor, and subviews from a nonisolated local function.",
        },
    }
    env = os.environ.copy()
    env["DEVELOPER_DIR"] = DEVELOPER
    env.pop("MIXER_GUEST_UI_VISIBLE_WINDOW", None)

    def run(name, argv, overrides=None):
        command_env = env.copy()
        command_env.update(overrides or {})
        before = time.monotonic()
        result = subprocess.run(argv, cwd=ROOT, env=command_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = LOGS / f"{name}.log"
        log.write_text(result.stdout)
        receipt["commands"].append({
            "name": name, "argv": argv, "cwd": str(ROOT),
            "environment": {"DEVELOPER_DIR": command_env["DEVELOPER_DIR"], "MIXER_GUEST_UI_VISIBLE_WINDOW": "unset", **(overrides or {})},
            "seconds": time.monotonic() - before, "exit": result.returncode,
            "log": rel(log), "sha256": digest(log),
        })
        (LOGS / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"{name} exited {result.returncode}; see {log}")
        return result.stdout

    run("swift-version", ["xcrun", "swiftc", "--version"])
    run("xcode-version", ["xcodebuild", "-version"])
    run("alternate-swift-version", ["xcrun", "swiftc", "--version"], {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"})
    run("alternate-xcode-version", ["xcodebuild", "-version"], {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"})
    run("platform", ["uname", "-a"])
    run("python-version", ["python3", "--version"])
    run("git-version", ["git", "--version"])
    diff = subprocess.check_output(["git", "diff", "--", WINDOW], cwd=ROOT, text=True)
    (LANE / "repair.patch").write_text(diff)
    receipt["repair_patch_sha256"] = digest(LANE / "repair.patch")
    by_name = {c["name"]: c for c in prior["commands"]}
    for mode in ["debug", "release", "tsan"]:
        out = BUILD / mode
        out.mkdir()
        prior_link = by_name[f"{mode}-model-tests-link"]
        argv = list(prior_link["argv"])
        argv[argv.index(str(retained_source / WINDOW))] = str(frozen_window)
        old_cache = argv.index("-module-cache-path") + 1
        argv[old_cache] = str(out / "swift-cache")
        old_output = argv.index("-o") + 1
        argv[old_output] = str(out / "MixerPresentationModels")
        run(f"{mode}-model-tests-link", argv)
        prior_run = by_name[f"{mode}-model-tests"]
        overrides = {k: v for k, v in prior_run["environment"].items() if k != "DEVELOPER_DIR"}
        log = run(f"{mode}-model-tests", [str(out / "MixerPresentationModels")], overrides)
        passed = [line for line in log.splitlines() if line.startswith("✔ Test ") and not line.startswith("✔ Test run ") and "passed after" in line]
        skipped = [line for line in log.splitlines() if " skipped." in line]
        assert len(passed) == 13, (mode, len(passed))
        assert len(skipped) == 1 and "visibleNativeWindowCompletesDisplayAndStopPreventsLaterObservation" in skipped[0], (mode, skipped)
        assert "Test run with 14 tests in 2 suites passed" in log, mode
        assert "WARNING: ThreadSanitizer" not in log and "ThreadSanitizer: data race" not in log, mode
        receipt["results"][mode] = {
            "compiled": True, "exit": 0, "passed_tests": 13, "skipped_tests": 1,
            "skip": "visibleNativeWindowCompletesDisplayAndStopPreventsLaterObservation",
            "executable": str(out / "MixerPresentationModels"),
            "executable_sha256": digest(out / "MixerPresentationModels"),
        }

    assert digest(ROOT / WINDOW) == EXPECTED_WINDOW, "Window source changed during qualification"
    for path, expected in current_manifest.items():
        if not path.startswith("capability-activation/Sources/"):
            assert digest(ROOT / path) == expected, f"Test source changed during qualification: {path}"
    for path, expected in retained_manifest.items():
        assert digest(path) == expected, f"Retained source changed during qualification: {path}"
    for group in retained_artifacts.values():
        for path, expected in group.items():
            assert digest(path) == expected, f"Retained artifact changed: {path}"
    for path, expected in dependency_manifest.items():
        assert digest(path) == expected, f"Dependency artifact changed: {path}"
    receipt["completed_utc"] = utc()
    receipt["result"] = "Actual model and window test compilation and execution passed in Debug, Release, and TSan: 13 passing tests and 1 explicit visible-window skip in each mode. No additional compile issue observed on local Swift 6.4. Hosted pinned Swift 6.2.4 result remains pending."
    (LOGS / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["result"])


if __name__ == "__main__":
    main()
