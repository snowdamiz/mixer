"""Copy only exact 146+11 sources and inject one private cfg(test) witness."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACK = ROOT / "verification/swift-guarded-snapshot-actual-owner-rust-implementation"
WORK = HERE / "witness-source"
WORK.mkdir(exist_ok=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


source = json.loads((PACK / "final-source-manifest.json").read_bytes())
host = json.loads((ROOT / "verification/swift-guarded-snapshot-host-composition/host-support-manifest.json").read_bytes())
before = []
for category, rows in (("vm", source["members"]), ("host", host["members"])):
    for row in rows:
        data = (PACK / "source" / category / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"]
        destination = WORK / category / row["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        before.append({**row, "path": category + "/" + row["path"]})
loader = WORK / "vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs"
data = loader.read_bytes()
marker = b"\n    }\n\n    // OWNER_PROBE_INSERTION"
assert data.count(marker) == 1
injection = (HERE / "retirement_witness.inc.rs").read_bytes()
loader.write_bytes(data.replace(marker, b"\n" + injection + marker, 1))
after = []
for path in sorted(WORK.rglob("*")):
    if path.is_file():
        raw = path.read_bytes()
        after.append({"path": str(path.relative_to(WORK)), "bytes": len(raw), "sha256": sha(raw)})
changed = [r["path"] for r in after if next(x for x in before if x["path"] == r["path"]) != r]
assert changed == ["vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs"]
result = {"schema": 1, "scope": "one private cfg(test) desired-property witness; all product core bytes unchanged", "source_inputs": 146, "host_inputs": 11, "before": sorted(before, key=lambda r: r["path"]), "after": after, "changed": changed, "source_tree_sha256": sha(json.dumps(after, sort_keys=True, separators=(",", ":")).encode()), "injection_sha256": sha(injection), "native_File_fixture_UI_or_Git_execution": False}
(HERE / "witness-source-manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
print(json.dumps({k: v for k, v in result.items() if k not in ("before", "after")}, sort_keys=True))
