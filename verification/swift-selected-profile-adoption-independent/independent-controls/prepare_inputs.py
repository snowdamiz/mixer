#!/usr/bin/env python3
"""Owned read-only custody verification and exact input copy; no frozen runner."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
PREP = ROOT / "preparation"
PREP.mkdir(exist_ok=True)
RUSTC = Path("/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def command(name, argv):
    result = subprocess.run(argv, cwd=REPO, capture_output=True, timeout=60)
    for stream, data in [("stdout", result.stdout), ("stderr", result.stderr)]:
        (PREP / f"{name}.{stream}").write_bytes(data)
    return {"argv": argv, "cwd": str(REPO), "timeout_seconds": 60,
            "exit_code": result.returncode,
            "stdout_sha256": sha(result.stdout),
            "stderr_sha256": sha(result.stderr)}

def verify(name, expected):
    packet = REPO / "verification" / name
    seal_file = packet / "seal.json"
    assert sha(seal_file.read_bytes()) == expected, name
    seal = json.loads(seal_file.read_text())
    declared = set()
    total = 0
    for member in seal["members"]:
        path = member["path"]
        assert path not in declared and not Path(path).is_absolute()
        assert ".." not in Path(path).parts
        declared.add(path)
        file = packet / path
        assert file.is_file() and not file.is_symlink(), str(file)
        data = file.read_bytes()
        assert len(data) == member["bytes"] and sha(data) == member["sha256"], str(file)
        total += len(data)
    actual = set()
    for file in packet.rglob("*"):
        assert not file.is_symlink(), str(file)
        if file.is_file() and file != seal_file:
            actual.add(str(file.relative_to(packet)))
    assert declared == actual, (name, sorted(declared ^ actual))
    assert len(declared) == seal["member_count"]
    return {"seal_sha256": expected, "members": len(declared), "member_bytes": total}

def main():
    custody = {
        "schema": 1,
        "at": datetime.now(timezone.utc).isoformat(),
        "scope": "offline design preparation and exact immutable source copy only",
        "platform": platform.platform(),
        "python": sys.executable,
        "python_version": sys.version,
        "process_UI_capture_native_inventory_started": False,
        "frozen_packet_scripts_executed": False,
    }
    custody["commands"] = [command("revision", ["git", "rev-parse", "HEAD"]),
                           command("rustc-version", [str(RUSTC), "-vV"])]
    custody["loader"] = verify("swift-real-profile-loader-binding", "e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2")
    custody["independent"] = verify("swift-real-profile-loader-independent", "20841ffd95685e0a65d926c747dfd2c7394341663593cca7c6c01d2c2f329c3f")
    packet = REPO / "verification/swift-real-profile-loader-binding"
    source_manifest = json.loads((packet / "source-manifest.json").read_text())
    host_manifest = json.loads((packet / "baseline-host-support-manifest.json").read_text())
    copies = []
    for entry in source_manifest["members"]:
        relative = Path("source/vm") / entry["path"]
        copies.append((packet / relative, ROOT / relative, entry))
    for entry in host_manifest["members"]:
        relative = Path(entry["retained_path"])
        copies.append((packet / relative, ROOT / relative, entry))
    for source, destination, entry in copies:
        data = source.read_bytes()
        assert len(data) == entry["bytes"] and sha(data) == entry["sha256"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == data, str(destination)
        else:
            destination.write_bytes(data)
    custody["source_copy"] = {"members": source_manifest["member_count"],
                              "tree_sha256": source_manifest["tree_sha256"],
                              "manifest_sha256": sha((packet / "source-manifest.json").read_bytes())}
    custody["host_copy"] = {"members": host_manifest["member_count"], "unchanged": True}
    root_acceptance = REPO / "verification/swift-semantic-adapter-root-review/real-loader-host-acceptance.json"
    acceptance_bytes = root_acceptance.read_bytes()
    custody["root_acceptance"] = {"path": str(root_acceptance.relative_to(REPO)),
                                   "sha256": sha(acceptance_bytes)}
    assert custody["root_acceptance"]["sha256"] == "6c579a2a868bb2eb8ba94f7680355171d28ade46f5a5c89ebf96f014915eeb70"
    custody["tools"] = [{"path": str(Path(sys.executable).resolve()),
                           "sha256": sha(Path(sys.executable).resolve().read_bytes())},
                          {"path": str(RUSTC.resolve()),
                           "sha256": sha(RUSTC.resolve().read_bytes())}]
    (PREP / "input-custody.json").write_text(json.dumps(custody, indent=2) + "\n")
    print(json.dumps(custody, indent=2))

if __name__ == "__main__":
    main()
