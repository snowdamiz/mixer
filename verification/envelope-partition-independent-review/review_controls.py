#!/usr/bin/env python3
"""Independent source/mocked orchestration controls. No runtime subprocess access."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
import offline_guard
offline_guard.install(HERE)
import ast
from contextlib import ExitStack, contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from types import SimpleNamespace
import tempfile
import unittest
import admission as a
c = a.subject()
ROOT = HERE.parents[1]
PACK = ROOT / c.PACK
EXPECTED = json.loads((PACK / 'inventories/expected-methods.json').read_bytes())
NAMES = EXPECTED['producer']['names']
REVISION = '00e087210c24406aff49bcf3563bd4226e76660b'
TREE = '8ffa6120f3173815ff12fdcb094554f000410ffc'
IDENTITY = ('rustc 1.98.1 (48a229cea 2026-09-01)\nbinary: rustc\n'
            'commit-hash: 48a229ceaefd4985c50990b14116b6d856af0985\n'
            'commit-date: 2026-09-01\nhost: aarch64-apple-darwin\nrelease: 1.98.1\nLLVM version: 22.1.8\n')


@contextmanager
def patched(target, name, value):
    previous = getattr(target, name); setattr(target, name, value)
    try: yield
    finally: setattr(target, name, previous)


def output(names, filtered=0):
    return ('running ' + str(len(names)) + ' tests\n' + ''.join('test ' + name + ' ... ok\n' for name in names) +
            '\ntest result: ok. ' + str(len(names)) + ' passed; 0 failed; 0 ignored; 0 measured; ' +
            str(filtered) + ' filtered out; finished in 0.00s\n')


def diagnostic(name):
    code, *terms = c.API_TARGETS[name]
    return json.dumps({'level': 'error', 'message': ' '.join(terms), 'code': {'code': code},
                      'children': [], 'spans': [{'is_primary': True, 'file_name': 'api/' + name + '.rs',
                      'byte_start': start, 'byte_end': end} for start, end, _ in c.API_SOURCE_TARGETS[name][2]]}) + '\n'


class Pipe:
    def __init__(self, fd): self.fd = fd; self.closed = False
    def fileno(self): return self.fd
    def close(self): self.closed = True


class Process:
    def __init__(self, code=0):
        self.pid = 999001; self.returncode = code; self.stdout = Pipe(90001); self.stderr = Pipe(90002)
        self.waits = []
    def poll(self): return self.returncode
    def wait(self, timeout): self.waits.append(timeout); return self.returncode


class Selector:
    def __init__(self): self.keys = {}; self.closed = False
    def register(self, pipe, event, data): self.keys[pipe.fd] = SimpleNamespace(fileobj=pipe, data=data)
    def unregister(self, pipe): del self.keys[pipe.fd]
    def get_map(self): return self.keys
    def select(self, timeout): return [(value, 1) for value in list(self.keys.values())]
    def close(self): self.closed = True


class Controls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pure-', dir=HERE)
        self.addCleanup(self.temp.cleanup); self.work = Path(self.temp.name)
        self.assertEqual(offline_guard.DENIED, [])

    def test_exact_frozen_source_and_overlay(self):
        self.assertEqual(a.verify_sources(review_seal=False).PACK_TREE_SHA256, c.PACK_TREE_SHA256)
        original = (ROOT / 'scripts/ci/check-analyzer-envelope.py').read_text()
        candidate = (ROOT / a.PRODUCER / 'candidate_runner.py').read_text()
        def functions(text):
            return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
        old, new = functions(original), functions(candidate)
        for name in old.keys() - {'execute', 'verify_methods'}: self.assertEqual(old[name], new[name], name)
        self.assertEqual(hashlib.sha256(candidate.encode()).hexdigest(), '32c98f00c18ce365306c166bc170a7369a89e26b25105858f36e82c2ef6515d5')

    def test_filter_semantics_and_partition_order(self):
        groups = c.producer_groups(NAMES)
        self.assertEqual(len(groups), 18)
        self.assertEqual([n for group in groups for n in group['methods']], NAMES)
        for group in groups:
            match = [n for n in NAMES if n == group['args'][0]] if '--exact' in group['args'] else [n for n in NAMES if group['args'][0] in n]
            self.assertEqual(match, group['methods'])
        self.assertEqual(sum(len(g['methods']) == 1 for g in groups), 17)

    def test_all_partition_failure_boundaries_stop(self):
        for broken in range(1, 19):
            for corrupt_summary in (False, True):
                with self.subTest(group=broken, bad_summary=corrupt_summary):
                    work = self.work / (str(broken) + str(corrupt_summary)); work.mkdir()
                    binary = work / 'fake'; binary.write_bytes(b'inert')
                    calls = []; receipt = {}
                    def run(name, argv, **kwargs):
                        calls.append((name, argv, kwargs))
                        group = c.producer_groups(NAMES)[len(calls)-1]
                        if len(calls) == broken and not corrupt_summary: raise ValueError('first failure')
                        text = output(group['methods'], 78-len(group['methods']))
                        if len(calls) == broken: text = text.replace('0 ignored', '1 ignored')
                        return text, '', {'name': name, 'stdout': {}}
                    fake = SimpleNamespace(receipt=receipt, save=lambda: None, run=run)
                    with self.assertRaises((ValueError, RuntimeError)):
                        c.execute_test_groups(fake, 'producer', binary, PACK, work, {}, NAMES)
                    self.assertEqual(len(calls), broken)
                    self.assertEqual(len(receipt['producer_partition']['completed_groups']), broken-1)
                    self.assertFalse(receipt['producer_partition']['complete_disjoint_coverage'])

    def test_transcript_negative_matrix(self):
        names = ['a', 'b']; valid = output(names, 76)
        bad = [valid.replace('76 filtered', '0 filtered'), valid.replace('2 passed', '1 passed'),
               valid.replace('0 failed', '1 failed'), valid.replace('0 ignored', '1 ignored'),
               valid.replace('0 measured', '1 measured'), valid.replace('a ... ok', 'a ... FAILED'),
               valid.replace('a ... ok', 'b ... ok'), valid.replace('b ... ok', 'c ... ok'),
               output(list(reversed(names)), 76), valid + valid, valid.split('test result:')[0]]
        self.assertEqual(c.verify_methods(valid, names, True, 76), names)
        for transcript in bad:
            with self.subTest(text=transcript), self.assertRaises(RuntimeError): c.verify_methods(transcript, names, True, 76)

    def command(self, data=None, cap=20, total=50, prior=0, running=False, tick=0, deadline=500,
                read_error=None, stop_error=None, group_error=None, spawn_error=None, exit=0):
        work = self.work / ('case-' + str(len(list(self.work.iterdir())))); work.mkdir()
        runner = c.Commands(work, {'commands': []}, deadline); runner.output_bytes = prior
        proc = Process(None if running else exit); selector = Selector(); clock = [0]
        data = data or {90001: [b'hello', b''], 90002: [b'world', b'']}
        def mono(): value = clock[0]; clock[0] += tick; return value
        def read(fd, count):
            if read_error: raise read_error
            return data[fd].pop(0) if data[fd] else b''
        def absent(pid, sig):
            self.assertEqual((pid, sig), (proc.pid, 0))
            if group_error: raise group_error
            raise ProcessLookupError()
        def stop(child, row):
            self.assertIs(child, proc)
            if stop_error: raise stop_error
            proc.returncode = -9; row.update(child_returned=True, owned_group_gone=True, owned_group_killed=True)
        def spawn(*args, **kwargs):
            self.assertTrue(kwargs['start_new_session'])
            self.assertEqual(set(kwargs['env']) - {'PATH', 'HOME', 'TMPDIR', 'SYSTEMROOT'}, {'RUSTUP_AUTO_INSTALL', 'LC_ALL'})
            if spawn_error: raise spawn_error
            return proc
        with ExitStack() as stack:
            for obj, name, value in [(c.subprocess, 'Popen', spawn), (c.selectors, 'DefaultSelector', lambda: selector),
                    (c.os, 'read', read), (c.os, 'killpg', absent), (c.time, 'monotonic', mono),
                    (runner, 'stop_group', stop), (c, 'OUTPUT_CAP', cap), (c, 'TOTAL_OUTPUT_CAP', total)]:
                stack.enter_context(patched(obj, name, value))
            try: result = runner.run('mock', ['never-run'], cwd=work, timeout=120); error = None
            except BaseException as caught: result = None; error = caught
        return SimpleNamespace(runner=runner, row=runner.receipt['commands'][0], proc=proc,
                               result=result, error=error, selector=selector, work=work)

    def test_capture_caps_exact_eof_and_accounting(self):
        for cap, total, prior, failed, retained in [(5,10,0,False,10), (4,50,0,True,4),
                (20,7,0,True,7), (20,10,3,True,7), (5,10,1,True,9)]:
            with self.subTest(cap=cap,total=total,prior=prior):
                case = self.command(cap=cap,total=total,prior=prior)
                self.assertEqual(case.error is not None, failed)
                self.assertEqual(case.row['stdout']['bytes'] + case.row['stderr']['bytes'], retained)
                self.assertEqual(case.row['aggregate_bytes_after'], prior+retained)
                self.assertEqual(case.row['output_capped'], failed)
                if not failed: self.assertTrue(all(case.row['pipe_eof'].values()))
                self.assertTrue(case.proc.stdout.closed and case.proc.stderr.closed and case.selector.closed)

    def test_cumulative_deadline_dominates_per_group_deadline(self):
        case = self.command(running=True, tick=11, deadline=10)
        self.assertIsInstance(case.error, TimeoutError); self.assertEqual(case.row['timeout_seconds'], 10)
        self.assertTrue(case.row['timed_out']); self.assertFalse(any(case.row['pipe_eof'].values()))

    def test_primary_error_and_unresolved_custody_are_preserved(self):
        first = ValueError('read failed'); case = self.command(read_error=first, stop_error=PermissionError('denied'))
        self.assertIs(case.error, first); self.assertIs(case.runner.active, case.proc)
        self.assertTrue(case.row['custody_hold']); self.assertFalse(case.row['owned_group_gone'])
        with self.assertRaisesRegex(RuntimeError, 'Only one synchronous child'):
            case.runner.run('forbidden', ['never'], cwd=self.work)
        with self.assertRaisesRegex(RuntimeError, 'Owned children/groups'):
            c.preserve_and_cleanup(self.work, self.work, None, None, set(), case.runner)

    def test_group_observation_permission_is_not_absence(self):
        denied = PermissionError('permission ambiguous')
        case = self.command(group_error=denied, stop_error=denied)
        self.assertIs(case.error, denied); self.assertTrue(case.row['custody_hold'])
        self.assertFalse(case.row['owned_group_gone'])

    def test_spawn_failure_has_no_fabricated_process_receipt(self):
        err = OSError('spawn failed'); case = self.command(spawn_error=err)
        self.assertIs(case.error, err); self.assertNotIn('pid', case.row)
        self.assertFalse(case.row['child_returned']); self.assertFalse(case.row['owned_group_gone'])

    def test_stop_group_is_bounded_and_permission_fail_closed(self):
        work = self.work / 'stop'; work.mkdir(); runner = c.Commands(work, {'commands': []}, 500)
        proc = Process(-9); row = {}; calls = []; times = iter([0,1,6])
        def kill(pid, sig): calls.append((pid,sig))
        with patched(c.os, 'killpg', kill), patched(c.time, 'monotonic', lambda: next(times)), patched(c.time, 'sleep', lambda _: None):
            runner.stop_group(proc, row)
        self.assertEqual(proc.waits, [5]); self.assertTrue(row['child_returned']); self.assertFalse(row['owned_group_gone'])
        self.assertEqual(len(calls), 3)
        def deny(*_): raise PermissionError('deny')
        with patched(c.os, 'killpg', deny), self.assertRaises(PermissionError): runner.stop_group(proc,{})

    def test_environment_injections_removed(self):
        with patched(os, 'environ', {'PATH':'/known', 'HOME':'/home', 'RUSTFLAGS':'injected', 'DYLD_INSERT_LIBRARIES':'injected', 'PYTHONPATH':'injected'}):
            case = self.command()
        self.assertIsNone(case.error)
        self.assertEqual(case.row['environment'], {'PATH':'/known','HOME':'/home','RUSTUP_AUTO_INSTALL':'0','LC_ALL':'C'})

    def test_dispatch_context_negative_matrix(self):
        env = dict(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='snowdamiz/mixer',
                   GITHUB_RUN_ATTEMPT='1', RUNNER_OS='macOS', RUNNER_ARCH='ARM64', MIXER_RUNNER_ENVIRONMENT='github-hosted',
                   MIXER_REVIEWED_SHA=REVISION, GITHUB_SHA=REVISION, GITHUB_RUN_ID='123')
        self.assertEqual(a.context(env)['revision'], REVISION)
        for key in env:
            bad = {**env, key: 'invalid'}
            with self.subTest(key=key), self.assertRaises(RuntimeError): a.context(bad)

    def test_complete_execute_and_terminal_replay_with_only_fake_children(self):
        self.complete_mock()

    def complete_mock(self, wrong_oracle=False):
        bundle = self.work / 'run'; bundle.mkdir(); out = c.fresh_output(bundle / 'fixture', root=self.work)
        toolchain = self.work / 'toolchain'; (toolchain / 'bin').mkdir(parents=True)
        compiler = toolchain / 'bin/rustc'; compiler.write_bytes(b'inert compiler model, never executable')
        case = self
        class FakeCommands:
            def __init__(self, out, receipt, deadline):
                self.out=out; self.receipt=receipt; self.active=None; self.deadline=deadline; self.total=0
                (out/'commands').mkdir()
            def save(self): c.write_json(self.out/'receipt.json',self.receipt)
            def run(self,name,argv,*,cwd,env=None,timeout=15,negative=False):
                text=''; stderr=''; argv=list(map(str,argv))
                if name.startswith('revision-'): text=REVISION+'\n'
                elif name.startswith('git-tree-'): text=TREE+'\n'
                elif name=='python-version': text=sys.version+'\n'
                elif name=='compiler-sysroot-selection': text=str(toolchain)+'\n'
                elif name=='rustc-verbose': text=IDENTITY
                elif name.endswith('-list'):
                    names=NAMES if name=='producer-list' else EXPECTED['independent_exact_source']['names']
                    text=''.join(n+': test\n' for n in names)+'\n'+str(len(names))+' tests, 0 benchmarks\n'
                elif name.startswith('producer-') and name not in ('producer-compile','producer-list'):
                    group=next(g for g in c.producer_groups(NAMES) if name=='producer-'+g['name'])
                    text=output(group['methods'],78-len(group['methods']))
                    if name=='producer-embedded':
                        layouts=json.loads((PACK/'inventories/expected-host-layouts.json').read_bytes())
                        text+='CORRECTED_ACTUAL_COMPLETE_LAYOUTS='+json.dumps([r['bytes'] for r in layouts['layouts']])+'\n'
                        text+='ENVELOPE_ORACLE_CASES='+('16169' if wrong_oracle else '16170')+'\nCORRECTED_FINITE_BUDGET_CASES=5544\n'
                elif name=='independent-execute': text=output(EXPECTED['independent_exact_source']['names'])
                elif name.startswith('api-negative-'): stderr=diagnostic(name.removeprefix('api-negative-'))
                if '-o' in argv and not negative: Path(argv[argv.index('-o')+1]).write_bytes(b'inert product model')
                row=dict(name=name,argv=argv,cwd=str(cwd),timeout_seconds=timeout,exit=1 if negative else 0,
                         child_returned=True,owned_group_gone=True,custody_hold=False,timed_out=False,output_capped=False,
                         pipe_eof={'stdout':True,'stderr':True},errors=[],aggregate_bytes_before=self.total)
                for label,data in [('stdout',text.encode()),('stderr',stderr.encode())]:
                    path='commands/'+name+'.'+label; (self.out/path).write_bytes(data)
                    row[label]={'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}; self.total+=len(data)
                row['aggregate_bytes_after']=self.total
                self.receipt['commands'].append(row); c.write_json(self.out/'commands'/(name+'.json'),row); self.save()
                return text,stderr,row
        with ExitStack() as stack:
            for obj,name,value in [(c,'Commands',FakeCommands),(c.shutil,'which',lambda value:str(compiler)),
                    (c.platform,'platform',lambda:'mock macOS'),(c.signal,'getsignal',lambda _:None),
                    (c.signal,'signal',lambda *args:None),(c.signal,'setitimer',lambda *args:None)]:
                stack.enter_context(patched(obj,name,value))
            with redirect_stdout(io.StringIO()): result=c.execute(out,str(compiler))
        receipt=json.loads((out/'receipt.json').read_bytes())
        if wrong_oracle:
            self.assertEqual(result,1); self.assertEqual(receipt['commands'][-1]['name'],'producer-root-16')
            self.assertNotIn('independent',receipt['test_binaries']); return
        self.assertEqual(result,0); self.assertEqual(len(receipt['commands']),40)
        admitted={'revision':REVISION,'compiler':str(compiler),'compiler_sha256':c.sha(compiler)}
        self.assertEqual(a.replay(bundle,admitted,c)['commands'],40)
        self.assertFalse((out/'scratch').exists())
        for label,mutate in [('missing-command',lambda r:r['commands'].pop()),
                ('wrong-revision',lambda r:r.update(revision_after='f'*40)),
                ('held',lambda r:r['commands'][0].update(custody_hold=True)),
                ('false-cleanup',lambda r:r['cleanup'].update(removed=False)),
                ('postflight',lambda r:r['postflight']['pack'].update(passed=False))]:
            changed=deepcopy(receipt); mutate(changed); c.write_json(out/'receipt.json',changed)
            with self.subTest(mutation=label),self.assertRaises(RuntimeError): a.replay(bundle,admitted,c)
        c.write_json(out/'receipt.json',receipt)

    def test_wrong_oracle_halts_before_independent_or_api_commands(self):
        self.complete_mock(wrong_oracle=True)

    def test_compiler_selection_is_exact(self):
        layouts = json.loads((PACK/'inventories/expected-host-layouts.json').read_bytes())
        identity = c.rustc_identity(IDENTITY)
        self.assertEqual(c.select_host_target(identity,layouts)['actual_release'],'1.98.1')
        self.assertEqual(c.select_host_target({**identity,'release':'1.99.0'},layouts)['actual_release'],'1.99.0')
        for change in [{'release':'1.99.1'},{'host':'x86_64-apple-darwin'},{'release':'1.98.1-nightly'}]:
            with self.subTest(change=change),self.assertRaises(RuntimeError): c.select_host_target({**identity,**change},layouts)

    def test_all_api_targets_and_wrong_span_refusal(self):
        row={'exit':1,'timed_out':False,'child_returned':True,'owned_group_gone':True}
        for name in c.API_TARGETS:
            with self.subTest(probe=name):
                accepted=c.verify_negative(name,diagnostic(name),PACK/'api'/(name+'.rs'),self.work/'absent',row)
                self.assertEqual(len(accepted),len(c.API_SOURCE_TARGETS[name][2]))
                bad=json.loads(diagnostic(name)); bad['spans'][0]['byte_start']+=1
                with self.assertRaises(RuntimeError):
                    c.verify_negative(name,json.dumps(bad),PACK/'api'/(name+'.rs'),self.work/'absent',row)

    def test_workflow_is_manual_single_invocation_no_installer(self):
        text=(HERE/'workflow-proposal.yml').read_text()
        self.assertIn('workflow_dispatch:',text); self.assertNotIn('push:',text); self.assertNotIn('pull_request:',text)
        self.assertEqual(text.count('candidate_runner.py \\'),1)
        self.assertIn('macos-15',text); self.assertIn('cancel-in-progress: false',text)
        for forbidden in ['rustup toolchain install','curl ','wget ','verify_packet.py','test_candidate.py','/.github/workflows/verify.yml','/hosted/']:
            self.assertNotIn(forbidden,text)
        self.assertTrue(all(str(n) in (HERE/'admission.py').read_text() for n in [40,78,14,21714]))

    def test_no_runtime_operations_attempted(self):
        self.assertEqual(offline_guard.DENIED,[])


if __name__=='__main__':
    logs=HERE/'logs'; logs.mkdir(exist_ok=True)
    stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    report=stream.getvalue(); print(report,end=''); (logs/'controls.stdout').write_text(report)
    evidence={'schema':1,'command':'python3 -B verification/envelope-partition-independent-review/review_controls.py',
              'python':sys.version,'interpreter':sys.executable,'source_baseline_head':REVISION,'source_baseline_tree':TREE,
              'source_revision_scope':'Parent-supplied baseline only; selection commit pending; immutable inputs rehashed; no Git operations',
              'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
              'success':result.wasSuccessful(),'denied_runtime_attempts':offline_guard.DENIED,
              'review_source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir()) if p.suffix in {'.py','.yml'}},
              'scope':'Actual Python candidate orchestration with fake children/clocks and inert compiler products only; no runtime or custody qualification'}
    (logs/'controls.json').write_text(json.dumps(evidence,sort_keys=True,indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
