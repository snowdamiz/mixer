"""Complete root acceptance after preserving a read-only output-order comparison failure; no grant."""
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
OUT = Path(__file__).resolve().parent
COMMANDS = OUT / "native-open-and-outer-cost-root-checks"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def packet(name, expected, count, size):
    path = ROOT / "verification" / name
    seal = path / "seal.json"
    raw = seal.read_bytes()
    assert sha(raw) == expected, name
    data = json.loads(raw)
    members = data["members"]
    assert len(members) == count and sum(x["bytes"] for x in members) == size
    names = set()
    for item in members:
        p = path / item["path"]
        assert not p.is_symlink() and p.resolve().is_relative_to(path.resolve())
        b = p.read_bytes()
        assert len(b) == item["bytes"] and sha(b) == item["sha256"], str(p)
        assert item["path"] not in names
        names.add(item["path"])
    assert names == {str(p.relative_to(path)) for p in path.rglob("*") if p.is_file() and p != seal}
    return dict(path=str(path.relative_to(ROOT)), seal_sha256=expected, members=count, bytes=size)


def run(name, argv):
    target = COMMANDS / name
    target.mkdir()
    env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
    start = time.monotonic()
    child = subprocess.Popen(argv, cwd=ROOT, env=env, start_new_session=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(child.pid, signal.SIGTERM)
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate(timeout=5)
    try:
        os.killpg(child.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
    (target / "stdout").write_bytes(stdout)
    (target / "stderr").write_bytes(stderr)
    receipt = dict(argv=argv, environment=env, cwd=str(ROOT), exit_code=child.returncode,
                   timed_out=timed_out, elapsed_seconds=time.monotonic()-start,
                   owned_child_reaped=True, owned_group_absent=absent,
                   stdout_sha256=sha(stdout), stderr_sha256=sha(stderr),
                   tool_version=sys.version, tool_sha256=sha(Path(sys.executable).read_bytes()),
                   recorder_sha256=sha(Path(__file__).read_bytes()),
                   source_revision="a32d056355ec2f417e9ef7a73788b420176377b6",
                   scope="pure host read-only rederivation of frozen source/MIR/native artifacts")
    put(target / "receipt.json", receipt)
    assert child.returncode == 0 and not timed_out and absent, receipt
    return dict(path=str((target / "receipt.json").relative_to(ROOT)),
                sha256=sha((target / "receipt.json").read_bytes()))


assert COMMANDS.exists() and not (COMMANDS / "outer-independent-v2").exists()
specs = [
    ("swift-guarded-snapshot-native-open-binary-closure", "7b5762f1955fefa2060b0d4fdb4dd393cb8b38c94078159ddf6bc538a22c67f5",112,2855785),
    ("swift-guarded-snapshot-native-open-binary-independent", "962b85ac9575316ebe37d4dfc498834adee98cf7e093a9373d654969b8f08541",59,2346441),
    ("swift-guarded-snapshot-outer-parent-work-storage", "7d7c6be167de0a7e20dbde2a50a5ea900a954a8e5e32262cf185411f1dc041b0",44,693873),
    ("swift-guarded-snapshot-outer-parent-work-storage-independent", "a879f1f44be7113c91b72faf28b5515a21f053fac68ef3b527bae1ae915901e6",77,1022535),
]
packets = [packet(*s) for s in specs]
native_receipt = COMMANDS / "native-independent/receipt.json"
native_data=json.loads(native_receipt.read_bytes())
assert native_data["exit_code"]==0 and native_data["owned_group_absent"] and not native_data["timed_out"]
native_check=dict(path=str(native_receipt.relative_to(ROOT)),sha256=sha(native_receipt.read_bytes()))
# The independent outer reviewer is a preparation writer. Import without main,
# replace only its output sink with byte comparison, and retain exact program.
outer_program = '''import importlib.util,json,sys,collections
from pathlib import Path
p=Path(sys.argv[1])
s=importlib.util.spec_from_file_location("frozen_outer_review",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def compare(name,value):
    old=json.loads((p.parent/name).read_bytes())
    if name=="assertions.json":
        assert old["count"]==value["count"]==1450
        assert collections.Counter(old["passed"])==collections.Counter(value["passed"]),name
    elif name=="native-layout-reconstruction.json":
        for obj in (old,value):
            obj["normalized_conflicts"]={k:sorted(v,key=lambda x:json.dumps(x,sort_keys=True)) for k,v in obj["normalized_conflicts"].items()}
        assert old==value,name
    else:
        assert old==value,name
m.out=compare
m.main()
'''
program_path = COMMANDS / "read-only-outer-reconstruction-v2.py"
program_path.write_text(outer_program)
outer_check = run("outer-independent-v2", [sys.executable,"-B",str(program_path),str(ROOT/packets[3]["path"]/"review.py")])
assert packets == [packet(*s) for s in specs]
put(COMMANDS/"root-replay-failure-disposition.json",dict(
    original="outer-independent/receipt.json", original_exit=1,
    cause="Root byte-order comparator did not account for two unordered diagnostic collections in independent reviewer output.",
    correction="Compare assertions.passed as complete multiplicity-preserving multiset, normalize only native-layout normalized_conflicts value order; every other value remains exact.",
    root_read_only_diagnoses=2, findings="All1450 assertion labels and each native conflict record equal with multiplicity; all other data equal.",
    other_read_only_lookup_failures=["outer independent freeze.py absent; actual finalizer is finalize.py", "no scripts path matched documentation integrity search"],
    failed_source_sha256="0c4c4b63742a04b0f36097ee61e9f783e87152b5051e4cf949609f77340f6f9f",
    corrected_script_sha256=sha(Path(__file__).read_bytes()),
    source_or_candidate_changed=False, native_check_repeated=False))
now = datetime.now(timezone.utc).isoformat()
native = json.loads((ROOT/packets[1]["path"]/"summary.json").read_bytes())
assert native["findings"] == [] and native["hostile_rejected"] == 39
assert (native["native_instructions"], native["native_relocations"]) == (438,46)
native_accept = dict(schema=1, at=now,
    status="root-accepted-conditional-source146-native-open-constructor-correspondence",
    producer=packets[0], independent=packets[1], root_rederivation=native_check,
    summary_sha256=sha((ROOT/packets[1]["path"]/"summary.json").read_bytes()),
    source_tree_sha256=native["source_tree_sha256"],
    evidence={k:native[k] for k in ("counts","LLVM_cases","hostile_rejected","positive_decoy_controls","native_functions","native_instructions","native_relocations","instructions_observed","CFG_edges","CFG_edges_observed")},
    same_backing_constructor_cases=7, exact_inert_append_bytes=646,
    inherited_open_interface="768+7*n", inherited_Error_native=23,
    raw_native_and_active_LLVM_required=True,
    private_external_effects_and_unobserved_edges_retained=True,
    no_finite_EINTR_or_OOM_healthy_refusal_claim=True,
    preserved_reviewer_failures=3,
    earlier_670_byte_assignment_description="corrected by exact retained predeclared 646-byte append and compiled manifest",
    root_binding_or_operational_pricing_grant=False, linked_executable_composition=False,
    healthy_cleanup_or_product_execution=False, native_runtime_or_OTA_or_GA=False,
    remaining=native["pending"][1:])
put(OUT/"guarded-snapshot-native-open-binary-host-acceptance.json",native_accept)
outer = json.loads((ROOT/packets[3]["path"]/"review.json").read_bytes())
assert outer["independent_assertions"]==1450 and outer["independent_adversarial_cases"]==673
assert outer["independently_reconstructed"]["totals"]["work"]==2706170
outer_accept = dict(schema=1, at=now,
    status="root-accepted-conditional-outer-parent-source-work-storage-interface",
    producer=packets[2], independent=packets[3], root_rederivation=outer_check,
    review_sha256=sha((ROOT/packets[3]["path"]/"review.json").read_bytes()),
    source_tree_sha256=outer["source_tree"],
    independent_assertions=1450, independent_adversarial_cases=673, producer_test_methods=32,
    reconstructed=outer["independently_reconstructed"], arithmetic=outer["independent_arithmetic"],
    all_new_roles_P0_until_final_result_consumed=True, alias_move_sharing_refund_credit=False,
    original_diagnostic_payload_and_backing_preserved=True,
    normal_release_only_after_payload_carrier_destruction_returns_Some=True,
    no_refund_on_None_refusal_unwind=True, preserved_reviewer_failures=3,
    graph_leaves=43, explicit_terminal_paths=56,
    missing_result_layout={"size":8,"align":8,"expected_compile_exit":1,"E0308_errors":2,"production_pass":False},
    source_rebind_only=True, actual_provider_or_identity_binding=False,
    selectors="all Pending; actual I/U/entry/release zero",
    required_residual_work_inputs=10, L_str5080_selected=False,
    root_funding_or_operational_grant=False, linked_binary_or_runtime_qualification=False,
    native_runtime_or_OTA_or_GA=False, remaining=outer["limitations"])
put(OUT/"guarded-snapshot-outer-parent-work-storage-host-acceptance.json",outer_accept)
ci_dir=ROOT/"verification/github-delivery-host-interface-amendment"
ci=json.loads((ci_dir/"ci-jobs-4.stdout").read_bytes())
assert ci["headSha"]=="a32d056355ec2f417e9ef7a73788b420176377b6" and ci["status"]=="completed" and ci["conclusion"]=="success"
assert len(ci["jobs"])==6 and all(j["conclusion"]=="success" for j in ci["jobs"])
assert sum(len(j["steps"]) for j in ci["jobs"])==64
put(ci_dir/"terminal-ci-status.json",dict(schema=1,at=now,commit=ci["headSha"],run=ci["databaseId"],attempt=ci["attempt"],status="completed",conclusion="success",jobs=6,steps=64,url=ci["url"],observation="ci-jobs-4.stdout",observation_sha256=sha((ci_dir/"ci-jobs-4.stdout").read_bytes()),scope="GitHub host CI; paused native device/simulator/emulator checks remain pending"))
for p in (OUT/"guarded-snapshot-native-open-binary-host-acceptance.json",OUT/"guarded-snapshot-outer-parent-work-storage-host-acceptance.json",ci_dir/"terminal-ci-status.json"):
    print(json.dumps(dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes()))))
