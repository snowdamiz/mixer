"""One-shot root receiver-bridge review; never release or runtime admission."""
from datetime import datetime, timezone
import copy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "verification/android-editor-membership-compiled-boundary-qualification/delegated-overload-association-v2"
SEAL = "4fec770228b4420a56bd1ab0c48446a09bfac8037b80c498c412f627abfb81cf"
JDK = ROOT / "verification/android-editor-membership-compiled-boundary-qualification/state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home"
REPLAY = OUT / "delegated-receiver-v2-fresh-replay"
RECEIPT = OUT / "delegated-receiver-v2-selection.json"

def identity(path):
    assert path.is_file() and not path.is_symlink(), path
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

def custody():
    assert identity(CANDIDATE / "seal.json")["sha256"] == SEAL
    seal = json.loads((CANDIDATE / "seal.json").read_bytes())
    names = set()
    for item in seal["members"]:
        rel = PurePosixPath(item["path"])
        assert not rel.is_absolute() and ".." not in rel.parts and str(rel) not in names
        names.add(str(rel))
        assert identity(CANDIDATE / rel) == {k: item[k] for k in ("bytes", "sha256")}
    nodes = list(CANDIDATE.rglob("*"))
    assert not any(p.is_symlink() for p in nodes)
    assert {str(p.relative_to(CANDIDATE)) for p in nodes if p.is_file()} == names | {"seal.json"}
    assert len(names) == 740 and sum(i["bytes"] for i in seal["members"]) == 7039543
    return {"path": str(CANDIDATE.relative_to(ROOT)), "seal_sha256": SEAL,
            "members": 740, "member_bytes": 7039543}

commands = []
def command(label, argv, maximum):
    start = time.monotonic()
    paths = {suffix: OUT / ("delegated-receiver-v2-" + label + "." + suffix) for suffix in ("stdout", "stderr")}
    with paths["stdout"].open("xb") as stdout, paths["stderr"].open("xb") as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        timed_out = False
        try:
            child.wait(timeout=maximum)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        except BaseException:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            raise
    record = {"argv": argv, "cwd": str(ROOT), "maximum_seconds": maximum,
              "exit": child.returncode, "timed_out": timed_out, "child_reaped": True,
              "elapsed_seconds": time.monotonic() - start,
              **{k: {"path": str(v.relative_to(ROOT)), **identity(v)} for k, v in paths.items()}}
    commands.append(record)
    (OUT / "delegated-receiver-v2-root-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert child.returncode == 0 and not timed_out, record

assert __debug__ and not RECEIPT.exists() and not REPLAY.exists()
candidate = custody()
command("fresh-jvm", [sys.executable, "-B", str(CANDIDATE / "replay.py"), "--jdk", str(JDK), "--output", str(REPLAY)], 60)
control_file = OUT / "delegated-receiver-v2-fresh-controls.json"
command("composed-controls", [sys.executable, "-B", str(CANDIDATE / "test_receiver_join.py"),
        "--producer-raw", str(CANDIDATE / "producer-run/direct-setComposingRegionWithAttributes.rows.jsonl.gz"),
        "--replay-raw", str(REPLAY / "attribute-states.rows.jsonl.gz"),
        "--receiver-fixture", str(REPLAY / "receiver-bridge-controls.json"), "--output", str(control_file)], 60)
spec = importlib.util.spec_from_file_location("_root_receiver_bridge_v2", CANDIDATE / "delegated_raw_v2.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
with gzip.open(REPLAY / "attribute-states.rows.jsonl.gz", "rt") as stream:
    rows = [json.loads(line) for line in stream]
assert len(rows) == 13 and all(api.validate_delegated_raw(r)["qualified"] is False for r in rows)
base = next(row for row in rows if row["state"] == "current")
controls = []
def refuses(name, mutate):
    row = copy.deepcopy(base)
    mutate(row)
    try:
        api.validate_delegated_raw(row)
    except api.DelegatedReceiverRefusal as failure:
        controls.append({"name": name, "refused": True, "reason": str(failure)})
    else:
        raise AssertionError("accepted root mutation: " + name)

def root_witness(row):
    for event in row["native_sequence"]:
        if event["method"] == "BaseInputConnection.setComposingRegion":
            event["receiver_identity"] = "android.view.inputmethod.BaseInputConnection@row-999999"

refuses("unchanged-root-both-raw-receiver-witness", root_witness)
refuses("reversed-first-actual-receiver-order", lambda r: r["native_receiver_bindings"].reverse())
refuses("boolean-raw-frame-index", lambda r: r["native_sequence"][0].__setitem__("frame_set", True))
refuses("float-native-event-index", lambda r: r["actual_native_outcomes"][0].__setitem__("native_event_sequence_index", 0.0))
refuses("selected-authority-receiver-null", lambda r: r["selected_event"][0]["authority"].__setitem__("receiver", None))
refuses("selected-authority-receiver-foreign", lambda r: r["selected_event"][0]["authority"].__setitem__("receiver", "android.view.inputmethod.BaseInputConnection@999999"))
refuses("zero-prefixed-global-identity", lambda r: r["native_receiver_bindings"][0].__setitem__("global_identity", r["native_receiver_bindings"][0]["class"] + "@01"))
refuses("negative-global-identity", lambda r: r["native_receiver_bindings"][0].__setitem__("global_identity", r["native_receiver_bindings"][0]["class"] + "@-1"))
refuses("missing-outcome-global-receiver", lambda r: r["actual_native_outcomes"][0].pop("receiver_identity"))
refuses("unknown-binding-field", lambda r: r["native_receiver_bindings"][0].__setitem__("trusted", True))
report = json.loads(control_file.read_bytes())
assert len(report["negative_controls"]) == 46 and report["all_controls_refused"]
replay = json.loads((REPLAY / "receipt.json").read_bytes())
assert replay["all_children_reaped"] and replay["scratch_removed"] and len(replay["commands"]) == 8
custody()
receipt = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "accepted-isolated-source-pinned-receiver-and-raw-consistency-utility", "candidate": candidate,
    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "python_version": platform.python_version(), "script": identity(Path(__file__)), "commands": commands,
    "fresh_jvm_commands": 8, "fresh_actual_states": 13, "actual_pair_serializer_assertions": 32,
    "actual_same_class_fixture": {"receivers": 2, "events": 6, "returns": 3},
    "producer_plus_fresh_raw_rows": 26, "retained_hostile_controls": 46, "independent_root_controls": controls,
    "fresh_control_report": {"path": str(control_file.relative_to(ROOT)), **identity(control_file)},
    "selected_module": identity(CANDIDATE / "delegated_raw_v2.py"), "selected_policy": identity(CANDIDATE / "policy.json"),
    "product_context": "1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd",
    "source_review": "Trace.append captures ordinal and global identity from the same Event.receiver. Exact closed mapping joins all raw events and outcomes, then original target and selected authority. Mandatory raw-v1 and corrected typed utility remain pinned closed dependencies. External source selection remains required; self-consistency is not authenticated execution.",
    "all_packet_members_unchanged_after": True, "original_failure_and_v1_packets_immutable": True,
    "all_children_reaped_and_owned_scratch_removed": True,
    "next_selected_action": "One bounded corrected selected-v4 all-selector host replay preserving original subjects/cases/history and all pending semantic obligations.",
    "pending": ["full compiled-boundary replay and all280 subjects", "all189 historical dispositions", "missing body/exceptional and enclosing observations", "complete execution closure", "canonical integration", "native runtime", "OTA", "GA"],
    "native_UI_capture_process_inventory_started": False, "full_matrix_native_OTA_GA_accepted": False}
with RECEIPT.open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(json.dumps({"status": receipt["status"], "receipt": identity(RECEIPT), "root_controls": len(controls)}))
