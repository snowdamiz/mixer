#!/usr/bin/env python3
"""Choose exact actual reached identities; prefer non-rollback positive setup when available."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
bindings={}
for number in [2,3,4,5]:
    for path in sorted((HERE/f'matrix-discovery-{number}').glob('*.stdout')):
        for line in path.read_text().splitlines():
            if line.startswith('{'):
                value=json.loads(line)
                for row in value.get('reached',[]):
                    if row['phase']=='entry':bindings.setdefault(row['id'],[]).append(dict(scenario=value['scenario'],**row))
def rank(row):
    s=row['scenario']
    return (0 if s=='initial' else 1 if s=='initial-section' else 3 if s.startswith('rollback') else 4 if s=='initial-commit-failure' else 2,s,row['leaf'])
lines=[]
for line in (HERE/'matrix-sites.tsv').read_text().splitlines():
    identifier=line.split('\t')[0];row=min(bindings[identifier],key=rank)
    lines.append('\t'.join([identifier,row['scenario'],row['leaf'],row['class'],row['method'],row['descriptor'],str(row['bci'])]))
assert len(lines)==189
(HERE/'matrix-targets.tsv').write_text('\n'.join(lines)+'\n')
