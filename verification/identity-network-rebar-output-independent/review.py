#!/usr/bin/env python3
"""Independent pure review. Never invokes compiler, container, socket or child."""
from pathlib import Path
import ast, contextlib, copy, hashlib, importlib.util, json, os, signal, stat, sys, tempfile, time, unittest

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PACKET = ROOT / 'verification/identity-network-rebar-output-correction'
TEMP = BASE / 'temporary'
TEMP.mkdir(exist_ok=True)
tempfile.tempdir = str(TEMP)
sys.dont_write_bytecode = True
events, denials = {}, []
def audit(event, args):
    events[event] = events.get(event, 0) + 1
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.posix_spawnp', 'os.fork', 'os.forkpty', 'os.exec', 'pty.spawn', 'ctypes.dlopen', 'os.kill'} or event.startswith('socket.'):
        denials.append({'event': event})
        raise RuntimeError('review forbids process/socket/native/custody operation')
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).absolute()
        if str(path).startswith(('/proc/', '/dev/')) or any(p in path.parts for p in ('.ssh', '.aws', '.wrangler', 'FieldLog')):
            denials.append({'event': event, 'path': str(path)})
            raise RuntimeError('review forbids held or private custody')
        mode, flags = args[1], args[2]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and not path.is_relative_to(BASE):
            denials.append({'event': event, 'path': str(path)})
            raise RuntimeError('review writes only within owned sibling')
sys.addaudithook(audit)
for event, args in [('subprocess.Popen', ()), ('socket.__new__', ()), ('ctypes.dlopen', ()), ('os.kill', (20745, 0)), ('open', ('/proc/20745/status', 'r', 0)), ('open', ('/private/FieldLog/secret', 'r', 0)), ('open', (str(ROOT / 'hosted/forbidden-write'), 'w', os.O_WRONLY))]:
    try: sys.audit(event, *args)
    except RuntimeError: pass
    else: raise AssertionError('audit did not refuse ' + event)
self_tests = denials[:]
denials.clear()
signal.alarm(50)
start = time.monotonic()
def row(body): return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
def digest(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def save(name, value): (BASE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
def verify_packet(base, expected):
    raw = (base / 'packet-manifest.json').read_bytes()
    assert row(raw)['sha256'] == expected
    manifest = json.loads(raw)
    actual = {}
    for p in sorted(base.rglob('*')):
        assert not p.is_symlink(), str(p)
        if p.is_file() and p != base / 'packet-manifest.json': actual[str(p.relative_to(base))] = row(p.read_bytes())
    assert actual == manifest['files']
    assert digest(actual) == manifest['tree_digest_sha256']
    return {'files': len(actual), 'packet_manifest': row(raw), 'tree_digest_sha256': digest(actual)}

checks = {'correction': verify_packet(PACKET, 'd56a5dde00bc61888d5cdf690cf0e44bf11430ac3bb82a819d3206de390349ac'),
          'actual_runtime_review': verify_packet(ROOT / 'verification/github-delivery-binary-export-and-ui/network-review', '148912f1c031a1bdd757376436cd4959235b170f7dd2ae60e6c38df2d6a96d8c')}
bindings = json.loads((PACKET / 'source-bindings.json').read_bytes())
for path, expected in bindings.items(): assert row((ROOT / path).read_bytes()) == row((PACKET / 'after' / path).read_bytes()) == expected
assert digest(bindings) == '163073180bacc272e3d19209508cf9e625950f1afb8bc7a5b6b1b1c27ae9bf91'
checks['canonical_source'] = {'files': bindings, 'tree_digest_sha256': digest(bindings)}
protected = {'.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57', 'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
for path, expected in protected.items(): assert row((ROOT / path).read_bytes())['sha256'] == expected
checks['protected_sha256'] = protected
source = (ROOT / 'hosted/scripts/test-identity-network.py').read_text()
before = (PACKET / 'before/hosted/scripts/test-identity-network.py').read_text()
def functions(s):
    out = {}
    for n in ast.parse(s).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): out[n.name] = ast.get_source_segment(s, n)
        elif isinstance(n, ast.ClassDef):
            out.update({n.name + '.' + f.name: ast.get_source_segment(s, f) for f in n.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))})
    return out
oldf, newf = functions(before), functions(source)
assert {key for key in oldf if newf.get(key) != oldf[key]} == {'Collector.collect'}
checks['unchanged_existing_python_functions_except_collect'] = len(oldf) - 1
def assignments(s): return {n.targets[0].id: ast.dump(n.value) for n in ast.parse(s).body if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
olda, newa = assignments(before), assignments(source)
assert {key for key in olda if newa.get(key) != olda[key]} == {'MANIFEST_EXS'}
checks['only_changed_existing_assignment'] = 'MANIFEST_EXS'
oldtests = functions((PACKET / 'before/hosted/scripts/test_identity_network_collector.py').read_text())
newtests = functions((ROOT / 'hosted/scripts/test_identity_network_collector.py').read_text())
prior = {k: v for k, v in oldtests.items() if '.test_' in k}
assert len(prior) == 111 and all(newtests[k] == v for k, v in prior.items())
checks['111_prior_tests_exact'] = True
save('source-verification.json', checks)

spec = importlib.util.spec_from_file_location('reviewed_controls', ROOT / 'hosted/scripts/test_identity_network_collector.py')
controls = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = controls
spec.loader.exec_module(controls)
collector = controls.collector
suite = unittest.defaultTestLoader.loadTestsFromModule(controls)
with (BASE / 'controls.stderr').open('w') as log, (BASE / 'controls.stdout').open('w') as stdout:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(log):
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
assert result.testsRun == 126 and result.wasSuccessful()

class IndependentProbes(unittest.TestCase):
    def setUp(self): self.fixture = controls.GeneratedCompilerOutputControls()
    def test_nested_parent_and_type_mutation_matrix(self):
        n = 0
        for path in collector.GENERATED_DAG_PARENTS:
            for field, value in [('uid', False), ('gid', 0.0), ('mode', 493.0), ('mode', 0o4755), ('type', 'directory\0'), ('extra', 0)]:
                candidate = self.fixture.row(); candidate['parents'][path][field] = value
                with self.assertRaises(collector.CollectorError): collector.validate_generated_dag_row(candidate)
                n += 1
        self.assertEqual(54, n)
    def test_exact_maximum_and_zero_capture(self):
        with tempfile.TemporaryDirectory() as d:
            body = bytes(range(256)) * 256
            subject = self.fixture.subject(d, body)
            captured = subject.capture_generated_dag(controls.owned('test'), self.fixture.row(body))
            self.assertEqual(65536, captured['bytes'])
            self.assertEqual(body, (subject.output / 'compiler-generated/telemetry-source.dag').read_bytes())
        with tempfile.TemporaryDirectory() as d:
            subject = self.fixture.subject(d, b'')
            with self.assertRaises(collector.CollectorError): subject.capture_generated_dag(controls.owned('test'), self.fixture.row(b'x'))
            receipt = json.loads((subject.output / 'compiler-generated/telemetry-source.json').read_bytes())
            self.assertEqual(0, receipt['bytes'])
            self.assertTrue(receipt['stdout_complete'])
    def test_known_capture_preserved_before_immutable_input_rejection(self):
        prepared, compiled = self.fixture.fixture()
        compiled['helpers']['collector-manifest.exs']['sha256'] = '0' * 64
        body = b'opaque inert DAG fixture\x00\x80\xff'
        with tempfile.TemporaryDirectory() as d:
            subject = self.fixture.subject(d, body)
            subject.capture_generated_dag(controls.owned('test'), compiled['deps'][collector.GENERATED_DAG_PATH])
            with self.assertRaises(collector.CollectorError): collector.validate_compiled_source_unchanged(prepared, compiled)
            self.assertEqual(body, (subject.output / 'compiler-generated/telemetry-source.dag').read_bytes())
    def test_invalid_row_rejects_before_export_and_does_not_mutate_manifests(self):
        prepared, compiled = self.fixture.fixture()
        frozen = copy.deepcopy((prepared, compiled))
        for field, value in [('uid', 0.0), ('gid', False), ('links', 1.0), ('mode', 420.0), ('sha256', 'A' * 64), ('parents', [])]:
            with tempfile.TemporaryDirectory() as d:
                expected = self.fixture.row(); expected[field] = value
                subject = self.fixture.subject(d, b'x')
                with self.assertRaises(collector.CollectorError): subject.capture_generated_dag(controls.owned('test'), expected)
                self.assertEqual(0, subject.command_number)
        self.assertEqual(frozen, (prepared, compiled))
    def test_helper_dispatch_exact_and_no_dag_decoder(self):
        helper = collector.MANIFEST_EXS
        self.assertEqual(3380, len(helper.encode()))
        self.assertEqual('a3d8461e7b399df162c0110892cd9cc32fbac2b3b3b552d76769745977173d30', row(helper.encode())['sha256'])
        for token in ['binary_to_term', 'Code.eval', 'System.cmd', ':os.cmd', ':erlang.apply']:
            self.assertNotIn(token, helper)
        self.assertEqual(1, helper.count('["export-generated"] ->'))
    def test_alias_rows_and_removal_fail_final_comparison(self):
        _, compiled = self.fixture.fixture()
        for alias in [collector.GENERATED_DAG_PATH.upper(), './' + collector.GENERATED_DAG_PATH, collector.GENERATED_DAG_PATH + '/', collector.GENERATED_DAG_PATH + '\0']:
            after = copy.deepcopy(compiled)
            after['deps'][alias] = after['deps'].pop(collector.GENERATED_DAG_PATH)
            with self.assertRaises(collector.CollectorError): collector.validate_source_unchanged(compiled, after)

with (BASE / 'probes.stderr').open('w') as log:
    probes = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentProbes))
assert probes.wasSuccessful()
assert not denials
assert not list(TEMP.iterdir())
TEMP.rmdir()
signal.alarm(0)
save('execution.json', {'schema': 1, 'argv': ['python3', '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version, 'alarm_seconds': 50, 'seconds': round(time.monotonic() - start, 3), 'producer_controls': result.testsRun, 'independent_probe_methods': probes.testsRun, 'status': 'passed', 'audit_self_tests': self_tests, 'unexpected_denials': denials, 'audit_event_counts': events, 'cleanup': 'all owned TemporaryDirectories and temporary root removed', 'new_compiler_container_PG_native_UI_network_or_child_execution': False, 'held_custody_probes': False, 'elixir_runtime_qualification': False})
print(json.dumps({'status': 'passed', 'producer_controls': result.testsRun, 'independent_probes': probes.testsRun, 'correction_files': checks['correction']['files'], 'actual_review_files': checks['actual_runtime_review']['files'], 'seconds': round(time.monotonic() - start, 3)}, sort_keys=True))
