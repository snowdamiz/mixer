#!/usr/bin/env python3
"""Read-only hash/stream/cleanup verification; does not rerun producer tests."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    errors = []
    manifest = json.loads((PACKET / "manifest.json").read_bytes())
    for relative, expected in manifest["members"].items():
        path = ROOT / relative
        if path.is_symlink() or not path.is_file() or identity(path.read_bytes()) != expected:
            errors.append(f"sealed identity mismatch: {relative}")
    binding = json.loads((PACKET / "source-bindings.json").read_bytes())
    value = {key: item for key, item in binding.items() if key not in ("tree_sha256", "tree_algorithm")}
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != binding["tree_sha256"]:
        errors.append("source-binding digest mismatch")
    for group in ("implementation", "unchanged_source_pair_1"):
        for relative, expected in binding[group].items():
            if identity((ROOT / relative).read_bytes()) != expected:
                errors.append(f"current source mismatch: {relative}")
    selection = binding["root_selection"]
    if identity((ROOT / selection["path"]).read_bytes()) != {k: selection[k] for k in ("bytes", "sha256")}:
        errors.append("root selection mismatch")
    commands = 0
    for name in ("first", "final"):
        attempt = PACKET / "attempts" / name
        for command in json.loads((attempt / "commands.json").read_bytes()):
            commands += 1
            for stream in ("stdout", "stderr"):
                recorded = command[stream]
                if identity((ROOT / recorded["path"]).read_bytes()) != {k: recorded[k] for k in ("bytes", "sha256")}:
                    errors.append(f"command stream mismatch: {name}/{command['label']}/{stream}")
            if command["exit_code"] != 0:
                errors.append(f"unexpected failed command: {name}/{command['label']}")
        cleanup = json.loads((attempt / "cleanup.json").read_bytes())
        if not cleanup["removed"] or not cleanup["owned_children_waited"] or (attempt / "scratch").exists():
            errors.append(f"owned cleanup incomplete: {name}")
    final = json.loads((PACKET / "attempts/final/receipt.json").read_bytes())
    if final["test_result"]["tests"] != 22 or final["test_result"]["assertions"] != 45841:
        errors.append("final observed test counts differ")
    print(json.dumps({"scope": "sealed identity/streams/owned cleanup only", "status": "pass" if not errors else "fail",
                      "sealed_members": len(manifest["members"]), "verified_command_results": commands,
                      "profile_inputs": len(binding["unchanged_source_pair_1"]), "source_binding_tree_sha256": digest,
                      "host_methods": final["test_result"]["tests"], "host_assertions": final["test_result"]["assertions"],
                      "errors": errors}, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
