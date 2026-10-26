#!/usr/bin/env python3
"""Read-only integrity verifier. It proves no Android or model behavior."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    manifest = json.loads((PACKET / "manifest.json").read_bytes())
    errors = []
    for relative, expected in manifest["members"].items():
        target = ROOT / relative
        if target.is_symlink() or not target.is_file() or identity(target.read_bytes()) != expected:
            errors.append(f"Packet identity mismatch: {relative}")
    binding = json.loads((PACKET / "source-bindings.json").read_bytes())
    files = binding["files"]
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != binding["tree_sha256"]:
        errors.append("Source tree digest mismatch")
    for relative, expected in files.items():
        result = subprocess.run(["git", "show", f"{binding['context_revision']}:{relative}"],
                                cwd=ROOT, capture_output=True)
        recorded = {key: expected[key] for key in ("bytes", "sha256")}
        if result.returncode or identity(result.stdout) != recorded:
            errors.append(f"Context blob mismatch: {relative}")
        if expected["binding"] == "product-current-and-git":
            target = ROOT / relative
            if target.is_symlink() or not target.is_file() or identity(target.read_bytes()) != recorded:
                errors.append(f"Current product mismatch: {relative}")
        if "profile_group" in expected:
            result = subprocess.run(["git", "show", f"{binding['native_base_revision']}:{relative}"],
                                    cwd=ROOT, capture_output=True)
            if result.returncode or identity(result.stdout) != recorded:
                errors.append(f"Accepted native baseline mismatch: {relative}")
    profiles = [v for v in files.values() if "profile_group" in v]
    if len(profiles) != 42 or len([v for v in profiles if v["profile_group"] == "sdk_files"]) != 22:
        errors.append("Accepted profile cardinality mismatch")
    print(json.dumps({"scope": "packet/source identity only; no model or Android behavior",
                      "status": "pass" if not errors else "fail",
                      "sealed_members": len(manifest["members"]),
                      "source_inputs": len(files), "profile_inputs": len(profiles),
                      "source_binding_tree_sha256": digest, "errors": errors}, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
