#!/usr/bin/env python3
"""Independent provenance and fresh nested-field occupation checks; no VM execution."""
from pathlib import Path
import collections,gzip,hashlib,json,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PACKET=ROOT/'verification/swift-control-accounting-candidate-2'
RESULT=PACKET/'results/20261024T065629251176Z'
def raw(p):return p.read_bytes() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes())
def read(p):return json.loads(raw(p))
def sha(b):return hashlib.sha256(b).hexdigest()
rows=read(RESULT/'bound-inventory-schema.json')
provenance={}
for config in ['production','unit']:
    data=raw(RESULT/f'swift-debug-{config}.mir');text=data.decode()
    spans=set(re.findall(r'src/[\w./-]+:\d+:\d+: \d+:\d+',text))
    selected=[r for r in rows if r['config']==config]
    assert all(r['qualifyingMIRSHA256']==sha(data) for r in selected)
    assert all(r['sourceSpans'] and set(r['sourceSpans'])<=spans for r in selected)
    provenance[config]=dict(fields=len(selected),canonicalMIRSHA256=sha(data),sourceSpansBound=True)
layouts=read(HERE/'independent-layouts.json')
for layout in layouts:
    key=(layout['config'],layout['profile'],layout['unit'])
    nested=next(n for n in read(RESULT/'nested-layout-receipt.json')['layouts'] if (n['config'],n['profile'],n['unit'])==key)
    assert layout['field']['private_scalar_transfers']==[nested['offset'],nested['bytes'],nested['alignment']]
    intervals=collections.defaultdict(list)
    for row in rows:
        if row['config']=='unit' and not layout['unit']:continue
        offset,size,align=layout['field'][row['field']]
        cls=row['ownerClass'];assert offset%align==0
        assert offset+size<=layout['class'][cls][0]
        if size:intervals[cls].append((offset,offset+size))
    intervals['ActivePositions'].append((nested['offset'],nested['offset']+nested['bytes']))
    for cls,spans in intervals.items():
        last=0
        for start,end in sorted(spans):assert start>=last,(key,cls,start,last);last=end
output=dict(status='passed',sourceProvenance=provenance,freshMetadataConfigurations=len(layouts),freshNestedComponentAndAllFieldsNonOverlapping=True,controlOperationsExecuted=False)
(HERE/'supplement.json').write_text(json.dumps(output,sort_keys=True,indent=2)+'\n')
print('passed: canonical source/MIR provenance; fresh measured nested component and every positive field non-overlapping')
