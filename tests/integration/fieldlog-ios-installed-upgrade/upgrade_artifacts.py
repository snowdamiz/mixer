"""Shared input identities and artifact hashing."""
import hashlib
import os
import subprocess
from pathlib import Path

PAIRS = {
    "prior": ("0.1.0", "1", "63a76a4c34ff01f50b9b38a936bc81c87f462c95"),
    "new": ("0.1.1", "2", "1a56d6d0f28298c8805dfd6c1e5738819dcf9a7d"),
}
FIELDLOG_REV = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
FIELDLOG_TREE = "1b62520f35c7e57a01b568291078686574f627c4"
MIXER_TREES = {
    "prior": "750807bc714063c2d1bcacd5a10d8b2e819ec60f",
    "new": "c5dfadb87080331c7d2d95cd254c40a75383c311",
}
TOOLCHAIN = "Xcode 27.2\nBuild version 27B52"
ENGINE_PRODUCTS = ("MixerCore", "MixerUI", "MixerApple")


def tool_environment():
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(Path.home()), "LANG": "en_US.UTF-8"}
    if "DEVELOPER_DIR" in os.environ:
        env["DEVELOPER_DIR"] = os.environ["DEVELOPER_DIR"]
    return env


def git_command(checkout, *args, **kwargs):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1")
    return subprocess.run(["/usr/bin/git", "-C", checkout, *args], env=env, check=True, **kwargs)


def git_tree(checkout, revision, path=None):
    # --verify rejects missing pins instead of echoing the unresolved argument.
    tree = f"{revision}^{{tree}}"
    if path is not None:
        tree += f":{path}"
    return git_command(checkout, "rev-parse", "--verify", tree,
                       capture_output=True, text=True).stdout.strip()


def sha(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Expected a regular file: {path}")
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def tree_sha(directory):
    entries = sorted(directory.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError(f"Unexpected symlink: {directory}")
    manifest = "".join(f"{sha(path)}  {path.relative_to(directory)}\n"
                       for path in entries if path.is_file())
    return hashlib.sha256(manifest.encode()).hexdigest()
