#!/usr/bin/env python3
"""Freeze independent requirements from accepted immutable inputs only."""
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

OWN = pathlib.Path(__file__).resolve().parent
REPO = OWN.parents[1]
ACCEPTED = REPO / "verification/swift-selected-profile-adoption-control-correction"
RUSTC = pathlib.Path("/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc")
EXPECTED = {
    "verification/swift-semantic-adapter-root-review/selected-adoption-host-acceptance.json": "635696d0f95e7adf231095ca05a223d47f0353c563b63f60ab242e9cf7bc2697",
    "verification/swift-semantic-adapter-root-review/post-adoption-export-preparation.json": "bf6a9c6600bba2a87e4c16dbbdac8fccb1ad5da562b92943267f6ab6c999f4fd",
    "verification/swift-selected-profile-adoption-control-correction/seal.json": "db09f708b4ee7db5a9e8a9c0bf70dd17b4b96d46cdd887b0f70385a8709d9616",
    "verification/swift-selected-profile-adoption/seal.json": "83a7c57bc5f208b06a42384f14b4056040604ef01685a9dfbe8bbe32b832a7ad",
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def identity(path, name=None):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": name or str(path.relative_to(REPO)), "bytes": len(data), "sha256": sha(data)}

def members(root):
    paths = sorted(root.rglob("*"))
    assert not any(p.is_symlink() for p in paths)
    return [identity(p, p.relative_to(root).as_posix()) for p in paths if p.is_file()]

def command(argv):
    r = subprocess.run(argv, cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return {"argv": [str(v) for v in argv], "exit_code": r.returncode, "output": r.stdout}

def main():
    assert not (OWN / "preaccess-freeze.json").exists(), "Do not overwrite preaccess freeze"
    inputs = [identity(REPO / p) for p in EXPECTED]
    assert all(i["sha256"] == EXPECTED[i["path"]] for i in inputs)
    manifest = json.loads((ACCEPTED / "source-manifest.json").read_text())
    actual = members(ACCEPTED / "source/vm")
    assert actual == manifest["members"] and len(actual) == 144
    source_tree = sha(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode())
    assert source_tree == manifest["tree_sha256"] == "9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb"
    seal = json.loads((ACCEPTED / "seal.json").read_text())
    actual_packet = [m for m in members(ACCEPTED) if m["path"] != "seal.json"]
    assert actual_packet == seal["members"] and len(actual_packet) == seal["member_count"]
    host = members(ACCEPTED / "host")
    assert len(host) == 11
    value = {
        "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
        "status": "independent-requirements-frozen-before-candidate-access",
        "producer_candidate_read": False, "root_release_received": False,
        "requirements": identity(OWN / "preaccess-requirements.md"),
        "freeze_script": identity(OWN / "freeze_preaccess.py"),
        "inputs": inputs, "accepted_source_tree_sha256": source_tree,
        "accepted_source_members": len(actual), "accepted_host_members": len(host),
        "corrected_packet_closed_members_verified": len(actual_packet),
        "tools": [command([sys.executable, "--version"]), command([str(RUSTC), "-vV"])],
        "revision": command(["git", "rev-parse", "HEAD"]),
        "initial_discovery_failures_retained": [
            {"argv": ["rustc", "--version"], "exit_code": 127, "output": "zsh:1: command not found: rustc\n", "resolution": "Use immutable accepted explicit toolchain path."},
            {"command": "rg against zsh experimental_wasi*.rs glob", "exit_code": 1, "output": "zsh:1: no matches found: verification/swift-selected-profile-adoption-control-correction/source/vm/src/experimental_wasi*.rs\n", "resolution": "Use exact existing module directory."},
        ],
        "scope": "Independent next exporter contract requirements only; no candidate access, implementation or native/runtime qualification.",
    }
    assert all(c["exit_code"] == 0 for c in value["tools"] + [value["revision"]])
    (OWN / "preaccess-freeze.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    print(json.dumps(identity(OWN / "preaccess-freeze.json"), sort_keys=True))

if __name__ == "__main__":
    main()
