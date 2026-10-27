"""Collect exact fixture CI output and run the copied data-only auditor once."""
import hashlib
import json
import pathlib
import sys
from capture import capture, digest, ROOT, REPO

SHA = '1734ea490c7c65c0086a6c60dd20c3687131c26b'
TREE = '6bd8baa4d20339764a000bc2c4babe66e0a12994'
RUN = 40433480424
assert __debug__ and not (ROOT / 'source-custody.json').exists()
capture('gh-version', ['gh', '--version'])
capture('git-version', ['git', '--version'])
assert capture('source-tree', ['git', 'rev-parse', SHA + '^{tree}']).decode().strip() == TREE
snapshot = json.loads(capture('run-at-fixture-audit', ['gh', 'api', f'repos/snowdamiz/mixer/actions/runs/{RUN}']))
assert snapshot['head_sha'] == SHA and snapshot['run_attempt'] == 1
jobs = json.loads(capture('jobs-at-fixture-audit', ['gh', 'api', f'repos/snowdamiz/mixer/actions/runs/{RUN}/jobs?per_page=100']))['jobs']
fixture, = [j for j in jobs if j['name'] == 'swift-cache-state-fixture']
assert fixture['head_sha'] == SHA and fixture['run_attempt'] == 1
assert fixture['status'] == 'completed' and fixture['conclusion'] == 'success'
assert len(fixture['steps']) == 8 and all(s['conclusion'] == 'success' for s in fixture['steps'])
capture('fixture-job-log', ['gh', 'api', '--allow-escape-sequences', f"repos/snowdamiz/mixer/actions/jobs/{fixture['id']}/logs"])
metadata = json.loads(capture('artifact-metadata', ['gh', 'api', f'repos/snowdamiz/mixer/actions/runs/{RUN}/artifacts?per_page=100']))
artifact, = [a for a in metadata['artifacts'] if a['name'] == f'swift-cache-state-fixture-{SHA}-{RUN}-1']
capture('fixture-artifact', ['gh', 'api', f"repos/snowdamiz/mixer/actions/artifacts/{artifact['id']}/zip"], 'fixture-artifact.zip')
paths = capture('source-paths', ['git', 'ls-tree', '-r', '--name-only', SHA, '--', 'verification/swift-cache-state-ci']).decode().splitlines()
assert len(paths) == len(set(paths)) == 91
rows = []
for i, path in enumerate(paths):
    assert path.startswith('verification/swift-cache-state-ci/')
    destination = 'sources/' + path
    (ROOT / destination).parent.mkdir(parents=True, exist_ok=True)
    data = capture('source-member-' + str(i), ['git', 'show', SHA + ':' + path], destination)
    rows.append({'path': path, 'captured_path': destination, **digest(data), 'command': 'source-member-' + str(i) + '.command.json'})
(ROOT / 'source-custody.json').write_text(json.dumps({'source_revision': SHA, 'source_tree': TREE, 'paths': rows}, indent=2) + '\n')
capture('source-selection', ['git', 'show', SHA + ':verification/swift-cache-state-ci-workflow-root-review/selection.json'])
capture('source-workflow', ['git', 'show', SHA + ':.github/workflows/verify.yml'])
capture('comparison-final-decision', ['git', 'show', SHA + ':verification/swift-cache-state-ci-independent/corrected-review/final-decision.json'], 'comparison-final-decision.json')
capture('content-audit', [sys.executable, '-B', str(ROOT / 'audit-content.py')])
report = json.loads((ROOT / 'full-audit.json').read_text())
assert report['passed'] and report['source_revision'] == SHA and report['source_tree'] == TREE
print(json.dumps({'passed': True, 'source_revision': SHA, 'actual_compiler': report['actual_compiler_release'], 'commands': report['commands'], 'focused': report['focused_controls'], 'global_status_at_snapshot': snapshot['status']}))
