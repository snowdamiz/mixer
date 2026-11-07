#!/usr/bin/env python3
"""Seal the bounded independent review while retaining the rejected producer proof."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from admit_frozen import verify_seal

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
DOC = ROOT/'docs/swift-ordered-retention-analyzer-envelope-accounting-review.md'
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

def main():
    if (OWN/'seal.json').exists() or (OWN/'seal.sha256').exists(): raise ValueError('review already frozen')
    producer = verify_seal()
    probe = json.loads((OWN/'commands/accounting-1/receipt.json').read_bytes())
    ledger = json.loads((OWN/'commands/source-ledger-1/receipt.json').read_bytes())
    findings = json.loads((OWN/'findings.json').read_bytes())
    assert probe['probe_methods_passed'] == 7
    assert ledger['checks']['prior_read_allocation_sufficient'] is False
    assert len(findings['findings']) == 1
    selection = OWN/'coordination/root-leaf-accounting-reconciliation-selection.json'
    assert sha(selection.read_bytes()) == '9b8de2ab2c7a8d3e72dbb934aec046e22473e3e20a1fee187ef9053534f2b362'
    receipt = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'frozen-independent-accounting-finding-revision-required',
        'scope': 'resource/debit accounting only for the exact separate fixture envelope; complementary public File reviewer is separate',
        'producer_freeze': producer,
        'admission_receipt': 'commands/frozen-admission-1/receipt.json',
        'preaccess_receipts': ['commands/preaccess-1/result.json', 'commands/preaccess-2/result.json'],
        'source_envelope_sha256': '80eb9830ed78b1122ff3ec0723e1ce20afb46fd4a4e5abf80c60c4883a65a84e',
        'source_analyzer_sha256': '1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b',
        'source_accounting_sha256': '3348b6c06b5e5511018840070c2d1c2b3cbe691ffe83adcab3e931bc64ea0d9d',
        'own_document_sha256': sha(DOC.read_bytes()),
        'host_probe_methods_passed': 7,
        'host_probe_receipt': 'commands/accounting-1/receipt.json',
        'source_ledger_receipt': 'commands/source-ledger-1/receipt.json',
        'findings': [{'id': 'A1', 'priority': 'P1', 'source_lines': [136, 139], 'minimum_caller_scalar_ops': 108, 'named_caller_scalar_capacity': 48, 'affected': ['prior-read subtotal27', 'leaf upper111', 'G36', 'combined proof']}],
        'supported_scoped_observations': ['26 complete host type layouts', 'one retained candidate and exact footprint controls', 'prepaid failure ordering and no mutation controls', 'preflight and atomic charge edges', 'truthful prepaid decode-failure/latch-skip debit', 'declared logical arithmetic24656 within assigned41984/65536', 'accepted framing source exact prefix'],
        'no_memory_ceiling_breach_identified': True,
        'declared_arithmetic_does_not_accept_complete_source_proof': True,
        'numeric_B_W_T_F_G_or_leaf_upper_accepted': False,
        'combined_lifetime_qualified': False,
        'combined_debit_preflight_qualified': False,
        'product_acceptance': False, 'fullReplayAccepted': False, 'storedPrefixValidated': False,
        'semanticMetricsValid': False, 'ga_gate_promotions': 0,
        'producer_tests_runners_or_forbidden_hosted_executed': False,
        'native_capture_process_or_device_discovery': False,
        'cleanup': probe['cleanup'],
        'withheld': ['amended complete source ledger and separately prepaid guard', 'combined numeric/lifetime qualification', 'semantic replay and real binding/custody', 'full target/compiler/native/device/signing/store/customer/operations/published FieldLog/GA'],
    }
    write_json(OWN/'review-receipt.json', receipt)
    files = sorted([DOC] + [p for p in OWN.rglob('*') if p.is_file() and p.name not in ['seal.json', 'seal.sha256']])
    # The admitted producer seal is an input and must remain in this review seal.
    admitted_seal = OWN/'commands/frozen-admission-1/inputs/seal.json'
    if admitted_seal not in files: files.append(admitted_seal)
    admitted_sha = OWN/'commands/frozen-admission-1/inputs/seal.sha256'
    if admitted_sha not in files: files.append(admitted_sha)
    files.sort()
    members = []
    for path in files:
        data = path.read_bytes()
        if path.suffix in ['.md', '.py', '.rs']:
            assert not any(line.endswith((' ', '\t')) for line in data.decode().splitlines()), str(path)
        if path.suffix == '.json': json.loads(data)
        members.append({'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)})
    assert verify_seal() == producer
    seal = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'scope': receipt['scope'], 'status': receipt['status'], 'members': members,
            'excluded': [str((OWN/'seal.json').relative_to(ROOT)), str((OWN/'seal.sha256').relative_to(ROOT))],
            'product_acceptance': False, 'combined_debit_preflight_qualified': False}
    write_json(OWN/'seal.json', seal)
    digest = sha((OWN/'seal.json').read_bytes())
    (OWN/'seal.sha256').write_text(digest+'\n')
    print(json.dumps({'status': receipt['status'], 'seal_sha256': digest, 'members': len(members), 'bytes': sum(x['bytes'] for x in members), 'findings': 1, 'host_probe_methods_passed': 7}, sort_keys=True))

if __name__ == '__main__': main()
