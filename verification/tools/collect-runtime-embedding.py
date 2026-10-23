#!/usr/bin/env python3
"""Recover only the initial embedding collector's object-name mismatch.

Preserves the failed receipt. Checks its successful command logs, immutable
source and actual compiled artifacts before writing a separate completion record.
Does not rerun tests or convert failed test/build commands into successful ones.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    require(re.fullmatch(r"[a-z0-9-]+", args.name), "invalid run name")
    evidence = ROOT / "verification" / ("runtime-embedding-" + args.name)
    work = ROOT / "verification/local" / ("runtime-embedding-" + args.name)
    previous = evidence / "receipt.json"
    receipt_bytes = previous.read_bytes()
    receipt = json.loads(receipt_bytes)
    require(receipt["status"] == "failed" and receipt["error"] == "Missing compiled identity object", "unrecognized failure")
    require(receipt["sourceRevision"] == "ce8f2c921dab12a0e859cb93366cef74277c6ef4", "unexpected initial source")
    source = work / "source"
    for path, expected in receipt["sourceFiles"].items():
        frozen = subprocess.check_output(["git", "show", receipt["sourceRevision"] + ":" + path], cwd=ROOT)
        require(digest(frozen) == expected == digest((source / path).read_bytes()), "source mismatch: " + path)
    for path, expected in receipt["generatedSourceFiles"].items():
        require(digest((work / "consumer" / path).read_bytes()) == expected, "generated source mismatch: " + path)
    commands = {item["name"]: item for item in receipt["commands"]}
    expected_names = {"source-export", "swift-version", "cross-swift-version", "python-version", "identity-cli-build",
                      "identity-cli-location", "tests-normal", "tests-optimized-python", "capture", "emit", "inspect",
                      "host-release-build", "host-release-location", "host-release-run", "ios-compile", "android-compile"}
    require(set(commands) == expected_names and len(commands) == len(receipt["commands"]), "command coverage mismatch")
    for command in commands.values():
        require(command["exitCode"] == 0 and not command["timedOut"] and not command["outputLimitExceeded"], "command failed")
        for stream in ("stdout", "stderr"):
            entry = command[stream]; data = (evidence / entry["path"]).read_bytes()
            require(digest(data) == entry["sha256"] and len(data) == entry["bytes"], "output mismatch")
    for mode in ("normal", "optimized-python"):
        text = (evidence / ("tests-" + mode + ".stderr")).read_text()
        require(re.search(r"^Ran 19 tests in", text, re.MULTILINE) and "\nOK\n" in text, "test count mismatch")
    policy = json.loads((evidence / "host-release-run.stdout").read_bytes())
    require(policy == json.loads((evidence / "inspect.stdout").read_bytes())["installedRuntime"], "compiled policy mismatch")
    emitted = json.loads((evidence / "embedding.json").read_bytes())
    require(emitted == json.loads((evidence / "emit.stdout").read_bytes()), "emission result mismatch")
    require(digest((evidence / "MixerInstalledRuntime.swift").read_bytes()) == emitted["source_sha256"], "source byte mismatch")
    require(digest((evidence / "descriptor.json").read_bytes()) == emitted["descriptor_sha256"], "descriptor byte mismatch")
    require(policy["runtime"] == emitted["fingerprint"], "compiled fingerprint mismatch")
    binary = Path(commands["host-release-run"]["command"][0])
    require(digest(binary.read_bytes()) == receipt["compiledConsumer"]["binarySHA256"], "binary mismatch")
    objects = {}
    for target, name, expected_type in [("ios", "MixerInstalledRuntime.o", "Mach-O 64-bit object arm64"),
                                         ("android", "MixerInstalledRuntime.swift.o", "ELF 64-bit LSB relocatable, ARM aarch64")]:
        found = list((work / target).rglob(name))
        require(len(found) == 1, "ambiguous object: " + target)
        path = found[0]
        command = ["/usr/bin/file", "-b", str(path)]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        require(expected_type in result.stdout, "unexpected object architecture")
        objects[target] = {"path": str(path.relative_to(work)), "sha256": digest(path.read_bytes()),
                           "bytes": path.stat().st_size, "inspection": {"command": command, "exitCode": result.returncode,
                           "stdout": result.stdout, "stderr": result.stderr}}
    require(previous.read_bytes() == receipt_bytes, "previous receipt mutated")
    completed = {"schema": 1, "status": "passed scoped compilation and artifact collection after collector correction",
                 "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "sourceRevision": receipt["sourceRevision"], "sourceDigest": receipt["sourceDigest"],
                 "previousFailedReceipt": {"path": str(previous.relative_to(ROOT)), "sha256": digest(receipt_bytes),
                 "reason": "iOS uses MixerInstalledRuntime.o; original glob only found Android .swift.o. All 16 commands passed."},
                 "collectorSHA256": digest(Path(__file__).read_bytes()), "invocation": ["python3", "-B", str(Path(__file__).relative_to(ROOT)), "--name", args.name],
                 "sourceFilesMatchedToGitAndExport": len(receipt["sourceFiles"]), "generatedSourceFilesMatched": len(receipt["generatedSourceFiles"]),
                 "commandOutputsMatched": len(commands) * 2, "testFunctionsPerMode": 19, "commandsRerun": False,
                 "compiledConsumer": receipt["compiledConsumer"], "mobileObjects": objects,
                 "limitations": receipt["limitations"]}
    destination = evidence / "completion-receipt.json"
    with destination.open("x") as stream:
        stream.write(json.dumps(completed, indent=2) + "\n")
    print(json.dumps({"status": completed["status"], "receipt": str(destination)}, indent=2))


if __name__ == "__main__":
    main()
