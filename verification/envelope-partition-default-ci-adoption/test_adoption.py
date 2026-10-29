#!/usr/bin/env python3
"""Guarded source, compiler-contract and synthetic orchestration controls only."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
import offline_guard
offline_guard.install(HERE)
import ast
from contextlib import ExitStack, contextmanager, redirect_stdout
from copy import deepcopy
import difflib
import hashlib
import io
import json
import os
from types import SimpleNamespace
import tempfile
import unittest
import adopt_envelope as a
c, BASE, PROOF = a.load_runner()
ROOT = HERE.parents[1]
PACK = ROOT / c.PACK
EXPECTED = json.loads((PACK / 'inventories/expected-methods.json').read_bytes())
NAMES = EXPECTED['producer']['names']
REVISION = '6d57e05e58e6d614e58a0a4dc0fad661264fb46f'
TREE = 'f' * 40  # Synthetic tree value; no Git operation.
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
        scratch = HERE / 'control-scratch'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='pure-', dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.assertEqual(offline_guard.DENIED, [])

    @classmethod
    def tearDownClass(cls):
        scratch = HERE / 'control-scratch'
        if scratch.exists():
            if list(scratch.iterdir()):
                raise RuntimeError('Unremoved synthetic control scratch')
            scratch.rmdir()
        if offline_guard.DENIED:
            raise RuntimeError('Unexpected denied operations: ' + repr(offline_guard.DENIED))

    def proposed(self):
        text = (HERE / 'workflow/original-verify.yml').read_text()
        for row in json.loads((HERE / 'workflow/changes.json').read_bytes())['changes']:
            self.assertEqual(text.count(row['before']), 1)
            text = text.replace(row['before'], row['after'])
        return text

    def test_seal_dependencies_frozen_pack_and_candidate_source(self):
        proof = a.verify()
        self.assertEqual(proof['fixture_source']['sha256'],
                         '32c98f00c18ce365306c166bc170a7369a89e26b25105858f36e82c2ef6515d5')
        self.assertEqual(c.verify_pack(PACK)['member_count'], 86)
        overlay = json.loads((ROOT / 'verification/envelope-producer-timeout-experiment/overlay.json').read_bytes())
        text = a.BASE_RUNNER.read_text()
        for row in overlay['changes']:
            self.assertEqual(text.count(row['before']), 1)
            text = text.replace(row['before'], row['after'])
        self.assertEqual(text, (a.PRODUCER / 'candidate_runner.py').read_text())

    def test_exact_minimal_workflow_diff_preserves_every_other_job_and_step(self):
        before = (HERE / 'workflow/original-verify.yml').read_text()
        after = self.proposed()
        self.assertEqual(a.job_text(after), (HERE / 'workflow/swift-job.yml').read_text())
        expected = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                          fromfile='a/.github/workflows/verify.yml', tofile='b/.github/workflows/verify.yml'))
        self.assertEqual(expected, (HERE / 'workflow.diff').read_text())
        self.assertEqual(before.replace(a.job_text(before), ''), after.replace(a.job_text(after), ''))
        changes = json.loads((HERE / 'workflow/changes.json').read_bytes())['changes']
        old, new = a.job_text(before), a.job_text(after)
        for row in changes:
            old = old.replace(row['before'], row['after'])
        self.assertEqual(old, new)
        self.assertEqual(len(changes), 2)

    def test_installed_job_identity_is_required_and_rejects_source_drift(self):
        workflow = self.work / 'verify.yml'
        workflow.write_text(self.proposed())
        with patched(a, 'WORKFLOW', workflow):
            self.assertTrue(a.verify(installed=True)['installed_job_verified'])
            workflow.write_text(self.proposed().replace('timeout-minutes: 12', 'timeout-minutes: 13'))
            with self.assertRaisesRegex(RuntimeError, 'Installed ordinary'):
                a.verify(installed=True)

    def test_sparse_closure_includes_all_inputs_and_no_local_preservation_anchors(self):
        job = (HERE / 'workflow/swift-job.yml').read_text()
        sparse = job.split('          sparse-checkout: |\n', 1)[1].split('      - name:', 1)[0]
        entries = [line.strip().lstrip('/') for line in sparse.splitlines() if line.strip()]
        for row in json.loads((HERE / 'dependencies.json').read_bytes())['members']:
            name = row['path']
            self.assertTrue(any(name == entry or entry.endswith('/') and name.startswith(entry)
                                for entry in entries) or not name.startswith('verification/'), name)
        for bad in ['verify_packet.py', 'test_candidate.py', '/hosted/', '/.wrangler', '/ci-review/',
                    'corrected-host-diagnostics-actual-results', 'envelope-partition-independent-review',
                    'envelope-partition-workflow-context-correction']:
            self.assertNotIn(bad, sparse)
        names = [r['path'] for r in json.loads((HERE / 'dependencies.json').read_bytes())['members']]
        self.assertEqual(len(names), 93)
        self.assertFalse(any('/hosted' in n or '/logs/' in n or '/ci-review/' in n for n in names))

    def test_workflow_one_invocation_no_install_finite_limits_and_always_postflight(self):
        job = (HERE / 'workflow/swift-job.yml').read_text()
        span = (HERE / 'workflow/envelope-steps.yml').read_text()
        self.assertEqual(span.count('adopt_envelope.py" run '), 1)
        self.assertEqual(span.count('test_adoption.py"'), 1)
        self.assertEqual(span.count('adopt_envelope.py" verify --workflow-installed'), 2)
        self.assertEqual(span.count('        if: always()'), 2)
        self.assertIn('timeout-minutes: 12', span)
        self.assertGreater(12 * 60, 480 + 60)
        self.assertIn('export RUSTUP_AUTO_INSTALL=0', span)
        for bad in ['rustup toolchain install', 'continue-on-error:', 'retry', 'RUSTUP_TOOLCHAIN',
                    'check-analyzer-envelope.py \\']:
            self.assertNotIn(bad, span)
        self.assertIn('    timeout-minutes: 30', job)
        for expression in span.split('${{')[1:]:
            self.assertIn(expression.split('}}', 1)[0].strip(), {'github.sha', 'github.workspace', 'runner.temp'})

    def test_ordinary_compiler_exact_functions_and_allowlist_are_reused(self):
        def definitions(path):
            text = path.read_text()
            return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body
                    if isinstance(n, ast.FunctionDef)}
        original = definitions(a.BASE_RUNNER)
        candidate = definitions(a.PRODUCER / 'candidate_runner.py')
        for name in a.POLICY_FUNCTIONS:
            self.assertEqual(original[name], candidate[name])
            self.assertIs(getattr(c, name), getattr(BASE, name))
            self.assertIs(getattr(c, name).__globals__, BASE.__dict__)
        layouts = json.loads((PACK / 'inventories/expected-host-layouts.json').read_bytes())
        identity = c.rustc_identity(IDENTITY)
        for release in ['1.98.1', '1.99.0']:
            self.assertEqual(c.select_host_target({**identity, 'release': release}, layouts)['actual_release'], release)
        for change in [{'release':'1.99.1'}, {'release':'1.98.1-nightly'}, {'host':'x86_64-apple-darwin'},
                       {'host':'aarch64-unknown-linux-gnu'}, {'release':None}]:
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                c.select_host_target({**identity, **change}, layouts)
        for bad in [IDENTITY.replace('release: 1.98.1','release: 1.99.0'),
                    IDENTITY + 'host: aarch64-apple-darwin\n',
                    IDENTITY.replace('2026-09-01','2026-02-30'),
                    IDENTITY.replace('LLVM version: 22.1.8\n',''),
                    IDENTITY.replace('commit-hash: 48','commit-hash: ab')]:
            with self.subTest(identity=bad), self.assertRaises((RuntimeError, ValueError)):
                c.rustc_identity(bad)

    def test_binding_missing_mutated_and_symlink_refused(self):
        source = self.work / 'source.py'
        source.write_text('frozen')
        row = {'path':'source.py', 'bytes':6, 'sha256':a.sha(source)}
        a.check_rows(self.work, [row])
        source.write_text('mutate')
        with self.assertRaises(RuntimeError): a.check_rows(self.work, [row])
        source.unlink()
        with self.assertRaises((RuntimeError, OSError)): a.check_rows(self.work, [row])
        target = self.work / 'owned-target.py'
        target.write_text('frozen')
        source.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, 'Symlink forbidden'):
            a.check_rows(self.work, [row])
        for name in ['../escape', '/absolute', './source.py']:
            with self.assertRaises(RuntimeError): a.row_path(self.work, {**row,'path':name})

    def test_install_disallowed_before_output_or_runner_admission(self):
        target = self.work / 'never-created'
        with patched(a.os, 'environ', {'RUSTUP_AUTO_INSTALL':'1','GITHUB_SHA':REVISION}), \
             patched(a, 'load_runner', lambda: self.fail('Runner must not load')):
            with self.assertRaisesRegex(RuntimeError, 'installation forbidden'):
                a.run_fixture(target, '/synthetic/rustc')
        self.assertFalse(target.exists())

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

    def test_environment_injections_removed(self):
        with patched(os, 'environ', {'PATH':'/known', 'HOME':'/home', 'RUSTFLAGS':'injected', 'DYLD_INSERT_LIBRARIES':'injected', 'PYTHONPATH':'injected'}):
            case = self.command()
        self.assertIsNone(case.error)
        self.assertEqual(case.row['environment'], {'PATH':'/known','HOME':'/home','RUSTUP_AUTO_INSTALL':'0','LC_ALL':'C'})

    def test_all_api_targets_and_wrong_span_refusal(self):
        row={'exit':1,'timed_out':False,'child_returned':True,'owned_group_gone':True}
        for name in c.API_TARGETS:
            with self.subTest(probe=name):
                accepted=c.verify_negative(name,diagnostic(name),PACK/'api'/(name+'.rs'),self.work/'absent',row)
                self.assertEqual(len(accepted),len(c.API_SOURCE_TARGETS[name][2]))
                bad=json.loads(diagnostic(name)); bad['spans'][0]['byte_start']+=1
                with self.assertRaises(RuntimeError):
                    c.verify_negative(name,json.dumps(bad),PACK/'api'/(name+'.rs'),self.work/'absent',row)

    def complete_mock(self, wrong_oracle=False):
        bundle = self.work / 'run'; bundle.mkdir(); out = bundle / 'fixture'
        toolchain = self.work / 'toolchain'; (toolchain / 'bin').mkdir(parents=True)
        compiler = toolchain / 'bin/rustc'; compiler.write_bytes(b'inert compiler model, never executable')
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
        real_verify = a.verify
        original_fresh = c.fresh_output
        with ExitStack() as stack:
            for obj,name,value in [(c,'Commands',FakeCommands),(c.shutil,'which',lambda value:str(compiler)),
                    (c.platform,'platform',lambda:'mock macOS'),(c.signal,'getsignal',lambda _:None),
                    (c.signal,'signal',lambda *args:None),(c.signal,'setitimer',lambda *args:None),
                    (a,'verify',lambda installed=False:real_verify(False)),
                    (a,'load_runner',lambda:(c,BASE,PROOF)),
                    (c,'fresh_output',lambda p:original_fresh(p,root=self.work)),
                    (a.os,'environ',{**os.environ,'RUSTUP_AUTO_INSTALL':'0','GITHUB_SHA':REVISION})]:
                stack.enter_context(patched(obj,name,value))
            with redirect_stdout(io.StringIO()): result=a.run_fixture(out,str(compiler))
        receipt=json.loads((out/'receipt.json').read_bytes())
        if wrong_oracle:
            self.assertEqual(result,1); self.assertEqual(receipt['commands'][-1]['name'],'producer-root-16')
            self.assertNotIn('independent',receipt['test_binaries']); return
        self.assertEqual(result,0); self.assertEqual(len(receipt['commands']),40)
        admitted={'revision':REVISION,'compiler':str(compiler),'compiler_sha256':c.sha(compiler)}
        replay = a.module_at('synthetic_terminal_replay', HERE / 'terminal_replay.py')
        self.assertEqual(replay.replay(out,admitted,c)['commands'],40)
        start=json.loads((out/'adapter-start.json').read_bytes())
        finish=json.loads((out/'adapter-result.json').read_bytes())
        self.assertTrue(all(start['ordinary_functions_reused_exactly'].values()))
        self.assertEqual(finish['terminal_replay']['commands'],40)
        self.assertEqual(finish['actual_compiler'],receipt['rustc'])
        for name, digest in start['source_snapshots'].items():
            self.assertEqual(a.sha(out/name),digest)
        self.assertFalse((out/'scratch').exists())
        for label,mutate in [('missing-command',lambda r:r['commands'].pop()),
                ('wrong-revision',lambda r:r.update(revision_after='e'*40)),
                ('held',lambda r:r['commands'][0].update(custody_hold=True)),
                ('false-cleanup',lambda r:r['cleanup'].update(removed=False)),
                ('postflight',lambda r:r['postflight']['pack'].update(passed=False))]:
            changed=deepcopy(receipt); mutate(changed); c.write_json(out/'receipt.json',changed)
            with self.subTest(mutation=label),self.assertRaises(RuntimeError): replay.replay(out,admitted,c)
        c.write_json(out/'receipt.json',receipt)

    def test_complete_40_command_adoption_with_fake_children(self):
        self.complete_mock()

    def test_wrong_oracle_halts_before_independent_and_api(self):
        self.complete_mock(wrong_oracle=True)

    def test_failed_or_raising_fixture_always_gets_source_postflight_and_no_retry(self):
        for failure in ['return-failure', 'raise', 'postflight-failure']:
            with self.subTest(failure=failure):
                output_path = self.work / failure
                calls = []
                checks = []
                real_verify = a.verify
                original_fresh = c.fresh_output
                compiler = {'identity':{'release':'1.98.1','host':'aarch64-apple-darwin'},'synthetic':True}
                def fake_execute(out, requested):
                    calls.append(requested)
                    c.write_json(out / 'receipt.json', {'status':'failed','rustc':compiler})
                    if failure == 'raise':
                        raise TimeoutError('synthetic invocation timeout')
                    return 1
                def fake_verify(installed=False):
                    checks.append(installed)
                    if failure == 'postflight-failure' and len(checks) > 1:
                        raise RuntimeError('synthetic source mutation')
                    return real_verify(False)
                with ExitStack() as stack:
                    for obj,name,value in [(a,'verify',fake_verify),
                            (a,'load_runner',lambda:(c,BASE,PROOF)),
                            (c,'fresh_output',lambda p:original_fresh(p,root=self.work)),
                            (c,'execute',fake_execute),
                            (a.os,'environ',{**os.environ,'RUSTUP_AUTO_INSTALL':'0','GITHUB_SHA':REVISION})]:
                        stack.enter_context(patched(obj,name,value))
                    self.assertEqual(a.run_fixture(output_path,'/synthetic/rustc'),1)
                self.assertEqual(calls,['/synthetic/rustc'])
                self.assertEqual(checks,[True,True])
                finish=json.loads((output_path/'adapter-result.json').read_bytes())
                self.assertEqual(finish['actual_compiler'],compiler)
                self.assertIsNone(finish['terminal_replay'])
                if failure=='raise':
                    self.assertEqual(finish['adapter_exception']['type'],'TimeoutError')
                if failure=='postflight-failure':
                    self.assertEqual(finish['errors'][0]['phase'],'source-postflight')

    def test_guard_precedes_subject_imports_and_sees_no_real_operations(self):
        source=Path(__file__).read_text()
        self.assertLess(source.index('offline_guard.install(HERE)'),source.index('import adopt_envelope as a'))
        self.assertEqual(offline_guard.DENIED,[])


if __name__ == '__main__':
    program = unittest.main(exit=False)
    print(json.dumps({'schema':1, 'tests':program.result.testsRun,
        'failures':len(program.result.failures), 'errors':len(program.result.errors),
        'skipped':len(program.result.skipped), 'passed':program.result.wasSuccessful(),
        'python':sys.version, 'interpreter':sys.executable,
        'denied_operation_attempts':offline_guard.DENIED,
        'control_scratch_absent':not (HERE/'control-scratch').exists(),
        'compiler_producer_product_native_runtime_runs':0,
        'scope':'Guarded pure source/contract tests and actual Python orchestration with fake children, streams, clocks and inert products only'},sort_keys=True))
    sys.exit(0 if program.result.wasSuccessful() else 1)
