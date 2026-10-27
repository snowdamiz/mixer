#!/usr/bin/env python3
"""Bounded host-only constructor execution against exact released product16/B87/v4."""
from pathlib import Path
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
COHERENT=ROOT/'verification/android-source-pair5-coherent-integration-preparation'
SEMANTIC=ROOT/'verification/android-renderer-semantic-policy-preparation'
FINITE=ROOT/'verification/android-renderer-finite-membership-controls'
PROBE=ROOT/'verification/android-editor-membership-compiled-boundary-qualification/passive-return-probe-v4'
JDK=ROOT/'verification/android-editor-membership-compiled-boundary-qualification/state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
SEALS=[(COHERENT,'0dc913d88d4ee7d1e6583bdf00e1e407cc6b446ac7c7aaf6180a36a45b021e9b'),(SEMANTIC,'35e5cf5d97652a76829bfd10c967898d1d32d7315104a592ab1a34c26c560c9b'),(FINITE,'e901741635c6827b0d14b70c51248ea64a5a4071defd0d8a4c58c9fbdb904f93'),(PROBE,'8501bfa60dbae4c3d90be181e8d4fe1e858d1f59908328c4c9855fe7bc99eff8')]

def identity(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def verify(packet,expected):
    assert identity(packet/'seal.json')['sha256']==expected,str(packet)
    seal=json.loads((packet/'seal.json').read_bytes())
    members=seal['members']
    members=([{'path':name,**value} for name,value in members.items()] if isinstance(members,dict) else members)
    for row in members:
        path=Path(row['path']);assert not path.is_absolute() and '..' not in path.parts
        assert identity(packet/path)=={'bytes':row['bytes'],'sha256':row['sha256']},str(packet/path)
    return {'path':str(packet.relative_to(ROOT)),'seal':identity(packet/'seal.json'),'members_verified':len(members)}

def main():
    runroot=D/sys.argv[1];runroot.mkdir()
    scratch=runroot/'scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
    commands=[];env=dict(os.environ)
    for name in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(name,None)
    def run(name,argv):
        started=time.monotonic();stdout=runroot/(name+'.stdout');stderr=runroot/(name+'.stderr')
        with stdout.open('wb') as out,stderr.open('wb') as err:
            child=subprocess.Popen([str(x) for x in argv],cwd=D,env=env,stdout=out,stderr=err,start_new_session=True)
            timeout=False
            try:child.wait(timeout=60)
            except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        row={'name':name,'argv':[str(x) for x in argv],'cwd':str(D),'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed_seconds':time.monotonic()-started,'stdout':{'path':stdout.name,**identity(stdout)},'stderr':{'path':stderr.name,**identity(stderr)}}
        commands.append(row);save(runroot/'commands.json',commands);print(name,child.returncode,flush=True)
        assert child.returncode==0 and not timeout,row
    try:
        shutil.copyfile(D/'ConstructorControls.java',runroot/'ConstructorControls.java');shutil.copyfile(Path(__file__),runroot/'run_controls.py')
        save(runroot/'launch.json',{'launch':[sys.executable,'-B',str(Path(__file__)),sys.argv[1]],'runner':identity(Path(__file__)),'control':identity(D/'ConstructorControls.java'),'python':sys.version,'platform':platform.platform()})
        verified=[verify(packet,expected) for packet,expected in SEALS]
        acceptance=ROOT/'verification/android-editor-boundary-root-review/passive-return-probe-v4-acceptance.json'
        accepted=json.loads(acceptance.read_bytes());assert accepted['candidate']['seal_sha256']==SEALS[-1][1]
        inputs=D/'inputs';inputs.mkdir(exist_ok=True)
        source_map=json.loads((FINITE/'inputs/selected-product-source-map.json').read_bytes());class_map=json.loads((FINITE/'inputs/selected-product-class-map.json').read_bytes())
        assert len(source_map)==16 and len(class_map)==209
        assert hashlib.sha256(json.dumps({'source_map':source_map,'class_map':class_map},sort_keys=True,separators=(',',':')).encode()).hexdigest()==CONTEXT
        roster=[]
        def copy(source,target,role):
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);roster.append({'origin':str(source.relative_to(ROOT)),'path':str(target.relative_to(D)),'role':role,**identity(target)})
        for name,expected in sorted(source_map.items()):
            source=COHERENT/'source/native/android/app/src/dev/mixer/android'/name;assert identity(source)==expected
            copy(source,inputs/'product'/name,'exact-product16')
        old=json.loads((FINITE/'inputs/source-roster.json').read_bytes())
        leaves_map={row['path'].split('/host-leaves/',1)[1]:{'bytes':row['bytes'],'sha256':row['sha256']} for row in old if '/host-leaves/' in row['path']}
        assert len(leaves_map)==87
        derivatives=json.loads((PROBE/'derivative-source-roster.json').read_bytes());assert derivatives['schema']==4 and len(derivatives['records'])==8
        derivative_map={row['path']:row['derivative'] for row in derivatives['records']}
        for name,expected in sorted(leaves_map.items()):
            original=FINITE/'inputs/host-leaves'/name;assert identity(original)==expected
            source=(PROBE/'NativeOutcomeProbe.java' if name=='dev/mixer/android/NativeOutcomeProbe.java' else PROBE/'leaves'/name) if name in derivative_map else original
            if name in derivative_map:assert identity(source)==derivative_map[name]
            copy(source,inputs/'host-leaves'/name,'selected-v4-derivative' if name in derivative_map else 'exact-B87')
        assert set(derivative_map).issubset(leaves_map)
        assert identity(inputs/'host-leaves/dev/mixer/android/NativeOutcomeProbe.java')==derivative_map['dev/mixer/android/NativeOutcomeProbe.java']
        copy(FINITE/'inputs/SelectedIdentityMembershipReviewControls.java',inputs/'SelectedIdentityMembershipReviewControls.java','released-selected6-exact-original-fixture')
        assert identity(inputs/'SelectedIdentityMembershipReviewControls.java')['sha256']=='3752075126e21678880e431a833ade2511c1a5c8c1110c3f5f7a39fe194d1c2b'
        copy(SEMANTIC/'inputs/descriptor.json',inputs/'descriptor.json','released-descriptor')
        save(inputs/'selected-product-source-map.json',source_map);save(inputs/'selected-product-class-map.json',class_map)
        proposal=json.loads((SEMANTIC/'proposal.json').read_bytes());subjects=[s for s in proposal['subjects'] if s['class'] in ('dev/mixer/android/NativeRenderer$NativeState','dev/mixer/android/NativeRenderer$AttachmentJournal')]
        assert len(subjects)==2
        save(inputs/'exact-two-subject-contracts.json',{'source_context':CONTEXT,'subjects':subjects})
        save(inputs/'source-roster.json',roster)
        shutil.copyfile(D/'ConstructorControls.java',runroot/'ConstructorControls.java');shutil.copyfile(Path(__file__),runroot/'run_controls.py')
        save(runroot/'provenance.json',{'schema':1,'frozen_inputs':verified,'root_v4_acceptance':{'path':str(acceptance.relative_to(ROOT)),**identity(acceptance)},'source_context':CONTEXT,'source_revision_context':proposal['source_revision_context'],'python':sys.version,'platform':platform.platform(),'runner':identity(Path(__file__)),'control':identity(D/'ConstructorControls.java'),'tool_lease':str(JDK.relative_to(ROOT)),'tool_lease_scope':'only JDK installation read/execute; surrounding active files not read or deleted','tools':{name:identity(JDK/name) for name in ('bin/java','bin/javac','lib/modules','lib/server/libjvm.dylib')},'javac_debug':'default; no -g or -g:none','model':'gpt-6.1-sol','reasoning_effort':'xhigh','launch':[sys.executable,'-B',str(Path(__file__)),sys.argv[1]]})
        run('java-version',[JDK/'bin/java','-version']);run('javac-version',[JDK/'bin/javac','-version'])
        sources=[D/row['path'] for row in roster if row['path'].endswith('.java')]+[D/'ConstructorControls.java']
        run('compile',[JDK/'bin/javac','--release','17','-proc:none','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources])
        actual={name:identity(classes/name) for name in class_map};assert actual==class_map,'all209 product class identity mismatch'
        context=hashlib.sha256(json.dumps({'source_map':source_map,'class_map':actual},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert context==CONTEXT
        save(runroot/'actual-product-class-map.json',actual);save(runroot/'compile-identity.json',{'product_sources':16,'product_classes':209,'B_leaves':87,'selected_v4_derivative_files':8,'source_context':context,'all_209_exact_matches':True,'BCI_remapping':False})
        run('constructor-controls',[JDK/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.ConstructorControls',inputs/'descriptor.json',runroot/'actual-results.json'])
        result=json.loads((runroot/'actual-results.json').read_bytes());assert result['invocations']==85 and result['callback_rows']==70 and result['finite_rows']==15
        assert result['original_final_counts']==[0,0,0] and result['original_edit_completed_after_restores']
        tuples={}
        for row in result['rows']:
            assert row['counts_before']==row['counts_after'] and row['mutations_restored'] and row['native_outcome_capture_clean'] and row['no_membership_or_release_authority']
            if row['native_site_id']:tuples.setdefault(row['native_site_id'],set()).add(row['callback_state'])
        assert len(tuples)==5 and all(len(states)==7 for states in tuples.values())
        save(runroot/'receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'two-exact-constructors-host-controls-passed-root-review-pending','source_context':CONTEXT,'source_revision_context':proposal['source_revision_context'],'results':identity(runroot/'actual-results.json'),'control':identity(D/'ConstructorControls.java'),'runner':identity(Path(__file__)),'invocations':85,'callback_rows':70,'finite_rows':15,'exact_hooked_tuples':5,'states_per_tuple':7,'checks':result['checks'],'host_environment':'macOS JDK17, exact product16/all209, released original Fixture(true,true), B87 with accepted v4 instrumentation','normal_result_scope':'actual reflected enclosing constructor object and immutable typed field/span/array/reference snapshots; exact exception identity for throwing constructors','void_output_scope':'normal completed NativeState.windowPosition values only; no nonvoid return or exceptional partial array identity invented','actual_original_edit_completed_after_restores':True,'original_boundary_counts':[2,2,3],'actual_final_counts':[0,0,0],'native_runtime_UI_capture_process_inventory_started':False,'physical_native_cleanup_credit':False,'full_matrix_canonical_membership_release_native_OTA_GA_accepted':False,'pending':['Root/independent selection and producer exact matrix joins','Original enclosing authority/cohort/completion/cleanup/funding obligations','Exceptional constructor receiver and private partial array identity are unobservable','Internal source drawable array identity and actual runtime allocation failure injection','Native runtime and physical checks remain paused']})
    except BaseException as failure:
        save(runroot/'failure.json',{'type':type(failure).__name__,'message':str(failure),'status':'actual-failed-attempt-no-pass-credit'});raise
    finally:
        shutil.rmtree(scratch)
        save(runroot/'cleanup.json',{'all_started_children_reaped':all(row['reaped'] for row in commands),'maximum_concurrent_children':1,'owned_scratch_removed':not scratch.exists(),'jdk_tool_lease_preserved':True,'native_instances_started':0,'process_inventory_or_other_projects_touched':False,'original_fixture_close_may_catch_errors':'host disposal only; no physical cleanup credit'})

if __name__=='__main__':main()
