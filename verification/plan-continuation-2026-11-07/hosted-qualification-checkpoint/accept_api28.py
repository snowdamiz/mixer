"""Bind the independent API28 package review to the current exact source closure."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent
REVIEW = BASE / 'pair9-api28-package-review'
DIGEST = 'a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca'


def identity(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


review = json.loads((REVIEW / 'result.json').read_text())
require(review['verdict'] == 'ACCEPT' and not review['blockingFindings'], 'review verdict')
for name, expected in review['evidence'].items():
    path = REVIEW / name
    require(path.resolve().is_relative_to(REVIEW), 'review member path')
    require(identity(path) == expected, 'review member changed: ' + name)
packet_path = BASE / 'pair9-api28-packaging/runtime-packet.json'
packet = json.loads(packet_path.read_text())
apk = Path(packet['apk']['path'])
require(identity(apk) == review['apk'], 'APK changed')
require(review['apk'] == {k: packet['apk'][k] for k in ('bytes', 'sha256')}, 'APK packet mismatch')
require(packet['sourceDigest101'] == review['source']['sourceDigest101'] == DIGEST, 'source binding')
spec = importlib.util.spec_from_file_location('source_inventory', ROOT / 'scripts/ci/check-android-generated-java.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
inputs = runner.source_inputs(runner.load_profile())
require(len(inputs) == 101 and runner.source_digest(inputs) == DIGEST, 'current owning source drift')
result = {
    'schema': 1,
    'acceptedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision': 'ACCEPT_EXACT_PAIR9_API28_PACKAGE_ONLY',
    'review': str((REVIEW / 'REVIEW.md').relative_to(ROOT)),
    'reviewResult': identity(REVIEW / 'result.json'),
    'allReviewMembersMatch': True,
    'runtimePacket': {'path': str(packet_path.relative_to(ROOT)), **identity(packet_path)},
    'apk': {'path': str(apk.relative_to(ROOT)), **review['apk']},
    'source': review['source'],
    'profile': review['profile'],
    'DEX': review['DEX'],
    'independentChecks': review['accountableChecks']['assertionsPassed'],
    'historicalPair8LabelsRequireExactAPKBinding': True,
    'runtimeExecuted': False,
    'notAccepted': review['notAccepted'],
    'historicalHoldsCleared': False,
}
with (BASE / 'pair9-api28-package-acceptance.json').open('x') as stream:
    stream.write(json.dumps(result, indent=2) + '\n')
print(json.dumps({'decision': result['decision'], 'sourceCount': len(inputs), 'runtimeExecuted': False}))
