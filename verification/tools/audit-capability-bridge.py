#!/usr/bin/env python3
"""Root integration audit of frozen implementation, independent review and observations."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / 'verification/capability-bridge-review'
ACTIVE = ROOT / 'experimental-capability-runtime/verification/2026-10-23-active-payload-4'
OWNER = ROOT / 'experimental-capability-runtime/verification/2026-10-23-candidate-5'
ACTIVE_SHA = 'b94b555e81a2806dba39e22d3ff7212776aa036b54851f9d0a7849e316f8208c'
REVIEW_SHA = 'c7ee5fa7495655611633685aeebbe193ed843aa4ee3c14d4466553dc11ad19fd'


def require(ok, detail):
    if not ok:
        raise RuntimeError(detail)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def manifest(path, base, expected_sha):
    require(sha(path) == expected_sha, 'manifest digest: ' + str(path))
    rows = {}
    for line in path.read_text().splitlines():
        digest, name = line.split('  ', 1)
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts, 'relative manifest path')
        require(not {'.build', '.swiftpm', '__pycache__'}.intersection(relative.parts), 'cache in manifest')
        require(name not in rows and sha(base / name) == digest, 'manifest bytes: ' + name)
        rows[name] = digest
    return rows


def main():
    # Recheck the live55-file freeze and immutable exports, not merely the prior report.
    subprocess.run([sys.executable, str(ROOT / 'verification/tools/audit-capability-bridge-owner.py')], check=True, stdout=subprocess.DEVNULL)
    owner = read(OWNER / 'receipt.json')
    require(sha(REVIEW / 'final-receipt.json') == REVIEW_SHA, 'independent review freeze')
    review = read(REVIEW / 'final-receipt.json')
    require(review['status'] == 'bounded independent review passed' and review['open_source_findings'] == [], 'independent approval incomplete')
    require(review['owner_receipt_sha256'] == sha(OWNER / 'receipt.json'), 'review owner binding')
    require(review['source_manifest_sha256'] == owner['sourceManifestSHA256'], 'review source binding')
    source = manifest(REVIEW / 'review-source.sha256', REVIEW, review['review_source_manifest_sha256'])
    evidence = manifest(REVIEW / 'evidence-manifest.sha256', REVIEW, review['evidence_manifest_sha256'])
    require(len(source) == review['review_source_files'] and len(evidence) == review['evidence_files'], 'review manifest counts')
    for name, key in [('public-receipt.json', 'public_receipt_sha256'), ('internal-receipt.json', 'derived_receipt_sha256'), ('derived-map.json', 'derived_mutation_map_sha256'), ('owner-audit.json', 'owner_audit_sha256')]:
        require(sha(REVIEW / 'candidate-5' / name) == review[key], 'nested review binding: ' + name)
    public = read(REVIEW / 'candidate-5/public-receipt.json')
    for name, digest in public['review_input_sha256'].items():
        require(sha(REVIEW / name) == digest, 'current public harness: ' + name)
    derived = read(REVIEW / 'candidate-5/derived-map.json')
    derived_root = Path(public['workspace']) / 'derived'
    for name, digest in derived['derived_source_sha256'].items():
        require(sha(derived_root / name) == digest, 'actual derived source: ' + name)
    for name, digest in derived['review_input_sha256'].items():
        require(sha(REVIEW / name) == digest, 'derived harness input: ' + name)
    bindings = read(REVIEW / 'candidate-5/owner-audit.json')['bindings']
    for entry in bindings:
        path = Path(entry['path'])
        require(sha(path) == entry['sha256'] and path.stat().st_size == entry['bytes'], 'independent owner audit binding')
    counts = {}
    for command in review['commands']:
        path = ROOT / command['log']
        require(command['exit_code'] == 0 and sha(path) == command['sha256'], 'review command: ' + command['name'])
        text = path.read_text()
        require('WARNING: ThreadSanitizer' not in text, 'sanitizer diagnostic')
        if 'observed_test_count' in command:
            expected = command['observed_test_count']
            observed = re.findall(r'Executed (\d+) tests?, with 0 failures', text)
            require(observed and {int(n) for n in observed} == {expected}, 'actual XCTest count: ' + command['name'])
            counts[command['name']] = expected
    require(sum(counts.values()) == review['counts']['final_test_case_executions'] == 76, 'independent test executions')
    for record in review['historical_attempts_preserved']:
        require(sha(REVIEW / record['path']) == record['sha256'], 'historical review attempt')

    require(sha(ACTIVE / 'receipt.json') == ACTIVE_SHA, 'active observation freeze')
    active = read(ACTIVE / 'receipt.json')
    require(active['status'] == 'scoped_observations_passed', 'active observation failed')
    require(active['baseReceiptSHA256'] == review['owner_receipt_sha256'], 'active observation base')
    for key in ['exportUnchanged', 'baseReceiptUnchanged', 'baseProductionCurrentUnchanged', 'nativeArtifactsUnchanged']:
        require(active[key], 'observation changed: ' + key)
    active_inputs = manifest(ACTIVE / 'source-manifest.sha256', ROOT, active['sourceManifestSHA256'])
    require(active_inputs == active['source'] and len(active_inputs) == 60, 'active source inventory')
    for name, digest in active_inputs.items():
        require(sha(Path(active['frozenExport']) / name) == digest, 'active immutable source')
    for name, digest in owner['source'].items():
        require(active_inputs[name] == digest, 'active vs final5 source')
    for name, digest in active['nativeArtifacts'].items():
        require(sha(Path(owner['stageRoot']) / name) == digest, 'active native artifact')
    for binary in active['binaries'].values():
        path = Path(binary['path'])
        require(sha(path) == binary['sha256'] and path.stat().st_size == binary['bytes'], 'active observer binary')
    observations = {}
    for command in active['commands']:
        path = ACTIVE / command['log']
        require(command['exitCode'] == 0 and sha(path) == command['logSHA256'], 'active command')
        if 'observations' in command:
            actual = [json.loads(row) for row in re.findall(r'ACTIVE_PAYLOAD_OBSERVATION (.+)', path.read_text())]
            require(actual == command['observations'] and len(actual) == 1, 'observation log parse')
            entry = actual[0]
            require(entry['acceptedCTakes'] == entry['acknowledgements'] == 8 and entry['drainedConfirmed'], 'active drain')
            require(entry['guestWrapperBytesTotal'] == 525976 and entry['payloadDecodedBytesEach'] == 49152, 'active payloads')
            observations[command['name']] = entry
    require(len(observations) == 4, 'four independent observer processes')
    report = {
        'schema': 1, 'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'script_sha256': sha(Path(__file__)), 'owner_receipt_sha256': sha(OWNER / 'receipt.json'),
        'review_receipt_sha256': sha(REVIEW / 'final-receipt.json'), 'active_receipt_sha256': ACTIVE_SHA,
        'source_manifest_sha256': owner['sourceManifestSHA256'],
        'matched': {'implementation_inputs': 55, 'active_inputs': 60, 'review_sources': len(source), 'review_evidence_files': len(evidence), 'independent_owner_bindings': len(bindings), 'independent_test_executions': sum(counts.values())},
        'independent_test_counts': counts, 'active_payload_observations': observations,
        'annotation': 'Active receipt scope prose still says candidate3; its baseReceipt, source manifest, all55 matching inputs and Ownership00601bbf prove this replay uses corrected candidate5. Original receipt bytes preserved.',
        'result': 'Qualified for a separate experimental host bridge checkpoint; root matched frozen inputs, exact archives, review outputs, failure regressions and scoped observations.',
        'limitations': list(dict.fromkeys(owner['limitations'] + review['limitations'] + active['limitations']))}
    output = ROOT / 'verification/capability-bridge-integration-2026-10-23.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['matched'], indent=2))


if __name__ == '__main__':
    main()
