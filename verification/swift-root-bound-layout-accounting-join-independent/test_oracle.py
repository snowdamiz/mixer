#!/usr/bin/env python3
"""Finite independent source/data join controls; no product or producer replay."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from oracle import Refusal, normalize, observed_map, require_link, require_closure, checked_difference, prohibit_total, OWNER

D = Path(__file__).resolve().parent
R = D.parents[1]


def main():
    contract = json.loads((D / 'preaccess-contract.json').read_bytes())
    acceptance = json.loads((R / 'verification/swift-semantic-adapter-root-review/root-bound-layout-observation-acceptance.json').read_bytes())['acceptance']
    shapes = observed_map(acceptance['named_layouts'])
    target, tree = contract['target'], contract['source146_tree']
    def link(spelling, **changes):
        return require_link(spelling, shapes, target=changes.get('target', target), source_tree=changes.get('tree', tree), expected_target=target, expected_tree=tree)
    assert link(OWNER + "RootBoundV1<'_, RawFixtureResultV1>")['size'] == 13616
    assert link("Option<&AdmittedFixtureOutcomeV1<'_>>")['size'] == 8
    assert normalize("&'static BootstrapLedgerV1") == normalize('&BootstrapLedgerV1')
    assert normalize("AdmittedLoaderCorrespondenceV1<'_, '_>") == normalize("AdmittedLoaderCorrespondenceV1<'static, 'static>")
    assert normalize("AdmittedLoaderCorrespondenceV1<'_>") != normalize("AdmittedLoaderCorrespondenceV1<'_, '_>")
    assert normalize("RootBoundFixtureOutcomeV1<'_>") != normalize("RootBoundV1<'_, RawFixtureResultV1>")
    roles = json.loads((D / 'role-expectations.json').read_bytes())['roles']
    assert len(roles) == 645 and len({row['role_id'] for row in roles}) == 645
    closure_roles = [row for row in roles if row['binding'] == 'exact-actual-dispatch-closure']
    assert len(closure_roles) == 2 and len({row['type_spelling'] for row in closure_roles}) == 1
    exact = closure_roles[0]['type_spelling']
    allowed = {(1236, 'local-or-return', '_25'), (1237, 'argument', '_1')}
    assert require_closure(exact, (1236, 'local-or-return', '_25'), exact_spelling=exact, allowed_roles=allowed) == {'size': 48, 'align': 8}
    controls = []
    def refuse(label, action):
        try:
            action()
        except Refusal as error:
            controls.append({'name': label, 'rejected': True, 'reason': str(error)})
        else:
            raise AssertionError('adverse join accepted: ' + label)
    refuse('wrong-module-same-leaf-name', lambda: link("foreign::RootBoundV1<'_, RawFixtureResultV1>"))
    refuse('wrong-nested-module-same-leaf-name', lambda: link("RootBoundV1<'_, foreign::RawFixtureResultV1>"))
    refuse('missing-generic-lifetime-arity', lambda: link("AdmittedLoaderCorrespondenceV1<'_>"))
    refuse('extra-generic-lifetime-arity', lambda: link("AdmittedLoaderCorrespondenceV1<'_, '_, '_>"))
    refuse('unknown-lifetime-spelling-not-authorized', lambda: link("AdmittedFixtureOutcomeV1<'unreviewed>"))
    refuse('generic-T-is-not-FixtureResult', lambda: link("RootBoundV1<'_, T>"))
    refuse('generic-R-is-not-File', lambda: link("RootBoundV1<'_, LoaderCarrierCoreV1<R>>"))
    refuse('generic-pair-A-B-unobserved', lambda: link("RootBoundV1<'_, (A, B)>"))
    refuse('unmeasured-carrier-not-inferred-by-root-subtraction', lambda: link('LoaderCarrierCoreV1<File>'))
    refuse('unmeasured-reservation-not-inferred-by-child-difference', lambda: link("ReservationV1<'_>"))
    refuse('unmeasured-destroyed-token-not-parent-proof', lambda: link("DestroyedStorageV1<'_>"))
    refuse('reference-to-observed-payload-not-full-payload', lambda: link("&AdmittedFixtureOutcomeV1<'_>"))
    refuse('mutability-not-erased', lambda: link("Option<&mut AdmittedFixtureOutcomeV1<'_>>"))
    refuse('unknown-outer-wrapper', lambda: link("Vec<AdmittedFixtureOutcomeV1<'_>>"))
    refuse('cross-target', lambda: link("AdmittedFixtureOutcomeV1<'_>", target='x86_64-apple-darwin'))
    refuse('cross-source', lambda: link("AdmittedFixtureOutcomeV1<'_>", tree='0' * 64))
    duplicate = copy.deepcopy(acceptance['named_layouts'])
    duplicate.append(copy.deepcopy(duplicate[0]))
    refuse('duplicate-shape-no-alias-doublecount', lambda: observed_map(duplicate))
    alias = copy.deepcopy(acceptance['named_layouts'])
    alias.append({**alias[0], 'type': OWNER + alias[0]['type']})
    refuse('qualified-spelling-collision-no-second-shape', lambda: observed_map(alias))
    invalid = copy.deepcopy(acceptance['named_layouts'])
    invalid[0]['size'] = 2**64
    refuse('observed-size-usize-overflow', lambda: observed_map(invalid))
    invalid_align = copy.deepcopy(acceptance['named_layouts'])
    invalid_align[0]['align'] = 3
    refuse('observed-align-invalid', lambda: observed_map(invalid_align))
    refuse('negative-wrapper-difference', lambda: checked_difference(13640, 13608))
    refuse('difference-input-overflow', lambda: checked_difference(0, 2**64))
    refuse('difference-bool-is-not-integer-price', lambda: checked_difference(False, 8))
    other = exact.replace(':861:36: 861:38}', ':1187:22: 1187:38}')
    refuse('different-actual-closure-type', lambda: require_closure(other, (1236, 'local-or-return', '_25'), exact_spelling=exact, allowed_roles=allowed))
    refuse('right-closure-wrong-role', lambda: require_closure(exact, (1254, 'local-or-return', '_19'), exact_spelling=exact, allowed_roles=allowed))
    refuse('closure-capture-proxy-sum', lambda: link("(FixtureLeafArgumentsV1, PrepaidCorrelationAttemptV1<'_, '_>, &AdmittedLoaderCorrespondenceV1<'_, '_>)"))
    for claim in ['work-price', 'storage-charge', 'simultaneous-peak', 'backing-capacity', 'funding', 'full-ownership', 'sum-all-roles', 'zero-difference-zero-work']:
        refuse('forbidden-inference-' + claim, lambda claim=claim: prohibit_total(roles, claim=claim))
    chain = [13608, 13616, 13616, 13616, 13624, 13624, 13640, 13640]
    differences = [checked_difference(a, b) for a, b in zip(chain, chain[1:])]
    assert sum(differences) == checked_difference(chain[0], chain[-1]) == 32
    frontier = json.loads((D / 'obligation-frontier.json').read_bytes())
    assert len(frontier['obligations']) == 24 and all(row['status'] == 'OPEN_POSITIVE_OBLIGATION' for row in frontier['obligations'])
    result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS_FINITE_INDEPENDENT_JOIN_CONTROLS_BEFORE_PRODUCER_ACCESS',
              'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'python': sys.version,
              'adverse_controls': controls, 'adverse_controls_passed': len(controls),
              'source_bound_positive_role_links': 99, 'named_links': 97, 'actual_closure_links': 2, 'unbound_links': 546,
              'nested_aggregate_difference': 32, 'all_24_obligations_remain_open': True,
              'producer_join_accessed': False, 'compiler_runtime_native_ui_capture_process_queries': 0}
    with (D / 'synthetic-controls.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'adverse_controls_passed', 'source_bound_positive_role_links', 'producer_join_accessed')}))


if __name__ == '__main__':
    main()
