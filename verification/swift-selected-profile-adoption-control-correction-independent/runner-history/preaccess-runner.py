"""Bounded I1 delta review; candidate is unread until explicit root release.

All writes are in this new independent directory. Frozen original evidence and
the original independent review remain immutable.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL=ROOT/'verification/swift-selected-profile-adoption'
PRIOR=ROOT/'verification/swift-selected-profile-adoption-independent'
SELECTION=ROOT/'verification/swift-semantic-adapter-root-review/selected-adoption-control-correction-selection.json'
SELECTION_SHA='ddd67f46d96c49a300bc46aabc73568cd73ab8e8d06c68a4a5dd0164ae452e9b'
SOURCE=HERE/'source/vm'
CONTROL='src/experimental_swift_reactor/control_tests.rs'
PREFIX='experimental_swift_reactor::control::tests::'
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']


def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def ident(p):
    b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def manifest(folder):
    rows=[]
    for p in sorted(folder.rglob('*')):
        assert not p.is_symlink(),str(p)
        if p.is_file():
            b=p.read_bytes();rows.append({'path':str(p.relative_to(folder)),'bytes':len(b),'sha256':sha(b)})
    return {'schema':1,'member_count':len(rows),'members':rows,'tree_sha256':sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode())}


def selection():
    assert sha(SELECTION.read_bytes())==SELECTION_SHA
    return load(SELECTION)


def prepare():
    assert not SOURCE.exists()
    chosen=selection()
    assert sha((ORIGINAL/'seal.json').read_bytes())==chosen['original_candidate_seal']['sha256']
    assert sha((PRIOR/'seal.json').read_bytes())==chosen['independent_review_seal']['sha256']
    original_manifest=load(ORIGINAL/'source-manifest.json')
    for m in original_manifest['members']:
        b=(ORIGINAL/'source/vm'/m['path']).read_bytes()
        assert len(b)==m['bytes']and sha(b)==m['sha256']
        p=SOURCE/m['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    assert manifest(SOURCE)==original_manifest
    shutil.copytree(ORIGINAL/'host',HERE/'host')
    host=manifest(HERE/'host');assert host['member_count']==11
    control=(SOURCE/CONTROL).read_text()
    assert sha(control.encode())==chosen['permitted_source_delta']['before_sha256']
    roster=re.findall(r'#\[test\]\s*fn\s+(\w+)\s*\(',control)
    assert len(roster)==37 and len(set(roster))==37
    target='optional_observation_chain_is_reserved_before_runtime_work'
    assert target in roster
    compiler=load(PRIOR/'compiler-privacy/receipt.json')['compiler']
    assert ident(Path(compiler['path']))==compiler
    write(HERE/'preaccess-plan.json',{
        'schema':1,'at':datetime.now(timezone.utc).isoformat(),
        'status':'focused-I1-independent-preaccess-prepared-correction-candidate-unread',
        'selection_sha256':SELECTION_SHA,
        'original_candidate_seal_sha256':chosen['original_candidate_seal']['sha256'],
        'original_review_seal_sha256':chosen['independent_review_seal']['sha256'],
        'original_source_manifest':original_manifest,'unchanged_host_support_manifest':host,
        'compiler':compiler,'python':ident(Path(sys.executable).resolve()),'python_version':sys.version,
        'runner_at_preparation':ident(Path(__file__)),
        'only_permitted_source_path':CONTROL,
        'four_required_named_floors':chosen['named_floors'],
        'required_delta_check':'Compare exact bytes outside non_observation_shapes expression; inside expression permit comments/whitespace and only addition of exact four existing named constants, once each and in selected order; no numeric substitutions.',
        'assertion_roster':{
            'observed_chain':'size_of::<[Option<WasiUsage>; 6]>()',
            'historical_observations':'2 * size_of::<WasiUsage>()',
            'extra':'observed_chain.checked_sub(historical_observations).unwrap()',
            'historical_floor':'non_observation_shapes + historical_observations',
            'required_floor':'non_observation_shapes + observed_chain',
            'headroom':'[0, extra - 1, extra]',
            'refusal':'CombinedExhausted, attempted before+required_floor, actual limit, at_failure before+zero construction, after_cleanup empty',
            'success':'actual construction required_floor, combined equals budget, five live tickets, no allocation, actual cleanup empty',
            'complete_tail_and_original_other36_tests':'byte-identical outside selected expression; preserve all comments/assertions elsewhere'
        },
        'original_control_test_names':roster,
        'after_release_commands':['exact rustc --version --verbose','Debug --test complete144source compile with unchanged4feature flags','Debug full37control suite zero skips','optimized --test complete144source compile with unchanged4feature flags','optimized full37control suite zero skips'],
        'per_child_time_bound_seconds':55,'output_byte_limit':1048576,
        'evidence_composition':'Original266 producer and329 independent commands retain original source trees and one retained failure; only fresh corrected-source commands receive corrected digest. Production143 bytes and existing201-layout identities are unchanged-source evidence, not new replay.',
        'broad_privacy_loader_layout_replay_required':False,
        'candidate_files_read_or_executed':0,'root_release_required_before_review':True,
        'native_UI_capture_process_inventory_or_Git_used':False,
        'acceptance':False
    })
    print(json.dumps({'status':'preaccess-prepared','source_members':144,'host_members':11,'control_methods':37,'candidate_files_read_or_executed':0,'plan_sha256':sha((HERE/'preaccess-plan.json').read_bytes())},sort_keys=True))


def run(label,argv,env):
    folder=HERE/'commands'/f'{len(list((HERE/"commands").glob("*")))+1:03d}-{label}'
    folder.mkdir(parents=True)
    started=time.monotonic();killed=None
    with (folder/'stdout').open('wb')as out,(folder/'stderr').open('wb')as err:
        child=subprocess.Popen([str(x)for x in argv],cwd=ROOT,env=env,stdout=out,stderr=err)
        while True:
            try:code=child.wait(timeout=.05);break
            except subprocess.TimeoutExpired:
                if time.monotonic()-started>55:killed='time'
                if (folder/'stdout').stat().st_size+(folder/'stderr').stat().st_size>1048576:killed='output'
                if killed:child.kill();child.wait();code=124;break
    d={'label':label,'argv':[str(x)for x in argv],'cwd':str(ROOT),'environment':env,'exit_code':code,'expectation_met':code==0,'timeout_seconds':55,'output_byte_limit':1048576,'supervisor_killed_for':killed,'terminally_waited':True,'elapsed_seconds':time.monotonic()-started,'source_tree_sha256':manifest(SOURCE)['tree_sha256'],'runner':ident(Path(__file__)),'executed_artifact':ident(Path(argv[0])),'stdout':ident(folder/'stdout'),'stderr':ident(folder/'stderr')}
    write(folder/'receipt.json',d)
    print(label+': '+('pass'if code==0 else'FAIL'),flush=True)
    assert code==0,(label,(folder/'stderr').read_text()[-4000:])
    return (folder/'stdout').read_text()


def flags(compiler,mode):
    args=[compiler,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+('0'if mode=='debug'else'3'),'-C','overflow-checks=yes','-C','panic=unwind']
    for feature in FEATURES:args+=['--cfg','feature="'+feature+'"']
    return args


if __name__=='__main__':
    assert sys.argv[1:]==['prepare'],'Candidate review requires a separate explicit root release and final bound seal'
    prepare()
