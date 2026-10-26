#!/usr/bin/env python3
"""Exact baseline/patch/compiled-return audit and independent original-leaf branch replay."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,signal,subprocess,sys,time
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;P=D/'input-v2';ROOT=D.parents[1]
HOST=ROOT/'android-editor-source-pair5-host-integration'
JDK=Path(json.loads((D.parent/'preaccess/tool-context-jdk17/provenance.json').read_bytes())['JDK_home'])
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
seal=HOST/'seal.json';assert identity(seal)['sha256']=='c356544da794b1ae630ec2bb4522f8a9ed93fe1aedb9958676dc84f27188733a'
hostseal=json.loads(seal.read_bytes());assert identity(HOST/'manifest.json')==hostseal['manifest']
manifest=json.loads((HOST/'manifest.json').read_bytes());frozen={r['path']:r for r in manifest['members']}
base=HOST/'candidate/native/android/tests/NativeOwnerV2ConcreteHostLeaves'
baseline={p.relative_to(base).as_posix():p for p in base.rglob('*.java')};assert len(baseline)==86
derivative={p.relative_to(P/'inputs/host-leaves').as_posix():p for p in (P/'inputs/host-leaves').rglob('*.java')}
assert set(derivative)-set(baseline)=={'dev/mixer/android/NativeOutcomeProbe.java'}
changed=[]
for relative,p in baseline.items():
 expected=frozen[p.relative_to(HOST).as_posix()];assert identity(p)=={k:expected[k] for k in ('bytes','sha256')}
 if p.read_bytes()!=derivative[relative].read_bytes():changed.append(relative)
expected_changes={'dev/mixer/android/ConcreteHostProbe.java','android/view/View.java','android/view/ViewGroup.java','android/widget/TextView.java','android/widget/EditText.java','android/widget/Switch.java','android/view/inputmethod/BaseInputConnection.java'}
assert set(changed)==expected_changes
spec=importlib.util.spec_from_file_location('independent_derivative_classfile',D.parent/'preaccess/interface-v3/classfile.py');cf=importlib.util.module_from_spec(spec);spec.loader.exec_module(cf)
returns=json.loads((P/'selected-return-sites.json').read_bytes());verified_methods=verified_returns=0
for leaf in returns['Android_leaves']:
 original=baseline[leaf['path']].read_text();expected=original;edits=[];name=Path(leaf['path']).stem
 clazz=cf.parse((D/'run-corrected/classes'/Path(leaf['path']).with_suffix('.class')).read_bytes())
 for m in leaf['methods']:
  actual=[v for v in clazz['methods'] if v['name']==m['method'] and v['descriptor']==m['descriptor']];assert len(actual)==1
  calls=[i for i in actual[0]['instructions'] if i.get('target',{}).get('owner')=='dev/mixer/android/NativeOutcomeProbe' and i['target']['name']=='returned']
  assert len(calls)==len(m['return_sites']);verified_methods+=1
  for site in m['return_sites']:
   start,end=site['start_offset'],site['end_offset'];expr=site['original_expression'];assert original[start:end]==expr
   edits.append((start,end,'dev.mixer.android.NativeOutcomeProbe.returned('+json.dumps(name+'.'+m['method'])+','+json.dumps(m['descriptor'])+',this,'+expr+')'));verified_returns+=1
 for start,end,replacement in sorted(edits,reverse=True):expected=expected[:start]+replacement+expected[end:]
 assert expected==derivative[leaf['path']].read_text(),leaf['path']
assert verified_methods==58 and verified_returns==64
probe=derivative['dev/mixer/android/ConcreteHostProbe.java'].read_text();assert 'auditSink' not in probe
roster=json.loads((P/'derivative-source-roster.json').read_bytes());assert roster['exact_file_count']==8
for row in roster['records']:
 assert identity(derivative[row['path']])==row['derivative']
 # Probe's packet baseline is an older3780B source; actual root-custodied3807B comparison is above.
 if row.get('accepted_original') is not None:
  assert identity(P/'original'/row['path'])==row['accepted_original']
out=D/'branch-and-baseline-review';out.mkdir();scratch=out/'scratch';scratch.mkdir();classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir();logs=[]
environment=dict(os.environ)
for k in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):environment.pop(k,None)
def run(name,argv):
 start=time.monotonic();stdout=out/(name+'.stdout');stderr=out/(name+'.stderr')
 with stdout.open('wb') as o,stderr.open('wb') as e:
  child=subprocess.Popen([str(x) for x in argv],cwd=D,stdout=o,stderr=e,env=environment,start_new_session=True)
  timeout=False
  try:child.wait(timeout=60)
  except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
 logs.append({'name':name,'argv':[str(x) for x in argv],'exit':child.returncode,'timeout':timeout,'reaped':True,'elapsed':time.monotonic()-start,'stdout':identity(stdout),'stderr':identity(stderr)});save(out/'commands.json',logs);assert child.returncode==0 and not timeout
 return stdout.read_bytes()
try:
 sources=sorted((P/'inputs/source').glob('*.java'))+sorted(baseline.values())+[P/'LeafBranchWitness.java']
 save(out/'baseline-source-closure.json',{'source16_and_accepted_host86_and_witness':[{'path':str(p),**identity(p)} for p in sources]})
 run('compile-actual-root-baseline',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',empty,'-d',classes,*sources])
 original=run('branch-actual-root-baseline',[JDK/'bin/java','-ea','-cp',classes,'dev.mixer.android.LeafBranchWitness'])
 amended=run('branch-independent-fresh-derivative',[JDK/'bin/java','-ea','-cp',D/'run-corrected/classes','dev.mixer.android.LeafBranchWitness'])
 assert original==amended
 save(out/'audit.json',{'actual_root_custodied_baseline':{'packet_seal':identity(seal),'manifest':identity(HOST/'manifest.json'),'probe':identity(baseline['dev/mixer/android/ConcreteHostProbe.java'])},
 'baseline_leaves':len(baseline),'modified_existing_files':sorted(changed),'new_files':['dev/mixer/android/NativeOutcomeProbe.java'],'exact_eight_source_delta':True,
 'methods58_and_return_expressions64_byte_exact_wrapping_only':True,'compiled_selected_return_calls':verified_returns,
 'branch_result_event_output_matches_actual_root_baseline':True,'branch_output':identity(out/'branch-actual-root-baseline.stdout'),
 'audit_sink_absent':True,'known_provenance_correction':'Packet original Probe is3780B; root-custodied migration Probe3807B includes same NativeEditor allowlist set. Actual delta against3807B independently reviewed.',
 'native_or_full_matrix_credit':False})
 print(json.dumps({'exact_eight_delta':True,'return_expressions':verified_returns,'branch_equivalence':True}))
finally:
 shutil.rmtree(scratch);save(out/'cleanup.json',{'scratch_removed':not scratch.exists(),'all_children_reaped':all(r['reaped'] for r in logs),'native_UI_capture_or_process_inventory':False})
