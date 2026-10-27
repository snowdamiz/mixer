#!/usr/bin/env python3
"""Independent preaccess arithmetic/source expectations; never reads candidate."""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
AUTH = ROOT / 'verification/swift-guarded-snapshot-scope-authority-correction'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')

def check_seal(rel, expected):
    path = ROOT / rel
    assert digest(path) == expected
    seal = json.loads(path.read_text())
    for member in seal['members']:
        p = path.parent / member['path']
        assert p.stat().st_size == member['bytes']
        assert digest(p) == member['sha256']
    return {'path': rel, 'sha256': expected, 'members_checked': len(seal['members'])}

acceptance = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-owner-storage-host-acceptance.json'
assert digest(acceptance) == '6830f6cf2d889b3df551b0ad1e6e278d340dfa291abf153401f467548d2e2688'
accepted = json.loads(acceptance.read_text())
assert accepted['source_members'] == 144
assert accepted['accepted_recipe_bytes'] == {'common':78240,'selected':941467,'admitted':430175,'concrete_host_caller':81327}
seals = [check_seal(accepted[k]['path'], accepted[k]['sha256']) for k in ['correction_seal','independent_seal']]
manifest = json.loads((AUTH / 'source-manifest.json').read_text())
assert manifest['source_tree_sha256'] == accepted['source_tree_sha256']
for m in manifest['members']:
    p = AUTH / 'source/vm' / m['path']
    assert p.stat().st_size == m['bytes'] and digest(p) == m['sha256']

C,S,A,H = 78240,941467,430175,81327
MAX = (1 << 64) - 1
def add(a, b):
    return None if a is None or a > MAX-b else a+b
def floors(f0):
    common = add(f0,C)
    selected = add(common,S)
    unit = add(selected,H)
    return [common,selected,unit,add(selected,A),add(unit,A)]
increments = [C,C+S,C+S+H,C+S+A,C+S+H+A]
cases = sorted(set([0,1,2191,2192,300000,366896,400000,268435456,MAX] + [MAX-n+d for n in increments for d in [-1,0,1] if 0 <= MAX-n+d <= MAX]))
checks=[]
for f0 in cases:
    actual = floors(f0)
    oracle = [f0+n if f0+n <= MAX else None for n in increments]
    assert actual == oracle
    checks.append({'f0_synthetic':f0,'floors':actual})
assert increments == [78240,1019707,1101034,1449882,1531209]
assert S+A == 1371642 and S+H+A == 1452969
dump('preaccess-expectations.json', {
    'schema':1,'at':datetime.now(timezone.utc).isoformat(),
    'candidate_accessed':False,'root_release_arrived_before_candidate_access':True,
    'accepted_source_members':144,'accepted_source_tree_sha256':manifest['source_tree_sha256'],
    'accepted_recipe_bytes':{'C':C,'S':S,'A':A,'H':H},
    'source_f0_numeric_pending':'derive from actual unchanged 13-term source constant/compiler evidence, never substitute synthetic366896',
    'expected_floors':dict(zip(['common','selected-production','selected-unit','admitted-production','admitted-unit'],['F0+78240','F0+1019707','F0+1101034','F0+1449882','F0+1531209'])),
    'required_delta_scope':['control.rs const funding integration','cache/initial_profile_v1.rs phase constant replacement'],
    'runtime_controls':['common/selected functions return existing const Option only; no new args/locals/helper/fields','compile-time checked additions reject overflow','retain unchanged 13-term sole F0 without optional2192 credit','replace placeholder aggregates; never additionally charge them','WorkAuditPending before storage commit remains','pair/preflight/planning/shape/emission/commit order unchanged','SnapshotAccess::complete forwards storage,previous,wasi to unchanged finalizer','all conservative finalization and diagnostics charges retained'],
    'refused_claims':['pre-ingressH/harness ownership','A narrowing lifetime','healthy cleanup','writer admission/execution','production caller','descriptor integration','physical stack/RSS/private library bound','canonicalLinux attribution','native/device/simulator/emulator/UI/capture','GA'],
    'default_budget_literals_required_unchanged':[268435456,1000000000,300000,400000],
    'frozen_seals_verified':seals,
})
dump('preaccess-arithmetic-controls.json',{'schema':1,'kind':'fresh independent pure integer oracle; all F0 inputs synthetic','usize_bits':64,'cases':checks,'assertions':len(cases)*5+3,'pass':True,'no_candidate_or_runtime_access':True})
dump('preaccess-receipt.json',{'schema':1,'command':[sys.executable,str(Path(__file__).resolve())],'python_version':platform.python_version(),'platform':platform.platform(),'output':'frozen accepted144 + correction75 + independent9 verified; arithmetic controls pass','source_tree_sha256':manifest['source_tree_sha256'],'candidate_read':False,'compiler_builds':0,'product_runtime_executions':0,'native_or_capture_executions':0})
members=[]
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name != 'preaccess-seal.json':
        members.append({'path':p.name,'bytes':p.stat().st_size,'sha256':digest(p)})
dump('preaccess-seal.json',{'schema':1,'scope':'expectations frozen before candidate access','members':members,'member_count':len(members)})
print(json.dumps({'source_members':144,'frozen_seal_members':[x['members_checked'] for x in seals],'arithmetic_assertions':len(cases)*5+3,'candidate_read':False}))
