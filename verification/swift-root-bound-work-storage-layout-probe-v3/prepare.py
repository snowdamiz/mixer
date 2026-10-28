#!/usr/bin/env python3
"""Prepare only the finite-publication v3 overlay; never start a child."""
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
V = R / 'verification/swift-root-bound-work-storage-layout-probe-v2'
P = R / 'verification/swift-root-bound-work-storage-layout-preaccess'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def row(path, base=R):
    assert path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    return {'path': str(path.relative_to(base)) if path.is_relative_to(base) else str(path), 'bytes': len(raw), 'sha256': sha(raw)}
def put(path, obj):
    with path.open('x') as handle: json.dump(obj, handle, indent=2, sort_keys=True); handle.write('\n')
def frozen(base, digest, count):
    seal_row = row(base/'seal.json'); assert seal_row['sha256'] == digest
    seal = loads((base/'seal.json').read_text()); assert len(seal['members']) == count
    assert sha(canonical(seal['members'])) == seal['tree_sha256']
    for member in seal['members']: assert row(base/member['path'],base) == member
    assert {str(path.relative_to(base)) for path in base.rglob('*') if path.is_file()} == {member['path'] for member in seal['members']} | {'seal.json'}
    assert not any(path.is_symlink() for path in base.rglob('*'))
    return seal_row, seal

def main():
    assert not (D/'plan.json').exists() and not (D/'seal.json').exists()
    assert not (O/'build').exists() and not (D/'command').exists()
    original_row, original_seal = frozen(O,'c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9',173)
    prior_row, prior_seal = frozen(V,'76fda3e073db9bb7408275cf5d8eb494cf491e5a9cd0a894ba8cca35171127f8',16)
    assert row(V/'plan.json')['sha256'] == 'ac581da773865faf19b72eef8f2b12d3693b6e691ca910130f4e01f97e241c3d'
    plan = loads((V/'plan.json').read_text())
    plan['schema'] = 3
    plan['status'] = 'PREPARED_V3_FROZEN_AWAITING_ROOT_INTERNAL_COMPILER_RELEASE'
    plan['prepared_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    plan['prior_v2_packet'] = {'seal':prior_row,'plan':row(V/'plan.json'),'members':16,
        'tree_sha256':prior_seal['tree_sha256'],'all_existing_files_and_seal_immutable':True,
        'return_reason':'No compiler execution. Final acceptance needed an explicit finite signal cutoff and observation-before-receipt publication.'}
    plan['preaccess_frozen_seals'] = [row(P/name) for name in ['preaccess-seal.json','review-01-seal.json','review-02-seal.json']]
    plan['execution_build_ownership'] = 'Transient original build directory becomes execution-owned only after exact root release; absent prelaunch. Original/v2 sealed members remain immutable. All new command/receipt evidence belongs to v3.'
    plan['scripts'] = [row(D/name,D) for name in ['prepare.py','check.py','controls.py','diagnostics.py','run.py','launch.py','strict_json.py','publication.py','verify_and_seal.py']]
    plan['finite_publication'] = {
        'cutoff':'Set one-way publication_cutoff=True after compiler cleanup, required source/tool/output hashes and parsing, before snapshotting pre-cutoff pending handler observations.',
        'pre_cutoff':'Handler observations before the assignment are frozen and reject acceptance, even if observed after the last work checkpoint.',
        'post_cutoff':'Handler observations after assignment are outside the completed observation. They only record bounded in-memory classification and return; no promise persists every later signal.',
        'post_cutoff_actions':'Only finite evidence serialization/publication and handler restoration/return. No compiler, child, source/tool hashing, parse, product or cleanup work.',
        'ordering':'Publish closed complete diagnostic-observation.json before constructing/publishing final receipt.json. Failed observation publication can produce only a rejected receipt; failed receipt publication yields no final accepted receipt.',
        'synthetic_windows':['before cutoff','between flag assignment and snapshot via fake clock','during observation write','during receipt write'],
        'qualification':'Source/offline only. No actual compiler diagnostics, actual layout, price, backing, peak, funding, full ownership or GA authority.'}
    plan['narrow_corrections']['finite_publication'] = plan['finite_publication']
    plan['narrow_corrections']['unchanged'].append('all16 v2 sealed members and preaccess frozen reviews')
    plan['argv_sha256_canonical_JSON'] = sha(canonical(plan['argv']))
    plan['environment_sha256_canonical_JSON'] = sha(canonical(plan['environment']))
    patch = ''
    for name in ['check.py','controls.py','diagnostics.py','run.py','launch.py','strict_json.py']:
        patch += ''.join(difflib.unified_diff((V/name).read_text().splitlines(True),(D/name).read_text().splitlines(True),fromfile='v2/'+name,tofile='v3/'+name))
    patch += ''.join(difflib.unified_diff([],(D/'publication.py').read_text().splitlines(True),fromfile='/dev/null',tofile='v3/publication.py'))
    (D/'correction-delta.patch').write_text(patch)
    put(D/'plan.json',plan)
    put(D/'preparation-receipt.json',{'schema':3,
        'command':[str(Path(sys.executable).resolve()),'-B',str(D/'prepare.py')], 'python':sys.version,
        'plan_sha256':sha((D/'plan.json').read_bytes()), 'original_seal_sha256':original_row['sha256'],
        'prior_v2_seal_sha256':prior_row['sha256'], 'original173_and_v2_16_members_and_membership_verified_unchanged':True,
        'exact_argv_environment_source_trees_preserved':True, 'compiler_runtime_or_child_processes_started':0,
        'owned_build_directory_created':False, 'scope':'Separate source/offline v3 correction; original and v2 frozen packets immutable.'})
    print(json.dumps({'status':'prepared-v3-not-executed','plan_sha256':sha((D/'plan.json').read_bytes()),
        'argv_sha256':plan['argv_sha256_canonical_JSON'],'environment_sha256':plan['environment_sha256_canonical_JSON']}))

if __name__ == '__main__': main()
