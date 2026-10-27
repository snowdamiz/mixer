"""Seal the bounded independent review; do not mutate any candidate or Git state."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
CANDIDATE = ROOT / 'verification/swift-guarded-snapshot-composition-source-preparation'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def identity(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(OUT)), 'bytes': len(data), 'sha256': sha(data)}


def main():
    assert sha((CANDIDATE / 'seal.json').read_bytes()) == 'bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751'
    candidate = json.loads((CANDIDATE / 'seal.json').read_text())
    for row in candidate['members']:
        data = (CANDIDATE / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    preaccess = ROOT / 'verification/swift-guarded-snapshot-composition-independent/preaccess/seal.json'
    assert sha(preaccess.read_bytes()) == '04102cfec8595314e80169eb8195e46cf4a50f99ca9c0e0eb332ce8bc7005f44'
    commands = []
    for path in sorted((OUT / 'commands').glob('*/receipt.json')):
        row = json.loads(path.read_text())
        assert row['passed'] and row['direct_child_reaped'] and not row['timed_out'], path
        commands.append({'receipt': identity(path), 'source_tree_sha256': row['source_tree_sha256'],
                         'exit_code': row['exit_code'], 'elapsed_seconds': row['elapsed_seconds'],
                         'direct_child_reaped': row['direct_child_reaped']})
    assert len(commands) == 19
    assert not (OUT / 'owned-work').exists()
    assert not list(OUT.rglob('*.rmeta')) and not list(OUT.rglob('*.ll'))
    checks = json.loads((OUT / 'source-checks.json').read_text())
    assert len(checks['checks']) == 18 and all(row['passed'] for row in checks['checks'])
    layouts = {}
    for path in sorted((OUT / 'commands').glob('independent-layout-*/layouts.json')):
        layouts[path.parent.name] = json.loads(path.read_text())
    assert len(layouts) == 4
    save('independent-layouts.json', {'schema': 1, 'profiles': layouts, 'types_per_profile': 22,
        'storage_floor_selected': False, 'scope': 'fresh actual source type identities; no occurrence sum or operational grant'})
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, timeout=15, check=True)
    save('cleanup.json', {'schema': 1, 'compiler_commands': len(commands),
        'maximum_compiler_elapsed_seconds': max(row['elapsed_seconds'] for row in commands),
        'owned_compiler_timeout_seconds': 55, 'timed_out': 0,
        'all_direct_compiler_children_reaped': True, 'owned_scratch_removed': True,
        'compiler_binary_or_full_LLVM_artifacts_retained': False,
        'retained': 'exact source preimages/edits, raw diagnostics, selected LLVM layout lines and output hashes',
        'descendant_absence_inventory': 'not performed; process inventories remain paused',
        'paused_surfaces_used': False, 'unrelated_processes_or_data_touched': False})
    save('review.json', {
        'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'bounded-source-review-complete-raw-parts-boundary-correction-required-accounting-unselected',
        'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve())], 'python': sys.version,
        'context_revision_command': ['git', 'rev-parse', 'HEAD'], 'context_revision': revision.stdout.decode().strip(),
        'authoritative_candidate_seal_sha256': 'bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751',
        'authoritative_144_source_tree_sha256': '140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395',
        'candidate_members_reverified': len(candidate['members']), 'candidate_bytes_reverified': sum(row['bytes'] for row in candidate['members']),
        'preaccess_unchanged': True,
        'fresh_evidence': {'compiler_commands': 19, 'actual_type_layout_profiles': 4, 'actual_type_identities_per_profile': 22,
                           'exact_default_production_debug_measurement_absence': 1,
                           'positive_actual_lifetime_compiles': 2, 'negative_actual_privacy_lifetime_compiles': 10,
                           'undesired_raw_parts_bypass_compiles': 2, 'bypass_call_sites_per_compile': 2,
                           'static_differential_and_shape_checks': 18, 'unexpected_compiler_failures': 0},
        'concrete_finding': {'id': 'C1', 'severity': 'blocks next operational source candidate',
            'summary': 'Both selected constructor boundaries accept ordinary raw owner parts without owning-scope authority',
            'outer_source': 'src/experimental_swift_reactor/cache.rs:4868',
            'inner_source': 'src/experimental_swift_reactor/cache/initial_profile_v1.rs:541',
            'evidence': identity(OUT / 'bypass-evidence.json'),
            'correction': 'Both boundaries consume the same control-minted opaque capability containing actual cache/control/WASI/adopted ownership; scope is sole mint; no detached permit or raw selected route',
            'runtime_limit': 'No writer executed; MissingSelectedProvenance still protects bytes and WorkAuditPending blocks this exact writer'},
        'proven_source_contracts': [
            'Original ABI associated output cannot receive a Selected result; original eight inline outcomes, guard type, header/rows, RuntimeControl fields and original finish helpers unchanged',
            'Actual access shared reborrow protects live encoder view through consuming completion; actual outer borrow protects consuming Run finalization',
            'Full refused None inline Option extent measured; no new plan or transfer value initialized on refusal',
            'Primary/export/phase and actual attachment/cache/WASI cleanup returns retained; finalizer WASI pairing .is_ok diagnostic disposition separately identified',
            'Descriptor alias/empty/position checks and bounded 32-attempt writes with pre/post-stop evidence are present in source',
            'Default production Debug LLVM excludes all ten measured preparation names checked; source layout additions are separate exact variants',
        ],
        'specific_next_accounting': 'accounting-and-funding.md contains measured normalized errors, begin/guard/retirement tuples, refused full-storage return/argument/drop roles, common adapter delta, attachment and retained-finalizer rows plus minimal funding design',
        'encoder_boundary': 'Separate encoder-local callee inventory remains an independently released dependency; caller call-result/move/owner roles are explicitly disjoint',
        'not_selected': ['complete storage floor', 'Original common adapter funding formula', 'healthy selected finalizer lifetime cutset',
                         'complete caller/control/capability work formula', 'bounded-call stop amendment', 'new genuine writer execution'],
        'limits': ['compiler/source review only; no native/device/simulator/emulator/UI/capture/process inventories',
                   'no new writer/VM runtime behavior or actual alias/fault/all-eight cleanup evidence',
                   'writer reports acknowledged File writes; no flush/sync/close/durable publication implemented',
                   'root scope-authority correction and other active work/review lanes were not read',
                   'no canonical source, Git state, product budget, publication, FieldLog, OTA/store/customer or GA change'],
        'commands': commands,
        'complete_floor_accepted': False, 'operational_admission_accepted': False, 'canonical_product_changed': False,
        'GA_gates_verified': 0,
    })
    members = [identity(path) for path in sorted(OUT.rglob('*')) if path.is_file() and path.name != 'seal.json']
    stream = ''.join(f"{row['path']}\0{row['bytes']}\0{row['sha256']}\n" for row in members).encode()
    save('seal.json', {'schema': 1, 'member_count': len(members), 'bytes': sum(row['bytes'] for row in members),
        'members': members, 'tree_sha256': sha(stream), 'tree_digest_format': 'path NUL decimal-bytes NUL sha256 newline in sorted path order',
        'scope': 'independent bounded source/ownership/layout review with concrete raw-parts defect; no storage/work floor or writer admission'})
    print(json.dumps(identity(OUT / 'seal.json')))


if __name__ == '__main__':
    main()
