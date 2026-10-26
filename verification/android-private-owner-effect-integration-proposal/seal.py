#!/usr/bin/env python3
"""Seal or verify only this proposal and its bounded source-only packet."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
PROPOSAL = ROOT / "docs/android-private-owner-effect-integration-proposal.md"


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("seal", "verify"):
        raise SystemExit("expected seal or verify")
    manifest_path = PACKET / "manifest.json"
    handoff = PACKET / "handoff.sha256"
    if sys.argv[1] == "seal":
        if manifest_path.exists() or handoff.exists():
            raise SystemExit("refuse to replace existing handoff")
        paths = [PROPOSAL] + [p for p in PACKET.rglob("*") if p.is_file()]
        if any(p.is_symlink() for p in paths):
            raise SystemExit("symlink not permitted in this handoff")
        files = {p.relative_to(ROOT).as_posix(): identity(p) for p in sorted(paths)}
        manifest = {"schema": 1, "scope": "source-only-unselected-proposal",
                    "command": [sys.executable, "-B", str(Path(__file__).resolve()), "seal"],
                    "python_version": sys.version, "files": files}
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        handoff.write_text(identity(manifest_path)["sha256"] + "  manifest.json\n")
    manifest = json.loads(manifest_path.read_text())
    expected_hash = handoff.read_text().split()[0]
    errors = []
    if identity(manifest_path)["sha256"] != expected_hash:
        errors.append("manifest binding")
    for name, expected in manifest["files"].items():
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or identity(path) != expected:
            errors.append(name)
    observed = {p.relative_to(ROOT).as_posix() for p in PACKET.rglob("*") if p.is_file()
                and p not in (manifest_path, handoff)} | {PROPOSAL.relative_to(ROOT).as_posix()}
    if observed != set(manifest["files"]):
        errors.append("packet member closure")
    print(json.dumps({"scope": manifest["scope"], "members": len(manifest["files"]),
                      "bytes": sum(v["bytes"] for v in manifest["files"].values()),
                      "manifest_sha256": identity(manifest_path)["sha256"],
                      "errors": errors}, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
