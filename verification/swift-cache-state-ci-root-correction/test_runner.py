#!/usr/bin/env python3
"""Focused controls for the isolated fixed fixture runner, no native runtime."""
import copy,importlib.util,json,os,pathlib,signal,subprocess,sys,tempfile,time,unittest
from unittest import mock
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cache_runner',HERE/'check_cache_state.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class RunnerControls(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory(prefix='mixer-cache-runner-controls-');self.base=pathlib.Path(self.temp.name).resolve()
 def tearDown(self):self.temp.cleanup()
 def bad(self,fn,*a,**kw):
  with self.assertRaises((RuntimeError,OSError,ValueError)):fn(*a,**kw)
 def commands(self):
  out=self.base/'out';out.mkdir();c=r.Commands(out,{'commands':[]},time.monotonic()+20);scratch=out/'scratch';scratch.mkdir();c.bind_scratch(scratch);return c
 def pack(self):p=self.base/'pack';r.shutil.copytree(r.PACK,p);return p
 def diagnostic(self):
  source=self.base/'api.rs';source.write_text('fn main(){let _=Missing;}\n');start=source.read_bytes().index(b'Missing');probe={'source':'api.rs','bytes':source.stat().st_size,'sha256':r.sha(source),'code':'E0425','message_contains':['Missing','scope'],'primary_spans':[{'byte_start':start,'byte_end':start+7,'text':'Missing'}]}
  d={'level':'error','message':'cannot find value Missing in this scope','code':{'code':'E0425'},'spans':[{'file_name':'api.rs','byte_start':start,'byte_end':start+7,'is_primary':True}],'children':[]};return probe,d
 def negative(self,probe,d):return r.verify_negative(probe,json.dumps(d),self.base,self.base/'binary',{'exit':1,'child_returned':True,'owned_group_gone':True})
 def test_closed_pack_source_and_manifest(self):
  m=r.verify_pack(r.PACK);self.assertEqual(m['member_count'],86);self.assertEqual(r.sha(r.PACK/'source/library/cache_state.rs'),r.SOURCE_SHA256)
 def test_missing_extra_mutated_pack_rejected(self):
  p=self.pack();(p/'extra').write_bytes(b'x');self.bad(r.verify_pack,p);(p/'extra').unlink();f=p/'source/library/cache_state.rs';f.write_bytes(f.read_bytes()+b'\n');self.bad(r.verify_pack,p);f.unlink();self.bad(r.verify_pack,p)
 def test_manifest_rewrite_and_source_hash_override_rejected(self):
  p=self.pack();m=json.loads((p/'manifest.json').read_bytes());m['members'][0]['sha256']='0'*64;(p/'manifest.json').write_text(json.dumps(m));self.bad(r.verify_pack,p)
 def test_paths_symlinks_special_members(self):
  for name in ['', '.', '../x', 'a/../b', '/x', 'a//b', './a','a/./b','.git/x','a\\b','x\x00']:self.bad(r.member,name)
  p=self.pack();f=p/'api/loan.rs';f.unlink();f.symlink_to(p/'api/receipt.rs');self.bad(r.inventory,p);f.unlink();os.mkfifo(f);self.bad(r.inventory,p)
 def test_fresh_output_fixed_directory(self):
  runs=self.base/'runs';runs.mkdir()
  with mock.patch.object(r,'RUNS',runs):
   q=r.fresh_output(runs/'fresh');self.assertTrue((q/'ownership.json').is_file());self.bad(r.fresh_output,q);self.bad(r.fresh_output,self.base/'other')
   alias=self.base/'alias';alias.symlink_to(runs,target_is_directory=True);self.bad(r.fresh_output,alias/'child')
 def test_checks_active_under_optimized_python(self):
  code="import runpy;d=runpy.run_path(%r);d['member']('../escape')"%str(HERE/'check_cache_state.py')
  p=subprocess.run([sys.executable,'-B','-O','-c',code],capture_output=True,timeout=15);self.assertNotEqual(p.returncode,0);self.assertIn(b'Noncanonical member path',p.stderr)
 def test_environment_scrubs_all_test_flags_and_caller_scratch(self):
  bad={'RUSTFLAGS':'bad','RUST_TEST_SHUFFLE':'1','RUST_TEST_NEW_OPTION':'bad','RUST_MIN_STACK':'bad','RUSTC_BOOTSTRAP':'bad','RUSTUP_AUTO_INSTALL':'1','RUSTC_WRAPPER':'bad','CARGO_ENCODED_RUSTFLAGS':'bad','MIXER_CACHE_FIXTURE_EVIDENCE':'bad','MIXER_OTHER':'bad','REVIEW_SCRATCH':'bad','TMPDIR':'bad','TMP':'bad','TEMP':'bad'}
  with mock.patch.dict(os.environ,bad):
   env=r.environment({'TMPDIR':'owned','TMP':'owned','TEMP':'owned'});self.assertTrue(all(k not in env for k in bad if k not in ['TMPDIR','TMP','TEMP','RUSTUP_AUTO_INSTALL']));self.assertTrue(all(env[k]=='owned'for k in ['TMPDIR','TMP','TEMP']));self.assertEqual(env['RUSTUP_AUTO_INSTALL'],'0')
 def test_exact_methods_full_and_partition(self):
  names=['a','b'];listing='a: test\nb: test\n\n2 tests, 0 benchmarks\n';self.assertEqual(r.verify_methods(listing,names),names)
  text='running 1 test\ntest a ... output\nok\n\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.01s\n';self.assertEqual(r.verify_methods(text,['a'],True,1),['a'])
  for bad in [listing.replace('b:','a:'),listing.replace('2 tests','1 tests'),'']:self.bad(r.verify_methods,bad,names)
  for bad in [text.replace('0 ignored','1 ignored'),text.replace('1 filtered','0 filtered'),text.replace('\nok\n','\nignored\n'),text.replace('test a','test b')]:self.bad(r.verify_methods,bad,['a'],True,1)
 def test_layouts_complete_and_no_duplicates(self):
  expected=json.loads((r.PACK/'inventories/layouts.json').read_bytes());text='\n'.join('ACCOUNTING_LAYOUT %s size=%d align=%d'%(x['type'],x['bytes'],x['align'])for x in expected['layouts']);self.assertEqual(r.verify_layouts(text,expected),expected['layouts']);self.bad(r.verify_layouts,text+'\n'+text,expected);self.bad(r.verify_layouts,text.replace('size=488','size=487'),expected)
 def test_negative_api_exact_primary_closure(self):
  probe,d=self.diagnostic();self.assertEqual(self.negative(probe,d)[0]['code'],'E0425')
  for part,value in [('code',{'code':'E0412'}),('message','unrelated'),('spans',[])]:
   changed=copy.deepcopy(d);changed[part]=value;self.bad(self.negative,probe,changed)
  for part,value in [('file_name','other.rs'),('byte_start',0),('is_primary',False)]:
   changed=copy.deepcopy(d);changed['spans'][0][part]=value;self.bad(self.negative,probe,changed)
  changed=copy.deepcopy(d);changed['spans']*=2;self.bad(self.negative,probe,changed)
 def test_unclassified_nested_or_duplicate_diagnostic_errors_rejected(self):
  probe,d=self.diagnostic();changed=copy.deepcopy(d);changed['children']=[dict(d,code={'code':'E9999'})];self.bad(self.negative,probe,changed)
  self.bad(r.verify_negative,probe,'{"level":"error","level":"note"}',self.base,self.base/'binary',{'exit':1,'child_returned':True,'owned_group_gone':True})
  self.bad(r.verify_negative,probe,'{"value":NaN}',self.base,self.base/'binary',{'exit':1,'child_returned':True,'owned_group_gone':True})
  self.bad(r.verify_negative,probe,json.dumps(dict(d,code=None)),self.base,self.base/'binary',{'exit':1,'child_returned':True,'owned_group_gone':True})
 def test_negative_api_binary_or_changed_source_refused(self):
  probe,d=self.diagnostic();(self.base/'binary').write_bytes(b'not-negative');self.bad(self.negative,probe,d);(self.base/'binary').unlink();(self.base/'api.rs').write_text('changed');self.bad(self.negative,probe,d)
 def test_negative_command_timeout_descendant_or_unreturned_refused(self):
  probe,d=self.diagnostic()
  for key,value in [('child_returned',False),('owned_group_gone',False),('timed_out',True),('output_capped',True),('descendants_outlived_child',True)]:
   row={'exit':1,'child_returned':True,'owned_group_gone':True};row[key]=value;self.bad(r.verify_negative,probe,json.dumps(d),self.base,self.base/'binary',row)
 def test_derivative_exact_roster_and_suffix(self):
  derived=self.base/'derived';r.shutil.copytree(r.PACK/'source',derived)
  p=derived/'library/cache_state.rs';p.write_bytes(p.read_bytes()+r.APPEND)
  for name in ['selected_controls.rs','scalar_cursor_independent.rs']:r.shutil.copyfile(r.PACK/'controls'/name,derived/name)
  self.assertEqual(len(r.verify_derived(derived,r.PACK)),19);p.write_bytes(p.read_bytes()+b'\n');self.bad(r.verify_derived,derived,r.PACK)
 def test_selected_compiler_identity_only(self):
  text='rustc 1.99.0 (b940084d7 2026-09-28)\nbinary: rustc\ncommit-hash: b940084d7eb6a299eb4bfeb8e34901bc051e7ac4\ncommit-date: 2026-09-28\nhost: aarch64-apple-darwin\nrelease: 1.99.0\nLLVM version: 23.1.1\n'
  self.assertEqual(r.rust_identity(text)['release'],'1.99.0');self.assertEqual(r.rust_identity(text.replace('1.99.0','1.98.1'))['release'],'1.98.1')
  for changed in [text.replace('1.99.0','1.99.1'),text.replace('aarch64-apple-darwin','x86_64-apple-darwin'),text.replace('release: 1.99.0','release: 1.98.1'),text.replace('1.99.0','1.99.0-nightly'),text+'host: aarch64-apple-darwin\n',text.replace('2026-09-28','2026-02-30')]:self.bad(r.rust_identity,changed)
 def test_missing_and_failed_commands_keep_raw_receipts(self):
  c=self.commands();self.bad(c.run,'missing',[self.base/'missing'],self.base);self.assertIn('spawn_error',c.receipt['commands'][-1]);self.bad(c.run,'failed',[sys.executable,'-c','print("partial");raise SystemExit(7)'],self.base);self.assertEqual((c.out/'commands/failed.stdout').read_text(),'partial\n');self.assertTrue(c.receipt['commands'][-1]['owned_group_gone'])
 def test_timeout_owned_child_group_and_output_cap(self):
  c=self.commands()
  with mock.patch.object(r,'CHILD_SECONDS',.5):self.bad(c.run,'timeout',[sys.executable,'-c','import time;print("ready",flush=True);time.sleep(10)'],self.base)
  self.assertTrue(c.receipt['commands'][-1]['timed_out']);self.assertTrue(c.receipt['commands'][-1]['owned_group_gone']);self.assertEqual((c.out/'commands/timeout.stdout').read_text(),'ready\n')
  with mock.patch.object(r,'OUTPUT_CAP',32):self.bad(c.run,'cap',[sys.executable,'-c','print("x"*2000)'],self.base)
  self.assertTrue(c.receipt['commands'][-1]['output_capped']);self.assertEqual((c.out/'commands/cap.stdout').stat().st_size,32)
 def test_owned_descendant_group_is_stopped(self):
  c=self.commands();code='import subprocess,sys,time;subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"]);print("descendant-ready",flush=True);time.sleep(20)'
  with mock.patch.object(r,'CHILD_SECONDS',.7):self.bad(c.run,'descendant',[sys.executable,'-c',code],self.base)
  row=c.receipt['commands'][-1];self.assertTrue(row['timed_out']);self.assertTrue(row['owned_group_gone']);self.assertTrue(row['child_returned']);self.assertIn('descendant-ready',(c.out/'commands/descendant.stdout').read_text())
 def test_expired_global_deadline_starts_no_child(self):
  c=self.commands();c.deadline=time.monotonic()-1;self.bad(c.run,'expired',[sys.executable,'-c','pass'],self.base);self.assertEqual(c.receipt['commands'],[])
 def test_cleanup_hashes_and_retains_before_delete(self):
  c=self.commands();scratch=self.base/'scratch';scratch.mkdir();marker={'token':'owned'};r.save(scratch/'ownership.json',marker);(scratch/'input').write_bytes(b'exact');(scratch/'binary').write_bytes(b'compiler-output');ident=r.identity(scratch)
  observed=r.cleanup(c.out,scratch,ident,marker,{'binary'},c);self.assertTrue(observed['removed']);self.assertFalse(scratch.exists());ret=json.loads((c.out/'retention.json').read_bytes());self.assertEqual(ret['compiler_products_hashed_before_removal'][0]['sha256'],r.hashlib.sha256(b'compiler-output').hexdigest());self.assertEqual((c.out/ret['files'][0]['content']).read_bytes(),b'exact')
 def test_changed_scratch_marker_preserves_recovery(self):
  c=self.commands();scratch=self.base/'scratch';scratch.mkdir();r.save(scratch/'ownership.json',{'token':'other'});self.bad(r.cleanup,c.out,scratch,r.identity(scratch),{'token':'owned'},set(),c);self.assertTrue(scratch.exists())
 def test_File_expected_counts_and_full_results_bound(self):
  x=json.loads((r.PACK/'inventories/file-cases.json').read_bytes());self.assertEqual(len(x['cases']),31);self.assertEqual(sum(c['aggregate_present']for c in x['cases']),29);self.assertEqual(sum(len(c['actual_complete32']or[])==32 for c in x['cases']),29);self.bad(r.verify_cases,self.base,x)
 def test_every_child_gets_owned_default_temporary_directory(self):
  c=self.commands();code='import json,os,tempfile;f=tempfile.NamedTemporaryFile(delete=False);f.write(b"owned");f.close();print(json.dumps({"vars":{k:os.environ.get(k)for k in ["TMPDIR","TMP","TEMP"]},"file":f.name}))'
  with mock.patch.dict(os.environ,{'TMPDIR':'/not-owned','TMP':'/not-owned','TEMP':'/not-owned'}):
   text,_,row=c.run('owned-tmp-default',[sys.executable,'-B','-c',code],self.base)
  observed=json.loads(text);self.assertEqual(set(observed['vars'].values()),{str(c.child_tmp)});self.assertTrue(pathlib.Path(observed['file']).is_relative_to(c.scratch));self.assertEqual(pathlib.Path(observed['file']).read_bytes(),b'owned');self.assertEqual(row['environment_overrides'],observed['vars']);self.assertTrue(row['owned_group_gone'])
 def test_commands_without_owned_scratch_start_nothing(self):
  out=self.base/'unbound';out.mkdir();c=r.Commands(out,{'commands':[]},time.monotonic()+20)
  self.bad(c.run,'unbound',[sys.executable,'-c','raise SystemExit(99)'],self.base);self.assertEqual(c.receipt['commands'],[])
 def test_foreign_mismatched_or_symlink_temporary_directory_refused(self):
  c=self.commands();foreign=self.base/'foreign';foreign.mkdir();link=c.scratch/'alias';link.symlink_to(foreign,target_is_directory=True)
  for override in [{'TMPDIR':str(c.child_tmp),'TMP':str(foreign),'TEMP':str(c.child_tmp)},dict.fromkeys(['TMPDIR','TMP','TEMP'],str(foreign)),dict.fromkeys(['TMPDIR','TMP','TEMP'],str(link))]:
   self.bad(c.run,'foreign',[sys.executable,'-c','raise SystemExit(99)'],self.base,override)
  self.assertEqual(c.receipt['commands'],[])
 def test_fixture_temporary_override_stays_inside_owned_scratch(self):
  c=self.commands();temp=c.scratch/'fixture-tmp';temp.mkdir();env=dict.fromkeys(['TMPDIR','TMP','TEMP'],str(temp))
  text,_,row=c.run('owned-tmp-fixture',[sys.executable,'-c','import json,os;print(json.dumps({k:os.environ[k]for k in ["TMPDIR","TMP","TEMP"]}))'],self.base,env)
  self.assertEqual(json.loads(text),env);self.assertTrue(row['owned_group_gone'])
 def deadline_control(self,stage):
  runs=self.base/'runs';runs.mkdir();state={'pack_calls':0,'cleanup_entered':False,'after_delay':False};original_verify=r.verify_pack;original_cleanup=r.cleanup
  def verify(base):
   state['pack_calls']+=1
   if stage=='postflight'and state['pack_calls']==3:time.sleep(.25);state['after_delay']=True
   return original_verify(base)
  def clean(*args):
   state['cleanup_entered']=True
   if stage=='retention':time.sleep(.25);state['after_delay']=True
   return original_cleanup(*args)
  with mock.patch.object(r,'RUNS',runs),mock.patch.object(r,'CLEANUP_SECONDS',.05),mock.patch.object(r,'verify_pack',verify),mock.patch.object(r,'cleanup',clean):
   out=r.fresh_output(runs/'deadline');status=r.execute(out,'mixer-no-such-official-compiler-control')
  receipt=json.loads((out/'receipt.json').read_bytes());self.assertEqual(status,1);self.assertTrue(receipt['cleanup']['deadline_expired']);self.assertFalse(receipt['cleanup']['removed']);self.assertTrue((out/'scratch/ownership.json').is_file());self.assertEqual(receipt['commands'],[]);self.assertFalse(state['after_delay']);self.assertEqual(state['cleanup_entered'],stage=='retention');self.assertLess(receipt['cleanup_elapsed_seconds'],.20)
  if stage=='postflight':self.assertEqual(state['pack_calls'],3);self.assertEqual(receipt['postflight'],{})
  r.save(HERE/'logs'/('deadline-'+stage+'-control.json'),{'scope':'Actual corrected runner with lowered test-only cleanup allowance, deliberately slow hook and missing compiler; zero child commands','state':state,'receipt':receipt,'scratch_preserved_at_assertion':True,'owned_test_directory_removed_by_tearDown':True})
 def test_postflight_deadline_is_terminal_and_preserves_scratch(self):self.deadline_control('postflight')
 def test_retention_deadline_is_terminal_and_preserves_scratch(self):self.deadline_control('retention')
if __name__=='__main__':unittest.main(verbosity=2)
