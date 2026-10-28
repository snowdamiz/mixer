#!/usr/bin/env python3
"""Offline exact-commit review. Does not import or execute artifact code."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
SHA = 'cc350d3303ca71c5d57e87846f6a61304b658fa7'
OLD = '0b99469dfbeb06ac53ad0223bd070a35f2a6a700'
PREFIX = 'verification/swift-cache-state-ci/'
CURRENT = 'runs/ci-40740023152-1/'

def digest(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_bytes())
def put(name, value):
    with (BASE/name).open('x') as out: out.write(json.dumps(value,sort_keys=True,indent=2)+'\n')
def git(*args, input=None):
    result = subprocess.run(['git','--no-replace-objects','-c','gc.auto=0',*args],cwd=REPO,input=input,capture_output=True,timeout=15,check=True)
    return result.stdout
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

manifest = load(BASE/'zip-manifest.json')
inventory = {row['path']:row for row in manifest['entries']}
assert len(inventory) == 1385 and manifest['expanded_bytes'] == 83249523
assert manifest['all_entries_streamed_for_crc_size_sha256']
run = load(BASE/'run-metadata.json')
remote = load(BASE/'remote-metadata.json')
assert run['head_sha'] == SHA and run['status'] == 'completed' and run['conclusion'] == 'success'
jobs=remote['jobs']['jobs']
assert len(jobs)==6 and all(row['status']=='completed' and row['conclusion']=='success' for row in jobs)
job=next(row for row in jobs if row['id']==122998786883)
assert all(row['conclusion']=='success' for row in job['steps'])
artifact=next(row for row in remote['artifacts']['artifacts'] if row['id']==12839930376)
assert artifact['workflow_run']['head_sha']==SHA and artifact['digest']=='sha256:'+manifest['archive_sha256']
with zipfile.ZipFile(BASE/'artifact.zip') as archive:
    def data(path):
        value=archive.read(path)
        assert digest(value)==inventory[path]['sha256'] and len(value)==inventory[path]['bytes']
        return value
    pack=json.loads(data('pack/manifest.json'))
    assert pack['member_count']==86 and len(pack['members'])==86
    assert pack['tree_sha256']==digest(canonical(pack['members']))
    expected_pack={'pack/'+row['path'] for row in pack['members']}|{'pack/manifest.json'}
    assert {p for p in inventory if p.startswith('pack/')}==expected_pack
    for row in pack['members']:
        assert inventory['pack/'+row['path']]['sha256']==row['sha256'] and inventory['pack/'+row['path']]['bytes']==row['bytes']
    source_names=['check_cache_state.py','test_runner.py','README.md','pack/manifest.json']+[f'pack/{row["path"]}' for row in pack['members']]
    raw=git('cat-file','--batch',input=''.join(SHA+':'+PREFIX+path+'\n' for path in source_names).encode())
    offset=0; bindings={}
    for path in source_names:
        end=raw.index(b'\n',offset);oid,kind,count=raw[offset:end].decode().split();count=int(count)
        assert kind=='blob'
        body=raw[end+1:end+1+count];assert raw[end+1+count:end+2+count]==b'\n';offset=end+2+count
        assert body==data(path)
        bindings[PREFIX+path]={'bytes':count,'sha256':digest(body),'git_blob':oid,'artifact_matches_exact_commit':True}
    assert offset==len(raw)
    assert bindings[PREFIX+'check_cache_state.py']['sha256']=='162b34dcf64fee840c53ead9ff0ee9ab7241741ac9708fbed8ccb697caff2bf3'
    assert bindings[PREFIX+'test_runner.py']['sha256']=='ec3dc457dc7a86c610348522ad42f7b9e4486abcda12fee3f699b7f9ee1368e1'
    current_source=data('check_cache_state.py').decode()
    old_source=git('cat-file','blob',OLD+':'+PREFIX+'check_cache_state.py').decode()
    def stop(source):
        parsed=ast.parse(source)
        cls=next(n for n in parsed.body if isinstance(n,ast.ClassDef) and n.name=='Commands')
        node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='stop')
        return ast.get_source_segment(source,node)
    assert stop(current_source)==stop(old_source)
    names=['ACTIVE_SECONDS','CLEANUP_SECONDS','CHILD_SECONDS','OUTPUT_CAP','APPEND','FLAGS']
    def constants(source):
        parsed=ast.parse(source)
        return {t.id:ast.dump(n.value) for n in parsed.body if isinstance(n,ast.Assign) for t in n.targets if isinstance(t,ast.Name) and t.id in names}
    assert constants(current_source)==constants(old_source)
    runner=data('logs/runner-controls.stderr').decode()
    controls=[line for line in runner.splitlines() if line.startswith('test_')]
    assert len(controls)==32 and all(line.endswith(' ... ok') for line in controls)
    assert 'Ran 32 tests in 2.389s' in runner and runner.rstrip().endswith('OK')
    descendant=json.loads(data('logs/descendant-control/control.json'))
    assert not descendant['custody_hold'] and descendant['exception']['type']=='RuntimeError'
    row=descendant['receipt']['commands'][0]
    assert row['timed_out'] and row['child_returned'] and row['owned_group_gone'] and row['owned_group_killed']
    assert row['exit']==-9 and not row['custody_hold'] and not row['errors']
    for output in descendant['outputs']:
        raw_output=data('logs/descendant-control/'+output['path'])
        assert len(raw_output)==output['bytes'] and digest(raw_output)==output['sha256']
    actual=json.loads(data(CURRENT+'receipt.json'))
    assert actual['source_revision']==actual['source_revision_after']==SHA
    tree=git('rev-parse',SHA+'^{tree}').decode().strip()
    assert actual['source_tree']==actual['source_tree_after']==tree
    assert actual['status']=='passed-host-fixture-check' and not actual['errors']
    assert actual['runner']['sha256']==bindings[PREFIX+'check_cache_state.py']['sha256']
    assert actual['pack_manifest_sha256']==digest(data('pack/manifest.json')) and actual['pack_tree_sha256']==pack['tree_sha256']
    assert all(row['passed'] for row in actual['postflight'].values())
    assert actual['active_checks_completed'] and actual['active_elapsed_seconds']<actual['active_deadline_seconds']==600
    assert actual['cleanup_elapsed_seconds']<actual['cleanup_allowance_seconds']==60
    commands=actual['commands'];assert len(commands)==len({r['name'] for r in commands})==103
    command_bindings=[]
    for command in commands:
        prefix=CURRENT+'commands/'+command['name']
        assert json.loads(data(prefix+'.json'))==command
        for suffix in ['stdout','stderr']:
            assert inventory[prefix+'.'+suffix]['sha256']==command[suffix+'_sha256']
        assert command['child_returned'] and command['owned_group_gone'] and not command['custody_hold']
        assert not command['timed_out'] and not command['output_capped'] and not command['errors']
        command_bindings.append({'name':command['name'],'exit':command['exit'],'stdout_sha256':command['stdout_sha256'],'stderr_sha256':command['stderr_sha256']})
    method_checks={}
    expected_nonzero=set()
    for mode,value in actual['modes'].items():
        assert mode in {'debug','optimized'}
        for api in value['api']:
            assert (api['compile_exit']==0)==api['expected_success']
            if not api['expected_success']:expected_nonzero.add('api-'+api['name']+'-'+mode)
        assert len(value['api'])==25 and sum(not r['expected_success'] for r in value['api'])==23
        for family,count in [('controls',94),('host',84),('independent',98),('producer',108)]:
            result=value['methods'][family];assert result['count']==len(result['names'])==len(set(result['names']))==count
            assert result['complete_disjoint_coverage']
            selected_commands=[c for c in commands if c['name'].startswith(family+'-'+mode+'-') and not c['name'].endswith(('-compile','-list'))]
            observed=[]
            for command in selected_commands:
                stdout=data(CURRENT+'commands/'+command['name']+'.stdout').decode()
                for line in stdout.splitlines():
                    match=re.fullmatch(r'test (.+) \.\.\. ok',line)
                    if match:observed.append(match.group(1))
                assert 'test result: ok.' in stdout
            assert sorted(observed)==sorted(result['names']) and len(observed)==len(set(observed))
            method_checks[family+'-'+mode]={'passed_methods':count,'complete_disjoint_actual_output_coverage':True,'commands':[c['name'] for c in selected_commands]}
        assert len(value['controls_File_cases'])==len(value['host_File_cases'])==31
        assert len(value['controls_layouts'])==len(value['host_layouts'])==23
    assert {c['name'] for c in commands if c['exit']!=0}==expected_nonzero
    assert all(c['exit']==1 for c in commands if c['name'] in expected_nonzero)
    assert actual['cleanup']['removed'] and actual['cleanup']['groups_returned'] and actual['cleanup']['files_hashed_before_removal']==916
    assert not actual['cleanup']['other_project_or_native_discovery']
    assert actual['original_full_Debug_timeout_remains_failed']
    for flag in ['fullReplayAccepted','semanticMetricsValid','storedPrefixValidated','performance_equivalence_claimed','GA_qualified','model_imported_or_evaluated']:assert actual[flag] is False
    historical=json.loads(data('runs/host-resource-ci-repair-root-1/receipt.json'))
    assert historical['source_revision']=='c4d04e56d0175f4c036c878db5ccb7bd9c7b30f0'
    receipt_paths=sorted(p for p in inventory if p.endswith('/receipt.json'))
    assert receipt_paths==[CURRENT+'receipt.json','runs/host-resource-ci-repair-root-1/receipt.json']
workflow=git('cat-file','blob',SHA+':.github/workflows/verify.yml')
with (BASE/'workflow-at-run.yml').open('xb') as out:out.write(workflow)
assert SHA in (BASE/'job.log').read_text()
put('source-bindings.json',{'source_revision':SHA,'source_tree':tree,'sources':bindings,'pack_members':86,'pack_tree_sha256':pack['tree_sha256'],'workflow_sha256':digest(workflow),'Commands_stop_unchanged_from_failed_commit':True,'active_cleanup_child_output_limits_append_and_flags_unchanged':True,'basis':'Exact byte comparison plus static selected AST node comparison; no runner import or execution'})
put('runtime-evidence.json',{'runner_controls':{'tests':32,'passed':32,'errors':0,'seconds':2.389,'raw_methods':controls},'descendant_control':descendant,'actual_fixture':{'commands':103,'expected_negative_api_commands':46,'methods':method_checks,'per_mode_actual_File_cases_each_host_and_controls':31,'per_mode_layouts_each_host_and_controls':23,'commands_output_hash_bindings':command_bindings,'cleanup':actual['cleanup'],'elapsed_seconds':actual['elapsed_seconds'],'active_elapsed_seconds':actual['active_elapsed_seconds'],'cleanup_elapsed_seconds':actual['cleanup_elapsed_seconds'],'rustc':actual['rustc']},'historical':{'path':'runs/host-resource-ci-repair-root-1/receipt.json','source_revision':historical['source_revision'],'started_utc':historical['started_utc'],'accepted_as_current':False}})
put('review.json',{'schema':1,'decision':'accepted-exact-commit-current-runner-controls-and-finite-host-fixture','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':SHA,'source_tree':tree,'run_id':40740023152,'job_id':122998786883,'artifact_id':12839930376,'artifact_sha256':manifest['archive_sha256'],'runner_controls_passed':32,'actual_fixture_commands':103,'Commands_stop_unchanged':True,'historical_receipt_accepted_as_current':False,'original_flaky_primary_failure_cause_resolved':False,'original_full_Debug_timeout_remains_failed':True,'semanticMetricsValid':False,'storedPrefixValidated':False,'fullReplayAccepted':False,'GA_qualified':False,'cleanup':{'current_CI_descendant_positive_group_disappearance':True,'current_fixture_owned_groups_returned':True,'current_fixture_scratch_removed':True,'local_custody_hold_cleared':False,'reviewer_started_native_or_product_processes':False},'limits':['Current passing remote observations do not identify or resolve the original unknown primary cleanup failure.','Exact finite host fixture only; original full Debug timeout, semantic/replay/performance/native/release/GA acceptance remain unqualified.','Historical copied fixture receipt is explicitly excluded from current acceptance.','No tests, compilers, runtime, UI, native, Docker, PostgreSQL, guest, phone, stopped Android v5, process inventory, CI retry or dispatch executed by reviewer. All holds preserved.'],'review_python':sys.version,'git_version':git('--version').decode().strip()})
print(json.dumps({'decision':'accepted-exact-commit-current-runner-controls-and-finite-host-fixture','runner_controls':32,'actual_fixture_commands':103,'source_revision':SHA,'historical_excluded':True,'original_primary_cause_resolved':False},sort_keys=True))
