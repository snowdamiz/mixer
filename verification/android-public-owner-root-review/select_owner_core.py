"""Select only the pure host ownership-decision core from the frozen contract."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
PACKET = ROOT / "verification/android-public-owner-contract"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


raw = (PACKET / "manifest.json").read_bytes()
assert identity(raw)["sha256"] == "4ecf1287a35219c11992769f95dfc7d699031001bf7d73306caaa4817f78c747"
members = json.loads(raw)["members"]
assert len(members) == 8
for name, expected in members.items():
    path = pathlib.PurePosixPath(name)
    assert not path.is_absolute() and ".." not in path.parts
    assert identity((ROOT / path).read_bytes()) == expected, name
bindings = json.loads((PACKET / "source-bindings.json").read_text())
assert len(bindings["files"]) == 55
context_changes = []
for name, expected in bindings["files"].items():
    actual = identity((ROOT / name).read_bytes())
    if actual != {key: expected[key] for key in ("bytes", "sha256")}:
        assert name == "PLAN.md", name
        context_changes.append({"path": name, "frozen": expected, "current": actual})
current = (ROOT / "PLAN.md").read_text()
committed = subprocess.check_output(["git", "show", "1f114d8f235e8042c275a2549fef7d4994272360:PLAN.md"], cwd=ROOT, text=True)
start, end = "4. **Android and cross-platform UI:**", "5. **Hosted product and console:**"
assert current[current.index(start):current.index(end)] == committed[committed.index(start):committed.index(end)]
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": identity(pathlib.Path(__file__).read_bytes())["sha256"],
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "pure-host-owner-core-selected-for-implementation",
    "contract_manifest_sha256": identity(raw)["sha256"],
    "contract_members_verified": 8,
    "contract_bytes_verified": sum(x["bytes"] for x in members.values()),
    "bound_inputs": 55,
    "current_inputs_equal_frozen": 55 - len(context_changes),
    "context_changes": context_changes,
    "context_interpretation": "Only PLAN context may have changed during independent Swift/CI progress; its Android execution section still equals accepted1f114d8f. No bound implementation input changed.",
    "owned_files": [
        "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java",
        "native/android/tests/OwnerLifecycleV2HostTests.java",
        "native/android/tests/run-owner-core-host.py",
        "docs/android-public-owner-core.md",
        "verification/android-public-owner-core/**"
    ],
    "selected_scope": "Package-private independently authored Java decision core outside exported adapter maps, with deterministic actual host tests. No Android effect runner or public Activity integration.",
    "root_contract_clarifications": [
        "Use bounded retained state and bounded per-call decision batches. An ever-growing action history belongs only to the test recorder, never the production core.",
        "Injected owner-thread assertion is trusted to check or throw without reentry/effects. Every entry, including stale deliveries, validates thread ownership before observing/mutating core state.",
        "Only the matching initial-open operation may first bind an acquired coordinator identity, including after retirement for one terminal close. Foreign/duplicate completions cannot adopt or close a foreign resource; refresh/input completions cannot replace ownership.",
        "Opening failure with an acquired resource must still request its one close. In-flight operation that never returns leaves actual cleanup pending; no guaranteed reclamation is inferred.",
        "The later effect runner owns actual registration/cleanup attempts and fatal error propagation. Core action emission alone does not establish listener, native gate, JNI or setter revocation safety.",
        "Keep pause/resume/configuration, focus invalidation and dirty epoch semantics explicit. Epoch exhaustion is terminal; no token reuse, wrap, event queue or replay.",
        "No public V2, API28 support, saved-state continuity, resource/font/accessibility or native environment claim. Existing unsupported errors and current source-pair1 remain unchanged."
    ],
    "verification": "Compile exact two Java sources using official javac --release17 -Xlint:all -Werror and empty accidental class/source paths; execute deterministic controls with fake queue/facts and actual core. Bind versions/source/outputs/classes; preserve failures and owned cleanup. Independent review follows.",
    "platform_source_precision": "Proposal supplement records access date only; exact per-request fetch timestamps were not retained. This does not qualify platform runtime behavior.",
    "implementation_accepted": False,
    "profile_update_or_public_routing_selected": False,
    "native_UI_capture_or_device_execution_authorized": False,
    "GA_qualified": False,
    "errors": [],
}
(OUT / "implementation-selection.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ("status", "contract_members_verified", "contract_bytes_verified", "current_inputs_equal_frozen", "implementation_accepted")}))
