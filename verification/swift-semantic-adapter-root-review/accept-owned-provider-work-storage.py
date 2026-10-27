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
OUT = HERE / "owned-provider-work-storage-root-check"
ACCEPT = HERE / "guarded-snapshot-owned-provider-work-storage-host-acceptance.json"
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
        ("swift-guarded-snapshot-owned-provider-work-storage", "28ba8099ce8b57f91cd46baac21f130986000ecbbf7df07b16e6bf061fc342d1", 56, 13734810),
        ("swift-guarded-snapshot-owned-provider-work-storage-independent", "aeb00877856dacca762ba9c885d043ed4b785cabe811e8f31251eaa55e4ada6b", 77, 820412),
    ]:
        packet = ROOT / "verification" / name
        raw = (packet / "seal.json").read_bytes()
        assert sha(raw) == expected
        seal = json.loads(raw)
        names = [m["path"] for m in seal["members"]]
        assert len(names) == len(set(names)) == seal["member_count"] == count
        assert sum(m["bytes"] for m in seal["members"]) == seal["total_bytes"] == total
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
review_dir = ROOT / "verification/swift-guarded-snapshot-owned-provider-work-storage-independent"
argv = [sys.executable, "-B", str(review_dir / "check_packet.py")]
plan = {"argv": argv, "cwd": str(ROOT), "timeout_seconds": 55,
        "python": sys.version, "python_executable_sha256": sha(Path(sys.executable).resolve().read_bytes()),
        "script_sha256": sha(Path(__file__).read_bytes()),
        "HEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=10, text=True).strip(),
        "custody": before, "scope": "read-only independent reconstruction; no compiler/product/native execution"}
save(OUT / "plan.json", plan)
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
    with (OUT / name).open("xb") as stream:
        stream.write(data)
receipt = {"argv": argv, "exit": child.returncode, "timed_out": timed,
           "elapsed_seconds": time.monotonic() - start, "child_pid_pgid": child.pid,
           "child_reaped": child.returncode is not None, "owned_group_absent": not group_exists(child.pid),
           "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr),
           "plan_sha256": sha((OUT / "plan.json").read_bytes())}
save(OUT / "receipt.json", receipt)
assert not timed and child.returncode == 0 and receipt["owned_group_absent"]
assert custody() == before
output = json.loads(stdout)
assert output["success"] and output["roles"] == 193 and output["operations"] == 565
assert output["logical_P0_addition"] == 9696 and output["host_methods"] == 20 and output["adverse_cases"] == 1013
report = json.loads((review_dir / "review.json").read_text())
assert report["findings_requiring_producer_correction"] == []
assert report["arithmetic"]["provider_source_fixed"] == 276580
assert report["arithmetic"]["actual_max22_body_coefficient"] == 1324
assert report["arithmetic"]["conditional_fixed_P0"] == 301733
assert len(report["strict_positive_external_std_terms"]) == 14
assert len(report["old_residual_terms"]) == 10 and len(report["strict_positive_upstream_work_terms"]) == 2
save(ACCEPT, {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "root-accepted-bounded-conditional-provider-source-work-and-logical-slot-interface",
    "source_tree_sha256": report["source_tree_sha256"], "custody": before,
    "independent_review_sha256": sha((review_dir / "review.json").read_bytes()),
    "fresh_readonly_root_check": str(OUT.relative_to(ROOT)), "root_check_receipt_sha256": sha((OUT / "receipt.json").read_bytes()),
    "arithmetic": report["arithmetic"], "independent_reconstruction": report["independent_reconstruction"],
    "host_methods": 20, "adverse_cases": 1013,
    "old_residual_terms": report["old_residual_terms"],
    "strict_positive_external_std_terms": report["strict_positive_external_std_terms"],
    "strict_positive_upstream_work_terms": report["strict_positive_upstream_work_terms"],
    "required": ["all written slots through all15 phases", "12 full preimages plus5 native plus5 separately retained bodies", "original diagnostics and future root/backing", "all six original child components", "normal Some release only after actual original payload and carrier destruction"],
    "mandatory_base_correspondence": {"constructs": 6006, "standalone_constants": 1785},
    "native_layout_observation": {"closure_bytes": 16, "alignment": 8, "named_dimensions": 36, "raw_query_metadata_removed": True},
    "all_six_upstream_requirements": "Pending", "all_three_selectors": "Pending",
    "L_str_selected": False, "external_prices_or_root_funding_selected": False,
    "actual_acquisition_or_authenticated_owner_or_execution": False,
    "logical_slots_are_physical_stack_or_allocator_footprint": False,
    "operational_grant_or_native_FieldLog_OTA_GA": False,
    "historical_producer_and_reviewer_failures_preserved": True,
})
print(json.dumps({"path": str(ACCEPT.relative_to(ROOT)), "sha256": sha(ACCEPT.read_bytes()), "source_work": output["source_work"], "P0_addition": 9696, "conditional_fixed_P0": 301733}))
