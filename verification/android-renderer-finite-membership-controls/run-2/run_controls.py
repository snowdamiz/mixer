#!/usr/bin/env python3
"""Reproduce frozen product16/B87 hashes then execute ordinary finite controls only."""
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

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
ROOT = D.parent.parent
COHERENT = ROOT / 'verification/android-source-pair5-coherent-integration-preparation'
SEMANTIC = ROOT / 'verification/android-renderer-semantic-policy-preparation'
LEDGER = ROOT / 'verification/android-finite-ledger-controls'
JDK = ROOT / 'verification/android-editor-membership-compiled-boundary-qualification/state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'
CONTEXT = '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
NAMES = ['preservationMembershipV2', 'fieldPreservationCapturedV2', 'preservationProvenanceV2', 'fieldPreservationIdentityV2', 'preservationCohortV2', 'preservationFailureFundedV2']
SEALS = [(COHERENT,'0dc913d88d4ee7d1e6583bdf00e1e407cc6b446ac7c7aaf6180a36a45b021e9b'),(SEMANTIC,'35e5cf5d97652a76829bfd10c967898d1d32d7315104a592ab1a34c26c560c9b'),(LEDGER,'f90c7fd6240fd8fc63c3c16ac01997e673747d222136271764e1e657ad447a0b')]

def identity(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def save(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n')

def verify(packet,seal):
    assert identity(packet/'seal.json')['sha256']==seal
    data=json.loads((packet/'seal.json').read_bytes())
    for member in data['members']:
        path=Path(member['path']);assert not path.is_absolute() and '..' not in path.parts
        assert identity(packet/path)=={'bytes':member['bytes'],'sha256':member['sha256']},str(packet/path)
    return {'root':str(packet.relative_to(ROOT)),'seal':identity(packet/'seal.json'),'members_verified':len(data['members'])}

def main():
    runroot=D/sys.argv[1];runroot.mkdir()
    scratch=runroot/'scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
    commands=[]
    env=dict(os.environ)
    for name in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):
        env.pop(name,None)
    def run(name,argv):
        start=time.monotonic();stdout=runroot/(name+'.stdout');stderr=runroot/(name+'.stderr')
        with stdout.open('wb') as out,stderr.open('wb') as err:
            child=subprocess.Popen([str(value) for value in argv],cwd=D,stdout=out,stderr=err,env=env,start_new_session=True)
            timeout=False
            try:child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        row={'name':name,'argv':[str(value) for value in argv],'cwd':str(D),'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed_seconds':time.monotonic()-start,
             'stdout':{'path':stdout.name,**identity(stdout)},'stderr':{'path':stderr.name,**identity(stderr)}}
        commands.append(row);save(runroot/'commands.json',commands);print(name,child.returncode,flush=True)
        assert child.returncode==0 and not timeout,row
    try:
        inputs=D/'inputs';inputs.mkdir(exist_ok=True)
        verified=[verify(packet,seal) for packet,seal in SEALS]
        source_map=json.loads((LEDGER/'inputs/selected-product-source-map.json').read_bytes())
        class_map=json.loads((LEDGER/'inputs/selected-product-class-map.json').read_bytes())
        assert len(source_map)==16 and len(class_map)==209
        assert hashlib.sha256(json.dumps({'source_map':source_map,'class_map':class_map},sort_keys=True,separators=(',',':')).encode()).hexdigest()==CONTEXT
        save(inputs/'selected-product-source-map.json',source_map);save(inputs/'selected-product-class-map.json',class_map)
        original=json.loads((SEMANTIC/'inputs/complete-280-checklist.json').read_bytes())
        subjects=[subject for subject in original['subjects'] if subject['method'] in NAMES]
        assert len(subjects)==6 and {s['method'] for s in subjects}==set(NAMES)
        save(inputs/'original-six-subjects.json',{'checklist':identity(SEMANTIC/'inputs/complete-280-checklist.json'),'subjects':subjects})
        selected=json.loads((SEMANTIC/'proposal.json').read_bytes())
        save(inputs/'original-six-semantic-proposals.json',{'subjects':[s for s in selected['subjects'] if s['method'] in NAMES]})
        roster=[]
        def copy(source,target,role):
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
            roster.append({'role':role,'origin':str(source.relative_to(ROOT)),'path':str(target.relative_to(D)),**identity(target)})
        for name,expected in source_map.items():
            source=COHERENT/'source/native/android/app/src/dev/mixer/android'/name;assert identity(source)==expected
            copy(source,inputs/'product'/name,'exact-product')
        leaves=COHERENT/'source/native/android/tests/NativeOwnerV2ConcreteHostLeaves'
        old=json.loads((LEDGER/'inputs/source-roster.json').read_bytes())
        leaves_map={row['path'].split('/host-leaves/',1)[1]:{'bytes':row['bytes'],'sha256':row['sha256']} for row in old if '/host-leaves/' in row['path']}
        assert len(leaves_map)==87
        for name,expected in sorted(leaves_map.items()):
            source=leaves/name;assert identity(source)==expected;copy(source,inputs/'host-leaves'/name,'exact-selected-B-leaf')
        copy(COHERENT/'source/native/android/tests/NativeEditorPreservationHostControls/SelectedIdentityMembershipReviewControls.java',inputs/'SelectedIdentityMembershipReviewControls.java','original-ordinary-fixture')
        copy(SEMANTIC/'inputs/descriptor.json',inputs/'descriptor.json','original-descriptor')
        roster.append({'role':'new-finite-control','path':'FiniteMembershipControls.java',**identity(D/'FiniteMembershipControls.java')})
        save(inputs/'source-roster.json',roster)
        shutil.copyfile(D/'FiniteMembershipControls.java',runroot/'FiniteMembershipControls.java');shutil.copyfile(Path(__file__),runroot/'run_controls.py')
        save(runroot/'provenance.json',{'packets':verified,'source_revision_context':'6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2','source_context':CONTEXT,'python':sys.version,'platform':platform.platform(),
            'runner':identity(Path(__file__)),'tool_lease':str(JDK.relative_to(ROOT)),'lease_scope':'JDK installation read/execute only; no active surrounding source reads',
            'tools':{name:identity(JDK/name) for name in ('bin/java','bin/javac','lib/modules','lib/server/libjvm.dylib')},'no_explicit_g_switch':True,
            'launch_command':[sys.executable,'-B',str(Path(__file__)),sys.argv[1]]})
        run('java-version',[JDK/'bin/java','-version']);run('javac-version',[JDK/'bin/javac','-version'])
        sources=[D/row['path'] for row in roster if row['path'].endswith('.java')]
        run('compile',[JDK/'bin/javac','--release','17','-proc:none','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources])
        actual_map={name:identity(classes/name) for name in class_map};assert actual_map==class_map,'209 exact class hash reproduction failed'
        actual_source={name:identity(inputs/'product'/name) for name in source_map}
        actual_context=hashlib.sha256(json.dumps({'source_map':actual_source,'class_map':actual_map},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert actual_context==CONTEXT
        save(runroot/'actual-product-class-map.json',actual_map);save(runroot/'compile-identity.json',{'source_context':actual_context,'all_209_exact_matches':True,'product_sources':16,'product_classes':209,'concrete_B_leaves':87,'BCI_remapping':False})
        run('finite-membership-controls',[JDK/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.FiniteMembershipControls',inputs/'descriptor.json',runroot/'actual-results.json'])
        result=json.loads((runroot/'actual-results.json').read_bytes())
        assert result['count_at_original_boundary']==3 and result['original_final_counts']==[0,0,0]
        assert len(result['rows'])==result['invocations'] and {row['subject_id'] for row in result['rows']}=={s['id'] for s in subjects}
        for row in result['rows']:
            subject=next(s for s in subjects if s['id']==row['subject_id']);assert row['class_sha256']==subject['class_sha256']
            assert row['all_snapshots_unchanged'] and row['native_effects']==0 and row['counts_before']==row['counts_after']
        shutil.copytree(classes,runroot/'classes')
        save(runroot/'receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'six-exact-finite-host-methods-passed-root-selection-pending','source_context':CONTEXT,
            'source_revision_context':'6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2','source_roster':identity(inputs/'source-roster.json'),'control':identity(D/'FiniteMembershipControls.java'),'results':identity(runroot/'actual-results.json'),
            'invocations':result['invocations'],'checks':result['checks'],'per_subject':{s['id']:sum(row['subject_id']==s['id'] for row in result['rows']) for s in subjects},
            'environment':'macOS host JVM17 with exact original concrete B87 leaves and ordinary original Fixture(true,true); passive hook after startup; synchronous direct reflection of exact six methods',
            'finite_mutation_scope':'ordinary test-only exact fields/array slots; all restored in finally before original edit resumes; no copied predicate code or special allocation',
            'purity':'every relevant reachable product/host field, inherited field, array slot, collection member, NativeBridge static fields and native event prefix compared before/after every direct call',
            'count_boundary':[2,2,3],'actual_original_edit_completed_after_restores':True,'actual_end_counts':[0,0,0],
            'native_runtime_devices_UI_capture_process_inventory_started':False,'physical_native_cleanup_credit':False,'full_policy_matrix_native_OTA_GA_accepted':False,
            'pending':['Root independent semantic selection and final producer joins','Original enclosing cohort/authority/callback/count/close/exception propagation obligations','Runtime allocation failures','Native and physical checks paused']})
    except BaseException as failure:
        save(runroot/'failure.json',{'type':type(failure).__name__,'message':str(failure),'status':'failed-authoring-attempt-no-pass-credit'})
        raise
    finally:
        shutil.rmtree(scratch)
        save(runroot/'cleanup.json',{'all_started_children_reaped':all(row['reaped'] for row in commands),'owned_scratch_removed':not scratch.exists(),'JDK_tool_installation_preserved':True,'native_instances_started':0,'physical_native_cleanup_credit':False,'process_inventory_or_other_projects_touched':False,'original_fixture_close_may_catch_errors':'host disposal only; no physical cleanup evidence'})

if __name__=='__main__':main()
