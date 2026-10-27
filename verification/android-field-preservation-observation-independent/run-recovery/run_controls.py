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
JDK=PRODUCER/'state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'

def identity(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
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
        shutil.copyfile(D/'dynamic-source/FieldObservationControls.java',runroot/'FieldObservationControls.java');shutil.copyfile(Path(__file__),runroot/'run_controls.py')
        save(runroot/'launch.json',{'launch':[sys.executable,'-B',str(Path(__file__)),sys.argv[1]],'runner':identity(Path(__file__)),'control':identity(D/'dynamic-source/FieldObservationControls.java'),'python':sys.version,'platform':platform.platform()})
        frozen=ROOT/'verification/android-field-preservation-observation-controls'
        assert identity(frozen/'seal.json')['sha256']=='02f4a046dd7f10266e17b804c6b86bd857f19807306bcf17214f9d5914e81250'
        seal=json.loads((frozen/'seal.json').read_bytes())
        expected={r['path']:r for r in seal['members']}
        assert len(expected)==171 and set(expected)=={str(p.relative_to(frozen)) for p in frozen.rglob('*') if p.is_file() and p.name!='seal.json'}
        for name,row in expected.items():
            assert not (frozen/name).is_symlink()
            assert identity(frozen/name)=={'bytes':row['bytes'],'sha256':row['sha256']},name
        inputs=frozen/'inputs'
        roster=json.loads((inputs/'source-roster.json').read_bytes())
        source_map=json.loads((inputs/'selected-product-source-map.json').read_bytes())
        class_map=json.loads((inputs/'selected-product-class-map.json').read_bytes())
        assert len(source_map)==16 and len(class_map)==209
        assert hashlib.sha256(json.dumps({'source_map':source_map,'class_map':class_map},sort_keys=True,separators=(',',':')).encode()).hexdigest()==CONTEXT
        for row in roster:
            assert identity(frozen/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']}
        selected=json.loads((inputs/'exact-four-subject-contracts.json').read_bytes())['subjects']
        source_revision=seal['source_revision_context']
        save(runroot/'provenance.json',{'schema':1,'frozen_packet_seal':identity(frozen/'seal.json'),'closed_members_verified':len(expected),'source_context':CONTEXT,'source_revision_context':source_revision,'python':sys.version,'platform':platform.platform(),'runner':identity(Path(__file__)),'author_runner':identity(D/'author-runner.py'),'control':identity(D/'dynamic-source/FieldObservationControls.java'),'tool_lease':str(JDK.relative_to(ROOT)),'tool_lease_scope':'installation read/execute only; shared installation retained','tools':{name:identity(JDK/name) for name in ('bin/java','bin/javac','lib/modules','lib/server/libjvm.dylib')},'javac_debug':'default, no -g or -g:none','replay_adaptation':'copied runner uses frozen inputs read-only; no upstream preparation, input writes or finalize; output only in this independent lane'})
        run('java-version',[JDK/'bin/java','-version']);run('javac-version',[JDK/'bin/javac','-version'])
        sources=[frozen/r['path'] for r in roster if r['path'].endswith('.java')]+[D/'dynamic-source/FieldObservationControls.java']
        run('compile',[JDK/'bin/javac','--release','17','-proc:none','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources])
        actual={name:identity(classes/name) for name in class_map};assert actual==class_map,'all209 product class mismatch';actual_context=hashlib.sha256(json.dumps({'source_map':source_map,'class_map':actual},sort_keys=True,separators=(',',':')).encode()).hexdigest();assert actual_context==CONTEXT
        save(runroot/'actual-product-class-map.json',actual);save(runroot/'compile-identity.json',{'product_sources':16,'product_classes':209,'B_leaves':87,'selected_v4_derivative_files':8,'source_context':actual_context,'all_209_exact_matches':True,'BCI_remapping':False})
        run('field-observation-controls',[JDK/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.FieldObservationControls',inputs/'descriptor.json',runroot/'actual-results.json'])
        result=json.loads((runroot/'actual-results.json').read_bytes());assert result['invocations']==56 and result['actual_final_counts']==[0,0,0] and result['original_edit_completed_after_restores']
        assert result['host_threads_started']==result['host_threads_joined']==3 and result['failure_latch_clear'] and result['no_final_field_or_exhaustion_mutations']
        assert {r['subject_id'] for r in result['rows']}=={r['id'] for r in selected}
        assert all(r['counts_before']==r['counts_after']==[2,2,3] and r['restored_before_original_edit_resumes'] and r['no_membership_release_authority'] for r in result['rows'])
        save(runroot/'receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'independent-two-finite-recovery-controls-passed-no-qualification-credit','source_context':CONTEXT,'source_revision_context':source_revision,'results':identity(runroot/'actual-results.json'),'control':identity(D/'dynamic-source/FieldObservationControls.java'),'runner':identity(Path(__file__)),'invocations':result['invocations'],'checks':result['checks'],'host_environment':'macOS JDK17, exact product16/all209, unchanged original Fixture(true,true), B87 with accepted v4 instrumentation','actual_original_edit_completed_after_restores':True,'original_boundary_counts':[2,2,3],'actual_final_counts':[0,0,0],'bounded_host_threads_started_and_joined':3,'native_runtime_UI_capture_process_inventory_started':False,'physical_native_cleanup_credit':False,'full_matrix_canonical_membership_release_native_OTA_GA_accepted':False,'pending':['Root independent selection and producer exact method joins','All eight original semantic cases per subject and enclosing obligations retained pending','Runtime allocation failures, snapshot/Mutation allocation exceptional partial outputs','Exact Input invocation counts and BCI tracing; original final Input is unchanged', 'Unexecuted final-field identity/mode/fence/token, terminal and loss-exhaustion branches','Native runtime and physical checks remain paused']})
    except BaseException as failure:
        save(runroot/'failure.json',{'type':type(failure).__name__,'message':str(failure),'status':'actual-failed-attempt-no-pass-credit'});raise
    finally:
        shutil.rmtree(scratch);save(runroot/'cleanup.json',{'all_started_children_reaped':all(r['reaped'] for r in commands),'maximum_concurrent_children':1,'owned_scratch_removed':not scratch.exists(),'jdk_tool_lease_preserved':True,'native_instances_started':0,'process_inventory_or_other_projects_touched':False,'original_fixture_close_scope':'host disposal only; no physical cleanup credit'})
if __name__=='__main__':main()
