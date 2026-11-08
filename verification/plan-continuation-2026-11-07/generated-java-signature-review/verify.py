#!/usr/bin/env python3
"""Independent bounded review. All writes are confined to this new directory."""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INTEGRATION = HERE.parent / 'generated-java-ci-integration'
ARTIFACT = HERE.parent / 'ci-e725-generated-java-failure/artifact'
SCRATCH = HERE / 'scratch'
SCRATCH.mkdir(exist_ok=True)
REAL_TEMP = tempfile.TemporaryDirectory
REAL_POPEN = subprocess.Popen
COUNTS = {}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def own_temp(*args, **kwargs):
    kwargs['dir'] = SCRATCH
    return REAL_TEMP(*args, **kwargs)


def readonly_git_popen(argv, *args, **kwargs):
    if not (argv[0] == 'git' and 'sparse-checkout' in argv and 'check-rules' in argv):
        raise AssertionError('Unexpected process in canonical controls: ' + repr(argv))
    return REAL_POPEN(argv, *args, **kwargs)


B = load('review_bootstrap', INTEGRATION / 'bootstrap.py')
OBSERVED = (ARTIFACT / 'bootstrap-commands/005-swift-package-signature.stdout').read_text()
MODERN = 'signed by a developer certificate issued by Apple for distribution'
LEGACY = ('signed by a certificate trusted by macOS', 'signed by a certificate trusted by Mac OS X')
NOTARY = '   Notarization: trusted by the Apple notary service\n'


def count(name):
    COUNTS[name] = COUNTS.get(name, 0) + 1


class Adversarial(unittest.TestCase):
    def refuse(self, text):
        count('parser_negative_cases')
        run = Mock(return_value=text)
        with self.assertRaisesRegex(RuntimeError, 'trust'):
            B.extract_host(run, HERE/'never-package', HERE/'never-expand', HERE/'never-toolchain')
        self.assertEqual(run.call_count, 1)

    def test_observed_report_and_all_statuses_with_notary(self):
        for status in (MODERN, *LEGACY):
            count('parser_positive_cases')
            self.assertEqual(B.validate_host_signature(OBSERVED.replace(MODERN, status)).value, status)

    def test_each_pin_byte_is_required_in_every_status(self):
        for status in (MODERN, *LEGACY):
            for name, fp in B.HOST_CERTIFICATES:
                for offset in range(0, 64, 2):
                    octets = [fp[i:i+2] for i in range(0, 64, 2)]
                    changed = octets.copy()
                    changed[offset//2] = '00' if octets[offset//2] != '00' else '01'
                    original = ' '.join(octets[:22]) + ' \n           ' + ' '.join(octets[22:])
                    replacement = ' '.join(changed[:22]) + ' \n           ' + ' '.join(changed[22:])
                    self.assertIn(original, OBSERVED)
                    self.refuse(OBSERVED.replace(MODERN, status).replace(original, replacement))

    def test_control_characters_non_ascii_and_report_budget(self):
        for suffix in ('\x00', '\x1b[0m', '\x7f', '\x85', '\u2028', '\u00a0', ' ' * 16385):
            self.refuse(OBSERVED + suffix)

    def test_negative_notary_never_admitted_in_any_branch(self):
        for status in (MODERN, *LEGACY):
            for value in ('not trusted', 'revoked', 'not notarized', 'trusted by attacker',
                          'trusted by the Apple notary service (revoked)'):
                self.refuse(OBSERVED.replace(MODERN, status).replace('trusted by the Apple notary service', value))

    def test_wrong_publisher_and_contradictions_in_every_branch(self):
        for status in (MODERN, *LEGACY):
            source = OBSERVED.replace(MODERN, status)
            for a, b in [('Swift Open Source', 'Different Publisher'), ('V9AUD2URP3', 'A9AUD2URP3'),
                         ('Developer ID Installer:', 'Developer ID Application:'),
                         ('Developer ID Certification Authority', 'Other Authority'),
                         ('Apple Root CA', 'Private Root CA')]:
                self.refuse(source.replace(a, b))
            for extra in ('Status: no signature', 'Status: revoked signature', 'error: certificate expired',
                          'Notarization: not trusted', 'Package "another.pkg":'):
                self.refuse(source + extra + '\n')

    def test_filename_is_not_a_credential(self):
        for status in (MODERN, *LEGACY):
            renamed = OBSERVED.replace(MODERN, status).replace('"swift.pkg"', '"renamed.pkg"')
            count('parser_positive_cases')
            self.assertEqual(B.validate_host_signature(renamed).value, status)
            self.refuse(renamed.replace('Swift Open Source', 'Wrong Publisher'))

    def test_legacy_missing_notary_must_not_downgrade_policy(self):
        # Brief requires notary evidence without a format-branch bypass.
        self.refuse(OBSERVED.replace(NOTARY, ''))
        for status in LEGACY:
            with self.subTest(status=status):
                self.refuse(OBSERVED.replace(MODERN, status).replace(NOTARY, ''))

    def test_original_source_refuses_exact_observation(self):
        original = ModuleType('review_original')
        original.__file__ = str(INTEGRATION / 'bootstrap.py')
        data = subprocess.run(['git', 'show', 'e7254f3703d5b8191aa72ec2fb11fa91b5ea99ba:' +
                              str((INTEGRATION/'bootstrap.py').relative_to(ROOT))], cwd=ROOT,
                              check=True, capture_output=True, timeout=15).stdout
        exec(compile(data, original.__file__, 'exec'), original.__dict__)
        run = Mock(return_value=OBSERVED)
        with self.assertRaisesRegex(RuntimeError, 'macOS package trust'):
            original.extract_host(run, HERE/'never-package', HERE/'never-expand', HERE/'never-toolchain')
        self.assertEqual(run.call_count, 1)
        count('baseline_red_reproduced')

    def test_real_command_runner_fake_child_exits_block_parser_and_expansion(self):
        for code in (1, 2, 3, 64, 127, -9):
            with self.subTest(code=code):
                self.command_case(code, OBSERVED, '', 'unexpected exit', parser_calls=0)

    def test_real_command_runner_fake_child_spawn_custody_and_stderr(self):
        self.command_case(0, OBSERVED, '', 'terminal custody', parser_calls=0, custody_error=True)
        self.command_case(0, OBSERVED, 'error: revoked certificate\n', 'macOS package trust', parser_calls=1)
        self.command_case(0, OBSERVED, '', 'Argument list too long', parser_calls=0, spawn_error=True)

    def command_case(self, code, stdout, stderr, error, parser_calls, custody_error=False, spawn_error=False):
        # Real Commands.run logic, owned pipe buffers, fake Popen, no OS process
        # launch, group query, or signal. Every killpg call is replaced.
        authority = B.canonical()
        with own_temp() as td, ExitStack() as stack:
            pipes = {}
            for name, data in (('stdout', stdout), ('stderr', stderr)):
                readfd, writefd = os.pipe()
                os.write(writefd, data.encode())
                os.close(writefd)
                pipes[name] = os.fdopen(readfd, 'rb', buffering=0)
                stack.callback(pipes[name].close)
            child = Mock(pid=2147483647, stdout=pipes['stdout'], stderr=pipes['stderr'])
            child.poll.return_value = code
            child.wait.return_value = code
            stack.enter_context(patch.object(authority.subprocess, 'Popen',
                side_effect=OSError('Argument list too long') if spawn_error else None, return_value=child))
            signal_mock = stack.enter_context(patch.object(authority.os, 'killpg',
                side_effect=PermissionError('fake denied') if custody_error else ProcessLookupError()))
            parser = stack.enter_context(patch.object(B, 'validate_host_signature', wraps=B.validate_host_signature))
            commands = authority.Commands(Path(td), {}, seconds=3, command_seconds=1, cleanup_seconds=.1)
            with self.assertRaisesRegex(RuntimeError, error):
                B.extract_host(commands.run, Path(td)/'swift.pkg', Path(td)/'expanded', Path(td)/'toolchain')
            self.assertEqual(parser.call_count, parser_calls)
            self.assertEqual(len(commands.records), 1)
            self.assertFalse((Path(td)/'expanded').exists())
            self.assertTrue(all(call.args[0] == child.pid for call in signal_mock.call_args_list))
            count('fake_command_runner_cases')


def child(mode):
    if mode == 'adversarial':
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Adversarial)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    else:
        module = load('review_' + mode, INTEGRATION / (mode + '.py'))
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        with patch.object(tempfile, 'TemporaryDirectory', own_temp), \
             patch.object(subprocess, 'Popen', readonly_git_popen), \
             patch.object(os, 'killpg', side_effect=AssertionError('Process probe forbidden')):
            result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures),
                      'errors': len(result.errors), 'case_counts': COUNTS, 'optimized': sys.flags.optimize}))
    return 0 if result.wasSuccessful() else 1


def main():
    before = json.loads((HERE/'before.json').read_text())
    records = []
    for optimized in (False, True):
        for mode in ('test_bootstrap', 'test_sparse_checkout', 'adversarial'):
            label = mode + ('-optimized' if optimized else '-normal')
            argv = [sys.executable, '-B'] + (['-O'] if optimized else []) + [str(Path(__file__).resolve()), mode]
            started = time.monotonic()
            result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
            (HERE/(label+'.stdout')).write_bytes(result.stdout)
            (HERE/(label+'.stderr')).write_bytes(result.stderr)
            summary = json.loads(result.stdout.decode().splitlines()[-1])
            records.append({'label': label, 'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 60,
                            'exit_code': result.returncode, 'elapsed_seconds': time.monotonic()-started,
                            'summary': summary, 'stdout': identity(HERE/(label+'.stdout')),
                            'stderr': identity(HERE/(label+'.stderr'))})
            print(label, result.returncode, summary)
    changed = [p for p, v in before['files'].items() if identity(ROOT/p) != v]
    acquisition = json.loads((ARTIFACT.parent/'acquisition.json').read_text())
    artifact_mismatches = [x['path'] for x in acquisition['files'] if identity(ARTIFACT/x['path']) !=
                           {k:x[k] for k in ('bytes','sha256')}]
    fixture = load('fixture_identity', INTEGRATION/'test_bootstrap.py').OFFICIAL_SIGNATURE
    witnesses = []
    for status in (MODERN, *LEGACY):
        report = OBSERVED.replace(MODERN, status).replace(NOTARY, '')
        events = []
        def witness_run(label, argv, **kwargs):
            events.append(label)
            if label == 'swift-package-signature':
                return report
            raise RuntimeError('FAKE expansion boundary reached; nothing executed')
        try:
            B.extract_host(witness_run, HERE/'never-package', HERE/'never-expand', HERE/'never-toolchain')
        except RuntimeError as error:
            outcome = str(error)
        witnesses.append({'status':status, 'notarization_present':False,
                          'events':events, 'outcome':outcome})
    (HERE/'missing-notary-witness.json').write_text(json.dumps(witnesses, indent=2)+'\n')
    authority = B.canonical()
    inputs = B.admit_source_inputs(authority, authority.load_profile())
    receipt = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'head': before['head'],
               'tree': before['tree'], 'python': sys.version, 'python_executable': sys.executable,
               'git': subprocess.check_output(['git','--version'], text=True).strip(),
               'platform': sys.platform, 'commands': records, 'changed_inputs': changed,
               'artifact_mismatches': artifact_mismatches, 'fixture_matches_ci': fixture == OBSERVED,
               'source_count':len(inputs), 'source_digest':authority.source_digest(inputs),
               'source_hashes':{str(p.relative_to(ROOT)):identity(p) for p in
                                (INTEGRATION/'bootstrap.py', INTEGRATION/'test_bootstrap.py',
                                 INTEGRATION/'test_sparse_checkout.py', B.RUNNER)},
               'scratch_empty': not any(SCRATCH.iterdir()),
               'missing_notary_witnesses':witnesses,
               'limits':'Pure/fake children and bounded read-only Git only; no real pkgutil, download, expansion, compiler, JVM, native, device, held-process probe, or workflow run.'}
    receipt['verdict'] = 'REQUEST CHANGES' if any(r['exit_code'] for r in records) else 'ACCEPT'
    receipt['findings'] = [{'id':'R1', 'priority':'P2',
        'location':'generated-java-ci-integration/bootstrap.py:146-149',
        'supporting_test':'generated-java-ci-integration/test_bootstrap.py:184-186',
        'description':'Both legacy statuses admit absent notarization evidence, contrary to the brief requiring notarization without a format-branch bypass.',
        'fix':'Require the trusted Apple notary field for all admitted statuses; retain legacy status spellings with that evidence.',
        'qualification':'Synthetic policy witness; not evidence that the captured official package is unnotarized.'}]
    receipt['producer_patch_matches'] = subprocess.check_output(['git','diff','--',
        str((INTEGRATION/'bootstrap.py').relative_to(ROOT)),
        str((INTEGRATION/'test_bootstrap.py').relative_to(ROOT))], cwd=ROOT) == (HERE.parent/'generated-java-signature-fix/change.patch').read_bytes()
    receipt['diff_check_exit'] = subprocess.run(['git','diff','--check','--',
        str(INTEGRATION/'bootstrap.py'), str(INTEGRATION/'test_bootstrap.py')], cwd=ROOT,
        capture_output=True, timeout=15).returncode
    receipt['reproduction_script'] = identity(Path(__file__).resolve())
    (HERE/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return 0 if receipt['verdict'] == 'ACCEPT' else 1


if __name__ == '__main__':
    sys.exit(child(sys.argv[1]) if len(sys.argv)>1 else main())
