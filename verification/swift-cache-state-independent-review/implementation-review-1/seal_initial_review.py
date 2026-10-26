"""Freeze the initial independent review after exact owned-product cleanup."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREP = HERE.parent / 'execution-preparation'
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('sealed_harness', PREP / 'harness.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def verify_seal(path, digest):
    raw = path.read_bytes()
    assert h.sha(raw) == digest
    seal = json.loads(raw)
    for m in seal['members']:
        member = (ROOT / m['path']).read_bytes()
        assert len(member) == m['bytes'] and h.sha(member) == m['sha256'], m['path']
    return {'path': str(path.relative_to(ROOT)), 'sha256': digest,
            'members': len(seal['members']), 'bytes': sum(m['bytes'] for m in seal['members'])}


def main():
    seal_path = HERE / 'review-seal.json'
    assert not seal_path.exists(), 'refuse to mutate an already sealed packet'
    old = [
        verify_seal(HERE.parent / 'preaccess/seal.json', '1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c'),
        verify_seal(PREP / 'seal.json', '07ff2daf1527fa459f68a4056b749ef71282b98f5b5a4ea634ba9ef19dae5ad6')]
    candidate = verify_seal(ROOT / 'verification/swift-cache-state-implementation/candidate-repo-seal.json', 'caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3')
    control = h.bounded(['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str(HERE / 'review_source.py')], ROOT, HERE / 'commands', 'independent-source-control-final')
    assert control['exit_code'] == 0 and not control['timed_out'] and not control['output_truncated'] and control['spawn_failure'] is None
    cleanup = []
    # Only the three explicit products returned by the already joined public/API commands.
    for name in ['libmixer_fixture_cache_state.rlib', 'public-driver', 'borrowed-positive.rmeta']:
        p = HERE / 'work' / name
        assert p.is_file(), 'expected owned returned product: ' + name
        raw = p.read_bytes()
        item = {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': h.sha(raw),
                'all_owned_commands_returned_before_cleanup': True}
        p.unlink()
        item['removed'] = not p.exists()
        cleanup.append(item)
    h.write_json(HERE / 'public-owned-product-cleanup.json', {
        'schema': 1, 'products': cleanup,
        'scope': 'Only the explicitly returned public-driver/rlib/positive-rmeta products; staged source, fixture Files, reports and all raw failures preserved',
        'unrelated_paths_removed': False, 'process_discovery_used': False})
    h.write_json(HERE / 'commands/private-orchestrator-invocation.json', {
        'scope': 'Transcribed actual outer exec_command result; inner compiler/run receipts are separately retained',
        'argv': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', 'verification/swift-cache-state-independent-review/implementation-review-1/run_private_guards.py'],
        'cwd': str(ROOT), 'exit_code': 1,
        'stdout': '{"preflight_failure": null, "observations": 14, "passing": 6, "failing": 8, "summary": "/Users/andreyyurlov/Documents/dev/mixer/verification/swift-cache-state-independent-review/implementation-review-1/private-guard-run-1/summary.json"}\n',
        'stderr': '', 'reason_for_nonzero': 'Eight exact admitted private witness comparisons failed; no preflight/compiler/protocol failure',
        'script_sha256': h.sha((HERE / 'run_private_guards.py').read_bytes())})
    h.write_json(HERE / 'review-preparation-notes.json', {
        'retained_source_control_attempts': 'source-control-attempt-1 preserves first manual dispositions/script. Final wording corrects P31: why retains15/17 mappings, but canonical guarded product calls never emit them. No semantic expectation changed.',
        'read_only_lookup_misses': [
            {'command': 'cat verification/swift-cache-state-independent-review/preaccess/source-proof-obligations.json', 'exit_code': 1, 'stderr': 'cat: verification/swift-cache-state-independent-review/preaccess/source-proof-obligations.json: No such file or directory\n', 'resolution': 'Read the actual immutable proof-obligations.json; no execution affected.'},
            {'command': 'ls docs/swift-cache-state-implementation-review.md', 'exit_code': 1, 'stderr': 'ls: docs/swift-cache-state-implementation-review.md: No such file or directory\n', 'resolution': 'The owned review document did not exist yet and was subsequently authored.'}],
        'candidate_runtime_reruns_due_to_these_notes': 0})
    receipt = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'initial-independent-review-reject-original-Q9-Q10',
        'candidate': candidate, 'immutable_prior_seals_verified': old,
        'public_actual_four_File_cases': {'run': 39, 'passed': 39, 'failed': 0},
        'API_compile_controls': {'positive': 1, 'negative': 14, 'expected_attributed_dispositions': 15},
        'private_guard_cases': {'per_mode': 7, 'modes': ['default', 'optimized'], 'observations': 14, 'passed': 6, 'failed': 8, 'public_reachability_inference': False},
        'private_binary_process_executions': 2,
        'confirmed_findings': ['F01-Q10-inactive-mask-read', 'F02-Q9-pending-feasibility'],
        'P01_through_P35_dispositions': 'source-proof-review.json',
        'accounting_and_lifetime_accepted': False,
        'unresolved': ['P23 exact per-group source work and complete transfers', 'P24 setup/error/finalizer/guard work', 'P25 exact comparison unit map', 'P28 complete lexical source/received/Option/helper/Result owners', 'P29 fixed role union', 'P30 private helper layouts'],
        'not_run_no_credit': ['public words/transitions/sequences bulk matrices', 'remaining complete terminal matrix', 'private numeric/row/victim/IO/budget/fault/layout controls', 'independent old86-member runtime regression suites', 'three impossible paid00/01/10 variants runtime passes'],
        'bounded_followups': 'After a separately admitted corrected freeze, root may admit<=64 public cases/batch through a separately frozen lossless deduplicated evidence transport; private seams require separate exact admission.',
        'product_sources_unchanged': True, 'producer_harness_models_tests_imported_or_executed': False,
        'evolving_correction_accessed': False, 'root_metadata_or_git_CI_changed': False,
        'native_UI_capture_simulator_emulator_phone_started': False,
        'public_owned_product_cleanup': 'public-owned-product-cleanup.json',
        'private_owned_product_cleanup': 'private-guard-run-1/cleanup.json',
        'all_returned_owned_binary_products_removed': True,
        'implementation_accepted': False, 'GA_qualified': False}
    h.write_json(HERE / 'review-receipt.json', receipt)
    # No included file is changed after the member scan. Only the seal itself is excluded.
    paths = sorted(p for p in HERE.rglob('*') if p.is_file() and p != seal_path)
    paths.append(ROOT / 'docs/swift-cache-state-implementation-review.md')
    members = []
    for p in paths:
        assert not p.is_symlink()
        raw = p.read_bytes()
        members.append({'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': h.sha(raw)})
    seal = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'scope': 'Initial independent review of original frozen candidate; rejected for Q9/Q10; accounting/matrix gates remain pending',
            'command': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str(Path(__file__).relative_to(ROOT))],
            'python': sys.version, 'script_sha256': h.sha(Path(__file__).read_bytes()),
            'members': members, 'member_count': len(members), 'member_bytes': sum(m['bytes'] for m in members),
            'implementation_accepted': False, 'GA_qualified': False}
    h.write_json(seal_path, seal)
    print(json.dumps({'seal': str(seal_path.relative_to(ROOT)), 'sha256': h.sha(seal_path.read_bytes()), 'members': seal['member_count'], 'bytes': seal['member_bytes']}))


if __name__ == '__main__':
    main()
