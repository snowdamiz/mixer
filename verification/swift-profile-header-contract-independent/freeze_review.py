#!/usr/bin/env python3
"""Seal this independent offline review; never mutate producer or product files."""
from pathlib import Path
import datetime
import hashlib
import json
import audit_inputs

P = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def check_row(base, row, name='path'):
    raw = (base / row[name]).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row[name]


def main():
    assert not (P / 'seal.json').exists(), 'sealed evidence is immutable'
    custody = audit_inputs.audit()
    for row in json.loads((P / 'input-custody.json').read_bytes())['inputs']:
        if 'snapshot' in row:
            check_row(P, row, 'snapshot')
        else:
            check_row(P.parents[1], row)
    witnesses = json.loads((P / 'source-witnesses.json').read_bytes())['witnesses']
    for row in witnesses:
        raw = (audit_inputs.PREP / row['producer_relative_path']).read_bytes()
        assert len(raw) == row['full_source_bytes'] and sha(raw) == row['full_source_sha256']
        assert row['excerpt'].encode() in raw
        assert sha(row['excerpt'].encode()) == row['excerpt_sha256']
    roster = json.loads((P / 'test-roster.json').read_bytes())
    runs = sorted((P / 'commands').iterdir())
    assert runs
    for run in runs:
        receipt = json.loads((run / 'receipt.json').read_bytes())
        for row in receipt['authored_script_bindings']:
            check_row(run / 'scripts', row)
        assert all(r['exit_code'] == 0 for r in receipt['commands'])
        for result in receipt['commands']:
            for stream in ['stdout', 'stderr']:
                raw = (run / f"{result['name']}.{stream}").read_bytes()
                assert len(raw) == result[stream]['bytes'] and sha(raw) == result[stream]['sha256']
        stderr = (run / 'controls.stderr').read_text()
        for name in roster['methods']:
            assert stderr.count(name + ' (') == 1, (str(run), name)
        assert f"Ran {roster['method_count']} tests" in stderr and stderr.endswith('OK\n')
        audit = json.loads((run / 'custody.stdout').read_bytes())
        assert audit['producer_member_count'] == 200 and audit['producer_total_bytes'] == 23038631
    latest = json.loads((runs[-1] / 'receipt.json').read_bytes())
    decision = {
        'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'decision': 'Independent contract review complete; five explicit root amendments required before dependent implementation',
        'scope': 'Offline frozen source/design review and synthetic positive/negative controls only',
        'producer_seal_sha256': audit_inputs.EXPECTED['verification/swift-profile-header-preparation/seal.json'],
        'producer_members_verified_unchanged': 200,
        'producer_bytes_verified_unchanged': 23038631,
        'producer_tree_sha256': custody['producer_tree_sha256'],
        'nested_snapshots_verified': custody['nested_snapshots_verified'],
        'archive_and_current_members_each': 132,
        'row_source_members_reconstructed': 131,
        'source_revision_context': latest['source_revision_context'],
        'source_revision_tree_context': latest['source_revision_tree_context'],
        'source_revision_scope': 'Context only; assigned seal and exact input member hashes authoritative',
        'independent_methods_per_run': roster['method_count'],
        'retained_successful_offline_runs': len(runs),
        'final_run': str(runs[-1].relative_to(P)),
        'source_witnesses': len(witnesses),
        'synthetic_counterexamples': len(json.loads((P / 'counterexamples.json').read_bytes())['cases']),
        'required_amendments': ['R1 local structure vs external build attestation',
                                'R2 common-control optional WASI vs historical instance identity',
                                'R3 source construction continuation before any acquisition attempt',
                                'R4 B equality vs unrelated zero-byte Cache ticket exclusivity',
                                'R5 private guard-derived same-cache-proof row bridge'],
        'concrete_continuation_shape': 'continuation-shape.md',
        'selected_complete17_field_budget': None,
        'actual_layout_sizes_or_alignments_selected': False,
        'provisional_row_complete_accounting_adopted': False,
        'row_root_acceptance_scope_preserved': 'Rust1.99 macOS host copied component only;11912/13904 logical places and450652288 source actions plus requested IO bytes, not VM credits or combined allowance',
        'product_implementation_or_root_contract_selection': False,
        'Rust_compiler_or_VM_executions': 0,
        'native_simulator_emulator_device_UI_capture_or_process_inventory': 0,
        'hosted_or_active_Android_correction_or_integration_protocol_access': False,
        'Git_mutations_or_canonical_or_other_lane_writes': 0,
        'cap_deadline_crypto_or_dependency_changes': False,
        'real_header_binding_digest_custody_semantics_runtime_new_CI_or_GA_accepted': False,
        'pending_native_and_physical_checks': 'Not run; explicit native/UI/capture pause preserved',
        'cleanup': 'Bounded Python review subprocesses completed/reaped; no compiler/VM/native instance, scratch, UI/capture/process inventory created. Retained packet is evidence. Other projects untouched.',
        'exploratory_observation': 'Initial plain lexical tree assertion failed because producer sorts Path component tuples; every member and assigned seal hash match. Both tree definitions recorded; producer unchanged.',
        'review_agent_requested': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh',
                                   'fresh_context': True, 'runtime_self_attestation': False},
    }
    (P / 'decision.json').write_text(json.dumps(decision, indent=2, sort_keys=True) + '\n')
    rows = []
    for file in sorted((p for p in P.rglob('*') if p.is_file()), key=lambda p: str(p.relative_to(P))):
        if file.name in ['seal.json', 'seal.sha256']:
            continue
        assert not file.is_symlink()
        raw = file.read_bytes()
        rows.append({'path': str(file.relative_to(P)), 'bytes': len(raw), 'sha256': sha(raw)})
    tree = audit_inputs.rows_digest(rows)
    seal = {'schema': 1, 'scope': decision['scope'],
            'excluded': ['seal.json', 'seal.sha256'], 'member_count': len(rows),
            'total_bytes': sum(r['bytes'] for r in rows),
            'tree_definition': 'SHA256(sorted relative POSIX path STRING lexical order; UTF8 path TAB decimal bytes TAB lowercase sha256 LF)',
            'tree_sha256': tree, 'members': rows,
            'implementation_or_real_binding_runtime_or_GA_accepted': False}
    raw = (json.dumps(seal, indent=2, sort_keys=True) + '\n').encode()
    (P / 'seal.json').write_bytes(raw)
    (P / 'seal.sha256').write_text(sha(raw) + '  seal.json\n')
    print(json.dumps({'member_count': len(rows), 'total_bytes': seal['total_bytes'],
                      'tree_sha256': tree, 'seal_sha256': sha(raw),
                      'decision_sha256': sha((P / 'decision.json').read_bytes()),
                      'offline_methods': roster['method_count'], 'required_root_amendments': 5,
                      'producer_200_unchanged': True}, sort_keys=True))


if __name__ == '__main__':
    main()
