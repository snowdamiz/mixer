#!/usr/bin/env python3
"""Guarded pure filesystem/mock tests of the authored admission; no real children."""
import unittest.mock  # load stdlib ssl types before socket API denial
import offline
offline.install()
import ast,contextlib,io,json,os,shutil,sys,tempfile,types,unittest
from pathlib import Path
from unittest import mock
import admit as a
import bounded_commands as r
HERE=Path(__file__).resolve().parent

class FakePipe:
 def __init__(self,n):self.n=n;self.closed=False
 def fileno(self):return self.n
 def close(self):self.closed=True
class FakeProcess:
 def __init__(self,code=0,wait_error=False):self.pid=987654321;self.returncode=code;self.stdout=FakePipe(9001);self.stderr=FakePipe(9002);self.wait_error=wait_error;self.waited=False
 def poll(self):return self.returncode
 def wait(self,timeout):
  if self.wait_error:raise TimeoutError('injected reaping failure')
  self.waited=True;return self.returncode
class FakeSelector:
 def __init__(self):self.items={};self.closed=False
 def register(self,p,event,data):self.items[p]=types.SimpleNamespace(fileobj=p,data=data)
 def unregister(self,p):del self.items[p]
 def get_map(self):return self.items
 def select(self,timeout):return [(v,1)for v in list(self.items.values())]
 def close(self):self.closed=True

class PureAdmission(unittest.TestCase):
 def setUp(self):self.work=Path(tempfile.mkdtemp(prefix='pure-',dir=HERE));self.commands=[]
 def tearDown(self):shutil.rmtree(self.work)
 def command(self):
  out=self.work/'out';out.mkdir();c=r.Commands(out,{'commands':[]},r.time.monotonic()+5000);scratch=out/'scratch';scratch.mkdir();c.bind_scratch(scratch);self.commands.append(c);return c
 def fake_run(self,*,data=b'ok\n',code=0,cap=8*1024*1024,wait_error=False,gone_error=False,descendant=False,timeout=False):
  c=self.command();proc=FakeProcess(code,wait_error);chunks={9001:[data,b''],9002:[b'']};gone_state={'first':descendant}
  def read(fd,size):return chunks[fd].pop(0)if chunks[fd]else b''
  def gone(pid):
   if gone_error:raise PermissionError('injected group uncertainty')
   if gone_state['first']:gone_state['first']=False;return False
   return True
  counter=[0]
  def clock():counter[0]+=1;return counter[0]*31 if timeout else counter[0]*.01
  failure=None;result=None
  with contextlib.ExitStack()as stack:
   stack.enter_context(mock.patch.object(r.subprocess,'Popen',return_value=proc))
   stack.enter_context(mock.patch.object(r.selectors,'DefaultSelector',FakeSelector))
   stack.enter_context(mock.patch.object(r.os,'read',side_effect=read))
   stack.enter_context(mock.patch.object(c,'gone',side_effect=gone))
   stack.enter_context(mock.patch.object(r,'child_usage',return_value={'ru_utime':0.,'ru_stime':0.,'ru_minflt':0,'ru_majflt':0}))
   stack.enter_context(mock.patch.object(r,'OUTPUT_CAP',cap))
   stack.enter_context(mock.patch.object(r.time,'monotonic',side_effect=clock))
   c.deadline=10_000
   try:result=c.run('fake',['fake-tool'],self.work,seconds=30)
   except BaseException as e:failure=e
  return c,proc,result,failure
 def focused(self):return ''.join('test '+a.FOCUSED_PREFIX+x+' ... ok\n'for x in a.FOCUSED_SUFFIXES)+'test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\n'
 def test_source_inputs_exact_and_six_commands(self):
  m,p,data=a.inputs();self.assertEqual(len(data),136);self.assertEqual(len(p),6);self.assertEqual(a.closure(m['candidateFiles']),a.CANDIDATE);self.assertEqual([s['commandSeconds']for s in p],[300,300,180,180,600,600]);self.assertEqual(sum(s['commandSeconds']for s in p),2160)
 def test_source_bound_rejects_changed_bytes(self):
  p=self.work/'x';p.write_bytes(b'a');row={'bytes':1,'sha256':a.digest(b'a')};self.assertEqual(a.bound(p,row),b'a');p.write_bytes(b'b')
  with self.assertRaises(RuntimeError):a.bound(p,row)
 def test_materialized_source_rejects_missing_extra_and_symlinks(self):
  p=self.work/'source';p.mkdir();(p/'Cargo.toml').write_bytes(b'a');m={'candidateFiles':{'Cargo.toml':{'bytes':1,'sha256':a.digest(b'a')}}};self.assertEqual(a.source_check(p,m),a.CANDIDATE)
  (p/'extra').write_bytes(b'x')
  with self.assertRaises(RuntimeError):a.source_check(p,m)
  (p/'extra').unlink();(p/'Cargo.toml').unlink()
  with self.assertRaises(RuntimeError):a.source_check(p,m)
  (p/'Cargo.toml').symlink_to(self.work/'other')
  with self.assertRaises(RuntimeError):a.source_check(p,m)
 def test_exact_seven_methods_and_zero_failure_rejection(self):
  good=self.focused();self.assertEqual(a.summary(good,True)[0]['passed'],7)
  for bad in [good.replace('7 passed','0 passed'),good.replace('0 failed','1 failed'),good.replace('0 ignored','1 ignored'),good.replace(a.FOCUSED_SUFFIXES[0],a.FOCUSED_SUFFIXES[1]),good.replace(a.FOCUSED_SUFFIXES[0],'unknown'),'',good+good]:
   with self.assertRaises(RuntimeError):a.summary(bad,True)
 def test_geometry_binding_and_cleanup_required(self):
  names=('floor','execution_header','execution_construction','frame_operation','category_ceiling_sum','wasi_max','shared','conservative_combined','combined_limit','constructed_current','constructed_peak','resident_current','resident_peak','frame_peak')
  text='PLAN_PROFILE '+ ' '.join(n+'='+str(268435456 if n=='combined_limit'else 1)for n in names)+' tickets=85/86\nPLAN_PROFILE cleanup_zero=true guest_instructions=0 initializes=0 invokes=0\n'
  self.assertEqual(a.geometry(text)['peak_tickets'],86)
  for bad in [text.replace('cleanup_zero=true','cleanup_zero=false'),text.replace('tickets=85/86','tickets=85/87'),text.replace('combined_limit=268435456','combined_limit=999999999'),text+text]:
   with self.assertRaises(RuntimeError):a.geometry(bad)
 def test_nonzero_followups_and_ignored_are_reported(self):
  text='test result: ok. 3 passed; 0 failed; 2 ignored; 0 measured; 0 filtered out; finished in 0.01s\n';self.assertEqual(a.summary(text)[0]['ignored'],2)
  with self.assertRaises(RuntimeError):a.summary(text.replace('3 passed','0 passed'))
 def test_environment_drops_cargo_rust_test_loader_hooks(self):
  poison={'HOME':'/home/runner','PATH':'/bin','RUSTUP_HOME':'/toolchains','CARGO_BUILD_RUSTC_WRAPPER':'bad','CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER':'bad','CARGO_HOME':'bad','RUSTC':'bad','RUSTFLAGS':'bad','RUST_TEST_THREADS':'99','RUSTUP_TOOLCHAIN':'nightly','LD_PRELOAD':'bad','MIXER_OTHER':'bad','GITHUB_TOKEN':'bad'}
  with mock.patch.dict(os.environ,poison,clear=True):
   env=r.environment({'CARGO_HOME':'owned','RUSTUP_TOOLCHAIN':'1.99.0'});self.assertEqual(set(env),{'HOME','PATH','RUSTUP_HOME','CARGO_HOME','RUSTUP_TOOLCHAIN','RUSTUP_AUTO_INSTALL'});self.assertEqual(env['RUSTUP_AUTO_INSTALL'],'0')
 def test_hosted_refuses_local_and_retries_before_actions(self):
  for env in [{},{'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_RUN_ATTEMPT':'2'}]:
   with mock.patch.dict(os.environ,env,clear=True):
    with self.assertRaises(RuntimeError):a.hosted()
 def test_success_preserves_output_and_terminal_facts(self):
  c,p,result,error=self.fake_run();self.assertIsNone(error);self.assertIsNone(c.active);self.assertEqual(result[0],'ok\n');row=c.receipt['commands'][0];self.assertTrue(row['child_returned']and row['owned_group_gone']);self.assertEqual(row['per_child_limit_seconds'],30);self.assertEqual(row['stdout_sha256'],a.digest(b'ok\n'));self.assertTrue(p.stdout.closed and p.stderr.closed)
 def test_cap_fails_and_retains_bounded_output(self):
  c,p,result,error=self.fake_run(data=b'123456789',cap=8);self.assertIsNotNone(error);row=c.receipt['commands'][0];self.assertTrue(row['output_capped']);self.assertIsNone(c.active);self.assertEqual((c.out/'commands/fake.stdout').read_bytes(),b'12345678')
 def test_timeout_closes_owned_child_without_retry(self):
  c,p,result,error=self.fake_run(timeout=True);self.assertIsNotNone(error);self.assertTrue(c.receipt['commands'][0]['timed_out']);self.assertEqual(len(c.receipt['commands']),1);self.assertIsNone(c.active)
 def test_nonzero_exit_is_not_acceptance(self):
  c,p,result,error=self.fake_run(code=101);self.assertIsNotNone(error);self.assertEqual(c.receipt['commands'][0]['exit'],101);self.assertIsNone(c.active)
 def test_reap_failure_keeps_custody_and_suppresses_usage(self):
  c,p,result,error=self.fake_run(wait_error=True);self.assertIsNotNone(error);self.assertIsNotNone(c.active);row=c.receipt['commands'][0];self.assertTrue(row['custody_hold']);self.assertIsNone(row['child_resource_usage']['aggregate_delta'])
 def test_unknown_group_keeps_custody(self):
  c,p,result,error=self.fake_run(gone_error=True);self.assertIsNotNone(error);self.assertIsNotNone(c.active);self.assertFalse(c.receipt['commands'][0]['owned_group_gone'])
 def test_outliving_descendants_not_success(self):
  c,p,result,error=self.fake_run(descendant=True);self.assertIsNotNone(error);self.assertTrue(c.receipt['commands'][0]['descendants_outlived_child'])
 def test_seventh_command_limit_and_aggregate_fit_before_spawn(self):
  c=self.command();c.receipt['commands']=[{}]*7
  with self.assertRaises(RuntimeError):c.run('extra',['fake'],self.work,seconds=30)
  c.receipt['commands']=[];c.deadline=r.time.monotonic()+30
  with self.assertRaises(RuntimeError):c.run('cannot-fit',['fake'],self.work,seconds=30)
  self.assertEqual(c.receipt['commands'],[])
 def test_python_syntax_and_no_autorun_import(self):
  for name in ['admit.py','bounded_commands.py','offline.py','test_admission.py']:ast.parse((HERE/name).read_text())
  self.assertIn("if __name__=='__main__':main()",(HERE/'admit.py').read_text())
 def test_real_runtime_apis_are_denied(self):
  for fn,args in [(os.killpg,(987654321,0)),(os.waitpid,(987654321,0)),(r.subprocess.Popen,(['false'],)),(r.signal.signal,(r.signal.SIGTERM,None)),(r.resource.getrusage,(r.resource.RUSAGE_CHILDREN,))]:
   with self.assertRaises(AssertionError):fn(*args)

if __name__=='__main__':
 start=r.time.monotonic();stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PureAdmission))
 record={'schema':1,'status':'passed'if result.wasSuccessful()else'failed','testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'seconds':r.time.monotonic()-start,'pythonVersion':sys.version,'realProductRuntimeRuns':0,'realChildOrSignalOrGroupOperations':0,'scope':'pure source/filesystem/AST and mocked authored-runner control flow; not live custody evidence','output':stream.getvalue()}
 target=HERE/'pure-harness-result.json'
 if not result.wasSuccessful()and not(HERE/'first-harness-failure.json').exists():(HERE/'first-harness-failure.json').write_text(json.dumps(record,indent=2)+'\n')
 target.write_text(json.dumps(record,indent=2)+'\n');print(stream.getvalue());print(json.dumps({k:v for k,v in record.items()if k!='output'}));sys.exit(0 if result.wasSuccessful()else 1)
