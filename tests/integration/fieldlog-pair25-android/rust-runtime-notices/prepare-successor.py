#!/usr/bin/env python3
"""Reconstruct the exact FieldLog photo composition and apply the Pair25 notice patch."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
RECIPE = "tests/integration/fieldlog-pair25-android"
RECIPE_REVISION = "1e2de0130d001ef9ada0001b59f9ae8b7f67b72a"
RECIPE_FILES = {
    "README.md": "ed60e2e3a9dca44e0fce80b77c6467ad5057ce91ca5b992934d965ac06166b5c",
    "packaging.patch": "ea477b7c04a4f09e3093b5ad685e421df8f7d8d7664776b443f5df98f0993a2a",
    "pins.json": "8862a93f9d9cd617abe9a4d3707f364fb8ac8e64bb64df9431feea36ee843e42",
    "prepare-sources.py": "b544ac4a82f1b4dff5ded8ef637f73d50cf4a1e70b9043d28640a2960f6fd748",
}
PHOTO_REF = ("6179aab15f10348e04492ab70922f3dfc566774d:"
             "verification/receipts/fieldlog-d2-entry-editor-photos-e39a5ea3.patch")
PHOTO_SHA256 = "5866c988222c8042b670511bf9920965321086ff8dc378c7744368e3403f7b4f"
PHOTO_TREE = "00406fe735a3e48b075dd545d8df77670caab336"
COMPOSED_TREE = "f4422116bb914c3c549f8ba31f1e30f7b94e0e9d"
NOTICE_PATCH_SHA256 = "998fe05c85e2e5d4870c234816b8a18e19c39513fc5cbebbae768ac1acbc87fa"
SUCCESSOR_TREE = "0c38770065656bf7c5a2aa768055ff8b453b082d"


def git(directory, *args, data=None):
    env = os.environ | {"GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(
        ["git", "-C", directory, *args], input=data, stdout=subprocess.PIPE,
        env=env, check=True, timeout=60,
    ).stdout


def checked(data, expected, label):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch: {label}")
    return data


def require_tree(path, expected):
    tree = git(path, "write-tree").decode().strip()
    if tree != expected:
        raise ValueError(f"Expected {expected}, got {tree} in {path}")
    return tree


def prepare(work, mixer):
    recipe = {
        name: checked(git(mixer, "show", f"{RECIPE_REVISION}:{RECIPE}/{name}"), digest, name)
        for name, digest in RECIPE_FILES.items()
    }
    photo = checked(git(mixer, "show", PHOTO_REF), PHOTO_SHA256, PHOTO_REF)
    notice_patch = checked((HERE / "fieldlog-packaging.patch").read_bytes(),
                           NOTICE_PATCH_SHA256, "FieldLog notice delta")
    pins = json.loads(recipe["pins.json"])
    fieldlog, sdk = pins["fieldlog"], pins["mixer"]
    work.mkdir(mode=0o700)
    app = work / "fieldlog"
    app.mkdir()
    git(app, "init", "--quiet")
    git(app, "fetch", "--quiet", "--no-tags", "--depth=1", fieldlog["url"], fieldlog["revision"])
    git(app, "checkout", "--quiet", "--detach", "FETCH_HEAD")
    if git(app, "rev-parse", "HEAD").decode().strip() != fieldlog["revision"]:
        raise ValueError("FieldLog checkout does not match the pinned revision")
    require_tree(app, fieldlog["tree"])
    for change in fieldlog["ordinaryChanges"]:
        ref = change["objectRevision"] + ":" + change["path"]
        data = checked(git(mixer, "show", ref), change["sha256"], ref)
        if destination := change.get("destination"):
            with (app / destination).open("xb") as stream:
                stream.write(data)
            git(app, "add", "--", destination)
        else:
            git(app, "apply", "--index", "--whitespace=nowarn", "-", data=data)
        require_tree(app, change["tree"])
    require_tree(app, fieldlog["ordinaryTree"])
    git(app, "apply", "--index", "--whitespace=error", "-", data=photo)
    require_tree(app, PHOTO_TREE)
    git(app, "apply", "--index", "--unidiff-zero", "--whitespace=error", "-", data=recipe["packaging.patch"])
    require_tree(app, COMPOSED_TREE)
    git(app, "apply", "--index", "--whitespace=error", "-", data=notice_patch)
    require_tree(app, SUCCESSOR_TREE)

    # Reuse the pinned Git objects in the supplied Mixer checkout. Sparse
    # checkout leaves the immutable HEAD and tree intact.
    checkout = work / "mixer"
    checkout.mkdir()
    git(checkout, "init", "--quiet")
    objects = Path(git(mixer, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()) / "objects"
    (checkout / ".git/objects/info/alternates").write_text(str(objects) + "\n")
    git(checkout, "sparse-checkout", "set", "--cone", *sdk["paths"], "contracts", "runtime/Sources/CMixerVM/include")
    git(checkout, "checkout", "--quiet", "--detach", sdk["revision"])
    require_tree(checkout, sdk["tree"])
    if (git(app, "diff", "--name-only") or git(app, "ls-files", "--others", "--exclude-standard")
            or git(checkout, "status", "--porcelain", "--untracked-files=all")):
        raise ValueError("Unexpected worktree changes after composition")
    return pins


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixer", type=Path, required=True)
    parser.add_argument("work", type=Path, help="New directory with an existing parent")
    args = parser.parse_args()
    prepare(args.work.resolve(), args.mixer.resolve(strict=True))
    print(SUCCESSOR_TREE)
