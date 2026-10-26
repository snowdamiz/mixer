#!/usr/bin/env python3
"""Verify remote host evidence against the pushed tree, without executing artifacts."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent / 'ci-owner-artifact'
REVISION = '5583fb2c61e2c12acb5f0120a9a072e05cdb5ac1'

def demand(ok, message):
    if not ok:
        raise ValueError(message)

def load(path):
    return json.loads(path.read_text())

def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def bind(path, expected):
    demand(identity(path.read_bytes()) == expected, 'Identity mismatch: ' + str(path))

artifact = next(a for a in load(HERE / 'artifact-metadata.stdout')['artifacts'] if a['id'] == 12663385059)
demand(artifact['workflow_run']['head_sha'] == REVISION and not artifact['expired'], 'Artifact revision')
demand(identity((HERE / 'artifact.zip').read_bytes())['sha256'] == artifact['digest'].split(':')[1], 'Archive digest')
extracted = HERE / 'extracted'
archive_rows = []
with zipfile.ZipFile(HERE / 'artifact.zip') as archive:
    for item in archive.infolist():
        if item.is_dir():
            continue
        data = archive.read(item)
        bind(extracted / item.filename, identity(data))
        archive_rows.append(dict(identity(data), path=item.filename))
demand(len(archive_rows) == 898, 'Archive member count')
summary = []
for directory in sorted(extracted.iterdir()):
    receipt = load(directory / 'receipt.json')
    demand(receipt['status'] == 'passed-host-only' and receipt['source_stable'], 'Host status/source stability')
    demand(receipt['native_or_capture_processes_started_or_queried'] is False, 'Native scope')
    is_environment = directory.name == 'android-owner-environment'
    if is_environment:
        demand(receipt['context_revision_is_inherited_not_live_git'] is True, 'Historical context labeling')
    else:
        demand(receipt['revision'] == REVISION, 'Observed revision')
        demand((directory / 'revision.stdout').read_text().strip() == REVISION, 'Revision command')
    commands = load(directory / 'commands.json')
    for command in commands:
        demand('/' not in command['label'] and '..' not in command['label'], 'Command label')
        demand(command['exit'] == 0 and command['child_reaped'], 'Command completion')
        demand(not command.get('timeout', False) and not command.get('output_limit_exceeded', False), 'Bounded output')
        for stream in ['stdout', 'stderr']:
            bind(directory / (command['label'] + '.' + stream), command[stream])
    demand((directory / 'javac-version.stdout').read_text().strip() == 'javac 17.0.20.1', 'javac version')
    demand('17.0.20.1' in (directory / 'java-version.stderr').read_text(), 'java version')
    compile_command = next(c for c in commands if c['label'] == 'compile')
    demand(compile_command['argv'][compile_command['argv'].index('--release') + 1] == '17', 'Java class target')
    source_map = load(directory / 'source-map.json')
    for name, expected in source_map.items():
        rel = PurePosixPath(name)
        demand(not rel.is_absolute() and '..' not in rel.parts, 'Source map path')
        bind(directory / 'inputs' / name, expected)
        data = subprocess.run(['git', 'show', REVISION + ':' + name], cwd=ROOT, capture_output=True, timeout=30, check=True).stdout
        demand(identity(data) == expected, 'Pushed source mismatch: ' + name)
    retained_classes = 0
    class_map = directory / 'class-map.json'
    if class_map.exists():
        for name, expected in load(class_map).items():
            bind(directory / 'classes' / name, expected)
            retained_classes += 1
    cleanup = receipt['cleanup']
    demand(cleanup.get('children_reaped', cleanup.get('owned_children_reaped')) is True, 'Children cleanup')
    demand(cleanup.get('scratch_removed', cleanup.get('owned_scratch_removed')) is True, 'Scratch cleanup')
    if is_environment:
        outputs = {name: (directory / (name + '.stdout')).read_text().strip() for name in ['NativeEnvironmentV2ObserverHostTests', 'NativeEnvironmentPlatformV2HostTests']}
        demand('PASS 162 production Observer host cases' in outputs['NativeEnvironmentV2ObserverHostTests'], 'Observer result')
        demand('cases=131 assertions=671' in outputs['NativeEnvironmentPlatformV2HostTests'], 'Platform result')
        isolation = load(directory / 'isolation.json')
        demand(len(isolation['checked_emitted_classes']) == 16, 'Environment isolation class count')
        for name in isolation['checked_emitted_classes']:
            dump = (directory / ('javap-' + name.rsplit('.', 1)[1] + '.stdout')).read_text()
            demand(all(symbol not in dump for symbol in isolation['forbidden_later_symbols']), 'Later API symbol leakage')
        class_hashes_only = len(load(directory / 'classes.json'))
    else:
        outputs = {'host': (directory / 'host.stdout').read_text().strip()}
        expected = 'cases=222 assertions=1180' if directory.name.endswith('orchestration') else 'checks=14477'
        demand(expected in outputs['host'], 'Owner result')
        class_hashes_only = 0
    summary.append({'closure': directory.name, 'sources_bound_to_pushed_commit': len(source_map),
                    'commands_verified': len(commands), 'retained_class_bytes_verified': retained_classes,
                    'class_hashes_only': class_hashes_only, 'outputs': outputs, 'cleanup': cleanup,
                    'inherited_context_revision_only': receipt.get('context_revision')})
target = HERE / 'root-audit.json'
demand(not target.exists(), 'Immutable root audit already exists')
result = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'argv': sys.argv, 'python': sys.version, 'auditor': identity(Path(__file__).read_bytes()),
          'git_version': subprocess.run(['git', '--version'], capture_output=True, check=True, timeout=30).stdout.decode().strip(),
          'source_revision': REVISION, 'artifact_id': artifact['id'], 'artifact_digest': artifact['digest'],
          'archive_members_verified': len(archive_rows), 'archive_member_bytes': sum(r['bytes'] for r in archive_rows),
          'closures': summary, 'archive_members': archive_rows,
          'remote_JDK17_host_scope_accepted': True, 'all_Engine_jobs_accepted_by_this_receipt': False,
          'independent_continuation_credit_added': False, 'native_runtime_public_V2_or_GA_qualified': False}
target.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['source_revision', 'archive_members_verified', 'remote_JDK17_host_scope_accepted', 'closures']}))
