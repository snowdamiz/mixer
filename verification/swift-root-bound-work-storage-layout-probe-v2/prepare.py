#!/usr/bin/env python3
"""Prepare the narrow v2 overlay without changing or executing the sealed packet."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import sys

from strict_json import loads

D = Path(__file__).resolve().parent
R = D.parents[1]
O = R / 'verification/swift-root-bound-work-storage-layout-probe'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def row(path, base=R):
    assert path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    return {'path': str(path.relative_to(base)) if path.is_relative_to(base) else str(path), 'bytes': len(raw), 'sha256': sha(raw)}
def put(path, obj):
    with path.open('x') as handle: json.dump(obj, handle, indent=2, sort_keys=True); handle.write('\n')
def main():
    assert not (D/'plan.json').exists() and not (D/'seal.json').exists()
    assert not (O/'build').exists() and not (O/'command').exists()
    original_seal = row(O/'seal.json')
    assert original_seal['sha256'] == 'c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9'
    seal = loads((O/'seal.json').read_text()); assert len(seal['members']) == 173
    for member in seal['members']: assert row(O/member['path'], O) == member
    assert {str(path.relative_to(O)) for path in O.rglob('*') if path.is_file()} == {member['path'] for member in seal['members']} | {'seal.json'}
    original_plan = row(O/'plan.json')
    assert original_plan['sha256'] == 'b76ab36cf7bc1137842ec3bc63d64eb30594e53dfb76c93abdc06e15cb1ae04b'
    plan = loads((O/'plan.json').read_text())
    plan['status'] = 'PREPARED_V2_FROZEN_AWAITING_ROOT_INTERNAL_COMPILER_RELEASE'
    plan['prepared_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    plan['original_packet'] = {'seal': original_seal, 'plan': original_plan, 'members': 173,
        'tree_sha256': seal['tree_sha256'], 'all_existing_files_and_seal_immutable': True}
    plan['diagnostic_source_directory'] = str(O/'source/vm')
    plan['execution_build_directory'] = str(O/'build')
    plan['execution_build_ownership'] = 'Transient directory becomes execution-owned only after exact root release; it must be absent prelaunch. Original sealed members and source remain immutable. All command evidence belongs to v2.'
    plan['scripts'] = [row(D/name, D) for name in ['prepare.py','check.py','controls.py','diagnostics.py','run.py','launch.py','strict_json.py','verify_and_seal.py']]
    plan['narrow_corrections'] = {
        'strict_JSON': 'Reject duplicate object keys at every depth, including conflicting or identical duplicates; reject non-finite JSON constants. Apply to diagnostic and custody JSON parsing.',
        'tracked_launch': 'Signal handlers only record SIGALRM/SIGINT/SIGTERM/SIGHUP. Protected work checkpoints before/after preflight/launch and during capture raise pending interruption; launch-in-progress stays true across Popen through internal handle assignment. The post-launch checkpoint follows retention. Outer finally reads retained handle even before caller assignment. Constructor failure clears flag. Cleanup/finalization call no raising signal checkpoint.',
        'signal_mask': 'Require empty inherited blocked set via observational pthread_sigmask(SIG_BLOCK, empty set); never block signals or use preexec_fn.',
        'unchanged': ['original173 sealed members','original and diagnostic146 trees','exact three source edits','28 named/actual anonymous closure query roster','argv','cwd','environment','compiler/toolchain identity','55-second one-command bounds','preaccess oracle'],
        'compiler_or_runtime_used_for_correction': False}
    plan['argv_sha256_canonical_JSON'] = sha(canonical(plan['argv']))
    plan['environment_sha256_canonical_JSON'] = sha(canonical(plan['environment']))
    patch = ''
    for name in ['check.py','controls.py','diagnostics.py','run.py']:
        patch += ''.join(difflib.unified_diff((O/name).read_text().splitlines(True),(D/name).read_text().splitlines(True),fromfile='v1/'+name,tofile='v2/'+name))
    for name in ['strict_json.py','launch.py']:
        patch += ''.join(difflib.unified_diff([], (D/name).read_text().splitlines(True),fromfile='/dev/null',tofile='v2/'+name))
    (D/'correction-delta.patch').write_text(patch)
    put(D/'plan.json', plan)
    put(D/'preparation-receipt.json', {'schema': 2, 'command': [str(Path(sys.executable).resolve()),'-B',str(D/'prepare.py')],
        'python': sys.version, 'plan_sha256': sha((D/'plan.json').read_bytes()), 'original_seal_sha256': original_seal['sha256'],
        'original_plan_sha256': original_plan['sha256'], 'original173_members_and_membership_verified_unchanged': True,
        'exact_argv_environment_source_trees_preserved': True, 'compiler_runtime_or_child_processes_started': 0,
        'owned_build_directory_created': False, 'scope': 'Separate source/offline v2 correction; original sealed packet unchanged.'})
    print(json.dumps({'status':'prepared-v2-not-executed','plan_sha256':sha((D/'plan.json').read_bytes()),
                      'argv_sha256':plan['argv_sha256_canonical_JSON'],'environment_sha256':plan['environment_sha256_canonical_JSON']}))
if __name__ == '__main__': main()
