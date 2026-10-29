#!/usr/bin/env python3
"""Bounded inert ZIP/data inspection; never imports or executes artifact code."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
DENIED = []


def blocked(*args, **kwargs):
    DENIED.append('active-runtime-api')
    raise RuntimeError('Read-only CI evidence review forbids active runtime APIs')


def audit(event, args):
    if event.startswith(('subprocess.', 'socket.')) or event in {
            'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty',
            'os.exec', 'os.kill', 'os.killpg', 'os.startfile'}:
        DENIED.append(event)
        raise RuntimeError('Read-only CI evidence review forbids ' + event)
    targets = []
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            targets = [args[0]]
    elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod'}:
        targets = [args[0]]
    elif event in {'os.rename', 'os.link', 'os.symlink'}:
        targets = args[:2]
    for value in targets:
        target = Path(os.fsdecode(value)).resolve(strict=False)
        if not target.is_relative_to(HERE) or target == HERE:
            raise RuntimeError('Write outside owned review directory: ' + str(target))


sys.addaudithook(audit)
sys.dont_write_bytecode = True
for name in ('system', 'posix_spawn', 'posix_spawnp', 'fork', 'forkpty', 'setsid',
             'setpgid', 'getsid', 'getpgid', 'getpgrp', 'kill', 'killpg', 'wait',
             'waitpid', 'waitid', 'wait3', 'wait4'):
    if hasattr(os, name):
        setattr(os, name, blocked)
for name in ('Popen', 'run', 'call', 'check_call', 'check_output'):
    setattr(subprocess, name, blocked)
for name in ('signal', 'alarm', 'setitimer', 'pause', 'sigwait', 'sigwaitinfo',
             'sigtimedwait', 'pthread_kill', 'pthread_sigmask', 'raise_signal',
             'siginterrupt', 'getitimer', 'getsignal', 'sigpending'):
    if hasattr(signal, name):
        setattr(signal, name, blocked)
socket.socket = blocked
socket.create_connection = blocked
time.sleep = blocked

# Only inert standard-library data readers load after the active API guard.
import hashlib
import json
import stat
import zipfile
import ast

EXPECTED_BYTES = 444759
EXPECTED_SHA256 = '4bf8af7420033af59134305742ccfc6e125a5a09a4e4e4f9ee4720948d94ab0e'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def strict_json(text):
    def pairs(items):
        answer = {}
        for key, value in items:
            need(key not in answer, 'Duplicate JSON key')
            answer[key] = value
        return answer
    def constant(value):
        raise RuntimeError('Non-finite JSON constant: ' + value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def summarize():
    source = HERE / 'local/artifact-inspection.json'
    need(not source.is_symlink() and source.is_file()
         and source.stat().st_size <= 2 * 1024 * 1024, 'Inspection JSON outside bound')
    inspected = strict_json(source.read_text())
    texts = inspected['selected_texts']
    receipt = strict_json(texts['_temp/analyzer-envelope/receipt.json'])
    adapter = strict_json(texts['_temp/analyzer-envelope/adapter-result.json'])
    start = strict_json(texts['_temp/analyzer-envelope/adapter-start.json'])
    logs = 'mixer/mixer/verification/envelope-partition-default-ci-adoption/logs/'
    command_rows = [strict_json(texts['_temp/analyzer-envelope/commands/' + row['name'] + '.json'])
                    for row in receipt['commands']]
    summary = {
        'schema': 1, 'artifact': inspected['artifact'],
        'member_count': inspected['member_count'], 'payload_bytes': inspected['total_payload_bytes'],
        'receipt_status': receipt['status'], 'receipt_errors': receipt['errors'],
        'revision_before': receipt.get('revision_before'),
        'git_tree_before': receipt.get('git_tree_before'),
        'source_tree_digest': receipt.get('source_tree_digest'),
        'rustc': receipt.get('rustc'), 'receipt_postflight': receipt.get('postflight'),
        'cleanup': receipt.get('cleanup'), 'commands': command_rows,
        'receipt_field_names': sorted(receipt), 'adapter_result': adapter,
        'adapter_start': start, 'fixture_stdout': texts[logs + 'fixture.stdout'],
        'fixture_stderr': texts[logs + 'fixture.stderr'],
        'preflight_stderr': texts[logs + 'preflight.stderr'],
        'postflight_stderr': texts[logs + 'postflight.stderr'],
        'controls_terminal': texts[logs + 'controls.stderr'].splitlines()[-5:],
        'denied_active_api_attempts': DENIED,
    }
    (HERE / 'local/failure-summary.json').write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n')
    compact = {key: summary[key] for key in (
        'member_count', 'payload_bytes', 'receipt_status', 'receipt_errors', 'cleanup',
        'fixture_stdout', 'fixture_stderr', 'preflight_stderr', 'postflight_stderr',
        'controls_terminal', 'denied_active_api_attempts')}
    compact['rustc_identity'] = summary['rustc']['identity']
    compact['commands'] = [{key: row.get(key) for key in (
        'name', 'exit', 'pid', 'owned_pgid', 'child_returned', 'owned_group_gone',
        'pipe_eof', 'custody_hold', 'errors')} for row in command_rows]
    compact['postflight'] = {key: {'passed': value.get('passed')} if isinstance(value, dict)
                             else value for key, value in receipt.get('postflight', {}).items()}
    compact['adapter_exception'] = adapter['adapter_exception']
    compact['adapter_errors'] = adapter['errors']
    compact['terminal_replay'] = adapter['terminal_replay']
    print(json.dumps(compact, sort_keys=True, indent=2))


def verify_evidence():
    root = HERE.parents[1]
    inspected = strict_json((HERE / 'local/artifact-inspection.json').read_text())
    summary = strict_json((HERE / 'local/failure-summary.json').read_text())
    archive_rows = {row['path']: row for row in inspected['members']}
    checked = []

    def check(value, name):
        need(value, name)
        checked.append(name)

    def sha(path):
        need(not path.is_symlink() and path.is_file() and path.stat().st_size <= 8 * 1024 * 1024,
             'Regular bounded source required')
        return hashlib.sha256(path.read_bytes()).hexdigest()

    check(inspected['artifact']['sha256'] == EXPECTED_SHA256
          and inspected['artifact']['bytes'] == EXPECTED_BYTES, 'exact-artifact-identity')
    check(summary['receipt_errors'] == [{'phase': 'active', 'type': 'RuntimeError',
          'message': 'Compiler host/release not selected'}], 'sole-exact-active-refusal')
    check(summary['adapter_result']['adapter_exception'] is None
          and summary['adapter_result']['errors'] == [], 'no-adapter-or-postflight-exception')
    check(summary['fixture_stderr'] == '' and summary['preflight_stderr'] == ''
          and summary['postflight_stderr'] == '', 'empty-fixture-and-source-stderr')
    check(summary['adapter_start']['revision'] == '2c751cbbc300efc9aa766b5d4add648610ca0341',
          'delivered-head-bound')
    check(summary['revision_before'] == summary['adapter_start']['revision']
          and isinstance(summary['git_tree_before'], str) and len(summary['git_tree_before']) == 40
          and all(character in '0123456789abcdef' for character in summary['git_tree_before']),
          'observed-revision-and-tree-bound')
    check(summary['cleanup'] == {'scratch_created': False, 'removed': False}, 'no-fixture-scratch-created')
    expected_names = ['revision-before', 'git-tree-before', 'python-version',
                      'compiler-sysroot-selection', 'rustc-verbose']
    check([row['name'] for row in summary['commands']] == expected_names, 'exact-five-precompile-commands')
    for row in summary['commands']:
        prefix = '_temp/analyzer-envelope/commands/'
        check(row['exit'] == 0 and row['child_returned'] and row['owned_group_gone']
              and row['pipe_eof'] == {'stdout': True, 'stderr': True}
              and row['custody_hold'] is False and row['errors'] == [], 'closed-command-' + row['name'])
        for channel in ('stdout', 'stderr'):
            capture = row[channel]
            retained = archive_rows['_temp/analyzer-envelope/' + capture['path']]
            check(retained['sha256'] == capture['sha256'] and retained['bytes'] == capture['bytes'],
                  'capture-binding-' + row['name'] + '-' + channel)
    check(set(summary['receipt_postflight']) == {'compiler', 'launcher', 'pack', 'python',
          'runner', 'runner-snapshot', 'snapshot', 'snapshot-observed'}
          and all(row['passed'] for row in summary['receipt_postflight'].values()), 'all-eight-source-postflights')
    check(summary['controls_terminal'][-4:] == ['----------------------------------------------------------------------',
          'Ran 22 tests in 1.524s', '', 'OK'], 'twenty-two-controls-pass')
    snapshots = {
        'executed-adapter.py': root / 'verification/envelope-partition-default-ci-adoption/adopt_envelope.py',
        'executed-ordinary-policy.py': root / 'scripts/ci/check-analyzer-envelope.py',
        'executed-terminal-replay.py': root / 'verification/envelope-partition-default-ci-adoption/terminal_replay.py',
        'executed-dependencies.json': root / 'verification/envelope-partition-default-ci-adoption/dependencies.json',
        'executed-adoption-seal.json': root / 'verification/envelope-partition-default-ci-adoption/seal.json',
        'executed-runner.py': root / 'verification/envelope-producer-timeout-experiment/candidate_runner.py',
    }
    source_bindings = []
    for name, local in snapshots.items():
        digest = sha(local)
        check(archive_rows['_temp/analyzer-envelope/' + name]['sha256'] == digest,
              'executed-snapshot-matches-checkout-' + name)
        if name in summary['adapter_start']['source_snapshots']:
            check(summary['adapter_start']['source_snapshots'][name] == digest, 'adapter-binds-' + name)
        source_bindings.append({'path': str(local.relative_to(root)), 'sha256': digest})
    adoption = root / 'verification/envelope-partition-default-ci-adoption'
    seal = strict_json((adoption / 'seal.json').read_text())
    for row in seal['members']:
        local = adoption / row['path']
        archived = archive_rows['mixer/mixer/verification/envelope-partition-default-ci-adoption/' + row['path']]
        check(sha(local) == row['sha256'] == archived['sha256']
              and local.stat().st_size == row['bytes'] == archived['bytes'], 'adoption-source-' + row['path'])
    dependencies = strict_json((adoption / 'dependencies.json').read_text())
    for row in dependencies['members']:
        local = root / row['path']
        check(sha(local) == row['sha256'] and local.stat().st_size == row['bytes'],
              'checkout-dependency-' + row['path'])
    pack = strict_json((root / 'verification/swift-envelope-ci-pack/manifest.json').read_text())
    check(summary['source_tree_digest'] == pack['tree_sha256'], 'recorded-immutable-pack-tree')
    pack_rows = pack['members']
    for row in pack_rows:
        archived = archive_rows['_temp/analyzer-envelope/pack/' + row['path']]
        check(archived['bytes'] == row['bytes'] and archived['sha256'] == row['sha256'],
              'immutable-pack-member-' + row['path'])
    workflow = root / '.github/workflows/verify.yml'
    workflow_sha = sha(workflow)
    check(workflow_sha == 'a90bab7dea218e5a098e45eb370e9b666afdf0bda9100cb35ec14dfc779de024'
          == archive_rows['mixer/mixer/.github/workflows/verify.yml']['sha256'], 'unchanged-actual-workflow')
    policy_source = (root / 'scripts/ci/check-analyzer-envelope.py').read_text()
    candidate_source = (root / 'verification/envelope-producer-timeout-experiment/candidate_runner.py').read_text()
    def definitions(source):
        return {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
    original, candidate = definitions(policy_source), definitions(candidate_source)
    for name in ('rustc_identity', 'select_compiler', 'select_host_target'):
        check(ast.get_source_segment(policy_source, original[name])
              == ast.get_source_segment(candidate_source, candidate[name]), 'exact-policy-definition-' + name)
    allowed_node = next(node.value for node in original['select_host_target'].body
                        if isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'allowed')
    allowed = ast.literal_eval(allowed_node)
    check(allowed == {('aarch64-apple-darwin', '1.98.1'), ('aarch64-apple-darwin', '1.99.0')},
          'exact-fixed-policy-allowlist')
    actual = summary['rustc']['identity']
    check((actual['host'], actual['release']) not in allowed, 'actual-compiler-outside-fixed-policy')
    check(DENIED == [] and inspected['denied_active_api_attempts'] == [], 'zero-active-runtime-attempts')
    result = {
        'schema': 1, 'scope': 'Bounded inert source/JSON/ZIP inspection; no artifact code or product execution',
        'revision': summary['adapter_start']['revision'], 'artifact': inspected['artifact'],
        'observed_git_revision': summary['revision_before'],
        'observed_git_tree': summary['git_tree_before'],
        'immutable_pack_tree_sha256': summary['source_tree_digest'],
        'archive_member_count': inspected['member_count'], 'archive_payload_bytes': inspected['total_payload_bytes'],
        'cause': summary['receipt_errors'][0], 'actual_compiler': summary['rustc'],
        'allowed_host_release_pairs': sorted(allowed), 'commands_observed': expected_names,
        'commands_closed': 5, 'pack_members_verified': len(pack_rows),
        'adoption_members_verified': len(seal['members']), 'checkout_dependencies_verified': len(dependencies['members']),
        'checks': checked, 'check_count': len(checked), 'source_bindings': source_bindings,
        'workflow_sha256': workflow_sha, 'no_fixture_compilation_started': True,
        'fixture_scratch_created': False, 'all_eight_recorded_postflights_pass': True,
        'native_ui_capture_or_process_probes': 0, 'denied_active_api_attempts': DENIED,
        'reviewer': {'role': 'CI failure source/data investigator', 'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'},
        'python': {'executable': sys.executable, 'version': sys.version},
        'inspection_commands': [
            'python3 -I -B -S verification/engine-ci-2c751cbb-swift-failure/inspect_artifact.py',
            'python3 -I -B -S verification/engine-ci-2c751cbb-swift-failure/inspect_artifact.py --summarize',
            'python3 -I -B -S verification/engine-ci-2c751cbb-swift-failure/inspect_artifact.py --verify'],
        'helper_sha256': sha(Path(__file__).resolve()),
    }
    (HERE / 'result.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('check_count', 'archive_member_count',
        'archive_payload_bytes', 'cause', 'commands_closed', 'pack_members_verified',
        'adoption_members_verified', 'checkout_dependencies_verified', 'denied_active_api_attempts')}, sort_keys=True))


def main():
    if sys.argv[1:] == ['--summarize']:
        summarize()
        return
    if sys.argv[1:] == ['--verify']:
        verify_evidence()
        return
    need(not sys.argv[1:], 'Unsupported inspection arguments')
    artifact = HERE / 'local/artifact.zip'
    need(not artifact.is_symlink() and artifact.is_file(), 'Regular artifact required')
    need(artifact.stat().st_size == EXPECTED_BYTES, 'Artifact byte count differs')
    blob = artifact.read_bytes()
    need(hashlib.sha256(blob).hexdigest() == EXPECTED_SHA256, 'Artifact SHA-256 differs')
    rows = []
    texts = {}
    with zipfile.ZipFile(artifact) as archive:
        infos = archive.infolist()
        need(0 < len(infos) <= 1000, 'ZIP member count outside review bound')
        need(len(infos) == len({row.filename for row in infos}), 'Duplicate ZIP members')
        need(sum(row.file_size for row in infos) <= 64 * 1024 * 1024, 'ZIP total size exceeds bound')
        for info in infos:
            name = info.filename
            path = Path(name.rstrip('/'))
            need(isinstance(name, str) and 0 < len(name) <= 1024 and '\\' not in name
                 and name.rstrip('/') not in {'', '.', '..'}
                 and not any(ord(character) < 32 or ord(character) == 127 for character in name)
                 and not path.is_absolute()
                 and path.as_posix() == name.rstrip('/')
                 and not any(piece in {'.', '..', '.git'} for piece in path.parts),
                 'Unsafe ZIP member name')
            need(not info.flag_bits & 1, 'Encrypted ZIP member refused')
            need(info.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}, 'Unsupported ZIP compression')
            mode = info.external_attr >> 16
            need(stat.S_IFMT(mode) in {0, stat.S_IFREG, stat.S_IFDIR}, 'Non-regular ZIP member')
            need(0 <= info.file_size <= 8 * 1024 * 1024, 'ZIP member exceeds bound')
            payload = archive.read(info)
            need(len(payload) == info.file_size, 'ZIP payload length differs')
            rows.append({'path': name, 'bytes': len(payload), 'compressed_bytes': info.compress_size,
                         'sha256': hashlib.sha256(payload).hexdigest(), 'crc32': info.CRC})
            if (name.endswith(('/fixture.stdout', '/fixture.stderr', '/adapter-start.json',
                               '/adapter-result.json', '/receipt.json', '/controls.stdout',
                               '/controls.stderr', '/preflight.stdout', '/preflight.stderr',
                               '/postflight.stdout', '/postflight.stderr'))
                    or '/commands/' in name):
                need(len(payload) <= 512 * 1024, 'Selected text exceeds review bound')
                texts[name] = payload.decode('utf-8', errors='strict')
    result = {'schema': 1, 'artifact': {'path': str(artifact.relative_to(HERE)),
              'bytes': len(blob), 'sha256': EXPECTED_SHA256}, 'members': rows,
              'member_count': len(rows), 'total_payload_bytes': sum(row['bytes'] for row in rows),
              'python': {'executable': sys.executable, 'version': sys.version},
              'denied_active_api_attempts': DENIED, 'selected_texts': texts}
    (HERE / 'local/artifact-inspection.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'members': result['member_count'], 'payload_bytes': result['total_payload_bytes'],
                      'selected_text_paths': sorted(texts), 'denied_active_api_attempts': DENIED}, sort_keys=True))


if __name__ == '__main__':
    main()
