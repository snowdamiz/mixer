"""Read-only source/artifact audit; outputs only within this review directory."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANDIDATE = HERE.parent / 'cache-deadline-control-fix'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_exact(text, patch):
    lines = text.splitlines(keepends=True)
    changes = patch.splitlines(keepends=True)
    need(changes[:2] == ['--- a/.github/workflows/verify.yml\n', '+++ b/.github/workflows/verify.yml\n'], 'Unexpected patch scope')
    output, position, index = [], 0, 2
    while index < len(changes):
        match = re.fullmatch(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n', changes[index])
        need(match is not None, 'Malformed hunk')
        old_start, old_count, new_start, new_count = map(int, match.groups())
        output.extend(lines[position:old_start - 1])
        position, old_seen, new_seen = old_start - 1, 0, 0
        need(len(output) == new_start - 1, 'New hunk offset')
        index += 1
        while index < len(changes) and not changes[index].startswith('@@'):
            line = changes[index]
            if line[0] in ' -':
                need(lines[position] == line[1:], 'Exact patch preimage mismatch')
                position += 1
                old_seen += 1
            if line[0] in ' +':
                output.append(line[1:])
                new_seen += 1
            index += 1
        need((old_seen, new_seen) == (old_count, new_count), 'Hunk size')
    output.extend(lines[position:])
    return ''.join(output)


original = (ROOT / '.github/workflows/verify.yml').read_text()
proposed = apply_exact(original, (CANDIDATE / 'workflow.diff').read_text())
previous_job = (CANDIDATE / 'workflow/previous-job.yml').read_text()
new_job = (CANDIDATE / 'workflow/swift-cache-state-fixture.yml').read_text()
need(original.count(previous_job) == 1, 'Exactly one job preimage')
need(proposed == original.replace(previous_job, new_job, 1), 'Changes outside cache job')
(HERE / 'prospective-verify.yml').write_text(proposed)
data = {'workflow': {'exact_job_replacement': True, 'other_jobs_unchanged': True,
    'installed_source_sha256': hashlib.sha256(original.encode()).hexdigest(),
    'proposed_source_sha256': hashlib.sha256(proposed.encode()).hexdigest(),
    'proposed_job_sha256': hashlib.sha256(new_job.encode()).hexdigest(),
    'limits_preserved': ['runs-on macos-15', 'job 30min', 'preflight 2min', 'controls 3min',
        'fixture 12min', 'postflight 2min', 'upload 5min', 'RUSTUP_AUTO_INSTALL=0']}}

# Audit every 163-row historical binding; establish which bindings the nested
# adoption independently enforces, rather than treating the candidate count as proof.
old_rows = json.loads((CANDIDATE / 'old-inputs-before.json').read_bytes())['members']
for row in old_rows:
    path = ROOT / row['path']
    need(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'Old binding mismatch ' + row['path'])
data['historical'] = {'count': len(old_rows), 'all_match': True,
    'roster_sha256': sha(CANDIDATE / 'old-inputs-before.json'),
    'roster': old_rows}

acquisition_path = HERE.parent / 'ci-e725-cache-failure/acquisition.json'
acquisition = json.loads(acquisition_path.read_bytes())
archive = Path(acquisition['zip'])
need(archive.stat().st_size == acquisition['bytes'] and sha(archive) == acquisition['sha256'], 'Retained archive mismatch')
artifact = acquisition_path.parent / 'artifact'
stderr_relative = 'verification/cache-fixture-shared-input-candidate-v2/logs/runner-controls.stderr'
stderr = artifact / stderr_relative
record = next(row for row in acquisition['files'] if row['path'] == stderr_relative)
need(sha(stderr) == record['sha256'] and stderr.stat().st_size == record['bytes'], 'Failure log mismatch')
failure_text = stderr.read_text()
need('0.200852 not less than 0.2' in failure_text and 'FAILED (failures=1)' in failure_text and 'Ran 36 tests' in failure_text,
     'Unexpected baseline failure')
data['failure_provenance'] = {key: acquisition[key] for key in ['run', 'attempt', 'job', 'artifact', 'head', 'bytes', 'sha256']}
data['failure_provenance'].update(stderr_sha256=sha(stderr), historical_latency_cause_proven=False,
    no_old_attempt_rerun=True)

# Existing final local runner logs are evidence to retain, not tests to repeat.
for mode, expected in [('normal', 'OK'), ('optimized', 'FAILED (failures=1)')]:
    log = CANDIDATE / ('final-runner-' + mode + '.stderr')
    text = log.read_text()
    need('Ran 36 tests' in text and text.rstrip().endswith(expected), 'Candidate final log differs')
    if mode == 'optimized':
        need('FAIL: test_owned_descendant_group_is_stopped' in text and 'Operation not permitted' in text and '23663' in text, 'Final optimized failure changed')
    data['final_' + mode] = {'sha256': sha(log), 'status': expected, 'full_suite_repeated': False}

selected = ROOT / 'verification/plan-continuation-2026-11-07/cache-fix/compiler-selection.json'
selection = json.loads(selected.read_bytes())
data['compiler_selection'] = {'sha256': sha(selected), 'profile': selection['profile'], 'new_fixture_qualified': False}
hold = HERE.parent / 'cache-deadline-custody-hold/receipt.json'
data['hold'] = {'receipt_sha256': sha(hold), 'pgid': 23663, 'probed': False, 'signalled': False,
                'retained_scratch_read_or_modified': False}
data['command'] = {'argv': sys.argv, 'python': sys.version}
(HERE / 'data-audit.json').write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
print(json.dumps({'bindings': len(old_rows), 'workflow': 'only cache job', 'retained_failure_verified': True,
                  'final_normal': '36/36', 'final_optimized': '35/36; descendant EPERM; PGID23663 held'}))
