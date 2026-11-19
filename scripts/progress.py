#!/usr/bin/env python3
"""Print the README progress table from the plan records."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLUMNS = (
    ('Passed', {'passed', 'verified'}),
    ('In progress', {'running', 'in_progress', 'review'}),
    ('Blocked', {'blocked', 'failed'}),
    ('Not started', {'planned', 'ready'}),
)


def load(name):
    return json.loads((ROOT / name).read_text())


def count(label, statuses):
    known = set().union(*(names for _, names in COLUMNS))
    unknown = set(statuses) - known
    if unknown:
        raise SystemExit(f'{label}: unknown status {sorted(unknown)}')
    return [sum(status in names for status in statuses) for _, names in COLUMNS]


milestones = [m['localAcceptance'] for m in load('dogfood/receipts/milestones.json')['milestones']
              if m['localAcceptance']['requiredForPlanCompletion']]
rows = [
    ('Local gates L01–L08', 'gates/local.json',
     [g['status'] for g in load('gates/local.json')['gates']]),
    ('FieldLog milestones D0–D6, D8', 'dogfood/receipts/milestones.json',
     [m['status'] for m in milestones]),
    ('Work packages W01–W18', 'work-graph.json',
     [p['state'] for p in load('work-graph.json')['packages']]),
    ('Launch gates G01–G38', 'gates/ga.json',
     [g['status'] for g in load('gates/ga.json')['gates']]),
]
counts = [count(label, statuses) for label, _, statuses in rows]
shown = [i for i, (name, _) in enumerate(COLUMNS)
         if name != 'Blocked' or any(row[i] for row in counts)]
print('| Checklist | ' + ' | '.join(COLUMNS[i][0] for i in shown) + ' |')
print('| --- |' + ' :-: |' * len(shown))
for (label, source, _), row in zip(rows, counts):
    print(f'| [{label}]({source}) | ' + ' | '.join(str(row[i]) for i in shown) + ' |')
