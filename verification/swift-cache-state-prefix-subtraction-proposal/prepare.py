#!/usr/bin/env python3
"""Assemble one isolated source edit and freeze its exact read-only inputs."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'verification/swift-cache-state-row-probe-proposal/source/cache_state.rs.txt'
BASE_SHA = 'a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1'
OLD = '''                    let Some(next) = remaining.checked_sub(bytes) else {
                        return reject(13);
                    };
                    remaining = next;
'''
NEW = '''                    remaining -= bytes;
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


base = BASE.read_bytes()
if sha(base) != BASE_SHA or base.count(OLD.encode()) != 1:
    raise ValueError('exact predecessor source or one-edit site differs')
start = base.index(OLD.encode())
proposed = base[:start] + NEW.encode() + base[start + len(OLD.encode()):]
(HERE / 'source').mkdir(exist_ok=True)
(HERE / 'source/cache_state.rs.txt').write_bytes(proposed)
(HERE / 'proposed.diff').write_text(''.join(difflib.unified_diff(
    base.decode().splitlines(True), proposed.decode().splitlines(True),
    fromfile='FROZEN_ROW_PROBE/cache_state.rs',
    tofile='UNSELECTED_PREFIX_SUBTRACTION/cache_state.rs')))
write('source-assembly.json', {
    'schema': 1, 'predecessor_path': str(BASE.relative_to(ROOT)),
    'predecessor_sha256': BASE_SHA, 'proposed_sha256': sha(proposed),
    'edit_start_byte': start, 'edit_start_line': base[:start].count(b'\n') + 1,
    'old_bytes': len(OLD.encode()), 'new_bytes': len(NEW.encode()),
    'old_site_sha256': sha(OLD.encode()), 'new_site_sha256': sha(NEW.encode()),
    'unchanged_prefix_sha256': sha(base[:start]),
    'unchanged_suffix_sha256': sha(base[start + len(OLD.encode()):]),
    'all_other_source_bytes_identical': True,
    'canonical_product_source_changed': False, 'implementation_selected': False,
})
paths = [
    'AGENTS.md', 'PLAN.md', 'mixer-product-plan.md',
    str(BASE.relative_to(ROOT)),
    'verification/swift-cache-state-row-probe-remaining-accounting/next-design-direction.json',
    'verification/swift-cache-state-row-probe-remaining-accounting/seal.json',
    'verification/swift-semantic-adapter-root-review/row-probe-G2-selection.json',
    'verification/swift-semantic-adapter-root-review/row-probe-G5-rejection.json',
    'verification/swift-semantic-adapter-root-review/row-probe-G5-G6-ownership.json',
    'verification/swift-semantic-adapter-root-review/C3-remaining-work-selection.json',
    'verification/swift-cache-state-row-probe-independent/correction-addendum.json',
    'verification/swift-cache-state-row-probe-proposal/components.json',
    'verification/swift-cache-state-seeded-first-pass-proposal/subtrace-summary.json',
    'verification/swift-cache-state-seeded-first-pass-proposal/component-templates.json',
]
files = []
for name in paths:
    data = (ROOT / name).read_bytes()
    item = {'path': name, 'bytes': len(data), 'sha256': sha(data)}
    if name in ('AGENTS.md', 'PLAN.md', 'mixer-product-plan.md'):
        # Root maintains these live files after handoff. Preserve the exact
        # authority snapshot read for this packet without requiring stale live
        # planning bytes on a later offline replay.
        snapshot = HERE / 'inputs' / name
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_bytes(data)
        item['frozen_packet_path'] = str(snapshot.relative_to(HERE))
    files.append(item)
write('input-bindings.json', {
    'schema': 1, 'files': files,
    'input_tree_digest': sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()),
    'input_code_imported_or_executed': False,
})
write('limits.json', {
    'schema': 1, 'work': {'G2': 2560, 'G3': 2568, 'G4': 768, 'G5': 640, 'G6': 640},
    'role_additions': {'Control': 1280, 'Wire': 256, 'Setup': 256, 'Report': 2896},
    'inherited_bytes': 24656, 'reserved_bytes': 41984, 'global_bytes': 65536,
    'scalar_group_max': 16, 'copy_group_max_bytes': 128,
    'candidate_bytes': 2048, 'cross_group_credit': False,
    'compiler_native_UI_capture_process_inventory': False,
    'old_G6_or_whole_lifetime_automatically_inherited': False,
})
print(json.dumps({'source_sha256': sha(proposed), 'input_files': len(files)}, sort_keys=True))
