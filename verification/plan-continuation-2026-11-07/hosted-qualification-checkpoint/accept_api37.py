"""Record narrow API37 development acceptance from exact independent evidence."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent
PREFIX = str(BASE.relative_to(ROOT)) + '/'
REVIEW = BASE / 'motion-r2-native-actual-review/review.json'
checked = {}


def identity(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_named(value):
    if isinstance(value, dict):
        if all(k in value for k in ('path', 'bytes', 'sha256')):
            path = Path(value['path'])
            require('scratch' not in path.parts, 'held scratch is not an admissible review input')
            actual = identity(path)
            require(actual == {k: value[k] for k in ('bytes', 'sha256')}, 'changed evidence: ' + str(path))
            checked[str(path)] = actual
        for child in value.values():
            check_named(child)
    elif isinstance(value, list):
        for child in value:
            check_named(child)


review = json.loads(REVIEW.read_text())
require(review['verdict'] == 'ACCEPT' and not review['blockingFindings'], 'review verdict')
check_named(review)
spec = importlib.util.spec_from_file_location('source_inventory', ROOT / 'scripts/ci/check-android-generated-java.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
inputs = runner.source_inputs(runner.load_profile())
require(len(inputs) == 101 and runner.source_digest(inputs) == review['independentAudit']['source101'], 'current source closure drift')
require(review['run']['reportedChecks'] == 104 and review['run']['reportedOriginalSmokeChecks'] == 11, 'assertion scope')
acceptance = {
    'schema': 1,
    'acceptedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision': 'ACCEPT_EXACT_PAIR9_R2_API37_ARM64_DEVELOPMENT_SMOKE',
    'sourceRevision': review['sourceRevision'], 'sourceTree': review['sourceTree'],
    'source101': review['independentAudit']['source101'],
    'review': {'path': str(REVIEW.relative_to(ROOT)), **identity(REVIEW)},
    'verifiedNamedEvidence': checked,
    'run': review['run'],
    'independentEvidencePredicates': review['independentAudit']['checks'],
    'correctedPriorInputComparison': {
        'unchanged': 103, 'total': 105,
        'intentionalChanges': review['nonblockingFindings'][0]['changedPaths'],
        'originalCount104PreservedInHistoricalReceipt': True,
    },
    'artifactReliance': review['artifactReliance'],
    'limitations': review['limitations'],
    'specificHoldsCleared': False, 'gaAccepted': False,
}
with (BASE / 'pair9-api37-native-acceptance.json').open('x') as stream:
    stream.write(json.dumps(acceptance, indent=2) + '\n')

old = 'Independent actual-runtime review is pending; the earlier failures and holds remain unchanged.'
new = '[Independent review and root acceptance](verification/plan-continuation-2026-11-07/pair9-api37-native-acceptance.json) qualify only this API37 arm64 development smoke. The review corrects one bookkeeping count to 103 unchanged prior inputs out of 105; it preserves the original receipt. The deleted test APK was not independently rehashed, and custody depends on retained command records. Earlier failures and all holds remain unchanged.'
for name in ('PLAN.md', 'STATUS.md'):
    path = ROOT / name
    current, marker, historical = path.read_text().partition('\n## Previous')
    require(current.count(old) == 1, 'current narrative drift: ' + name)
    path.write_text(current.replace(old, new) + marker + historical)
for name, key, ids in [('work-graph.json', 'packages', {'W02', 'W05'}), ('gates/ga.json', 'gates', {'G02', 'G06'})]:
    path = ROOT / name
    data = json.loads(path.read_text())
    gate_states = [(x['id'], x.get('status')) for x in data[key]]
    for item in data[key]:
        if item['id'] not in ids:
            continue
        item['currentCheckpoint'] = item['currentCheckpoint'].replace('actual-runtime review pending', 'independently accepted API37 development smoke only')
        c = item['continuation20261107']
        c['state'] = 'pair9 host/Java and narrow API37 development smoke accepted; API28 package accepted, ART/JNI unrun'
        c['pair9API37Actual'].update(status='independently accepted API37 arm64 development smoke only', runtimeAccepted=True, acceptance=PREFIX + 'pair9-api37-native-acceptance.json', unchangedPriorInputs=103, totalPriorInputs=105)
        c['pair9CandidateR2']['api37DevelopmentSmokeAcceptance'] = PREFIX + 'pair9-api37-native-acceptance.json'
        c['pair9CandidateR2']['completeNativeRuntimeQualification'] = False
    require(gate_states == [(x['id'], x.get('status')) for x in data[key]], 'GA gate changed')
    path.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'decision': acceptance['decision'], 'checkedEvidenceFiles': len(checked), 'runtimeChecks': 104, 'gaPromoted': False}))
