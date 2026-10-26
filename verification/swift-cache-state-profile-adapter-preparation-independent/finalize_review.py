#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys

HERE = Path(__file__).absolute().parent
ROOT = HERE.parent.parent
SOURCE = ROOT / 'verification/swift-cache-state-next-integration-preparation'
AMENDMENT = ROOT / 'verification/swift-semantic-adapter-root-review/profile-adapter-protocol-amendment.md'
AMENDMENT_SHA = 'ae64f81fc4051bf59e31fb4552a25b9d533256e5bb429ee90b547af9058764fd'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory(base):
    result = []
    for path in sorted(base.rglob('*')):
        mode = path.lstat().st_mode
        assert stat.S_ISDIR(mode) or stat.S_ISREG(mode)
        if stat.S_ISREG(mode):
            result.append({'path': path.relative_to(base).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)})
    return result

def main():
    assert sha(AMENDMENT) == AMENDMENT_SHA
    shutil.copy2(AMENDMENT, HERE / 'root-protocol-amendment.md')
    source_seal = json.loads((SOURCE / 'seal.json').read_bytes())
    assert sha(SOURCE / 'seal.json') == '02f16c13fcea823444a5b775b45e778209f877259fd7222fbfbc7936c19ac412'
    assert [r for r in inventory(SOURCE) if r['path'] not in source_seal['excluded']] == source_seal['members']
    audit = json.loads((HERE / 'offline-audit.json').read_bytes())
    for row in audit['additional_validator_core']:
        assert sha(ROOT / row['path']) == row['sha256'] == sha(HERE / row['snapshot'])
    original_findings = [
        {'id': 'R1', 'file': 'proposed-contract.md', 'lines': [44, 68, 85, 109],
         'issue': 'Original proposal left block/file attempt limits and exact fixed error/stage/offset accounting open',
         'resolved_by': AMENDMENT_SHA,
         'closure': '4096-byte128-row blocks;625blocks;32calls/block;20000calls/file; exactcode1..13/stage1..5 and acknowledgement/error precedence'},
        {'id': 'R2', 'file': 'test-plan.md', 'lines': [12, 25, 27, 39],
         'issue': 'rows_ Cargo filter alone could omit writer/File/layout cases or grant zero-match success without a selected roster',
         'resolved_by': AMENDMENT_SHA,
         'closure': 'Frozen complete compiler-listed selected namespace and bridge invocation rosters in both modes; exact total/passed/ignored/filtered counts'}]
    decision = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'builder_sha256': sha(Path(__file__)),
        'decision': 'Preparation plus exact frozen protocol amendment is ready for root selection of isolated actual-source row/body candidate',
        'contract_ready_for_root_selection': True, 'implementation_selected_by_this_review': False,
        'implementation_or_product_gate_accepted': False,
        'preparation_seal_sha256': sha(SOURCE / 'seal.json'), 'preparation_members_verified': 67,
        'preparation_bytes_verified': 1660679, 'protocol_amendment_sha256': AMENDMENT_SHA,
        'offline_audit_sha256': sha(HERE / 'offline-audit.json'),
        'source_revision_of_preparation': audit['prepared_source_revision'],
        'source_tree_of_preparation': audit['prepared_source_tree'],
        'additional_validator_core': audit['additional_validator_core'],
        'disclosed_cache_control_source_differences': audit['known_cache_control_differences'],
        'smallest_next_dependency': 'Private real ValidatedSwiftReactor execution_function ->32-byte little-endian rows -> bounded safe-File row body',
        'no_new_parser_or_owner_constructor_or_public_API': True,
        'original_findings': original_findings, 'remaining_preselection_blockers': [],
        'fixed_protocol': {'rows': 80000, 'row_bytes': 32, 'body_bytes': 2560000,
            'block_bytes': 4096, 'rows_per_block': 128, 'blocks': 625, 'calls_per_block': 32,
            'maximum_write_calls_per_file': 20000, 'error_codes': list(range(1,14)), 'stages': list(range(1,6)),
            'write_coordinates': 'All actual write calls counted; only valid acknowledged bytes advance output_bytes',
            '32nd_complete': 'success', '32nd_incomplete_or_Interrupted': 'exhaustion without33rd call',
            '32nd_error_zero_overreport': 'specific code retained',
            'File_scope': 'Regular initial0/empty File borrow; quiescent output/open-description offset; success acknowledged writes only'},
        'required_before_candidate_compilation': ['Freeze exact full actual VM source closure and supported compiler/host; no mixed old/current runtime acceptance',
            'Freeze complete required selected namespace and bridge invocation rosters for both modes'],
        'required_before_implementation_acceptance': ['Actual complete validation of independently encoded fixed34-import Wasm; no forged metadata/proof',
            'Actual Debug/optimized row/File/writer/error/layout/API tests and independent expected wire/offset/File bytes',
            'Zero-allocation row helper and no whole-body/vector allocation',
            'Complete owner/argument/Result/caller layout and simultaneous lifetime proof',
            'Complete exact-source loop/instruction/serialization/I/O/error accounting under unchanged reservations/debit caps',
            'Independent rerun and new field/offset/import/tail/fault negatives'],
        'deferred_dependencies': ['Actual real profile header/cache construction/layout and all eight digests',
            'Original typed result, exact failure applicability, optional cursor and all15 final ledger/cleanup joins',
            'Separately named real context/replay/semantic metrics/report path',
            'Standard-library same-descriptor hashing/path custody and private exactly-once CLI adoption',
            'Inherited serializer/CODE-buffer writer accounting and separately selected full-target diagnosis'],
        'fixture_bridge': 'Real small-module row provenance, synthetic configuration/binding; all authority getters remain false',
        'Failure14_applicability_enabled': False, 'CAP_tail_known': False,
        'old_closed_fixture_CI': 'Root reports Rust1.98.1 job40373807988 success; artifact audit separately active; not independently reviewed here and no new-source qualification inferred',
        'product_compiler_or_model_or_VM_or_File_driver_or103pack_executed': False,
        'native_UI_capture_process_inventory_Git_or_canonical_edits': False,
        'owned_changes_only': str(HERE), 'source_and_preparation_unchanged': True,
        'target_native_FieldLog_signing_store_customer_operations_GA_qualified': False,
        'retained_authoring_failure': 'authoring-failures.json'}
    (HERE / 'decision.json').write_text(json.dumps(decision, sort_keys=True, indent=2) + '\n')
    rows = [r for r in inventory(HERE) if r['path'] != 'seal.json']
    seal = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'builder_sha256': sha(Path(__file__)), 'excluded': ['seal.json'],
        'member_base': 'packet-relative', 'members': rows, 'member_count': len(rows),
        'total_bytes': sum(r['bytes'] for r in rows),
        'tree_sha256': hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'decision_sha256': sha(HERE / 'decision.json'), 'contract_ready_for_root_selection': True,
        'implementation_selected_or_accepted': False, 'native_or_GA_accepted': False}
    (HERE / 'seal.json').write_text(json.dumps(seal, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'seal_sha256': sha(HERE / 'seal.json'), 'members': len(rows), 'bytes': seal['total_bytes'],
        'decision_sha256': seal['decision_sha256'], 'contract_ready_for_root_selection': True}))

if __name__ == '__main__':
    main()
