import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKET = ROOT.parent / "swift-retained-profile-composition-preparation"
receipt = json.loads((PACKET / "receipt.json").read_bytes())
entries = receipt["source_entries"]
assert [x["path"] for x in entries] == sorted(x["path"] for x in entries)
preimage = b"retained-profile-preparation-source-v1\n"
for entry in entries:
    data = (PACKET / entry["path"]).read_bytes()
    assert len(data) == entry["bytes"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    preimage += (entry["path"] + "\0" + str(entry["bytes"]) + "\0" + entry["sha256"] + "\n").encode()
assert hashlib.sha256(preimage).hexdigest() == receipt["source_tree_sha256"] == "fd3c6972e040cb038a5e59d0836eba0c8315c3c4c2eb230f1c82925e5aeed13b"
replay = ROOT / "replay"
replay.mkdir(exist_ok=True)
copied = []
for name in ("schema.py", "prototype.py", "consumer.py", "test_preparation.py"):
    data = (PACKET / name).read_bytes()
    (replay / name).write_bytes(data)
    copied.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
(ROOT / "source-custody.json").write_text(json.dumps({"producer_source_tree_sha256": receipt["source_tree_sha256"], "all_ten_source_members_verified": True, "copied_for_execution": copied}, indent=2, sort_keys=True) + "\n")
print("verified producer source tree; copied four exact host source members")
