"""One-shot custody release of provider accounting, without cost acceptance."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
packet = root / "verification/swift-guarded-snapshot-owned-provider-work-storage"
out = Path(__file__).with_name("guarded-snapshot-owned-provider-work-storage-frozen-release.json")
assert not out.exists(), "one-shot release already exists"
sha = lambda b: hashlib.sha256(b).hexdigest()
raw = (packet / "seal.json").read_bytes()
assert sha(raw) == "28ba8099ce8b57f91cd46baac21f130986000ecbbf7df07b16e6bf061fc342d1"
seal = json.loads(raw)
members = seal["members"]
names = [m["path"] for m in members]
assert len(names) == len(set(names)) == seal["member_count"] == 56
assert sum(m["bytes"] for m in members) == seal["total_bytes"] == 13734810
assert all(not p.is_symlink() for p in packet.rglob("*"))
assert {str(p.relative_to(packet)) for p in packet.rglob("*") if p.is_file()} == set(names) | {"seal.json"}
for m in members:
    rel = Path(m["path"])
    assert not rel.is_absolute() and ".." not in rel.parts
    body = (packet / rel).read_bytes()
    assert len(body) == m["bytes"] and sha(body) == m["sha256"], m["path"]
receipt = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "root-rehashed-provider-accounting-candidate-released-for-fresh-independent-review",
    "path": str(packet.relative_to(root)), "seal_sha256": sha(raw),
    "members": 56, "bytes": 13734810,
    "source_tree_sha256": seal["source_tree_sha256"],
    "root_HEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, timeout=10, text=True).strip(),
    "complete_membership_and_all_digests_match": True,
    "tool": {"argv": sys.argv, "python": sys.version,
             "executable_sha256": sha(Path(sys.executable).resolve().read_bytes()),
             "script_sha256": sha(Path(__file__).read_bytes())},
    "scope": "pure host custody; no compiler rerun, semantic cost acceptance or operational quote",
    "fresh_independent_review_required": True, "accepted": False,
    "root_policy_or_funding_or_L_str_selected": False,
    "operational_grant_or_OTA_or_GA": False,
}
with out.open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(json.dumps({"path": str(out.relative_to(root)), "sha256": sha(out.read_bytes()), "members": 56, "bytes": 13734810}))
