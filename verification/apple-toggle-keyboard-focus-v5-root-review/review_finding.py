"""Replay the immutable independent V5 finding without native execution."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


seal = ROOT / 'verification/apple-toggle-keyboard-focus-v5-independent-review/review-seal.json'
assert sha(seal) == 'dbe9f176e1f32d418fb70592b976dcb3ff84789d10104d50816b720c54d7af6d'
sealed = json.loads(seal.read_text())
for name, digest in sealed['files'].items():
    assert sha(ROOT / name) == digest, name
producer = ROOT / 'verification/apple-toggle-keyboard-focus-v5-preparation'
sys.path.insert(0, str(producer))
spec = importlib.util.spec_from_file_location('v5replay', producer / 'replay.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
witness_dir = ROOT / 'verification/apple-toggle-keyboard-focus-v5-independent-review/witnesses/pre-tap-destination'
result = module.replay(witness_dir / 'captures')
witness = json.loads((witness_dir / 'witness.json').read_text())
assert result == witness['settingsDiagnostic'] == witness['replayed']
assert result['setupObservationSatisfied'] and result['selectedRouteEvidenceExpected']
assert len(result['routeOpenedBindings']) == 3
assert all(row['destinationMatched'] and not row['oldSelectorAbsent'] for row in result['routeOpenedBindings'])
assert all(row['destinationObserved'] < row['tapStarted'] < row['tapFinished'] for row in witness['detail'])
review = {
    'schema': 'mixer.keyboard-v5-root-finding-review.1',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'accountableReviewer': '/root',
    'reviewSealSHA256': sha(seal),
    'sealedFilesVerified': len(sealed['files']),
    'independentBridgeWitnessReplayed': True,
    'exactSummaryMatches': True,
    'finding': 'V5-IR-01',
    'status': 'confirmed-stale-pre-tap-destination-credit',
    'initialRootAttempt': 'An initial inline check compared the diagnostic summary with general bridge-summary.json and failed. Corrected to the sealed witness.json settingsDiagnostic and replayed fields; producer and witness unchanged.',
    'nativeExecuted': False,
    'nativeStaleCaptureClaimed': False,
    'sourceAndHostAccepted': False,
    'nativeExecutionSelected': False,
    'gaAccepted': False,
    'summary': result,
}
(OUT / 'finding-review.json').write_text(json.dumps(review, indent=2) + '\n')
selection = {
    'schema': 'mixer.apple-toggle.keyboard-v6-repair-selection.1',
    'observedUTC': review['observedUTC'],
    'accountableReviewer': '/root',
    'status': 'selected-host-ordering-repair-only',
    'reviewSealSHA256': sha(seal),
    'rootFindingReviewSHA256': sha(OUT / 'finding-review.json'),
    'producerPacketSHA256': sha(producer / 'packet-seal.json'),
    'ownership': ['verification/apple-toggle-keyboard-focus-v6-preparation/**', 'docs/apple-toggle-keyboard-focus-v6-preparation.md'],
    'selectedCorrection': 'Retain exact same-route tap finishedUptime; require it <= route-opened captureStartedUptime before accepting or crediting any destination. Bind route index and tap sequence; reject pre-tap or overlapping captures transactionally in real Bridge and offline replay.',
    'verification': [
        'Fresh boundary controls before tap start, during tap, just before completion, equality and just after completion, each route independently and stale other-route completion',
        'Real Bridge rejection preserves last durable cursor and supplies no route/destination success; exact V5 stale journal replay must reject',
        'Preserve independent 26-method semantics; adapt changed rejection API transparently without weakening the CONTRACT assertion',
        'All existing route metadata, initial-enabled and switched anchors, first-error transport, host-clock, bounds, replay and cleanup controls pass',
    ],
    'unchanged': [
        'Exact app/carrier bytes, V2 keyboard oracle, V5 native runner and shared Swift transport bytes',
        'All request/event/upload/payload/time bounds and three-second switch window',
        'Six app cases remain unrun; DIAGNOSTIC_ONLY, keyboard/carrier/GA false',
        'All prior packets/findings/failures remain immutable',
    ],
    'nativeRunnerRebuild': 'Not needed if exact runner source/product/archive identities remain unchanged; verify all identities. Any runner change requires separate root review.',
    'nativeExecutionSelected': False,
    'gaAccepted': False,
}
(OUT / 'v6-repair-selection.json').write_text(json.dumps(selection, indent=2) + '\n')
print(json.dumps({'review': sha(OUT / 'finding-review.json'), 'selection': sha(OUT / 'v6-repair-selection.json'), 'sealedFiles': len(sealed['files']), 'replayMatches': True}))
