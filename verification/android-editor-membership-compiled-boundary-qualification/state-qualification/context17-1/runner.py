#!/usr/bin/env python3
"""Normal no-g JDK17 exact-source context. All subprocesses are bounded to60 seconds."""
from pathlib import Path
import os,sys,subprocess,json,hashlib,time,signal,shutil,tempfile,datetime
D=Path(__file__).resolve().parent;Q=D.parent;R=Q.parents[1];jdk=Path(json.loads((D/'jdk17-download-receipt.json').read_bytes())['jdk_home']);env=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
env['JAVA_HOME']=str(jdk);env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','')
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
i=1
while (D/f'context17-{i}').exists():i+=1
E=D/f'context17-{i}';E.mkdir();commands=[];scratch=Path(tempfile.mkdtemp(prefix='owned-context17-',dir=E));empty=scratch/'empty';empty.mkdir();classes=scratch/'classes';classes.mkdir();temp=scratch/'tmp';temp.mkdir();env.update({'TMPDIR':str(temp),'TMP':str(temp),'TEMP':str(temp)});status='failed'
def run(name,args):
 start=time.monotonic()
 with (E/(name+'.stdout')).open('wb') as o,(E/(name+'.stderr')).open('wb') as e:
  p=subprocess.Popen([str(a) for a in args],stdout=o,stderr=e,cwd=R,env=env,start_new_session=True);timedout=False
  try:p.wait(timeout=60)
  except subprocess.TimeoutExpired:timedout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
 c={'name':name,'argv':[str(a) for a in args],'exit':p.returncode,'timeout':timedout,'timeout_seconds':60,'elapsed_seconds':time.monotonic()-start,'stdout':ident(E/(name+'.stdout')),'stderr':ident(E/(name+'.stderr')),'reaped':True};commands.append(c);save(E/'commands.json',commands);print(name,'exit',p.returncode,flush=True);return p.returncode
try:
 sources=sorted((Q/'inputs/accepted/source').glob('*.java'));sources += [p for p in sorted((Q/'inputs/accepted/host-leaves').rglob('*.java')) if p.name!='ConcreteHostProbe.java'];sources += sorted((Q/'inputs/accepted/tests').glob('*.java'))+[Q/'inputs/instrumentation/ConcreteHostProbe.java',Q/'TraceRunner.java',Q/'inputs/protocol/NativeOwnerV2ConcreteHostTests.java'];harnesses=sorted(D.glob('*.java'));sources+=harnesses
 for f in harnesses:shutil.copy2(f,E/f.name)
 shutil.copy2(D/'run_context.py',E/'runner.py');save(E/'source-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'product_source_tree':'a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4','flags':['--release','17','-Xlint:all','-Werror','-proc:none','-classpath','<empty>','-sourcepath','<empty>'],'explicit_sources':[{'path':str(p.relative_to(R)),**ident(p)} for p in sources],'compiler_runtime':'actual temporary official Temurin17, default debug information; not JDK25 --release17','tools':{str(p.relative_to(jdk)):ident(p) for p in (jdk/'bin/java',jdk/'bin/javac',jdk/'bin/javap',jdk/'lib/modules',jdk/'lib/server/libjvm.dylib')}})
 assert run('java-version',[jdk/'bin/java','-version'])==0;assert run('javac-version',[jdk/'bin/javac','-version'])==0
 assert run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*sources])==0
 shutil.copytree(classes,E/'classes');save(E/'class-map.json',{str(p.relative_to(classes)):ident(p) for p in sorted(classes.rglob('*.class'))})
 families=[r['family'] for r in json.loads((Q/'inputs/protocol/family-migration.json').read_bytes())['families']]
 for family in families:run('direct-'+family,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.DirectBoundaryStates',Q/'inputs/accepted/descriptor.json',family,E/('direct-'+family+'.rows.jsonl.gz')])
 for family in ('getCursorCapsMode','getSelectedText','getTextBeforeCursor','getTextAfterCursor','getExtractedText','getSurroundingText','takeSnapshot'):run('query-'+family,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.QueryBoundaryStates',Q/'inputs/accepted/descriptor.json',family,E/('query-'+family+'.rows.jsonl.gz')])
 for scenario in ('smoke','positive','hierarchy','rollback','rollbackState'):run('legacy-discovery-'+scenario,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.LegacyDiscovery',Q/'inputs/accepted/descriptor.json',scenario,E/('legacy-discovery-'+scenario+'.jsonl.gz')])
 status='passed-host17-scope' if all(c['exit']==0 and not c['timeout'] for c in commands) else 'retained-host17-failures'
finally:
 shutil.rmtree(scratch);save(E/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'status':status,'scope':'Supplementary direct/query states plus unchanged legacy discovery, exact accepted product classes, actual temporary Temurin17 normal no-g flags; host mechanical leaves only','all_commands_passed':all(c['exit']==0 and not c['timeout'] for c in commands),'cleanup':{'scratch_removed':not scratch.exists(),'all_children_reaped':all(c['reaped'] for c in commands),'owned_temporary_jdk_still_held_for_remaining_qualification':True,'native_UI_capture_or_process_inventory':False}})
