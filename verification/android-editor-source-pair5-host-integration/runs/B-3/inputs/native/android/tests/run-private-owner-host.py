#!/usr/bin/env python3
"""Explicit profile5 host closures. Controlled leaves do not qualify native runtime."""
import argparse,datetime,hashlib,json,os,shutil,signal,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
STRIP=('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS','SWIFT_EXEC','SWIFT_DRIVER_SWIFT_FRONTEND_EXEC')
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
class BoundedRun:
 def __init__(self,evidence,root,env):self.evidence=evidence;self.root=root;self.env=env;self.commands=[]
 def run(self,label,argv,expect=0,contains=None):
  outpath=self.evidence/(label+'.stdout');errpath=self.evidence/(label+'.stderr');start=time.monotonic();timed=overflow=False
  with outpath.open('wb') as out,errpath.open('wb') as err:
   child=subprocess.Popen([str(x) for x in argv],cwd=self.root,env=self.env,stdout=out,stderr=err,start_new_session=True)
   try:
    while child.poll() is None:
     timed=time.monotonic()-start>60;overflow=max(outpath.stat().st_size,errpath.stat().st_size)>4_000_000
     if timed or overflow:os.killpg(child.pid,signal.SIGKILL);break
     time.sleep(.025)
   finally:
    if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
    child.wait()
  stdout=outpath.read_bytes();stderr=errpath.read_bytes();passed=not timed and not overflow and child.returncode==expect and (contains is None or contains in stdout+stderr)
  row={'label':label,'argv':[str(x) for x in argv],'exit':child.returncode,'expected_exit':expect,'timeout_seconds':60,'timeout':timed,'output_limit_bytes_each_stream':4_000_000,'output_limit_exceeded':overflow,'elapsed_seconds':time.monotonic()-start,'stdout':ident(stdout),'stderr':ident(stderr),'child_reaped':True,'passed':passed};self.commands.append(row);save(self.evidence/'commands.json',self.commands)
  if not passed:raise RuntimeError(label+' failed; see retained '+str(self.evidence))
  return stdout
 def reap_group(self):return all(c['child_reaped'] for c in self.commands)
def freeze(root,evidence,paths):
 if len(paths)!=len(set(paths)):raise RuntimeError('duplicate explicit source')
 frozen={p:(root/p).read_bytes() for p in paths}
 for p,b in frozen.items():q=evidence/'inputs'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
 source_map={p:ident(b) for p,b in frozen.items()};save(evidence/'source-map.json',source_map);save(evidence/'source-freeze.json',{'frozen_before_tools':True,'source_map':ident((evidence/'source-map.json').read_bytes()),'source_tree_sha256':hashlib.sha256(''.join(p+'\0'+source_map[p]['sha256']+'\n' for p in sorted(source_map)).encode()).hexdigest()});return frozen

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--closure',choices=('A','B'),default='B');p.add_argument('--jdk',type=Path,default=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'));p.add_argument('--matrix',type=Path);p.add_argument('--skip-matrix',action='store_true');p.add_argument('--preservation',action='store_true');a=p.parse_args()
 evidence=a.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False);roster_path='native/android/tests/private-owner-source-pair5-roster.json';roster=json.loads((ROOT/roster_path).read_text());closure=roster['closures']['A-orchestration' if a.closure=='A' else 'B-concrete-renderer-views']
 sources=closure['actual_production_sources']+[x['source'] for x in closure['substitutes']]+closure['test_support_sources']+[closure['test_source']]
 if a.preservation:
  if a.closure!='B':raise RuntimeError('preservation uses actual B only')
  sources+=roster['preservation_controls']
 descriptor='descriptor.json' if (ROOT/'descriptor.json').exists() else 'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
 auxiliary=[roster_path,'native/android/tests/run-private-owner-host.py',descriptor];frozen=freeze(ROOT,evidence,sources+auxiliary);save(evidence/'source-closure.json',{'sources':sources,'auxiliary':auxiliary,'A_models_editor_busy':False if a.closure=='A' else None,'legacy_matrix_requested':a.matrix is not None,'explicit_development_skip_matrix':a.skip_matrix})
 env=dict(os.environ)
 for k in STRIP:env.pop(k,None)
 scratch=Path(tempfile.mkdtemp(prefix='owned-profile5-host-',dir=evidence));tmp=scratch/'tmp';tmp.mkdir();env['TMPDIR']=str(tmp);env['TMP']=str(tmp);env['TEMP']=str(tmp)
 run=BoundedRun(evidence,ROOT,env);receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'closure':a.closure,'status':'failed','scope':'exact actual source host JVM with mechanical Android/JNI leaves','target_java_release':17,'native_or_capture_processes_started_or_queried':False}
 try:
  if a.matrix and a.skip_matrix:raise RuntimeError('matrix and scoped skip are mutually exclusive')
  if a.closure=='B' and not a.skip_matrix and a.matrix is None:raise RuntimeError('default requires root-selected fresh qualified sourcepair5 matrix; interface pending; use explicit --skip-matrix for scoped development only')
  receipt['matrix_status']='explicit-scoped-development-skip-pending' if a.skip_matrix else 'explicit-qualified-matrix-requested' if a.matrix else 'not-applicable-A-orchestration'
  jdk=a.jdk.resolve(strict=True);java=jdk/'bin/java';javac=jdk/'bin/javac';javap=jdk/'bin/javap';receipt['actual_tool_identities']={str(x):ident(x.resolve().read_bytes()) for x in (java,javac,javap,jdk/'lib/modules',jdk/'lib/server/libjvm.dylib') if x.exists()}
  run.run('javac-version',[javac,'-version']);run.run('java-version',[java,'-version']);run.run('javap-version',[javap,'-version'])
  classes=scratch/'classes';empty=scratch/'empty';classes.mkdir();empty.mkdir()
  run.run('compile',[javac,'-J-Djava.io.tmpdir='+str(tmp),'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*[evidence/'inputs'/s for s in sources]])
  shutil.copytree(classes,evidence/'classes');save(evidence/'class-map.json',{str(f.relative_to(classes)):ident(f.read_bytes()) for f in sorted(classes.rglob('*.class'))})
  inspection=['dev.mixer.android.NativeOwnerV2','dev.mixer.android.NativeCoordinatorV2'] if a.closure=='A' else ['dev.mixer.android.NativeRenderer','dev.mixer.android.NativeEnvironmentV2','dev.mixer.android.NativeEditorConnectionV2$Base','dev.mixer.android.NativeEditorConnectionV2$Api34','dev.mixer.android.NativeAppearanceViewsV2$Mutation']
  run.run('bytecode',[javap,'-c','-p','-s','-classpath',classes,*inspection])
  base=[java,'-Djava.io.tmpdir='+str(tmp),'-ea','-Xmx256m','-cp',classes];desc=evidence/'inputs'/descriptor;name='dev.mixer.android.NativeOwnerV2'+('Concrete' if a.closure=='B' else '')+'HostTests'
  hostargv=base+[name,desc,evidence/'observed-sites.txt']
  if a.matrix:
   if a.closure!='B':raise RuntimeError('concrete matrix requested for A')
   shutil.copy2(a.matrix,evidence/'qualified-matrix-input.json');hostargv += [evidence/'qualified-matrix-input.json',evidence/'barrier-cases.json']
  run.run('host',hostargv,contains=b'PASS ')
  if a.closure=='B':
   for section in ('imeControls','platformGuards','v1'):run.run(section,base+[name,desc,evidence/('sites-'+section+'.txt'),'--section',section,evidence/(section+'-rows.json')],contains=b'PASS ')
  if a.preservation:
   run.run('producer-52',base+['dev.mixer.android.EditorImplementationTests',desc],contains=b'PASS ')
   groups={
    'ReplacementReviewControls':('admission-order','positive-values','foreign-dispatch','selection-postevent','annotation-mutable-bundle','snapshot-reservation'),
    'AdditionalReplacementControls':('final-balance','tuple-after-getter','captured-target','blurred-A-replacement','focused-B-echo-after-A-blur'),
    'FocusHistoryControls':('positive-history','entry-loss','stage-loss','other-denials','marker-exhaustion','preservation-callback','first-fatal-busy','restoration','live-exhaustion','event-reentry','multiple-preservations','preservation-balance-fatal','scope-custody'),
    'IndependentFocusHistoryControls':('prior-focus-values','coexistence','eligible-restore','lost-original-restore','foreign-token-restore','loss-phases','settled-loss-phases','observed-hooks','event-reentry','event-postgetter','scope-imbalance','exhaustion','post-attach-rollback','cross-renderer-end'),
    'IndependentAdditionalFocusAuditControls':('multiple-with-active-B','event-provenance'),
    'PreservationCompletionControls':('outcomes','refresh','no-scopes','partial-entry','partial-release','chronology','foreign-endpoints','terminal-end','imbalances','getter-loss','begin-accounting','precommit-refusals'),
    'PreservationMembershipControls':('finish-membership','failed-membership','precommit-membership','endpoint-membership','report-reentry-membership','healthy'),
    'SelectedIdentityMembershipReviewControls':('fixture-smoke','three-success','three-known-rejections','outcome-failures','refresh-zero-count','no-scope','pre-attach-no-original','captured-A-refusal','partial-A-entered-C-refusal','constructor-before-registration','malformed-custody','fatal-chronology','foreign-replay','progress-states','cohort-preflight','identity-matrix','getter-suffix-matrix','journal-membership'),
    'IndependentOwnForwardControls':('native','commit')}
   for cls,cases in groups.items():
    for case in cases:run.run(cls+'-'+case,base+['dev.mixer.android.'+cls,case,desc],contains=b'PASS ')
   run.run('preserved-original-own-forward-expectation',base+['dev.mixer.android.IndependentPreservationCompletionControls','identity-matrix',desc],expect=1,contains=b'identity forward/native changed cancelClaim')
   run.run('descriptors-38',base+['DescriptorClosure','dev.mixer.android.NativeEditorConnectionV2$Api34'],contains=b'descriptor closure: 38;')
  receipt['status']='passed-host-only';print('PASS profile5 closure '+a.closure+'; actual JDK version recorded separately from release17; native runtime pending')
 except BaseException as failure:receipt['failure']={'type':type(failure).__name__,'message':str(failure)};raise
 finally:
  shutil.rmtree(scratch);receipt['cleanup']={'owned_scratch_removed':not scratch.exists(),'owned_children_reaped':run.reap_group(),'native_instances_created':False};receipt['source_stable']=all((ROOT/p).read_bytes()==b for p,b in frozen.items());receipt['pending']=['fresh combined compiled boundary acceptance unless supplied explicitly','native runtime/IME/keyboard/focus/accessibility/physical phones','immutable external FieldLog packages','public V2/OTA/store/operations/GA'];save(evidence/'receipt.json',receipt)
if __name__=='__main__':main()
