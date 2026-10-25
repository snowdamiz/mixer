#!/usr/bin/env python3
"""Seal only this review lane and its assigned report; no source or Git writes."""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda data: hashlib.sha256(data).hexdigest()
stable = lambda value: (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
paths = sorted([p for p in HERE.rglob('*') if p.is_file() and p.name not in ['handoff.json', 'handoff.sha256']] + [ROOT / 'docs/apple-passive-lifecycle-review.md'])
members = {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in paths}
host = json.loads((HERE / 'host-receipt.json').read_bytes())
assert host['passed'] and host['ownedHostScratchRemoved'] and not (HERE / '.host-work').exists()
handoff = {'schema': 1, 'status': 'accepted-source-and-finite-foundation-host-prerequisite',
    'sourceContextRevision': host['sourceContextRevision'], 'candidateHandoffSHA256': host['candidateHandoffSHA256'],
    'sourceArchiveSHA256': host['sourceArchiveSHA256'], 'sourceMemberTreeSHA256': host['sourceMemberTreeSHA256'],
    'members': members, 'memberTreeSHA256': sha(stable(members)),
    'independentArchiveChecks': 83, 'producerReadOnlyAuditChecks': 142, 'producerHostChecks': 116, 'independentHostChecks': 371,
    'blockingFindings': [], 'interpretationLimits': [
        'Off-main fault accounting precedes identity filtering; unrelated matching-name delivery can mark incomplete.',
        'Ownership-loss cleanup occurs on next main sample/notification or observer deinit, without an autonomous wakeup.',
        'Current-scene and conservative notification-object filtering can miss lifecycle events.',
        'Complete capture status is local fault status, never continuous coverage or cause/anchor authority.',
        'Retention is value-dependent; larger independent notification fixtures retain 46-59 rows.'],
    'maximumTestedFieldBytes': host['independentHost']['largestEncodedFieldBytes'],
    'futureGenericBuild': {'selected': False, 'requiredPrototypeSwiftFiles': 12, 'requiredOverallSwiftFiles': 37, 'unchangedHarnessSwiftFiles': 4, 'minimumIOS': '26.0'},
    'historicalNativeResult': {'settings': 'Passed', 'firstTab': 'Failed', 'xcodeExitCode': 65},
    'uikitCompiled': False, 'nativeExecution': False, 'gaAccepted': False, 'physicalPhones': 'disconnected-deferred',
    'ownedHostScratchRemoved': True, 'producerEvidencePreserved': True}
(HERE / 'handoff.json').write_bytes(stable(handoff))
digest = sha((HERE / 'handoff.json').read_bytes())
(HERE / 'handoff.sha256').write_text(digest + '\n')
print(json.dumps({'handoffSHA256': digest, 'members': len(members), 'status': handoff['status']}, sort_keys=True))
