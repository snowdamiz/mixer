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


def frozen(path,expected):
    assert sha((path/'seal.json').read_bytes())==expected
    d=load(path/'seal.json');actual=set()
    for p in path.rglob('*'):
        assert not p.is_symlink(),str(p)
        if p.is_file():actual.add(str(p.relative_to(path)))
    assert actual=={m['path']for m in d['members']}|{'seal.json'}
    for m in d['members']:
        b=(path/m['path']).read_bytes();assert len(b)==m['bytes']and sha(b)==m['sha256'],m['path']
    return {'seal_sha256':expected,'members':len(d['members']),'member_bytes':sum(m['bytes']for m in d['members']),'all_bytes_and_exact_closed_file_set_verified':True}


def release(expected):
    assert expected=='db09f708b4ee7db5a9e8a9c0bf70dd17b4b96d46cdd887b0f70385a8709d9616'
    assert not (HERE/'release-review.json').exists()
    assert sha((HERE/'preaccess-plan.json').read_bytes())=='549e9b7d3bd7cdbd4d9c6e2775d8ecb34c573b21a2780a847995a8132867e068'
    chosen=selection();packet=ROOT/'verification/swift-selected-profile-adoption-control-correction'
    custody=frozen(packet,expected)
    assert custody['members']==223 and custody['member_bytes']==21846054
    source=manifest(packet/'source/vm');assert source==load(packet/'source-manifest.json')
    assert source['tree_sha256']=='9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb'
    before=load(HERE/'preaccess-plan.json')['original_source_manifest']
    bm={m['path']:m for m in before['members']}
    changed=[m['path']for m in source['members']if bm[m['path']]!=m]
    assert changed==[CONTROL]
    old=(ORIGINAL/'source/vm'/CONTROL).read_text();new=(packet/'source/vm'/CONTROL).read_text()
    assert sha(old.encode())==chosen['permitted_source_delta']['before_sha256']
    assert len(new.encode())==73334 and sha(new.encode())=='e3192686fbd539b943c39c81402e05127036ae82dd60df4580cd558e88dd7095'
    start='    let non_observation_shapes = '
    end='    let historical_floor = '
    oi=old.index(start);oj=old.index(end,oi);ni=new.index(start);nj=new.index(end,ni)
    assert old[:oi]==new[:ni]and old[oj:]==new[nj:]
    def compact(expression):return re.sub(r'\s+','',re.sub(r'//[^\n]*','',expression))
    old_expression=compact(old[oi:oj]);new_expression=compact(new[ni:nj])
    terms=chosen['named_floors']
    assert new_expression==old_expression.removesuffix(';')+''.join('+'+term for term in terms)+';'
    assert all(new_expression.count(term)==1 for term in terms)
    roster=re.findall(r'#\[test\]\s*fn\s+(\w+)\s*\(',new)
    assert roster==load(HERE/'preaccess-plan.json')['original_control_test_names']
    assert (SOURCE/CONTROL).read_bytes()in [old.encode(),new.encode()]
    (SOURCE/CONTROL).write_bytes(new.encode());assert manifest(SOURCE)==source
    assert manifest(packet/'host')==load(packet/'host-support-manifest.json')==manifest(HERE/'host')
    attribution=load(packet/'historical-command-attribution.json');counts={};failed=[]
    for group,number in [('candidate',266),('independent',329)]:
        entries=attribution[group]['entries'];assert len(entries)==number==attribution[group]['commands']
        for row in entries:
            for key in ['receipt','stdout','stderr']:
                assert ident(Path(row[key]['path']))==row[key]
            original=load(Path(row['receipt']['path']))
            assert row['original_source_tree_sha256']==original['source_tree_sha256']
            assert row['original_source_tree_sha256']!=source['tree_sha256']
            assert row['exit_code']==original['exit_code']and row['expectation_met']==original['expectation_met']
            assert row['rerun_for_corrected_tree']is False
            if not row['expectation_met']:failed.append({'group':group,'label':row['label'],'receipt':row['receipt']})
        counts[group]=number
    assert len(failed)==1 and failed[0]['label']=='debug-suite-experimental_swift_reactor::control::tests::'
    layout=load(packet/'layout-custody.json')
    for m in layout['measurements']:
        assert m['new_measurement']is False and m['rows']==201
        assert ident(Path(m['original']['path']))==m['original']
        assert ident(Path(m['retained']['path']))==m['retained']
        assert m['source_tree_sha256']==before['tree_sha256']
    current=[]
    for p in sorted((packet/'commands').glob('*/receipt.json')):
        d=load(p);assert d['terminally_waited']and d['exit_code']==0 and d['supervisor_killed_for']is None
        assert d['source_tree_sha256']==source['tree_sha256']
        for k in ['stdout','stderr']:assert ident(Path(d[k]['path']))==d[k]
        current.append({'receipt':ident(p),'label':d['label'],'source_tree_sha256':d['source_tree_sha256']})
    assert len(current)==9
    write(HERE/'corrected-source-manifest.json',source)
    write(HERE/'release-review.json',{
        'schema':1,'at':datetime.now(timezone.utc).isoformat(),'candidate':str(packet),'custody':custody,
        'selection_sha256':SELECTION_SHA,'preaccess_plan_sha256':'549e9b7d3bd7cdbd4d9c6e2775d8ecb34c573b21a2780a847995a8132867e068',
        'corrected_source_tree_sha256':source['tree_sha256'],'source_members':144,'only_changed_source':CONTROL,
        'unchanged_source_members':143,'unchanged_host_support_members':11,
        'all_bytes_outside_selected_expression_unchanged':True,
        'only_four_named_floors_once_each_plus_comment_and_whitespace':True,
        'observation_historical_headroom_refusal_and_success_assertions_byte_unchanged':True,
        'all37_original_control_methods_preserved':True,
        'historical_identity_attribution_verified_commands':counts,'historical_failure_preserved':failed,
        'historical_layout_sets_verified':4,'layout_records_each':201,'historical_layouts_remeasured_here':False,
        'producer_new_corrected_source_commands_verified':current,
        'producer_parser_failure':'retained runner failure followed passing Debug child; no child rerun/relabel; checked source/output identity only',
        'candidate_runner_or_finalizer_executed':False,'paused_native_UI_capture_process_inventory_or_Git_used':False,
        'acceptance':False
    })
    print('Released exact one-file delta verified; original assertions and595historical command identities preserved',flush=True)


def env():
    work=HERE/'owned-work';work.mkdir(exist_ok=True)
    return {'PATH':'/usr/bin:/bin','TMPDIR':str(work),'CARGO_MANIFEST_DIR':str(SOURCE)}


def compile_mode(mode):
    assert mode in ['debug','optimized']
    released=load(HERE/'release-review.json')
    assert manifest(SOURCE)==load(HERE/'corrected-source-manifest.json')
    compiler=load(HERE/'preaccess-plan.json')['compiler'];assert ident(Path(compiler['path']))==compiler
    if not (HERE/'compiler-version.json').exists():
        output=run('rustc-version',[compiler['path'],'--version','--verbose'],env())
        write(HERE/'compiler-version.json',{'compiler':compiler,'stdout':output})
    binary=HERE/'owned-work'/('unit-'+mode)
    run('compile-'+mode,flags(compiler['path'],mode)+['--test',SOURCE/'src/lib.rs','-o',binary],env())
    write(HERE/('compiled-'+mode+'.json'),{'artifact':ident(binary),'source_tree_sha256':released['corrected_source_tree_sha256'],'runner':ident(Path(__file__))})


def suite_mode(mode):
    compiler=load(HERE/('compiled-'+mode+'.json'));binary=Path(compiler['artifact']['path'])
    assert ident(binary)==compiler['artifact']
    out=run('full-control-'+mode,[binary,PREFIX,'--nocapture','--test-threads=1'],env())
    names=re.findall(r'(?m)^test ('+re.escape(PREFIX)+r'\w+) \.\.\.',out)
    expected=[PREFIX+x for x in load(HERE/'preaccess-plan.json')['original_control_test_names']]
    assert sorted(names)==sorted(expected)and len(names)==37
    assert 'test result: ok. 37 passed; 0 failed; 0 ignored;'in out
    observation=re.search(r'observation chain target=.*?old_floor=(\d+) new_floor=(\d+) added=(\d+)',out)
    assert observation and list(map(int,observation.groups()))==[366432,366896,464]
    write(HERE/('control-result-'+mode+'.json'),{'mode':mode,'source_tree_sha256':compiler['source_tree_sha256'],'methods':names,'passed':37,'failed':0,'ignored':0,'observation_old_floor':366432,'observation_required_floor':366896,'observation_increment':464,'headroom_cases':[0,463,464],'all_original_headroom_refusal_success_assertions_executed':True})


def finalize():
    assert not (HERE/'seal.json').exists()
    released=load(HERE/'release-review.json')
    frozen(Path(released['candidate']),released['custody']['seal_sha256'])
    chosen=selection()
    assert sha((ORIGINAL/'seal.json').read_bytes())==chosen['original_candidate_seal']['sha256']
    assert sha((PRIOR/'seal.json').read_bytes())==chosen['independent_review_seal']['sha256']
    assert sha((HERE/'preaccess-plan.json').read_bytes())=='549e9b7d3bd7cdbd4d9c6e2775d8ecb34c573b21a2780a847995a8132867e068'
    assert manifest(SOURCE)==load(HERE/'corrected-source-manifest.json')
    commands=[]
    for p in sorted((HERE/'commands').glob('*/receipt.json')):
        d=load(p);assert d['expectation_met']and d['terminally_waited']and d['supervisor_killed_for']is None
        assert d['source_tree_sha256']==released['corrected_source_tree_sha256']
        for key in ['stdout','stderr']:assert ident(Path(d[key]['path']))==d[key]
        commands.append(ident(p))
    assert len(commands)==5
    results=[load(HERE/('control-result-'+mode+'.json'))for mode in ['debug','optimized']]
    assert all(d['passed']==37 and d['failed']==0 and d['ignored']==0 for d in results)
    artifacts=[ident(p)for p in sorted((HERE/'owned-work').rglob('*'))if p.is_file()]
    write(HERE/'artifacts-before-owned-removal.json',artifacts)
    shutil.rmtree(HERE/'owned-work')
    cleanup={'direct_owned_children_terminally_waited':5,'owned_scratch_removed':True,'original_candidate_and_original_independent_review_and_correction_candidate_mutated':False,'native_UI_capture_process_inventory_or_Git_used':False,'File_drop_or_process_exit_is_close_success':False,'other_projects_touched':False}
    write(HERE/'cleanup.json',cleanup)
    write(HERE/'review-result.json',{
        'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'independent-I1-test-only-delta-review-pass',
        'candidate':released['custody'],'corrected_source_tree_sha256':released['corrected_source_tree_sha256'],
        'source_members':144,'unchanged_production_and_other_source_members':143,'unchanged_host_support_members':11,
        'exact_selected_delta_and_all_original_assertions_preserved':True,'I1_closed_for_corrected_source':True,
        'fresh_commands':5,'fresh_passed_commands':5,'fresh_control_tests':74,'control_results':results,'command_receipts':commands,
        'historical_266_producer_and329_independent_receipt_source_output_identities_verified':True,
        'historical_I1_failure_preserved_without_relabel':True,'existing_four201_layout_sets_preserved_with_original_source_attribution':True,
        'no_new_layout_or_performance_measurements':True,'actionable_findings':[],
        'retained_independent_tooling_failure':{'path':'preparation/release-first-parser-error.json','kind':'receipt-schema KeyError before any compiler/test child','test_children_replayed_for_parser_repair':False},
        'recommendation':'Root may accept this narrow I1 test-expectation correction and compose exact unchanged-source prior host evidence. Original frozen candidate/review/failure remain historical; no whole-suite or broader qualification claim.',
        'scope':'Exact4existingnamedfloors test-only arithmetic/comment correction and full37control methods in Debug/optimized on macOS Rust host',
        'cleanup':cleanup,
        'limits':['Other428unit methods not newly replayed for this test-only correction; prior path-bound evidence remains separately attributed','Original nested Cargo wrapper,raw APFS path/nonUTF8 argv0 and previous scope limitations remain','Native/device/simulator/emulator/UI/capture/process inventory paused-unused','No loader operational storage,File close-success,authenticated package or hostile launcher guarantee','No exporter/context/canonical integration,FieldLog immutable package release,OTA/store/customer/operations or GA acceptance'],
        'canonical_or_native_or_operational_or_GA_accepted':False
    })
    rows=[]
    for p in sorted(HERE.rglob('*')):
        assert not p.is_symlink(),str(p)
        if p.is_file():
            b=p.read_bytes();rows.append({'path':str(p.relative_to(HERE)),'bytes':len(b),'sha256':sha(b)})
    write(HERE/'seal.json',{'schema':1,'scope':'Independent focused I1 selected-adoption control-test correction review','member_count':len(rows),'member_bytes':sum(m['bytes']for m in rows),'members':rows})
    print(json.dumps({'status':'I1-delta-review-pass','commands':5,'passed_control_tests':74,'members':len(rows),'member_bytes':sum(m['bytes']for m in rows),'seal_sha256':sha((HERE/'seal.json').read_bytes())},sort_keys=True))


if __name__=='__main__':
    args=sys.argv[1:]
    if args==['prepare']:prepare()
    elif len(args)==2 and args[0]=='release':release(args[1])
    elif len(args)==2 and args[0]=='compile':compile_mode(args[1])
    elif len(args)==2 and args[0]=='suite':suite_mode(args[1])
    elif args==['finalize']:finalize()
    else:raise AssertionError(args)
