#!/usr/bin/env python3
"""Audit retained JVM evidence without executing product or artifact code."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent / 'ci-owner-artifact'
REVISION = 'fb4c8f074f1a3e5eb2b1b1a45b44f0fa61a7cc62'


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text())


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def bind(path, expected):
    demand(identity(path.read_bytes()) == expected, 'Identity mismatch: ' + str(path))


download = load(HERE / 'download-receipt.json')
artifact = download['artifact']
demand(artifact['workflow_run']['head_sha'] == REVISION, 'Artifact revision')
demand(artifact['id'] == 12654862335 and not artifact['expired'], 'Artifact identity')
demand(identity((HERE / 'artifact.zip').read_bytes())['sha256'] == artifact['digest'].split(':')[1], 'Archive digest')
extracted = HERE / 'extracted'
for row in download['members']:
    bind(extracted / row['path'], {k: row[k] for k in ['bytes', 'sha256']})
demand(len(download['members']) == 817, 'Artifact member count')
summary = []
for directory in sorted(extracted.iterdir()):
    receipt = load(directory / 'receipt.json')
    demand(receipt.get('revision', receipt.get('source_revision')) == REVISION, 'Receipt revision')
    demand(receipt['status'] == 'passed-host-only', 'Receipt status')
    demand(receipt['native_or_capture_processes_started_or_queried'] is False, 'Native scope')
    commands = load(directory / 'commands.json')
    for command in commands:
        demand(command['exit'] == 0 and command['child_reaped'], 'Command completion')
        demand(not command.get('timeout', command.get('timed_out', False)), 'Timeout')
        demand(not command.get('output_limit_exceeded', False), 'Output truncation')
        for stream in ['stdout', 'stderr']:
            bind(directory / (command['label'] + '.' + stream), command[stream])
    demand((directory / 'revision.stdout').read_text().strip() == REVISION, 'Observed revision')
    demand((directory / 'javac-version.stdout').read_text().strip() == 'javac 17.0.20.1', 'Compiler identity')
    demand('17.0.20.1' in (directory / 'java-version.stderr').read_text(), 'Runtime identity')
    compile_command = next(c for c in commands if c['label'] == 'compile')
    demand(compile_command['argv'][compile_command['argv'].index('--release') + 1] == '17', 'Class target')
    source_path = directory / ('source-freeze.json' if directory.name.endswith('observer') else 'source-map.json')
    source_map = load(source_path)
    if 'files' in source_map:
        bind(source_path, receipt['source_freeze'])
        source_map = source_map['files']
    for name, expected in source_map.items():
        bind(directory / 'inputs' / name, expected)
        data = subprocess.run(['git', 'show', REVISION + ':' + name], cwd=ROOT, capture_output=True, check=True).stdout
        demand(identity(data) == expected, 'Committed source mismatch: ' + name)
    class_map = directory / 'class-map.json'
    retained_classes = 0
    if class_map.exists():
        for name, expected in load(class_map).items():
            bind(directory / 'classes' / name, expected)
            retained_classes += 1
    cleanup = receipt['cleanup']
    demand(cleanup.get('children_reaped', cleanup.get('owned_children_reaped')) is True, 'Child cleanup')
    demand(cleanup.get('scratch_removed', cleanup.get('owned_scratch_removed')) is True, 'Scratch cleanup')
    summary.append({'closure': directory.name, 'sources_bound_to_commit': len(source_map),
                    'commands_verified': len(commands), 'retained_classes_verified': retained_classes,
                    'observed_output': (directory / 'host.stdout').read_text().strip(), 'cleanup': cleanup})
demand('cases=222 assertions=1180' in summary[1]['observed_output'], 'Owner case result')
demand('checks=14477' in summary[2]['observed_output'], 'Renderer assertion result')
demand('PASS 162 production Observer host cases' in summary[0]['observed_output'], 'Observer result')
barriers = load(extracted / 'android-owner-renderer' / 'barrier-cases.json')
# Preserve the raw case roster; this CI recipe repeats the producer matrix and
# is not additional independent caller-continuation or native coverage.
result = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'argv': sys.argv, 'python': sys.version, 'auditor': identity(Path(__file__).read_bytes()),
          'source_revision': REVISION, 'artifact_id': artifact['id'], 'artifact_digest': artifact['digest'],
          'archive_members_verified': 817, 'archive_member_bytes': download['member_bytes'],
          'closures': summary, 'barrier_roster_identity': identity((extracted / 'android-owner-renderer' / 'barrier-cases.json').read_bytes()),
          'remote_JDK17_host_scope_accepted': True, 'observer_class_bytes_retained': False,
          'observer_class_hashes_only': len(load(extracted / 'android-owner-observer' / 'receipt.json')['classes']),
          'all_Engine_jobs_accepted_by_this_receipt': False, 'independent_continuation_credit_added': False,
          'native_runtime_public_V2_or_GA_qualified': False}
(HERE / 'root-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['source_revision', 'archive_members_verified', 'remote_JDK17_host_scope_accepted', 'closures']}))
