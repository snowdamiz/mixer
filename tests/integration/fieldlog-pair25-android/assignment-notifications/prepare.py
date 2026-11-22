#!/usr/bin/env python3
"""Reconstruct the exact current FieldLog source plus the assignment tap route."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PUBLIC = "e6622741eaa1a4b699fa604870b2168920926582"
RECIPE = "126b31fea12ddb7e07b00c8f5ed551bdb462cad5"
NOTICE_DIR = "tests/integration/fieldlog-pair25-android/rust-runtime-notices"
RECIPE_INPUTS = {
    "prepare-successor.py": "99a8b563f84f345a0d2d6c63b5f11ad6d98434df2b517de34199845a2bf8580f",
    "fieldlog-packaging.patch": "998fe05c85e2e5d4870c234816b8a18e19c39513fc5cbebbae768ac1acbc87fa",
    "fieldlog-l07-notices.patch": "f70c721ea18541b2bbe8100d327ccca534058b1f4b36dcfcdde42786347d3931",
}
BASE_CHANGES = (
    ("fieldlog-ios-settings-bounded-7b2b98f0.patch",
     "2639352790e03eadd4fc0ae1cb81fe2fbdcfd4d1c7f7d3f872dc405869fa7418", "d886f34875028dad8100d595bdea5495165a3be6"),
    ("fieldlog-android-settings-elapsed-7b2b98f0.patch",
     "b1c53a93f02fbbf057fc7e77244ad471b1f4c58a14268ae19c3bc038d9d1abb9", "9c2d665c31a6f3f2bfabc42bdfffaf72c6661731"),
    ("fieldlog-ios-task-conflict-injected-f2865989.patch",
     "f5c09970636d4b4aa650aa7ee709d923f68281f7a09a41d17af05cb2772f7b34", "e51be0f5c88fe532d05c2e38d2cf901410df6cdb"),
    ("fieldlog-android-saved-task-edit-568793c0.patch",
     "6bbdb51ae7b5d5e23e635201aa5da1568c6c39587e80201a487907d9917388cf", "e14b61898dab519dbe314ad6204aac15f93b47b1"),
)
ROUTE = ("fieldlog-assignment-route.patch",
         "ad5c8589b2c0b27232ac93861f165628704d30c69733da91a6ad2ae65c6fb44e", "b965c417fdc57f5d4d0932701b53b15a9880a515")
FIXTURE = ("fieldlog-assignment-local-provider.patch",
           "ba50dd95a24444cfbbae415f2b71e16963907d15c262e7ea70f6dbefd3b92c4a", "c4c133d68d98f76a7f8822d43aa5ad0882cf5d4a")


def git(checkout, *args, data=None):
    return subprocess.run(["git", "-C", checkout, *args], input=data,
                          capture_output=True, check=True).stdout


def checked(data, expected, label):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch for {label}")
    return data


def apply(app, patch, tree):
    git(app, "apply", "--index", "--unidiff-zero", "--whitespace=error", "-", data=patch)
    observed = git(app, "write-tree").decode().strip()
    if observed != tree:
        raise ValueError(f"Expected FieldLog tree {tree}, got {observed}")


def prepare(mixer, work, include_fixture):
    with tempfile.TemporaryDirectory(prefix=".pair25-recipe-", dir=work.parent) as directory:
        recipe = Path(directory)
        for name, digest in RECIPE_INPUTS.items():
            ref = f"{RECIPE}:{NOTICE_DIR}/{name}"
            (recipe / name).write_bytes(checked(git(mixer, "show", ref), digest, ref))
        subprocess.run([sys.executable, "-B", recipe / "prepare-successor.py",
                        "--mixer", mixer, work], check=True)
    app = work / "fieldlog"
    for name, digest, tree in BASE_CHANGES:
        ref = f"{PUBLIC}:verification/receipts/{name}"
        apply(app, checked(git(mixer, "show", ref), digest, ref), tree)
    for name, digest, tree in (ROUTE, FIXTURE) if include_fixture else (ROUTE,):
        apply(app, checked((HERE / name).read_bytes(), digest, name), tree)
    if git(app, "diff", "--name-only") or git(app, "ls-files", "--others", "--exclude-standard"):
        raise ValueError("Unexpected FieldLog working-copy changes")
    print(tree)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixer", type=Path, required=True)
    parser.add_argument("--fixture", action="store_true", help="Include the local Android notification provider")
    parser.add_argument("work", type=Path, help="New work directory with an existing parent")
    args = parser.parse_args()
    try:
        prepare(args.mixer.resolve(strict=True), args.work.resolve(), args.fixture)
    except subprocess.CalledProcessError as failure:
        if failure.stderr:
            sys.stderr.buffer.write(failure.stderr)
        raise SystemExit(failure.returncode)
    except (OSError, ValueError) as failure:
        raise SystemExit(str(failure))
