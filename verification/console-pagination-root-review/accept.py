"""Verify the released pagination source and retained host results before delivery."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / 'verification/console-workflow-next-slice-review'
OUT = HERE / 'acceptance.json'
assert not OUT.exists()

def row(p):
    raw = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def verify(items):
    names = set()
    for item in items:
        rel = Path(item['path'])
        assert not rel.is_absolute() and '..' not in rel.parts and item['path'] not in names
        names.add(item['path'])
        assert row(ROOT / rel) == item
    return len(items)

manifest_path = PACKET / 'packet-manifest.json'
assert row(manifest_path)['sha256'] == 'a5b985fbf9b2c619e3ce82599ba3baf6459f968c0bac7a0095dd07f15330e62c'
manifest = json.loads(manifest_path.read_bytes())
assert verify(manifest) == 14
assert {str(p.relative_to(ROOT)) for p in PACKET.rglob('*') if p.is_file()} == {x['path'] for x in manifest} | {str(manifest_path.relative_to(ROOT))}
source = json.loads((PACKET / 'implementation-source-manifest.json').read_bytes())
source_count = verify(source)
owned = json.loads((PACKET / 'owned-final-source-manifest.json').read_bytes())
assert verify(owned) == 11
receipt = json.loads((PACKET / 'implementation-validation-receipt.json').read_bytes())
assert receipt['source_revision'] == 'd6af73813244c330a979afb83b45f53490ff5b29'
assert receipt['source_unchanged_during_validation'] and not receipt['new_remaining_scratch_paths']
assert receipt['source_manifest_sha256'] == row(PACKET / 'implementation-source-manifest.json')['sha256']
assert receipt['final_owned_source_manifest_sha256'] == row(PACKET / 'owned-final-source-manifest.json')['sha256']
for command in receipt['commands']:
    assert command['exit_code'] == 0 and not command['timed_out'] and command['group_absent_after_cleanup']
    for stream in ['stdout', 'stderr']:
        assert row(ROOT / command[stream])['sha256'] == command[stream + '_sha256']
assert receipt['actual_test_totals']['outer']['pass'] == 57
assert receipt['actual_test_totals']['nested_binding']['pass'] == 4
log = (PACKET / 'attempt-1-focused.stdout.log').read_text()
assert '\n# tests 57\n' in log and '\n# pass 57\n' in log and '\n# fail 0\n' in log
assert '# \\# tests 4\n' in log and '# \\# pass 4\n' in log and '# \\# fail 0\n' in log
paths = [x['path'] for x in owned]
subprocess.run(['git', 'diff', '--check', '--', *paths], cwd=ROOT, timeout=10, check=True)
review = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'status': 'accepted-console-first-page-return-host-slice',
    'source_revision': receipt['source_revision'], 'source_manifest': row(PACKET / 'implementation-source-manifest.json'),
    'source_inputs_verified': source_count, 'owned_source': owned, 'packet_manifest': row(manifest_path),
    'packet_members_verified': 14, 'retained_results': row(PACKET / 'implementation-validation-receipt.json'),
    'script': row(Path(__file__).resolve()), 'python': sys.version,
    'root_review': [
        'Reviewed all 11 changed product/test/documentation files before execution; tested bytes remain identical.',
        'Controller derives first-page availability from canonical attempted requests and independently checks current client, list request and exact project organization.',
        'First organization request clears and aborts dependent project state before notification; existing session/request generation checks reject late completions.',
        'Solid binding gates new actions on current session; page component wires them to native disabled buttons and current validated organization.',
        'Later-cursor error recovery sends the existing frozen empty request; no cursor decoding, row cache or backend authorization change.',
    ],
    'verification': {'outer_tests_passed': 57, 'nested_binding_cases_passed': 4,
        'counting': receipt['actual_test_totals']['counting'], 'project_typecheck_passed': True,
        'source_diff_check_passed': True, 'fresh_root_test_replay': False},
    'cleanup': 'Retained exact owned child/process group evidence is terminal and absent; no generated output remains outside the packet.',
    'scope': receipt['scope'], 'pending': receipt['pending'],
    'production_App_session_admission_or_build_release_connection_added': False,
    'remote_CI_pending_for_changed_source': True, 'GA_verified': 0,
}
with OUT.open('x') as stream:
    json.dump(review, stream, indent=2)
    stream.write('\n')
w = json.loads((ROOT / 'work-graph.json').read_bytes())
g = json.loads((ROOT / 'gates/ga.json').read_bytes())
assert w['packages'][13]['id'] == 'W14' and g['gates'][21]['id'] == 'G22'
node = {'status': review['status'], 'root_acceptance': row(OUT), 'owned_files': 11,
    'outer_tests_passed': 57, 'nested_binding_cases_passed': 4, 'project_typecheck_passed': True,
    'browser_or_provider_or_GA_acceptance': False, 'delivery': 'validated-local-awaiting-coherent-push'}
for target in [w['packages'][13], g['gates'][21]]:
    target['firstPageReturn'] = copy.deepcopy(node)
    target['evidence'].append(str(OUT.relative_to(ROOT)))
w['packages'][13]['nextImplementation'] = 'Deliver the accepted First-page navigation slice. Determine the exact authenticated same-origin session integration prerequisite for the production App; preserve unavailable builds/releases until connected and retain the stopped hosted review boundary.'
for name, value in [('work-graph.json', w), ('gates/ga.json', g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')
paragraph = ('The console can now return to the first organizations or projects page after paging forward, including after a later-page failure. '
    'Root source review and 57 outer host tests pass, with four nested Solid binding cases and the project typecheck also passing. '
    'The eleven-file implementation preserves scoped selection, session freshness and cancellation; it is validated locally and awaits delivery. '
    'Production session admission, connected builds/releases, browser/provider operation and G22 acceptance remain pending.')
for name, anchor in [('PLAN.md', '## Resumed checkpoint\n\n'), ('STATUS.md', '# Implementation status\n\n')]:
    p = ROOT / name
    text = p.read_text()
    assert text.count(anchor) == 1 and paragraph not in text
    p.write_text(text.replace(anchor, anchor + paragraph + '\n\n', 1))
print(json.dumps({'acceptance': row(OUT), 'source_inputs_verified': source_count, 'outer_tests': 57, 'nested_binding_cases': 4, 'owned_files': 11, 'GA_verified': 0}))
