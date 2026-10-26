"""Freeze only the mechanical transport proposal; authorize no candidate run."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from dedup_transport import HERE, ROOT, validate_pack
from harness import sha, write_json


def verify(path, digest):
    raw = path.read_bytes()
    if sha(raw) != digest:
        raise ValueError('prior seal changed')
    data = json.loads(raw)
    for m in data['members']:
        b = (ROOT / m['path']).read_bytes()
        if len(b) != m['bytes'] or sha(b) != m['sha256']:
            raise ValueError('prior member changed: ' + m['path'])
    return {'path': str(path.relative_to(ROOT)), 'sha256': digest, 'members': len(data['members'])}


def main():
    output = HERE / 'transport-seal.json'
    if output.exists():
        raise ValueError('preserve existing immutable transport proposal')
    summary = json.loads((HERE / 'controls/summary.json').read_bytes())
    if summary['failure'] is not None or summary['checks'] != 120 or len(summary['intentional_refusals']) != 14 or summary['candidate_Rust_executions'] != 0:
        raise ValueError('tooling controls not clean')
    for name in ['dedup_transport.py', 'dedup_runner.py', 'control_transport.py']:
        if sha((HERE / name).read_bytes()) != summary['source_hashes'][name]:
            raise ValueError('tooling changed after controls')
    for p in summary['packs']:
        validate_pack(HERE / p['path'])
    prior = [
        verify(HERE.parent / 'correction-control-seal.json', '13b4e77974be545bb34274ddba68b6b3b159e8d2287390dcffff864373d136c5'),
        verify(HERE.parent.parent / 'implementation-review-1/review-seal.json', '3c189178c6c8cef3fa2236bbe9d3d0c8cb2806fc4afcf9940bdc7af67a444382')]
    write_json(HERE / 'transport-receipt.json', {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'frozen-reviewer-owned-transport-proposal-awaiting-root-admission',
        'prior_explicit_seals_and_members_unchanged': prior,
        'reviewer_owned_assertions_passed': 120, 'intentional_integrity_or_gate_refusals': 14,
        'new_candidate_Rust_executions': 0, 'new_product_semantic_tests': 0,
        'lossless_64_word_sample': {'logical_input_bytes': 164470784, 'unique_input_bytes': 2642432, 'profile_objects': 1},
        'raw_reconstruction': 'All logical input bytes recoverable from role+SHA objects and per-case mapping; verbatim fixture metadata/expected words retained and materializer equivalence verified.',
        'private_full32': 'Data packing only; no execution mode, source-construction exclusions remain zero runtime credit.',
        'private_fault_layout_numeric_IO_budget_glue': 'Explicit unimplemented plan only; separate exact root freeze/admission required.',
        'limits': {'public_cases_per_batch': 64, 'per_owned_command_seconds': 60, 'stdout_stderr_bytes_each': 1048576, 'owned_groups_at_once': 1},
        'execution_authorized': False, 'source_accounting_or_lifetime_accepted': False,
        'implementation_accepted': False, 'GA_qualified': False,
        'cleanup': 'Control-only negative byte/path mutations restored exactly and revalidated; no binary products or child processes remain. Subsequent public runner would hash/remove only returned owned binaries.',
        'source_product_or_prior_sealed_files_modified': False,
        'native_UI_capture_simulator_emulator_phone_or_process_discovery': False})
    paths = sorted(p for p in HERE.rglob('*') if p.is_file() and p != output)
    members = []
    for p in paths:
        if p.is_symlink():
            raise ValueError('symlink in immutable proposal')
        b = p.read_bytes()
        members.append({'path': str(p.relative_to(ROOT)), 'bytes': len(b), 'sha256': sha(b)})
    data = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Mechanical lossless reviewer transport proposal and own data controls only; no new candidate execution authorization',
        'command': ['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str(Path(__file__).relative_to(ROOT))],
        'python': sys.version, 'python_executable_sha256': sha(Path(sys.executable).read_bytes()),
        'script_sha256': sha(Path(__file__).read_bytes()), 'members': members,
        'member_count': len(members), 'member_bytes': sum(m['bytes'] for m in members),
        'execution_authorized': False, 'implementation_accepted': False, 'GA_qualified': False}
    write_json(output, data)
    print(json.dumps({'seal': str(output.relative_to(ROOT)), 'sha256': sha(output.read_bytes()), 'members': len(members), 'bytes': data['member_bytes']}))


if __name__ == '__main__':
    main()
