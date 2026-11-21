#!/usr/bin/env python3
"""Reconstruct the pinned FieldLog app and its Pair25 Mixer checkout."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def git(checkout, *args, data=None):
    return subprocess.run(
        ["git", "-C", str(checkout), *args], input=data, stdout=subprocess.PIPE, check=True,
    ).stdout


def require_bytes(data, expected, label):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch: {label}")
    return data


def require_tree(checkout, expected):
    tree = git(checkout, "write-tree").decode().strip()
    if tree != expected:
        raise ValueError(f"Expected Git tree {expected} in {checkout}, found {tree}")
    return tree


def checkout(path, pin):
    path.mkdir()
    git(path, "init", "--quiet")
    git(path, "remote", "add", "origin", pin["url"])
    if "paths" in pin:
        git(path, "sparse-checkout", "set", "--cone", *pin["paths"])
        git(path, "config", "remote.origin.promisor", "true")
        git(path, "config", "remote.origin.partialclonefilter", "blob:none")
    fetch = ["fetch", "--quiet", "--no-tags", "--depth=1"]
    if "paths" in pin:
        fetch.append("--filter=blob:none")
    git(path, *fetch, "origin", pin["revision"])
    git(path, "checkout", "--quiet", "--detach", "FETCH_HEAD")
    if git(path, "rev-parse", "HEAD").decode().strip() != pin["revision"]:
        raise ValueError(f"Unexpected Git revision in {path}")
    require_tree(path, pin["tree"])
    if git(path, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError(f"Expected a clean checkout: {path}")


def reconstruct(work):
    pins = json.loads((HERE / "pins.json").read_bytes())
    fieldlog, mixer = pins["fieldlog"], pins["mixer"]
    changes = []
    for change in fieldlog["ordinaryChanges"]:
        ref = f'{change["objectRevision"]}:{change["path"]}'
        changes.append(require_bytes(git(REPO, "show", ref), change["sha256"], ref))
    recipe = require_bytes(
        (HERE / "packaging.patch").read_bytes(),
        fieldlog["packagingPatchSHA256"],
        "Pair25 packaging patch",
    )

    work.mkdir()
    app = work / "fieldlog"
    checkout(app, fieldlog)
    for change, data in zip(fieldlog["ordinaryChanges"], changes, strict=True):
        if destination := change.get("destination"):
            with (app / destination).open("xb") as file:
                file.write(data)
            git(app, "add", "--", destination)
        else:
            git(app, "apply", "--index", "--whitespace=nowarn", "-", data=data)
        require_tree(app, change["tree"])
    ordinary_tree = require_tree(app, fieldlog["ordinaryTree"])
    git(app, "apply", "--index", "--unidiff-zero", "-", data=recipe)
    packaging_tree = require_tree(app, fieldlog["packagingTree"])
    checkout(work / "mixer", mixer)
    return {
        "ordinaryFieldLogTree": ordinary_tree,
        "packagingFieldLogTree": packaging_tree,
        "mixerRevision": mixer["revision"],
        "mixerTree": mixer["tree"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path, help="New build directory with an existing parent")
    args = parser.parse_args()
    print(json.dumps(reconstruct(args.work.resolve()), indent=2))
