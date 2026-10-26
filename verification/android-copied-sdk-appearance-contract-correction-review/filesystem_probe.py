#!/usr/bin/env python3
"""Independent inert-file probe; no Swift, product code or native runtime runs."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import shutil
import sys

HERE = Path(__file__).resolve().parent
SCRATCH = HERE / "owned-filesystem-scratch"
assert not SCRATCH.exists(), "Refuse existing scratch"
SCRATCH.mkdir()
translate = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def original_namespace_rule(name):
    return not name.translate(translate).startswith("package") or name == "Package.swift"


def amended_namespace_rule(name):
    return name.isascii() and original_namespace_rule(name)


cases = [
    ("kelvin-version-selector", "Pac\u212aage@swift-6.4.swift", "Package@swift-6.4.swift"),
    ("kelvin-base-manifest", "Pac\u212aage.swift", "Package.swift"),
    ("unrelated-root-unicode", "caf\u00e9.txt", "cafe\u0301.txt"),
    ("ordinary-version-selector", "Package@swift-6.4.swift", "Package@swift-6.4.swift"),
    ("canonical-manifest", "Package.swift", "Package.swift"),
    ("ordinary-unrelated-entry", "README.md", "README.md"),
]
results = []
try:
    for label, name, lookup in cases:
        directory = SCRATCH / label
        directory.mkdir()
        payload = ("Inert review fixture: " + label + "\n").encode()
        path = directory / name
        path.write_bytes(payload)
        entries = os.listdir(directory)
        assert entries == [name]
        alternate = directory / lookup
        resolves = alternate.exists()
        original_stat = path.lstat()
        same_inode = resolves and (alternate.lstat().st_dev, alternate.lstat().st_ino) == (original_stat.st_dev, original_stat.st_ino)
        result = {"case": label, "created_name": name, "enumerated_names": entries,
                  "created_codepoints": [f"U+{ord(x):04X}" for x in name],
                  "ascii_lookup": lookup, "lookup_exists": resolves, "lookup_same_inode": same_inode,
                  "ascii_folded_name": name.translate(translate),
                  "old_ascii_prefix_rule_accepts": original_namespace_rule(name),
                  "amended_rule_accepts": amended_namespace_rule(name),
                  "fixture_bytes": len(payload), "fixture_sha256": hashlib.sha256(payload).hexdigest(),
                  "scope": "Local filesystem path lookup for inert regular file; not SwiftPM/compiler behavior."}
        results.append(result)
    by_case = {x["case"]: x for x in results}
    assert by_case["kelvin-version-selector"]["lookup_same_inode"]
    assert by_case["kelvin-version-selector"]["old_ascii_prefix_rule_accepts"]
    assert not by_case["kelvin-version-selector"]["amended_rule_accepts"]
    assert by_case["kelvin-base-manifest"]["lookup_same_inode"]
    assert by_case["kelvin-base-manifest"]["old_ascii_prefix_rule_accepts"]
    assert not by_case["kelvin-base-manifest"]["amended_rule_accepts"]
    assert not by_case["unrelated-root-unicode"]["amended_rule_accepts"]
    assert not by_case["ordinary-version-selector"]["amended_rule_accepts"]
    assert by_case["canonical-manifest"]["amended_rule_accepts"]
    assert by_case["ordinary-unrelated-entry"]["amended_rule_accepts"]
finally:
    shutil.rmtree(SCRATCH)
    assert not SCRATCH.exists()

report = {"schema": "mixer.independent-correction-review.filesystem-probe.v1",
          "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "python_version": sys.version, "platform": platform.platform(),
          "cases": results, "checks_passed": True, "cleanup": {"scratch_absent": True},
          "finding": "Directory enumeration preserves a non-ASCII Kelvin-sign Package alias that ASCII-only prefix folding admits; an ordinary ASCII manifest lookup resolves to the same file on this host. Rejecting every non-ASCII SDK-root entry closes this observed name gap.",
          "limitations": "No compiler, manifest evaluation, source admission implementation, native runtime, process discovery, or UI/capture execution. A different filesystem may not resolve the same alias; rejection remains conservative."}
(HERE / "filesystem-probe.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n")
print(json.dumps(report, indent=2, ensure_ascii=True))
