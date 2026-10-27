#!/usr/bin/env python3
"""Independent frozen-only replay. Never calls the producer runner or external packets."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
ROOT=D.parent.parent
PACKET=ROOT/'verification/android-field-preservation-replacement-finite-controls'
SEAL='309dc0fe8b70849fd95df09b673577cbbb74dbeeac02c4aee9b01870306a9626'
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
JDK=ROOT/'verification/android-editor-membership-compiled-boundary-qualification/state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'

def identity(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def verify_packet():
    assert identity(PACKET/'seal.json')['sha256']==SEAL
    seal=json.loads((PACKET/'seal.json').read_bytes())
    assert seal['member_count']==146 and seal['member_bytes']==1408355
    allowed={row['path'] for row in seal['members']}
    assert len(allowed)==146
    present=set()
    for path in PACKET.rglob('*'):
        assert not path.is_symlink(),str(path)
        if path.is_file():present.add(str(path.relative_to(PACKET)))
    assert present==allowed|{'seal.json'}
    for row in seal['members']:
        path=Path(row['path']);assert not path.is_absolute() and '..' not in path.parts
        assert identity(PACKET/path)=={key:row[key] for key in ('bytes','sha256')},str(path)
    assert sum(row['bytes'] for row in seal['members'])==1408355
    return {'seal':identity(PACKET/'seal.json'),'members':146,'bytes':1408355,'exact_file_roster':True,'symlinks':False}

def main():
    run=D/sys.argv[1];run.mkdir()
    scratch=run/'scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
    commands=[];env=dict(os.environ)
    for name in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(name,None)
    def command(name,argv):
        out=run/(name+'.stdout');err=run/(name+'.stderr');started=time.monotonic()
        with out.open('wb') as stdout,err.open('wb') as stderr:
            child=subprocess.Popen([str(x) for x in argv],cwd=D,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            timeout=False
            try:child.wait(timeout=45)
            except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        row={'name':name,'argv':[str(x) for x in argv],'cwd':str(D),'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed_seconds':time.monotonic()-started,'stdout':{'path':out.name,**identity(out)},'stderr':{'path':err.name,**identity(err)}}
        commands.append(row);save(run/'commands.json',commands)
        print(name,child.returncode,flush=True)
        assert child.returncode==0 and not timeout,row
    try:
        shutil.copyfile(Path(__file__),run/'replay.py');shutil.copyfile(D/'IndependentFieldControls.java',run/'IndependentFieldControls.java')
        custody=verify_packet();save(run/'custody-before.json',custody)
        source_map=json.loads((PACKET/'inputs/selected-product-source-map.json').read_bytes());class_map=json.loads((PACKET/'inputs/selected-product-class-map.json').read_bytes())
        assert len(source_map)==16 and len(class_map)==209
        roster=json.loads((PACKET/'inputs/source-roster.json').read_bytes())
        assert collections.Counter(row['role'] for row in roster)=={'exact-product16':16,'exact-B87':79,'selected-v4-derivative':8,'released-selected6-exact-original-fixture':1,'released-descriptor':1}
        for row in roster:assert identity(PACKET/row['path'])=={key:row[key] for key in ('bytes','sha256')}
        assert {Path(row['path']).name:identity(PACKET/row['path']) for row in roster if row['role']=='exact-product16'}==source_map
        provenance=json.loads((PACKET/'run-2/provenance.json').read_bytes())
        tools={name:identity(JDK/name) for name in provenance['tools']};assert tools==provenance['tools']
        contracts=json.loads((PACKET/'inputs/exact-four-subject-contracts.json').read_bytes())
        assert contracts['source_context']==CONTEXT and len(contracts['subjects'])==4
        save(run/'provenance.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'input_packet':str(PACKET.relative_to(ROOT)),'custody':custody,'source_context':CONTEXT,'source_revision_context':provenance['source_revision_context'],'read_boundary':'only named frozen packet members, AGENTS, and leased JDK; no producer runner execution or external packet reads','runner':identity(Path(__file__)),'independent_control':identity(D/'IndependentFieldControls.java'),'producer_control':identity(PACKET/'FieldFiniteControls.java'),'python':sys.version,'platform':platform.platform(),'tools':tools,'launch':[sys.executable,'-B',str(Path(__file__)),sys.argv[1]],'javac_debug':'default; no explicit -g or -g:none'})
        command('java-version',[JDK/'bin/java','-version']);command('javac-version',[JDK/'bin/javac','-version'])
        sources=[PACKET/row['path'] for row in roster if row['path'].endswith('.java')]+[PACKET/'FieldFiniteControls.java',D/'IndependentFieldControls.java']
        command('compile',[JDK/'bin/javac','--release','17','-proc:none','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources])
        actual={name:identity(classes/name) for name in class_map};assert actual==class_map
        context=hashlib.sha256(json.dumps({'source_map':source_map,'class_map':actual},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert context==CONTEXT
        save(run/'actual-product-class-map.json',actual)
        save(run/'compile-identity.json',{'product_sources':16,'product_classes':209,'B_leaves':87,'v4_derivatives':8,'all_209_exact':True,'context':context,'BCI_remapping':False})
        command('producer-replay',[JDK/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.FieldFiniteControls',PACKET/'inputs/descriptor.json',run/'actual-results.json'])
        result=json.loads((run/'actual-results.json').read_bytes());original=json.loads((PACKET/'run-2/actual-results.json').read_bytes())
        assert result==original,'fresh replay differs from selected frozen actual results'
        assert result['invocations']==123 and result['checks']==645 and result['host_threads_started']==result['host_threads_joined']==3
        counts=collections.Counter((row['subject_id'].split('#')[0],row['subject_id'].split('#')[1].split('(')[0]) for row in result['rows'])
        assert sorted(counts.values())==[9,16,22,76]
        masks={row['independent_expected_before_invocation']['mask']:row['actual_result'] for row in result['rows'] if row['finite_case'].startswith('truth-table-')}
        assert masks=={mask:mask==63 for mask in range(64)}
        constructors=[row for row in result['rows'] if '#<init>' in row['subject_id'] and row['completion']=='normal'];assert len(constructors)==24
        assert len({row['actual_after']['reference'] for row in constructors})==24
        assert len({row['actual_after']['hooks_reference'] for row in constructors})==24
        returns=exceptions=nocall=0
        for row in result['rows']:
            assert row['counts_before']==row['counts_after']==[2,2,3] and row['shared_mutations_restored'] and row['no_native_events'] and row['no_membership_release_authority']
            if '#endReady(' in row['subject_id'] or '#unchangedLoss(' in row['subject_id']:assert row['actual_before']==row['actual_after']
            observation=row['input_observation']
            if observation is None:continue
            assert observation['delegate_reference'].startswith('dev.mixer.android.NativeRenderer$2@')
            if observation['calls']==0:nocall+=1;assert observation['actual_return_long'] is None and observation['actual_exception_reference']=='null';continue
            assert observation['calls']==1
            if row['completion']=='normal':returns+=1;assert isinstance(observation['actual_return_long'],int)
            else:
                exceptions+=1;assert observation['actual_exception_type']=='java.lang.IllegalStateException' and observation['actual_exception_message']=='V2 requires UI owner thread'
                assert observation['actual_exception_reference']==row['exact_exception_reference']!='null'
        assert (returns,exceptions,nocall)==(25,2,20)
        command('independent-controls',[JDK/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.IndependentFieldControls',PACKET/'inputs/descriptor.json',run/'independent-results.json'])
        additional=json.loads((run/'independent-results.json').read_bytes());assert additional['cases']==4 and additional['host_threads_started']==additional['host_threads_joined']==1
        failure=json.loads((PACKET/'run-1/failure.json').read_bytes());assert failure['status']=='actual-failed-attempt-no-pass-credit'
        assert 'non-static method counts()' in (PACKET/'run-1/compile.stderr').read_text()
        assert verify_packet()==custody;save(run/'custody-after.json',custody)
        save(run/'receipt.json',{'schema':1,'status':'narrow-four-body-finite-host-facets-accepted','source_context':CONTEXT,'producer_replay_exact_json_equal':True,'producer_replay':{'invocations':123,'checks':645,'constructor_objects':24,'actual_Input_long_returns':25,'identical_actual_Input_exceptions':2,'Input_no_call_rows':20,'guard_masks':64,'threads_started_joined':3},'independent_controls':additional,'prior_producer_run1':'retained actual javac accessor-name-collision failure; no pass credit','all_209_product_classes_exact':True,'packet_unchanged':True,'Input_calls_are_separate_actual_product_interface_observations':True,'native_callback_state_credit':0,'native_UI_capture_process_inventory_started':False,'pending':['actual Input Long.MAX_VALUE terminal exhaustion branch','runtime allocation failures','exceptional constructor partial receiver state','all original semantic categories and enclosing membership/release authority','native runtime and physical-device qualification, paused'],'canonical_membership_release_native_OTA_GA_accepted':False})
    except BaseException as failure:
        save(run/'failure.json',{'type':type(failure).__name__,'message':str(failure),'status':'actual-failed-attempt-no-pass-credit'});raise
    finally:
        shutil.rmtree(scratch)
        save(run/'cleanup.json',{'all_started_children_reaped':all(row['reaped'] for row in commands),'maximum_concurrent_children':1,'owned_scratch_removed':not scratch.exists(),'jdk_lease_preserved':True,'native_instances_started':0,'native_UI_capture_process_inventory_started':False,'other_projects_touched':False,'physical_cleanup_credit':False})

if __name__=='__main__':main()
