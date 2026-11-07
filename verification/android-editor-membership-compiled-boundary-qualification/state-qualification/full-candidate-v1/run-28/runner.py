from pathlib import Path
import os,sys,json,hashlib,shutil,subprocess,signal,time,tempfile,datetime,collections
D=Path(__file__).resolve().parent;S=D.parent;Q=S.parent;R=Q.parents[1];P=Q/'passive-return-probe-v4';jdk=Path(json.loads((S/'jdk17-download-receipt.json').read_bytes())['jdk_home'])
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
 sources=sorted((P/'inputs/source').glob('*.java'))+sorted((P/'inputs/host-leaves').rglob('*.java'))+sorted((P/'inputs/tests').glob('*.java'))+[S/'final-selected-support/NativeOwnerV2ConcreteHostTests.java']+sorted(D.glob('*.java'))
 for p in D.glob('*.java'):shutil.copy2(p,E/p.name)
 shutil.copy2(__file__,E/'runner.py');save(E/'source-freeze.json',{'sources':[{'path':str(p.relative_to(R)),**ident(p)} for p in sources],'passive_derivative_seal':ident(P/'seal.json'),'product_context_id':'1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd','flags':['--release','17','-Xlint:all','-Werror','-proc:none','-classpath','<empty>','-sourcepath','<empty>'],'tools':{str(p.relative_to(jdk)):ident(p) for p in (jdk/'bin/java',jdk/'bin/javac',jdk/'lib/modules',jdk/'lib/server/libjvm.dylib')},'environment':env,'scope':'Candidate replay; independent derivative and full semantic/execution closure review pending'})
 assert run('java-version',[jdk/'bin/java','-version'])==0
 assert run('javac-version',[jdk/'bin/javac','-version'])==0
 assert run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*sources])==0
 shutil.copytree(classes,E/'classes');save(E/'class-map.json',{str(p.relative_to(classes)):ident(p) for p in sorted(classes.rglob('*.class'))})
 sys.path.insert(0,str(Q));from classfile import parse
 products={str(p.relative_to(classes)):ident(p) for p in classes.rglob('*.class') if parse(p.read_bytes())['source_file'] in {p.name for p in (P/'inputs/source').glob('*.java')}};expected=json.loads((S/'context17-1/product-context.json').read_bytes())['class_map'];assert products==expected,'unreviewed actual product compiler context'
 save(E/'product-class-equality.json',{'product209_exact_context_1b71':True,'classes':products,'selected_support_source':ident(S/'final-selected-support/NativeOwnerV2ConcreteHostTests.java')})
 selector=sys.argv[1:] or ['all']
 if any(x in selector for x in ('all','original')):
  original_roster=json.loads((D/'selected-original-behavior-roster.json').read_bytes());shutil.copyfile(D/'selected-original-behavior-roster.json',E/'selected-original-behavior-roster.json')
  frozen_source=S/'final-selected-support/frozen-focus/FocusHistoryControls.java';(E/'frozen-focus').mkdir();shutil.copyfile(frozen_source,E/'frozen-focus/FocusHistoryControls.java');frozen_classes=scratch/'frozen-focus-classes';frozen_classes.mkdir()
  assert run('compile-frozen-focus',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',classes,'-sourcepath',empty,'-d',frozen_classes,frozen_source])==0
  shutil.copytree(frozen_classes,E/'frozen-focus/classes');save(E/'frozen-focus/class-map.json',{str(p.relative_to(frozen_classes)):ident(p) for p in sorted(frozen_classes.rglob('*.class'))})
  for n,item in enumerate(original_roster['cases']):
   source=R/item['source']['path'];assert ident(source)=={k:item['source'][k] for k in ('bytes','sha256')},'changed unchanged original control source'
   classpath=str(frozen_classes)+':'+str(classes) if item['variant']=='frozen-focus' else str(classes)
   argv=[P/'descriptor.json' if arg=='<descriptor>' else arg for arg in item['args']]
   run('original-'+str(n).zfill(3)+'-'+item['case_id'],[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classpath,item['class'],*argv])
 assert run('typed-snapshot-controls',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.TypedSnapshotControls'])==0
 assert run('observer-failure-controls',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.ObserverFailureControls'])==0
 assert run('event-join-controls',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.EventJoinControls'])==0
 if any(x in selector for x in ('all','direct','direct-extra')) or any(x.startswith('direct-family:') for x in selector):
  families=[] if 'direct-extra' in selector else [r['family'] for r in json.loads((Q/'inputs/protocol/family-migration.json').read_bytes())['families']]
  families+=['performContextMenuAction','reportFullscreenMode','requestCursorUpdates','requestCursorUpdatesFiltered']
  selected_families=[x.split(':',1)[1]for x in selector if x.startswith('direct-family:')]
  if selected_families:assert set(selected_families)<=set(families);families=selected_families
  for family in families:run('direct-'+family,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.DirectBoundaryStates',P/'descriptor.json',family,E/('direct-'+family+'.rows.jsonl.gz')])
 if any(x in selector for x in ('all','v1')):
  run('v1-original-assertions',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.OriginalV1Controls'])
  run('v1-exact-five',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.V1PositiveWitness',E/'v1-exact-five.json'])
 if any(x in selector for x in ('all','close')):run('direct-close',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.CloseBoundaryStates',P/'descriptor.json',E/'direct-close.rows.jsonl.gz'])
 if any(x in selector for x in ('all','finite')):run('direct-finite-38',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.DirectFiniteCases',P/'descriptor.json',E/'direct-finite-38.rows.jsonl.gz'])
 if any(x in selector for x in ('all','field-finite')):run('field-finite',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.FieldFiniteCases',P/'descriptor.json',E/'field-finite.rows.jsonl.gz'])
 if any(x in selector for x in ('all','unsupported')):run('unsupported-callbacks',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.UnsupportedCallbackStates',P/'descriptor.json',E/'unsupported-callbacks.rows.jsonl.gz'])
 if any(x in selector for x in ('all','scalar')):run('scalar-applicability',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.ScalarApplicabilityControls'])
 if any(x in selector for x in ('all','scalar')):run('typed-scalar-companions',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.TypedScalarControls',E/'actual-typed-scalars.json'])
 if any(x in selector for x in ('all','ledger')):run('finite-ledgers',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.FiniteLedgerControls',E/'actual-ledger-results.json'])
 if any(x in selector for x in ('all','renderer-finite')):run('finite-renderer-membership',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.FiniteMembershipControls',P/'descriptor.json',E/'actual-renderer-membership.json'])
 if any(x in selector for x in ('all','renderer-ledger-constructor')):run('finite-renderer-ledger-constructor',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.FiniteRendererLedgerConstructorControls',P/'descriptor.json',E/'actual-renderer-ledger-constructor.json',E/'renderer-ledger-constructor-snapshots.json',E/'renderer-ledger-constructor-boundary.json'])
 if any(x in selector for x in ('all','renderer-state-journal-constructors')):run('renderer-state-journal-constructors',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.ConstructorControls',P/'descriptor.json',E/'actual-renderer-state-journal-constructors.json'])
 if any(x in selector for x in ('all','lifecycle-finite')):run('finite-lifecycle-lambdas',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.NoInvokeLifecycleControls',P/'descriptor.json',E/'actual-lifecycle-lambdas.json'])
 if any(x in selector for x in ('all','query')):
  for family in ('getCursorCapsMode','getSelectedText','getTextBeforeCursor','getTextAfterCursor','getExtractedText','getSurroundingText','takeSnapshot'):run('query-'+family,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.QueryBoundaryStates',P/'descriptor.json',family,E/('query-'+family+'.rows.jsonl.gz')])
 allrows=json.loads((S/'context17-1/legacy189-bindings.json').read_bytes())['records']
 if any(x in selector for x in ('all','legacy')) or any(x.startswith('Native') for x in selector):
  for item in allrows:
   eligible=item['historical_id']=='NativeRenderer:L344:C98:1'
   if not (item['discovered_entry_and_return'] or eligible) or not ('all' in selector or 'legacy' in selector or item['historical_id'] in selector):continue
   byscenario=collections.defaultdict(set)
   for h in item['discovery_hits']:byscenario[h['scenario']].add(h['phase'])
   available=[s for s,phases in byscenario.items() if {'entry','beforeReturn'}<=phases];assert available or eligible
   item['selected_scenario']='eligible-toggle-rollback' if eligible else next(s for s in ('smoke','positive','hierarchy','rollback','rollbackState') if s in available)
   label='boundary-'+str(allrows.index(item)).zfill(3);binding=E/(label+'.binding.json');save(binding,{'records':[item]});run(label,[jdk/'bin/java','-Djava.io.tmpdir='+str(temp),'-ea','-Xmx512m','-cp',classes,'dev.mixer.android.LegacyBoundaryStates',P/'descriptor.json',binding,item['historical_id'],E/(label+'.rows.jsonl.gz')])
 status='passed-candidate-scope' if all(x['exit']==0 and not x['timeout'] for x in commands) else 'retained-candidate-failures'
finally:
 shutil.rmtree(scratch);save(E/'receipt.json',{'status':status,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'all_commands_passed':all(x['exit']==0 and not x['timeout'] for x in commands),'scope':'Actual after-original-hook candidate replay; no full policy/derivative/execution closure acceptance inferred','cleanup':{'scratch_removed':not scratch.exists(),'all_children_reaped':all(x['reaped'] for x in commands),'native_UI_capture_or_process_inventory':False}})
