#!/usr/bin/env python3
"""Compile the frozen20 Java closure with the sealed consumer's exact javac/D8 flags only."""
from pathlib import Path
import datetime, json, os, shutil, signal, subprocess, sys, tempfile, time
sys.dont_write_bytecode=True
import run as producer

def main():
    packet=Path(__file__).resolve().parent
    evidence=packet/'consumer-flags'
    if evidence.exists(): raise SystemExit('retain previous consumer-flags evidence; choose a fresh packet')
    evidence.mkdir()
    scratch=Path(tempfile.mkdtemp(prefix='mixer-collections-consumer-flags-'))
    commands=[]; status='failed'
    env=dict(os.environ)
    for key in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH'): env.pop(key,None)
    env['JAVA_HOME']=str(producer.JDK.parent);env['PATH']=str(producer.JDK)+os.pathsep+env.get('PATH','')
    def run(label,argv):
        start=time.monotonic()
        child=subprocess.Popen([str(v) for v in argv],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed_out=False
        try: out,err=child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (evidence/(label+'.stdout')).write_bytes(out);(evidence/(label+'.stderr')).write_bytes(err)
        commands.append({'argv':[str(v) for v in argv],'exit_code':child.returncode,'seconds':time.monotonic()-start,
            'timed_out':timed_out,'owned_child_reaped':True})
        if timed_out or child.returncode: raise RuntimeError(label)
    try:
        classes=scratch/'classes';classes.mkdir();dex=scratch/'dex';dex.mkdir()
        sources=[packet/'inputs'/producer.JAVA_DIR/(name+'.java') for name in producer.JAVA]
        run('javac',[producer.JDK/'javac','--release','17','-Xlint:all','-Werror','-classpath',producer.ANDROID,'-d',classes,*sources])
        run('d8',[producer.D8,'--min-api','28','--lib',producer.ANDROID,'--output',dex,*sorted(classes.rglob('*.class'))])
        artifact=dex/'classes.dex'; refs=producer.dex_refs(artifact)
        previous=json.loads((packet/'attempt-1/dex-java-reference-ids.json').read_text())
        # JSON arrays and Python tuples compare through canonical JSON to avoid a representation mismatch.
        assert json.loads(json.dumps(refs))==previous,'consumer flags changed the finite Java reference closure'
        shutil.copyfile(artifact,evidence/'classes.dex')
        (evidence/'dex-java-reference-ids.json').write_text(json.dumps(refs,indent=2,sort_keys=True)+'\n')
        status='passed-exact-javac-D8-flags-source-only'
    finally:
        shutil.rmtree(scratch)
        (evidence/'receipt.json').write_text(json.dumps({'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'argv':sys.argv,'python':sys.version,'status':status,'commands':commands,'owned_scratch_removed':not scratch.exists(),
            'same_170_Java_member_and_60_type_reference_closure':status.startswith('passed'),
            'frozen_source_count':20,'generated_app_or_APK_built':False,'native_execution_or_process_inventory':False,
            'scope':'Exact consumer javac/D8 flags over frozen Java20 only; no Swift/JNI/package/signing or runtime proof'},indent=2)+'\n')
    print(status)

if __name__=='__main__':main()
