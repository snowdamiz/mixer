#!/usr/bin/env python3
"""Seal the complete owned scoped review after independent compilation."""
from pathlib import Path
import datetime, hashlib, json, re

D = Path(__file__).resolve().parent
assert not (D/'seal.json').exists()

def ident(path):
    b = path.read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def save(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')

proof = {}
for name in ('finishV2', 'fieldPreservationBegin', 'fieldPreservationEnd'):
    lines = (D/(name+'-scalar-tail.bytecode')).read_text().splitlines()
    offsets = [int(re.match(r'\s*(\d+):', line)[1]) for line in lines]
    targets = []
    for line in lines:
        m = re.search(r':\s+(?:if\w*|goto)\s+(\d+)', line)
        if m:
            targets.append(int(m[1]))
    assert all(target in offsets for target in targets)
    assert 'Exception table:' not in (D/(name+'-full.bytecode')).read_text()
    proof[name] = {'all_tail_branch_targets_within_tail': True, 'tail_branch_targets': targets, 'method_has_no_exception_handlers': True}

text = (D/'completion-bytecode.stdout').read_text()
body = text[text.index('  void completeFailedV2('):text.index('  void finishV2(')]
lines = [line for line in body.splitlines() if re.match(r'\s+\d+:', line)]
tail = [line for line in lines if int(re.match(r'\s*(\d+):', line)[1]) >= 701]
assert tail[0].strip() == '701: iconst_0'
assert not any(re.search(r': (?:invoke\w*|new\w*|anewarray|multianewarray|monitor\w*)\b', line) for line in tail)
assert [line.strip().split(':')[0] for line in tail if ': athrow' in line] == ['824']
(D/'completeFailedV2-release-tail.bytecode').write_text('\n'.join(tail)+'\n')
(D/'completeFailedV2-full.bytecode').write_text(body)
proof['completeFailedV2'] = {'scalar_release_tail_start': 701, 'no_invocation_allocation_monitor_after_release_phase_starts': True, 'only_explicit_throw_after_release_is_retained_firstFatal': 824, 'tail': ident(D/'completeFailedV2-release-tail.bytecode')}
save(D/'additional-bytecode-proof.json', proof)

assert json.loads((D/'execution-receipt.json').read_text())['status'] == 'passed-scoped-host-compilation-and-bytecode-only'
assert not list(D.glob('owned-*'))
assert not list(D.rglob('__pycache__'))
members = [{'path': str(p.relative_to(D)), **ident(p)} for p in sorted(D.rglob('*')) if p.is_file() and p.name not in ('seal.json', 'manifest.json')]
save(D/'manifest.json', members)
save(D/'seal.json', {
    'schema': 1,
    'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'verdict': 'no-blocking-finding-in-focused-actual-source-and-independent-host-bytecode-review',
    'candidate_seal_sha256': '8f355ae83ec4d734e8d28451fc64a45200967a718eecb7c1987fa0fcc69d9920',
    'product_tree': 'cb5c2b813b9cb375f2907bafcb066ba9c556a2713ffd04c9d74777d9595d01e4',
    'member_count': len(members),
    'member_bytes': sum(member['bytes'] for member in members),
    'manifest': ident(D/'manifest.json'),
    'members': members,
    'main_independent_behavioral_review_not_duplicated': True,
    'native_OTA_canonical_publicV2_release_dogfood_or_GA_accepted': False,
    'cleanup': {'owned_scratch_removed': True, 'owned_children_reaped': True, 'maximum_child_seconds': 60, 'native_UI_capture_or_process_inventory_started_or_queried': False, 'other_projects_touched': False},
})
print(json.dumps({'seal': ident(D/'seal.json'), 'manifest': ident(D/'manifest.json'), 'members': len(members), 'member_bytes': sum(member['bytes'] for member in members)}, indent=2))
