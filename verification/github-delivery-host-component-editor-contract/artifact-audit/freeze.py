"""Validate persisted audit custody and seal the final finite evidence set."""
import datetime
import hashlib
import json
import pathlib
import stat
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
assert __debug__
assert not (ROOT / 'seal.json').exists(), 'Final seal is one-shot'
SHA = '8ac624160a2cfff10d201d8063f69cf05f005edb'
TREE = '604a1360677391356ce401d17f966dfd5f1393e8'
RUN = 40366004814


def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


acceptance = read(ROOT / 'acceptance.json')
assert acceptance['source_revision'] == SHA and acceptance['source_tree'] == TREE
assert acceptance['run_id'] == RUN and acceptance['run_attempt'] == 1
assert acceptance['successful_jobs'] == 5 and acceptance['successful_steps'] == 56
assert acceptance['retries_executed'] == 0
assert acceptance['status'] == 'all-five-jobs-and-retained-host-artifacts-pass'
assert read(ROOT / 'driver.stdout') == acceptance
assert (ROOT / 'driver.stderr').read_bytes() == b''
assert acceptance['full_ci_log']['sha256'] == digest((ROOT / 'ci-full-log.stdout').read_bytes())['sha256']
commands = []
for path in sorted(ROOT.rglob('*.command.json')):
    record = read(path)
    assert record.get('exit_code', record.get('exit')) == 0, str(path)
    stem = path.name.removesuffix('.command.json')
    stdout = path.parent / record.get('stdout_file', stem + '.stdout')
    stderr = path.parent / (stem + '.stderr')
    assert digest(stdout.read_bytes()) == record['stdout'], str(stdout)
    assert digest(stderr.read_bytes()) == record['stderr'], str(stderr)
    commands.append(str(path.relative_to(ROOT)))
source_commands = []
for path in (ROOT / 'source-commands.json', ROOT / 'capability/source-commands.json'):
    entries = read(path)
    assert entries and all(e['exit_code'] == 0 and e['argv'][0] == 'git' and e['argv'][1] in ('show', 'rev-parse', 'archive', 'ls-tree') and any(arg.startswith(SHA) for arg in e['argv']) for e in entries)
    source_commands.append({'path':str(path.relative_to(ROOT)), 'commands':len(entries), **digest(path.read_bytes())})
source_manifests = []
for path in (ROOT / 'source-blobs.json', ROOT / 'capability/source-blobs.json'):
    manifest = read(path)
    assert all(len(item['sha256']) == 64 and len(item['git_blob']) == 40 and item['bytes'] >= 0 for item in manifest.values())
    assert not any(any(token in name.lower() for token in ('hostedcatalog','hosted-catalog','authority-driver','rejectedworker','hosted-harness')) for name in manifest)
    source_manifests.append({'path':str(path.relative_to(ROOT)), 'unique_source_paths':len(manifest), **digest(path.read_bytes())})
archives = []
for directory, name, key in ((ROOT, 'swift-core-toolchain-host', 'core'), (ROOT, 'android-owner-host', 'JVM'), (ROOT / 'capability', 'android-binding-host', 'capability')):
    archive = directory / (name + '.zip')
    metadata = read(directory / 'artifact-metadata.stdout')['artifacts']
    artifact, = [a for a in metadata if a['name'] == name + '-' + SHA]
    data_digest = digest(archive.read_bytes())
    assert artifact['digest'] == 'sha256:' + data_digest['sha256']
    assert artifact['workflow_run']['id'] == RUN and artifact['workflow_run']['head_sha'] == SHA and not artifact['expired']
    members = read(directory / (name + '.members.json'))
    with zipfile.ZipFile(archive) as z:
        assert len(z.infolist()) == len(members)
        actual = []
        for item in z.infolist():
            p = pathlib.PurePosixPath(item.filename)
            assert not p.is_absolute() and '..' not in p.parts and '\\' not in item.filename
            assert not stat.S_ISLNK(item.external_attr >> 16) and not item.flag_bits & 1
            actual.append({'path':item.filename, **digest(z.read(item))})
        assert actual == members
        assert len(set(item['path'] for item in members)) == len(members)
    assert data_digest['sha256'] == acceptance[key]['sha256']
    assert artifact['id'] == acceptance[key]['id']
    assert len(members) == acceptance[key]['members']
    assert sum(item['bytes'] for item in members) == acceptance[key]['member_bytes']
    archives.append({'path':str(archive.relative_to(ROOT)), 'artifact_id':artifact['id'], 'members':len(members), 'member_bytes':sum(item['bytes'] for item in members), **data_digest})
capability = read(ROOT / 'capability/audit.json')
assert capability['status'] == 'passed-retained-host-artifact-audit'
assert [(m['mode'],m['cases_verified'],m['command_log_digests_verified']) for m in capability['modes']] == [('debug',39,51),('release',39,51),('tsan',39,51)]
assert read(ROOT / 'core-jvm-audit.json')['source_commands'] == digest((ROOT / 'source-commands.json').read_bytes())
assert capability['source_blob_manifest']['sha256'] == digest((ROOT / 'capability/source-blobs.json').read_bytes())['sha256']
validation = {
    'schema':1, 'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'argv':sys.argv, 'python':sys.version,
    'status':'persisted-command-and-archive-custody-validated',
    'source_revision':SHA, 'source_tree':TREE, 'run_id':RUN,
    'command_records_revalidated':len(commands), 'commands':commands,
    'source_commands':source_commands, 'source_manifests':source_manifests, 'archives':archives,
    'authoring_failures':0,
    'scope':'Hash/digest and archive-member revalidation only; no imported or executed archive code, native runtime, UI, capture, process inventory, git mutation or network mutation',
    'limitations':acceptance['limits'],
}
(ROOT / 'custody-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
members = []
for path in sorted(ROOT.rglob('*')):
    if path.is_file():
        assert not path.is_symlink()
        members.append({'path':str(path.relative_to(ROOT)),**digest(path.read_bytes())})
seal = {'schema':1, 'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope':'Frozen read-only terminal five-job exact-source host artifact audit',
        'source_revision':SHA, 'source_tree':TREE, 'run_id':RUN,
        'acceptance_sha256':digest((ROOT / 'acceptance.json').read_bytes())['sha256'],
        'member_count':len(members), 'total_bytes':sum(m['bytes'] for m in members),
        'members':members}
(ROOT / 'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'status':'sealed', 'acceptance_sha256':seal['acceptance_sha256'], 'seal_sha256':digest((ROOT / 'seal.json').read_bytes())['sha256'], 'sealed_members':len(members), 'sealed_bytes':seal['total_bytes'], 'source_manifests':source_manifests, 'source_command_counts':[i['commands'] for i in source_commands]}))
