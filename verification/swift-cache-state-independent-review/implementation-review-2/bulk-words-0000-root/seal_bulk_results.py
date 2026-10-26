"""Seal exactly the three admitted public batches; do not execute any candidate."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent
ROOT = HERE.parents[3]
TRANSPORT = REVIEW / 'transport-amendment'
sys.dont_write_bytecode = True
sys.path.insert(0, str(TRANSPORT))
from dedup_transport import validate_pack, object_path
from harness import compare_public, protocol, sha, write_json

SELECTED = [
    ('words', 'f47dc338189df9bfb60df32a6b6d114904f8b58e904055b584c10c4b39a6baa3', '6427da586593d5ecc296580e9ff50e21634e2fb85cf5fc7cadbf846c9aecddb8', 95726, '94bdf9', '673d92'),
    ('transitions', '6861b0ddb63eb3fd2fae1f0ceb8451a4ad66b184b650b93d34ea505d3f689378', 'e0eb9f227e84245cfeb3dd4c66f5a03e710695f5bc621aa1c834dce21f2ab0c9', 81835, 'dab077', '534896'),
    ('sequences', '935fe761e67977cb5d710c1ac2b9e9147a203e7e13c759a87d302da908a4e428', '2215c2701fca5c7802e4e95ae6a7a5dc461959a8e61c9fe196fec494f7553154', 66011, '2dc946', 'fd9f5e')]


def verify_seal(path, digest):
    raw = path.read_bytes()
    if sha(raw) != digest:
        raise ValueError('immutable seal changed')
    data = json.loads(raw)
    for m in data['members']:
        value = (ROOT / m['path']).read_bytes()
        if len(value) != m['bytes'] or sha(value) != m['sha256']:
            raise ValueError('immutable member changed: ' + m['path'])
    return {'path': str(path.relative_to(ROOT)), 'sha256': digest, 'members': len(data['members'])}


def main():
    output = HERE / 'bulk-results-seal.json'
    if output.exists():
        raise ValueError('preserve sealed results')
    prior = [
        verify_seal(REVIEW / 'correction-control-seal.json', '13b4e77974be545bb34274ddba68b6b3b159e8d2287390dcffff864373d136c5'),
        verify_seal(TRANSPORT / 'transport-seal.json', '27d8d6313c7578c8bb486d5044b68f1a1482945e338e7c111ec8635f04879afc'),
        verify_seal(REVIEW.parent / 'implementation-review-1/review-seal.json', '3c189178c6c8cef3fa2236bbe9d3d0c8cb2806fc4afcf9940bdc7af67a444382'),
        verify_seal(ROOT / 'verification/swift-cache-state-implementation/correction-1/candidate-repo-seal.json', 'b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6')]
    directories = []
    batches = []
    parents = []
    cleanup_products = []
    for kind, digest, previous_digest, session, first_chunk, last_chunk in SELECTED:
        directory = REVIEW / ('bulk-' + kind + '-0000-root')
        directories.append(directory)
        admission_name = 'bulk-' + kind + '-0000-admission-v2.json'
        admission_path = ROOT / 'verification/swift-semantic-adapter-root-review' / admission_name
        raw = admission_path.read_bytes()
        if sha(raw) != digest:
            raise ValueError('exact v2 admission changed')
        admission = json.loads(raw)
        if ROOT / admission['review_output_directory'] != directory:
            raise ValueError('output ownership binding')
        copied = directory / 'root-admission-v2.json'
        copied.write_bytes(raw)
        old_name = 'bulk-' + kind + '-0000-admission.json'
        old_raw = (admission_path.parent / old_name).read_bytes()
        if sha(old_raw) != previous_digest:
            raise ValueError('prior ambiguous receipt changed')
        (directory / 'root-admission-v1-superseded-unused.json').write_bytes(old_raw)
        summary = json.loads((directory / 'batch-summary.json').read_bytes())
        if summary['executed_count'] != 64 or summary['failed_cases'] != 0 or summary['orchestration_failure'] is not None:
            raise ValueError('batch result not clean')
        pack = validate_pack(directory / 'transport')
        if (pack['kind'], pack['start'], pack['count']) != (kind, 0, 64):
            raise ValueError('exact batch selection changed')
        case_dirs = sorted((directory / 'cases').iterdir())
        if len(case_dirs) != 64:
            raise ValueError('actual case directory count')
        for index, (case, case_dir) in enumerate(zip(pack['cases'], case_dirs)):
            result = json.loads((case_dir / 'result.json').read_bytes())
            diagnostic = protocol((case_dir / 'driver.stdout').read_bytes())
            if result['case'] != case['id'] or result['expected_words'] != case['expected_words'] or result['diagnostic'] != diagnostic or result['failures']:
                raise ValueError('case identity/expected/actual failure')
            refs = [object_path(directory / 'transport', pack, case['input_refs'][role], role) for role in ['stream', 'profile', 'context']]
            observed_hashes = [sha(p.read_bytes()) for p in refs]
            if result['input_sha256_before'] != observed_hashes or result['input_sha256_after'] != observed_hashes or result['input_refs'] != case['input_refs']:
                raise ValueError('lossless input mapping/integrity')
            report = (case_dir / 'report.bin').read_bytes()
            if sha(report) != result['report_sha256'] or compare_public(diagnostic, case['expected_words'], report, refs[2].read_bytes(), refs[0].read_bytes()):
                raise ValueError('retained full32/report/input assertion mismatch')
        command_receipts = sorted((directory / 'commands').glob('*.json')) + sorted((directory / 'cases').glob('*/driver.json'))
        times = []
        for p in command_receipts:
            r = json.loads(p.read_bytes())
            if r['exit_code'] != 0 or r['timed_out'] or r['output_truncated'] or r['spawn_failure'] is not None:
                raise ValueError('child command failure')
            if r['timeout_seconds'] != 60 or r['output_byte_cap_per_stream'] != 1048576:
                raise ValueError('child command bound changed')
            for key in ['stdout', 'stderr']:
                if sha(Path(r[key]).read_bytes()) != r[key + '_sha256']:
                    raise ValueError('raw child output changed')
            times.append({'at': r['at'], 'duration_seconds': r['duration_seconds'], 'receipt': str(p.relative_to(ROOT))})
        if len(command_receipts) != 67:
            raise ValueError('compiler/version/driver command count')
        cleanup = json.loads((directory / 'cleanup.json').read_bytes())
        if len(cleanup['products']) != 2:
            raise ValueError('returned owned compiler product count')
        for product in cleanup['products']:
            if not product['all_owned_commands_returned'] or not product['removed'] or (ROOT / product['path']).exists():
                raise ValueError('owned binary cleanup incomplete')
            cleanup_products.append(product)
        argv = ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str((TRANSPORT / 'dedup_runner.py').relative_to(ROOT)),
                '--admission', str(admission_path.relative_to(ROOT)), '--admission-sha256', digest,
                '--transport-seal-sha256', '27d8d6313c7578c8bb486d5044b68f1a1482945e338e7c111ec8635f04879afc',
                '--case-set', kind, '--start', '0', '--count', '64']
        parents.append({'kind': kind, 'argv': argv, 'cwd': str(ROOT), 'observed_outer_exit': 0,
            'observed_outer_combined_output': '', 'exec_session_id': session,
            'outer_start_chunk': first_chunk, 'outer_completion_chunk': last_chunk,
            'parent_exact_wall_clock_duration_measured': False,
            'timing_limitation': 'Original direct parent invocations were observed through exec/write_stdin; no exact parent wall-clock interval is invented. Every actual compiler/version/driver child has exact UTC start/duration and deadline in its raw command receipt.',
            'actual_child_times': times,
            'output_directory_birth_UTC': datetime.fromtimestamp(directory.stat().st_birthtime, timezone.utc).isoformat(),
            'batch_summary_last_written_UTC': datetime.fromtimestamp((directory / 'batch-summary.json').stat().st_mtime, timezone.utc).isoformat()})
        batches.append({'kind': kind, 'start': 0, 'count': 64, 'passed': 64, 'failed': 0,
            'public_File_only': True, 'private_cases': 0, 'new_API_controls': 0,
            'logical_input_bytes': pack['logical_input_bytes'], 'unique_input_bytes': pack['unique_input_bytes'],
            'admission_sha256': digest, 'summary_path': str((directory / 'batch-summary.json').relative_to(ROOT)),
            'source_tree_digest': admission['source_tree_digest'], 'rustc_sha256': admission['rustc_sha256'],
            'rustc_version': admission['rustc_version']})
    write_json(HERE / 'outer-parent-invocations.json', {'scope': 'Exact actual parent argv/observed exec exits with complete inner timing; no global batch timeout',
        'python': sys.version, 'python_executable_sha256_observed_at_seal': sha(Path(sys.executable).read_bytes()), 'parents': parents})
    write_json(HERE / 'bulk-results-receipt.json', {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'three-initial-root-selected-public-batches-pass', 'command': sys.argv, 'python': sys.version,
        'script_sha256': sha(Path(__file__).read_bytes()), 'batches': batches,
        'total_public_cases': 192, 'passed': 192, 'failed': 0, 'orchestration_failures': 0,
        'new_API_controls': 0, 'new_private_controls': 0, 'additional_batches_run': 0,
        'execution_order': ['words', 'transitions', 'sequences'],
        'stop_policy': 'Preflight mismatch identified before execution. Root issued immutable v2 receipts clarifying complete each<=64-case batch, preserve all failures, stop before next batch on any failure. All three had zero failures; no sealed tooling/expectations changed.',
        'unchanged_prior_seals_and_candidate_verified': prior,
        'all_six_returned_owned_binary_products_hashed_then_removed': cleanup_products,
        'parent_timing_limitation': 'Exact per-child UTC/durations/deadlines and output metadata times retained; exact parent wall-clock duration was not separately instrumented and is not claimed.',
        'source_budget_lifetime_or_implementation_credit': False,
        'source_accounting_blockers': 'Remain open in separate source review; finite semantic passes do not alter them.',
        'full32_private_terminal_and_other_private_matrices': 'Unrun; zero new runtime credit.',
        'all_authority_getters_false': True, 'product_source_or_prior_sealed_files_changed': False,
        'native_UI_capture_simulator_emulator_phone_or_process_discovery': False,
        'implementation_accepted': False, 'GA_qualified': False})
    members = []
    for directory in directories:
        for p in sorted(directory.rglob('*')):
            if not p.is_file() or p == output:
                continue
            if p.is_symlink():
                raise ValueError('symlink in sealed results')
            raw = p.read_bytes()
            members.append({'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)})
    write_json(output, {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Exactly three root-selected first64 public word/transition/sequence batches and retained raw evidence; no other execution or source acceptance',
        'command': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str(Path(__file__).relative_to(ROOT))],
        'python': sys.version, 'script_sha256': sha(Path(__file__).read_bytes()),
        'members': members, 'member_count': len(members), 'member_bytes': sum(m['bytes'] for m in members),
        'implementation_accepted': False, 'GA_qualified': False})
    print(json.dumps({'seal': str(output.relative_to(ROOT)), 'sha256': sha(output.read_bytes()), 'members': len(members), 'bytes': sum(m['bytes'] for m in members)}))


if __name__ == '__main__':
    main()
