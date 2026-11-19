#!/usr/bin/env python3
"""Print the README progress table from the plan records."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUPS = (
    ('█', {'passed', 'verified'}),
    ('▒', {'running', 'in_progress', 'review'}),
    ('✗', {'blocked', 'failed'}),
    ('░', {'planned', 'ready'}),
)


def load(name):
    return json.loads((ROOT / name).read_text())


def row(label, source, statuses):
    marks = [next(mark for mark, names in GROUPS if status in names) for status in statuses]
    counts = ' | '.join(str(marks.count(mark)) for mark, _ in GROUPS)
    return f"| {label} | `{''.join(marks)}` | {counts} | [`{source}`]({source}) |"


milestones = [m['localAcceptance'] for m in load('dogfood/receipts/milestones.json')['milestones']
              if m['localAcceptance']['requiredForPlanCompletion']]
rows = (
    ('Local gates L01–L08', 'gates/local.json',
     [g['status'] for g in load('gates/local.json')['gates']]),
    ('FieldLog milestones D0–D6, D8', 'dogfood/receipts/milestones.json',
     [m['status'] for m in milestones]),
    ('Work packages W01–W18', 'work-graph.json',
     [p['state'] for p in load('work-graph.json')['packages']]),
    ('Launch gates G01–G38', 'gates/ga.json',
     [g['status'] for g in load('gates/ga.json')['gates']]),
)
print('| Checklist | Progress | Passed | In progress | Blocked | Not started | Record |')
print('| --- | --- | --- | --- | --- | --- | --- |')
for label, source, statuses in rows:
    print(row(label, source, statuses))
