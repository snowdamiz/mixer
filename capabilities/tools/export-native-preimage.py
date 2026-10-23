#!/usr/bin/env python3
"""Read-only exporter for the generated native identity's exact source preimage.

This does not import the generator (its module has write side effects). --check
executes only the generator's explicit read-only check mode before comparing the
independently reconstructed preimage with the checked-in identity metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def preimage(root):
    records = {}
    excluded = {"GeneratedIdentity.swift", "CapabilityNativeIdentity.java", "CapabilityProbe.java"}
    for directory in ("sdk/Sources/MixerCapabilities", "capabilities/java/mixer/capabilities"):
        for path in (root / directory).rglob("*"):
            if path.is_file() and path.name not in excluded:
                # Match the generator's UTF-8 text/universal-newline preimage,
                # rather than treating generated identity text as its own input.
                content = path.read_text(encoding="utf-8").encode("utf-8")
                records[path.relative_to(root).as_posix()] = hashlib.sha256(content).hexdigest()
    schema = json.loads((root / "capabilities/schema/v1.json").read_text(encoding="utf-8"), object_pairs_hook=unique)
    records["capabilities/schema/v1.json"] = hashlib.sha256(canonical(schema)).hexdigest()
    return canonical([{"path": path, "sha256": digest} for path, digest in sorted(records.items())])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="also verify generated files without writing them")
    parser.add_argument("--output", type=Path, help="export exact preimage bytes (no final LF)")
    args = parser.parse_args()
    if args.check:
        subprocess.run([sys.executable, str(ROOT / "capabilities/tools/generate.py"), "--check"], check=True, stdout=subprocess.PIPE)
    encoded = preimage(ROOT)
    digest = hashlib.sha256(encoded).hexdigest()
    metadata = json.loads((ROOT / "capabilities/schema/hashes.json").read_text(encoding="utf-8"), object_pairs_hook=unique)
    if digest != metadata["nativeImplementationSHA256"]:
        raise SystemExit("native preimage differs from generated identity; no files changed")
    if args.output:
        output = args.output.resolve()
        protected = (ROOT / "sdk", ROOT / "capabilities", ROOT / "contracts")
        if any(output == path or path in output.parents for path in protected):
            raise SystemExit("refusing to export into production identity/source directories")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
    print(json.dumps({"nativeImplementationSHA256": digest, "preimageBytes": len(encoded), "sources": len(json.loads(encoded)), "finalLF": False}, sort_keys=True))


if __name__ == "__main__":
    main()
