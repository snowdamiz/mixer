"""Read-only producer evidence admission; independent behavior acceptance follows."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / "verification/android-public-owner-core"


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


manifest = json.loads((PACKET / "manifest.json").read_text())
members = manifest["members"]
assert len(members) == 48
for name, expected in members.items():
    path = Path(name)
    assert not path.is_absolute() and ".." not in path.parts
    assert identity(ROOT / path) == expected, name
bindings = json.loads((PACKET / "source-bindings.json").read_text())
assert bindings["tree_sha256"] == "c5597d41313b506ef39a0dcd36ebde7fd8f50c78db436410681262c1c233833d"
assert len(bindings["implementation"]) == 4
assert len(bindings["unchanged_source_pair_1"]) == 42
for group in ("implementation", "unchanged_source_pair_1"):
    for name, expected in bindings[group].items():
        assert identity(ROOT / name) == expected, name
root_selection = bindings["root_selection"]
assert identity(ROOT / root_selection["path"]) == {k: root_selection[k] for k in ("bytes", "sha256")}
receipt = json.loads((PACKET / "receipt.json").read_text())
assert receipt["final_host_methods"] == 22 and receipt["final_host_assertions"] == 45841
assert receipt["final_class_files"] == 13
for row in receipt["cleanup"].values():
    assert row["owned_children_waited"] and row["removed"]
    assert not Path(row["scratch"]).exists()
assert not receipt["implementation_accepted"] and not receipt["native_UI_capture_device_or_process_discovery"]
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "python_version": sys.version,
    "checker": identity(Path(__file__)),
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "producer_manifest": identity(PACKET / "manifest.json"),
    "root_verified_members": len(members),
    "root_verified_bytes": sum(v["bytes"] for v in members.values()),
    "current_inputs_verified": 46,
    "source_pair_1_inputs_unchanged": 42,
    "candidate_source": bindings["implementation"]["native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java"],
    "producer_host_methods": 22,
    "producer_assertions": 45841,
    "independent_review": "running in verification/android-public-owner-core-independent-review",
    "preaccess_seal": identity(OUT / "preaccess-seal.json"),
    "implementation_accepted": False,
    "native_runtime_or_capture_started": False,
    "public_V2_or_GA_qualified": False,
    "errors": [],
}
(OUT / "implementation-preflight.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ("root_verified_members", "root_verified_bytes", "current_inputs_verified", "implementation_accepted")}))
