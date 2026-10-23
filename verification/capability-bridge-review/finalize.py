#!/usr/bin/env python3
"""Validate and freeze review-owned evidence; never build or modify production."""
from pathlib import Path
import datetime
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'candidate-5'
PIN = '070f626acd4cfc99ec2bdeb9b1e1dc45da228548d3f6458fb8fbe1b7bbca4b4d'


def sha(data): return hashlib.sha256(data).hexdigest()
def require(value, message):
    if not value: raise RuntimeError(message)

def main():
    require(not (HERE / 'final-receipt.json').exists(), 'preserve previous final receipt')
    public = json.loads((OUT / 'public-receipt.json').read_text())
    internal = json.loads((OUT / 'internal-receipt.json').read_text())
    owner = json.loads((OUT / 'owner-audit.json').read_text())
    require(public['status'].startswith('public checks passed') and internal['status'].startswith('internal checks passed'), 'green review commands')
    require(public['source_manifest_sha256'] == internal['source_manifest_sha256'] == owner['source_manifest_sha256'] == PIN, 'single final source freeze')
    manifest = (OUT / 'source-manifest.sha256').read_bytes()
    require(sha(manifest) == PIN, 'final source manifest pin')
    source = Path(public['immutable_owner_export']); copied = Path(public['public_source_copy'])
    mapping_raw = (OUT / 'derived-map.json').read_bytes(); mapping = json.loads(mapping_raw)
    require(sha(mapping_raw) == internal['derived_map_sha256'], 'exact executed derived map')
    derived = Path(public['workspace']) / 'derived'
    require(mapping['input_manifest_sha256'] == PIN, 'derived input pin')
    for line in manifest.decode().splitlines():
        digest, relative = line.split('  ',1)
        for path in [ROOT / relative, source / relative, copied / relative]: require(sha(path.read_bytes()) == digest, 'final immutable source ' + relative)
        expected = mapping['derived_source_sha256'].get(relative, digest)
        require(sha((derived / relative).read_bytes()) == expected, 'exact executed derived production ' + relative)
    for relative, digest in mapping['derived_source_sha256'].items(): require(sha((derived / relative).read_bytes()) == digest, 'derived injection hash')
    for relative, digest in public['review_input_sha256'].items(): require(sha((HERE / relative).read_bytes()) == digest, 'public tested source unchanged')
    for relative, digest in mapping['review_input_sha256'].items(): require(sha((HERE / relative).read_bytes()) == digest, 'internal tested source unchanged')
    require(sha((HERE / 'InternalHarness/ReviewBridgeControls.swift').read_bytes()) == mapping['derived_source_sha256']['experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/ReviewBridgeControls.swift'], 'tested controls unchanged')
    require(sha((HERE / 'make-derived-review.py').read_bytes()) == mapping['script_sha256'], 'tested derivation helper unchanged')
    for receipt, driver in [(public,'run-public.py'),(internal,'run-internal.py')]:
        require(sha((HERE / driver).read_bytes()) == receipt['driver_sha256'], 'tested runner unchanged')
    require(sha((ROOT / public['archive']['path']).read_bytes()) == public['archive']['sha256'], 'native archive remains exact')
    stage = ROOT / 'experimental-capability-runtime/build-verification/local/qualified-final-v3/host/include'
    for name, digest in public['headers_sha256'].items(): require(sha((stage / name).read_bytes()) == digest, 'native header remains exact')
    for binding in owner['bindings']: require(sha(Path(binding['path']).read_bytes()) == binding['sha256'], 'owner audited binding unchanged')
    counts = {'public-debug':10,'public-release':10,'ordering-debug':14,'ordering-release':14,
              'metadata-fault-debug':1,'metadata-fault-release':1,'constructor-fault-debug':1,'constructor-fault-release':1,
              'public-tsan':10,'ordering-tsan':14}
    commands = []
    for receipt in [public,internal]:
        for command in receipt['commands']:
            require(command['exit_code'] == 0, 'nonzero final review command')
            data = (ROOT / command['log']).read_bytes(); require(sha(data) == command['sha256'], 'raw review log pin')
            if command['name'] in counts:
                summaries = re.findall(rb'Executed (\d+) tests?, with (\d+) failures?', data)
                require(summaries and all(int(n) == counts[command['name']] and int(f) == 0 for n,f in summaries), 'XCTest raw count ' + command['name'])
                if command['name'] == 'ordering-tsan': require(b'WARNING: ThreadSanitizer' not in data, 'TSan warning')
                command = dict(command, observed_test_count=counts[command['name']])
            commands.append(command)
    require(len(commands) == 14, '14 review tool/test commands')
    # Preserve every earlier attempt: validate log pins without upgrading any failure.
    historical = []
    for path in sorted((HERE / 'candidate-1').rglob('*receipt.json')):
        receipt = json.loads(path.read_text())
        for command in receipt.get('commands',[]):
            log = ROOT / command['log']; require(sha(log.read_bytes()) == command['sha256'], 'preserved historical log')
        historical.append({'path':str(path.relative_to(HERE)),'sha256':sha(path.read_bytes()),'status':receipt.get('status')})
    # Authored review files only; outputs/logs/snapshots are bound in a separate manifest.
    authored = [p for p in HERE.iterdir() if p.is_file() and p.suffix in ['.swift','.py','.mjs','.md']]
    for folder in ['PublicHarness','InternalHarness','fixtures']:
        authored += [p for p in (HERE / folder).rglob('*') if p.is_file()]
    excluded_components = {'.build', '.swiftpm', '__pycache__'}
    authored = sorted(p for p in set(authored) if not excluded_components.intersection(p.relative_to(HERE).parts))
    source_manifest = ''.join(sha(p.read_bytes())+'  '+str(p.relative_to(HERE))+'\n' for p in authored).encode()
    (HERE / 'review-source.sha256').write_bytes(source_manifest)
    evidence = sorted(p for p in HERE.rglob('*') if p.is_file() and not excluded_components.intersection(p.relative_to(HERE).parts) and p.name not in ['final-receipt.json','evidence-manifest.sha256'])
    evidence_manifest = ''.join(sha(p.read_bytes())+'  '+str(p.relative_to(HERE))+'\n' for p in evidence).encode()
    (HERE / 'evidence-manifest.sha256').write_bytes(evidence_manifest)
    receipt = {'status':'bounded independent review passed','completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source_manifest_sha256':PIN,'production_source_files':55,'native_revision':public['native_revision'],
               'native_archive':public['archive'],'native_headers_sha256':public['headers_sha256'],
               'review_source_files':len(authored),'review_source_manifest_sha256':sha(source_manifest),
               'evidence_files':len(evidence),'evidence_manifest_sha256':sha(evidence_manifest),
               'public_receipt_sha256':sha((OUT/'public-receipt.json').read_bytes()),
               'derived_receipt_sha256':sha((OUT/'internal-receipt.json').read_bytes()),
               'derived_mutation_map_sha256':sha(mapping_raw),'owner_audit_sha256':sha((OUT/'owner-audit.json').read_bytes()),
               'owner_receipt_sha256':owner['owner_receipt_sha256'],'commands':commands,
               'historical_attempts_preserved':historical,'open_source_findings':[],
               'resolved_finding':{'candidate_1':'normal late take/close drained but recorded invalid_arguments',
                                   'failing_probe':'candidate-1/internal-replay-3/internal-receipt.json',
                                   'candidate_5':'checked closed status3 explained at drain/wake/both remaining queries; ack/metadata/status4 handling preserved',
                                   'final_regression_and_related_close_cases':4},
               'counts':{'public_unique_cases':10,'derived_main_unique_cases':14,'separate_metadata_case':1,'separate_constructor_case':1,
                         'final_test_case_executions':sum(counts.values())},
               'scope':'Host unmodified public tests and separately labelled scheduling/metadata derivations; owner cross-build and builder receipts audited without duplicate builds',
               'limitations':['Swift/C-shim TSan only; pinned Rust/system code uninstrumented',
                              'No physical platforms, credentials, trust changes, pushes or production edits',
                              'No hard real-time/global-process cap/no-OOM/no-unwind/rollback/OS or Task destruction claim',
                              'TLS audited evidence is normal-trust rejection only; successful trusted fixture remains pending',
                              'No verified activation, immutable external dogfood, identity, publication or GA'],
               'integration_or_commit_approval':'root-controlled; this receipt does not publish or authorize production integration'}
    (HERE / 'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'source_files':len(authored),'evidence_files':len(evidence),
                      'final_receipt_sha256':sha((HERE/'final-receipt.json').read_bytes()),'review_source_manifest_sha256':sha(source_manifest),
                      'evidence_manifest_sha256':sha(evidence_manifest)}))

if __name__ == '__main__': main()
