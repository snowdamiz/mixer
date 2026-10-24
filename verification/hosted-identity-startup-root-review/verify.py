#!/usr/bin/env python3
"""Verify immutable startup acceptance; optionally compare current source."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-source", action="store_true")
    args = parser.parse_args()
    receipt = json.loads((HERE / "acceptance.json").read_text())
    for path, expected in receipt["bindings"].items():
        if digest((ROOT / path).read_bytes()) != expected:
            raise SystemExit(f"binding mismatch: {path}")
    sources = json.loads((HERE / "integrated-source-manifest.json").read_text())
    host = json.loads((HERE / "integrated-host/receipt.json").read_text())
    archive = HERE / "integrated-host/source.tar.gz"
    if digest(archive.read_bytes()) != host["source_archive_sha256"]:
        raise SystemExit("host source archive mismatch")
    with tarfile.open(archive, "r:gz") as tf:
        archived = {m.name: digest(tf.extractfile(m).read())
                    for m in tf.getmembers() if m.isfile()}
    if archived != host["inputs"]:
        raise SystemExit("host archive/input manifest mismatch")
    if any(sources.get(p) != h for p, h in host["inputs"].items()):
        raise SystemExit("host inputs differ from reviewed source")
    if args.live_source:
        for path, expected in sources.items():
            if digest((ROOT / path).read_bytes()) != expected:
                raise SystemExit(f"live source mismatch: {path}")
    print(f"verified {len(receipt['bindings'])} evidence bindings, "
          f"{len(host['inputs'])} archived inputs, {len(sources)} reviewed sources; "
          f"live source checked={args.live_source}")


if __name__ == "__main__":
    main()
