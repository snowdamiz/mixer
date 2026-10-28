#!/usr/bin/env python3
"""One root-released frozen independent saved-raw parse and candidate comparison.

No producer imports/replay, compiler, child, runtime or process query. A failure
is preserved and ends this invocation without retry.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'verification/swift-root-bound-work-storage-layout-probe'
V2 = ROOT / 'verification/swift-root-bound-work-storage-layout-probe-v2'
V3 = ROOT / 'verification/swift-root-bound-work-storage-layout-probe-v3'
A1 = ROOT / 'verification/swift-root-bound-layout-observation-amendment'
A2 = ROOT / 'verification/swift-root-bound-layout-observation-amendment-v2'
WARNINGS = ROOT / 'verification/swift-root-bound-layout-warning-classification'
RELEASE = ROOT / 'verification/swift-semantic-adapter-root-review/root-bound-layout-observation-amendment-release.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def need(value, detail):
    if not value:
        raise ValueError(detail)


def hashed(path, deadline):
    need(time.monotonic() < deadline, 'custody deadline')
    need(path.is_file() and not path.is_symlink(), 'not regular non-symlink input: ' + str(path))
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while True:
            need(time.monotonic() < deadline, 'custody hash deadline')
            raw = stream.read(262144)
            if not raw:
                break
            digest.update(raw)
            size += len(raw)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def custody(deadline):
    verified = {}
    def pin(row, base):
        path = base / row['path']
        actual = hashed(path, deadline)
        need(actual == {key: row[key] for key in ('bytes', 'sha256')}, 'input pin mismatch: ' + str(path))
        verified[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = actual
    def seal(base, name, expected, count, extras=None):
        raw = (base / name).read_bytes()
        need(sha(raw) == expected, 'seal digest: ' + str(base / name))
        value = load(base / name)
        need(len(value['members']) == count, 'seal member count')
        if 'tree_sha256' in value:
            need(sha(canonical(value['members'])) == value['tree_sha256'], 'seal tree')
        pin({'path': name, 'bytes': len(raw), 'sha256': expected}, base)
        for row in value['members']:
            pin(row, base)
        if extras is not None:
            found = set()
            for path in base.rglob('*'):
                need(time.monotonic() < deadline and not path.is_symlink(), 'inventory deadline or symlink')
                if path.is_file():
                    found.add(path.relative_to(base).as_posix())
            need(found == {row['path'] for row in value['members']} | {name} | set(extras), 'closed membership')
    command_names = ['plan.json', 'plan.json.staged', 'owned-process.json', 'owned-process.json.staged',
                     'receipt.json', 'receipt.json.staged', 'stderr', 'stdout']
    actual_names = ['candidate-observation.json', 'candidate-observation.json.staged', 'receipt.json', 'receipt.json.staged']
    seal(OLD, 'seal.json', 'c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9', 173, [])
    seal(V2, 'seal.json', '76fda3e073db9bb7408275cf5d8eb494cf491e5a9cd0a894ba8cca35171127f8', 16, [])
    seal(V3, 'seal.json', '898e88217ab2f04505d09571dbd8748b85cabc3b443a0dde12c47f4c800ed72c', 17, ['command/' + name for name in command_names])
    seal(A1, 'seal.json', '298d2f3e9ac0f5ef0abacdeb24996d3a8d1031de02c91cb2cba82a62236a8723', 22, [])
    seal(A2, 'seal.json', '409a1e4fcea8ac54cd7e96b4ab179bab397f4e49c19d019b1751307ab8e3d8a3', 16, ['actual/' + name for name in actual_names])
    seal(WARNINGS, 'seal.json', '39976085aa6fd3cebf5c12bb6376358c46b11223df8347b8fb70ef12c20be5ab', 9, [])
    for name, digest, count in [
        ('preaccess-seal.json', '001ec6fbfb69a6c784083615323df670c9d932ecace8fd598fc68447867d9d67', 22),
        ('review-01-seal.json', 'edbf7e50d0d8b1847ac75d391d47ba6a16c17e73e6811b153203b8cafe5fc15c', 5),
        ('review-02-seal.json', '8409755f4e955a4ccdc2132eeea5b3218aee44fbe87127d288f434360852a0fa', 5),
        ('review-03-seal.json', '373f849c3ce8aafa861ca4c9585d9521794cd85f43259df47ef4858fa0bcb753', 5),
        ('terminal-v3-review-seal.json', '4e42f67ff992fe7f3c9192b638ea9960eee4d3787bf5eeb40443113f5592760e', 5),
        ('amendment-preaccess-seal.json', 'a3c35353d4749fac7c814489596e8927cf0c268d72fcb41b6e162174a9334b0a', 10),
        ('amendment-review-01-seal.json', 'c0daaec0379bc1b51aa89669ccf617fa0eb78bba222b88e15365fa33c1331186', 5),
        ('amendment-review-02-seal.json', '93b1a0321b464ff1b0f17f846cfbdc27340544f27bec55ea950fc7f13d53c9be', 5)]:
        seal(HERE, name, digest, count)
    plan = load(V3 / 'plan.json')
    need(sha((A2 / 'plan.json').read_bytes()) == '96a08ff362f1e5a4f7b12a51d41873a27c79ddedf585cfdfe9bd046b0c735130', 'selected amendment plan')
    for field, base in [('original_source', Path(plan['original_source']['directory'])), ('diagnostic_source', OLD / 'source/vm')]:
        tree = plan[field]
        need(len(tree['members']) == 146 and sha(canonical(tree['members'])) == tree['tree_sha256'], 'source146 tree')
        found = set()
        for path in base.rglob('*'):
            need(time.monotonic() < deadline and not path.is_symlink(), 'source inventory deadline or symlink')
            if path.is_file():
                found.add(path.relative_to(base).as_posix())
        need(found == {row['path'] for row in tree['members']}, 'source146 membership')
        for row in tree['members']:
            pin(row, base)
    tools = load(OLD / 'toolchain-manifest.json')
    need(len(tools['members']) == 67 and sha(canonical(tools['members'])) == tools['tree_sha256'], 'toolchain tree')
    for row in tools['members']:
        pin(row, Path(tools['root']))
    pin(plan['compiler'], ROOT)
    pin(plan['python']['tool'], ROOT)
    need(sys.version == plan['python']['version'], 'Python version changed')
    for row in load(OLD / 'sdk-path-settings.json')['settings']:
        pin(row, ROOT)
    terminal = load(HERE / 'terminal-v3-review.json')
    for row in terminal['saved_command_members']:
        pin(row, V3 / 'command')
    for name in actual_names:
        path = A2 / 'actual' / name
        observed = hashed(path, deadline)
        pin({'path': name, **observed}, A2 / 'actual')
    for name in ['candidate-observation.json', 'receipt.json']:
        need((A2 / 'actual' / name).read_bytes() == (A2 / 'actual' / (name + '.staged')).read_bytes(), 'amended final/staged bytes differ')
    release_raw = RELEASE.read_bytes()
    pin({'path': str(RELEASE), 'bytes': len(release_raw), 'sha256': '0e79a49bd80a4092a3089c3905b1ecf7a19c91c188c95dc54f8cdb290553d5b5'}, ROOT)
    release = load(RELEASE)
    need(release['offline_saved_raw_parser_released'] is True and release['actual_saved_raw_parser_calls'] == 1 and release['compiler_invocations'] == 0, 'offline release scope')
    need(release['plan_sha256'] == '96a08ff362f1e5a4f7b12a51d41873a27c79ddedf585cfdfe9bd046b0c735130', 'offline release plan')
    need(not (OLD / 'build').exists() and not (V3 / 'command/diagnostic-observation.json').exists(), 'original cleanup/refusal changed')
    return {'members': dict(sorted(verified.items())), 'member_count': len(verified),
            'tree_sha256': sha(canonical(dict(sorted(verified.items()))))}


def write_once(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    started = time.monotonic()
    calls, result, error, pre, post = 0, None, None, None, None
    candidate = None
    try:
        pre = custody(started + 20)
        need(sha((HERE / 'independent_amended_diagnostic_parser.py').read_bytes()) == '0bc60d7d83850b6e3dc6093fc214f7017c5bf1a62d704cde8c10411f9d93116f', 'frozen independent parser changed')
        need(sha((HERE / 'amendment-independent-policy.json').read_bytes()) == '7c4720265b7d284a6ba679f53eef139d278e8f56f89561119862d80fbe704c0d', 'frozen independent policy changed')
        with (V3 / 'command/stderr').open('rb') as stream:
            stderr = stream.read(292319)
        with (V3 / 'command/stdout').open('rb') as stream:
            stdout = stream.read(1)
        need(len(stderr) == 292318 and sha(stderr) == '05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635', 'actual in-memory stderr identity')
        need(stdout == b'', 'actual in-memory stdout identity')
        need(time.monotonic() < started + 45, 'independent parser preflight deadline')
        spec = importlib.util.spec_from_file_location('frozen_independent_amended_terminal_oracle', HERE / 'independent_amended_diagnostic_parser.py')
        oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        calls += 1
        result = oracle.parse_amended(stderr, stdout, 1, mode='saved-raw-root-released')
        need(time.monotonic() < started + 45, 'independent parser completion deadline')
        candidate = load(A2 / 'actual/candidate-observation.json')
        producer_receipt = load(A2 / 'actual/receipt.json')
        need(producer_receipt['actual_saved_raw_parser_calls'] == 1 and producer_receipt['candidate_emitted'] is True and producer_receipt['error'] is None, 'producer terminal outcome')
        need(producer_receipt['bounded_input_memory_sha256_verified_before_parser'] is True, 'producer memory custody receipt')
        need(producer_receipt['root_release_sha256'] == '0e79a49bd80a4092a3089c3905b1ecf7a19c91c188c95dc54f8cdb290553d5b5', 'producer release join')
        need(result['named_layouts'] == candidate['named_layout_candidates'] and len(result['named_layouts']) == 28, '28 named numeric candidates differ')
        need(result['actual_closure'] == candidate['actual_closure_candidate'], 'actual closure numeric candidate differs')
        need(result['source_geometries_verified'] == candidate['source_spans_verified'] == 346, 'complete span count differs')
        need(result['warning_count'] == candidate['exact_source_bound_warnings'] == 3, 'closed warning count differs')
        need(candidate['primary_E0308'] == 56 and candidate['primary_E0512'] == 2 and candidate['summaries'] == 3, 'closed stream counts differ')
        need(result['original_oracle_accepted'] is False and candidate['original_contract_accepted'] is False, 'original refusal overridden')
        need(candidate['layouts_accepted'] is False, 'premature producer layout acceptance')
        post = custody(started + 51)
        need(pre == post, 'custody changed across independent parse')
        need(time.monotonic() < started + 55, 'independent total ceiling')
        result.update({'producer_candidate_sha256': sha((A2 / 'actual/candidate-observation.json').read_bytes()),
                       'all_28_named_and_actual_closure_candidates_match': True,
                       'root_offline_release_sha256': '0e79a49bd80a4092a3089c3905b1ecf7a19c91c188c95dc54f8cdb290553d5b5',
                       'root_acceptance_pending': True})
        write_once(HERE / 'independent-amended-saved-observation.json', result)
    except BaseException as failure:
        error = {'type': type(failure).__name__, 'message': str(failure)}
        traceback.print_exc(file=sys.stderr)
    report = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'INDEPENDENT_RETROSPECTIVE_LAYOUT_OBSERVATIONS_MATCH_ROOT_ACCEPTANCE_RECOMMENDED' if error is None else 'INDEPENDENT_AMENDED_RAW_FAILURE_PRESERVED_NO_RETRY',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
        'script_sha256': sha(Path(__file__).read_bytes()), 'elapsed_seconds': time.monotonic() - started,
        'actual_independent_amended_saved_raw_parser_calls': calls,
        'producer_actual_amended_saved_raw_parser_calls': 1,
        'historical_compiler_invocations': 1, 'new_compiler_runtime_native_ui_capture_child_process_queries': 0,
        'frozen_independent_parser_sha256': '0bc60d7d83850b6e3dc6093fc214f7017c5bf1a62d704cde8c10411f9d93116f',
        'frozen_independent_policy_sha256': '7c4720265b7d284a6ba679f53eef139d278e8f56f89561119862d80fbe704c0d',
        'producer_amendment_plan_sha256': '96a08ff362f1e5a4f7b12a51d41873a27c79ddedf585cfdfe9bd046b0c735130',
        'saved_stderr': {'bytes': 292318, 'sha256': '05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635'},
        'source_revision_from_pinned_historical_root_release': '837e7084a0c6e69a88848b484fa3556563c75a59',
        'source146_tree': '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
        'diagnostic146_tree': '2ec0d8555d6a18d7c8222984faaec3a1543c1a1b800f4b90381f70571215516e',
        'custody_before': pre, 'custody_after': post, 'custody_unchanged': pre is not None and pre == post,
        'all_28_named_and_actual_closure_numeric_candidates_match': error is None,
        'full_stream': {'named_E0308': 56, 'closure_E0512': 2, 'source_geometries': 346, 'whole_exact_warnings': 3, 'exact_summary_and_notes': 3} if error is None else None,
        'actual_closure': result['actual_closure'] if result is not None else None,
        'error': error, 'automatic_retry': False,
        'original_oracle_accepted': False, 'root_retrospective_offline_layout_observation_acceptance_recommended': error is None,
        'acceptance_scope': 'Only target/compiler/source/cfg-bound retrospective diagnostic size/alignment observations for the exact28 named shapes and actual closure. Original frozen rejection remains authoritative for its policy.',
        'prices_backing_peak_funding_ownership_runtime_native_FieldLog_OTA_GA_accepted': False,
        'cleanup': 'No compiler/runtime/native/capture process or generated build artifact created; no such cleanup owed.'}
    write_once(HERE / 'independent-amended-terminal-review.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'actual_independent_amended_saved_raw_parser_calls',
          'all_28_named_and_actual_closure_numeric_candidates_match', 'actual_closure', 'error', 'elapsed_seconds')}))
    return int(error is not None)


if __name__ == '__main__':
    raise SystemExit(main())
