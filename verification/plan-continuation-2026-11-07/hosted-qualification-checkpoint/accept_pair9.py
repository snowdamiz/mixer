"""Accept the exact independently audited pair9 CI artifacts, preserving scope."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent
REVISION = '96f03ab65966a6374e958e780fa09a3eed814c0b'
DIGEST = 'a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca'


def read(path):
    return json.loads(path.read_text())


def identity(path):
    body = path.read_bytes()
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def check_members(directory, members):
    for name, expected in members.items():
        path = directory / name
        require(path.resolve().is_relative_to(directory.resolve()), 'member path')
        require(identity(path) == {k: expected[k] for k in ('bytes', 'sha256')}, 'changed review: ' + name)


spec = importlib.util.spec_from_file_location('source_inventory', ROOT / 'scripts/ci/check-android-generated-java.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
inputs = runner.source_inputs(runner.load_profile())
require(len(inputs) == 101 and runner.source_digest(inputs) == DIGEST, 'integrated source drift')
jobs = read(BASE / 'pair9-r2-delivery/ci-discovery/final-jobs.json')['jobs']
require(len(jobs) == 7 and all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in jobs), 'CI not complete')

host_dir = BASE / 'pair9-host-ci-review'
host = read(host_dir / 'receipt.json')
check_members(host_dir, host['ownedFiles'])
require(host['verdict'] == 'ACCEPT' and not host['blockingFindings'], 'host review')
require((host['revision'], host['run'], host['attempt'], host['job'], host['artifact']) ==
        (REVISION, 42430741909, 1, 128578860306, 13597407658), 'host identity')
require(identity(Path(host['archiveRetained']['path'])) == {k: host['archiveRetained'][k] for k in ('bytes', 'sha256')}, 'host archive')
host_audit = read(host_dir / 'audit-result.json')
require(host_audit['canonicalDigest'] == DIGEST, 'host sources')
host_acceptance = {
    'schema': 1, 'acceptedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision': 'ACCEPT_EXACT_PAIR9_ORDINARY_HOST_CI',
    'revision': REVISION, 'run': host['run'], 'attempt': 1, 'job': host['job'], 'artifact': host['artifact'],
    'sourceCount': len(inputs), 'sourceDigest': DIGEST,
    'review': str((host_dir / 'REVIEW.md').relative_to(ROOT)),
    'reviewReceipt': identity(host_dir / 'receipt.json'), 'allReviewMembersMatch': True,
    'archive': host['archiveRetained'], 'matrix': host_audit['matrix'],
    'hostOutputs': host_audit['outputs'], 'independentChecks': host['checks'],
    'limitations': host['custodyLimits'], 'nativeAndGAQualified': False,
    'specificCustodyHoldsCleared': False,
}

java_dir = BASE / 'pair9-generated-hosted-review'
java = read(java_dir / 'result.json')
seal = read(java_dir / 'seal.json')
check_members(java_dir, seal['files'])
require(java['verdict'] == 'ACCEPT' and not java['blocking_findings'], 'Java review')
require((java['reviewed_revision'], java['run'], java['attempt'], java['job'], java['artifact']) ==
        (REVISION, 42430741909, 1, 128578860259, 13597797001), 'Java identity')
require(identity(Path('/tmp/mixer-ci96-generated-java.zip')) == java['archive'], 'Java archive')
require(java['source_count'] == 101 and java['source_digest'] == DIGEST, 'Java sources')
java_acceptance = {
    'schema': 1, 'acceptedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision': 'ACCEPT_EXACT_PAIR9_HOSTED_JAVA_BOOTSTRAP',
    'revision': REVISION, 'run': java['run'], 'attempt': 1, 'job': java['job'], 'artifact': java['artifact'],
    'sourceCount': len(inputs), 'sourceDigest': DIGEST, 'sdk': java['sdk'], 'adapter': java['adapter'],
    'review': str((java_dir / 'REVIEW.md').relative_to(ROOT)),
    'reviewResult': identity(java_dir / 'result.json'), 'reviewSeal': identity(java_dir / 'seal.json'),
    'allReviewMembersMatch': True, 'archive': java['archive'],
    'bootstrapCommands': java['bootstrap_commands'], 'integrationCommands': java['integration_commands'],
    'consumers': java['consumers'], 'javaSourcesEach': java['java_sources_per_consumer'],
    'classesEach': java['classfiles_per_consumer'], 'memberReferencesEach': java['member_references_per_consumer'],
    'tamperInvocations': java['tamper_invocations'], 'independentChecks': java['checks'],
    'dex': java['dex'], 'limitations': java['limitations'], 'notGranted': java['not_granted'],
    'specificCustodyHoldsCleared': False,
}
for name, data in [('pair9-host-ci-acceptance.json', host_acceptance),
                   ('pair9-generated-hosted-acceptance.json', java_acceptance)]:
    with (BASE / name).open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')
print(json.dumps({'accepted': ['pair9 host CI', 'pair9 hosted Java/D8'], 'sourceCount': len(inputs), 'nativeAccepted': False}))
