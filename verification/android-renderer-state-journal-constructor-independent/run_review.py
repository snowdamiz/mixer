#!/usr/bin/env python3
"""Independent bounded replay; reads only the sealed packet, its named frozen closure and leased JDK."""
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
P = ROOT/'verification/android-renderer-state-journal-constructor-controls'
EXPECTED = 'd134612993dd5d2071c55e2f63c2ee93fbaea503f5123e146a839ee89354a279'
CONTEXT = '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'

def identity(path):
    value=path.read_bytes()
    return {'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}

def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')

def verify(packet,expected):
    assert identity(packet/'seal.json')['sha256']==expected
    seal=json.loads((packet/'seal.json').read_bytes())
    members=seal['members']
    if isinstance(members,dict):members=[{'path':name,**value} for name,value in members.items()]
    names=[]
    for row in members:
        path=Path(row['path'])
        assert not path.is_absolute() and '..' not in path.parts and not (packet/path).is_symlink()
        assert identity(packet/path)=={'bytes':row['bytes'],'sha256':row['sha256']},str(packet/path)
        names.append(row['path'])
    assert len(names)==len(set(names))
    return {'path':str(packet.relative_to(ROOT)),'seal':identity(packet/'seal.json'),'members':len(names),'bytes':sum(row['bytes'] for row in members)}

def main():
    run=D/sys.argv[1];run.mkdir()
    scratch=run/'scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
    commands=[];environment=dict(os.environ)
    for name in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):environment.pop(name,None)
    def command(name,argv):
        out=run/(name+'.stdout');err=run/(name+'.stderr');start=time.monotonic()
        with out.open('wb') as stdout,err.open('wb') as stderr:
            child=subprocess.Popen([str(x) for x in argv],cwd=D,env=environment,stdout=stdout,stderr=stderr,start_new_session=True)
            timeout=False
            try:child.wait(timeout=60)
            except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        row={'name':name,'argv':[str(x) for x in argv],'cwd':str(D),'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed_seconds':time.monotonic()-start,'stdout':{'path':out.name,**identity(out)},'stderr':{'path':err.name,**identity(err)}}
        commands.append(row);save(run/'commands.json',commands);print(name,child.returncode,flush=True)
        assert child.returncode==0 and not timeout
    try:
        shutil.copyfile(Path(__file__),run/'run_review.py');shutil.copyfile(D/'IndependentConstructorControls.java',run/'IndependentConstructorControls.java')
        custody=[verify(P,EXPECTED)]
        assert custody[0]['members']==152 and custody[0]['bytes']==2814411
        actual_names={str(x.relative_to(P)) for x in P.rglob('*') if x.is_file() and x.name!='seal.json'}
        frozen_names={r['path'] for r in json.loads((P/'seal.json').read_bytes())['members']}
        assert actual_names==frozen_names,'producer packet has unsealed extra/missing files'
        provenance=json.loads((P/'run-3/provenance.json').read_bytes())
        for row in provenance['frozen_inputs']:
            custody.append(verify(ROOT/row['path'],row['seal']['sha256']))
        acceptance=provenance['root_v4_acceptance'];assert identity(ROOT/acceptance['path'])=={k:acceptance[k] for k in ('bytes','sha256')}
        roster=json.loads((P/'inputs/source-roster.json').read_bytes())
        for row in roster:assert identity(P/row['path'])=={k:row[k] for k in ('bytes','sha256')}
        product=json.loads((P/'inputs/selected-product-source-map.json').read_bytes());expected_classes=json.loads((P/'inputs/selected-product-class-map.json').read_bytes())
        assert len(product)==16 and len(expected_classes)==209
        assert hashlib.sha256(json.dumps({'source_map':product,'class_map':expected_classes},sort_keys=True,separators=(',',':')).encode()).hexdigest()==CONTEXT
        assert identity(P/'ConstructorControls.java')==identity(P/'run-3/ConstructorControls.java')
        assert identity(P/'run_controls.py')==identity(P/'run-3/run_controls.py')
        jdk=ROOT/provenance['tool_lease']
        for name,expected in provenance['tools'].items():assert identity(jdk/name)==expected
        tool_map={name:identity(jdk/name) for name in (*provenance['tools'],'bin/javap')}
        save(run/'provenance.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform(),'launch':[sys.executable,'-B',str(Path(__file__)),sys.argv[1]],'source_context':CONTEXT,'source_revision_context':provenance['source_revision_context'],'producer':custody[0],'named_frozen_closure':custody[1:],'selected_source':identity(P/'ConstructorControls.java'),'independent_source':identity(D/'IndependentConstructorControls.java'),'runner':identity(Path(__file__)),'tools':tool_map,'jdk_lease':str(jdk.relative_to(ROOT)),'lease_scope':'read/execute only exact JDK installation','debug':'default javac debug; no -g/no -g:none','native_runtime_UI_capture_process_inventory_started':False})
        command('java-version',[jdk/'bin/java','-version']);command('javac-version',[jdk/'bin/javac','-version'])
        sources=[P/row['path'] for row in roster if row['path'].endswith('.java')]+[P/'ConstructorControls.java',D/'IndependentConstructorControls.java']
        command('compile',[jdk/'bin/javac','--release','17','-proc:none','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources])
        actual={name:identity(classes/name) for name in expected_classes};assert actual==expected_classes
        save(run/'actual-product-class-map.json',actual)
        save(run/'compile-identity.json',{'source_context':CONTEXT,'all_209_exact_matches':True,'sources':16,'B_leaves':87,'selected_v4_derivatives':8,'no_BCI_remap':True})
        command('producer-replay',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.ConstructorControls',P/'inputs/descriptor.json',run/'producer-results.json'])
        original=json.loads((P/'run-3/actual-results.json').read_bytes());replayed=json.loads((run/'producer-results.json').read_bytes())
        assert replayed==original,'exact producer result replay differs'
        command('independent-cases',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.IndependentConstructorControls',P/'inputs/descriptor.json',run/'independent-results.json'])
        command('constructor-bytecode',[jdk/'bin/javap','-p','-c','-s','-l','-classpath',classes,'dev.mixer.android.NativeRenderer$NativeState','dev.mixer.android.NativeRenderer$AttachmentJournal'])
        save(run/'receipt.json',{'status':'host-replay-and-three-independent-cases-pass','producer_result_exact_match':True,'source_context':CONTEXT,'producer_invocations':85,'producer_checks':replayed['checks'],'independent_cases':3,'independent_checks':json.loads((run/'independent-results.json').read_bytes())['checks'],'custody':custody,'original_callback_counts':[2,2,3],'final_counts':[0,0,0],'host_only':True})
    except BaseException as failure:
        save(run/'failure.json',{'type':type(failure).__name__,'message':str(failure),'status':'failed-attempt-retained-no-pass-credit'});raise
    finally:
        shutil.rmtree(scratch)
        save(run/'cleanup.json',{'all_started_children_reaped':all(row['reaped'] for row in commands),'max_concurrent_children':1,'owned_scratch_removed':not scratch.exists(),'leased_JDK_preserved':True,'native_instances_started':0,'UI_capture_process_inventory':False,'other_projects_touched':False,'fixture_close':'original fixture close may catch host disposal errors; no physical cleanup credit'})

if __name__=='__main__':main()
