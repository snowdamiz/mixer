"""Select real private Rust ownership source work without granting native authority."""
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
PACKET = ROOT / 'verification/swift-guarded-snapshot-actual-owner-rust-selection'
OUT = HERE / 'actual-owner-Rust-selection-root-check'
ACCEPT = HERE / 'guarded-snapshot-actual-owner-Rust-implementation-selection.json'
assert not OUT.exists() and not ACCEPT.exists()
OUT.mkdir()
sha = lambda b: hashlib.sha256(b).hexdigest()
def row(p):
    data = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}
def save(p, data):
    with p.open('x') as f: json.dump(data, f, indent=2); f.write('\n')
seal_raw = (PACKET / 'seal.json').read_bytes()
assert sha(seal_raw) == '1b0c3234a22f559280f5eb461bab5bf367a2ee0b7acda45c744b1da92b10d0f7'
seal = json.loads(seal_raw)
members = seal['members']
assert len(members) == seal['member_count'] == 32
assert sum(m['bytes'] for m in members) == 1392587
assert {str(p.relative_to(PACKET)) for p in PACKET.rglob('*') if p.is_file()} == {m['path'] for m in members} | {'seal.json'}
assert all(not p.is_symlink() for p in PACKET.rglob('*'))
for m in members:
    path = Path(m['path'])
    assert not path.is_absolute() and '..' not in path.parts
    data = (PACKET / path).read_bytes()
    assert len(data) == m['bytes'] and sha(data) == m['sha256']
selection = json.loads((PACKET / 'selection.json').read_bytes())
test_plan = json.loads((PACKET / 'host-test-plan.json').read_bytes())
assert selection['source_ownership']['new_distribution_member_count'] == 146
assert len(selection['source_ownership']['changed_existing_members']) == 2
assert len(test_plan['host_tests_required']) == 13
assert len(test_plan['compiler_rejection_probes']) == 8
env = {'PATH':'/opt/homebrew/bin:/usr/bin:/bin', 'LANG':'C', 'LC_ALL':'C', 'TZ':'UTC',
       'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONHASHSEED':'0'}
argv = [sys.executable, '-B', str(PACKET / 'check_selection.py'), '--check-seal']
plan = {'argv':argv,'environment':env,'cwd':str(ROOT),'timeout_seconds':45,'python':sys.version,
        'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),
        'root_script':row(Path(__file__).resolve()),'checker':row(PACKET/'check_selection.py'),
        'source_revision':'d6af73813244c330a979afb83b45f53490ff5b29','packet_seal':row(PACKET/'seal.json')}
save(OUT/'plan.json',plan)
start = time.monotonic()
child = subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
timed = False
try: stdout,stderr = child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed = True
    os.killpg(child.pid,signal.SIGTERM)
    try: stdout,stderr = child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGKILL)
        stdout,stderr = child.communicate(timeout=5)
try:
    os.killpg(child.pid,0)
    absent = False
except ProcessLookupError: absent = True
for name,data in [('stdout',stdout),('stderr',stderr)]:
    with (OUT/name).open('xb') as f: f.write(data)
save(OUT/'receipt.json',{'argv':argv,'exit':child.returncode,'timed_out':timed,
    'elapsed_seconds':time.monotonic()-start,'owned_pid':child.pid,'owned_pgid':child.pid,
    'child_reaped':child.returncode is not None,'owned_group_absent':absent,
    'outputs':[row(OUT/n) for n in ['stdout','stderr']],'plan':row(OUT/'plan.json')})
assert child.returncode == 0 and not timed and absent
save(ACCEPT,{'schema':1,'at':datetime.now(timezone.utc).isoformat(),
    'status':'root-selected-isolated-actual-Rust-ownership-implementation-and-finite-host-test-slice',
    'packet_seal':row(PACKET/'seal.json'),'selection_contract':row(PACKET/'selection.json'),
    'source_map':row(PACKET/'source-map.json'),'prospective_test_plan':row(PACKET/'host-test-plan.json'),
    'root_check':row(OUT/'receipt.json'),
    'A1':'selected: preserve actual executable drop before source/proof and other loader local Vec lifetimes; retain complete typed LoaderOutcome and proof backing; charge actual overlap rather than synthetic four-buffer ownership',
    'A2':'selected: isolated146-member source implementation; only two named existing members change; host11 and host_account_v1.rs unchanged',
    'implementation_ownership':'verification/swift-guarded-snapshot-actual-owner-rust-implementation',
    'independent_preaccess_ownership':'verification/swift-guarded-snapshot-actual-owner-rust-preaccess',
    'source_ownership':selection['source_ownership'],
    'required_host_cases':[r['id'] for r in test_plan['host_tests_required']],
    'compiler_plan':{'planned_compiler_invocations':11,'production_metadata_MIR':1,'test_binary_builds':2,
        'negative_compiler_probes':8,'simultaneous_compilers':1,'layout_queries':0,
        'additional_targeted_repair_compiles_max':3,
        'repairs_only_after_specific_source_or_probe_correction_no_blind_retry':True,
        'final_host_runs':2,'additional_targeted_repair_host_runs_max':2,
        'host_filters':['prepaid_actual_owner_v1'],'each_command_seconds_max':55,
        'stdout_stderr_each_bytes_max':4194304,'full_MIR_retained_separately':True},
    'production_boundary':'zeroarg startup refuses BootstrapPolicyPending before any input effect; no native admission/raw handle conversion/allocator assumption/source-policy grant',
    'actual_source_requirement':'implement immutable owned backing, affine reservations and fixed partial owners, bounded read/path cores, real binary record checks, typed correlation and retirement; test guards exercise the same ownership cores; no unconditional successful admission or synthetic dictionary authority',
    'independent_preaccess_review_may_require_contract_correction':True,
    'all_existing_loader_checks_and_original_diagnostics_preserved':True,
    'old_source_prices_layouts_bind_new_source':False,'actual_native_acquisition_authorized':False,
    'genuine_fixture_loader_writer_execution_authorized':False,
    'root_policy_funding_native_FieldLog_OTA_GA_selected':False,
    'all17_fields_8_claims_3_Pending_selectors_6_Pending_upstream_preserved':True,
    'physical_native_UI_capture_checks_remain_paused':True})
print(json.dumps({'selection':row(ACCEPT),'packet_members':32,'implementation_authorized':True,
    'native_authority':False,'planned_compiler_invocations':11,'targeted_repair_compiles_max':3}))
