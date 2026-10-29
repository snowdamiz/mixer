#!/usr/bin/env python3
"""Finite pure filesystem and guarded mock controls. Never execute Rust tools."""
import unittest.mock
import offline
offline.install()
import collections,contextlib,io,json,os,shutil,sys,tempfile,types,unittest
from pathlib import Path
from unittest import mock
import admit as a
import bounded_commands as b
HERE=Path(__file__).resolve().parent

def cargo_json(success=False,message='fixture lint',root=''):
 m={'message':message,'level':'error','code':{'code':'clippy::fixture'},'spans':[{'file_name':root+'src/example.rs','line_start':1}],'rendered':'error: '+message+'\n'}
 return json.dumps({'reason':'compiler-message','message':m})+'\n'+json.dumps({'reason':'build-finished','success':success})+'\n'

class Pipe:
 def __init__(self,n):self.n=n
 def fileno(self):return self.n
 def close(self):pass
class Process:
 def __init__(self,code=0):self.pid=987654321;self.returncode=code;self.stdout=Pipe(9001);self.stderr=Pipe(9002)
 def poll(self):return self.returncode
 def wait(self,timeout):return self.returncode
class Selector:
 def __init__(self):self.items={}
 def register(self,p,event,data):self.items[p]=types.SimpleNamespace(fileobj=p,data=data)
 def unregister(self,p):del self.items[p]
 def get_map(self):return self.items
 def select(self,timeout):return [(v,1)for v in list(self.items.values())]
 def close(self):pass

class Controls(unittest.TestCase):
 def setUp(self):self.work=Path(tempfile.mkdtemp(prefix='pure-',dir=HERE))
 def tearDown(self):shutil.rmtree(self.work)
 def fixture(self):
  paths={};expected={};raw={}
  for arm in ('baseline','candidate'):
   paths[arm]={n:self.work/arm/n for n in ('source','target','cargo','home')}
   for p in paths[arm].values():p.mkdir(parents=True)
   raw[arm]={n:('fn fixture() {} // '+arm+'\n').encode()for n in a.OVERLAYS};raw[arm]['Cargo.toml']=b'[package]\n'
   for n,v in raw[arm].items():
    p=paths[arm]['source']/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
   expected[arm]={n:a.file_row(v)for n,v in raw[arm].items()}
  return paths,expected,raw
 def test_exact_source_materializer_and_four_overlay_closures(self):
  m,data=a.inputs();self.assertEqual(len(data['baseline']),136);self.assertEqual(len(data['candidate']),136)
  self.assertEqual(a.closure(m['baselineFiles']),a.BASELINE);self.assertEqual(a.closure(m['candidateFiles']),a.CANDIDATE)
  self.assertEqual({n for n in data['baseline']if data['baseline'][n]!=data['candidate'][n]},set(a.OVERLAYS))
 def test_input_helper_fails_closed_before_import(self):
  with mock.patch.object(a,'sha',return_value='wrong'):
   with self.assertRaisesRegex(RuntimeError,'helper changed'):a.inputs()
 def test_local_preservation_and_raw_actual_paths_are_never_opened(self):
  original=Path.open;seen=[]
  def opened(path,*args,**kwargs):
   name=str(path);seen.append(name)
   self.assertNotIn('/reviewed-host-slice-actual-results/local/',name)
   self.assertFalse(name.endswith('/.github/workflows/hosted.yml')or name.endswith('/browser_auth/store.ex'))
   return original(path,*args,**kwargs)
  with mock.patch.object(Path,'open',opened):a.inputs()
  self.assertTrue(seen)
 def test_exact_five_argv_and_four_path_format_scope(self):
  p,e,r=self.fixture();tool=self.work/'toolbin';config=self.work/'rustfmt.toml';plan=a.command_plan(p,tool,config)
  self.assertEqual([x['name']for x in plan],['toolchain-identity','format-baseline','format-candidate','clippy-baseline','clippy-candidate'])
  self.assertEqual([x['seconds']for x in plan],[30,30,30,300,300]);self.assertEqual(sum(x['seconds']for x in plan),690)
  for row in plan[1:3]:self.assertEqual(row['argv'],[str(tool/'rustfmt'),'--edition','2021','--emit','files','--config-path',str(config),*[str(p[row['arm']]['source']/n)for n in a.OVERLAYS]])
  for row in plan[3:]:
   self.assertEqual(row['argv'][3:],[str(p[row['arm']]['source']/'Cargo.toml'),'--locked','--offline','--all-features','--all-targets','--message-format=json','--','-D','warnings'])
   self.assertEqual(row['accepted_exits'],(0,101));self.assertNotIn('test',row['argv'])
 def test_arm_isolation_and_no_ambient_rust_hooks(self):
  p,e,r=self.fixture();tool=self.work/'toolbin';base=a.arm_environment(p['baseline'],tool);candidate=a.arm_environment(p['candidate'],tool)
  for n in ('HOME','CARGO_HOME','CARGO_TARGET_DIR'):self.assertNotEqual(base[n],candidate[n])
  with mock.patch.dict(os.environ,{'RUSTFLAGS':'bad','RUSTC_WRAPPER':'bad','CARGO_ENCODED_RUSTFLAGS':'bad','LD_PRELOAD':'bad'},clear=False):actual=b.environment(base)
  for n in ('RUSTFLAGS','RUSTC_WRAPPER','CARGO_ENCODED_RUSTFLAGS','LD_PRELOAD'):self.assertNotIn(n,actual)
  self.assertEqual(actual['RUSTUP_AUTO_INSTALL'],'0');self.assertEqual(actual['CARGO_NET_OFFLINE'],'true')
 def test_format_evidence_exact_copies_hashes_and_diff(self):
  p,e,r=self.fixture();n=a.OVERLAYS[0];(p['candidate']['source']/n).write_bytes(b'fn fixture() {\n}\n')
  after,result=a.format_evidence(self.work/'evidence','candidate',p['candidate']['source'],e['candidate'],r['candidate'])
  self.assertEqual(result['changedPaths'],[n]);self.assertEqual(result['beforeTreeSHA256'],a.closure(e['candidate']));self.assertEqual(result['afterTreeSHA256'],a.closure(after))
  dest=self.work/'evidence/format/candidate';self.assertEqual((dest/'before'/n).read_bytes(),r['candidate'][n]);self.assertEqual((dest/'after'/n).read_bytes(),b'fn fixture() {\n}\n');self.assertIn('--- before/',(dest/'format.diff').read_text())
 def test_format_rejects_unexpected_change_and_retains_receipt(self):
  p,e,r=self.fixture();(p['baseline']['source']/'Cargo.toml').write_bytes(b'changed')
  with self.assertRaisesRegex(RuntimeError,'outside the four'):a.format_evidence(self.work/'evidence','baseline',p['baseline']['source'],e['baseline'],r['baseline'])
  result=json.loads((self.work/'evidence/format/baseline/receipt.json').read_text());self.assertFalse(result['verified']);self.assertEqual(result['outsideOverlayChanges'],['Cargo.toml'])
 def test_source_rejects_missing_extra_and_symlink(self):
  p,e,r=self.fixture();source=p['baseline']['source'];n=a.OVERLAYS[0];q=source/n
  q.unlink()
  with self.assertRaises(RuntimeError):a.exact_source(source,e['baseline'])
  q.write_bytes(r['baseline'][n]);(source/'extra').write_bytes(b'x')
  with self.assertRaises(RuntimeError):a.exact_source(source,e['baseline'])
  (source/'extra').unlink();q.unlink();q.symlink_to(source/'Cargo.toml')
  with self.assertRaises(RuntimeError):a.exact_source(source,e['baseline'])
 def test_parent_cargo_config_is_refused(self):
  p,e,r=self.fixture();config=self.work/'.cargo';config.mkdir();(config/'config.toml').write_text('[build]\n')
  with self.assertRaisesRegex(RuntimeError,'Inherited Cargo'):a.cargo_configs_absent(p['baseline']['source'])
 def test_parent_clippy_config_is_refused(self):
  p,e,r=self.fixture();(self.work/'.clippy.toml').write_text('too-many-arguments-threshold = 100\n')
  with self.assertRaisesRegex(RuntimeError,'Inherited Clippy'):a.cargo_configs_absent(p['baseline']['source'])
 def test_lint_nonzero_is_findings_and_full_json_retained(self):
  result=a.lint_evidence(cargo_json(),101,self.work);self.assertFalse(result['lintPassed']);self.assertFalse(result['buildFinished']);self.assertEqual(result['diagnostics'][0]['rendered'],'error: fixture lint\n')
  clean=a.lint_evidence(json.dumps({'reason':'build-finished','success':True}),0,self.work);self.assertTrue(clean['lintPassed'])
 def test_lint_malformed_and_unknown_failure_are_refused(self):
  for text,code in [('',0),('bad json',101),(cargo_json(),0),(cargo_json()+cargo_json(),101),(json.dumps({'reason':'build-finished','success':False}),101)]:
   with self.subTest(text=text):
    with self.assertRaises((RuntimeError,ValueError)):a.lint_evidence(text,code,self.work)
 def test_diagnostics_compare_without_line_shift_or_suppression(self):
  base=a.lint_evidence(cargo_json(root='/base/'),101,Path('/base'));candidate=a.lint_evidence(cargo_json(root='/candidate/'),101,Path('/candidate'));candidate['diagnostics'][0]['spans'][0]['line_start']=999
  result=a.comparison({'baseline':base,'candidate':candidate});self.assertEqual(len(result['shared']),1);self.assertFalse(result['candidateOnly']);self.assertFalse(result['integrationAccepted'])
  candidate['diagnostics'].append({**candidate['diagnostics'][0],'message':'new fixture lint'});self.assertEqual(len(a.comparison({'baseline':base,'candidate':candidate})['candidateOnly']),1)
 def fake_helper(self,*,code=0,data=b'ok\n',cap=None,group_error=False,timeout=False):
  out=self.work/'helper';out.mkdir();c=b.Commands(out,{'commands':[]},10000);scratch=out/'scratch';scratch.mkdir();c.bind_scratch(scratch);proc=Process(code);chunks={9001:[data,b''],9002:[b'']};clock=[0]
  def read(fd,size):return chunks[fd].pop(0)if chunks[fd]else b''
  def gone(pid):
   if group_error:raise PermissionError('guarded unknown group')
   return True
  def tick():clock[0]+=1;return clock[0]*(31 if timeout else .01)
  with contextlib.ExitStack()as stack:
   for obj,name,value in ((b.subprocess,'Popen',mock.Mock(return_value=proc)),(b.selectors,'DefaultSelector',Selector),(b.os,'read',mock.Mock(side_effect=read)),(c,'gone',mock.Mock(side_effect=gone)),(b,'child_usage',mock.Mock(return_value={'ru_utime':0.,'ru_stime':0.,'ru_minflt':0,'ru_majflt':0})),(b.time,'monotonic',mock.Mock(side_effect=tick))):stack.enter_context(mock.patch.object(obj,name,value))
   if cap is not None:stack.enter_context(mock.patch.object(b,'AGGREGATE_OUTPUT_CAP',cap))
   error=None;result=None
   try:result=c.run('mock',['mock-tool'],self.work,seconds=30,accepted_exits=(0,101))
   except BaseException as e:error=e
  return c,result,error
 def test_helper_known_lint_exit_has_verified_mock_custody(self):
  c,result,error=self.fake_helper(code=101);self.assertIsNone(error);self.assertEqual(result[2]['exit'],101);self.assertTrue(result[2]['child_returned']);self.assertTrue(result[2]['owned_group_gone']);self.assertEqual(result[2]['accepted_exit_codes'],[0,101])
 def test_helper_unknown_exit_refused(self):
  c,result,error=self.fake_helper(code=2);self.assertIsNotNone(error);self.assertIsNone(result)
 def test_helper_output_cap_refused(self):
  c,result,error=self.fake_helper(data=b'oversized',cap=2);self.assertIsNotNone(error);self.assertTrue(c.receipt['commands'][0]['output_capped']);self.assertEqual(c.receipt['aggregate_output_bytes'],2)
 def test_helper_timeout_refused(self):
  c,result,error=self.fake_helper(timeout=True);self.assertIsNotNone(error);self.assertTrue(c.receipt['commands'][0]['timed_out'])
 def test_helper_group_uncertainty_keeps_hold(self):
  c,result,error=self.fake_helper(group_error=True);self.assertIsNotNone(error);self.assertIsNotNone(c.active);self.assertTrue(c.receipt['commands'][0]['custody_hold'])
 def test_command_failure_still_checks_both_sources_and_preserves_primary(self):
  p,e,r=self.fixture();c=types.SimpleNamespace(receipt={'commands':[]},run=mock.Mock(side_effect=RuntimeError('primary refusal')),save=mock.Mock());spec=a.command_plan(p,self.work/'toolbin',self.work/'config')[3]
  with self.assertRaisesRegex(RuntimeError,'primary refusal'):a.checked_command(c,spec,p,self.work/'toolbin',e,self.work/'evidence',r)
  row=c.receipt['unregisteredPostflights'][0];self.assertTrue(row['sourcePostflight']['verified']);self.assertTrue(row['sourcePostflight']['bothArms'])
 def test_cross_arm_mutation_after_command_fails_closed(self):
  p,e,r=self.fixture();spec=a.command_plan(p,self.work/'toolbin',self.work/'config')[4]
  def run(*args,**kwargs):
   (p['baseline']['source']/'Cargo.toml').write_bytes(b'changed');row={'name':spec['name'],'exit':0};c.receipt['commands'].append(row);return json.dumps({'reason':'build-finished','success':True}),'',row
  c=types.SimpleNamespace(receipt={'commands':[]},run=run,save=mock.Mock())
  with self.assertRaisesRegex(RuntimeError,'postflight mismatch'):a.checked_command(c,spec,p,self.work/'toolbin',e,self.work/'evidence',r)
 def execute_mock(self,failure=None):
  temp=self.work/'runner';temp.mkdir();toolbin=self.work/'rustup/toolchains'/a.TOOLCHAIN/'bin';toolbin.mkdir(parents=True)
  for n in ('rustc','rustfmt','cargo','cargo-clippy','clippy-driver'):(toolbin/n).write_bytes(('guarded fake '+n).encode())
  component=toolbin.parent/'lib/rustlib/components';component.parent.mkdir(parents=True);component.write_text('cargo-x86_64-unknown-linux-gnu\nclippy-preview-x86_64-unknown-linux-gnu\nrustc-x86_64-unknown-linux-gnu\nrust-std-x86_64-unknown-linux-gnu\nrustfmt-preview-x86_64-unknown-linux-gnu\n')
  data={arm:{n:('fn fixture() {} // '+arm+'\n').encode()for n in a.OVERLAYS}for arm in ('baseline','candidate')}
  for arm in data:data[arm]['Cargo.toml']=b'[package]\n'
  manifest={'baselineFiles':{n:a.file_row(v)for n,v in data['baseline'].items()},'candidateFiles':{n:a.file_row(v)for n,v in data['candidate'].items()}}
  class FakeCommands(b.Commands):
   def run(self,name,argv,cwd,env=None,negative=False,seconds=30,accepted_exits=(0,)):
    row={'name':name,'argv':argv,'cwd':str(cwd),'pid':987654321,'child_returned':True,'owned_group_gone':True,'exit':0,'timed_out':False,'output_capped':False}
    self.receipt['commands'].append(row)
    if name=='clippy-baseline'and failure:
     if failure=='custody':self.active=object();row['child_returned']=False;row['owned_group_gone']=False
     if failure=='timeout':row['timed_out']=True
     if failure=='output-cap':row['output_capped']=True
     raise RuntimeError('injected '+failure)
    if name.startswith('format-'):
     for n in a.OVERLAYS:
      p=cwd/n;p.write_bytes(p.read_bytes()+b'\n')
    text='release: 1.99.0\nhost: x86_64-unknown-linux-gnu\n'
    if name.startswith('clippy-'):row['exit']=101;text=cargo_json(root=str(cwd)+'/')
    return text,'',row
  env={'GITHUB_SHA':'a'*40,'GITHUB_RUN_ID':'mock-only'}
  with contextlib.ExitStack()as stack:
   stack.enter_context(mock.patch.object(a,'hosted',return_value=(temp,toolbin)));stack.enter_context(mock.patch.object(a,'inputs',return_value=(manifest,data)));stack.enter_context(mock.patch.object(a,'Commands',FakeCommands));stack.enter_context(mock.patch.dict(os.environ,env,clear=False))
   for n in ('getsignal','signal','setitimer'):stack.enter_context(mock.patch.object(a.signal,n,return_value=None))
   error=None
   try:a.execute()
   except BaseException as e:error=e
  out=temp/(a.PROFILE+'-evidence');return json.loads((out/'receipt.json').read_text()),error,out
 def test_aggregate_baseline_lint_failure_still_runs_candidate(self):
  receipt,error,out=self.execute_mock();self.assertIsNone(error);self.assertEqual(len(receipt['commands']),5);self.assertEqual(receipt['status'],'diagnostic-completed-with-lint-findings');self.assertEqual(receipt['lintPassed'],{'baseline':False,'candidate':False});self.assertTrue(receipt['cleanup']['ownedScratchRemoved'])
  self.assertTrue((out/'clippy-baseline.json').is_file());self.assertTrue((out/'clippy-candidate.json').is_file());self.assertFalse((out/'scratch').exists())
  self.assertTrue(all(x['sourcePostflight']['bothArms']for x in receipt['commands']))
 def test_aggregate_timeout_stops_before_candidate_lint(self):
  receipt,error,out=self.execute_mock('timeout');self.assertIsNotNone(error);self.assertEqual(len(receipt['commands']),4);self.assertTrue(receipt['cleanup']['ownedScratchRemoved']);self.assertFalse((out/'clippy-candidate.json').exists())
 def test_aggregate_output_cap_stops_before_candidate_lint(self):
  receipt,error,out=self.execute_mock('output-cap');self.assertIsNotNone(error);self.assertEqual(len(receipt['commands']),4);self.assertTrue(receipt['cleanup']['ownedScratchRemoved']);self.assertFalse((out/'clippy-candidate.json').exists())
 def test_aggregate_unknown_custody_preserves_scratch_and_stops(self):
  receipt,error,out=self.execute_mock('custody');self.assertIsNotNone(error);self.assertEqual(len(receipt['commands']),4);self.assertFalse(receipt['cleanup']['ownedScratchRemoved']);self.assertTrue(receipt['cleanup']['custodyHold']);self.assertTrue((out/'scratch').is_dir());self.assertFalse((out/'clippy-candidate.json').exists())
 def test_workflow_is_manual_pinned_bounded_and_proposed_only(self):
  text=(HERE/'workflow.yml').read_text();self.assertIn('workflow_dispatch:',text);self.assertNotIn('push:',text);self.assertIn('cancel-in-progress: false',text);self.assertIn('rustup toolchain install 1.99.0 --profile minimal --component rustfmt --component clippy',text)
  self.assertIn('MIXER_PIN_BITMAP_FORMAT_LINT_SELECTION: ${{ inputs.profile }}',text);self.assertNotIn('MIXER_PIN_BITMAP_FORMAT_LINT_SELECTION:',text.split('    steps:')[0]);self.assertIn('timeout-minutes: 17',text)
  self.assertNotIn('cargo test',text);self.assertNotIn('/.github/workflows/hosted.yml',text);self.assertNotIn('/hosted/lib/mixer_hosted/browser_auth/store.ex',text)
 def test_hosted_preconditions_refuse_local_or_wrong_attempt(self):
  with mock.patch.dict(os.environ,{},clear=True):
   with self.assertRaisesRegex(RuntimeError,'GitHub hosted only'):a.hosted()
  env={'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_RUN_ATTEMPT':'2'}
  with mock.patch.dict(os.environ,env,clear=True):
   with self.assertRaisesRegex(RuntimeError,'first attempt'):a.hosted()

if __name__=='__main__':
 from correction_controls import CorrectionControls
 suite=unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromTestCase(Controls),unittest.defaultTestLoader.loadTestsFromTestCase(CorrectionControls)))
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 record={'schema':1,'status':'passed'if result.wasSuccessful()else'failed','testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'pythonVersion':sys.version,'actualRustRuns':0,'realNestedProcessOrSignalOperations':0,'liveCustodyEvidence':False,'scope':'guarded pure filesystem and mock controls; no formatting/lint execution','output':stream.getvalue()}
 record.update({'priorSemanticsReplayed':26,'correctionControls':suite.countTestCases()-26,'sparseClosure':getattr(CorrectionControls,'sparse_result',None),'historicalResultsAreCurrentEvidence':False,'officialValidatorExecuted':False})
 record['controlSourceFiles']={n:a.file_row((HERE/n).read_bytes())for n in ('admit.py','bounded_commands.py','offline.py','root_controls.py','correction_controls.py','context_check.py','context-rules.json','workflow.yml')}
 record['controlSourceTreeSHA256']=a.closure(record['controlSourceFiles'])
 if not result.wasSuccessful()and not(HERE/'first-control-failure.json').exists():b.save(HERE/'first-control-failure.json',record)
 b.save(HERE/'root-controls-result.json',record);print(stream.getvalue());print(json.dumps({k:v for k,v in record.items()if k!='output'}));sys.exit(0 if result.wasSuccessful()else 1)
