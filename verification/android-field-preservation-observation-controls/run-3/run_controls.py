#!/usr/bin/env python3
"""Bounded actual JVM controls; source-specific evidence, no release authority."""
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
PRODUCER=ROOT/'verification/android-editor-membership-compiled-boundary-qualification'
PROBE=PRODUCER/'passive-return-probe-v4'
SEMANTIC=PRODUCER/'semantic-review-candidate-v1'
REVIEW=ROOT/'verification/android-editor-preservation-membership-independent/actual-review'
JDK=PRODUCER/'state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
SEALS=[(PROBE,'8501bfa60dbae4c3d90be181e8d4fe1e858d1f59908328c4c9855fe7bc99eff8'),(SEMANTIC,'361412b6ee2124ace685a2242390ece375d0327b119876b13db27dc95ea3f5e6'),(PRODUCER/'tool-context-jdk17','969b09648e2c3061e4a86d74da95df2fc90cc905b690be54715a98bfbceee1a6')]

def identity(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def verify(packet,expected):
    assert identity(packet/'seal.json')['sha256']==expected,str(packet)
    seal=json.loads((packet/'seal.json').read_bytes());members=seal['members']
    members=([{'path':name,**value} for name,value in members.items()] if isinstance(members,dict) else members)
    for row in members:
        path=Path(row['path']);assert not path.is_absolute() and '..' not in path.parts
        assert identity(packet/path)=={'bytes':row['bytes'],'sha256':row['sha256']},str(packet/path)
    return {'path':str(packet.relative_to(ROOT)),'seal':identity(packet/'seal.json'),'members_verified':len(members)}
def main():
    assert len(sys.argv)==2 and Path(sys.argv[1]).name==sys.argv[1] and sys.argv[1].startswith('run-')
    runroot=D/sys.argv[1];runroot.mkdir();scratch=runroot/'scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
    commands=[];env=dict(os.environ)
    for name in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(name,None)
    def run(name,argv):
        started=time.monotonic();stdout=runroot/(name+'.stdout');stderr=runroot/(name+'.stderr');timeout=False
        with stdout.open('wb') as out,stderr.open('wb') as err:
            child=subprocess.Popen([str(x) for x in argv],cwd=D,env=env,stdout=out,stderr=err,start_new_session=True)
            try:child.wait(timeout=60)
            except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
            except BaseException:
                os.killpg(child.pid,signal.SIGKILL);child.wait();raise
        row={'name':name,'argv':[str(x) for x in argv],'cwd':str(D),'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed_seconds':time.monotonic()-started,'stdout':{'path':stdout.name,**identity(stdout)},'stderr':{'path':stderr.name,**identity(stderr)}}
        commands.append(row);save(runroot/'commands.json',commands);print(name,child.returncode,flush=True);assert child.returncode==0 and not timeout,row
    try:
        shutil.copyfile(D/'FieldObservationControls.java',runroot/'FieldObservationControls.java');shutil.copyfile(Path(__file__),runroot/'run_controls.py')
        save(runroot/'launch.json',{'launch':[sys.executable,'-B',str(Path(__file__)),sys.argv[1]],'runner':identity(Path(__file__)),'control':identity(D/'FieldObservationControls.java'),'python':sys.version,'platform':platform.platform()})
        verified=[verify(packet,expected) for packet,expected in SEALS]
        acceptance=ROOT/'verification/android-editor-boundary-root-review/passive-return-probe-v4-acceptance.json';assert identity(acceptance)['sha256']=='cb9b8481827d4e5966e68292b447f610f67061cff9b997bf32da8c26f0ffec16'
        assert identity(REVIEW/'review-seal.json')['sha256']=='8d51b0e6d04b152621e9e6f9ad3b6c46b3301853ed5d0c545fd4781a66c36c6d'
        context=json.loads((SEMANTIC/'product-context.json').read_bytes());source_map=context['source_map'];class_map=context['class_map'];assert len(source_map)==16 and len(class_map)==209 and context['context_id']==CONTEXT
        assert hashlib.sha256(json.dumps({'source_map':source_map,'class_map':class_map},sort_keys=True,separators=(',',':')).encode()).hexdigest()==CONTEXT
        inputs=D/'inputs';inputs.mkdir(exist_ok=True);roster=[]
        def copy(source,target,role):
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert identity(target)==identity(source),str(target)
            else:shutil.copyfile(source,target)
            roster.append({'origin':str(source.relative_to(ROOT)),'path':str(target.relative_to(D)),'role':role,**identity(target)})
        for name,expected in sorted(source_map.items()):
            source=PROBE/'inputs/source'/name;assert identity(source)==expected;copy(source,inputs/'product'/name,'unchanged-exact-product16')
        derivatives=json.loads((PROBE/'derivative-source-roster.json').read_bytes());assert derivatives['schema']==4 and len(derivatives['records'])==8;derivative_map={r['path']:r['derivative'] for r in derivatives['records']}
        leaves=sorted((PROBE/'inputs/host-leaves').rglob('*.java'));assert len(leaves)==87
        for original in leaves:
            name=str(original.relative_to(PROBE/'inputs/host-leaves'));source=(PROBE/'NativeOutcomeProbe.java' if name=='dev/mixer/android/NativeOutcomeProbe.java' else PROBE/'leaves'/name) if name in derivative_map else original
            if name in derivative_map:assert identity(source)==derivative_map[name]
            copy(source,inputs/'host-leaves'/name,'accepted-v4-derivative' if name in derivative_map else 'unchanged-B87')
        fixture=REVIEW/'selected-controls/SelectedIdentityMembershipReviewControls.java';assert identity(fixture)=={'bytes':56594,'sha256':'3752075126e21678880e431a833ade2511c1a5c8c1110c3f5f7a39fe194d1c2b'};copy(fixture,inputs/fixture.name,'unchanged-released-original-fixture')
        copy(PROBE/'descriptor.json',inputs/'descriptor.json','released-descriptor')
        copy(SEMANTIC/'active-semantic-obligations.json',inputs/'original-280-obligations.json','all-original280-unchanged')
        active=json.loads((inputs/'original-280-obligations.json').read_bytes());subjects=active['subjects'];assert len(subjects)==280 and len({r['id'] for r in subjects})==280
        selected=[r for r in subjects if r['class']=='dev/mixer/android/NativeAppearanceViewsV2$FieldPreservation' and r['method'] in ('tuple','capture','exact','continuation')];assert len(selected)==4 and all(len(r['required_semantic_cases'])==8 for r in selected)
        save(inputs/'exact-four-subject-contracts.json',{'source_context':CONTEXT,'subjects':selected,'all_original_fields_categories_ids_cases_instructions_retained':True,'original_cases_not_discharged_by_finite_facets':True})
        save(inputs/'historical189-custody.json',{'path':str((SEMANTIC/'historical189-current-bindings.json').relative_to(ROOT)),**identity(SEMANTIC/'historical189-current-bindings.json'),'unchanged':True,'count':'189 historical V2 dispositions plus 5 separately witnessed V1 sites','qualification':'preserved by immutable seal/reference; no roster reduction'})
        save(inputs/'selected-product-source-map.json',source_map);save(inputs/'selected-product-class-map.json',class_map);save(inputs/'source-roster.json',roster)
        source_revision=json.loads(acceptance.read_bytes())['source_revision_context']
        save(runroot/'provenance.json',{'schema':1,'frozen_inputs':verified,'root_v4_acceptance':{'path':str(acceptance.relative_to(ROOT)),**identity(acceptance)},'fixture_review_seal':identity(REVIEW/'review-seal.json'),'source_context':CONTEXT,'source_revision_context':source_revision,'python':sys.version,'platform':platform.platform(),'runner':identity(Path(__file__)),'control':identity(D/'FieldObservationControls.java'),'tool_lease':str(JDK.relative_to(ROOT)),'tool_lease_scope':'installation read/execute only; shared installation retained','tools':{name:identity(JDK/name) for name in ('bin/java','bin/javac','lib/modules','lib/server/libjvm.dylib')},'javac_debug':'default, no -g or -g:none','model':'gpt-6.1-sol','reasoning_effort':'xhigh'})
        run('java-version',[JDK/'bin/java','-version']);run('javac-version',[JDK/'bin/javac','-version'])
        sources=[D/r['path'] for r in roster if r['path'].endswith('.java')]+[D/'FieldObservationControls.java']
        run('compile',[JDK/'bin/javac','--release','17','-proc:none','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources])
        actual={name:identity(classes/name) for name in class_map};assert actual==class_map,'all209 product class mismatch';actual_context=hashlib.sha256(json.dumps({'source_map':source_map,'class_map':actual},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert actual_context==CONTEXT
        save(runroot/'actual-product-class-map.json',actual);save(runroot/'compile-identity.json',{'product_sources':16,'product_classes':209,'B_leaves':87,'selected_v4_derivative_files':8,'source_context':actual_context,'all_209_exact_matches':True,'BCI_remapping':False})
        run('field-observation-controls',[JDK/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.FieldObservationControls',inputs/'descriptor.json',runroot/'actual-results.json'])
        result=json.loads((runroot/'actual-results.json').read_bytes());assert result['invocations']==56 and result['actual_final_counts']==[0,0,0] and result['original_edit_completed_after_restores']
        assert result['host_threads_started']==result['host_threads_joined']==2 and result['failure_latch_clear'] and result['no_final_field_or_exhaustion_mutations']
        assert {r['subject_id'] for r in result['rows']}=={r['id'] for r in selected}
        assert all(r['counts_before']==r['counts_after']==[2,2,3] and r['restored_before_original_edit_resumes'] and r['no_membership_release_authority'] for r in result['rows'])
        save(runroot/'receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'four-exact-bodies-finite-host-observations-passed-root-review-pending','source_context':CONTEXT,'source_revision_context':source_revision,'results':identity(runroot/'actual-results.json'),'control':identity(D/'FieldObservationControls.java'),'runner':identity(Path(__file__)),'invocations':result['invocations'],'checks':result['checks'],'host_environment':'macOS JDK17, exact product16/all209, unchanged original Fixture(true,true), B87 with accepted v4 instrumentation','actual_original_edit_completed_after_restores':True,'original_boundary_counts':[2,2,3],'actual_final_counts':[0,0,0],'bounded_host_threads_started_and_joined':2,'native_runtime_UI_capture_process_inventory_started':False,'physical_native_cleanup_credit':False,'full_matrix_canonical_membership_release_native_OTA_GA_accepted':False,'pending':['Root independent selection and producer exact method joins','All eight original semantic cases per subject and enclosing obligations retained pending','Runtime allocation failures, snapshot/Mutation allocation exceptional partial outputs','Exact Input invocation counts and BCI tracing; original final Input is unchanged', 'Unexecuted final-field identity/mode/fence/token, terminal and loss-exhaustion branches','Native runtime and physical checks remain paused']})
    except BaseException as failure:
        save(runroot/'failure.json',{'type':type(failure).__name__,'message':str(failure),'status':'actual-failed-attempt-no-pass-credit'});raise
    finally:
        shutil.rmtree(scratch);save(runroot/'cleanup.json',{'all_started_children_reaped':all(r['reaped'] for r in commands),'maximum_concurrent_children':1,'owned_scratch_removed':not scratch.exists(),'jdk_tool_lease_preserved':True,'native_instances_started':0,'process_inventory_or_other_projects_touched':False,'original_fixture_close_scope':'host disposal only; no physical cleanup credit'})
if __name__=='__main__':main()
