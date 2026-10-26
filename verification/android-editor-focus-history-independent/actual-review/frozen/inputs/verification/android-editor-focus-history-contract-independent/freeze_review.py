#!/usr/bin/env python3
"""Record bounded official-contract and released-source review; no source execution."""
from pathlib import Path
import datetime, hashlib, json, sys
D=Path(__file__).resolve().parent
ROOT=D.parents[1]
OLD=ROOT/'verification/android-editor-replacement-independent'
def row(path):
    data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
seal_path=OLD/'review-seal.json'
assert row(seal_path)['sha256']=='11cd26bbc78f54e48de297b931fab2fcb9becce4d4aa4884d145641f2a615b15'
members={member['path']:member for member in json.loads(seal_path.read_text())['members']}
focus=ROOT/'verification/android-editor-boundary-root-review/focus-history-amendment.md'
assert row(focus)['sha256']=='736476a269fae9a6745fbfbd5413a7ef231f57f9254c3279e41c2921d2088833'
inputs=D/'inputs';inputs.mkdir(exist_ok=False)
(inputs/'focus-history-amendment.md').write_bytes(focus.read_bytes())
specs={'NativeRenderer.java':[(93,109),(137,173),(274,312),(460,510),(534,565)],'NativeAppearanceViewsV2.java':[(65,121),(180,203),(282,300),(358,365),(946,978),(1170,1210)],'NativeOwnerV2.java':[(290,327)]}
excerpts=[];sources={}
for name,ranges in specs.items():
    relative='actual-review/frozen/source/'+name;source=OLD/relative
    actual=row(source);assert actual=={key:members[relative][key] for key in ['bytes','sha256']}
    sources[str(source.relative_to(ROOT))]=actual
    lines=source.read_text().splitlines()
    for start,end in ranges:
        excerpts.append('## '+name+':'+str(start)+'–'+str(end)+'\n\n```java\n'+'\n'.join(f'{n}: {lines[n-1]}' for n in range(start,end+1))+'\n```\n')
(D/'source-excerpts.md').write_text('# Released frozen source excerpts\n\n'+'\n'.join(excerpts))
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':sys.argv,'python':sys.version,'scope':'Bounded independent protocol review only; no implementation acceptance','decision':'suitable for root selection with stated exact refinements including journal-bound matching preservation','input_contract':{'path':str(focus.relative_to(ROOT)),**row(focus)},'reviewed_source_seal':row(seal_path),'reviewed_released_source':sources,'active_producer_reads':0,'new_product_tests_or_execution':0,'native_UI_capture_or_process_inventory':False,'canonical_Git_or_prior_sealed_writes':False,'new_child_processes':0,'cleanup':'No runtime, compiler, temporary child or scratch created; evidence files retained only in this owned new packet','pending':['Root precise protocol freeze before dependent edits','Future separate frozen actual-source implementation audit/replay','Native qualification after explicit resumption']}
(D/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
rows=[]
for path in sorted(D.rglob('*')):
    if path.is_file():rows.append({'path':str(path.relative_to(D)),**row(path)})
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Small independent focus-history protocol review only; no active-source or product execution','members':rows,'member_count':len(rows),'member_bytes':sum(item['bytes'] for item in rows)}
data=(json.dumps(seal,indent=2)+'\n').encode();(D/'seal.json').write_bytes(data)
print(json.dumps({'seal':str(D/'seal.json'),'sha256':hashlib.sha256(data).hexdigest(),'members':len(rows),'bytes':seal['member_bytes']}))
