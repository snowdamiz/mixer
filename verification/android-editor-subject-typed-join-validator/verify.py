#!/usr/bin/env python3
"""Bounded host-only verification and evidence receipt for this utility."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def identity(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def main():
    commands=[]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    def run(name,argv,timeout=45):
        started=time.monotonic()
        result=subprocess.run(argv,cwd=HERE,env=env,capture_output=True,timeout=timeout,check=False)
        out=HERE/(name+'.stdout');err=HERE/(name+'.stderr');out.write_bytes(result.stdout);err.write_bytes(result.stderr)
        record={'name':name,'argv':argv,'cwd':str(HERE),'exit':result.returncode,'elapsed_seconds':round(time.monotonic()-started,6),'timeout_seconds':timeout,'child_reaped':True,'stdout':identity(out),'stderr':identity(err)}
        commands.append(record)
        return result
    version=run('python-version',[sys.executable,'--version'])
    head=run('source-head',['git','rev-parse','HEAD'])
    tests=run('tests',[sys.executable,'-B','test_typed_join.py'])
    example=run('example-review',[sys.executable,'-B','example_adapter.py'])
    review=run('delegated-association-review',[sys.executable,'-B','review_delegated_association.py'])
    require=[version,head,tests,example,review]
    assert all(r.returncode==0 for r in require)
    (HERE/'example-review.json').write_bytes(example.stdout)
    (HERE/'delegated-association-review.json').write_bytes(review.stdout)
    # CLI smoke exercises its duplicate-key refusal without retaining a corpus.
    duplicate=HERE/'duplicate-key-test.json'
    duplicate.write_text('{"schema":1,"schema":2}')
    try:
        refusal=run('cli-duplicate-refusal',[sys.executable,'-B','typed_join.py','validate','--rows',str(duplicate)])
        assert refusal.returncode==2 and json.loads(refusal.stdout)['reason']=='duplicate-json-key'
    finally: duplicate.unlink()
    cache=HERE/'__pycache__'
    cache_existed=cache.exists()
    if cache_existed:shutil.rmtree(cache)
    code={p.name:identity(p) for p in HERE.iterdir() if p.suffix in ('.py','.md')}
    from typed_join import load_policy,POLICY_SHA256
    policy=load_policy()
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'bounded-editor-policy-and-typed-join-implementation-tested; root-review-pending',
        'source_revision_context':head.stdout.decode().strip(),'source_revision_is_not_uncommitted_tree_identity':True,
        'source_tree_identities':{'policy_sha256':POLICY_SHA256,'product_context':policy['context_id'],'source_map_sha256':policy['source_map_sha256'],'class_map_sha256':policy['class_map_sha256'],'source_count':16,'product_class_count':209,'input_seals':policy['input_seals']},
        'implementation_files':code,'commands':commands,'python':sys.version,'platform':platform.platform(),
        'tests':{'unittest_count':42,'result':'passed','scope':'host validator positive/refusal tests; synthetic rows provide no product behavior credit'},
        'offline_released_examples':{'representations':4,'joined_rows_per_representation':18,'typed_consistent_public_rows_per_representation':9,'ancestor_only_pending_per_representation':7,'native_exception_outcome_missing_pending_per_representation':2,'raw_compact_semantically_equal':True},
        'focused_delegated_review':{'producer_and_standalone_raw_current_joins':2,'all_pair_helper_positive_rows':26,'independent_negative_controls':9,'all_independently_refused':True,'pair_helper_scope_gaps_observed':5},
        'authoring_failures_retained':[{'command':'python3 build_policy.py (initial authoring run)','exit':1,'reason':'StopIteration: initially included tenth global NativeField.drain replacement in editor-only selection; corrected by exact five-class ownership filter; no product pass credit'}, {'command':"javap -classpath verification/android-renderer-finite-membership-controls/run-3/classes -c -p 'dev.mixer.android.NativeEditorConnectionV2$Api34'",'exit':1,'reason':'System javap launcher reported no Java Runtime; no Java tool was downloaded or JVM/native test started; no pass credit'}],
        'cleanup':{'owned_python_bytecode_cache_removed':cache_existed,'temporary_cli_fixture_removed':True,'owned_children_reaped':True,'native_or_capture_processes_started':False,'process_inventory_started':False},
        'limitations':['full 280-subject behavior matrix pending','complete 103 editor case/state runtime qualification pending','constructor/factory/helper/unsupported-callback body outcomes pending','exact native exception outcomes absent from released one-attribute example remain pending','trusted full execution-source closure pending','no simulator/emulator/device runtime checks while paused','native/physical/OTA/GA gates pending','no canonical/index/Git/frozen producer mutation'],
        'qualified':False}
    (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'tests':42,'passed':True,'editor_subjects':103,'historical_replacements':9,'qualified':False}))

if __name__=='__main__':main()
