"""Validate root direction; freeze a closed, finite packet. No external writes."""
import hashlib,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent.parent
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,indent=2)+'\n')
direction=ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-export-admission-proposal-direction.json'
expected='26dd7ba06c216978b94c1aed9378a9065a91d6c5ec78d3239d3bf0d706c68dc7'
assert digest(direction)==expected
dump(HERE/'proposal-direction-custody.json',dict(path=str(direction.relative_to(ROOT)),bytes=direction.stat().st_size,sha256=expected,
    authority='Root-selected recommendation direction for review only; no implementation, budget or final floor accepted'))
for p in HERE.rglob('*'):
    assert not p.is_symlink()
    assert not (p.parent==HERE and p.is_dir() and (p.name.startswith('bounded-compile-') or p.name.startswith('unit-layout-') or p.name.startswith('profile-layout-')))
assert json.loads((HERE/'cleanup.json').read_text())['scratch_removed']
assert json.loads((HERE/'unit-layout-cleanup.json').read_text())['scratch_removed']
assert json.loads((HERE/'profile-layout-cleanup.json').read_text())['scratch_removed']
model=json.loads((HERE/'expanded-controls-result.json').read_text()); assert len(model['groups'])==9
assert model['controls_sha256']==digest(HERE/'controls.py')
assert json.loads((HERE/'profile-layout-result.json').read_text())['runner_sha256']==digest(HERE/'run_profile_layout.py')
dump(HERE/'release.json',dict(schema=1,status='frozen recommended design for independent review only',
    scope='No full encoder/wrapper/admission profile implemented or accepted',
    accepted_source_tree='9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb',
    proposal_direction_sha256=expected,model_groups=9,
    original_grants_unchanged=True,positive_host_grant_selected=False,
    common_core_candidate_bytes=8536,selected_shell_candidate_bytes=29256,
    owning_scope_candidate_unit_bytes=5984,owning_scope_candidate_production_bytes=5936,
    final_source_place_floor_measured=False,all_compiler_children_reaped=True,scratch_removed=True,
    native_runtime_ui_capture_process_inventory_or_git_used=False,
    pending=['independent review and root contract selection','actual profile/admission/encoder/wrapper implementation and exact source-place closure',
        'fresh full floors and separately selected host positive grant','actual eight-outcome/error/cleanup/File writer controls',
        'operational acquisition/File close/custody','native paused','FieldLog published immutable separate-repo package','GA']))
members=[]
for p in sorted(HERE.rglob('*')):
    if p.is_file() and p.name!='seal.json': members.append(dict(path=str(p.relative_to(HERE)),bytes=p.stat().st_size,sha256=digest(p)))
tree=hashlib.sha256()
for m in members: tree.update((m['path']+'\0'+str(m['bytes'])+'\0'+m['sha256']+'\n').encode())
dump(HERE/'seal.json',dict(schema=1,member_count=len(members),bytes=sum(m['bytes'] for m in members),members=members,tree_sha256=tree.hexdigest(),
    scope='Frozen bounded admission design/prototype review packet only'))
print(json.dumps(dict(seal_sha256=digest(HERE/'seal.json'),members=len(members),bytes=sum(m['bytes'] for m in members)),indent=2))
