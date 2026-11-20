"""Check the recipe's working inputs against an independently selected Git commit."""

from hashlib import sha256
import os
from pathlib import Path
import re
import subprocess
import sys

RECIPE = Path("tests/integration/fieldlog-native-capability-ota")
CALCULATION_LOCK = Path("tests/integration/fieldlog-task-calculation/android-packaging/recipe.sha256")
SOURCE_LIMIT = 8 * 1024 * 1024
SOURCES = {RECIPE / name for name in (
    "SealPair.swift", "android-origin.py", "android-successor.patch", "build-current-abi-android-pair.sh",
    "calculation-apk-signer.patch", "current-abi.py", "current_abi_packet.py", "current_abi_recipe.py",
    "inspect-current-abi.py", "package-android-pair.py", "replay-android-pair.py",
)} | {Path("cli/release-tools/canonical.py"), CALCULATION_LOCK}


def verify(root, revision, *, git_root=None, campaign=None):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected the full independently selected recipe commit")

    def git(*args):
        return subprocess.check_output(
            ["git", "--no-replace-objects", "-C", git_root or root, *args], timeout=15,
            env=os.environ | {"GIT_NO_LAZY_FETCH": "1"},
        )

    checked = {}

    def check(name, expected):
        path = root / name
        if path.resolve() != path or not path.is_file():
            raise ValueError(f"Expected a regular recipe source: {name}")
        with path.open("rb") as stream:
            content = stream.read(SOURCE_LIMIT + 1)
        if len(content) > SOURCE_LIMIT or sha256(content).hexdigest() != expected:
            raise ValueError(f"Recipe source differs: {name}")
        checked[name] = content

    if git("cat-file", "-t", revision).strip() != b"commit":
        raise ValueError("Recipe selection must be a Git commit")
    lock = git("cat-file", "blob", f"{revision}:{CALCULATION_LOCK}")
    pins = {}
    for name in sorted(SOURCES):
        content = lock if name == CALCULATION_LOCK else git("cat-file", "blob", f"{revision}:{name}")
        expected = sha256(content).hexdigest()
        check(name, expected)
        pins[name.as_posix()] = expected

    seen = set()
    for line in lock.decode().splitlines():
        expected, name = line.split("  ", maxsplit=1)
        path = Path(name)
        if (not re.fullmatch(r"[0-9a-f]{64}", expected) or path.is_absolute() or ".." in path.parts
                or path.as_posix() != name or path in seen):
            raise ValueError(f"Invalid calculation recipe pin: {line}")
        seen.add(path)
        check(path, expected)
    calculation = root / CALCULATION_LOCK.parent
    working = {path.relative_to(root) for path in calculation.rglob("*") if path.is_file() or path.is_symlink()}
    expected = {path for path in seen if path.is_relative_to(CALCULATION_LOCK.parent)} | {CALCULATION_LOCK}
    if working != expected:
        raise ValueError("Unexpected files in the calculation recipe directory")
    if campaign is not None:
        if campaign != campaign.resolve() or not campaign.parent.is_dir():
            raise ValueError(f"Expected a new canonical campaign directory: {campaign}")
        campaign.mkdir()
        snapshot = campaign / "work/recipe-source"
        # Write only the exact bytes checked above, including all pinned helper inputs.
        for name, content in checked.items():
            path = snapshot / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(content)
    return pins


if __name__ == "__main__":
    root, revision, campaign = sys.argv[1:]
    verify(Path(root).resolve(strict=True), revision, campaign=Path(campaign))
