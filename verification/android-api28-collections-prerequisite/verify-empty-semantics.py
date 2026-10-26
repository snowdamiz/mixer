#!/usr/bin/env python3
"""Finite actual-JDK mismatch witness only, no Android/D8 helper execution."""
from pathlib import Path
import datetime, json, os, shutil, signal, subprocess, sys, tempfile
sys.dont_write_bytecode=True
import run as producer

packet=Path(__file__).resolve().parent
evidence=packet/'empty-mutation-witness'
if evidence.exists(): raise SystemExit('retain existing witness; choose a fresh packet')
evidence.mkdir()
scratch=Path(tempfile.mkdtemp(prefix='mixer-empty-mutation-witness-'))
commands=[];status='failed'
env=dict(os.environ)
for key in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH'):env.pop(key,None)
try:
    rows=[('compile',[producer.JDK/'javac','--release','17','-d',scratch,packet/'prototype/EmptyMutationOracle.java']),
          ('oracle',[producer.JDK/'java','-ea','-cp',scratch,'dev.mixer.android.EmptyMutationOracle'])]
    for label,argv in rows:
        child=subprocess.Popen([str(v) for v in argv],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True)
        timeout=False
        try:out,err=child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timeout=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (evidence/(label+'.stdout')).write_bytes(out);(evidence/(label+'.stderr')).write_bytes(err)
        commands.append({'argv':[str(v) for v in argv],'exit_code':child.returncode,'timed_out':timeout,'owned_child_reaped':True})
        if timeout or child.returncode:raise RuntimeError(label)
    status='passed-JVM-exception-mismatch-witness-only'
finally:
    shutil.rmtree(scratch)
    (evidence/'receipt.json').write_text(json.dumps({'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv':sys.argv,'python':sys.version,'status':status,'commands':commands,'assertions':8 if status.startswith('passed') else None,
        'source':producer.identity(packet/'prototype/EmptyMutationOracle.java'),
        'owned_scratch_removed':not scratch.exists(),'native_runtime_or_process_inventory':False,
        'scope':'Four observed JDK25 empty-mutator exception mismatches; not API28 runtime evidence'},indent=2)+'\n')
print(status)
