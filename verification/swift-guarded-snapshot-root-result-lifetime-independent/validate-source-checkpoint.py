#!/usr/bin/env python3
"""Read-only pin validation; writes only a new independent validation receipt."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
CANDIDATE = ROOT / "verification/swift-guarded-snapshot-root-result-lifetime-implementation"
PREACCESS = ROOT / "verification/swift-guarded-snapshot-root-result-preaccess"
CONTRACT = ROOT / "verification/swift-guarded-snapshot-root-result-lifetime-contract"
OLD = ROOT / "verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def read_manifest(base):
    return [
        {"path": str(p.relative_to(base)), "bytes": len(p.read_bytes()), "sha256": sha(p.read_bytes())}
        for p in sorted(base.rglob("*"))
        if p.is_file()
    ]


preaccess = json.loads((PREACCESS / "freeze.json").read_text())
preaccess_rows = []
for row in preaccess["files"]:
    data = (PREACCESS / row["path"]).read_bytes()
    assert len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"]
    preaccess_rows.append(f'{sha(data)}  {len(data)}  {row["path"]}\n')
preaccess_digest = sha("".join(sorted(preaccess_rows, key=lambda s: s.split("  ", 2)[2])).encode())
assert preaccess_digest == "231ad6382dc863b154d7e734d7a3b298320486aaa862fb49b6c0815edccc879e"
assert sha((CONTRACT / "seal.json").read_bytes()) == "5cbf7f3c49baa7e8db9a61ee720a9e5eee0d81241a580d8997b75fad6030c4eb"
for row in json.loads((CONTRACT / "seal.json").read_text())["members"]:
    data = (CONTRACT / row["path"]).read_bytes()
    assert len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"]

assert sha((CANDIDATE / "source-manifest.json").read_bytes()) == "5f20215aef11436b0a3cde511c0820450f37a613de20e74d810728bd5efa8249"
source_rows = read_manifest(CANDIDATE / "source/vm")
host_rows = read_manifest(CANDIDATE / "source/host")
assert len(source_rows) == 146 and len(host_rows) == 11
assert source_rows == json.loads((CANDIDATE / "source-manifest.json").read_text())["members"]
assert host_rows == json.loads((CANDIDATE / "host-manifest.json").read_text())["members"]
source_digest = canonical_digest(source_rows)
host_digest = canonical_digest(host_rows)
assert source_digest == "91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f"
assert host_digest == "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2"
old_source = json.loads((OLD / "source-manifest.json").read_text())["members"]
assert [r["path"] for r in source_rows] == [r["path"] for r in old_source]
changed = [new["path"] for new, old in zip(source_rows, old_source) if new != old]
assert changed == [
    "src/experimental_swift_reactor/cache/initial_profile_v1.rs",
    "src/experimental_swift_reactor/retained_profile_loader_v1.rs",
]
assert host_rows == json.loads((OLD / "host-manifest.json").read_text())["members"]
adoption = json.loads((PACKET / "oracle-adoption.json").read_text())
assert adoption["candidate_source_accessed_before_this_adoption"] is False
assert adoption["producer_tests_probes_results_accessed_before_adoption"] is False
assert json.loads((PACKET / "source-review.json").read_text())["candidate_source_tree_sha256"] == source_digest

result = {
    "schema": 1,
    "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "source-checkpoint-pins-pass-no-compiler-host-or-native-run",
    "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))],
    "tool_version": sys.version,
    "script_sha256": sha(Path(__file__).read_bytes()),
    "source_revision_basis": "Original preaccess revision ee9f6dc77f88259e2b143fc81dc1085b34a4a943 and immutable candidate source tree, not current unrelated HEAD",
    "source146_tree_sha256": source_digest,
    "host11_tree_sha256": host_digest,
    "preaccess_content_sha256": preaccess_digest,
    "changed_members": changed,
    "scope": "Exact packet/source pins and source review only. No native File, VM fixture, runtime, product leaf, UI/capture, phone, network, process inventory or Git mutation.",
    "compiler_invocations": 0,
    "host_runs": 0,
    "producer_results_reviewed": False,
    "compiler_authority": "Pending exact root-selected independent roster; producer reservation respected",
}
with (PACKET / "source-checkpoint-validation.json").open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps(result, indent=2))
