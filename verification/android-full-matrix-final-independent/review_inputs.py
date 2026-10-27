#!/usr/bin/env python3
"""Independently hash only root-released reconciler/manifest-named files."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKAGE = REPO / "verification/android-editor-membership-compiled-boundary-qualification/state-qualification/offline-reconciler-v1"
SEAL = "71449d54fd7a549ddf60ddad0acdbe3a8a5dd6c4a6bd1a96be099c3389a5097b"
MANIFEST = "deef4efeae2adf4d358036f31e60c8802bba1135128ca1a72622ed1f38bdfd93"
FORBIDDEN = ("execution-closure-v5", "execution_closure_v5", "catalog-inspector", "authority-driver", "rejectedworkerv2", "broadhostedharness")

def need(value, message):
    if not value:
        raise ValueError(message)

def identity(path):
    size = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return {"bytes": size, "sha256": digest.hexdigest()}

def screen(relative):
    need(type(relative) is str and not any(word in relative.lower() for word in FORBIDDEN), "forbidden manifest path: " + str(relative))
    path = Path(relative)
    need(not path.is_absolute() and ".." not in path.parts and str(path) == relative, "unbounded manifest path")
    return path

def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result

def load(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs)

def main():
    started = time.monotonic()
    need(identity(PACKAGE / "seal.json")["sha256"] == SEAL, "root-selected reconciler seal")
    seal = load(PACKAGE / "seal.json")
    need(seal["member_count"] == len(seal["members"]) == 5 and seal["qualified"] is False, "five-member unqualified input package")
    for member in seal["members"]:
        screen(member["path"])
        need(identity(PACKAGE / member["path"]) == {key: member[key] for key in ("bytes", "sha256")}, "package member: " + member["path"])
    need(identity(PACKAGE / "input-manifest.json")["sha256"] == MANIFEST, "selected input manifest")
    manifest = load(PACKAGE / "input-manifest.json")
    # Screen the entire named path roster before opening any descendant input.
    files = manifest["files"]
    all_names = [item["path"] for item in files]
    for relative in all_names:
        screen(relative)
    root_summaries = []
    for entry in manifest["closed_roots"]:
        root = screen(entry["root"])
        names = entry["paths"]
        for relative in names:
            need(screen(relative).is_relative_to(root), "root member escapes declared root")
        need(len(names) == len(set(names)), "duplicate declared root member")
        need(set(names) == {name for name in all_names if Path(name).is_relative_to(root)}, "declared root/file manifest mismatch")
        root_summaries.append({"root": str(root), "members": len(names)})
    need(len(all_names) == len(set(all_names)) == 3241, "exact unique manifest inputs")
    total = 0
    for item in files:
        path = REPO / item["path"]
        for ancestor in (path, *path.parents):
            if ancestor == REPO:
                break
            need(not ancestor.is_symlink(), "symlink in named input ancestry")
        need(identity(path) == {key: item[key] for key in ("bytes", "sha256")}, "manifest member: " + item["path"])
        total += item["bytes"]
    script = identity(Path(__file__))
    receipt = {
        "schema": 1,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "released-input-identities-verified; final-output-review-pending",
        "command": [sys.executable, "-B", str(Path(__file__).resolve())],
        "python": sys.version,
        "platform": platform.platform(),
        "source_revision_context": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip(),
        "script": script,
        "source_packet_seal_sha256": SEAL,
        "manifest_sha256": MANIFEST,
        "package_members": 5,
        "manifest_members": len(files),
        "manifest_member_bytes": total,
        "declared_roots_internal_consistency": root_summaries,
        "filesystem_discovery": "none; exact manifest-named files only, no broad root glob",
        "forbidden_path_matches": [],
        "author_or_product_code_executed": False,
        "unreleased_output_accessed": False,
        "native_UI_capture_process_inventory_started": False,
        "elapsed_seconds": time.monotonic() - started,
        "qualified": False,
    }
    target = OUT / "released-input-identities.json"
    need(not target.exists(), "retain existing independent input receipt")
    target.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in ("status", "manifest_members", "manifest_member_bytes", "elapsed_seconds")}))

if __name__ == "__main__":
    main()
