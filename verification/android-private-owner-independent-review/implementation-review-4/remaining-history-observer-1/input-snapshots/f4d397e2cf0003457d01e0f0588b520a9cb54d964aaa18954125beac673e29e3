#!/usr/bin/env python3
"""Independent decoder verifies exact ordered trace integrity; tail policy is a separate source review."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib
import json
import sys
HERE=Path(__file__).resolve().parent

def expand(trace):
    assert trace['schema']==1
    identities=[]
    for event in trace['events']:
        prefix,ids=event['identity'].split(':',1)
        stack=[trace['frames'][int(index)] for index in ids.split('|')] if ids else []
        identities.append((prefix,stack))
    counts=Counter();ordered=[]
    for index,count in trace['runs']:
        assert count>0 and 0<=index<len(identities)
        counts[index]+=count;ordered.extend([identities[index]]*count)
    assert [counts[index] for index in range(len(identities))]==[event['count'] for event in trace['events']]
    assert len(ordered)==trace['length']
    raw=''.join(prefix+':'+('|'.join(stack))+'\n' for prefix,stack in ordered)
    assert hashlib.sha256(raw.encode()).hexdigest()==trace['expanded_sha256']
    return ordered

def main():
    batches=[int(value) for value in sys.argv[1:]]
    rows=[];pending=defaultdict(list)
    for number in batches:
        out=HERE/f'matrix-execution-{number}'
        for path in sorted(out.glob('02-*.stdout')):
            command=json.loads(path.with_suffix('.command.json').read_text());assert command['exit_code']==0,(path,command['exit_code'])
            for line in path.read_text().splitlines():
                if not line.startswith('{'):continue
                row=json.loads(line)
                if 'variant' not in row:continue
                ordered=expand(row['orderedTrace'])
                rows.append(dict(id=row['id'],variant=row['variant'],source=str(path.relative_to(HERE)),assertions=row['assertions'],ordered_events=len(ordered),expanded_sha256=row['orderedTrace']['expanded_sha256']))
                if row['variant']=='clean' or row['variant'].startswith('dirty') and row['before']['operationPresent']:continue
                exact=row['class']+'#'+row['method']+row['descriptor']+'@'+str(row['bci'])
                for prefix,stack in ordered:
                    if not prefix.endswith('/entry'):continue
                    top=stack[0] if stack else ''
                    if top.startswith(exact+':'):continue
                    pending[(prefix,top)].append(row['id']+'/'+row['variant'])
    unique={(row['id'],row['variant']) for row in rows};assert len(rows)==len(unique)
    result=dict(scope='Trace identity/integrity only; subsequent-call authority classification and complete implementation qualification separate',batches=batches,executed_unique_rows=len(rows),assertions=sum(row['assertions'] for row in rows),all_ordered_expansions_and_hashes_valid=True,rows=rows,source_classification_candidates=[dict(native=key[0],top_frame=key[1],affected_rows=sorted(set(values))) for key,values in sorted(pending.items())])
    (HERE/'matrix-trace-integrity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(rows=len(rows),assertions=result['assertions'],classification_candidate_pairs=len(pending))))

if __name__=='__main__':main()
