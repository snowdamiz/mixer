#!/usr/bin/env python3
from pathlib import Path
import os,sys,subprocess,json,hashlib,time,signal,shutil,tempfile,datetime
D=Path(__file__).resolve().parent;Q=D.parent;R=Q.parents[1];jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');env=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
i=1
while (D/f'run-{i}').exists():i+=1
E=D/f'run-{i}';E.mkdir();commands=[];scratch=Path(tempfile.mkdtemp(prefix='owned-state-qualification-',dir=E));empty=scratch/'empty';empty.mkdir();classes=scratch/'classes';classes.mkdir();temp=scratch/'tmp';temp.mkdir();env.update({'TMPDIR':str(temp),'TMP':str(temp),'TEMP':str(temp)})
def run(name,args):
 start=time.monotonic()
 with (E/(name+'.stdout')).open('wb') as o,(E/(name+'.stderr')).open('wb') as e:
  p=subprocess.Popen([str(a) for a in args],stdout=o,stderr=e,cwd=R,env=env,start_new_session=True);timedout=False
  try:p.wait(timeout=60)
  except subprocess.TimeoutExpired:timedout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
 c={'name':name,'argv':[str(a) for a in args],'exit':p.returncode,'timeout':timedout,'timeout_seconds':60,'elapsed_seconds':time.monotonic()-start,'stdout':ident(E/(name+'.stdout')),'stderr':ident(E/(name+'.stderr')),'reaped':True};commands.append(c);save(E/'commands.json',commands);print(name,'exit',p.returncode,flush=True);return p.returncode
try:
 shutil.copy2(D/'DirectBoundaryStates.java',E/'DirectBoundaryStates.java');shutil.copy2(D/'run_states.py',E/'runner.py');save(E/'source-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'product_source_tree':'a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4','compiled_host_class_map':ident(Q/'runs/host-2/class-map.json'),'supplementary_harness':ident(E/'DirectBoundaryStates.java'),'runner':ident(E/'runner.py'),'unmodified_product_and_original_assertions':True})
 rc=run('compile',[jdk/'bin/javac','--release','17','-g','-Xlint:all','-Werror','-proc:none','-classpath',Q/'runs/host-2/classes','-sourcepath',empty,'-d',classes,E/'DirectBoundaryStates.java']);assert rc==0
 shutil.copytree(classes,E/'classes');families=sys.argv[1:] or [r['family'] for r in json.loads((Q/'inputs/protocol/family-migration.json').read_bytes())['families']]
 for family in families:run(family,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',str(classes)+os.pathsep+str(Q/'runs/host-2/classes'),'dev.mixer.android.DirectBoundaryStates',Q/'inputs/accepted/descriptor.json',family,E/(family+'.rows.jsonl.gz')])
finally:
 shutil.rmtree(scratch);save(E/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'scope':'Supplementary direct editor states using exact retained accepted product classfiles and unchanged original fixture; host mechanical leaves only','all_commands_passed':all(c['exit']==0 and not c['timeout'] for c in commands),'cleanup':{'scratch_removed':not scratch.exists(),'all_children_reaped':all(c['reaped'] for c in commands),'native_UI_capture_or_process_inventory':False}})
