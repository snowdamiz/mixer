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
FAKE_RECORDS = []


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

    def test_real_command_runner_fake_child_exits_block_parser_and_expansion(self):
        for code in (1, 2, 3, 64, 127, -9):
            with self.subTest(code=code):
                self.command_case(code, OBSERVED, '', 'unexpected exit', parser_calls=0)

    def test_real_command_runner_fake_child_spawn_custody_and_stderr(self):
        self.command_case(0, OBSERVED, '', 'terminal custody', parser_calls=0, custody_error=True)
        self.command_case(0, OBSERVED, 'error: revoked certificate\n', 'macOS package trust', parser_calls=1)
        self.command_case(0, OBSERVED, '', 'Argument list too long', parser_calls=0, spawn_error=True)

    def command_case(self, code, stdout, stderr, error, parser_calls, custody_error=False, spawn_error=False, timeout=False, output_limit=False):
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
            commands = authority.Commands(Path(td), {}, seconds=3, command_seconds=0 if timeout else 1,
                                          output_bytes=16 if output_limit else 65536, cleanup_seconds=.1)
            with self.assertRaisesRegex(RuntimeError, error):
                B.extract_host(commands.run, Path(td)/'swift.pkg', Path(td)/'expanded', Path(td)/'toolchain')
            self.assertEqual(parser.call_count, parser_calls)
            self.assertEqual(len(commands.records), 1)
            self.assertFalse((Path(td)/'expanded').exists())
            self.assertTrue(all(call.args[0] == child.pid for call in signal_mock.call_args_list))
            FAKE_RECORDS.extend(commands.records)
            count('fake_command_runner_cases')



    def test_each_required_line_and_each_truncation_in_all_statuses(self):
        for status in (MODERN, *LEGACY):
            lines = OBSERVED.replace(MODERN, status).splitlines(keepends=True)
            for i, line in enumerate(lines):
                if line.strip():
                    self.refuse(''.join(lines[:i] + lines[i+1:]))
                    self.refuse(''.join(lines[:i] + [line] + lines[i:]))
            for i in range(1, len(lines)-2):
                self.refuse(''.join(lines[:i]))

    def test_invalid_dates_expiry_and_status_downgrades(self):
        for status in (MODERN, *LEGACY):
            report = OBSERVED.replace(MODERN, status)
            for a, b in [('2026-06-26', '2026-02-30'), ('2026-06-26', '2028-06-26'),
                         ('2027-02-01', '2025-02-01'), ('+0000', '+0100'),
                         ('trusted timestamp', 'untrusted timestamp'),
                         ('Certificate Chain:', 'Certificate Chain: untrusted')]:
                self.refuse(report.replace(a, b))
            for bad in ('no signature', 'signed by an untrusted certificate',
                        'signed by a certificate that has since expired', 'revoked signature'):
                self.refuse(report.replace(status, bad))

    def test_status_formatting_and_trusted_timestamp_are_not_wall_clock_checks(self):
        for status in (MODERN, *LEGACY):
            report = OBSERVED.replace(MODERN, status)
            for good in (report.replace('\n', '\r\n'),
                         '\n' + '\n'.join('\t'+line.strip() for line in report.splitlines())+'\n',
                         report.replace('2026-06-26', '2020-06-26').replace('2027-02-01', '2021-02-01')):
                count('parser_positive_cases')
                self.assertEqual(B.validate_host_signature(good).value, status)

    def test_fake_runner_timeout_and_output_budget_stop_before_parser(self):
        self.command_case(0, OBSERVED, '', 'timeout', parser_calls=0, timeout=True)
        self.command_case(0, OBSERVED, '', 'output-limit', parser_calls=0, output_limit=True)

    def test_fake_runner_success_and_mixed_streams_reach_fake_expansion_only(self):
        for status in (MODERN, *LEGACY):
            report = OBSERVED.replace(MODERN, status)
            for split in (len(report), report.index('   Notarization:')):
                authority = B.canonical()
                with own_temp() as td, ExitStack() as stack:
                    pipes = {}
                    for name, data in (('stdout', report[:split]), ('stderr', report[split:])):
                        r, w = os.pipe()
                        os.write(w, data.encode())
                        os.close(w)
                        pipes[name] = os.fdopen(r, 'rb', buffering=0)
                        stack.callback(pipes[name].close)
                    child = Mock(pid=2147483647, stdout=pipes['stdout'], stderr=pipes['stderr'])
                    child.poll.return_value = child.wait.return_value = 0
                    stack.enter_context(patch.object(authority.subprocess, 'Popen', return_value=child))
                    stack.enter_context(patch.object(authority.os, 'killpg', side_effect=ProcessLookupError()))
                    commands = authority.Commands(Path(td), {}, seconds=3, command_seconds=1, cleanup_seconds=.1)
                    events = []
                    def boundary(label, argv, **kw):
                        events.append(label)
                        if label == 'swift-package-signature':
                            self.assertEqual(kw, {'diagnostics': True})
                            return commands.run(label, argv, **kw)
                        raise RuntimeError('independent fake expansion boundary')
                    with self.assertRaisesRegex(RuntimeError, 'independent fake expansion boundary'):
                        B.extract_host(boundary, Path(td)/'p', Path(td)/'e', Path(td)/'t')
                    self.assertEqual(events, ['swift-package-signature', 'swift-package-expand'])
                    self.assertTrue(commands.custody_terminal())
                    FAKE_RECORDS.extend(commands.records)
                    count('fake_command_runner_positive_cases')


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
    if mode == 'adversarial':
        (HERE / ('fake-records-optimized.json' if sys.flags.optimize else 'fake-records-normal.json')).write_text(json.dumps(FAKE_RECORDS, indent=2)+'\n')
    print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures),
                      'errors': len(result.errors), 'case_counts': COUNTS, 'optimized': sys.flags.optimize}))
    return 0 if result.wasSuccessful() else 1


def snapshot():
    paths = set()
    for name in ('generated-java-ci-integration', 'generated-java-signature-fix',
                 'generated-java-signature-review', 'generated-java-signature-fix-r2',
                 'ci-e725-generated-java-failure'):
        paths.update(p for p in (HERE.parent/name).rglob('*') if p.is_file())
    authority = B.canonical()
    paths.update(ROOT/p for p in authority.source_inputs(authority.load_profile()))
    paths.update((B.RUNNER, ROOT/'.github/workflows/verify.yml'))
    return {str(p.relative_to(ROOT)): identity(p) for p in sorted(paths)}


def main():
    import ast
    import platform
    started = time.monotonic()
    before = snapshot()
    (HERE/'before.json').write_text(json.dumps(before, indent=2)+'\n')
    authority = B.canonical()
    out = HERE/'commands'
    out.mkdir(exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(SCRATCH))
    commands = authority.Commands(out, env, seconds=300, command_seconds=45,
                                  output_bytes=262144, total_output_bytes=2097152,
                                  cleanup_seconds=2)
    receipt = {'scope':'Independent R2 review for root delivery and fresh ordinary generatedJava CI only',
               'observed_utc':datetime.now(timezone.utc).isoformat(),
               'python':sys.version, 'executable':sys.executable, 'platform':sys.platform,
               'os_uname':list(os.uname()), 'macos':platform.mac_ver(),
               'env':{k:env.get(k) for k in ('PATH','TMPDIR','PYTHONDONTWRITEBYTECODE','LANG','LC_ALL')},
               'limits':{'seconds':300,'command_seconds':45,'output_bytes':2097152},
               'source_before':before, 'findings':[], 'test_runs':[]}
    passed = False
    try:
        receipt['head'] = commands.run('head', ['git','rev-parse','HEAD']).strip()
        receipt['tree'] = commands.run('tree', ['git','rev-parse','HEAD^{tree}']).strip()
        receipt['git'] = commands.run('git-version', ['git','--version']).strip()
        for optimized in (False, True):
            for mode in ('test_bootstrap', 'test_sparse_checkout', 'adversarial'):
                label = mode+('-optimized' if optimized else '-normal')
                argv = [sys.executable, '-B']+(['-O'] if optimized else [])+[str(Path(__file__).resolve()),mode]
                text = commands.run(label,argv)
                summary = json.loads(text.splitlines()[-1])
                receipt['test_runs'].append(dict(label=label, **summary))
                print(label, json.dumps(summary), flush=True)
        paths=[str((INTEGRATION/n).relative_to(ROOT)) for n in ('bootstrap.py','test_bootstrap.py')]
        diff = commands.run('candidate-patch',['git','diff','--',*paths])
        (HERE/'reviewed.patch').write_text(diff)
        commands.run('diff-check',['git','diff','--check','--',*paths])
        receipt['producer_patch_matches'] = diff.encode() == (HERE.parent/'generated-java-signature-fix-r2/change.patch').read_bytes()
        baseline = commands.run('baseline-source',['git','show',receipt['head']+':'+paths[0]])
        # Read-only structural identity check; do not execute historical source.
        old_tree, new_tree = ast.parse(baseline), ast.parse((INTEGRATION/'bootstrap.py').read_text())
        old_nodes={n.name:ast.dump(n,include_attributes=False) for n in old_tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        new_nodes={n.name:ast.dump(n,include_attributes=False) for n in new_tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        receipt['changed_functions']=[n for n in old_nodes if old_nodes[n]!=new_nodes.get(n)]
        receipt['added_functions_or_classes']=sorted(set(new_nodes)-set(old_nodes))
        old_assign=[ast.dump(n,include_attributes=False) for n in old_tree.body if isinstance(n,ast.Assign)]
        new_assign=[ast.dump(n,include_attributes=False) for n in new_tree.body if isinstance(n,ast.Assign)]
        receipt['original_constants_unchanged']=all(n in new_assign for n in old_assign)
        receipt['guards_and_limits_unchanged']=receipt['changed_functions']==['extract_host'] and receipt['original_constants_unchanged']
        profile = authority.load_profile()
        inputs = B.admit_source_inputs(authority, profile)
        receipt['pair8']={'id':profile['id'],'count':len(inputs),'sha256':authority.source_digest(inputs)}
        fixture=load('review_fixture_identity', INTEGRATION/'test_bootstrap.py').OFFICIAL_SIGNATURE
        receipt['fixture_matches_observed_report']=fixture==OBSERVED
        receipt['observed_report']=identity(ARTIFACT/'bootstrap-commands/005-swift-package-signature.stdout')
        acquisition=json.loads((ARTIFACT.parent/'acquisition.json').read_text())
        receipt['artifact_mismatches']=[x['path'] for x in acquisition['files'] if identity(ARTIFACT/x['path'])!={k:x[k] for k in ('bytes','sha256')}]
        producer=json.loads((HERE.parent/'generated-java-signature-fix-r2/receipt.json').read_text())
        producer_cmds=json.loads((HERE.parent/'generated-java-signature-fix-r2/commands/commands.json').read_text())
        producer_log_mismatch=[]
        for command in producer_cmds:
            for log in command['logs'].values():
                if identity(Path(log['path'])) != {k:log[k] for k in ('bytes','sha256')}:
                    producer_log_mismatch.append(log['path'])
        receipt['producer']={'commands':len(producer_cmds),'all_terminal':all(r['terminal_custody'] for r in producer_cmds),
                             'all_exit_zero':all(r['exit_code']==0 for r in producer_cmds),
                             'log_mismatches':producer_log_mismatch,
                             'source_mismatches':[x['path'] for x in producer['sources'] if identity(ROOT/x['path'])!={k:x[k] for k in ('bytes','sha256')}],
                             'preserved_mismatches':[x['path'] for x in producer['preserved_evidence'] if identity(ROOT/x['path'])!={k:x[k] for k in ('bytes','sha256')}]}
        captured=json.loads((ARTIFACT/'bootstrap-commands/commands.json').read_text())
        receipt['captured_signature_command']=next(r for r in captured if r['label']=='swift-package-signature')
        receipt['captured_bootstrap_limits']=json.loads((ARTIFACT/'bootstrap-receipt.json').read_text())['limits']
        receipt['source_after']=snapshot()
        receipt['changed_inputs']=[p for p in set(before)|set(receipt['source_after']) if before.get(p)!=receipt['source_after'].get(p)]
        receipt['scratch_empty']=not any(SCRATCH.iterdir())
        receipt['head_after']=commands.run('head-after',['git','rev-parse','HEAD']).strip()
        authority.require(receipt['head']==receipt['head_after']=='e7254f3703d5b8191aa72ec2fb11fa91b5ea99ba','Head drift')
        authority.require(not receipt['changed_inputs'] and not receipt['artifact_mismatches'],'Input drift')
        authority.require(receipt['producer_patch_matches'] and receipt['guards_and_limits_unchanged'] and receipt['fixture_matches_observed_report'],'Source or guard mismatch')
        authority.require(not any(receipt['producer'][k] for k in ('source_mismatches','preserved_mismatches','log_mismatches')),'Producer evidence mismatch')
        authority.require(receipt['producer']['commands']==9 and receipt['producer']['all_terminal'] and receipt['producer']['all_exit_zero'],'Producer commands differ')
        authority.require(receipt['scratch_empty'],'Scratch remains')
        passed=True
    except BaseException as error:
        receipt['error']=type(error).__name__+': '+str(error)
    finally:
        receipt['terminal_custody']=commands.custody_terminal()
        receipt['elapsed_seconds']=time.monotonic()-started
        receipt['output_bytes']=commands.used_output
        receipt['command_records']=identity(out/'commands.json')
        receipt['reproduction_script']=identity(Path(__file__).resolve())
        receipt['verdict']='ACCEPT' if passed and receipt['terminal_custody'] else 'REQUEST CHANGES'
        receipt['limitations']='Fake children, pure parsing, read-only Git only. No actual signature verification, downloading, expansion, compiler, native/UI/device/capture, CI dispatch, commit/push/delegation, or held-process probes. Native held; physical phones disconnected; historical PGID 23663 and prior holds untouched. No hosted/GA qualification.'
        (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({k:receipt.get(k) for k in ('verdict','error','terminal_custody','elapsed_seconds','output_bytes','changed_inputs','pair8')}))
    return 0 if receipt['verdict']=='ACCEPT' else 1


if __name__ == '__main__':
    sys.exit(child(sys.argv[1]) if len(sys.argv)>1 else main())
