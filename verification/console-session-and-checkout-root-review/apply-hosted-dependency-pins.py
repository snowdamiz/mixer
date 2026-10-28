"""Apply the independently reviewed, officially generated two-pin correction once."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

R = Path(__file__).resolve().parents[2]
P = R / 'verification/hosted-dependency-advisory-correction/integration-v1'
REVIEW = R / 'verification/hosted-dependency-advisory-correction-independent/runtime-review-1/review-seal.json'
RUN = R / 'verification/hosted-dependency-advisory-correction/resolution-v4/attempts/fe41774456c8435e841b30f9b48cb7ec'
DEST = Path(__file__).with_name('hosted-dependency-canonical-application.json')

def read(p):
    return json.loads(p.read_bytes())

def row(p):
    b = p.read_bytes()
    return {'path': str(p.relative_to(R)), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

assert not DEST.exists()
assert row(P / 'seal.sha256')['sha256'] == '5b2b8a2850a17a5e355ae49cdbda4b3b51122439bd551aefd29c125617371b6b'
for line in (P / 'seal.sha256').read_text().splitlines():
    h, n = line.split('  ', 1)
    assert row(P / n)['sha256'] == h, n
assert row(REVIEW)['sha256'] == '3efc908cedcff554909b2f3e64a783c2c0259be728ea224285b80507770890f6'
seal = read(REVIEW)
for m in seal.get('members', seal.get('files', [])):
    a = row(REVIEW.parent / m['path'])
    assert a['bytes'] == m['bytes'] and a['sha256'] == m['sha256']
assert len(seal.get('members', seal.get('files', []))) == 3
receipt = read(RUN / 'receipt.json')
assert receipt['status'] == 'resolved_two_pins_only' and receipt['scratch_removed'] and receipt['groups_closed'] and not receipt['errors']
assert len(receipt['commands']) == 5 and all(x['returncode'] == 0 for x in receipt['commands'])
protected = {n: row(R / n) for n in ['.github/workflows/hosted.yml', 'hosted/lib/mixer_hosted/browser_auth/store.ex', 'hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex', 'hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs']}
rows = read(P / 'application-map.json')['canonical_files']
assert {x['canonical_path'] for x in rows} == {'hosted/mix.exs', 'hosted/mix.lock', 'THIRD_PARTY.yml'}
for x in rows:
    assert row(R / x['canonical_path'])['sha256'] == x['required_before_sha256']
    assert row(R / x['proposed_path'])['sha256'] == x['proposed_sha256']
w, g = read(R / 'work-graph.json'), read(R / 'gates/ga.json')
d = w['packages'][15]['hostedDependencyAdvisoryCorrection']
assert d == g['gates'][24]['hostedDependencyAdvisoryCorrection']
d.update({'status': 'two-patched-dependency-pins-applied-awaiting-full-remote-CI', 'current_canonical_pins_changed': True, 'runtime_released': True,
          'lock_resolution': {'status': receipt['status'], 'commands_passed': 5, 'other_complete_lock_entries_unchanged': 19, 'receipt': row(RUN / 'receipt.json'), 'independent_review': row(REVIEW), 'scratch_removed': True, 'groups_closed': True, 'private_rebar3_staging_observed': True},
          'integration_packet': row(P / 'seal.sha256'), 'dependency_inventory': row(P / 'dependencies.json'), 'canonical_application': str(DEST.relative_to(R)),
          'pending': ['Full ordinary remote Phoenix CI on the applied pins', 'Two separately selected real HTTP/2 body batching/deadline checks', 'Production ingress/proxy and all existing operational/native/GA qualification']})
g['gates'][24]['hostedDependencyAdvisoryCorrection'] = copy.deepcopy(d)
old = 'A read-only dependency review confirms nineteen logged advisory matches in Bandit 1.13.1 and JOSE 1.11.12. The minimum two-pin correction to Bandit 1.14.0 and JOSE 1.11.13 is selected for isolated official lock generation and separate remote CI; canonical pins remain unchanged. Source exposure is distinguished from unverified deployment reachability. Two actual HTTP/2 body batching/deadline checks and all operational/GA qualification remain pending.'
new = 'Bandit 1.14.0 and JOSE 1.11.13 are applied with an officially generated and independently reviewed lock; all nineteen other complete lock entries are unchanged. The isolated five-command resolution passed and cleaned up its groups and scratch. Full remote CI on these pins is pending. Two actual HTTP/2 body batching/deadline checks and all operational/GA qualification remain pending.'
texts = {}
for n in ['PLAN.md', 'STATUS.md']:
    t = (R / n).read_text()
    assert t.count(old) == 1
    texts[n] = t.replace(old, new, 1)
for x in rows:
    (R / x['canonical_path']).write_bytes((R / x['proposed_path']).read_bytes())
for x in rows:
    assert row(R / x['canonical_path'])['sha256'] == x['proposed_sha256']
assert protected == {n: row(R / n) for n in protected}
result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'status': d['status'], 'canonical_files': [row(R / x['canonical_path']) for x in rows],
          'integration_seal': row(P / 'seal.sha256'), 'independent_resolution_review': row(REVIEW), 'selected_versions': d['selected_pins'], 'other_lock_entries_unchanged': 19,
          'runtime_qualification': 'Dependency resolution only; product compile/tests await full remote CI', 'protected_sources_unchanged': protected,
          'inflight_prepared_6_real_runtime': 'Unreleased; empirical controls exposed additional custody refusal/cleanup corrections; successor must pin these new dependency bytes', 'GA_accepted': False}
with DEST.open('x') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
for n, v in [('work-graph.json', w), ('gates/ga.json', g)]:
    (R / n).write_text(json.dumps(v, indent=2) + '\n')
for n, t in texts.items():
    (R / n).write_text(t)
print(row(DEST))
