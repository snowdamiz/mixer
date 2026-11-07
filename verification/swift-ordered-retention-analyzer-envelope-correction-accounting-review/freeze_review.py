#!/usr/bin/env python3
"""Freeze proposal1 accounting findings, not numeric or implementation selection."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from admit_proposal import verify_proposal
from prepare_baseline import verify_old_seals

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
DOC = ROOT/'docs/swift-ordered-retention-analyzer-envelope-correction-accounting-review.md'
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
    assert not (OWN/'seal.json').exists() and not (OWN/'seal.sha256').exists()
    proposal = verify_proposal(); old = verify_old_seals()
    findings = json.loads((OWN/'findings.json').read_bytes())
    audit = json.loads((OWN/'commands/source-audit-2/receipt.json').read_bytes())
    layout = json.loads((OWN/'commands/proposal-layout-1/receipt.json').read_bytes())
    crosswalk = json.loads((OWN/'framing22-crosswalk.json').read_bytes())
    assert len(findings['findings']) == 2 and audit['all_115_row_arithmetic_checks_pass']
    assert audit['early_finalization_prepaid_coverage_sufficient'] is False
    assert layout['status'] == '32-actual-layouts-pass-unit-result40-proposal-source-audit-separate'
    assert crosswalk['accepted_source_exact_prefix']
    receipt = {
        'schema':1,'at':datetime.now(timezone.utc).isoformat(),
        'status':'proposal1-independent-accounting-review-frozen-revision-required',
        'scope':'immutable operation/numeric proposal1 source audit with limited actual-layout probe only',
        'proposal':proposal,'original_seals_verified':old,
        'source_envelope_sha256':'e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535',
        'operation_ledger_sha256':'cca5739c3447ed6180f5f93979465931193e0ad81a2be90d2aebdce30751ccff',
        'numeric_proposal_sha256':'1e130be69cc05683f5dbac9308f231b15164aed5d44771fa0134a96f650196ec',
        'own_document_sha256':sha(DOC.read_bytes()),
        'row_arithmetic_checks_passed':115,'fresh_actual_type_layouts_passed':32,
        'layout_receipt':'commands/proposal-layout-1/receipt.json',
        'source_audit_receipt':'commands/source-audit-2/receipt.json',
        'reviewer_failed_attempt_retained':'commands/source-audit-1/receipt.json',
        'inherited_framing22_crosswalk':'framing22-crosswalk.json',
        'proposed_arithmetic_reconciled':{'leaf_upper':425,'W':24,'B':471,'G':112,'T':42,'setup_actual_upper':329,'setup_selected':534,'finish':47,'F':29},
        'findings':[
            {'id':'C1','priority':'P1','title':'Early-error finalize/project lacks proposed named prepaid funding','source_lines':[300,348,353,375],'declared_early_path_upper':13,'finish_reservation_success':False},
            {'id':'C2','priority':'P2','title':'Complete unit Results labeled32 instead of actual40','rows':['BR01','BS01','BP01','S01','S03','F03'],'copy_group_change_inferred':False}
        ],
        'no_new_private_leaf_undercount_identified_in_bounded_source_rows':True,
        '425_source_upper_is_not_a_minimum_lower_bound':True,
        'no128_or_B471_sufficiency_inferred':True,
        'cost_dependent_runtime_replay':False,
        'historical_seven_probes_promoted_to_new_code_pass':False,
        'numeric_values_selected':False,'implementation_accepted':False,
        'combined_lifetime_qualified':False,'combined_debit_preflight_qualified':False,
        'product_acceptance':False,'fullReplayAccepted':False,'storedPrefixValidated':False,'ga_gate_promotions':0,
        'producer_scripts_or_tests_executed':False,'native_capture_process_or_device_discovery':False,
        'cleanup':layout['cleanup'],
        'withheld':['C1 all-path prepaid funding correction','C2 complete type annotation correction','new frozen source/numeric proposal','explicit root contract/numeric selection','cost-dependent replay and finite oracle against selected amended contract','combined lifetime qualification','semantic/custody/target/native/device/signing/store/FieldLog/GA']
    }
    write_json(OWN/'review-receipt.json',receipt)
    excluded={OWN/'seal.json',OWN/'seal.sha256'}
    files=sorted([DOC]+[p for p in OWN.rglob('*') if p.is_file() and p not in excluded])
    members=[]
    for path in files:
        raw=path.read_bytes()
        if path.suffix in ['.py','.rs','.md']: assert not any(line.endswith((' ','\t')) for line in raw.decode().splitlines()),str(path)
        if path.suffix=='.json': json.loads(raw)
        members.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)})
    assert verify_proposal()==proposal and verify_old_seals()==old
    seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'scope':receipt['scope'],'status':receipt['status'],'members':members,
          'excluded':[str(p.relative_to(ROOT)) for p in sorted(excluded)],'numeric_values_selected':False,'implementation_accepted':False}
    write_json(OWN/'seal.json',seal)
    digest=sha((OWN/'seal.json').read_bytes());(OWN/'seal.sha256').write_text(digest+'\n')
    print(json.dumps({'status':receipt['status'],'seal_sha256':digest,'members':len(members),'bytes':sum(m['bytes'] for m in members),'findings':2,'row_arithmetic_checks_passed':115,'fresh_type_layouts':32},sort_keys=True))
if __name__=='__main__':main()
