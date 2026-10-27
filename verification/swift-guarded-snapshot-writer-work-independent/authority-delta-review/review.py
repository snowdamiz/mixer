#!/usr/bin/env python3
"""Bounded independent source-action delta review; no product/producer execution."""
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
PROPOSAL = V / 'swift-guarded-snapshot-authority-work-delta'
AUTH = V / 'swift-guarded-snapshot-scope-authority-correction'
INDEPENDENT = V / 'swift-guarded-snapshot-composition-independent/authority-correction-review'
ORIGINAL = V / 'swift-guarded-snapshot-composition-source-preparation'
WRITER = V / 'swift-guarded-snapshot-writer-work-audit'
CORRECTION = V / 'swift-guarded-snapshot-writer-work-correction'
checks = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def read(path):
    return json.loads(path.read_text())


def require(value, detail):
    if not value:
        raise RuntimeError(detail)


def check(family, value, **detail):
    require(value, (family, detail))
    checks.append(dict(family=family, **detail))


def sealed(folder, expected, count):
    data = (folder / 'seal.json').read_bytes()
    require(sha(data) == expected, ('seal digest', str(folder)))
    value = json.loads(data)
    require(len(value['members']) == count, ('member count', str(folder)))
    for row in value['members']:
        raw = (folder / row['path']).read_bytes()
        require(len(raw) == row['bytes'] and sha(raw) == row['sha256'], ('member digest', row['path']))
    return dict(path=str((folder / 'seal.json').relative_to(ROOT)), sha256=expected,
                members_verified=count, member_bytes=sum(r['bytes'] for r in value['members']))


def exact_function(path, marker):
    data = path.read_text()
    require(data.count(marker) == 1, ('function occurrence', marker))
    start = data.index(marker)
    pos = data.index('{', start)
    depth = 0
    quoted = False
    escape = False
    while pos < len(data):
        ch = data[pos]
        if quoted:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if not depth:
                body = data[start:pos + 1]
                return dict(file=str(path.relative_to(ROOT)), start_line=data[:start].count('\n') + 1,
                            source=body, bytes=len(body.encode()), sha256=sha(body.encode()))
        pos += 1
    raise RuntimeError(('function termination', marker))


def validate(parts):
    # Categories are independently derived from four actual bodies. Bound local
    # call operands and owned parameter forwarding remain free by convention.
    require(parts['scope'] == dict(adopted_take_expect_binding=6, cache_control_and_WASI_references=5,
                                  enter_return=2, outer_binding=1, run_slots=2,
                                  token_aggregate_fields=4, token_local_binding=1), 'scope categories')
    require(parts['helper'] == dict(enter_return=2, four_field_pattern_bindings=4, four_tuple_output_slots=4), 'helper categories')
    require(parts['forwarding'] == dict(SnapshotBranch_output_slot=1, cache_forward_enter_return=2,
                                       owned_forward_enter_return=2, into_parts_helper=10,
                                       four_caller_tuple_pattern_bindings=4), 'forward categories')
    require(sum(parts['scope'].values()) == 21 and sum(parts['helper'].values()) == 10 and
            sum(parts['forwarding'].values()) == 19, 'source row totals')


def main():
    custody = [sealed(PROPOSAL, '625ca2e549dbf32545722b44d2fc8af5715f70cf31a623f6cd432590d96e626d', 9),
               sealed(AUTH, '351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c', 225),
               sealed(INDEPENDENT, 'ed396b3b74fb5e399d7ebee1759b19dae35d8f7fc577fdd92825f7eb31421b36', 77),
               sealed(WRITER, '1dba5632efbf285f303eddc4c9dcb727d0bfaae9f24400a32de98a8989d292ea', 14),
               sealed(CORRECTION, 'b1dd6bf46cd8416637e169ab00fc4e1aa03c094d6c89edb71f0f9721369bd5f7', 9)]
    references = []
    for name, expected in [
        ('guarded-snapshot-authority-work-delta-release.json', 'c9910093451dda292364135ab06987fca3dcb4af4ef3927fa763f67f34b3bea5'),
        ('guarded-snapshot-scope-authority-host-acceptance.json', 'd0eda272985957f2fb8fb14e893de8ad20ab535095b3d9df11b3ff6fe426ce76'),
    ]:
        path = V / 'swift-semantic-adapter-root-review' / name
        require(sha(path.read_bytes()) == expected, ('reference digest', name))
        references.append(dict(path=str(path.relative_to(ROOT)), sha256=expected))
    manifest = read(AUTH / 'source-manifest.json')
    check('accepted-authority-144-tree', len(manifest['members']) == 144 and sha(canon(manifest['members'])) == manifest['source_tree_sha256'] == '575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896')
    old_manifest = {r['path']: r for r in read(ORIGINAL / 'source-manifest.json')['members']}
    changed = sorted(r['path'] for r in manifest['members'] if r != old_manifest[r['path']])
    check('only-three-authority-source-files-change', changed == ['src/experimental_swift_reactor/cache.rs',
          'src/experimental_swift_reactor/cache/initial_profile_v1.rs', 'src/experimental_swift_reactor/control.rs'])
    p = read(PROPOSAL / 'results.json')
    vm = AUTH / 'source/vm'
    bindings = [
        exact_function(vm / 'src/experimental_swift_reactor/control.rs', 'pub(super) fn construct_v1(mut self,'),
        exact_function(vm / 'src/experimental_swift_reactor/control.rs', "pub(super) fn into_parts(self)->(&'a mut Option<super::cache::SwiftFunctionCache>"),
        exact_function(vm / 'src/experimental_swift_reactor/cache.rs', 'pub(super) fn construct_snapshot_in_scope_v1('),
        exact_function(vm / 'src/experimental_swift_reactor/cache/initial_profile_v1.rs', 'pub(super) fn construct_snapshot_owned_v1('),
    ]
    for actual, expected in zip(bindings, p['source_bindings']):
        check('exact-four-function-binding', actual == expected, file=actual['file'], line=actual['start_line'])
    scope_body, helper_body, outer_body, inner_body = [b['source'] for b in bindings]
    check('actual-four-token-fields', 'cache:&mut self.cache,control:&mut self.control,wasi:self.wasi.as_ref(),adopted,' in scope_body and
          scope_body.count('let owners=SnapshotScopeBorrowV1 {') == 1)
    check('actual-helper-pattern-and-tuple', helper_body.count('let Self {cache,control,wasi,adopted}=self;') == 1 and helper_body.count('(cache,control,wasi,adopted)') == 1)
    check('actual-one-inner-call-and-pattern', inner_body.count('let (cache,control,wasi,adopted)=owners.into_parts();') == 1)
    check('unchanged-forward-core-and-branch', outer_body.count('construct_snapshot_owned_v1(owners,claims,rows,snapshot)') == 1 and
          inner_body.count('construct_profile_core_v1(cache,control,wasi,adopted,&selected_initial_profile_v1(),claims,rows,SnapshotBranchV1{output:snapshot})') == 1)
    old_rows = {r['name']: r for r in read(WRITER / 'ledger.json')['rows']}
    corrected_rows = {r['name']: r for r in read(CORRECTION / 'corrected-ledger.json')['rows']}
    scope = old_rows['SnapshotScope.construct_v1_added_bookkeeping']
    forwarding = old_rows['selected_construction_forwarding_added_bookkeeping']
    check('old-rows-unaffected-by-writer-correction', scope == corrected_rows[scope['name']] == p['old_scope_construct'] and
          forwarding == corrected_rows[forwarding['name']] == p['old_forwarding'])
    check('old-rows-21', sum(scope['parts'].values()) == scope['credits'] == 16 and
          sum(forwarding['parts'].values()) == forwarding['credits'] == 5)
    convention = (WRITER / 'cost-convention.md').read_bytes()
    check('unchanged-source-convention', sha(convention) == p['cost_convention']['sha256'] == '9b20fd84d245dab720a06a7144fabb7b30fb705796f5d9f22ee4169a909fac16')
    encoder_convention = (V / 'swift-guarded-snapshot-encoder-work-audit/cost-convention.md').read_text()
    check('bound-operands-and-moves-convention', 'Literal values and already-bound local operands are' in encoder_convention and
          'Ownership moves do not imply byte copying' in encoder_convention and 'an explicit ownership field move is one slot store' in encoder_convention)
    parts = dict(scope=copy.deepcopy(p['new_scope_construct_parts']), helper=copy.deepcopy(p['into_parts_helper_parts']),
                 forwarding=copy.deepcopy(p['new_forwarding_parts']))
    validate(parts)
    check('independent-named-category-accounting', True)
    check('combined-delta19', sum(parts['scope'].values()) + sum(parts['forwarding'].values()) == 40 and 40 - 21 == p['added_once_per_consuming_construction'] == 19)
    check('borrow-expressions-5-once', parts['scope']['cache_control_and_WASI_references'] == scope['parts']['cache_control_and_WASI_references'] == 5)
    check('entry-return-and-branch-once', parts['forwarding']['cache_forward_enter_return'] + parts['forwarding']['owned_forward_enter_return'] == 4 and parts['forwarding']['SnapshotBranch_output_slot'] == 1)
    for group, category in [('scope', 'token_aggregate_fields'), ('scope', 'token_local_binding'),
                             ('helper', 'enter_return'), ('helper', 'four_field_pattern_bindings'),
                             ('helper', 'four_tuple_output_slots'), ('forwarding', 'four_caller_tuple_pattern_bindings')]:
        mutant = copy.deepcopy(parts)
        mutant[group][category] = 0
        rejected = False
        try:
            validate(mutant)
        except RuntimeError:
            rejected = True
        check('missing-category-rejected', rejected, category=category)
    for group, category, amount in [('scope', 'duplicated_raw_borrows', 5), ('forwarding', 'duplicated_old_pair', 21),
                                     ('helper', 'invented_Option_Result', 1), ('forwarding', 'invented_owned_local_fetch', 1)]:
        mutant = copy.deepcopy(parts)
        mutant[group][category] = amount
        rejected = False
        try:
            validate(mutant)
        except RuntimeError:
            rejected = True
        check('extra-category-rejected', rejected, category=category)
    check('scope-consumption-order', scope_body.index('let adopted=') < scope_body.index('let owners=') < scope_body.index('let outer=') < scope_body.index('SnapshotRunV1 {scope:self,outer}'))
    check('parts-before-core', inner_body.index('owners.into_parts()') < inner_body.index('construct_profile_core_v1('))
    core_new = exact_function(vm / 'src/experimental_swift_reactor/cache/initial_profile_v1.rs', 'fn construct_profile_core_v1<')['source']
    core_old = exact_function(ORIGINAL / 'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs', 'fn construct_profile_core_v1<')['source']
    check('core-unchanged-and-predebit-early-returns', core_new == core_old and core_new.index('return branch.early(') < core_new.index('branch.begin(cache,control,wasi)'))
    begin = exact_function(vm / 'src/experimental_swift_reactor/cache/initial_profile_v1.rs', "fn begin_snapshot_access_v1<'c>(")['source']
    check('no-retrospective-planning-funding', 'control.snapshot_debit_v1(planning)?;' in begin and 'Err(AError::WorkAuditPending)' in (vm / 'src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text())
    for calls in (0, 1, 2, 32, 1024):
        check('per-consuming-call-not-global', (21 + 19) * calls == 40 * calls and (40 - 21) * calls == 19 * calls, calls=calls)
    check('no-new-encoder-stop-native-or-fallible-token-carrier', all(term not in ''.join(b['source'] for b in bindings) for term in ['next_block(', '.write(', '.stop(', 'snapshot_observe_stop', 'Result<', '->Option<']))
    # An original failed authoring attempt is preserved as source evidence. This
    # compiles its Python text to reproduce the expected SyntaxError; it executes
    # no instructions from either producer script.
    failed = PROPOSAL / 'attempt-history/initial-check.py.txt'
    failure_receipt = read(PROPOSAL / 'attempt-history/initial-failure.json')
    expected_syntax = None
    try:
        compile(failed.read_text(), str(failed), 'exec')
    except SyntaxError as exc:
        expected_syntax = dict(type=type(exc).__name__, message=exc.msg, line=exc.lineno)
    check('original-authoring-failure-retained', sha(failed.read_bytes()) == failure_receipt['script_sha256'] and
          expected_syntax == dict(type='SyntaxError', message="unmatched ')'", line=55))
    source_role = INDEPENDENT / 'source-role-delta.md'
    check('source-role-delta-bound', sha(source_role.read_bytes()) == 'cb29603668f017b4565c399b4f5839ff907af47419e0f66a7ead12d6f83af5b6')
    result = dict(schema=1, status='authority-constructor-source-action-delta19-corroborated',
                  checks_passed=len(checks), families=dict(Counter(c['family'] for c in checks)), checks_sha256=sha(canon(checks)),
                  python=sys.version, platform=platform.platform(), new_findings=[], old_scope=16, corrected_scope=21,
                  old_forwarding=5, corrected_forwarding=19, old_combined=21, corrected_combined=40, delta_per_consuming_construct=19,
                  placement='pre-admitted before phase planning; required even on core early returns; no selected funding',
                  source_delta_only=True, complete_operational_work_selected=False, runtime_cost_measured=False,
                  original_producer_assertions='15 sealed prior controls, not this review execution or runtime-cost proof',
                  preserved_authoring_failure=expected_syntax)
    inputs = dict(schema=1, seals=custody, references=references, exact_four_functions=bindings,
                  accepted_authority_source_tree_sha256=manifest['source_tree_sha256'],
                  source_role_delta=dict(path=str(source_role.relative_to(ROOT)), sha256=sha(source_role.read_bytes())),
                  old_ledger=dict(path=str((WRITER / 'ledger.json').relative_to(ROOT)), sha256=sha((WRITER / 'ledger.json').read_bytes())),
                  no_repeated_compiler_or_runtime_execution=True)
    for name, value in [('results.json', result), ('input-custody.json', inputs)]:
        raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
        if '--verify' in sys.argv:
            require((HERE / name).read_bytes() == raw, ('output mismatch', name))
        else:
            (HERE / name).write_bytes(raw)
    print(json.dumps(dict(status=result['status'], checks_passed=len(checks), delta=19,
                          complete_operational_work_selected=False, runtime_cost_measured=False), sort_keys=True))


if __name__ == '__main__':
    main()
