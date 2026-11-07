#!/usr/bin/env python3
"""Deliver the prepared immutable evidence slice without active lane files."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def run(label, argv):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True)
    (HERE / (label + '.stdout')).write_bytes(result.stdout)
    (HERE / (label + '.stderr')).write_bytes(result.stderr)
    (HERE / (label + '.command.json')).write_text(json.dumps({
        'argv': argv, 'started': start, 'ended': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'exit': result.returncode, 'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
        'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()}, indent=2) + '\n')
    demand(result.returncode == 0, 'Command failed: ' + label)
    return result.stdout


demand(not (HERE / 'receipt.json').exists(), 'Delivery already completed')
prepared = json.loads((HERE / 'prepared.json').read_text())
demand(hashlib.sha256((HERE / 'manifest.json').read_bytes()).hexdigest() == prepared['manifest_sha256'], 'Manifest drift')
head = run('before-head', ['git', 'rev-parse', 'HEAD']).decode().strip()
demand(head == prepared['parent'], 'Parent changed')
demand(run('before-branch', ['git', 'branch', '--show-current']).strip() == b'main', 'Branch changed')
remote = run('before-remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0]
demand(remote == head, 'Remote advanced; reconcile before delivery')
staged = set(run('staged-paths', ['git', 'diff', '--cached', '--name-only', '-z']).decode().split('\0')) - {''}
demand(staged == set(prepared['staged_paths']), 'Index scope changed')
# The exact staged bytes were audited by prepare.py. Check the staged tree is
# still identical to the live immutable member inventory before committing.
for row in json.loads((HERE / 'manifest.json').read_text())['members']:
    data = (ROOT / row['path']).read_bytes()
    demand(len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'Selected evidence drift')
run('git-version', ['git', '--version'])
run('commit', ['git', 'commit', '-m', 'Record reviewed source accounting and Android environment contracts'])
commit = run('after-head', ['git', 'rev-parse', 'HEAD']).decode().strip()
tree = run('tree', ['git', 'rev-parse', 'HEAD^{tree}']).decode().strip()
committed = set(run('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', '-z', 'HEAD']).decode().split('\0')) - {''}
demand(committed == staged, 'Committed scope differs from prepared scope')
run('push', ['git', 'push', 'origin', 'HEAD:main'])
after = run('after-remote', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split()[0]
demand(after == commit, 'Remote did not confirm new commit')
demand(not run('index-after', ['git', 'diff', '--cached', '--name-only']), 'Index not empty')
receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'argv': sys.argv, 'python': sys.version, 'parent': head, 'commit': commit, 'tree': tree,
           'manifest_sha256': prepared['manifest_sha256'], 'changed_paths': len(staged),
           'remote_main_verified': True, 'active_product_and_proof_lanes_excluded': True,
           'CI_status': 'not_yet_discovered', 'GA_promoted': False}
(HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
