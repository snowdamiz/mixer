#!/usr/bin/env python3
"""Prepare the maintained Pair25 app with the complete runtime notice inventory."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

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
L07_MIXER_BASE = "24b8efb98ee53d543a68c297e99bcfe4243a8c26"
L07_PAIRED_TREE = "7b2b98f098559f57ce39e213321478058c289c5a"
L07_TREE = "34810962320bdfb7877b8bbdd065495e9ec1e2bb"
L07_PATCH_SHA256 = "f70c721ea18541b2bbe8100d327ccca534058b1f4b36dcfcdde42786347d3931"
L07_PAIRED_PATCHES = (
    ("fieldlog-android-project-picker-ad6c8dba",
     "53a221508c9d2fee4c6821e9954aaf8f880a4a9d5a4c77af82e516e64335d85a"),
    ("fieldlog-apple-project-pagination-00406fe7",
     "4fbbb6e6c63afd886df2054d36c1024e3cdcab014a4307d14c1a896900ae2c4e"),
    ("fieldlog-android-camera-corrected-26bbde4a",
     "1e604e26655a723720b4f53ce3c50610b6c99bdb9666c513dd2d6282e67adcc8"),
    ("fieldlog-android-queue-from-camera-cb54a33d",
     "5ccb079b9d6c20a2ada389424608e35ec5212c18b41a6637d74184f9c6665cb6"),
    ("fieldlog-site-map-shared-26bbde4a",
     "7d8c60759f7012946a4de300963ce88c9c27c567e833e40e31d0d4b3dfd357fa"),
    ("fieldlog-android-site-map-pair25-87c95c5a",
     "fccd104d5908ffe56034ad473190b235864b434b89942aa80e5f95cf114ca0fc"),
    ("fieldlog-ios-entry-camera-corrected-e10048f8",
     "0e3a7262b22217c501a0dc6a3dd7e964ddb59e92794797f397accf19bcbf39f2"),
    ("fieldlog-ios-site-map-rename-33398784",
     "53ef2d543346b0fb102382bd88dea4a53da23518c83c6aa323556c25cd53846c"),
)


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


def prepare_sources(work, mixer):
    recipe = {
        name: checked(git(mixer, "show", f"{RECIPE_REVISION}:{RECIPE}/{name}"), digest, name)
        for name, digest in RECIPE_FILES.items()
    }
    photo = checked(git(mixer, "show", PHOTO_REF), PHOTO_SHA256, PHOTO_REF)
    notice_patch = checked((HERE / "fieldlog-packaging.patch").read_bytes(),
                           NOTICE_PATCH_SHA256, "FieldLog notice delta")
    pins = json.loads(recipe["pins.json"])
    fieldlog, sdk = pins["fieldlog"], pins["mixer"]
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


def compose_l07(work, mixer):
    app = work / "fieldlog"
    require_tree(app, SUCCESSOR_TREE)
    for name, digest in L07_PAIRED_PATCHES:
        ref = f"{L07_MIXER_BASE}:verification/receipts/{name}.patch"
        patch = checked(git(mixer, "show", ref), digest, ref)
        git(app, "apply", "--index", "--unidiff-zero", "--whitespace=error", "-", data=patch)
    require_tree(app, L07_PAIRED_TREE)
    patch = checked((HERE / "fieldlog-l07-notices.patch").read_bytes(), L07_PATCH_SHA256, "L07 notice delta")
    git(app, "apply", "--index", "--whitespace=error", "-", data=patch)
    return require_tree(app, L07_TREE)


def prepare(work, mixer, *, historical_rust_only=False):
    work.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix=".prepare-", dir=work) as directory:
        stage = Path(directory)
        pins = prepare_sources(stage, mixer)
        if not historical_rust_only:
            compose_l07(stage, mixer)
        (stage / "mixer").rename(work / "mixer")
        (stage / "fieldlog").rename(work / "fieldlog")
    return pins


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixer", type=Path, required=True)
    parser.add_argument("work", type=Path, help="New directory with an existing parent")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--l07", action="store_true", help="Prepare the paired successor (the default)")
    mode.add_argument("--historical-rust-only", action="store_true",
                      help="Reproduce the exact historical photo-only tree and five-notice recipe")
    args = parser.parse_args()
    work, mixer = args.work.resolve(), args.mixer.resolve(strict=True)
    prepare(work, mixer, historical_rust_only=args.historical_rust_only)
    print(SUCCESSOR_TREE if args.historical_rust_only else L07_TREE)
