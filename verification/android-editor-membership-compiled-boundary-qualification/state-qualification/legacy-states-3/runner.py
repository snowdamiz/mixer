from pathlib import Path
import os,sys,subprocess,json,hashlib,time,signal,shutil,tempfile,datetime
D=Path(__file__).resolve().parent;Q=D.parent;R=Q.parents[1];C=D/'context17-1';jdk=Path(json.loads((D/'jdk17-download-receipt.json').read_bytes())['jdk_home']);env=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(k,None)
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
i=1
while (D/f'legacy-states-{i}').exists():i+=1
E=D/f'legacy-states-{i}';E.mkdir();scratch=Path(tempfile.mkdtemp(prefix='owned-legacy-states-',dir=E));empty=scratch/'empty';empty.mkdir();classes=scratch/'classes';classes.mkdir();commands=[]
def run(label,argv):
 start=time.monotonic()
 with (E/(label+'.stdout')).open('wb') as o,(E/(label+'.stderr')).open('wb') as e:
  p=subprocess.Popen([str(a) for a in argv],stdout=o,stderr=e,cwd=R,env=env,start_new_session=True);timeout=False
  try:p.wait(timeout=60)
  except subprocess.TimeoutExpired:timeout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
 commands.append({'label':label,'argv':[str(a) for a in argv],'exit':p.returncode,'timeout':timeout,'timeout_seconds':60,'elapsed_seconds':time.monotonic()-start,'stdout':ident(E/(label+'.stdout')),'stderr':ident(E/(label+'.stderr')),'reaped':True});save(E/'commands.json',commands);print(label,'exit',p.returncode,flush=True);return p.returncode
try:
 for name in ('DirectBoundaryStates.java','LegacyBoundaryStates.java'):shutil.copy2(D/name,E/name)
 shutil.copy2(D/'run_legacy_states.py',E/'runner.py');save(E/'source-freeze.json',{'product_context':json.loads((C/'product-context.json').read_bytes())['context_id'],'product_class_map':ident(C/'class-map.json'),'legacy_bindings':ident(C/'legacy189-bindings.json'),'harnesses':{n:ident(E/n) for n in ('DirectBoundaryStates.java','LegacyBoundaryStates.java')},'scope':'Actual callback-scope and failure-state stimuli, not full original nonvoid result qualification'})
 assert run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',C/'classes','-sourcepath',empty,'-d',classes,E/'DirectBoundaryStates.java',E/'LegacyBoundaryStates.java'])==0;shutil.copytree(classes,E/'classes')
 allrows=json.loads((C/'legacy189-bindings.json').read_bytes())['records'];selected=[r for r in allrows if r['discovered_entry_and_return']]
 if sys.argv[1:]:selected=[r for r in selected if r['historical_id'] in sys.argv[1:]]
 for item in selected:
  hid=item['historical_id'];label='boundary-'+str(allrows.index(item)).zfill(3);binding=E/(label+'.binding.json');save(binding,{'records':[{k:item[k] for k in ('historical_id','original_boundary','fresh_compiled_candidates','witness_scenarios')}]});run(label,[jdk/'bin/java','-ea','-Xmx512m','-cp',str(classes)+os.pathsep+str(C/'classes'),'dev.mixer.android.LegacyBoundaryStates',Q/'inputs/accepted/descriptor.json',binding,hid,E/(label+'.rows.jsonl.gz')])
finally:
 shutil.rmtree(scratch);save(E/'receipt.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'all_subprocesses_passed':all(c['exit']==0 and not c['timeout'] for c in commands),'scope':'Callback scope/state coverage only. Original nonvoid/helper outcomes and independent semantic review remain pending.','cleanup':{'scratch_removed':not scratch.exists(),'all_children_reaped':all(c['reaped'] for c in commands),'native_UI_capture_or_process_inventory':False}})
