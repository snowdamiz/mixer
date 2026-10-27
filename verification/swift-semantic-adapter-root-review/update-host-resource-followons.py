"""One-shot recording of reviewed source interfaces and failed delivery CI."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

def save_new(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')

def main():
    review_path = ROOT / 'verification/swift-guarded-snapshot-whole-host-work-independent/review.json'
    review = json.loads(review_path.read_bytes())
    assert sha(review_path) == 'ba2dde275b7ab532ee082794af8d08c2426485c6bd138c0bc1ac1489d2040236'
    proposal_path = review_path.parent / 'contract-clarification-proposal.json'
    proposal = json.loads(proposal_path.read_bytes())
    assert sha(proposal_path) == 'ee8b282cd51c5b1b1c0a13bffbdb309b0bd0f0932ad19f28d236b731a0f0df37'
    assert len(proposal['proposed_scope']) == 9
    amendment = {
        'schema': 1, 'at': stamp,
        'status': 'root-selected-source-bound-nine-direct-adapter-logical-unit-clarification',
        'source_tree_sha256': proposal['source_tree_sha256'],
        'host_tree_sha256': proposal['host_tree_sha256'],
        'independent_proposal': str(proposal_path.relative_to(ROOT)),
        'independent_proposal_sha256': sha(proposal_path),
        'exact_export_scope': proposal['proposed_scope'],
        'in_unit': proposal['in_unit'], 'outside_unit': proposal['outside_unit'],
        'actual_callbacks': proposal['actual_callbacks'],
        'selection': 'For only these nine exact source-bound direct adapters, the already charged fixed event plus caller operand/result occurrences and separate downstream owned payload destruction cover the declared logical interface. No additional numeric zero/one price is introduced; no fixed action is subtracted.',
        'unchanged_frozen_interface': 'The frozen 35-symbol model is preserved. A later amended composer must bind this exact receipt and discharge only the nine named obligations, retaining the other twelve callee and two whole-leaf boundary choices.',
        'source_binary_correspondence_complete': False,
        'actual_root_policy_or_grant': False, 'native_runtime_or_GA': False,
    }
    amendment_path = OUT / 'guarded-snapshot-direct-adapter-contract-amendment.json'
    save_new(amendment_path, amendment)
    acceptance = {
        'schema': 1, 'at': stamp,
        'status': 'root-accepted-conditional-source146-whole-work-composition',
        'producer': review['candidate'],
        'independent': {'path': str(review_path.parent.relative_to(ROOT)), 'seal_sha256': '7d18cb048499cac2cb62bec2b4a954d1d032b1fbd950cb6f6941d181debc024b', 'members': 99, 'bytes': 1078416, 'review_sha256': sha(review_path)},
        'observed': review['observed'], 'scope_decisions': review['scope_decisions'],
        'source': review['source'], 'limitations': review['limitations'],
        'separate_direct_adapter_amendment': str(amendment_path.relative_to(ROOT)),
        'separate_direct_adapter_amendment_sha256': sha(amendment_path),
        'frozen_symbols_rewritten': False,
        'all_components_prepaid_before_setup': True,
        'actual_root_policy_or_work_storage_grant': False,
        'actual_fixture_loader_writer_or_healthy_cleanup': False,
        'native_runtime_or_GA': False,
    }
    acceptance_path = OUT / 'guarded-snapshot-whole-host-work-host-acceptance.json'
    save_new(acceptance_path, acceptance)
    work_path, gates_path = ROOT / 'work-graph.json', ROOT / 'gates/ga.json'
    work, gates = json.loads(work_path.read_bytes()), json.loads(gates_path.read_bytes())
    candidate = work['packages'][7]['fixtureCacheStateContractCandidate']
    assert candidate == gates['gates'][1]['fixtureCacheStateContractCandidate']
    terminal_path = ROOT / 'verification/github-delivery-snapshot-host-resource-composition/terminal-ci-status.json'
    terminal = json.loads(terminal_path.read_bytes())
    delivery = candidate['guarded_snapshot_host_resource_delivery']
    delivery['CI'] = {
        'run': terminal['run'], 'attempt': terminal['attempt'], 'status': 'completed',
        'conclusion': 'failure', 'url': terminal['url'], 'terminal': True,
        'observed_jobs': 6, 'jobs_passed': 4, 'jobs_failed': 2,
        'evidence': str(terminal_path.relative_to(ROOT)), 'evidence_sha256': sha(terminal_path),
        'failed_jobs': ['swift', 'swift-cache-state-fixture'],
        'rerun_requested': False,
    }
    delivery['CI_repair'] = {
        'swift_selection': 'test-only-owned-group-fixture-repair-reviewed-local-64-tests-pass-pushed-CI-pending',
        'swift_selection_evidence': 'verification/swift-host-resource-ci-regression-root-review/receipt.json',
        'cache_fixture': 'final-context-case-timeout-retained-isolated-equivalent-fixture-setup-correction-active',
        'cache_fixture_evidence': 'verification/swift-host-resource-ci-cache-state/incident.json',
        'production_timeouts_increased': False,
    }
    boundary = candidate['scalar_cursor_host_acceptance']['real_profile_adapter_preparation']['next_header_preparation']['retained_profile_composition_preparation']['real_binding_preparation']['real_profile_loader_binding']['next_adoption_lane']['guarded_snapshot_export_contract_review']['composition_source_preparation']['bootstrap_host_boundary']
    storage = boundary['host_storage_composition']
    storage.update(status='root-accepted-conditional-source146-storage-lifetime-interface', anonymous_closure_applicability_review='accepted exact original compiler observation with independent source/lifetime review', independent_seal_sha256='7b22aeda5d398877b545a5cb87896bc923937bab68d3e8a236146b1ffc6e3f74', independent_members=41, independent_bytes=335222, independent_methods=20, independent_arithmetic_cases=128, root_acceptance='verification/swift-semantic-adapter-root-review/guarded-snapshot-host-storage-host-acceptance.json', root_acceptance_sha256='9862bbe187dea2e1c6999218604ec43db3d3c9bc28d4fd815615d81dd98df432', product_retention_floor=1899541, late_storage_release_after_payload_and_carrier_destruction=True, actual_P0_paths_native_backing_and_caller_binding_pending=True)
    binary = boundary['resource_binary_correspondence']
    binary.update(status='frozen-compiled-resource-candidate-independent-review-active', producer_seal_sha256='58f49d3bcc844678bef604bc4989e81b2bfea758b300ca3158b229a510018f1d', producer_members=116, producer_bytes=2151908, root_release='verification/swift-semantic-adapter-root-review/guarded-snapshot-resource-binary-frozen-release.json', independent_owner='/root/swift_resource_binary_independent', independent_ownership='verification/swift-guarded-snapshot-resource-binary-independent')
    composed = boundary['whole_host_work_composition']
    composed.update(status='root-accepted-conditional-source146-whole-work-composition', producer_seal_sha256='95c1a3087b36996dc06e8411f97e3ebce2610120f9ac742326824a52ab9c63ca', independent_seal_sha256='7d18cb048499cac2cb62bec2b4a954d1d032b1fbd950cb6f6941d181debc024b', independent_assertions=33493, independent_adverse_controls=246, known_constant=895084428322997895, frozen_unresolved_symbols=35, root_acceptance=str(acceptance_path.relative_to(ROOT)), root_acceptance_sha256=sha(acceptance_path), separate_direct_adapter_amendment=str(amendment_path.relative_to(ROOT)), separate_direct_adapter_amendment_sha256=sha(amendment_path), amended_composer_pending=True)
    boundary['native_interface_bounds'] = {
        'status': 'frozen-source-native-interface-candidate-independent-review-active',
        'ownership': 'verification/swift-guarded-snapshot-native-interface-bounds',
        'producer_seal_sha256': 'd02b6602bc7c4419d908db90a8e67d24b1dd3a46f9c9d2c2bb9158c70229b60f',
        'producer_members': 115, 'producer_bytes': 1255928,
        'root_release': 'verification/swift-semantic-adapter-root-review/guarded-snapshot-native-interface-frozen-release.json',
        'independent_owner': '/root/swift_native_interface_independent',
        'independent_ownership': 'verification/swift-guarded-snapshot-native-interface-independent',
        'positive_storage_amendment_selected': False, 'whole_grant': False,
    }
    gates['gates'][1]['fixtureCacheStateContractCandidate'] = candidate
    work_path.write_text(json.dumps(work, indent=2) + '\n')
    gates_path.write_text(json.dumps(gates, indent=2) + '\n')
    paragraph = 'Source146 resource and storage checkpoint `c4d04e5` is pushed with 433 selected paths and seven frozen packets. [CI](https://github.com/snowdamiz/mixer/actions/runs/40507305688) finished on attempt one with four jobs passing and two failing. The Swift selection test could not confirm disappearance of its orphaned test group; a test-only owned-group correction now passes all 64 local host tests and two fresh root controls, with production policy unchanged. The cache-state fixture reached its final malformed-context case before its 60-second deadline; exact inputs and confirmed cleanup are retained while an equivalent fixture-setup correction is qualified. Storage lifetimes and the conditional whole-work composition now have bounded independent acceptance. The latter retains 35 symbolic inputs; a separate exact nine-adapter clarification is selected for a future amended composer. Compiled-resource and native-interface candidates are frozen and under independent review. Canonical product source remains at `b4a9fd4`; whole-host funding, actual fixture/writer execution, native runtime and GA acceptance remain pending.'
    for name in ['PLAN.md', 'STATUS.md']:
        path = ROOT / name
        text = path.read_text()
        start = text.index('Source146 resource and storage checkpoint `c4d04e5`')
        end = text.index('\n\n', start)
        text = text[:start] + paragraph + text[end:]
        text = text.replace('The 30-member storage/lifetime candidate is frozen and under independent review. Two other active lanes resolve remaining installed-library bodies and compose actual host work costs.', 'The 30-member storage/lifetime candidate now has bounded root acceptance after 20 independent methods and 128 arithmetic cases. The complete symbolic work composition has bounded acceptance after 33,493 independent assertions and 246 adverse cases. Frozen compiled-resource and native-interface candidates remain under independent review; the nine direct-adapter contract clarification does not rewrite the frozen work model or select a grant.')
        path.write_text(text)
    print(json.dumps({'work_acceptance_sha256': sha(acceptance_path), 'nine_adapter_amendment_sha256': sha(amendment_path), 'CI': delivery['CI']}))

if __name__ == '__main__':
    main()
