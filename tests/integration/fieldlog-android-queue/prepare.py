#!/usr/bin/env python3
"""Apply the pinned FieldLog stack in a fresh directory."""
import argparse
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
MIXER = HERE.parents[2]
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
       "GIT_ALLOW_PROTOCOL": "file", "GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1"}


def git(repo, *args):
    return subprocess.check_output(["git", "-C", repo, *args], env=ENV, timeout=45)


def expect(actual, expected, label):
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected}, found {actual}")


def check_hash(path, expected):
    expect(sha256(path.read_bytes()).hexdigest(), expected, str(path))


def check_tree(repo, commit, expected):
    expect(git(repo, "rev-parse", f"{commit}^{{tree}}").decode().strip(), expected, str(repo))


def check_index(repo, expected):
    expect(git(repo, "write-tree").decode().strip(), expected, str(repo))


def archive(repo, destination, object_name):
    archive_path = destination.parent / "source.tar"
    try:
        git(repo, "archive", "--format=tar", f"--output={archive_path}", object_name)
        with tarfile.open(archive_path) as source:
            source.extractall(destination, filter="data")
    finally:
        archive_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path, help="directory produced by fetch.sh")
    parser.add_argument("output", type=Path, help="new directory for prepared sources")
    args = parser.parse_args()
    source_dir, output = args.sources.resolve(), args.output.resolve()
    inputs = json.loads((HERE / "inputs.json").read_text())
    fieldlog, mixer = inputs["fieldLog"], inputs["mixer"]
    fieldlog_checkout, mixer_checkout = source_dir / "fieldlog.git", source_dir / "mixer"
    check_tree(fieldlog_checkout, fieldlog["base"], fieldlog["baseTree"])
    expect(git(mixer_checkout, "rev-parse", "HEAD").decode().strip(), mixer["pair23Revision"], "Mixer HEAD")
    expect(git(mixer_checkout, "status", "--porcelain"), b"", "Mixer checkout status")
    check_tree(mixer_checkout, mixer["pair23Revision"], mixer["pair23Tree"])
    delivery_patch = HERE / "fieldlog-android-queue.patch"
    check_hash(delivery_patch, fieldlog["patchSHA256"])
    check_hash(HERE / "android/pair23-system-libz.patch", inputs["pair23CompatibilityPatchSHA256"])
    for item in fieldlog["inputsInOrder"]:
        check_hash(MIXER / item["path"], item["sha256"])

    os.umask(0o077)
    output.mkdir()
    app = output / "app"
    app.mkdir()
    archive(fieldlog_checkout, app, fieldlog["base"])
    git(app, "init", "--quiet", "--template=")
    git(app, "add", "--all")
    check_index(app, fieldlog["baseTree"])

    for index, item in enumerate(fieldlog["inputsInOrder"], start=1):
        git(app, "apply", "--index", MIXER / item["path"])
        if index == 4:
            check_index(app, fieldlog["pair23SequenceTree"])
    check_index(app, fieldlog["combinedInputTree"])
    git(app, "apply", "--index", delivery_patch)
    check_index(app, fieldlog["candidateTree"])

    backend = "Backend/local_entry_sync.py"
    expect(git(app, "hash-object", backend).decode().strip(), fieldlog["backendBlob"], backend)
    check_hash(app / backend, inputs["backendSHA256"])

    pair = output / "pair23"
    pair.mkdir()
    for name in ("sdk", "cli", "updates", "native/android"):
        destination = pair / name
        destination.mkdir(parents=True)
        archive(mixer_checkout, destination, f"{mixer['pair23Revision']}:{name}")
    for pin in json.loads((pair / "sdk/Package.resolved").read_text())["pins"]:
        name, state = pin["identity"], pin["state"]
        actual = git(source_dir / f"{name}.git", "rev-parse", f"refs/tags/{state['version']}^{{commit}}")
        expect(actual.decode().strip(), state["revision"], name)
    print(f"Prepared FieldLog {fieldlog['candidateTree']} and Mixer Pair23 {mixer['pair23Revision']} in {output}")


if __name__ == "__main__":
    main()
