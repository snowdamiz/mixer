#!/usr/bin/env python3
"""Stage and verify the source of the installed FieldLog Android calculation replay."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


RECIPE = Path(__file__).resolve().parent
SELECTED_DRAFT = RECIPE.parent / "fieldlog-saved-draft" / "android"
RECEIPT = RECIPE.parents[2] / "verification/receipts/fieldlog-android-calculation-source-review-20261120.json"


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True, timeout=30
    ).stdout.strip()


def check_tree(repo, expected):
    tree = git(repo, "write-tree")
    if tree != expected:
        raise ValueError(f"Expected FieldLog tree {expected}, found {tree}")


def check_source_bytes(repo, hashes):
    for name, expected in hashes.items():
        actual = sha256((repo / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"FieldLog source SHA-256 differs for {name}")


def compose_source(fieldlog):
    pins = json.loads(RECEIPT.read_bytes())["fieldlog"]
    if Path(git(fieldlog, "rev-parse", "--show-toplevel")).resolve() != fieldlog:
        raise ValueError("Use the root of a disposable FieldLog checkout")
    revision = git(fieldlog, "rev-parse", "HEAD")
    if revision != pins["publicRevision"]:
        raise ValueError(f"Expected FieldLog checkout {pins['publicRevision']}, found {revision}")
    if git(fieldlog, "status", "--porcelain", "--untracked-files=all", "--ignored"):
        raise ValueError("Start from a clean disposable FieldLog checkout")
    check_tree(fieldlog, pins["publicTree"])

    pre_trace = pins["preTrace"]
    traced = pins["traced"]
    for checkpoint in (pre_trace, traced):
        patch = RECIPE / "patches" / checkpoint["patch"]
        if sha256(patch.read_bytes()).hexdigest() != checkpoint["patchSHA256"]:
            raise ValueError(f"SHA-256 differs for {patch.name}")

    for patch, tree in pins["selectedDraftPatches"]:
        git(fieldlog, "apply", "--index", "--whitespace=error", SELECTED_DRAFT / patch)
        check_tree(fieldlog, tree)

    git(fieldlog, "apply", "--index", "--whitespace=error", RECIPE / "patches" / pre_trace["patch"])
    check_tree(fieldlog, pre_trace["tree"])
    check_source_bytes(fieldlog, pre_trace["sourceSHA256"])
    print(f"Verified pre-trace FieldLog tree {pre_trace['tree']} and {len(pre_trace['sourceSHA256'])} file hashes.")

    git(fieldlog, "apply", "--index", "--whitespace=error", RECIPE / "patches" / traced["patch"])
    check_tree(fieldlog, traced["tree"])
    traced_hashes = pre_trace["sourceSHA256"] | traced["changedSourceSHA256"]
    check_source_bytes(fieldlog, traced_hashes)
    print(f"Verified traced FieldLog tree {traced['tree']} and {len(traced_hashes)} file hashes.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fieldlog", type=Path, help="clean checkout of the pinned public FieldLog revision")
    args = parser.parse_args()
    try:
        compose_source(args.fieldlog.resolve())
    except subprocess.CalledProcessError as error:
        print(error.stderr.strip() or error, file=sys.stderr)
        return 1
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
