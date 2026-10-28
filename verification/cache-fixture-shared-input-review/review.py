#!/usr/bin/env python3
"""Bounded independent source/file-model review. Never execute product or compiler."""
import ast
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'verification/swift-cache-state-ci'
PROPOSAL = ROOT / 'verification/cache-fixture-debug-timeout-investigation'
DENIED = []


def blocked(*args, **kwargs):
    DENIED.append('patched process/socket/signal/wait entry')
    raise RuntimeError('Offline review forbids process/socket/signal/wait operations')


def audit(event, args):
    if event.startswith(('subprocess.', 'socket.')) or event in {
        'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty',
        'os.exec', 'os.kill', 'os.killpg', 'os.startfile',
    }:
        DENIED.append(event)
        raise RuntimeError('Offline review forbids ' + event)
    targets = []
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        flags = args[2]
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            targets = [args[0]]
    elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod'}:
        targets = [args[0]]
    elif event in {'os.rename', 'os.link', 'os.symlink'}:
        targets = list(args[:2])
    for raw in targets:
        # shutil.rmtree uses relative names plus owned-directory descriptors.
        p = Path(os.fsdecode(raw))
        if not p.is_absolute():
            continue
        if not p.is_relative_to(HERE):
            raise RuntimeError('Review write outside assigned sibling: ' + str(p))


sys.addaudithook(audit)
for name in ['system', 'posix_spawn', 'posix_spawnp', 'fork', 'forkpty', 'kill',
             'killpg', 'wait', 'waitpid', 'wait3', 'wait4']:
    if hasattr(os, name):
        setattr(os, name, blocked)
for name in ['Popen', 'run', 'call', 'check_call', 'check_output']:
    setattr(subprocess, name, blocked)
for name in ['signal', 'alarm', 'setitimer', 'pause', 'sigwait', 'sigwaitinfo',
             'sigtimedwait', 'pthread_kill']:
    if hasattr(signal, name):
        setattr(signal, name, blocked)
time.sleep = blocked


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(value, message):
    if not value:
        raise AssertionError(message)


CHECKS = []


def check(name, fn):
    fn()
    CHECKS.append({'name': name, 'passed': True})


def rejects(fn):
    try:
        fn()
    except (AssertionError, RuntimeError, OSError, ValueError):
        return
    raise AssertionError('negative control admitted')


READSET = {}


def read(path):
    data = path.read_bytes()
    READSET[str(path.relative_to(ROOT))] = {'bytes': len(data), 'sha256': sha(data)}
    return data


def region(text, start, end):
    a = text.index(start)
    return text[a:text.index(end, a)]


original_path = BASE / 'pack/source/regression/independent_tests.rs'
candidate_path = PROPOSAL / 'candidate/source/regression/independent_tests.rs'
original = read(original_path).decode()
candidate = read(candidate_path).decode()
need(sha(original.encode()) == '7c9c3006e1e7fd6a927fc7c3ca472c33abe3084f50a1f5aea0d31c6d9d75c411', 'original source binding')
need(sha(candidate.encode()) == 'f7d62c01e251642677e22f7595af9683f9c451f1db43683be5d2ef86fedba141', 'candidate source binding')
for name in ['README.md', 'candidate-receipt.json', 'candidate-source-audit.json',
             'context-harness-proposal.diff', 'git-source-bindings.json', 'seal.json',
             'report.json', 'ordered-context-vector-inventory.json', 'prepare_candidate.py']:
    read(PROPOSAL / name)
for name in ['check_cache_state.py', 'test_runner.py', 'README.md']:
    read(BASE / name)
read(ROOT / '.github/workflows/verify.yml')
manifest_bytes = read(BASE / 'pack/manifest.json')
manifest = json.loads(manifest_bytes)
for member in manifest['members']:
    data = read(BASE / 'pack' / member['path'])
    need(len(data) == member['bytes'] and sha(data) == member['sha256'], 'frozen member differs ' + member['path'])

spec = importlib.util.spec_from_file_location('reviewed_fixture_runner', BASE / 'check_cache_state.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
check('actual_runner_verifies_unchanged_frozen_pack', lambda: runner.verify_pack(BASE / 'pack'))

start = '#[test]\nfn context_schema_scalar_reserved_and_lengths() {'
end = '#[test]\nfn profile_schema_reserved_digest_and_row_boundaries() {'
old_method = region(original, start, end)
new_method = region(candidate, start, end)
helpers = region(candidate, '#[derive(Default)]\nstruct ContextPhaseTimes', '#[test]\nfn independently_encoded_all_kind_baseline()')
restored = candidate.replace(helpers, '', 1).replace(new_method, old_method, 1)
check('only_helper_insertion_and_context_method_change', lambda: need(restored == original, 'source changed outside allowed scope'))
old_run = region(original, 'fn run(f: &Fixture', '\n#[test]')
new_run = region(candidate, 'fn run(f: &Fixture', '\n#[derive(Default)]')
check('original_general_run_byte_exact', lambda: need(new_run == old_run, 'general run changed'))
old_assertions = region(old_run, '    output.seek(', '    drop(')
new_assertions = region(helpers, '    output.seek(', '    let report_assert=')
check('result_report_assertions_byte_exact', lambda: need(new_assertions == old_assertions, 'assertions differ'))
diff = ''.join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True),
    fromfile='a/verification/swift-cache-state-ci/pack/source/regression/independent_tests.rs',
    tofile='b/verification/swift-cache-state-ci/pack/source/regression/independent_tests.rs'))
check('proposal_diff_reproduced_exactly', lambda: need(diff.encode() == read(PROPOSAL / 'context-harness-proposal.diff'), 'diff differs'))

MAX = 2**64 - 1
context = bytearray(8192)
for i, value in enumerate([int.from_bytes(b'MIXFIX01', 'little'), 1, 8192, 1, 32, 33, 1000, 3, 2, 3, 1, 100, 1000, 500, 0, 0]):
    context[i*8:i*8+8] = value.to_bytes(8, 'little')
for digest in range(8):
    context[128+digest*32:160+digest*32] = bytes([17+digest]) * 32
baseline = bytes(context)


def vectors(source_method):
    token = 'for (word,value) in ['
    scalars = ast.literal_eval('[' + source_method.split(token, 1)[1].split('] {', 1)[0].replace('M', str(MAX)) + ']')
    need('for word in 48..1024 {' in source_method, 'reserved domain differs')
    need('for len in [0usize,1,8191,8193] {' in source_method, 'length domain differs')
    out = []
    for word, value in scalars:
        data = bytearray(baseline)
        data[word*8:word*8+8] = value.to_bytes(8, 'little')
        out.append((f'context-{word}-{value}', bytes(data)))
    for word in range(48, 1024):
        data = bytearray(baseline)
        data[word*8:word*8+8] = (1).to_bytes(8, 'little')
        out.append((f'context-reserved-{word}', bytes(data)))
    for length in [0, 1, 8191, 8193]:
        data = baseline[:length] + bytes(max(0, length-len(baseline)))
        out.append((f'context-length-{length}', data))
    return out


expected_vectors = vectors(old_method)
inventory = json.loads(read(PROPOSAL / 'ordered-context-vector-inventory.json'))


def verify_vectors(method):
    actual = vectors(method)
    need(actual == expected_vectors and len(actual) == 1003, 'ordered vector bytes differ')
    for i, ((label, data), record) in enumerate(zip(actual, inventory)):
        need((record['ordinal'], record['label'], record['context_bytes'], record['context_sha256']) ==
             (i, label, len(data), sha(data)), 'inventory context identity differs')


check('all_1003_ordered_context_bytes_match_independent_encoder_and_inventory', lambda: verify_vectors(new_method))
check('negative_changed_scalar_rejected', lambda: rejects(lambda: verify_vectors(new_method.replace('(1,2)', '(1,3)', 1))))
check('negative_removed_scalar_rejected', lambda: rejects(lambda: verify_vectors(new_method.replace('(1,2),', '', 1))))
check('negative_reordered_scalars_rejected', lambda: rejects(lambda: verify_vectors(new_method.replace('(1,2),(2,8191)', '(2,8191),(1,2)', 1))))
check('negative_reserved_endpoint_rejected', lambda: rejects(lambda: verify_vectors(new_method.replace('48..1024', '48..1023', 1))))
check('negative_length_domain_rejected', lambda: rejects(lambda: verify_vectors(new_method.replace('8191,8193', '8191,8192', 1))))


def clone_model():
    before = bytes(context)
    a, b = bytearray(context), bytearray(context)
    a[8] ^= 1
    need(bytes(b) == before and bytes(context) == before, 'independent context clones')
    alias = context
    alias[8] ^= 1
    rejects(lambda: need(bytes(context) == before, 'baseline changed through alias'))
    alias[8] ^= 1


check('independent_context_clone_model_with_alias_negative', clone_model)
work = HERE / 'control-scratch'
need(not work.exists(), 'review control scratch must be fresh')
work.mkdir()


def file_model():
    shared = work / 'shared'
    shared.mkdir()
    stream, profile = shared / 'stream', shared / 'profile'
    stream.write_bytes(b'stream-payload')
    profile.write_bytes(b'profile-payload')
    for path in [stream, profile]:
        path.chmod(path.stat().st_mode & ~0o222)
    with stream.open('rb') as one, stream.open('rb') as two:
        need(one.tell() == two.tell() == 0, 'fresh initial cursors')
        one.read(1)
        need(two.tell() == 0, 'fresh opens must have independent cursor')
        rejects(lambda: need(one.tell() == 0, 'reused cursor must refuse'))
        rejects(lambda: two.write(b'x'))
    need(stream.stat().st_mode & 0o222 == 0, 'readonly bits absent')
    profile.chmod(profile.stat().st_mode | stat.S_IWUSR)
    rejects(lambda: need(profile.stat().st_mode & 0o222 == 0, 'writable profile refused'))
    profile.chmod(profile.stat().st_mode & ~0o222)
    case = work / 'case'
    case.mkdir()
    inp, report = case / 'context', case / 'report'
    inp.write_bytes(b'context')
    with report.open('xb+') as output:
        need(output.tell() == 0 and report.stat().st_size == 0, 'fresh output')
        rejects(lambda: report.open('xb+'))
    paths = [stream, profile, inp, report]
    identities = [(p.stat().st_dev, p.stat().st_ino) for p in paths]
    need(len(set(identities)) == 4, 'four distinct identities')
    linked = case / 'linked'
    os.link(profile, linked)
    alias_ids = identities[:3] + [(linked.stat().st_dev, linked.stat().st_ino)]
    rejects(lambda: need(len(set(alias_ids)) == 4, 'hardlink output alias refused'))
    linked.unlink()
    # A simulated assertion failure performs no source cleanup; retained files stay.
    try:
        raise AssertionError('injected result assertion failure')
    except AssertionError:
        need(all(p.exists() for p in paths), 'failure inputs must remain')
    shutil.rmtree(case)
    need(stream.exists() and profile.exists(), 'shared inputs outlive case cleanup')
    need(profile.read_bytes() == b'profile-payload', 'shared content unchanged')
    # Content drift is rejected independently of mode assertions.
    profile.chmod(profile.stat().st_mode | stat.S_IWUSR)
    profile.write_bytes(b'drift')
    profile.chmod(profile.stat().st_mode & ~0o222)
    rejects(lambda: need(profile.read_bytes() == b'profile-payload', 'shared drift refused'))
    shutil.rmtree(shared)


check('real_python_file_cursor_readonly_alias_freshness_and_failure_models', file_model)


def actual_retention():
    out = work / 'retention'
    out.mkdir()
    scratch = out / 'scratch'
    scratch.mkdir()
    marker = {'purpose': 'independent shared-input retention control', 'token': 'fixed-pure-control'}
    runner.save(scratch / 'ownership.json', marker)
    shared = scratch / '0-context-shared-inputs'
    shared.mkdir()
    expected = {}
    for name, data in [('stream', b'stream-evidence'), ('profile', b'profile-evidence')]:
        path = shared / name
        path.write_bytes(data)
        path.chmod(path.stat().st_mode & ~0o222)
        expected[str(path.relative_to(scratch))] = data
    case = scratch / '1-context-1-2'
    case.mkdir()
    for name, data in [('context', b'context-evidence'), ('report', b'')]:
        path = case / name
        path.write_bytes(data)
        expected[str(path.relative_to(scratch))] = data
    commands = types.SimpleNamespace(active=None, receipt={'commands': []})
    ident = runner.identity(scratch)
    rejects(lambda: runner.cleanup(out, scratch, ident, {'token': 'wrong'}, set(), commands))
    need(all((scratch / n).exists() for n in expected), 'wrong marker preserves scratch')
    held = types.SimpleNamespace(active=object(), receipt={'commands': []})
    rejects(lambda: runner.cleanup(out, scratch, ident, marker, set(), held))
    need(scratch.exists(), 'custody hold preserves scratch without probing')
    result = runner.cleanup(out, scratch, ident, marker, set(), commands)
    need(result['removed'] and not scratch.exists(), 'positive runner cleanup')
    retained = json.loads((out / 'retention.json').read_bytes())['files']
    need({r['path'] for r in retained} == set(expected), 'exact failed case/shared retention')
    for row in retained:
        need((out / row['content']).read_bytes() == expected[row['path']], 'retained content differs')
    shutil.rmtree(out)


check('actual_runner_cleanup_retains_failed_shared_and_case_bytes_with_marker_and_hold_negatives', actual_retention)
need(not list(work.iterdir()), 'all owned file controls cleaned')
work.rmdir()
check('profile_traffic_arithmetic', lambda: need((2_560_512*1003, 2_560_512*1002) == (2_568_193_536, 2_565_633_024), 'traffic arithmetic'))
for path, binding in READSET.items():
    data = (ROOT / path).read_bytes()
    need(len(data) == binding['bytes'] and sha(data) == binding['sha256'], 'readset changed during review: ' + path)
check('postflight_exact_readset_preserved', lambda: need(True, 'postflight'))
report = {
    'schema': 1,
    'decision': 'source-acceptable-for-one-root-selected-bounded-remote-full-fixture-diagnostic',
    'blocking_findings': [],
    'candidate_sha256': sha(candidate.encode()),
    'original_sha256': sha(original.encode()),
    'compiler_or_product_runtime_executed': False,
    'scope': 'Independent source review, pure Python vector checks, actual Python file models and frozen runner retention function only; no Rust compilation or timing authority.',
    'checks': CHECKS,
    'check_count': len(CHECKS),
    'tool': {'version': sys.version, 'platform': sys.platform, 'command': 'python3 -B verification/cache-fixture-shared-input-review/review.py'},
    'process_socket_signal_wait_entries_denied': True,
    'unexpected_blocked_operation_attempts': DENIED,
    'owned_control_scratch_removed': True,
    'frozen_pack_manifest_sha256': sha(manifest_bytes),
    'frozen_pack_tree_sha256': manifest['tree_sha256'],
    'readset': [{'path': p, **binding} for p, binding in sorted(READSET.items())],
    'readset_tree_sha256': runner.tree([{'path': p, **binding} for p, binding in sorted(READSET.items())]),
    'limitations': [
        'Static source/vector equivalence and Python models do not prove Rust compile success, analyzer runtime behavior, performance or a 60-second pass.',
        'prepare_ms excludes baseline construction, shared-input creation/checks and caller context clones; elapsed_ms includes them. Final shared validation/removal follows the completed=1003 progress line.',
        'Readonly bits are not adversarial custody; the existing trusted, quiescent checkout requirement remains.',
        'The prior timeout remains failed. Later unchanged passes mean no current red-CI or product-regression claim.',
        'Physical phones and native UI/simulator/emulator/capture checks remain paused or pending; no GA/release authority.',
    ],
}
(HERE / 'review.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
print(json.dumps({'decision': report['decision'], 'checks': len(CHECKS), 'readset_files': len(READSET), 'readset_tree_sha256': report['readset_tree_sha256'], 'unexpected_denied_attempts': len(DENIED)}, sort_keys=True))
