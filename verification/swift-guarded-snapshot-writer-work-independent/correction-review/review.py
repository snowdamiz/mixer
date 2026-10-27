#!/usr/bin/env python3
"""Independent bounded correction review; immutable reads and Python arithmetic only."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import platform
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
V = ROOT / 'verification'
OLD = V / 'swift-guarded-snapshot-writer-work-audit'
FIX = V / 'swift-guarded-snapshot-writer-work-correction'
FIRST = HERE.parent / 'candidate-review'
PREP = V / 'swift-guarded-snapshot-composition-source-preparation'
checks = []


def require(value, detail):
    if not value:
        raise RuntimeError(detail)


def check(family, value, **detail):
    require(value, (family, detail))
    checks.append(dict(family=family, **detail))


def sha(value):
    return hashlib.sha256(value).hexdigest()


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def read(path):
    return json.loads(path.read_text())


def sealed(folder, expected, count):
    raw = (folder / 'seal.json').read_bytes()
    require(sha(raw) == expected, ('seal digest', str(folder)))
    value = json.loads(raw)
    require(len(value['members']) == count, ('seal count', str(folder)))
    for row in value['members']:
        data = (folder / row['path']).read_bytes()
        require(len(data) == row['bytes'] and sha(data) == row['sha256'], ('member digest', row['path']))
    return {'path': str((folder / 'seal.json').relative_to(ROOT)), 'sha256': expected,
            'members_verified': count, 'member_bytes': sum(r['bytes'] for r in value['members'])}


def delta(a, b, path=''):
    """Independent structural comparison; additions retain the whole added value."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(set(a) | set(b))
        for key in keys:
            p = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in a:
                out.append(dict(path=p, operation='add', after=b[key]))
            elif key not in b:
                out.append(dict(path=p, operation='remove', before=a[key]))
            else:
                out.extend(delta(a[key], b[key], p))
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            p = path + '/' + str(i)
            if i >= len(a):
                out.append(dict(path=p, operation='add', after=b[i]))
            elif i >= len(b):
                out.append(dict(path=p, operation='remove', before=a[i]))
            else:
                out.extend(delta(a[i], b[i], p))
    elif a != b:
        out.append(dict(path=path, operation='replace', before=a, after=b))
    return out


def rows(value):
    return {r['name']: r for r in value['rows']}


def algebra(value, corrected):
    r = rows(value)
    n = lambda name: r[name]['credits']
    require(all(sum(x['parts'].values()) == x['credits'] for x in value['rows']), 'row arithmetic')
    require(r['snapshot_totals_v1']['parts']['enter_foundation_question_binding'] == n('snapshot_foundation_pair_v1') + 5, 'totals foundation')
    require(r['snapshot_storage_preflight_v1']['parts']['enter_foundation_question_binding'] == n('snapshot_foundation_pair_v1') + 5, 'preflight foundation')
    require(r['snapshot_commit_storage_v1']['parts']['enter_repeated_preflight_question_binding'] == n('snapshot_storage_preflight_v1') + 5, 'repeat preflight')
    require(r['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts']['optional_WASI_match_upper'] == n('AccountedWasi.snapshot_pair_v1') + 10, 'embedded WASI')
    require(r['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts']['totals_args_and_question'] == n('snapshot_totals_v1') + 4, 'cache totals')
    w, a, wrap = value['writer'], value['admission'], value['wrappers']
    require(w['base_without_terminal_tail'] == n('writer_fixed_nonstop_nogetters') + 12 * 15 + 2 * 3, 'fixed writer')
    require(w['base_with_terminal_tail'] == w['base_without_terminal_tail'] + n('writer_global_terminal_tail'), 'writer tail')
    require(w['per_block_including_clear_and_observations_getters'] == n('writer_per_block_nonstop_nogetters_nonclear') + 5 * 15 + 3 * 3 + 4096 == 4259, 'block')
    require(w['per_attempt_including_observations_getters'] == n('writer_per_attempt_nonstop_nogetters') + 2 * 15 + 2 * 3 == 122, 'attempt')
    require(a['max_optional_WASI_pair'] == n('SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI'), 'admission pair')
    require(wrap['finish_once_including_retire_and_optional_pair_Existing_copy'] == n('SnapshotRun.finish_v1_added_bookkeeping_without_retire') + wrap['retire_once'] + 302, 'finish')
    terminal = 2 if corrected else 0
    require(a['current_pending_path_upper'] == 32 + a['max_optional_WASI_pair'] + 260 + 44 + 55 + 501 + 3 + 608 + terminal, 'current begin')
    require(a['future_all_branch_begin_excluding_formula_evaluator'] == 66 + a['max_optional_WASI_pair'] + 260 + 88 + 55 + 501 + 293 + 31 + 4096 + 608 + terminal, 'future begin')
    require(a['pre_admitted_shell_with_common_refusal_tail_upper'] == 13 + 14 + a['max_optional_WASI_pair'] + 260 + 44 + 608 + terminal, 'shell')
    require(wrap['adoption_callbacks_all_branch_upper'] == sum(n(k) for k in ['SnapshotAdoption.foundation_added_bookkeeping', 'SnapshotAdoption.retire_tickets_added_bookkeeping', 'SnapshotAdoption.failure_added_bookkeeping']), 'callbacks')
    if corrected:
        require(r['writer_fixed_nonstop_nogetters']['parts']['actual_proof_counts_binding'] == 57, 'W1')
        require(r['AccountedWasi.snapshot_pair_v1']['parts']['four_identity_loop_with_setup'] == 247, 'W2-WASI')
        require(r['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts']['three_identity_loop'] == 186, 'W2-cache')
        require(n('snapshot_observe_stop_v1_Deadline_branch') == 17 and n('snapshot_observe_stop_v1_without_large_Copy') == 15, 'Deadline full branch')
        require(r['writer_global_terminal_tail']['parts']['terminal_Deadline_excess_over_success'] == 2 and n('admission_once_only_terminal_Deadline_tail') == 2, 'Deadline excess once')


def main():
    custody = [sealed(FIX, 'b1dd6bf46cd8416637e169ab00fc4e1aa03c094d6c89edb71f0f9721369bd5f7', 9),
               sealed(OLD, '1dba5632efbf285f303eddc4c9dcb727d0bfaae9f24400a32de98a8989d292ea', 14),
               sealed(FIRST, '8ecf12f725d6a6ffc449d46c29243948efcb95332a8d9a33dda0f0eac7732592', 6),
               sealed(PREP, 'bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751', 495)]
    release = V / 'swift-semantic-adapter-root-review/guarded-snapshot-writer-work-correction-release.json'
    require(sha(release.read_bytes()) == '9a9f0b2502bb6a956c173bf2e22193b79577d5ab4e868e0d6f8679973d469488', 'release')
    bindings = read(OLD / 'source-bindings.json')
    fixbindings = read(FIX / 'source-bindings.json')
    check('same-121-definition-interface', len(bindings['definitions']) == 121 and
          sha(canon(bindings['definitions'])) == fixbindings['definition_tree_sha256'] == '394b4a582a1490a04635a2b5a1ae10eb94da55db25b18c5606ac493ea346edd3' and
          all(b in bindings['definitions'] for b in fixbindings['focused_definitions']))
    for f in bindings['observed_files']:
        raw = (PREP / 'source/vm/src' / f['path']).read_bytes()
        check('unchanged-bound-source-file', len(raw) == f['bytes'] and sha(raw) == f['sha256'], path=f['path'])
    manifest = read(PREP / 'source-manifest.json')
    check('same-144-source-tree', len(manifest['members']) == 144 and sha(canon(manifest['members'])) == '140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395')
    old, fixed = read(OLD / 'ledger.json'), read(FIX / 'corrected-ledger.json')
    changes = delta(old, fixed)
    documented = read(FIX / 'ledger-diff.json')
    check('exact-38-path-delta', changes == documented['changes'] and len(changes) == 38 and sha(canon(fixed)) == documented['after_canonical_sha256'])
    numeric = {
        '/admission/current_pending_path_upper': 3435,
        '/admission/future_all_branch_begin_excluding_formula_evaluator': 7930,
        '/admission/global_terminal_Deadline_tail': 2,
        '/admission/max_optional_WASI_pair': 1930,
        '/admission/pre_admitted_shell_with_common_refusal_tail_upper': 2871,
        '/rows/26/credits': 667, '/rows/26/parts/four_identity_loop_with_setup': 247,
        '/rows/27/credits': 1930, '/rows/27/parts/optional_WASI_match_upper': 677,
        '/rows/27/parts/three_identity_loop': 186,
        '/rows/29/credits': 401, '/rows/29/parts/actual_proof_counts_binding': 57,
        '/rows/32/credits': 630, '/rows/32/parts/terminal_Deadline_excess_over_success': 2,
        '/rows/35/credits': 813, '/rows/35/parts/WASI_pair_ref_result_guard': 670,
        '/wrappers/finish_once_including_retire_and_optional_pair_Existing_copy': 1247,
        '/writer/S_observe_terminal_Deadline_without_large_Copy': 17,
        '/writer/base_with_terminal_tail': 1217, '/writer/base_without_terminal_tail': 587,
        '/writer/global_terminal_tail': 630,
    }
    text_paths = {'/admission/current_pending_path_decomposition', '/admission/future_begin_decomposition',
                  '/admission/shell_decomposition', '/formula_interface/conservative_partial_substitution',
                  '/formula_interface/partial_emission_consumption_contract', '/status',
                  '/writer/required_native_transfer_additive_term', '/writer/source_action_upper'}
    text_paths.update('/rows/' + str(i) + '/note' for i in (10, 26, 27, 29, 32, 33, 35))
    additions = {'/rows/54', '/rows/55'}
    check('only-findings-related-paths', {c['path'] for c in changes} == set(numeric) | text_paths | additions)
    mapped = {c['path']: c for c in changes}
    for path, expected in numeric.items():
        check('independent-expected-source-delta', mapped[path]['after'] == expected, path=path)
    r = rows(fixed)
    check('named-terminal-row-parts', r['snapshot_observe_stop_v1_Deadline_branch']['parts'] ==
          dict(preceding_common_actions=14, deadline_origin_fetch=1, Deadline_tag=1, Err_carrier=1))
    check('named-admission-terminal-row', r['admission_once_only_terminal_Deadline_tail']['parts'] == dict(terminal_Deadline_excess_over_success=2))
    algebra(old, False)
    check('original-algebra-reproduced', True)
    algebra(fixed, True)
    check('corrected-algebra-reproduced', True)
    changed_rows = {'snapshot_observe_stop_v1_without_large_Copy', 'AccountedWasi.snapshot_pair_v1',
                    'SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI', 'writer_fixed_nonstop_nogetters',
                    'writer_global_terminal_tail', 'admission_global_large_copy_tail',
                    'SnapshotRun.finish_v1_added_bookkeeping_without_retire'}
    for name, row in rows(old).items():
        if name not in changed_rows:
            check('original-row-exactly-retained', row == r[name], name=name)
    for parent, field in [('wrappers', 'inherited_dependencies'), ('wrappers', 'call_count_constraints'),
                          ('admission', 'global_large_copy_tail'), ('admission', 'admitted_transfer_zero_bytes_once'),
                          ('admission', 'pending_formula_evaluator')]:
        check('unchanged-external-obligation', fixed[parent][field] == old[parent][field], field=field)
    check('no-pair-doublecount', r['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts']['optional_WASI_match_upper'] - rows(old)['SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI']['parts']['optional_WASI_match_upper'] == 1 and fixed['admission']['max_optional_WASI_pair'] - old['admission']['max_optional_WASI_pair'] == 2)
    for blocks in (1, 2, 3, 17, 17033):
        for factor in (1, 2, 16, 31, 32):
            A = factor * blocks
            check('writer-substitution', 1217 + 4259 * blocks + 122 * A <= 1217 + 8163 * blocks)
            total = 12 + 5 * blocks + 2 * A
            # All earlier observations succeed, one selected Deadline then abort.
            for terminal in (1, 2, total // 2, total - 1, total):
                check('once-terminal-writer-prefix', (terminal - 1) * 15 + 17 == terminal * 15 + 2)
    # Five possible admission observation sites: pair, preflight, planning debit,
    # emission debit, commit's repeated preflight. Any selected error stops the
    # decision closure before a later site, so excess2 is shared across all five.
    for first_error in range(5):
        visited = []
        extra = 0
        for site in range(5):
            visited.append(site)
            if site == first_error:
                extra += 17 - 15
                break
        check('once-terminal-admission-prefix', len(visited) == first_error + 1 and extra == 2)
    # Reversion mutation controls use our own algebra validator, not producer code.
    for name, term, prior in [('writer_fixed_nonstop_nogetters', 'actual_proof_counts_binding', 56),
                               ('AccountedWasi.snapshot_pair_v1', 'four_identity_loop_with_setup', 246),
                               ('SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI', 'three_identity_loop', 185),
                               ('writer_global_terminal_tail', 'terminal_Deadline_excess_over_success', 0),
                               ('admission_once_only_terminal_Deadline_tail', 'terminal_Deadline_excess_over_success', 0)]:
        mutant = copy.deepcopy(fixed)
        rows(mutant)[name]['parts'][term] = prior
        for row in mutant['rows']:
            row['credits'] = sum(row['parts'].values())
        rejected = False
        try:
            algebra(mutant, True)
        except RuntimeError:
            rejected = True
        check('independent-reversion-rejected', rejected, name=name)
    for extent in (2560, 4095, 4096, 4097, 8191, 8192, 8193, 69765152):
        B = (extent + 4095) // 4096
        check('transfer-contract-separation', 32 * extent != B * 4096 and 4096 == fixed['admission']['admitted_transfer_zero_bytes_once'] and
              '+32E' in fixed['formula_interface']['partial_emission_consumption_contract'])
    check('partial-contract-preserved', 'evaluator' in fixed['admission']['pending_formula_evaluator'] or 'arithmetic' in fixed['admission']['pending_formula_evaluator'])
    source = (PREP / 'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text()
    check('source-still-fails-closed', 'Err(AError::WorkAuditPending)' in source and 'if final_block{break;}' in source)
    result = dict(schema=1, status='corrected-original495-local-source-action-interface-corroborated',
                  checks_passed=len(checks), families=dict(Counter(c['family'] for c in checks)),
                  checks_sha256=sha(canon(checks)), python=sys.version, platform=platform.platform(),
                  findings_repaired=['W1', 'W2', 'W3'], new_findings=[], source_delta=False,
                  operational_work_selected=False, later225_authority_delta_reviewed=False,
                  prior_916_producer_controls='read as sealed prior evidence; not rerun or claimed as this review',
                  prior_1413_review_controls='sealed predecessor evidence; new independent algebra reproduced here')
    custody_out = dict(schema=1, inputs=custody, release={'path': str(release.relative_to(ROOT)), 'sha256': sha(release.read_bytes())},
                       source_members=144, source_tree_sha256=fixbindings['original144_source_tree_sha256'],
                       exact_121_binding_reference=fixbindings['full_bindings_reference'], definition_tree_sha256=fixbindings['definition_tree_sha256'],
                       custody_method='Rehash495 sealed composer members and all10 producer-observed full source files; preserve original121 exact-definition reference and compare focused correction bindings. No new definition extraction claim.',
                       ledger_delta_paths=38, corrected_ledger_canonical_sha256=sha(canon(fixed)))
    for name, value in [('results.json', result), ('input-custody.json', custody_out)]:
        raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
        if '--verify' in sys.argv:
            require((HERE / name).read_bytes() == raw, ('output drift', name))
        else:
            (HERE / name).write_bytes(raw)
    print(json.dumps(dict(status=result['status'], checks_passed=len(checks), ledger_delta_paths=38,
                          findings_repaired=result['findings_repaired'], operational_work_selected=False), sort_keys=True))


if __name__ == '__main__':
    main()
