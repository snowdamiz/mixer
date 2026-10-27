#!/usr/bin/env python3
"""Freeze this lane only after completed offline review; no compiler/runtime."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
assert not (HERE / 'seal.json').exists(), 'review-already-frozen'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def ref(p):
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': sha(b)}


def write(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2) + '\n')


at = datetime.datetime.now(datetime.timezone.utc).isoformat()
target = ROOT / 'verification/swift-root-bound-work-storage-delta/seal.json'
assert ref(target)['sha256'] == '1b077039023f424fb72f9e32902f329e3257edb50a4ab99aa42192149271cb29'
receipts = [json.loads(p.read_text()) for p in sorted((HERE / 'commands').glob('*/receipt.json'))]
producer = [r for r in receipts if r['script']['path'].endswith('/swift-root-bound-work-storage-delta/check.py')]
assert len(producer) == 1 and producer[0]['exit_code'] == 0
assert all(not r['timed_out'] and r['wall_bound_seconds'] == 50 for r in receipts)
inventory = json.loads((HERE / 'independent-check-result.json').read_text())
layout = json.loads((HERE / 'layout-review.json').read_text())
assert inventory['status'] == 'PASS_INDEPENDENT_FINITE_CUSTODY_AND_COVERAGE'
assert layout['status'] == 'ACCEPTED_SOURCE_ONLY_CONDITIONAL_NEXT_LAYOUT_PROPOSAL'
assert not list(HERE.rglob('__pycache__'))
assert not any(p.suffix in ['.rmeta', '.rlib', '.o', '.dylib', '.so', '.pyc'] for p in HERE.rglob('*'))
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
write('command-summary.json', {
    'schema': 1, 'receipts': receipts, 'producer_checker_runs': 1,
    'independent_inventory_successes': 1,
    'independent_inventory_development_failures': len([r for r in receipts if r['exit_code'] != 0]),
    'development_disposition': 'All six reviewer harness errors were inspected and corrected; complete stderr preserved and causes documented in REVIEW.md. One additional targeted schema-introspection command failed with KeyError line_end, then was corrected. No compiler/runtime retries or producer checker repeats.',
    'pre_oracle_reads': ['AGENTS.md', 'mixer-product-plan.md relevant scope', 'root lifetime acceptance', 'accepted isolated source-origin, source-manifest, source-delta, relevant exact source bodies and complete MIR hash', 'git rev-parse HEAD'],
    'ancillary_read_commands': 'cat, rg --files/rg -n, sed -n and bounded python3 -B source/MIR introspection; no compiler/version query, network, native/runtime, UI/capture or process inventory',
})
write('cleanup.json', {
    'schema': 1, 'at': at, 'compiler_children_started': 0, 'native_runtime_children_started': 0,
    'UI_capture_or_browser_operations': 0, 'phone_operations': 0,
    'network_requests': 0, 'global_process_inventories': 0,
    'hosted_or_stopped_Android_harness_operations': 0,
    'source_or_MIR_authoritative_packets_modified': 0,
    'diagnostic_scratch_sources_written': 0, 'generated_binaries_or_metadata': 0,
    'python_bytecode_disabled': sys.dont_write_bytecode,
    'owned_native_instances_started': 0, 'owned_native_instance_cleanup_required': False,
    'retained_selected_MIR': 'Offline review evidence only; candidate53 and baseline23 complete relevant bodies, not full archive copies.',
    'other_projects_or_protected_hosted_files': 'No modifications or process actions by this lane.',
})
write('result.json', {
    'schema': 1, 'at': at, 'status': 'accepted-finite-source-MIR-accounting-inventory-and-conditional-layout-proposal-only',
    'concrete_producer_defects': [], 'target_seal': ref(target),
    'pre_producer_oracle': ref(HERE / 'pre-producer-oracle.json'),
    'independent_check': ref(HERE / 'independent-check-result.json'),
    'layout_review': ref(HERE / 'layout-review.json'),
    'review': ref(HERE / 'REVIEW.md'),
    'git_revision_for_review_tools_only': revision,
    'source_tree': inventory['source_trees_fully_read'],
    'producer_check_runs': 1, 'producer_check_passed': True,
    'independent_inventory_controls_passed': len(inventory['independent_controls']),
    'independent_layout_proposal_and_synthetic_arithmetic_controls_passed': len(layout['controls']),
    'accepted_scope': [
        'Exact frozen packet custody and source146/MIR bindings independently verified',
        'Meaningful type/argument/local/return/capture/retirement obligations reconstructed with complete selected MIR rows and explicit unchanged-family exclusions',
        'Relocated leaf sequence occurs once in new fixed frame; extra wrappers/frames remain positive obligations',
        '28 named boundary shapes plus actual anonymous closure are a sufficient conditional next layout frontier relative to the explicit roster',
    ],
    'layout_diagnostic_strategy': 'Unexecuted and unqualified. Require a separately released root compiler lane/runner. No compiler or runtime invocation authorized by this review.',
    'unresolved': [
        'all numerical work and storage prices, including stdlib/drop/unwind dependencies',
        'actual target layouts and exact closure diagnostic behavior',
        'source/proof/File/io-error/cancellation/setup/leaf dynamic backing capacities',
        'simultaneous lifetime/peak storage and allocation composition',
        'original-root acquisition and child funding partition sufficiency',
        'durable forgotten-result/root funding, complete root shutdown and full charge lifetime',
        'useful joint retirement and full ownership',
        'native File setup/correlation/child/token/VM Ok/Err/unwind runtime',
        'production selector/startup/allocator/custody/healthy close',
        'paused UI/capture/native/phone checks and immutable external FieldLog packages',
        'OTA and GA',
    ],
    'work_prices_accepted': False, 'storage_prices_accepted': False,
    'layouts_accepted': False, 'backing_peak_funding_accepted': False,
    'full_ownership_or_durable_funding_accepted': False,
    'compiler_runtime_run': False, 'GA_accepted': False,
})
write('freeze-receipt.json', {
    'schema': 1, 'at': at, 'command': [sys.executable, '-B', str(Path(__file__).resolve())],
    'cwd': str(ROOT), 'python': sys.version, 'platform': platform.platform(),
    'tool': ref(Path(sys.executable)), 'script': ref(Path(__file__).resolve()),
    'git_revision': revision,
    'scope': 'Writes independent lane metadata/seal only. No compiler/runtime/network/process inventory.',
})
members = []
for p in sorted(HERE.rglob('*'), key=lambda p: str(p.relative_to(HERE))):
    if p.is_file() and p.name != 'seal.json':
        assert not p.is_symlink()
        b = p.read_bytes()
        members.append({'path': str(p.relative_to(HERE)), 'bytes': len(b), 'sha256': sha(b)})
seal = {
    'schema': 1, 'at': at, 'status': 'frozen-independent-offline-review-complete',
    'member_count': len(members), 'member_bytes': sum(r['bytes'] for r in members),
    'tree_hash_algorithm': 'sha256 compact sorted-key JSON of member records sorted by path string; excludes seal.json',
    'tree_sha256': sha(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()),
    'members': members,
    'producer_seal_sha256': ref(target)['sha256'],
    'prices_layouts_backing_peak_funding_full_ownership_or_GA_accepted': False,
    'compiler_runtime_invocations': 0,
}
write('seal.json', seal)
print(json.dumps({'seal': ref(HERE / 'seal.json'), 'member_count': seal['member_count'], 'member_bytes': seal['member_bytes'], 'tree_sha256': seal['tree_sha256'], 'status': seal['status']}, indent=2))
