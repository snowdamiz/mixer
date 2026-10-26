#!/usr/bin/env python3
"""Read-only verifier for this static authored-source ledger, never Mixer code."""
import gzip
import json
from pathlib import Path
import sys
import ledger

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
for path,expected in ledger.EXPECTED.items():
    assert ledger.digest(path.read_bytes())==expected,str(path)
if (HERE/'seal.json').exists():
    seal=json.loads((HERE/'seal.json').read_text())
    for item in seal['members']: assert ledger.info(ROOT/item['path'])==item,item['path']
model=json.loads((ledger.REVIEW/'clear-block-ledger.json').read_text())
traces=ledger.make_traces(model)
summary=json.loads((HERE/'paths.json').read_text())
detail=json.loads(gzip.decompress((HERE/'path-segments.json.gz').read_bytes()))
assert len(summary['paths'])==len(traces)==len(detail['paths'])
for t,s,d in zip(traces,summary['paths'],detail['paths']):
    assert s['path']==t.name==d['path']
    expected=ledger.totals(t)
    for k,v in expected.items(): assert s[k]==v and d[k]==v,(t.name,k)
    assert d['segments']==t.segments,t.name
    actual=[x for x in t.ops if x['owner']=='G6']
    scalars=[x for x in actual if x['kind']=='scalar']
    copies=[x for x in actual if x['kind']=='copy']
    blocks=[scalars[i:i+16] for i in range(0,len(scalars),16)]
    assert all(1<=len(x)<=16 for x in blocks)
    assert [op for b in blocks for op in b]==scalars
    assert len(set(x['id'] for x in actual))==len(actual)
    assert all(0<x['bytes']<=128 for x in copies)
    clear=[x for x in actual if x['site'].startswith('anonymous clear128[')]
    if clear:
        assert sum(x['kind']=='scalar' for x in clear)==2768
        assert sum(x['kind']=='copy' for x in clear)==16
        assert all(x['bytes']==128 for x in clear if x['kind']=='copy')
    assert expected['actual_G6_groups']<=640
    # This is solely an upper comparison; G1 work is never in G6 partitions.
    assert expected['actual_G6_groups']<=expected['conservative_group_bound']
extremal=max(traces,key=lambda t:ledger.totals(t)['actual_G6_groups'])
operations=json.loads(gzip.decompress((HERE/'extremal-operations.json.gz').read_bytes()))
assert operations['operations']==extremal.ops and operations['path']==extremal.name
# Independently cross-check the direct-copy metadata grammar against the selected
# M01..M43 clear model, without repeat construction or product execution.
t=ledger.Trace('metadata-cross-check')
t.rangeview('c',ledger.K(0),ledger.K(128),array=True,exclusive=True)
t.opset('copy receiver reborrow','view.data -> copy received receiver.data','view.len -> copy received receiver.len',
        'anonymous array address formation','source shared borrow','array address -> source view.data',
        'array length128 -> source view.len','source view.data -> received copy source.data','source view.len -> received copy source.len')
t.copytail(128)
assert sum(x['kind']=='scalar' for x in t.ops)==43
assert sum(x['kind']=='copy' for x in t.ops)==1
assert len(model['per_initializer_component_edges'])==130
assert 16*(43+130)==2768
result={'status':'verified static source ledger only','command':[sys.executable,'-B',str(Path(__file__).resolve())],
        'python':sys.version,'source_sha256':ledger.SOURCE_SHA,
        'paths':len(traces),'maximum_G6':ledger.totals(extremal)['actual_G6_groups'],
        'extremal_path':extremal.name,'all_scalar_blocks_at_most16':True,
        'all_actual_payload_copies_at_most128':True,'selected_clear_189_reproduced':True,
        'G1_in_G6_partition':False,'runtime_compiler_product_executions':0,
        'implementation_accepted':False,'whole_lifetime_accepted':False}
print(json.dumps(result,indent=2))
