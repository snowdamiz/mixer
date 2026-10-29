#!/usr/bin/env python3
"""Bounded independent data/AST review; imports no repository subject or helper."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DENIED = []


def denied(*args, **kwargs):
    DENIED.append('runtime-operation')
    raise RuntimeError('Independent review permits source/data operations only')


def audit(event, args):
    if event.startswith(('subprocess.', 'socket.')) or event in {
            'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty',
            'os.exec', 'os.kill', 'os.killpg', 'os.startfile', 'pty.spawn'}:
        DENIED.append(event)
        raise RuntimeError('Independent review denies ' + event)
    targets = []
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            targets = [args[0]]
    elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod', 'os.truncate', 'os.utime'}:
        targets = [args[0]]
    elif event in {'os.rename', 'os.link', 'os.symlink'}:
        targets = list(args[:2])
    for value in targets:
        target = Path(os.fsdecode(value)).resolve(strict=False)
        if not target.is_relative_to(HERE):
            DENIED.append('unowned-write')
            raise RuntimeError('Write outside review directory')


sys.dont_write_bytecode = True
sys.addaudithook(audit)
for name in ('system', 'posix_spawn', 'posix_spawnp', 'fork', 'forkpty', 'setsid',
             'setpgid', 'getsid', 'getpgid', 'getpgrp', 'getpid', 'getppid', 'kill',
             'killpg', 'wait', 'waitpid', 'waitid', 'wait3', 'wait4', 'execv',
             'execve', 'execvp', 'execvpe', 'execl', 'execle', 'execlp', 'execlpe',
             'spawnv', 'spawnve', 'spawnvp', 'spawnvpe', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe'):
    if hasattr(os, name):
        setattr(os, name, denied)
for name in ('Popen', 'run', 'call', 'check_call', 'check_output', 'getoutput', 'getstatusoutput'):
    setattr(subprocess, name, denied)
for name in ('signal', 'alarm', 'setitimer', 'pause', 'sigwait', 'sigwaitinfo',
             'sigtimedwait', 'pthread_kill', 'pthread_sigmask', 'raise_signal',
             'siginterrupt', 'getitimer', 'getsignal', 'sigpending'):
    if hasattr(signal, name):
        setattr(signal, name, denied)
for name in ('socket', 'socketpair', 'create_connection', 'create_server', 'fromfd',
             'getaddrinfo', 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr', 'getnameinfo'):
    if hasattr(socket, name):
        setattr(socket, name, denied)
time.sleep = denied

# Only standard-library data parsers are imported after the guard. No subject,
# packet helper, compiler, test, oracle, or retained executable is imported.
import ast
import difflib
import hashlib
import json
import re

PACKET = ROOT / 'verification/envelope-rust-1991-default-ci-adoption'
OLD = ROOT / 'verification/envelope-partition-default-ci-adoption'
INPUTS = {}
CHECKS = []


def check(value, label):
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise AssertionError('Duplicate JSON key: ' + key)
        value[key] = item
    return value


def raw(path):
    check(path.is_relative_to(ROOT), 'input contained: ' + str(path.relative_to(ROOT)))
    check(not any(p.is_symlink() for p in [path, *path.parents]), 'input regular ancestry: ' + str(path.relative_to(ROOT)))
    size = path.stat().st_size
    check(size <= 10 * 1024 * 1024, 'input per-file bound: ' + str(path.relative_to(ROOT)))
    data = path.read_bytes()
    INPUTS[path.relative_to(ROOT).as_posix()] = {'bytes': len(data), 'sha256': digest(data)}
    return data


def read(path):
    return raw(path).decode()


def parsed(path):
    return json.loads(raw(path), object_pairs_hook=unique)


def rows(base, manifest, expected_count=None):
    members = manifest['members']
    check(0 < len(members) <= 150, 'bounded manifest count: ' + str(base.relative_to(ROOT)))
    check(members == sorted(members, key=lambda r: r['path']), 'sorted manifest: ' + str(base.relative_to(ROOT)))
    check(len(members) == len({r['path'] for r in members}), 'distinct manifest: ' + str(base.relative_to(ROOT)))
    check(manifest['member_count'] == len(members), 'declared count: ' + str(base.relative_to(ROOT)))
    if expected_count is not None:
        check(len(members) == expected_count, 'expected count: ' + str(base.relative_to(ROOT)))
    check(sum(r['bytes'] for r in members) == manifest['total_bytes'], 'manifest total: ' + str(base.relative_to(ROOT)))
    check(digest(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()) == manifest['tree_sha256'],
          'manifest tree: ' + str(base.relative_to(ROOT)))
    for row in members:
        check(set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int,
              'row schema: ' + row['path'])
        name = row['path']; part = Path(name)
        check(type(name) is str and part.as_posix() == name and not part.is_absolute()
              and not any(p in {'.', '..', '.git'} for p in part.parts) and name not in {'', '.'}
              and '\\' not in name and '\x00' not in name, 'canonical row: ' + name)
        data = raw(base / name)
        check(len(data) == row['bytes'] and digest(data) == row['sha256'], 'row hash: ' + name)


def functions(path, class_name=None):
    tree = ast.parse(read(path))
    nodes = tree.body
    if class_name:
        nodes = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name).body
    return {n.name: ast.dump(n, include_attributes=False) for n in nodes if isinstance(n, ast.FunctionDef)}


def job(text):
    return '  swift:\n' + text.split('  swift:\n', 1)[1].split('  swift-capability-native:\n', 1)[0]


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    check(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode,
          'isolated no-site no-bytecode interpreter')
    check(not any(name.startswith(('adopt_envelope', 'offline_guard', 'terminal_replay',
                                  'ordinary_envelope', 'reviewed_envelope')) for name in sys.modules),
          'no repository subject/helper imports')
    for name in ('AGENTS.md', 'PLAN.md', 'verification/rust-1991-qualification-design/DESIGN.md'):
        raw(ROOT / name)
    seal = parsed(PACKET / 'seal.json')
    check(INPUTS[(PACKET / 'seal.json').relative_to(ROOT).as_posix()] == {
        'bytes': 3259, 'sha256': '46757940a874b44ec89330d4bbbba9feea0681123685c063283b728c807d6994'}, 'frozen supplied seal')
    rows(PACKET, seal, 19)
    check(seal['total_bytes'] == 185846 and seal['tree_sha256'] ==
          '08c0f1d30ec93a85132e16bde53a41b2f812a77a29f3acd761d8490e13483f6a', 'frozen own tree')
    observed = sorted(p.relative_to(PACKET).as_posix() for p in PACKET.rglob('*')
                      if p.is_file() and p.relative_to(PACKET).parts[0] not in {'logs', 'control-scratch', '__pycache__'}
                      and p.name != 'seal.json')
    check(observed == [r['path'] for r in seal['members']], 'complete own shipping closure')
    deps = parsed(PACKET / 'dependencies.json'); rows(ROOT, deps, 111)
    check(deps['total_bytes'] == 8615165 and deps['tree_sha256'] ==
          '7ee912e70f14ecd165202dfd3197884bd289e2ab8047532ca7125a05e312ed0d', 'frozen dependency tree')
    old_deps = parsed(OLD / 'dependencies.json'); old_seal = parsed(OLD / 'seal.json')
    rows(OLD, old_seal, 17)
    check(len(old_deps['members']) == 93, '93 original historical dependencies')
    expected_deps = old_deps['members'] + [dict(r, path=(OLD.relative_to(ROOT) / r['path']).as_posix()) for r in old_seal['members']]
    old_seal_bytes = raw(OLD / 'seal.json')
    expected_deps.append({'path': (OLD / 'seal.json').relative_to(ROOT).as_posix(),
                          'bytes': len(old_seal_bytes), 'sha256': digest(old_seal_bytes)})
    check(sorted(expected_deps, key=lambda r: r['path']) == deps['members'], 'exact 93+17+1 preservation closure')
    check(digest(old_seal_bytes) == 'db618546d866abee7cf93e3f7bda678aba6c0c8199c560a93357037b088f6960', 'historical seal unchanged')
    pack = ROOT / 'verification/swift-envelope-ci-pack'; rows(pack, parsed(pack / 'manifest.json'), 86)
    for name in ('offline_guard.py', 'terminal_replay.py'):
        check(raw(PACKET / name) == raw(OLD / name), 'historical unchanged copy: ' + name)
    base = ROOT / 'scripts/ci/check-analyzer-envelope.py'
    candidate = ROOT / 'verification/envelope-producer-timeout-experiment/candidate_runner.py'
    base_defs, candidate_defs = functions(base), functions(candidate)
    for name in ('rustc_identity', 'select_compiler', 'select_host_target'):
        check(base_defs[name] == candidate_defs[name], 'unchanged policy AST: ' + name)
    candidate_text = read(base)
    for change in parsed(ROOT / 'verification/envelope-producer-timeout-experiment/overlay.json')['changes']:
        check(candidate_text.count(change['before']) == 1, 'partition overlay unique target')
        candidate_text = candidate_text.replace(change['before'], change['after'])
    check(candidate_text == read(candidate), 'exact existing partition derivation')
    selection = parsed(PACKET / 'compiler-selection.json'); decision = parsed(PACKET / 'root-selection.json')
    expected_profile = {'identity': {'binary': 'rustc', 'release': '1.99.1', 'host': 'aarch64-apple-darwin',
        'commit_hash': '58cf8f9c35b355199727627d07ae34a4e2846d67', 'commit_date': '2026-10-13', 'llvm_version': '23.1.1'},
        'compiler_sha256': '1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1'}
    check(selection['profile'] == decision['profile'] == expected_profile, 'exact root compiler profile')
    check(selection['status'] == 'selected-prospective-not-yet-qualified' and selection['exact_compiler_qualified'] is False
          and decision['qualified'] is False and decision['selected'] is True, 'prospective scope retained')
    bound = selection['root_selection_record']; actual = INPUTS[bound['path']]
    check(actual == {k: bound[k] for k in ('bytes', 'sha256')}, 'root selection bytes bound')
    check(decision['design']['sha256'] == INPUTS['verification/rust-1991-qualification-design/DESIGN.md']['sha256'],
          'root selected exact Astra design')
    before = read(PACKET / 'workflow/original-verify.yml'); after = before
    changes = parsed(PACKET / 'workflow/changes.json')['changes']
    check(len(changes) == 2, 'two exact workflow substitutions')
    for change in changes:
        check(after.count(change['before']) == 1, 'workflow unique substitution: ' + change['label'])
        after = after.replace(change['before'], change['after'])
    check(job(before) == read(PACKET / 'workflow/original-swift-job.yml'), 'original full Swift job bytes')
    check(job(after) == read(PACKET / 'workflow/swift-job.yml'), 'proposed full Swift job bytes')
    check(before.replace(job(before), '') == after.replace(job(after), ''), 'every other job byte-identical')
    old_remainder = job(before).replace(changes[0]['before'], changes[0]['after']).replace(changes[1]['before'], '')
    check(old_remainder == job(after).replace(changes[1]['after'], ''), 'non-envelope Swift steps byte-identical')
    check(before == read(ROOT / '.github/workflows/verify.yml'), 'root workflow remains draft baseline during review')
    check(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='a/.github/workflows/verify.yml', tofile='b/.github/workflows/verify.yml')) == read(PACKET / 'workflow.diff'),
        'exact complete workflow diff')
    span = read(PACKET / 'workflow/envelope-steps.yml')
    check(span == changes[1]['after'], 'sealed exact envelope span')
    check(re.findall(r'timeout-minutes: ([0-9]+)', span) == ['2', '3', '12', '2', '5'], 'step limits unchanged')
    check('    timeout-minutes: 30\n' in job(after), '30-minute enclosing job')
    check(span.count('adopt_envelope.py" run ') == 1 and span.count('        if: always()') == 2,
          'single fixture plus always postflight/upload')
    check('export RUSTUP_AUTO_INSTALL=0' in span and '$(command -v rustc)' in span,
          'existing launcher no auto-install')
    check(all(bad not in span for bad in ('workflow_dispatch', 'continue-on-error', 'toolchain install', 'retry', 'fallback')),
          'no new dispatch installer retry fallback or continued errors')
    sparse = job(after).split('          sparse-checkout: |\n', 1)[1].split('      - name:', 1)[0]
    entries = [line.strip().lstrip('/') for line in sparse.splitlines() if line.strip()]
    check(all(not r['path'].startswith('verification/') or any(r['path'] == p or p.endswith('/') and r['path'].startswith(p)
              for p in entries) for r in deps['members']), 'all111 dependencies in proposed sparse checkout')
    old_methods = functions(OLD / 'test_adoption.py', 'Controls')
    new_methods = functions(PACKET / 'test_adoption.py', 'Controls')
    old_tests = sorted(n for n in old_methods if n.startswith('test_'))
    new_tests = sorted(n for n in new_methods if n.startswith('test_'))
    check(len(old_tests) == 22 and len(new_tests) == 33, '22 historical and33 derivative controls')
    rename = {'test_ordinary_compiler_exact_functions_and_allowlist_are_reused':
              'test_ordinary_compiler_exact_parser_and_delegated_functions_are_preserved'}
    check(all(rename.get(n, n) in new_tests for n in old_tests), 'all historical control behaviors represented')
    changed_methods = [n for n in old_tests if old_methods[n] != new_methods[rename.get(n, n)]]
    stderr = read(PACKET / 'logs/controls-final.stderr')
    actual_tests = re.findall(r'^(test_\w+) \(__main__\.Controls\.\w+\) \.\.\. ok$', stderr, re.M)
    check(actual_tests == new_tests and len(set(actual_tests)) == 33, 'all33 final log names correspond exactly to source')
    check('Ran 33 tests in 4.111s\n\nOK\n' in stderr and 'FAILED' not in stderr, 'retained final33 pass summary')
    result = parsed(PACKET / 'logs/controls-final.stdout')
    check(result['tests'] == 33 and result['passed'] is True and result['failures'] == result['errors'] == result['skipped'] == 0,
          'retained result count and exit-success semantics')
    check(result['denied_operation_attempts'] == [] and result['control_scratch_absent'] is True
          and result['compiler_producer_product_native_runtime_runs'] == 0, 'retained no-runtime/scratch result')
    check(raw(PACKET / 'pure-controls.stdout') == raw(PACKET / 'logs/controls-final.stdout'),
          'sealed and final control stdout identical')
    sealed_stderr = read(PACKET / 'pure-controls.stderr')
    check('Ran 33 tests in 3.925s\n\nOK\n' in sealed_stderr, 'sealed prior33 pass summary')
    check(re.sub(r'Ran 33 tests in [0-9.]+s', 'Ran 33 tests in ELAPSED', sealed_stderr) ==
          re.sub(r'Ran 33 tests in [0-9.]+s', 'Ran 33 tests in ELAPSED', stderr),
          'sealed and final33 controls identical except elapsed duration')
    receipt = parsed(PACKET / 'checks.json')
    for name, info in receipt['own_executed_sources'].items():
        check(raw(PACKET / name) is not None and INPUTS[(PACKET / name).relative_to(ROOT).as_posix()] == info,
              'retained execution source pin: ' + name)
    frozen = parsed(PACKET / 'logs/frozen-verify.stdout')
    check(frozen['proof']['adoption_seal_sha256'] == digest(raw(PACKET / 'seal.json'))
          and frozen['proof']['adoption_tree_sha256'] == seal['tree_sha256']
          and frozen['proof']['dependencies_sha256'] == digest(raw(PACKET / 'dependencies.json'))
          and frozen['proof']['workflow_job_sha256'] == digest(raw(PACKET / 'workflow/swift-job.yml')),
          'final frozen verification binds current full seal/dependencies/job')
    check(frozen['denied'] == [] and frozen['scratch_absent'] is True and raw(PACKET / 'logs/frozen-verify.stderr') == b'',
          'retained frozen verification no denied operations or stderr')
    check(not (PACKET / 'control-scratch').exists(), 'scratch currently absent')
    check(DENIED == [], 'review no denied operation attempts')
    check(not any(name.startswith(('adopt_envelope', 'offline_guard', 'terminal_replay',
                                  'ordinary_envelope', 'reviewed_envelope')) for name in sys.modules),
          'review completed without subject/helper import')
    write('source-bindings.json', {'schema': 1, 'members': [dict(path=n, **v) for n, v in sorted(INPUTS.items())],
          'context_revision': '2c751cbbc300efc9aa766b5d4add648610ca0341',
          'context_tree': 'f2df6833ee8e9ce85306210b63dc35d45747fa0d',
          'revision_tree_source': 'Parent supplied; no Git invoked', 'scope': 'Exact reviewed source/data inputs; no whole-checkout claim'})
    summary = {'schema': 1, 'passed': True, 'data_assertions': len(CHECKS), 'input_files': len(INPUTS),
        'input_bytes': sum(r['bytes'] for r in INPUTS.values()), 'command':
        'python3 -I -B -S verification/envelope-rust-1991-default-ci-adoption-review/review_data.py',
        'python': sys.version, 'interpreter': sys.executable, 'denied_operations': DENIED,
        'subject_or_helper_imports': 0, 'product_compiler_oracle_native_ui_network_process_probe_signal_custody_runs': 0,
        'controls_rerun': 0, 'retained_controls': {'passed': 33, 'seconds': 4.111, 'synthetic_only': True},
        'historical_test_methods_changed_for_derivative': changed_methods,
        'own_packet': {k: seal[k] for k in ('member_count', 'total_bytes', 'tree_sha256')},
        'dependencies': {k: deps[k] for k in ('member_count', 'total_bytes', 'tree_sha256')},
        'root_workflow_draft_baseline_verified': True,
        'check_labels_sha256': digest(json.dumps(CHECKS, separators=(',', ':')).encode())}
    write('data-audit.json', summary)
    print(json.dumps(summary, sort_keys=True))


def seal_review():
    bindings = json.loads((HERE / 'source-bindings.json').read_bytes(), object_pairs_hook=unique)
    for item in bindings['members']:
        data = raw(ROOT / item['path'])
        check(len(data) == item['bytes'] and digest(data) == item['sha256'], 'final input rehash: ' + item['path'])
    members = []
    for path in sorted(HERE.iterdir()):
        if path.name == 'seal.json':
            continue
        check(path.is_file() and not path.is_symlink(), 'flat regular review output: ' + path.name)
        data = path.read_bytes()
        members.append({'path': path.name, 'bytes': len(data), 'sha256': digest(data)})
    value = {'schema': 1, 'member_count': len(members), 'members': members,
             'total_bytes': sum(r['bytes'] for r in members),
             'tree_sha256': digest(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()),
             'scope': 'Focused independent source/data review; no subject imports or33-control rerun; actual compiler qualification pending',
             'final_input_rehash_members': len(bindings['members']), 'denied_operations': DENIED}
    check(DENIED == [], 'final review no denied operations')
    write('seal.json', value)
    data = (HERE / 'seal.json').read_bytes()
    print(json.dumps({'seal_bytes': len(data), 'seal_sha256': digest(data),
                      'member_count': value['member_count'], 'total_bytes': value['total_bytes'],
                      'tree_sha256': value['tree_sha256'], 'final_input_rehash_members': len(bindings['members']),
                      'denied_operations': DENIED}, sort_keys=True))


if __name__ == '__main__':
    if sys.argv[1:] == ['--seal']:
        seal_review()
    else:
        assert sys.argv[1:] == []
        main()
