#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def read(name):return json.loads((HERE/name).read_text())
frozen=read('frozen-runs.json');regressions=read('independent-regressions.json');probes=read('independent-probes.json');privacy=read('internal-privacy.json');legacy=read('independent-legacy-normalized.json')
assert len(frozen['commands'])==36 and frozen['source_unchanged']
assert all(c['exit_code']==0 and c['exact_one_passed'] for c in frozen['commands'])
assert len(regressions['commands'])==4 and regressions['source_unchanged']
assert all(c['exit_code']==0 and c['passed']==c['expected'] for c in regressions['commands'])
assert len(probes['commands'])==2 and all(c['exit_code']==0 and c['passed']==7 for c in probes['commands'])
assert len(privacy['commands'])==12 and all(c['expected_outcome'] for c in privacy['commands'])
assert len(legacy['comparisons'])==4 and all(c['equal'] for c in legacy['comparisons'])
for target,meta in probes['overlays'].items():
    assert sha((HERE/'tree'/target).read_bytes())==meta['derived_sha256']
    assert sha((HERE/meta['test_include']).read_bytes())==meta['test_include_sha256']
names=[p for p in HERE.iterdir() if p.is_file() and p.name!='candidate-1-review-receipt.json']
bindings={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(names)}
receipt={'schema':'mixer-independent-private-swift-cache-review-v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision':'behavioral_evidence_passed_accounting_and_complete_named_assertion_acceptance_withheld',
    'candidate':1,'producer_receipt_sha256':'90d80a9b29aca64f07bcda56196b29523dbf1635fedb8d393f807591e5c43fdd',
    'baseline_revision':'39199ae5475de5d03926807ce60add5dcb0741c2','frozen_source_manifest_sha256':'d85f853acfb173e8b75c931ffc09d875c47a0dfcb2bf44eb2c28bff6a21d5fa9',
    'full_vm_inputs':len(read('full-vm-input-manifest.json')),'exact_named_commands':36,'all_feature_tests_per_mode':340,'minimal_swift_tests_per_mode':226,
    'additional_behavioral_probes_per_mode':6,'additional_measurement_probes_per_mode':1,'privacy_cases_per_mode':6,
    'legacy_observations_per_mode':[122,126],
    'blocking_findings':['Incomplete construction/operation/permanent-release type and scalar maps','Unassigned early bound-calculation arrays/iterators before enlargement','Coverage labels exceed assertions in several named test bodies'],
    'selected_final_cleanup_helper_boundary':'source-reviewed and fault-probed; small40-byte transfer whole-slot assignment structurally valid; composed executor pending',
    'root_deadline_test_repair':'source-reviewed exact reached marker and calls==ordinal; bounded early-expiry-only retry; complete suites pass',
    'bound_artifacts':bindings,
    'scope_limits':{'guest_target_instantiated_initialized_or_invoked':False,'devices_discovered_or_run':False,'product_source_written_by_reviewer':False,'public_execution_route_added':False,'publications_or_commits':False,'ga_qualification':False,'composed_executor_qualified':False},
    'candidate2':'root-authorized producer repair; requires new source freeze and independent review'}
(HERE/'candidate-1-review-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'decision':receipt['decision'],'receipt_sha256':sha((HERE/'candidate-1-review-receipt.json').read_bytes()),'bound_artifacts':len(bindings)},indent=2))
