"""Archive the failed pre-staging attempt and prepare a distinct corrected wrapper.

This tool never stages, commits, pushes, or executes either delivery wrapper.
"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = "f678177785accb9e74dbdcb7bbc84222b81c9448"
REL = "attempts/02-parameter-parser-repair/seal.json"
HISTORICAL = {"path": REL, "bytes": 24852,
              "sha256": "23f4ff890933621745b642c06f538d45f590503a501fc5f82c47cdd7c663e082"}


def identity(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def row(path):
    return {"path": str(path.relative_to(ROOT)), **identity(path)}


def write(path, data, exclusive=True):
    with path.open("x" if exclusive else "w") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")


assert __debug__
assert not (OUT / "manifest.json").exists()
assert not (OUT / "deliver-corrected.py").exists()
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=30).decode().strip()
index = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, timeout=30)
assert head == BASE and not index
release = json.loads((OUT / "release-selection.json").read_bytes())
assert release["ready"] is True and release["base"] == BASE
assert len(release["packets"]) == 5
packet = next(p for p in release["packets"] if p["path"] == "swift-guarded-snapshot-host-account-entry")
historical_path = ROOT / "verification" / packet["path"] / REL
assert identity(historical_path) == {k: HISTORICAL[k] for k in ("bytes", "sha256")}
assert "historical_seal_files" not in packet

# Recheck the sole extra file before archiving any attempt evidence.
for item in release["packets"]:
    folder = ROOT / "verification" / item["path"]
    assert identity(folder / "seal.json")["sha256"] == item["seal_sha256"]
    seal = json.loads((folder / "seal.json").read_bytes())
    names = {"seal.json"}
    for member in seal["members"]:
        assert identity(folder / member["path"]) == {k: member[k] for k in ("bytes", "sha256")}
        names.add(member["path"])
    for member in item.get("postseal_files", []):
        names.add(member["path"])
    actual = {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()}
    expected_extra = {REL} if item is packet else set()
    assert actual - names == expected_extra and not names - actual, item["path"]

attempt = OUT / "attempts/01-historical-nested-seal"
attempt.mkdir(parents=True, exist_ok=False)
for name in ("deliver.py", "release-selection.json", "metadata-validation.json"):
    shutil.copyfile(OUT / name, attempt / name)
for prefix in ("branch", "head", "remote", "index-before"):
    for suffix in ("stdout", "stderr", "command.json"):
        (OUT / f"{prefix}.{suffix}").rename(attempt / f"{prefix}.{suffix}")
write(attempt / "failure-observation.json", {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "source": "Root observed prior tool exit and rechecked repository state; this is not a fabricated subprocess receipt.",
    "failed_wrapper": "deliver.py", "observed_exit": 1,
    "assertion": "('swift-guarded-snapshot-host-account-entry', {'attempts/02-parameter-parser-repair/seal.json'})",
    "failure_stage": "Packet closure validation before manifest, staging, commit or push",
    "head_rechecked": head, "index_rechecked_empty": not index,
    "manifest_absent": True, "commands_archived": 4,
    "historical_file": HISTORICAL, "frozen_packets_modified": False,
})
amendment = OUT / "historical-seal-closure-amendment.json"
write(amendment, {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "Explicit immutable historical nonmember added to delivery closure",
    "packet": packet["path"], "current_authoritative_seal_sha256": packet["seal_sha256"],
    "current_authoritative_members": 136,
    "historical_file": HISTORICAL,
    "historical_seal_is_current_acceptance_or_closure_authority": False,
    "historical_member_count_for_identification_only": 126,
    "frozen_packet_source_or_seals_modified": False,
    "original_failed_wrapper_replayed": False,
    "next_wrapper": "deliver-corrected.py",
    "reason": "The original closure guard correctly refused an unlisted nested historical seal. Preserve it as exact data, without using its obsolete membership as current acceptance.",
})

original = (OUT / "deliver.py").read_text()
old = '    actual = set()\n'
addition = '''    for row in packet.get("historical_seal_files", []):
        assert packet["path"] == "swift-guarded-snapshot-host-account-entry"
        assert row == {"path": "attempts/02-parameter-parser-repair/seal.json", "bytes": 24852,
                       "sha256": "23f4ff890933621745b642c06f538d45f590503a501fc5f82c47cdd7c663e082"}
        assert row["path"] not in names
        assert identity(folder / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}
        names.add(row["path"])
    actual = set()
'''
assert original.count(old) == 1
corrected = original.replace(old, addition)
old = 'for name in ("deliver.py", "release-selection.json", "metadata-validation.json"):'
assert corrected.count(old) == 1
corrected = corrected.replace(old, 'for name in ("deliver-corrected.py", "release-selection.json", "metadata-validation.json"):')
old = '    "verification/swift-guarded-snapshot-loader-work-independent/",\n'
assert corrected.count(old) == 1
corrected = corrected.replace(old, old + '    "verification/swift-guarded-snapshot-loader-work-correction/",\n    "verification/swift-guarded-snapshot-loader-work-source146/",\n    "verification/swift-guarded-snapshot-parent-work-independent/",\n')
ast.parse(corrected)
with (OUT / "deliver-corrected.py").open("x") as stream:
    stream.write(corrected)

packet["historical_seal_files"] = [HISTORICAL]
release["root_and_source_files"].extend(row(p) for p in sorted(attempt.iterdir()))
release["root_and_source_files"].extend(row(p) for p in (amendment, OUT / "deliver.py", Path(__file__).resolve()))
assert len({x["path"] for x in release["root_and_source_files"]}) == len(release["root_and_source_files"])
write(OUT / "release-selection.json", release, exclusive=False)

validation = json.loads((attempt / "metadata-validation.json").read_bytes())
for item in validation["metadata_files"]:
    assert identity(ROOT / item["path"]) == {k: item[k] for k in ("bytes", "sha256")}
validation["historical_seal_closure_amendment"] = row(amendment)
validation["corrected_wrapper"] = row(OUT / "deliver-corrected.py")
validation["correction_command"] = [sys.executable, str(Path(__file__).resolve())]
validation["correction_at"] = datetime.now(timezone.utc).isoformat()
validation["scope"] += "; explicit one-file historical seal closure and corrected wrapper syntax; source and accepted seals unchanged"
write(OUT / "metadata-validation.json", validation, exclusive=False)
print(json.dumps({"prepared_corrected_wrapper": True, "historical_files": 1,
                  "archived_attempt_members": len(list(attempt.iterdir())),
                  "staged_or_committed": False}))
