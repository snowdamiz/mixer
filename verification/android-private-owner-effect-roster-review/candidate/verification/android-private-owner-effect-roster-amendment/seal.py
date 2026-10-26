#!/usr/bin/env python3
"""Seal/check only the additive R1 roster amendment packet."""
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOC = ROOT / "docs/android-private-owner-effect-roster-amendment.md"


def ident(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    assert len(sys.argv) == 2 and sys.argv[1] in ("seal", "check")
    manifest_path = BASE / "manifest.json"
    handoff = BASE / "handoff.sha256"
    if sys.argv[1] == "seal":
        assert not manifest_path.exists() and not handoff.exists(), "do not replace seal"
        result = json.loads((BASE / "source-only-result.json").read_text())
        assert result["failed"] == 0 and result["product_tests_run"] is False
        assert (BASE / "capture.stderr").read_bytes() == (BASE / "verify.stderr").read_bytes() == b""
        paths = [DOC] + [p for p in BASE.rglob("*") if p.is_file()]
        assert all(not p.is_symlink() for p in paths)
        manifest = {"schema": 1, "scope": "source-only-five-ID-roster-amendment-unselected",
                    "command": [sys.executable, "-B", str(Path(__file__).resolve()), "seal"],
                    "python_version": sys.version, "files": {str(p.relative_to(ROOT)): ident(p) for p in sorted(paths)}}
        manifest["members"] = len(manifest["files"])
        manifest["bytes"] = sum(x["bytes"] for x in manifest["files"].values())
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        handoff.write_text(ident(manifest_path)["sha256"] + "  manifest.json\n")
    manifest = json.loads(manifest_path.read_text())
    assert handoff.read_text().split()[0] == ident(manifest_path)["sha256"]
    observed = {str(p.relative_to(ROOT)) for p in BASE.rglob("*") if p.is_file() and p not in (manifest_path, handoff)} | {str(DOC.relative_to(ROOT))}
    assert observed == set(manifest["files"])
    for name, expected in manifest["files"].items():
        p = ROOT / name
        assert not p.is_symlink() and ident(p) == expected, name
    print(json.dumps({"scope": manifest["scope"], "members": manifest["members"], "bytes": manifest["bytes"],
                      "manifest_sha256": ident(manifest_path)["sha256"], "errors": []}, sort_keys=True))


if __name__ == "__main__":
    main()
