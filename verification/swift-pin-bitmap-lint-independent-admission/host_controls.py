#!/usr/bin/env python3
"""Guarded local/hosted source and mock controls; never launch a child."""
import unittest.mock  # Load standard-library socket subclasses before replacing socket.socket.
import offline
offline.install()
import ast, contextlib, io, json, os, re, shutil, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock
import admit as a
import bounded_commands as b

HERE = Path(__file__).resolve().parent


def passed_text():
    names = list(a.ORACLES) + ['fixture_' + str(i) for i in range(690)]
    return ''.join('test '+n+' ... ok\n' for n in names)+'test result: ok. 699 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1s\n'


class Pipe:
    def __init__(self, n): self.n = n
    def fileno(self): return self.n
    def close(self): pass


class Process:
    def __init__(self, code=0): self.pid = 987654321; self.returncode = code; self.stdout = Pipe(9001); self.stderr = Pipe(9002)
    def poll(self): return self.returncode
    def wait(self, timeout): return self.returncode


class Selector:
    def __init__(self): self.items = {}
    def register(self, p, event, data): self.items[p] = types.SimpleNamespace(fileobj=p, data=data)
    def unregister(self, p): del self.items[p]
    def get_map(self): return self.items
    def select(self, timeout): return [(v, 1) for v in list(self.items.values())]
    def close(self): pass


class Controls(unittest.TestCase):
    def setUp(self): self.work = Path(tempfile.mkdtemp(prefix='pure-', dir=HERE))
    def tearDown(self):
        self.remove_absolute(self.work)

    def remove_absolute(self, root):
        # Absolute local paths retain the write guard; do not grant an opaque
        # dir_fd blanket exception just to accommodate shutil's fast teardown.
        for p in sorted(root.rglob('*'), key=lambda x:len(x.parts), reverse=True):
            if p.is_symlink() or p.is_file(): p.unlink()
            else: p.rmdir()
        root.rmdir()

    def fixture(self):
        paths = {n: self.work/n for n in ('source','target','cargo','home','nodebin')}
        for p in paths.values(): p.mkdir()
        raw = {n: ('fn fixture() {} // '+n+'\n').encode() for n in a.OVERLAYS}; raw['Cargo.toml'] = b'[package]\n'
        for n, value in raw.items():
            p = paths['source']/n; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(value)
        expected = {n:a.file_row(v) for n,v in raw.items()}
        toolbin = self.work/'tools'; toolbin.mkdir()
        for n in a.TOOLS:
            p = toolbin/n; p.write_text('mock '+n); p.chmod(0o700)
        tools = {n:a.binary_row(toolbin/n) for n in a.TOOLS}
        external = self.work/'external'; external.mkdir(); binary = external/'node'; binary.write_text('mock node'); binary.chmod(0o700)
        node = a.binary_row(binary); (paths['nodebin']/'node').symlink_to(binary)
        config = self.work/'rustfmt.toml'; config.write_text('edition = "2021"\n')
        return paths, expected, raw, toolbin, tools, node, config

    def test_guard_and_subject_no_live_side_effects(self):
        self.assertIs(b.subprocess.Popen, offline.denied)
        self.assertIs(b.os.killpg, offline.denied)
        self.assertIs(b.signal.setitimer, offline.denied)
        self.assertIs(b.resource.getrusage, offline.denied)
        self.assertTrue(sys.dont_write_bytecode)
        self.assertEqual(offline.ATTEMPTS, [])

    def test_exact_lean_source_materialization(self):
        seen = []; original = Path.open
        def opened(path, *args, **kwargs):
            seen.append(str(path))
            self.assertNotIn('/clock-format-actual-results/local/', str(path))
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'open', opened): m, data = a.inputs()
        self.assertEqual(len(data), 136); self.assertEqual(a.closure(m['candidateFiles']), a.CANDIDATE)
        self.assertEqual(set(m['overlayPaths']), set(a.OVERLAYS)); self.assertTrue(seen)

    def test_seal_rejection_happens_before_materialization(self):
        with mock.patch.object(a, 'sha', return_value='wrong'):
            with self.assertRaisesRegex(RuntimeError, 'seal changed'): a.inputs()

    def test_command_helper_only_fixed_numeric_plan_changes(self):
        reuse = json.loads((HERE/'reuse.json').read_text())
        old = (a.ROOT/reuse['helperPreimage']['path']).read_text()
        self.assertEqual(a.digest(old.encode()), reuse['helperPreimage']['sha256'])
        expected = old.replace('MAX_COMMANDS=5', 'MAX_COMMANDS=6').replace('seconds in (30,300)', 'seconds in (30,60,300,600)').replace('CHILD_SECONDS=300', 'CHILD_SECONDS=600')
        self.assertEqual((HERE/'bounded_commands.py').read_text(), expected)
        self.assertEqual((b.MAX_COMMANDS,b.OUTPUT_CAP,b.AGGREGATE_OUTPUT_CAP,a.ACTIVE_SECONDS,a.CLEANUP_SECONDS),(6,8388608,33554432,1800,60))

    def test_generic_evidence_functions_preserve_reviewed_source(self):
        reuse = json.loads((HERE/'reuse.json').read_text())
        old = (a.ROOT/reuse['genericPreimage']['path']).read_text()
        self.assertEqual(a.digest(old.encode()), reuse['genericPreimage']['sha256'])
        new = (HERE/'admit.py').read_text()
        def funcs(text): return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
        before, after = funcs(old), funcs(new)
        for n in reuse['genericFunctions']:
            self.assertEqual(before[n].replace('outside the four overlays','outside the fifteen overlays'), after[n])

    def test_exact_six_child_vectors_and_bounds(self):
        p,e,r,t,tools,node,c = self.fixture(); plan = a.command_plan(p,t,c,node)
        self.assertEqual([x['name'] for x in plan], ['compiler-identity','node-identity','format-candidate','clippy-candidate','debug-regression','release-regression'])
        self.assertEqual([x['seconds'] for x in plan], [30,30,60,300,600,600])
        self.assertEqual(sum(x['seconds'] for x in plan),1620)
        self.assertEqual(plan[2]['argv'],[str(t/'rustfmt'),'--edition','2021','--emit','files','--config-path',str(c),*[str(p['source']/n) for n in a.OVERLAYS]])
        self.assertEqual(plan[3]['argv'],[str(t/'cargo'),'clippy','--manifest-path',str(p['source']/'Cargo.toml'),'--locked','--offline','--all-features','--all-targets','--message-format=json','--','-D','warnings'])
        for spec in plan[4:]:
            self.assertEqual(spec['argv'][-4:], ['--','--include-ignored','--test-threads=1','--show-output'])
            self.assertEqual(spec['accepted_exits'],(0,))
        self.assertNotIn('--release',plan[4]['argv']);self.assertIn('--release',plan[5]['argv'])

    def test_ambient_hooks_are_removed_and_single_node_resolves(self):
        p,e,r,t,tools,node,c = self.fixture(); env = a.arm_environment(p,t,node)
        with mock.patch.dict(os.environ, {'NODE_OPTIONS':'--require unsafe','NODE_PATH':'unsafe','RUSTFLAGS':'unsafe','RUSTC_WRAPPER':'unsafe','LD_PRELOAD':'unsafe'},clear=False):
            actual=b.environment(env)
        for n in ('NODE_OPTIONS','NODE_PATH','RUSTFLAGS','RUSTC_WRAPPER','LD_PRELOAD'):self.assertNotIn(n,actual)
        self.assertEqual(actual['MIXER_NODE'],node['path']);self.assertEqual(actual['PATH'],str(p['nodebin'])+':'+str(t)+':/usr/bin:/bin')
        self.assertEqual(actual['RUSTUP_AUTO_INSTALL'],'0');self.assertEqual(actual['CARGO_NET_OFFLINE'],'true')

    def test_node_single_resolution_and_absence_refusal(self):
        p,e,r,t,tools,node,c = self.fixture()
        with mock.patch.object(a,'ROOT',self.work/'checkout'), mock.patch.object(a.shutil,'which',return_value=node['path']) as which:
            selected=a.choose_node(self.work/'runner-temp');self.assertEqual(selected['sha256'],node['sha256']);which.assert_called_once()
        with mock.patch.object(a.shutil,'which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'Existing absolute'):a.choose_node(self.work/'runner-temp')

    def test_node_checkout_temp_nonexecutables_refuse(self):
        p,e,r,t,tools,node,c=self.fixture()
        with mock.patch.object(a,'ROOT',self.work/'external'),mock.patch.object(a.shutil,'which',return_value=node['path']):
            with self.assertRaisesRegex(RuntimeError,'outside checkout'):a.choose_node(self.work/'runner-temp')
        with mock.patch.object(a,'ROOT',self.work/'checkout'),mock.patch.object(a.shutil,'which',return_value=node['path']):
            with self.assertRaisesRegex(RuntimeError,'outside checkout'):a.choose_node(self.work/'external')
            Path(node['path']).chmod(0o600)
            with self.assertRaisesRegex(RuntimeError,'Executable'):a.choose_node(self.work/'runner-temp')

    def test_node_and_compiler_binary_drift_refuse(self):
        p,e,r,t,tools,node,c=self.fixture();self.assertTrue(a.check_binaries(tools,node,p)['verified'])
        original=Path(node['path']).read_bytes();Path(node['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError,'identity changed'):a.check_binaries(tools,node,p)
        Path(node['path']).write_bytes(original);(t/'rustc').write_bytes(b'changed compiler')
        with self.assertRaisesRegex(RuntimeError,'identity changed'):a.check_binaries(tools,node,p)

    def test_private_node_link_drift_refuses(self):
        p,e,r,t,tools,node,c=self.fixture();(p['nodebin']/'node').unlink();(p['nodebin']/'node').symlink_to(t/'rustc')
        with self.assertRaisesRegex(RuntimeError,'Node link'):a.check_binaries(tools,node,p)

    def test_format_fifteen_before_after_diff_full_closure(self):
        p,e,r,t,tools,node,c=self.fixture();n=a.OVERLAYS[-1];(p['source']/n).write_text('fn fixture() {\n}\n')
        after,record=a.format_evidence(self.work/'evidence','candidate',p['source'],e,r)
        self.assertEqual(record['changedPaths'],[n]);self.assertEqual(len(record['files']),15);self.assertEqual(record['afterTreeSHA256'],a.closure(after))
        for name in a.OVERLAYS:self.assertEqual((self.work/'evidence/format/candidate/before'/name).read_bytes(),r[name])
        self.assertTrue((self.work/'evidence/format/candidate/format.diff').read_text())

    def test_format_unrelated_file_change_refuses_and_retains_receipt(self):
        p,e,r,t,tools,node,c=self.fixture();(p['source']/'Cargo.toml').write_text('changed')
        with self.assertRaisesRegex(RuntimeError,'outside the fifteen'):a.format_evidence(self.work/'evidence','candidate',p['source'],e,r)
        self.assertFalse(json.loads((self.work/'evidence/format/candidate/receipt.json').read_text())['verified'])

    def test_exact_699_terminals_and_nine_oracles(self):
        record=a.test_evidence(passed_text());self.assertEqual(record['passed'],699);self.assertEqual(len(record['nodeOracles']),9)
        for text in (passed_text().replace('699 passed','698 passed'),passed_text().replace('0 ignored','9 ignored'),passed_text().replace(' ... ok',' ... FAILED',1),passed_text().replace(a.ORACLES[0],'not_the_oracle'),passed_text()+'test extra ... ok\n',passed_text().replace('0 filtered out','1 filtered out')):
            with self.assertRaises(RuntimeError):a.test_evidence(text)

    def fake_command(self, spec, *, failure=None, text=None, code=0, mutation=None):
        c=types.SimpleNamespace(receipt={'commands':[]},save=mock.Mock())
        def run(*args,**kwargs):
            row={'name':spec['name'],'exit':code};c.receipt['commands'].append(row)
            if mutation:mutation()
            if failure:raise failure
            return text or '', '', row
        c.run=run;return c

    def test_primary_failure_kept_with_source_and_binary_postflight(self):
        p,e,r,t,tools,node,config=self.fixture();spec=a.command_plan(p,t,config,node)[4];primary=RuntimeError('primary command failed');c=self.fake_command(spec,failure=primary)
        with self.assertRaisesRegex(RuntimeError,'primary command failed'):a.checked_command(c,spec,p,t,tools,node,e,self.work/'evidence',r,config)
        row=c.receipt['commands'][0];self.assertTrue(row['sourcePostflight']['verified']);self.assertTrue(row['binaryPostflight']['verified'])

    def test_binary_postflight_runs_when_source_postflight_fails(self):
        p,e,r,t,tools,node,config=self.fixture();spec=a.command_plan(p,t,config,node)[4]
        c=self.fake_command(spec,text=passed_text(),mutation=lambda:(p['source']/'Cargo.toml').write_text('changed'))
        (self.work/'evidence').mkdir()
        with self.assertRaisesRegex(RuntimeError,'source postflight mismatch'):a.checked_command(c,spec,p,t,tools,node,e,self.work/'evidence',r,config)
        self.assertFalse(c.receipt['commands'][0]['sourcePostflight']['verified']);self.assertTrue(c.receipt['commands'][0]['binaryPostflight']['verified'])

    def test_prespan_failure_has_postflight_record_without_launch(self):
        p,e,r,t,tools,node,config=self.fixture();spec=a.command_plan(p,t,config,node)[0];c=types.SimpleNamespace(receipt={'commands':[]},run=mock.Mock(),save=mock.Mock())
        config.write_text('not selected')
        with self.assertRaisesRegex(RuntimeError,'config changed'):a.checked_command(c,spec,p,t,tools,node,e,self.work/'evidence',r,config)
        c.run.assert_not_called();self.assertTrue(c.receipt['unregisteredPostflights'][0]['sourcePostflight']['verified'])

    def test_failed_clippy_is_not_runtime_admission(self):
        p,e,r,t,tools,node,config=self.fixture();spec=a.command_plan(p,t,config,node)[3];(self.work/'evidence').mkdir()
        text=json.dumps({'reason':'compiler-message','message':{'message':'fixture lint','level':'error','code':{'code':'clippy::fixture'},'spans':[]}})+'\n'+json.dumps({'reason':'build-finished','success':False})+'\n'
        c=self.fake_command(spec,text=text,code=101)
        with self.assertRaisesRegex(RuntimeError,'regression not admitted'):a.checked_command(c,spec,p,t,tools,node,e,self.work/'evidence',r,config)
        self.assertFalse(json.loads((self.work/'evidence/clippy-candidate.json').read_text())['lintPassed']);self.assertTrue(c.receipt['commands'][0]['sourcePostflight']['verified'])

    def test_node_identity_json_exact_path_and_version(self):
        p,e,r,t,tools,node,config=self.fixture();spec=a.command_plan(p,t,config,node)[1];(self.work/'evidence').mkdir()
        info={'execPath':node['path'],'version':'v22.20.0','versions':{'node':'22.20.0'},'platform':'linux','arch':'x64'}
        c=self.fake_command(spec,text=json.dumps(info));result=a.checked_command(c,spec,p,t,tools,node,e,self.work/'evidence',r,config)
        self.assertEqual(result,info)
        for key,value in [('execPath','/other/node'),('platform','darwin'),('arch','arm64'),('version','invalid')]:
            bad={**info,key:value};c=self.fake_command(spec,text=json.dumps(bad))
            with self.assertRaises(RuntimeError):a.checked_command(c,spec,p,t,tools,node,e,self.work/'evidence',r,config)

    def fake_helper(self,code=0,data=b'ok\n',cap=None,group_error=False,timeout=False):
        out=self.work/'helper';out.mkdir();c=b.Commands(out,{'commands':[]},10000);scratch=out/'scratch';scratch.mkdir();c.bind_scratch(scratch)
        proc=Process(code);chunks={9001:[data,b''],9002:[b'']};clock=[0]
        def read(fd,size):return chunks[fd].pop(0) if chunks[fd] else b''
        def gone(pid):
            if group_error:raise PermissionError('mock custody unknown')
            return True
        def tick():clock[0]+=1;return clock[0]*(31 if timeout else .01)
        popen=mock.Mock(return_value=proc)
        with contextlib.ExitStack() as stack:
            for obj,name,value in ((b.subprocess,'Popen',popen),(b.selectors,'DefaultSelector',Selector),(b.os,'read',mock.Mock(side_effect=read)),(c,'gone',mock.Mock(side_effect=gone)),(b,'child_usage',mock.Mock(return_value={'ru_utime':0.,'ru_stime':0.,'ru_minflt':0,'ru_majflt':0})),(b.time,'monotonic',mock.Mock(side_effect=tick))):stack.enter_context(mock.patch.object(obj,name,value))
            if cap is not None:stack.enter_context(mock.patch.object(b,'AGGREGATE_OUTPUT_CAP',cap))
            error=None;result=None
            try:result=c.run('mock',['mock-tool'],self.work,seconds=30,accepted_exits=(0,101))
            except BaseException as e:error=e
        return c,result,error,popen

    def test_mock_command_new_session_reap_group_and_stderr_stdout(self):
        c,result,error,popen=self.fake_helper();self.assertIsNone(error);self.assertTrue(popen.call_args.kwargs['start_new_session'])
        self.assertTrue(result[2]['child_returned']);self.assertTrue(result[2]['owned_group_gone']);self.assertFalse(result[2]['custody_hold'])

    def test_mock_output_cap_fails_and_retains_bound(self):
        c,result,error,popen=self.fake_helper(data=b'exceeds',cap=2);self.assertIsNotNone(error);self.assertTrue(c.receipt['commands'][0]['output_capped']);self.assertEqual(c.receipt['aggregate_output_bytes'],2)

    def test_mock_timeout_fails(self):
        c,result,error,popen=self.fake_helper(timeout=True);self.assertIsNotNone(error);self.assertTrue(c.receipt['commands'][0]['timed_out'])

    def test_mock_group_uncertainty_preserves_hold(self):
        c,result,error,popen=self.fake_helper(group_error=True);self.assertIsNotNone(error);self.assertIsNotNone(c.active);self.assertTrue(c.receipt['commands'][0]['custody_hold'])

    def execute_mock(self, failure=None, held=False):
        p,e,r,t,tools,node,config=self.fixture();temp=self.work/'runner';temp.mkdir()
        component=t.parent/'lib/rustlib/components';component.parent.mkdir(parents=True);component.write_text('\n'.join(a.REQUIRED_HOST_COMPONENTS)+'\n')
        manifest={'baselineFiles':e,'candidateFiles':e,'overlayPaths':list(a.OVERLAYS)}
        calls=[]
        def run(c,name,argv,cwd,env,seconds,accepted_exits):
            row={'name':name,'exit':0,'pid':987654321,'child_returned':not held,'owned_group_gone':not held}
            c.receipt['commands'].append(row);calls.append(name)
            if held:c.active=object()
            if failure and name=='clippy-candidate':raise RuntimeError(failure)
            if name=='compiler-identity':text='release: 1.99.0\nhost: x86_64-unknown-linux-gnu\n'
            elif name=='node-identity':text=json.dumps({'execPath':node['path'],'version':'v22.20.0','versions':{'node':'22.20.0'},'platform':'linux','arch':'x64'})
            elif name=='clippy-candidate':text=json.dumps({'reason':'build-finished','success':True})
            elif name.endswith('-regression'):text=passed_text()
            else:text=''
            return text,'',row
        error=None;result=None
        with contextlib.ExitStack() as stack:
            for obj,name,value in ((a,'hosted',mock.Mock(return_value=(temp,t))),(a,'inputs',mock.Mock(return_value=(manifest,r))),(a,'choose_node',mock.Mock(return_value=node)),(a.Commands,'run',run),(a.signal,'getsignal',mock.Mock(return_value=None)),(a.signal,'signal',mock.Mock()),(a.signal,'setitimer',mock.Mock()),(a.shutil,'rmtree',mock.Mock(side_effect=self.remove_absolute))):stack.enter_context(mock.patch.object(obj,name,value))
            stack.enter_context(mock.patch.dict(os.environ,{'GITHUB_SHA':'a'*40,'GITHUB_RUN_ID':'mock'},clear=False))
            try:result=a.execute()
            except BaseException as e:error=e
        out=temp/(a.PROFILE+'-evidence');record=json.loads((out/'receipt.json').read_text())
        return result,error,record,out,calls

    def test_mock_complete_sequence_retains_outputs_and_cleans_scratch(self):
        result,error,record,out,calls=self.execute_mock();self.assertIsNone(error)
        self.assertEqual(record['status'],'host-regression-completed');self.assertEqual(len(calls),6)
        self.assertEqual(record['DebugPassed'],699);self.assertEqual(record['ReleasePassed'],699);self.assertEqual(record['ignored'],0)
        self.assertTrue(record['cleanup']['ownedScratchRemoved']);self.assertFalse((out/'scratch').exists())
        self.assertTrue((out/'formatted-source-manifest.json').exists());self.assertTrue((out/'node-identity.json').exists())
        self.assertTrue(all(r['sourcePostflight']['verified'] and r['binaryPostflight']['verified'] for r in record['commands']))

    def test_mock_failure_postflight_precedes_owned_cleanup(self):
        result,error,record,out,calls=self.execute_mock(failure='mock clippy runtime failure')
        self.assertIsNotNone(error);self.assertEqual(len(calls),4);self.assertNotIn('debug-regression',calls)
        self.assertEqual(record['status'],'failed');self.assertTrue(record['commands'][-1]['sourcePostflight']['verified'])
        self.assertTrue(record['cleanup']['ownedScratchRemoved']);self.assertFalse((out/'scratch').exists())

    def test_mock_unresolved_custody_preserves_entire_scratch(self):
        result,error,record,out,calls=self.execute_mock(failure='mock group failure',held=True)
        self.assertIsNotNone(error);self.assertEqual(record['status'],'failed-custody-or-cleanup')
        self.assertTrue(record['cleanup']['custodyHold']);self.assertFalse(record['cleanup']['ownedScratchRemoved']);self.assertTrue((out/'scratch').exists())

    def test_workflow_no_node_install_and_exact_scope(self):
        text=(HERE/'workflow.yml').read_text()
        self.assertEqual(text.count('rustup toolchain install 1.99.0 --profile minimal --component rustfmt --component clippy'),1)
        self.assertNotIn('setup-node',text);self.assertNotIn('npm ',text);self.assertNotIn('node --',text)
        self.assertIn('cancel-in-progress: false',text);self.assertIn('timeout-minutes: 32',text)
        self.assertEqual(text.count('RUSTUP_HOME: ${{ runner.temp }}/swift-pin-bitmap-lint-regression-v1-toolchain'),2)
        self.assertIn('/verification/swift-pin-bitmap-lint-correction/',text)
        # Context validity comes from explicit step env placement; this is a
        # source check, not official workflow validation or actual execution.
        self.assertEqual(re.findall(r'^        run: (.+)$',text,re.M),[
            'python3 -B verification/swift-pin-bitmap-lint-independent-admission/host_controls.py',
            'rustup toolchain install 1.99.0 --profile minimal --component rustfmt --component clippy',
            'python3 -B verification/swift-pin-bitmap-lint-independent-admission/admit.py run'])


if __name__=='__main__':
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    sys.stderr.write(stream.getvalue())
    record={'schema':1,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'pythonVersion':sys.version,'guardBeforeSubjectImports':True,'realProcessSessionGroupSignalTimerWaitSocketCalls':0,'liveApiAttempts':offline.ATTEMPTS,'RustRuns':0,'NodeRuns':0,'mockedCustodyIsLiveEvidence':False,'scratchRemaining':[p.name for p in HERE.glob('pure-*')]}
    (HERE/'host-controls-result.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    if not result.wasSuccessful():raise SystemExit(1)
