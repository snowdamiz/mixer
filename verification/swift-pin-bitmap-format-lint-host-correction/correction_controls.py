"""Additional pure controls for the two corrected host preconditions."""
import ast,contextlib,json,os,shutil,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock
import admit as a
import context_check as w

HERE=Path(__file__).resolve().parent


class CorrectionControls(unittest.TestCase):
 def setUp(self):self.work=Path(tempfile.mkdtemp(prefix='pure-',dir=HERE))
 def tearDown(self):shutil.rmtree(self.work)
 def documents(self):return w.parse((HERE/'workflow.yml').read_text()),w.parse((HERE/'historical/workflow.yml').read_text())
 def components(self,text):
  path=self.work/'components';path.write_text(text);return a.component_evidence(path)
 def test_frozen_parent_and_historical_controls_are_bound(self):
  result=w.verify_parent();self.assertEqual(result['membersVerified'],10)
  self.assertFalse(result['historicalResultsAreCurrentEvidence'])
  record=json.loads((HERE/'historical/root-controls-result.json').read_bytes());self.assertEqual(record['testsRun'],26)
 def test_materializer_command_plan_and_runtime_policies_unchanged(self):
  old=ast.parse((HERE/'historical/admit.py').read_text());new=ast.parse((HERE/'admit.py').read_text())
  def functions(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
  before=functions(old);after=functions(new)
  self.assertEqual(set(after)-set(before),{'component_evidence'})
  self.assertEqual({n:v for n,v in before.items()if n!='execute'},{n:after[n]for n in before if n!='execute'})
  self.assertEqual((a.ACTIVE_SECONDS,a.CLEANUP_SECONDS),(900,60))
  self.assertEqual((a.MAX_FILE_BYTES,a.MAX_SOURCE_BYTES),(16*1024*1024,64*1024*1024))
  # Only the component read/check is changed inside execute; all child/custody code is exact.
  old_execute=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name=='execute')
  new_execute=next(n for n in new.body if isinstance(n,ast.FunctionDef)and n.name=='execute')
  def component_statement(n):
   text=ast.unparse(n)
   return text.startswith('component = regular(')or text.startswith("receipt['components'] =")or text.startswith("need({'rustfmt-preview', 'clippy-preview'}")
  self.assertEqual([ast.dump(n,include_attributes=False)for n in old_execute.body if not component_statement(n)],
                   [ast.dump(n,include_attributes=False)for n in new_execute.body if not component_statement(n)])
 def test_real_host_qualified_component_manifest_passes(self):
  text='cargo-x86_64-unknown-linux-gnu\nclippy-preview-x86_64-unknown-linux-gnu\nrustc-x86_64-unknown-linux-gnu\nrust-std-x86_64-unknown-linux-gnu\nrustfmt-preview-x86_64-unknown-linux-gnu\n'
  result=self.components(text);self.assertEqual(result['text'],text);self.assertEqual(result['sha256'],a.digest(text.encode()))
  self.assertEqual(result['requiredHostComponents'],list(a.REQUIRED_HOST_COMPONENTS))
 def test_bare_component_names_reject(self):
  with self.assertRaisesRegex(RuntimeError,'Required pinned host components absent'):self.components('rustfmt-preview\nclippy-preview\n')
 def test_wrong_host_or_target_component_names_reject(self):
  for host in ('aarch64-unknown-linux-gnu','x86_64-unknown-linux-musl','x86_64-apple-darwin','x86_64-pc-windows-msvc'):
   with self.subTest(host=host):
    with self.assertRaisesRegex(RuntimeError,'Required pinned host components absent'):
     self.components('rustfmt-preview-'+host+'\nclippy-preview-'+host+'\n')
 def test_either_missing_host_component_rejects(self):
  for component in a.REQUIRED_HOST_COMPONENTS:
   with self.subTest(only=component):
    with self.assertRaisesRegex(RuntimeError,'Required pinned host components absent'):self.components(component+'\n')
  with self.assertRaisesRegex(RuntimeError,'Required pinned host components absent'):self.components('')
 def test_component_prefix_suffix_and_mixed_target_names_reject(self):
  for text in ('\n'.join('extra-'+n for n in a.REQUIRED_HOST_COMPONENTS),
               '\n'.join(n+'-extra'for n in a.REQUIRED_HOST_COMPONENTS),
               a.REQUIRED_HOST_COMPONENTS[0]+'\nclippy-preview-aarch64-unknown-linux-gnu',
               'rustfmt-preview-aarch64-unknown-linux-gnu\n'+a.REQUIRED_HOST_COMPONENTS[1],
               a.REQUIRED_HOST_COMPONENTS[0]+'\nclippy-preview',
               'rustfmt-preview\n'+a.REQUIRED_HOST_COMPONENTS[1]):
   with self.subTest(text=text):
    with self.assertRaisesRegex(RuntimeError,'Required pinned host components absent'):self.components(text+'\n')
 def test_component_order_is_not_reproducibility_identity(self):
  first=self.components('\n'.join(a.REQUIRED_HOST_COMPONENTS)+'\n')
  second=self.components('\n'.join(reversed(a.REQUIRED_HOST_COMPONENTS))+'\n')
  self.assertNotEqual(first['sha256'],second['sha256']);self.assertEqual(first['requiredHostComponents'],second['requiredHostComponents'])
  self.assertIn('not a reproducibility identity',first['sha256Scope'])
 def test_frozen_workflow_runner_context_defect_is_retained_and_rejects(self):
  corrected,original=self.documents()
  with self.assertRaisesRegex(ValueError,'Context runner unavailable at jobs.diagnose.env.RUSTUP_HOME'):w.validate(original)
 def test_corrected_workflow_has_exact_two_step_environments(self):
  corrected,original=self.documents();result=w.validate_contract(corrected,original)
  references=[r for r in result['expressionReferences']if r['expression']=='runner.temp'and r['location'].endswith('.env.RUSTUP_HOME')]
  self.assertEqual(len(references),2);self.assertFalse(result['officialValidatorExecuted']);self.assertFalse(result['workflowOrShellExecuted'])
 def test_omitting_either_consuming_rustup_home_rejects(self):
  corrected,original=self.documents()
  for name in (w.INSTALL,w.DRIVER):
   changed=deepcopy(corrected);step=next(s for s in changed['jobs']['diagnose']['steps']if s.get('name')==name);del step['env']['RUSTUP_HOME']
   with self.subTest(step=name):
    with self.assertRaisesRegex(ValueError,'exceeds the authorized host correction'):w.validate_contract(changed,original)
 def test_job_env_runner_reintroduction_rejects(self):
  corrected,original=self.documents();corrected['jobs']['diagnose']['env']={'RUSTUP_HOME':w.RUSTUP_HOME}
  with self.assertRaisesRegex(ValueError,'Context runner unavailable'):w.validate_contract(corrected,original)
 def test_altered_home_caps_policy_or_profile_rejects(self):
  corrected,original=self.documents()
  changed=deepcopy(corrected);next(s for s in changed['jobs']['diagnose']['steps']if s.get('name')==w.INSTALL)['env']['RUSTUP_HOME']+='-other'
  with self.assertRaisesRegex(ValueError,'exceeds the authorized host correction'):w.validate_contract(changed,original)
  changed=deepcopy(corrected);changed['jobs']['diagnose']['timeout-minutes']=26
  with self.assertRaisesRegex(ValueError,'exceeds the authorized host correction'):w.validate_contract(changed,original)
  changed=deepcopy(corrected);next(s for s in changed['jobs']['diagnose']['steps']if s.get('name')==w.INSTALL)['run']+=' --force'
  with self.assertRaisesRegex(ValueError,'exceeds the authorized host correction'):w.validate_contract(changed,original)
  changed=deepcopy(corrected);next(s for s in changed['jobs']['diagnose']['steps']if s.get('name')==w.DRIVER)['env']['MIXER_PIN_BITMAP_FORMAT_LINT_SELECTION']='other'
  with self.assertRaisesRegex(ValueError,'exceeds the authorized host correction'):w.validate_contract(changed,original)
 def test_restricted_parser_and_expression_fail_closed(self):
  for text in ('jobs:\n  a: x\n  a: y\n','on: *alias\n','on: [one, {two}]\n','---\non: x\n','on:\n\tkey: x\n'):
   with self.subTest(source=text):
    with self.assertRaises(ValueError):w.parse(text)
  for expression in ('${{ runner["temp"] }}','${{ runner.temp || vars.other }}','${{ runner.temp','${{ unknown.temp }}'):
   with self.subTest(expression=expression):
    with self.assertRaises(ValueError):w.expressions(expression,['runner'],'test')
 def test_sparse_checkout_covers_actual_reads_and_control_sources(self):
  corrected,original=self.documents();opened=set();original_open=Path.open
  def trace(path,*args,**kwargs):
   opened.add(path.resolve().relative_to(w.ROOT).as_posix());return original_open(path,*args,**kwargs)
  with mock.patch.object(Path,'open',trace):
   manifest,data=a.inputs();w.verify_parent();w.validate_contract(corrected,original)
  opened.update(w.SIBLING+n for n in ('root_controls.py','correction_controls.py','context_check.py','admit.py','bounded_commands.py','offline.py','workflow.yml','context-rules.json'))
  opened.add(a.INPUT_HELPER)
  result=w.require_sparse_contains(corrected,opened);self.assertEqual(result['missing'],[])
  self.assertEqual((len(data['baseline']),len(data['candidate'])),(136,136))
  self.assertEqual(len(manifest['overlayPaths']),4)
  # Store finite observed paths in memory for the fresh aggregate receipt only.
  type(self).sparse_result=result
 def test_sparse_omitting_any_required_packet_or_source_root_rejects(self):
  corrected,original=self.documents();patterns=w.sparse_patterns(corrected)
  for pattern in patterns:
   changed=deepcopy(corrected);checkout=changed['jobs']['diagnose']['steps'][0]
   checkout['with']['sparse-checkout']='\n'.join(p for p in patterns if p!=pattern)+'\n'
   probe=pattern[1:]+('member'if pattern.endswith('/')else'')
   with self.subTest(pattern=pattern):
    with self.assertRaisesRegex(ValueError,'Sparse checkout omits inputs'):w.require_sparse_contains(changed,[probe])
 def test_no_imported_parent_test_module_and_all_prior_test_names_replayed(self):
  def methods(path):
   tree=ast.parse(path.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='Controls')
   return {n.name:ast.dump(n,include_attributes=False)for n in cls.body if isinstance(n,ast.FunctionDef)and n.name.startswith('test_')}
  before=methods(HERE/'historical/root_controls.py');after=methods(HERE/'root_controls.py')
  self.assertEqual(len(before),26);self.assertEqual(before,after)
  import sys
  self.assertFalse(any(getattr(v,'__file__','')and str(getattr(v,'__file__','')).startswith(str(w.ROOT/w.PARENT))for v in list(sys.modules.values())))
