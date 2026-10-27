"""One-shot root custody and read-only independent reconstruction acceptance."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "owned-string-exact-binding-root-check"
ACCEPT = HERE / "guarded-snapshot-string-exact-binding-host-acceptance.json"
assert not OUT.exists() and not ACCEPT.exists(), "one-shot root check"
OUT.mkdir()
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def custody():
    result = []
    for name, expected, count, total in [
        ("swift-guarded-snapshot-string-exact-binding-correction", "4eb0437b5ed1f7ec056340ffac08a0221cfd5f6f216a9d3aebb6fd4d25cc5f4b", 895, 70066404),
        ("swift-guarded-snapshot-string-exact-binding-independent", "5cc1e09727426ae84ef0c078c7a20153886d72495a1b4949ee31f69e6a37c956", 176, 14734444),
    ]:
        packet = ROOT / "verification" / name
        raw = (packet / "seal.json").read_bytes()
        assert sha(raw) == expected
        seal = json.loads(raw)
        names = [m["path"] for m in seal["members"]]
        assert len(names) == len(set(names)) == seal["member_count"] == count
        assert sum(m["bytes"] for m in seal["members"]) == seal["bytes"] == total
        assert all(not p.is_symlink() for p in packet.rglob("*"))
        assert {str(p.relative_to(packet)) for p in packet.rglob("*") if p.is_file()} == set(names) | {"seal.json"}
        for m in seal["members"]:
            p = Path(m["path"])
            assert not p.is_absolute() and ".." not in p.parts
            body = (packet / p).read_bytes()
            assert len(body) == m["bytes"] and sha(body) == m["sha256"], m["path"]
        result.append({"path": str(packet.relative_to(ROOT)), "seal_sha256": expected, "members": count, "bytes": total})
    return result


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


before = custody()
review_dir = ROOT / "verification/swift-guarded-snapshot-string-exact-binding-independent"
commands = [[sys.executable, "-B", str(review_dir / "check.py")],
            [sys.executable, "-B", str(review_dir / "audit.py"), "--check"]]
plan = {"commands": commands, "cwd": str(ROOT), "timeout_seconds_each": 55,
        "python": sys.version, "python_executable_sha256": sha(Path(sys.executable).resolve().read_bytes()),
        "script_sha256": sha(Path(__file__).read_bytes()),
        "HEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=10, text=True).strip(),
        "custody": before, "scope": "read-only independent source/MIR reconstruction; no compiler/product/native execution"}
save(OUT / "plan.json", plan)
receipts = []
outputs = []
for index, argv in enumerate(commands):
    start = time.monotonic()
    child = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed = False
    try:
        stdout, stderr = child.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed = True
        if group_exists(child.pid):
            os.killpg(child.pid, signal.SIGTERM)
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if group_exists(child.pid):
                os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate(timeout=5)
    for name, data in [("stdout", stdout), ("stderr", stderr)]:
        with (OUT / (str(index) + "-" + name)).open("xb") as stream:
            stream.write(data)
    receipt = {"argv": argv, "exit": child.returncode, "timed_out": timed,
               "elapsed_seconds": time.monotonic() - start, "child_pid_pgid": child.pid,
               "child_reaped": child.returncode is not None, "owned_group_absent": not group_exists(child.pid),
               "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr),
               "plan_sha256": sha((OUT / "plan.json").read_bytes())}
    save(OUT / (str(index) + "-receipt.json"), receipt)
    receipts.append(receipt)
    assert not timed and child.returncode == 0 and receipt["owned_group_absent"]
    assert custody() == before
    outputs.append(json.loads(stdout))
assert outputs[0]["complete_input_files"] == 2046 and outputs[0]["qualifying_receipts"] == 10
analysis = outputs[1]
for key, value in {"compiled_headers_independently_parsed": 2009, "selected_bodies": 525,
                   "selected_edges": 1908, "primitive_str_assignments": 80,
                   "direct_ports": 9, "direct_and_nested_ports": 257,
                   "nonidentical_structural_pairs_solved": 323, "source_aliases_rebound_to_declarations": 129,
                   "allocation_max_bytes": 5080}.items():
    assert analysis[key] == value, key
report = json.loads((review_dir / "review.json").read_text())
assert report["findings"] == [] and not report["additional_candidate_correction_required"]
assert report["prior_independent_adverse_methods_passed"] == 17
assert report["new_independent_adverse_methods_passed"] == 12
save(ACCEPT, {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "root-accepted-S1-S5-exact-binding-and-conditional-original-source-string-provenance",
    "source_tree_sha256": report["source_tree_sha256"], "host_tree_sha256": report["host_tree_sha256"],
    "custody": before, "independent_review_sha256": sha((review_dir / "review.json").read_bytes()),
    "fresh_readonly_root_checks": str(OUT.relative_to(ROOT)),
    "root_check_receipts": [{"path": str((OUT / (str(i) + "-receipt.json")).relative_to(ROOT)),
                             "sha256": sha((OUT / (str(i) + "-receipt.json")).read_bytes())} for i in range(2)],
    "S1_S5_dispositions": report["dispositions"], "independent_analysis": analysis,
    "prior_adverse_methods_passed": 17, "new_adverse_methods_passed": 12,
    "conditional_original_source_byte_envelope": 5080,
    "caller_preconditions": ["exact selected loader proof forwarded unchanged", "fresh cancellation/control and no incoming failure latch", "no arbitrary incoming str/Fault/failure or custom callback", "Policy::swift and selected concrete trait specializations", "no intervening mutation", "native path/OsStr/io::Error backing remains separate"],
    "current_outer_scoped_provider_source_requires_separate_rebind": True,
    "mandatory_6006_structural_constructs_and_1785_standalone_constants_replaced": False,
    "L_str_selected_for_current_provider_or_whole_host": False,
    "actual_P0_caller_or_immutable_executable_session_binding_selected": False,
    "root_policy_or_funding_or_operational_native_OTA_GA": False,
    "historical_producer_and_reviewer_failures_preserved": True,
})
print(json.dumps({"path": str(ACCEPT.relative_to(ROOT)), "sha256": sha(ACCEPT.read_bytes()), "original_source_conditional_envelope": 5080, "current_provider_rebind_required": True}))
