#!/usr/bin/env python3
"""Explicit-source independent actual-observer runner. Not executed at authoring seal."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

HOST = pathlib.Path(__file__).resolve().parent
PACKET = HOST.parent
REPO = PACKET.parent.parent
MANIFEST = PACKET / "authored-sources-v2.sha256"
HARNESS = "dev/mixer/android/ObserverIndependentHostTests.java"
LEAVES = (
    "android/app/Activity.java",
    "android/app/UiModeManager.java",
    "android/content/ComponentCallbacks.java",
    "android/content/ContentResolver.java",
    "android/content/Context.java",
    "android/content/res/Configuration.java",
    "android/content/res/Resources.java",
    "android/database/ContentObserver.java",
    "android/graphics/Insets.java",
    "android/net/Uri.java",
    "android/os/Build.java",
    "android/os/Handler.java",
    "android/os/LocaleList.java",
    "android/os/Looper.java",
    "android/provider/Settings.java",
    "android/util/DisplayMetrics.java",
    "android/util/TypedValue.java",
    "android/view/View.java",
    "android/view/ViewTreeObserver.java",
    "android/view/Window.java",
    "android/view/WindowInsets.java",
    "android/view/accessibility/AccessibilityManager.java",
    "android/widget/FrameLayout.java",
    "dev/mixer/android/AppearanceDescriptorV2.java",
    "dev/mixer/android/AppearanceGeometryV2.java",
    "dev/mixer/android/AppearanceResolverV2.java",
    "dev/mixer/android/IndependentFaults.java",
    "dev/mixer/android/NativeRenderer.java",
)
STRIP = ("CLASSPATH", "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "JDK_JAVAC_OPTIONS")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(path: pathlib.Path, expected: str) -> bytes:
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError("Frozen identity mismatch: " + str(path))
    return data


def checked_tool(path: str, expected: str) -> pathlib.Path:
    tool = pathlib.Path(path)
    if not tool.is_absolute():
        raise ValueError("Tool must be explicitly selected by absolute path")
    tool = tool.resolve(strict=True)
    identity(tool, expected)
    return tool


def text(value: str | bytes | None) -> str:
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value or ""


def command(argv: list[str], env: dict[str, str], receipt: dict, timeout: int = 45) -> subprocess.CompletedProcess:
    record = {"argv": argv, "timeout_seconds": timeout, "cwd": str(PACKET)}
    receipt["commands"].append(record)
    try:
        result = subprocess.run(argv, cwd=PACKET, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=timeout, check=False)
        record.update(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr, timed_out=False)
        if result.returncode:
            raise RuntimeError("Independent command failed: " + repr(argv))
        return result
    except subprocess.TimeoutExpired as failure:
        record.update(exit_code=None, stdout=text(failure.stdout), stderr=text(failure.stderr), timed_out=True)
        raise


def source_manifest(expected_hash: str) -> list[pathlib.Path]:
    data = identity(MANIFEST, expected_hash)
    members: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if relative in members or len(digest) != 64:
            raise ValueError("Malformed/duplicate frozen source entry")
        members[relative] = digest
    required = {str((HOST / name).relative_to(REPO)) for name in (*LEAVES, HARNESS, pathlib.Path(__file__).name)}
    if set(members) != required:
        raise ValueError("Frozen independent source inventory differs from explicit list")
    for relative, digest in members.items():
        identity(REPO / relative, digest)
    return [HOST / name for name in (*LEAVES, HARNESS)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observer", required=True)
    parser.add_argument("--observer-sha256", required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--javac", required=True)
    parser.add_argument("--javac-sha256", required=True)
    parser.add_argument("--java", required=True)
    parser.add_argument("--java-sha256", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    receipt_path = pathlib.Path(args.receipt).resolve()
    if not receipt_path.is_relative_to(PACKET) or receipt_path == MANIFEST:
        raise ValueError("Receipt must be a new owned packet path")
    if receipt_path.exists():
        raise ValueError("Refusing to overwrite an existing receipt")
    receipt = {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "running", "commands": [], "stripped_environment_variables": list(STRIP),
        "observer": {"path": args.observer, "sha256": args.observer_sha256},
        "independent_source_manifest_sha256": args.source_manifest_sha256,
        "scope": "Actual admitted observer compiled with independent modeled leaves. Host lifecycle evidence only; no Android runtime, capture, public API, publication or GA evidence.",
        "native_or_capture_or_ui_or_process_discovery": False,
    }
    scratch: pathlib.Path | None = None
    try:
        sources = source_manifest(args.source_manifest_sha256)
        observer = pathlib.Path(args.observer)
        if not observer.is_absolute():
            raise ValueError("Observer must be an absolute root-admitted frozen source path")
        observer_data = identity(observer, args.observer_sha256)
        javac = checked_tool(args.javac, args.javac_sha256)
        java = checked_tool(args.java, args.java_sha256)
        receipt["tools"] = {"javac": {"path": str(javac), "sha256": args.javac_sha256},
                            "java": {"path": str(java), "sha256": args.java_sha256}}
        env = {key: value for key, value in os.environ.items() if key not in STRIP}
        command([str(javac), "-version"], env, receipt)
        command([str(java), "-version"], env, receipt)
        scratch_parent = PACKET / "execution"
        scratch_parent.mkdir(exist_ok=True)
        scratch = pathlib.Path(tempfile.mkdtemp(prefix="independent-observer-", dir=scratch_parent))
        empty = scratch / "empty"; empty.mkdir()
        classes = scratch / "classes"; classes.mkdir()
        copied_observer = scratch / "NativeEnvironmentV2.java"
        copied_observer.write_bytes(observer_data)
        receipt["source_files"] = [{"path": str(path), "sha256": sha(path.read_bytes())} for path in sources]
        command([str(javac), "--release", "17", "-Xlint:all", "-Werror", "-proc:none",
                 "-classpath", str(empty), "-sourcepath", str(empty), "-d", str(classes),
                 str(copied_observer), *map(str, sources)], env, receipt)
        receipt["classes"] = [{"path": str(path.relative_to(classes)), "sha256": sha(path.read_bytes())}
                              for path in sorted(classes.rglob("*.class"))]
        result = command([str(java), "-ea", "-classpath", str(classes),
                          "dev.mixer.android.ObserverIndependentHostTests"], env, receipt)
        if "INDEPENDENT_OBSERVER_SUCCESS cases=" not in result.stdout:
            raise RuntimeError("Independent harness did not report complete success")
        identity(observer, args.observer_sha256)
        source_manifest(args.source_manifest_sha256)
        receipt["status"] = "passed-host-modeled-controls"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as failure:
        receipt["status"] = "failed"
        receipt["failure"] = {"type": type(failure).__name__, "message": str(failure)}
    finally:
        if scratch is not None:
            shutil.rmtree(scratch)
            receipt["cleanup"] = {"owned_scratch": str(scratch), "removed": not scratch.exists()}
        else:
            receipt["cleanup"] = {"owned_scratch": None, "removed": True}
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path)}))
    return 0 if receipt["status"] == "passed-host-modeled-controls" else 1


if __name__ == "__main__":
    raise SystemExit(main())
