#!/usr/bin/env python3
"""Replay documentation integrity checks; never authorizes a release."""
import json
import re
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
plan = (ROOT / 'mixer-product-plan.md').read_text()
work = json.loads((ROOT / 'work-graph.json').read_text())
old_work = json.loads((PACKET / 'inputs/work-graph.json').read_text())
gates = json.loads((ROOT / 'gates/ga.json').read_text())
old_gates = json.loads((PACKET / 'inputs/gates/ga.json').read_text())
changed_gates = {'G20', 'G22', 'G23', 'G24', 'G29', 'G30'}
checks = []


def check(name, condition):
    checks.append({'check': name, 'passed': bool(condition)})


check('all 18 packages retained and ordered',
      [p['id'] for p in work['packages']] == [f'W{i:02}' for i in range(1, 19)])
check('all 38 GA gates retained and ordered',
      [g['id'] for g in gates['gates']] == [f'G{i:02}' for i in range(1, 39)])
check('all package states preserved',
      [p['state'] for p in work['packages']] == [p['state'] for p in old_work['packages']])
check('all gate statuses and reviewers preserved',
      [(g['status'], g['reviewer']) for g in gates['gates']]
      == [(g['status'], g['reviewer']) for g in old_gates['gates']])
for name, old, current in [
    ('gate', old_gates['gates'], gates['gates']),
    ('package', old_work['packages'], work['packages']),
]:
    check(f'all prior {name} evidence preserved',
          all(set(a['evidence']) <= set(b['evidence']) for a, b in zip(old, current)))
check('unrelated gate requirements preserved',
      all(a['requirement'] == b['requirement']
          for a, b in zip(old_gates['gates'], gates['gates'])
          if a['id'] not in changed_gates))
check('all GA requirements agree with product plan',
      all(f"- [ ] {g['id']}: {g['requirement']}" in plan for g in gates['gates']))
for package in work['packages']:
    if package['id'] not in {'W11', 'W12', 'W14', 'W16'}:
        continue
    row = next(line for line in plan.splitlines() if line.startswith('| ' + package['id'] + ' '))
    cells = [cell.strip() for cell in row.split('|')[1:-1]]
    check(package['id'] + ' deliverables and acceptance agree with product plan',
          package['deliverables'] == cells[2] and package['acceptance'] == cells[4])
index = (ROOT / 'PLAN.md').read_text()
for name in ['Elixir', 'Phoenix', 'Bandit', 'Ecto', 'Postgrex', 'Oban', 'Neon',
             'Cloudflare Containers', 'Cloudflare R2', 'SolidJS', 'Solid Router',
             'Stripe Billing', 'Stripe Checkout', 'Customer Portal']:
    check('selected stack includes ' + name, name in plan or name in index)
check('obsolete Go hosted-service direction removed',
      '| Go services' not in plan and 'initial cloud region/vendor' not in plan)
check('Go reference and migration boundary explicit',
      'Existing independently authored Go services' in plan
      and '13.5 Hosted migration and qualification' in plan)
check('native testing pause remains recorded',
      'pauses computer use, screen capture and native' in index
      and 'paused computer use, screen capture' in (ROOT / 'STATUS.md').read_text())
check('no gate newly passed', not any(g['status'] == 'passed' for g in gates['gates']))
check('Markdown code fences remain paired',
      sum(line.startswith('```') for line in plan.splitlines()) % 2 == 0)
check('all 34 original top-level sections retained',
      [int(m.group(1)) for m in re.finditer(r'^## (\d+)\.', plan, re.M)] == list(range(1, 35)))
result = {'scope': 'documentation-and-plan-integrity-only', 'checks': checks,
          'passed': all(c['passed'] for c in checks), 'count': len(checks)}
(PACKET / 'integrity.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': result['passed'], 'checks': len(checks),
                  'failures': [c['check'] for c in checks if not c['passed']]}))
raise SystemExit(0 if result['passed'] else 1)
