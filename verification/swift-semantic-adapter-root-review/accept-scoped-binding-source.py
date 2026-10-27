"""One-shot bounded lifetime acceptance and explicit conditional source rebind."""
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
OUT = HERE / "scoped-binding-root-check"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2)
        f.write("\n")


def verify(name, expected, count, size):
    folder = ROOT / "verification" / name
    raw = (folder / "seal.json").read_bytes()
    assert sha(raw) == expected
    seal = json.loads(raw)
    assert len(seal["members"]) == count
    assert sum(x["bytes"] for x in seal["members"]) == size
    actual = {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file() and p != folder/"seal.json"}
    assert actual == {m["path"] for m in seal["members"]}
    for m in seal["members"]:
        path = folder / m["path"]
        assert not path.is_symlink() and path.resolve().is_relative_to(folder.resolve())
        data = path.read_bytes()
        assert len(data) == m["bytes"] and sha(data) == m["sha256"], str(path)
    return dict(path=str(folder.relative_to(ROOT)), seal_sha256=expected, members=count, bytes=size)


assert not OUT.exists(), "Do not replay or overwrite this root attempt"
specs = [
    ("swift-guarded-snapshot-scoped-binding-source", "84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2",200,24834896),
    ("swift-guarded-snapshot-scoped-binding-independent", "e11d9eff0eda83ccf46563526e3c7025172cc8e05513b4a9ba1a5a0d9c13344a",33,14913574),
]
packets = [verify(*spec) for spec in specs]
OUT.mkdir()
argv = [sys.executable,"-B",str(ROOT/packets[1]["path"]/"check.py"),"--read-only"]
environment = {"PATH":"/usr/bin:/bin","PYTHONDONTWRITEBYTECODE":"1"}
plan = dict(argv=argv, environment=environment, cwd=str(ROOT), deadline_seconds=45,
            python_version=sys.version, python_sha256=sha(Path(sys.executable).read_bytes()),
            script_sha256=sha(Path(__file__).read_bytes()),
            source_revision="b20cd3bcd83f9110fbbc62ce60a265373f2a85e5",
            candidate_source_tree_sha256="69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7",
            scope="pure host read-only retained compiler/source/MIR review; no new compiler or runtime")
put(OUT/"plan.json",plan)
start=time.monotonic()
child=subprocess.Popen(argv,cwd=ROOT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
timed=False
try:
    stdout,stderr=child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed=True
    os.killpg(child.pid,signal.SIGTERM)
    try:
        stdout,stderr=child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGKILL)
        stdout,stderr=child.communicate(timeout=5)
try:
    os.killpg(child.pid,0)
    absent=False
except ProcessLookupError:
    absent=True
(OUT/"stdout").write_bytes(stdout)
(OUT/"stderr").write_bytes(stderr)
receipt=dict(plan,exit_code=child.returncode,timed_out=timed,elapsed_seconds=time.monotonic()-start,
             owned_child_reaped=True,owned_group_absent=absent,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
put(OUT/"receipt.json",receipt)
assert child.returncode==0 and absent and not timed
result=json.loads(stdout)
assert (result["production_constructs"],result["production_functions"],result["standalone_constants"],result["layouts"],result["adversarial_controls"])==(6006,2020,1785,46,38)
assert packets==[verify(*spec) for spec in specs]
previous=HERE/"guarded-snapshot-outer-parent-work-storage-host-acceptance.json"
assert sha(previous.read_bytes())=="8b6190049be7d5c995b6bd01c477454e503ac1dcad518602370416f510779d9c"
ind=ROOT/packets[1]["path"]
acceptance=dict(schema=1,at=datetime.now(timezone.utc).isoformat(),
    status="root-accepted-scoped-immutable-binding-source-with-mandatory-full-MIR-completeness-amendment",
    producer=packets[0],independent=packets[1],root_check=str((OUT/"receipt.json").relative_to(ROOT)),
    root_check_sha256=sha((OUT/"receipt.json").read_bytes()),
    previous_source_tree_sha256="27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3",
    source_tree_sha256=plan["candidate_source_tree_sha256"],source_members=146,unchanged_source_members=145,
    source_delta="Six types use scoped shared lifetimes; affected signatures/comments only; all selectors Pending.",
    production_functions=2020,braced_const_static_anonymous=248,standalone_constants=1785,
    emitted_allocation_blocks=1953,distinct_allocation_ids=1459,production_constructs=6006,
    mandatory_amendment=dict(path=str((ind/"standalone-constants.json").relative_to(ROOT)),sha256=sha((ind/"standalone-constants.json").read_bytes()),
        producer_4221_claim="braced constructs only; 1785 standalone constants additionally required",raw_identical=1746,display_coordinate_only=39),
    exact_allocation_payload_extent_alignment_relocation_correspondence=True,
    layout_observations=46,independent_adversarial_controls=38,
    retained_compilers=dict(positive_exit=0,negative_exit=1,negative_codes=["E0515","E0515","E0506","E0505","E0382"],both_children_reaped_groups_absent_scratch_removed=True),
    new_root_or_independent_compiler_invocations=0,
    explicit_conditional_source_work_storage_rebind=dict(
        previous_acceptance=str(previous.relative_to(ROOT)),previous_acceptance_sha256=sha(previous.read_bytes()),
        selected=True,unit="unchanged logical source/typed-role/native-inline interface only",
        basis="Complete production MIR, actual layout, source-field and ownership/lifetime correspondence including mandatory standalone amendment",
        outer_work=2706170,outer_roles=130,outer_operations=386,new_outer_inline=56414,
        fixed_P0=292037,whole_fixed=895084428325956794,residual_work_inputs=10,
        prior_backing_identity_native_error_destructor_upstream_obligations_preserved=True,
        future_provider_source_covered=False,operational_pricing_or_root_funding=False),
    actual_bounded_input_acquisition_or_authenticated_owner=False,
    actual_identity_path_binding=False,root_policy_account_quote_selected=False,
    L_str5080_selected=False,linked_executable_closure=False,
    healthy_cleanup_or_product_runtime=False,native_runtime_FieldLog_OTA_GA=False,
    preserved_producer_and_reviewer_failures=True,
    pending=["Actual immutable inputs and native path correspondence", "Reviewed prepaid child-side acquisition and immutable owner", "New provider work/inline/backing and complete original diagnostics", "Root policy/account/whole quote and operational funding", "Executable closure, successful fixture, healthy cleanup and paused native/runtime/FieldLog/OTA/GA gates"])
path=HERE/"guarded-snapshot-scoped-binding-source-host-acceptance.json"
put(path,acceptance)
print(json.dumps(dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()),conditional_source_rebind=True,operational_grant=False)))
