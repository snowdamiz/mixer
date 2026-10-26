#!/usr/bin/env python3
"""Exact two-source Java host harness; output/scratch stay in this lane's packet."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "verification/android-public-owner-core"
SOURCES = ["native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java",
           "native/android/tests/OwnerLifecycleV2HostTests.java"]
DEFAULT_JDK = "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jdk", default=os.environ.get("MIXER_JDK", DEFAULT_JDK))
    parser.add_argument("--attempt", required=True, help="New simple name under the owned attempts directory")
    args = parser.parse_args()
    if not args.attempt or not args.attempt.isascii() or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in args.attempt):
        parser.error("attempt must be a simple ASCII name")
    jdk = Path(args.jdk).resolve(strict=True)
    output = PACKET / "attempts" / args.attempt
    for parent in (PACKET, PACKET / "attempts", output):
        if parent.is_symlink():
            parser.error("owned output path must not be a symlink")
    output.mkdir(parents=True, exist_ok=False)
    scratch = output / "scratch"
    scratch.mkdir()
    inputs = output / "inputs"
    inputs.mkdir()
    env = os.environ.copy()
    stripped = []
    for key in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "JDK_JAVAC_OPTIONS", "CLASSPATH"):
        if key in env:
            stripped.append(key)
            del env[key]
    commands = []
    errors = []
    class_files = {}
    test_result = None
    cleanup = {"scratch": str(scratch), "removed": False, "owned_children_waited": True,
               "other_processes_queried_or_changed": False}
    bound = {}

    def run(label, argv):
        command = {"label": label, "argv": [str(a) for a in argv], "cwd": str(ROOT), "timeout_seconds": 45}
        try:
            result = subprocess.run(command["argv"], cwd=ROOT, env=env, capture_output=True, timeout=45)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as failure:
            code, stdout, stderr = None, failure.stdout or b"", failure.stderr or b""
            command["timeout"] = True
            # subprocess.run has killed and waited for its own direct child.
        except OSError as failure:
            code, stdout, stderr = None, b"", str(failure).encode()
            command["launch_failure"] = True
        command["exit_code"] = code
        for name, value in (("stdout", stdout), ("stderr", stderr)):
            target = output / f"{label}.{name}"
            target.write_bytes(value)
            command[name] = {"path": target.relative_to(ROOT).as_posix(), **identity(value)}
        commands.append(command)
        if code != 0:
            raise RuntimeError(f"{label} failed ({code}); retained streams")
        return stdout

    try:
        for path in SOURCES:
            data = (ROOT / path).read_bytes()
            if (ROOT / path).is_symlink():
                raise RuntimeError("source symlink not accepted")
            destination = inputs / Path(path).name
            destination.write_bytes(data)
            bound[path] = {**identity(data), "compiled_copy": destination.relative_to(ROOT).as_posix()}
        run("context", ["git", "rev-parse", "HEAD"])
        run("git-version", ["git", "--version"])
        run("javac-version", [jdk / "bin/javac", "--version"])
        run("java-version", [jdk / "bin/java", "--version"])
        classes = scratch / "classes"
        classes.mkdir()
        classpath = scratch / "empty-classpath"
        classpath.mkdir()
        sourcepath = scratch / "empty-sourcepath"
        sourcepath.mkdir()
        run("compile", [jdk / "bin/javac", "--release", "17", "-Xlint:all", "-Werror", "-proc:none",
                        "-classpath", classpath, "-sourcepath", sourcepath, "-d", classes,
                        *[inputs / Path(path).name for path in SOURCES]])
        class_files = {path.relative_to(classes).as_posix(): identity(path.read_bytes())
                       for path in sorted(classes.rglob("*.class"))}
        if not class_files:
            raise RuntimeError("no compiled classes")
        test_output = run("tests", [jdk / "bin/java", "-ea", "-Xmx128m", "-XX:ActiveProcessorCount=1",
                                    "-cp", classes, "dev.mixer.android.OwnerLifecycleV2HostTests"])
        test_result = json.loads(test_output)
        if test_result.get("status") != "pass" or test_result.get("tests") != len(test_result.get("cases", [])):
            raise RuntimeError("incomplete structured test result")
    except Exception as failure:
        errors.append({"type": type(failure).__name__, "message": str(failure)})
    finally:
        try:
            if scratch.is_symlink():
                raise RuntimeError("owned scratch replaced by symlink; refuse removal")
            shutil.rmtree(scratch)
            cleanup["removed"] = not scratch.exists()
        except Exception as failure:
            cleanup["failure"] = str(failure)
            errors.append({"type": type(failure).__name__, "message": str(failure)})
        write(output / "commands.json", commands)
        write(output / "source-bindings.json", {"sources": bound, "runner": identity(Path(__file__).read_bytes())})
        write(output / "classes.json", class_files)
        write(output / "cleanup.json", cleanup)
        write(output / "receipt.json", {
            "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "argv": [sys.executable, *sys.argv], "python_version": sys.version,
            "scope": "Actual host ownership-decision core only; no Android toolkit, JNI or native behavior",
            "jdk": str(jdk), "removed_java_option_environment_names": stripped,
            "status": "pass" if not errors else "fail", "test_result": test_result,
            "source_files": len(bound), "class_files": len(class_files), "cleanup": cleanup,
            "errors": errors, "public_V2_or_API28_qualification": False,
            "native_runtime_UI_capture_or_process_discovery": False
        })
    print(json.dumps({"status": "pass" if not errors else "fail", "attempt": str(output),
                      "result": test_result, "class_files": len(class_files), "errors": errors,
                      "scratch_removed": cleanup["removed"]}, sort_keys=True))
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
