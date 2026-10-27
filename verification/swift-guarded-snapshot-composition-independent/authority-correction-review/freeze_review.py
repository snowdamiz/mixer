"""Recheck frozen source deltas and seal the compact independent authority review."""
import datetime
import hashlib
import json
import pathlib
import re
import sys

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
CORRECTION = ROOT / 'verification/swift-guarded-snapshot-scope-authority-correction'
BASE = ROOT / 'verification/swift-guarded-snapshot-composition-source-preparation/source/vm'
SOURCE = CORRECTION / 'source/vm'


def sha(data): return hashlib.sha256(data).hexdigest()
def save(name, value): (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def identity(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(OUT)), 'bytes': len(data), 'sha256': sha(data)}


def block(text, name):
    begin = text.index(name); opening = text.index('{', begin); depth = 1
    for i in range(opening + 1, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}': depth -= 1
        if depth == 0: return text[begin:i+1]
    raise ValueError(name)


def main():
    assert sha((CORRECTION / 'source-seal.json').read_bytes()) == 'a51d5791cad11e6fb3a587d11b7c225216c11b75ccd89768a691c477a7f51b4c'
    seal = json.loads((CORRECTION / 'source-seal.json').read_text())
    for row in seal['members']:
        data = (CORRECTION / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    preparation = json.loads((CORRECTION / 'preparation.json').read_text())
    checks, changed = [], []
    def check(name, passed, detail):
        checks.append({'name': name, 'passed': passed, 'detail': detail})
        assert passed, (name, detail)
    for path in sorted(SOURCE.rglob('*')):
        if not path.is_file(): continue
        relative = str(path.relative_to(SOURCE)); before = (BASE / relative).read_bytes(); after = path.read_bytes()
        expected = before.decode()
        for replacement in preparation['exact_replacements'].get(relative, []):
            assert expected.count(replacement['old']) == 1
            expected = expected.replace(replacement['old'], replacement['new'], 1)
        assert expected.encode() == after, relative
        if before != after:
            changed.append({'path': relative, 'before_sha256': sha(before), 'after_sha256': sha(after)})
    check('exact three-file declared reconstruction', len(changed) == 3, changed)
    control = (SOURCE / 'src/experimental_swift_reactor/control.rs').read_text()
    old_control = (BASE / 'src/experimental_swift_reactor/control.rs').read_text()
    initial = (SOURCE / 'src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text()
    old_initial = (BASE / 'src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text()
    cache = (SOURCE / 'src/experimental_swift_reactor/cache.rs').read_text()
    token = block(control, "pub(super) struct SnapshotScopeBorrowV1<'a>")
    check('token fields private and actual same-lifetime owners', token == "pub(super) struct SnapshotScopeBorrowV1<'a> {\n    cache:&'a mut Option<super::cache::SwiftFunctionCache>,\n    control:&'a mut RuntimeControl,\n    wasi:Option<&'a AccountedWasi>,\n    adopted:AdoptedProof,\n}", sha(token.encode()))
    check('one actual private token mint', len(re.findall(r'SnapshotScopeBorrowV1\s*\{', control)) == 1,
          'sole mint is the exact declared scope construct replacement')
    for name in ['pub(crate) struct RuntimeControl', 'pub(super) struct SnapshotScopeV1', 'pub(super) struct SnapshotRunV1',
                 'pub(super) struct SnapshotScopeFinishV1', 'fn snapshot_scope_candidate_foundation_v1', 'pub(crate) fn foundation_construction_bytes']:
        before, after = block(old_control, name), block(control, name)
        check('unchanged ' + name, before == after, sha(after.encode()))
    for name in ['enum InitialProfileConstructionOutcomeV1', 'pub(crate) struct InitialProfileBorrowV1',
                 'fn construct_with_initial_profile_v1', 'fn construct_profile_core_v1', 'fn write_snapshot_v1', 'fn proposed_emission_work_v1']:
        before, after = block(old_initial, name), block(initial, name)
        check('unchanged ' + name, before == after, sha(after.encode()))
    check('outer entry requires token only for owner bundle',
          'construct_snapshot_in_scope_v1(owners:super::control::SnapshotScopeBorrowV1' in cache,
          'no raw cache/control/WASI/adopted owner signature')
    check('inner entry consumes token into tied parts',
          'construct_snapshot_owned_v1(owners:super::super::control::SnapshotScopeBorrowV1' in initial
          and 'let (cache,control,wasi,adopted)=owners.into_parts();' in initial,
          'same private Selected branch core call follows consuming accessor')
    check('one remaining private Selected branch construction', initial.count('SnapshotBranchV1{output:snapshot}') == 1,
          'inside token-requiring inner entry; closed generic core unchanged')
    save('source-checks.json', {'schema': 1, 'checks': checks,
        'scope': 'exact reconstruction/differential evidence supplements fresh compiler controls; not syntax-only release authority'})
    receipts = []
    for path in sorted((OUT / 'commands').glob('*/receipt.json')):
        row = json.loads(path.read_text())
        assert row['passed'] and row['direct_child_reaped'] and row['owned_group_absent'] and not row['timed_out']
        receipts.append({'receipt': identity(path), 'source_tree_sha256': row['source_tree_sha256'],
                         'elapsed_seconds': row['elapsed_seconds'], 'diagnostics': row['observed_diagnostics']})
    assert len(receipts) == 14
    assert not (OUT / 'owned-work').exists() and not list(OUT.rglob('*.rmeta'))
    save('review.json', {
        'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'authority-correction-accepted-in-bounded-source-compiler-scope',
        'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve())], 'python_version': sys.version,
        'source_seal_sha256': 'a51d5791cad11e6fb3a587d11b7c225216c11b75ccd89768a691c477a7f51b4c',
        'source_tree_sha256': '575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896',
        'source_members': 144, 'source_subset_members_reverified': len(seal['members']),
        'source_subset_bytes_reverified': sum(row['bytes'] for row in seal['members']),
        'prior_C1': 'closed at both formerly callable raw-parts Selected boundaries',
        'fresh_controls': {'compiler_metadata_commands': 14, 'authentic_route_positive': 2,
            'both_exact_old_bypasses_negative': 2, 'private_forge_negative': 2, 'double_consume_negative': 2,
            'borrow_escape_negative': 2, 'move_borrowed_scope_negative': 2, 'foreign_control_substitution_negative': 2,
            'token_and_parts_tuple_symbolic_size_alignment_equalities': 4,
            'static_reconstruction_checks': len(checks), 'unexpected_failures': 0},
        'accepted_contract': ['sole private mint inside consuming actual selected scope',
            'opaque single-use token carries same actual exclusive cache/control borrows, optional WASI borrow and adopted owner',
            'both outer and inner selected constructors require the token; no detached permit or replacement raw-parts route',
            'consuming parts tuple preserves original lifetimes and adopted ownership; all borrows end before scope moves into Run',
            'Original ABI, guard, eight outcomes, encoder/writer bodies, work stop and existing foundation formulas unchanged'],
        'role_and_work_delta': identity(OUT / 'source-role-delta.md'),
        'storage_floor_selected': False, 'work_formula_selected': False, 'healthy_cleanup_qualified': False,
        'runtime_executed': False, 'writer_executed': False, 'paused_surfaces_or_process_inventories_used': False,
        'scope': 'bounded source authority correction only; whole accounting, caller work, stop amendment and operational behavior remain pending',
        'cleanup': {'all_direct_compiler_children_reaped': True, 'all_known_owned_groups_absent': True,
                    'owned_scratch_removed': True, 'compiler_timeout_seconds': 55,
                    'maximum_elapsed_seconds': max(row['elapsed_seconds'] for row in receipts), 'timed_out': 0},
        'root_command_results_read': False, 'other_active_lanes_read': False,
        'canonical_product_changed': False, 'git_mutations': False, 'GA_gates_verified': 0,
        'compiler_receipts': receipts,
    })
    members = [identity(path) for path in sorted(OUT.rglob('*')) if path.is_file() and path.name != 'seal.json']
    stream = ''.join(f"{row['path']}\0{row['bytes']}\0{row['sha256']}\n" for row in members).encode()
    save('seal.json', {'schema': 1, 'member_count': len(members), 'bytes': sum(row['bytes'] for row in members),
        'members': members, 'tree_sha256': sha(stream), 'tree_digest_format': 'path NUL decimal-bytes NUL sha256 newline in sorted path order',
        'scope': 'independent source/compiler authority correction acceptance only; no complete floor/work or writer execution'})
    print(json.dumps(identity(OUT / 'seal.json')))


if __name__ == '__main__': main()
