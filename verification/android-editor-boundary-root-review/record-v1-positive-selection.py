"""Root data-only custody and scoped selection of the five legacy witnesses."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).resolve().parent
PACKET = REPO / "verification/android-editor-membership-qualification-independent/v1-positive-preparation"
OUT = ROOT / "five-v1-positive-selection.json"


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


assert __debug__ and not OUT.exists()
seal_bytes = (PACKET / "seal.json").read_bytes()
assert digest(seal_bytes)["sha256"] == "d982305bafe8abcfc6945ea37ca8ff908aa748f00dfcad7e303517b327d74c8f"
seal = json.loads(seal_bytes)
members = {row["path"]: row for row in seal["members"]}
assert len(members) == len(seal["members"]) == 366
actual = set()
for path in PACKET.rglob("*"):
    assert not path.is_symlink(), str(path)
    if path.is_file():
        actual.add(path.relative_to(PACKET).as_posix())
assert actual == set(members) | {"seal.json"}
for name, row in members.items():
    assert digest((PACKET / name).read_bytes()) == {k: row[k] for k in ("bytes", "sha256")}, name

proposal = json.loads((PACKET / "run-1/bound-five-v1-proposal.json").read_bytes())
context = {"source_map": proposal["product_sources"], "class_map": proposal["product_class_map"]}
assert len(context["source_map"]) == 16 and len(context["class_map"]) == 209
assert digest(json.dumps(context, sort_keys=True, separators=(",", ":")).encode())["sha256"] == proposal["context_id"] == "1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd"
for name, expected in context["class_map"].items():
    assert digest((PACKET / "run-1/classes" / name).read_bytes()) == expected
body = (PACKET / "inputs/unchanged-v1Baselines.java.txt").read_bytes()
assert digest(body) == proposal["original_v1_method_body"] and len(body) == 1962
original = (PACKET / "inputs/original-NativeOwnerV2ConcreteHostTests.java").read_bytes()
assert digest(original)["sha256"] == "fc75586bd7779a693c08ac9cce3926e5ff2a7cb82d3bd2f92a7f40e764dcb74e"
assert original.count(body) == 1
assert (PACKET / "inputs/NativeOwnerV2ConcreteHostTests.java").read_bytes().count(body) == 1
commands = json.loads((PACKET / "run-1/commands.json").read_bytes())
assert len(commands) == 5
for command in commands:
    assert command["exit"] == 0 and command["reaped"] and not command["timeout"]
    for stream in ("stdout", "stderr"):
        assert digest((PACKET / "run-1" / (command["name"] + "." + stream)).read_bytes()) == command[stream]
events = proposal["event_sequence"]
assert len(events) == 1422 and proposal["checks"] == 1433
assert [event["sequence"] for event in events] == list(range(len(events)))
assert max(len(event["production_frames"]) for event in events) == 3
expected = {111: "removeViewAt", 220: "addView", 262: "setLayoutParams", 381: "setMarginEnd", 398: "setLayoutParams"}
assert {row["bci"] for row in proposal["rows"]} == set(expected)
for row in proposal["rows"]:
    assert row["authority_mode"] == "LEGACY_V1" and row["v2_fence"] is None and row["captured_attempt_identity"] is None
    assert row["caller"]["opcode"] == "invokevirtual" and row["caller"]["callee"]["name"] == expected[row["bci"]]
    assert row["entry"]["sequence"] < row["before_return"]["sequence"]
    for phase in ("entry", "before_return"):
        point = row[phase]
        event = events[point["sequence"]]
        assert event["method"] == point["method"] == row["method"]
        assert event["receiver_identity"] == point["receiver"]["identity"]
        assert event["production_frames"] == point["production_frames"] and point["native_count"] > 0
    outcome = row["enclosing_result"]
    assert outcome["normal_return"] and outcome["same_reference"] and outcome["escaped_exception"] is None
    assert outcome["actual_identity"] == outcome["expected_identity"]
cleanup = json.loads((PACKET / "run-1/cleanup.json").read_bytes())
assert cleanup["all_children_reaped"] and cleanup["scratch_removed"] and not cleanup["native_UI_capture_or_process_inventory"]

selection = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "selected-exact-five-legacy-positive-witnesses-for-future-matrix-consumption",
    "packet": str(PACKET.relative_to(REPO)), "seal": digest(seal_bytes),
    "members_verified": len(members), "bytes_verified": sum(row["bytes"] for row in members.values()),
    "root_review": ["Complete closed packet hashes and command outputs", "Exact original 1962-byte V1 method body in both original and migrated tests", "Witness and runner source inspection", "Exact 16-source/209-class context and retained product class bytes", "Five separate exact call tuples, typed enclosing results, receiver states and complete actual event sequence"],
    "selected_witness": {"path": "V1PositiveWitness.java", **digest((PACKET / "V1PositiveWitness.java").read_bytes())},
    "selected_bound_proposal": {"path": "run-1/bound-five-v1-proposal.json", **digest((PACKET / "run-1/bound-five-v1-proposal.json").read_bytes())},
    "product_context": proposal["context_id"], "legacy_call_bcis": sorted(expected),
    "independent_commands": 5, "unchanged_original_assertions": 10, "witness_checks": 1433,
    "event_bound_checks_included_in_witness_total": 1422, "maximum_actual_product_frames": 3,
    "outcome_scope": "These five native calls return void; actual entry/beforeReturn plus normal typed enclosing apply outcome and exact emitted no-catch caller establish these finite positive cases. No native nonvoid result or new visual-spacing claim is invented.",
    "remaining_conditions": ["Copy exact selected source and class identities into final closed execution inputs", "Fresh selected final producer must execute these witnesses and retain original assertions", "All 189 V2 dispositions, 38 descriptor cases, 280 source-backed semantic joins and complete typed state/content obligations remain required", "Independent v5 interpreter and execution closure review remains required"],
    "full_matrix_policy_execution_closure_canonical_native_OTA_GA_accepted": False,
    "cleanup": cleanup, "root_command": [sys.executable, "-B", str(Path(__file__).relative_to(REPO))],
    "root_python": sys.version, "root_source": digest(Path(__file__).read_bytes()),
}
OUT.write_text(json.dumps(selection, indent=2) + "\n")
print(json.dumps({"selection": str(OUT.relative_to(REPO)), **digest(OUT.read_bytes()), "members_verified": len(members)}))
