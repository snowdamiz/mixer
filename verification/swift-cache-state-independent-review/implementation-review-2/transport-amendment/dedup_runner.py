"""Proposed later bounded public runner; exact separate root admission required."""
import argparse
import json
from pathlib import Path
import sys
from dedup_transport import HERE, ROOT, PREP, build_pack, validate_pack, object_path, sealed
from harness import bounded, compare_public, protocol, sha, write_json


def admission(path, digest, transport_digest, kind, start, count):
    value = sealed.read_root_admission(path, digest)
    ext = value.get('dedup_transport')
    if not isinstance(ext, dict) or ext.get('seal_sha256') != transport_digest or ext.get('execution_authorized') is not True:
        raise ValueError('no separate exact root transport admission')
    if kind not in ('words', 'transitions', 'sequences') or type(start) is not int or type(count) is not int or start < 0 or not 1 <= count <= 64:
        raise ValueError('public bulk kinds only; no private terminal execution')
    if (value.get('selected_case_set'), value.get('selected_start'), value.get('selected_count')) != (kind, start, count):
        raise ValueError('root exact selected batch differs')
    seal_path = HERE / 'transport-seal.json'
    raw = seal_path.read_bytes()
    if sha(raw) != transport_digest:
        raise ValueError('transport seal hash')
    closure = json.loads(raw)
    for m in closure['members']:
        if not m['path'].startswith(str(HERE.relative_to(ROOT)) + '/'):
            raise ValueError('transport closed ownership')
        member = (ROOT / m['path']).read_bytes()
        if len(member) != m['bytes'] or sha(member) != m['sha256']:
            raise ValueError('transport member changed')
    if not value['review_output_directory'].startswith('verification/swift-cache-state-independent-review/implementation-review-2/bulk-'):
        raise ValueError('new admitted owned batch output only')
    return value


def execute(value, kind, start, count):
    """Equivalent public protocol/assertions, shared content inputs, no API reruns."""
    out = ROOT / value['review_output_directory']
    if out.exists():
        raise ValueError('preserve existing batch')
    out.mkdir(parents=True)
    commands = out / 'commands'
    work = out / 'work'
    work.mkdir()
    products = []
    results = []
    failure = None
    cleanup = []
    try:
        build_pack(kind, start, count, out / 'transport')
        pack = validate_pack(out / 'transport')
        entry = sealed.stage_candidate(value, work)
        tool = bounded([value['rustc'], '--version', '--verbose'], ROOT, commands, 'compiler-version')
        if tool['exit_code'] != 0 or tool['timed_out'] or tool['output_truncated'] or Path(tool['stdout']).read_text() != value['rustc_version']:
            raise ValueError('exact compiler identity')
        lib = work / 'libmixer_fixture_cache_state.rlib'
        driver = work / 'public-driver'
        products = [lib, driver]
        for name, argv in [
            ('library', [value['rustc'], '--edition=' + value['edition'], '--crate-name', 'mixer_fixture_cache_state', '--crate-type', 'rlib', str(entry), '-o', str(lib)]),
            ('driver', [value['rustc'], '--edition=2021', str(work / 'public_driver.rs'), '--extern', 'mixer_fixture_cache_state=' + str(lib), '-o', str(driver)])]:
            r = bounded(argv, ROOT, commands, name)
            if r['exit_code'] != 0 or r['timed_out'] or r['output_truncated'] or r['spawn_failure'] is not None:
                raise ValueError('compilation failure retained')
        for ordinal, case in enumerate(pack['cases']):
            directory = out / 'cases' / (str(ordinal).zfill(2) + '-' + case['id'])
            directory.mkdir(parents=True)
            paths = [object_path(out / 'transport', pack, case['input_refs'][role], role) for role in ['stream', 'profile', 'context']]
            before = [sha(p.read_bytes()) for p in paths]
            report = directory / 'report.bin'
            r = bounded([str(driver), *[str(p) for p in paths], str(report)], ROOT, directory, 'driver')
            problems = []
            diagnostic = None
            if r['exit_code'] != 0 or r['timed_out'] or r['output_truncated'] or r['spawn_failure'] is not None:
                problems.append('driver/harness execution failure')
            else:
                try:
                    diagnostic = protocol(Path(r['stdout']).read_bytes())
                    problems += compare_public(diagnostic, case['expected_words'], report.read_bytes(), paths[2].read_bytes(), paths[0].read_bytes())
                except (ValueError, OSError) as exc:
                    problems.append('driver/report protocol error: ' + str(exc)[:256])
            after = [sha(p.read_bytes()) for p in paths]
            if before != after:
                problems.append('input bytes changed')
            item = {'case': case['id'], 'source_index': case['index'], 'source_item_ref': case['source_item'],
                    'input_refs': case['input_refs'], 'expected_words': case['expected_words'], 'diagnostic': diagnostic,
                    'input_sha256_before': before, 'input_sha256_after': after,
                    'driver_exit': r['exit_code'], 'timed_out': r['timed_out'], 'output_truncated': r['output_truncated'],
                    'report_sha256': sha(report.read_bytes()) if report.exists() else None,
                    'failures': problems, 'layer': case['coverage_layer'], 'actual_candidate_executed': True}
            write_json(directory / 'result.json', item)
            results.append(item)
        validate_pack(out / 'transport')
    except Exception as exc:
        failure = {'type': type(exc).__name__, 'message': str(exc)[:1024]}
    finally:
        for p in products:
            if p.exists():
                raw = p.read_bytes()
                item = {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw), 'all_owned_commands_returned': True}
                p.unlink()
                item['removed'] = not p.exists()
                cleanup.append(item)
        write_json(out / 'cleanup.json', {'products': cleanup, 'only_returned_owned_products_removed': True, 'raw_sources_commands_data_and_failures_preserved': True})
        write_json(out / 'batch-summary.json', {'kind': kind, 'start': start, 'admitted_count': count, 'executed_count': len(results),
            'failed_cases': sum(bool(v['failures']) for v in results), 'orchestration_failure': failure,
            'candidate_seal_sha256': value['candidate_seal_sha256'], 'source_proof_accepted': False,
            'API_compile_controls_executed_this_batch': 0, 'private_controls': 0,
            'scope': 'public actual-File only; shared input objects retain exact raw bytes and per-case mapping',
            'implementation_accepted': False, 'GA_qualified': False})
    return 0 if failure is None and len(results) == count and all(not r['failures'] for r in results) else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--admission', required=True)
    parser.add_argument('--admission-sha256', required=True)
    parser.add_argument('--transport-seal-sha256', required=True)
    parser.add_argument('--case-set', choices=['words', 'transitions', 'sequences'], required=True)
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--count', type=int, required=True)
    args = parser.parse_args()
    value = admission(args.admission, args.admission_sha256, args.transport_seal_sha256, args.case_set, args.start, args.count)
    raise SystemExit(execute(value, args.case_set, args.start, args.count))


if __name__ == '__main__':
    main()
