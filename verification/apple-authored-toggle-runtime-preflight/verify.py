#!/usr/bin/env python3
"""Read-only frozen producer + handoff verifier. Writes nothing."""
import json
import pathlib
import sys
sys.dont_write_bytecode = True
from packet import BASE, ROOT, file_sha, read_json, require, verify_original, verify_restored


def verify_handoff():
    seal_path = BASE / "packet-seal.json"
    seal = read_json(seal_path)
    for name, digest in seal["files"].items():
        target = ROOT / name
        require(target.is_file() and not target.is_symlink() and file_sha(target) == digest, "Handoff file changed: " + name)
    require(seal["excludedMutableSubtrees"] == ["verification/apple-authored-toggle-runtime-preflight/runtime/"], "Unexpected mutable exclusion")
    return {"files": len(seal["files"]), "packetSealSHA256": file_sha(seal_path), "mutableRuntimeExcluded": True}


if __name__ == "__main__":
    result = {"producer": verify_original(), "handoff": verify_handoff()}
    app = BASE / "runtime/restored-app/MixerAuthoredToggle.app"
    if app.exists():
        result["restoredApp"] = verify_restored(app)
    print(json.dumps(result, indent=2))
