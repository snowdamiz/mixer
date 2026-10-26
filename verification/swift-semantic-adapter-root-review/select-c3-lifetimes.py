#!/usr/bin/env python3
"""Bind the reviewed immutable source inventory and correction addendum."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


packets = []
for name, digest, count, size in [
    ('swift-cache-state-c3-lifetime-accounting', '703bf7ca338dac74574c60a7ac42addcd4d1bc44645d559dd05ca0c4dad56c22', 36, 483656),
    ('swift-cache-state-c3-lifetime-independent', '233d419d128e0806beaafeacdfc567f9ad02098acc2a804f3ce77d55e1c3aa92', 25, 114751),
]:
    path = ROOT / 'verification' / name / 'seal.json'
    demand(sha(path) == digest, 'Seal identity')
    seal = read(path)
    demand(len(seal['members']) == count and sum(r['bytes'] for r in seal['members']) == size, 'Seal totals')
    for row in seal['members']:
        member = ROOT / row['path']
        demand(member.stat().st_size == row['bytes'] and sha(member) == row['sha256'], 'Member identity: ' + str(member))
    packets.append({'path': str(path.relative_to(ROOT)), 'sha256': digest, 'members': count, 'bytes': size})

independent = ROOT / 'verification/swift-cache-state-c3-lifetime-independent'
addendum = read(independent / 'coverage-addendum.json')
demand(len(addendum['schedules']) == 18, 'Complete supplement')
maxima = {'Control': 1201, 'Wire': 152, 'Setup': 160, 'Report': 2688}
allowances = {'Control': 1280, 'Wire': 256, 'Setup': 256, 'Report': 2896}
for row in addendum['schedules']:
    demand(sum(row['Control_groups'].values()) == row['Control'], 'Control subtotal')
    for role in maxima:
        demand(row[role] <= maxima[role] <= allowances[role], 'Role allowance')
demand(5 * (488 - 232) + 5 * 256 + 4 * 32 == 2688, 'Full Result accounting')
demand(24656 + sum(allowances.values()) == 29344 < 41984 < 65536, 'Role union')
source = ROOT / 'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs'
demand(sha(source) == addendum['source_sha256'], 'Exact source')
latest = read(independent / 'latest-run.json')
command_directory = independent / latest['directory']
demand(sha(command_directory / 'receipt.json') == latest['receipt_sha256'], 'Latest command binding')
outputs = {}
for mode in ['normal', 'optimized']:
    output = read(command_directory / (mode + '.stdout'))
    outputs[mode] = output

document = ROOT / 'docs/swift-cache-state-c3-lifetime-selection.md'
result = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'argv': sys.argv, 'python': sys.version, 'selector_sha256': sha(Path(__file__)),
          'packets': packets, 'source_sha256': sha(source),
          'document': {'path': str(document.relative_to(ROOT)), 'sha256': sha(document)},
          'coverage_addendum_sha256': sha(independent / 'coverage-addendum.json'),
          'selected_corrections': {'semantic_reply_Control': 584, 'projection_return_Control': 275,
                                   'independent_supplementary_schedules': 18},
          'added_peaks': maxima, 'added_allowances': allowances, 'inherited_role_union': 24656,
          'whole_role_union': 29344, 'reserved_bytes': 41984, 'ceiling': 65536,
          'retained_independent_outputs': outputs,
          'whole_role_union_accepted': True,
          'scope': 'Exact C3 authored source-level logical lifetime inventory with inherited accepted predecessor proof',
          'original_producer_exact_phase_completeness_accepted': False,
          'machine_stack_or_libstd_bound_accepted': False, 'predecessor_proof_replayed_in_full': False,
          'combined_all_work_groups_accepted': False, 'implementation_accepted': False,
          'sorting_amendment_selected': False, 'numeric_caps_changed': False,
          'product_compiler_runtime_native_or_capture_executed': False, 'GA_qualified': False}
target = HERE / 'C3-lifetime-selection.json'
demand(not target.exists(), 'Selection is immutable; do not overwrite')
target.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'receipt': str(target.relative_to(ROOT)), 'sha256': sha(target), 'members_verified': 61,
                  'whole_role_union_accepted': True, 'whole_role_union': 29344}))
