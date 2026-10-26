#!/usr/bin/env python3
"""Select the exact independently corrected G2 proof, without product integration."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def demand(ok, message):
    if not ok:
        raise ValueError(message)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

packets = []
for name, expected, count, size in [
    ('swift-cache-state-row-probe-proposal', '8d3317005e5db2b6114a9bd2be3c40682920f20041a5b46bd22d50ae929aab7f', 29, 2106607),
    ('swift-cache-state-row-probe-independent', '4918dfa723161e9cead7087e066baf8021efe64a9a27dee67a6e8518f61c365e', 45, 1505651),
]:
    path = ROOT / 'verification' / name / 'seal.json'
    demand(digest(path) == expected, 'Seal identity')
    rows = json.loads(path.read_text())['members']
    demand(len(rows) == count and sum(r['bytes'] for r in rows) == size, 'Packet totals')
    for row in rows:
        member = ROOT / row['path']
        demand(member.stat().st_size == row['bytes'] and digest(member) == row['sha256'], row['path'])
    packets.append({'path': str(path.relative_to(ROOT)), 'sha256': expected, 'members_verified': count, 'bytes': size})

independent = ROOT / 'verification/swift-cache-state-row-probe-independent'
review = json.loads((independent / 'review.json').read_text())
source = ROOT / 'verification/swift-cache-state-row-probe-proposal/source/cache_state.rs.txt'
demand(digest(source) == review['source_sha256'] == 'a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1', 'Source identity')
upper = review['complete_G2_upper']
demand(upper == {'copies': 838, 'groups': 2494, 'scalar_groups': 1656, 'scalars': 26491}, 'Upper')
demand((upper['scalars'] + 15) // 16 + upper['copies'] == upper['groups'] <= review['G2_cap'] == 2560, 'Cap')
latest = independent / json.loads((independent / 'latest-run.json').read_text())['path']
commands = json.loads((latest / 'receipt.json').read_text())['commands']
for row in commands:
    demand(row['exit'] == 0, 'Independent command failed')
    for stream in ['stdout', 'stderr']:
        demand(digest(latest / (row['label'] + '.' + stream)) == row[stream + '_sha256'], 'Output custody')
receipt = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'argv': sys.argv, 'python': sys.version, 'selector_sha256': digest(Path(__file__)),
    'packets': packets, 'source_sha256': digest(source),
    'decision': 'Accept exact corrected G2 source-work upper and scoped added logical lifetimes for remaining proof work only',
    'complete_G2_upper': upper, 'G2_cap': 2560, 'valid_witness': review['valid_G2_witness'],
    'scoped_added_peaks': {'Control': 1220, 'Wire': 24, 'Setup': 80},
    'allowances': {'Control': 1280, 'Wire': 256, 'Setup': 256},
    'correction_addendum_sha256': digest(independent / 'correction-addendum.json'),
    'ownership_handoff_sha256': digest(independent / 'ownership-boundaries.json'),
    'retained_independent_command_receipt': str((latest / 'receipt.json').relative_to(ROOT)),
    'retained_independent_outputs': {mode: json.loads((latest / (mode + '.stdout')).read_text()) for mode in ['normal', 'optimized']},
    'original_2332_2230_1140_totals_accepted': False,
    'finite_2443_543_merge_subtraces_are_uppers': False,
    'G3_G4_G5_or_whole_new_lifetime_accepted': False,
    'G2_unused_groups_transferable': False,
    'numeric_caps_changed': False, 'canonical_source_changed': False,
    'implementation_or_native_or_GA_qualified': False,
    'source_API_abstraction_only': True,
    'scope': 'Exact G2 eight accumulators plus scan/post block; no whole source, machine stack, library internals, new sorting or public integration authority',
    'next': 'Complete G3/G4/G5 and changed-source lifetime proof under original caps; independent review before implementation selection',
}
target = HERE / 'row-probe-G2-selection.json'
demand(not target.exists(), 'Immutable selection already exists')
target.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'path': str(target.relative_to(ROOT)), 'sha256': digest(target), 'members_verified': 74, 'G2_upper': 2494}))
