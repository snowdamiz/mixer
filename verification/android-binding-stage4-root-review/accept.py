#!/usr/bin/env python3
"""Accept only the independently reviewed private host implementation scope."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
checked = 0


def check(path, expected):
    global checked
    actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError('Changed bound file: ' + str(path))
    checked += 1


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


review_path = 'verification/android-binding-final-host-review/review.json'
check(review_path, '8938ad3c48bb51b222cd263fb8f399c6e4b91b14335a3d69f4a37feea897fffa')
review = json.loads((ROOT / review_path).read_text())
if review['blocking_findings'] or review['decision'] != 'accept_qualified_private_host_checkpoint_and_local_fresh_CI_only':
    raise RuntimeError('Independent review did not accept this scope')
for path, expected in review['files'].items():
    check(path, expected)
artifact_audit_path = 'verification/android-binding-final-host-review/artifact-audit.json'
artifact_audit = json.loads((ROOT / artifact_audit_path).read_text())
for path, expected in artifact_audit['bindings'].items():
    check(path, expected)
root_audit_path = 'verification/android-binding-stage4-root-review/binding-audit.json'
root_audit = json.loads((ROOT / root_audit_path).read_text())
for path, expected in root_audit['files'].items():
    check(path, expected)
receipt = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'decision': 'accepted_private_host_implementation_and_local_fresh_CI_scope_only',
    'accountable_integrator': 'root', 'independent_reviewer': 'android_binding_final_host_review',
    'root_binding_checks': checked,
    'review': review_path, 'review_sha256': digest(review_path),
    'root_binding_audit': root_audit_path, 'root_binding_audit_sha256': digest(root_audit_path),
    'producer_evidence': 'verification/android-binding-stage4/evidence.json',
    'producer_evidence_sha256': review['producer_evidence_sha256'],
    'canonical_source_manifest_sha256': review['canonical_manifest_sha256'],
    'fresh_CI_receipt': 'verification/android-binding-ci/qualified-1/receipt.json',
    'fresh_CI_receipt_sha256': review['fresh_CI_receipt_sha256'],
    'accepted': [
        'Private host binding uses actual Task.value, exact C endpoint/facade return fences and real reservation-owned resource destruction.',
        'Closed host evidence remains disjoint from Apple/common and future JNI authority; normal supported routes remain unchanged.',
        'Final fault-join delta follows the separately reviewed control-local versus admission-serialized C reclaim boundary.',
        'Fresh SDK/dependency/C source builds pass39 ordinary scenarios per Debug/Release/TSan; exact archives, headers and clean pinned checkout revisions are checked.',
        'Independent source/binding review, targeted lifecycle replays and optimized-Python provenance rejection checks pass.',
    ],
    'pending': review['pending'],
    'full_original_dynamic_matrix_pass': False,
    'native_android_authority': False, 'release_authority': False, 'ga_gate_pass': False,
    'next_step': 'A separate bounded JNI/Java type and verification contract may be designed. Implementation and signed core/native integration require their own coordinated contracts and evidence.',
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
output = HERE / 'acceptance.json'
if output.exists():
    raise RuntimeError('Refusing to overwrite acceptance evidence')
output.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'acceptance': str(output.relative_to(ROOT)), 'binding_checks': checked,
                  'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))
