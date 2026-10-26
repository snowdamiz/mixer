"""Record verified terminal CI without promoting unrelated product gates."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
receipt = json.loads((HERE / 'receipt.json').read_bytes())
observation = ROOT / receipt['latest_observation']
data = json.loads(observation.read_bytes())
assert receipt['commit'] == data['headSha'] == '137d3e1d833fcaee08244b439e50c2c42723bddd'
assert data['status'] == 'completed' and data['conclusion'] == 'success'
assert len(data['jobs']) == 3
steps = [s for j in data['jobs'] for s in j['steps']]
assert len(steps) == 42
assert all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in data['jobs'])
assert all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in steps)
terminal = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'python': sys.version, 'argv': sys.argv,
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'status': 'passed-all-jobs-and-steps', 'commit': data['headSha'], 'tree': receipt['tree'],
    'run_id': 40292240567, 'url': data['url'], 'jobs': 3, 'steps': 42,
    'skipped_steps': 0, 'failed_steps': 0,
    'observation': receipt['latest_observation'],
    'observation_sha256': hashlib.sha256(observation.read_bytes()).hexdigest(),
    'job_summaries': [{k: j[k] for k in ('name', 'databaseId', 'status', 'conclusion', 'startedAt', 'completedAt')} for j in data['jobs']],
    'scope': 'Test-only runner timeout readiness repair and existing Engine checks. New Android owner/cache-state source remains outside this commit; preceding 5c CI failure remains failed.',
    'production_runner_changed': False, 'native_runtime_or_capture_started': False, 'GA_qualified': False,
}
path = HERE / 'ci-terminal.json'
assert not path.exists()
path.write_text(json.dumps(terminal, indent=2) + '\n')
digest = hashlib.sha256(path.read_bytes()).hexdigest()
for name, key in [('work-graph.json', 'packages'), ('gates/ga.json', 'gates')]:
    metadata = ROOT / name
    d = json.loads(metadata.read_bytes())
    matches = [i['orderedRetentionAnalyzerEnvelopeCI']['timeout_control_repair'] for i in d[key] if 'orderedRetentionAnalyzerEnvelopeCI' in i]
    assert len(matches) == 1
    item = matches[0]
    item.update(status='host-controls-and-pushed-CI-passed', CI_passed=True,
        terminal_receipt=path.relative_to(ROOT).as_posix(), terminal_receipt_sha256=digest)
    item['delivery'].update(status='passed', all_jobs_and_steps_passed=True, jobs=3, steps=42)
    metadata.write_text(json.dumps(d, indent=2) + '\n')
for name in ('PLAN.md', 'STATUS.md'):
    p = ROOT / name
    before = p.read_text()
    after = before.replace('corrected `137d3e1d` is pushed and [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40292240567) is running.',
        'corrected `137d3e1d` passes all 42 steps across three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40292240567).')
    assert after != before, name
    p.write_text(after)
print(json.dumps({'path': path.relative_to(ROOT).as_posix(), 'sha256': digest, 'jobs': 3, 'steps': 42}))
