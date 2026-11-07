from pathlib import Path
import os,sys,json,hashlib,shutil,subprocess,signal,time,tempfile,datetime,collections
D=Path(__file__).resolve().parent;S=D.parent;Q=S.parent;R=Q.parents[1];P=Q/'passive-return-probe-v3';jdk=Path(json.loads((S/'jdk17-download-receipt.json').read_bytes())['jdk_home'])
if (D/'seal.json').exists():raise SystemExit('frozen producer source; prepare owned replay child')
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
i=1
while (D/f'run-{i}').exists():i+=1
E=D/f'run-{i}';E.mkdir();scratch=Path(tempfile.mkdtemp(prefix='owned-full-state-',dir=E));classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir();temp=scratch/'tmp';temp.mkdir();commands=[];status='failed'
# No inherited JVM/Python/classpath/tool-option injection reaches child processes.
env={'PATH':str(jdk/'bin')+':/usr/bin:/bin','JAVA_HOME':str(jdk),'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC','TMPDIR':str(temp),'TMP':str(temp),'TEMP':str(temp)}
def run(label,argv):
 start=time.monotonic()
 with (E/(label+'.stdout')).open('wb') as o,(E/(label+'.stderr')).open('wb') as e:
  child=subprocess.Popen([str(x) for x in argv],cwd=R,env=env,stdout=o,stderr=e,start_new_session=True);timed=False
  try:child.wait(timeout=60)
  except subprocess.TimeoutExpired:timed=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
  except BaseException:
   os.killpg(child.pid,signal.SIGKILL);child.wait();raise
 commands.append({'label':label,'argv':[str(x) for x in argv],'exit':child.returncode,'timeout':timed,'timeout_seconds':60,'elapsed_seconds':time.monotonic()-start,'stdout':ident(E/(label+'.stdout')),'stderr':ident(E/(label+'.stderr')),'reaped':True});save(E/'commands.json',commands);print(label,'exit',child.returncode,flush=True);return child.returncode
try:
 sources=sorted((P/'inputs/source').glob('*.java'))+sorted((P/'inputs/host-leaves').rglob('*.java'))+sorted((P/'inputs/tests').glob('*.java'))+[Q/'inputs/protocol/NativeOwnerV2ConcreteHostTests.java']+sorted(D.glob('*.java'))
 for p in D.glob('*.java'):shutil.copy2(p,E/p.name)
 shutil.copy2(__file__,E/'runner.py');save(E/'source-freeze.json',{'sources':[{'path':str(p.relative_to(R)),**ident(p)} for p in sources],'passive_derivative_seal':ident(P/'seal.json'),'product_context_id':'1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd','flags':['--release','17','-Xlint:all','-Werror','-proc:none','-classpath','<empty>','-sourcepath','<empty>'],'tools':{str(p.relative_to(jdk)):ident(p) for p in (jdk/'bin/java',jdk/'bin/javac',jdk/'lib/modules',jdk/'lib/server/libjvm.dylib')},'environment':env,'scope':'Candidate replay; independent derivative and full semantic/execution closure review pending'})
 assert run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*sources])==0
 shutil.copytree(classes,E/'classes');save(E/'class-map.json',{str(p.relative_to(classes)):ident(p) for p in sorted(classes.rglob('*.class'))})
 selector=sys.argv[1:] or ['all']
 assert run('typed-snapshot-controls',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.TypedSnapshotControls'])==0
 if any(x in selector for x in ('all','direct','direct-extra')):
  families=[] if 'direct-extra' in selector else [r['family'] for r in json.loads((Q/'inputs/protocol/family-migration.json').read_bytes())['families']]
  families+=['performContextMenuAction','reportFullscreenMode','requestCursorUpdates','requestCursorUpdatesFiltered']
  for family in families:run('direct-'+family,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.DirectBoundaryStates',P/'descriptor.json',family,E/('direct-'+family+'.rows.jsonl.gz')])
 if any(x in selector for x in ('all','query')):
  for family in ('getCursorCapsMode','getSelectedText','getTextBeforeCursor','getTextAfterCursor','getExtractedText','getSurroundingText','takeSnapshot'):run('query-'+family,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.QueryBoundaryStates',P/'descriptor.json',family,E/('query-'+family+'.rows.jsonl.gz')])
 allrows=json.loads((S/'context17-1/legacy189-bindings.json').read_bytes())['records']
 if any(x in selector for x in ('all','legacy')) or any(x.startswith('Native') for x in selector):
  for item in allrows:
   if not item['discovered_entry_and_return'] or not ('all' in selector or 'legacy' in selector or item['historical_id'] in selector):continue
   byscenario=collections.defaultdict(set)
   for h in item['discovery_hits']:byscenario[h['scenario']].add(h['phase'])
   available=[s for s,phases in byscenario.items() if {'entry','beforeReturn'}<=phases];assert available
   item['selected_scenario']=next(s for s in ('smoke','positive','hierarchy','rollback','rollbackState') if s in available)
   label='boundary-'+str(allrows.index(item)).zfill(3);binding=E/(label+'.binding.json');save(binding,{'records':[item]});run(label,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.LegacyBoundaryStates',P/'descriptor.json',binding,item['historical_id'],E/(label+'.rows.jsonl.gz')])
 status='passed-candidate-scope' if all(x['exit']==0 and not x['timeout'] for x in commands) else 'retained-candidate-failures'
finally:
 shutil.rmtree(scratch);save(E/'receipt.json',{'status':status,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'all_commands_passed':all(x['exit']==0 and not x['timeout'] for x in commands),'scope':'Actual after-original-hook candidate replay; no full policy/derivative/execution closure acceptance inferred','cleanup':{'scratch_removed':not scratch.exists(),'all_children_reaped':all(x['reaped'] for x in commands),'native_UI_capture_or_process_inventory':False}})
