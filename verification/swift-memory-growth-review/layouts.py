#!/usr/bin/env python3
"""Independent raw layout parser, arithmetic audit, and fresh paired replay."""
from pathlib import Path
import gzip,json,re,sys
import run as r
from compile import compile_context
def parse(data):
    value=dict(types={},owners={},newTypes={},newOwners={},classes={},fields={},totals={})
    for line in data.splitlines():
        m=re.search(r'MG_(TYPE|OWNER|NEWTYPE|NEWOWNER|CLASS|FIELD|TOTAL) (\S+) (\d+)(?: (\d+))?(?: (\d+))?',line)
        if not m:continue
        kind,name,a,b,c=m.groups();a=int(a)
        table={'TYPE':'types','OWNER':'owners','NEWTYPE':'newTypes','NEWOWNER':'newOwners','CLASS':'classes','FIELD':'fields','TOTAL':'totals'}[kind]
        assert name not in value[table],(table,name)
        value[table][name]=(dict(offset=a,bytes=int(b),alignment=int(c)) if kind=='FIELD' else dict(bytes=a,alignment=int(b)) if kind in ['TYPE','NEWTYPE','CLASS'] else a)
    return value
def audit(value,expected,schema):
    for key in value:assert value[key]==expected[key],key
    if expected['label']=='baseline':return []
    fields={x['field']:x for x in schema if expected['unit'] or x['config']!='unit'}
    assert set(value['fields'])==set(fields)
    rows=[]
    for cls,container in value['classes'].items():
        intervals=[];payload=0
        for name,layout in value['fields'].items():
            if fields[name]['ownerClass']!=cls:continue
            off,n,a=layout['offset'],layout['bytes'],layout['alignment']
            assert off%a==0 and off+n<=container['bytes']
            payload+=n
            if n:intervals.append((off,off+n,name))
        end=0;holes=[]
        for start,stop,name in sorted(intervals):
            assert start>=end,(cls,name)
            if start>end:holes.append((end,start))
            end=stop
        if end<container['bytes']:holes.append((end,container['bytes']))
        padding=sum(b-a for a,b in holes)
        assert payload+padding==container['bytes']
        assert padding==(4 if expected['unit'] and cls=='ActivePositions' else 0)
        rows.append(dict(ownerClass=cls,payloadBytes=payload,paddingBytes=padding,containingBytes=container['bytes'],holes=holes))
    return rows
def main():
    layouts=json.loads((r.PRODUCER/'layouts.json').read_text());schema=json.loads((r.PRODUCER/'inventory-schema.json').read_text());rows=[]
    commands=json.loads((r.PRODUCER/'command-index.json').read_text())
    for row in layouts:
        name='layout-qualified-'+row['label']+'-'+row['features']+'-'+row['profile']+('-unit' if row['unit'] else '-production')
        raw=gzip.decompress((r.PRODUCER/'commands'/name/'stdout.gz').read_bytes()).decode()
        value=parse(raw);padding=audit(value,row,schema)
        paired=next(v for v in layouts if v['label']=='baseline' and all(v[k]==row[k] for k in ['features','profile','unit']))
        assert row['types']==paired['types'] and row['owners']==paired['owners']
        if row['features']=='all':assert value['totals']['frozen_header']==2912
        if row['label']=='candidate':
            t=value['totals'];assert t['header']==paired['totals']['header']+t['growth_permanent'];assert t['frame']==paired['totals']['frame']+t['growth_active']
            assert t['growth_permanent']==(559472 if row['unit'] else 316376) and t['growth_active']==(1815568 if row['unit'] else 973920)
            assert t['state_limit']==128*1024*1024 and t['combined_limit']==256*1024*1024
        rows.append(dict(command=name,rawSHA256=r.sha(raw.encode()),padding=padding))
    r.write(r.HERE/'raw-layout-audit.json',rows)
    scratch=Path(json.loads((r.HERE/'scratch.json').read_text())['path']);fresh=[]
    for label in ['baseline','candidate']:
        original=r.archive(r.PRODUCER/(label+'-source.tar.gz'))
        for features,profile,unit in [('swift','debug',False),('all','release',True)]:
            name='layout-qualified-'+label+'-'+features+'-'+profile+('-unit' if unit else '-production');digest=commands[name]['sourceTreeSHA256'];derived=r.archive(r.PRODUCER/'sources'/(digest+'.tar.gz'))
            assert all(derived[p].startswith(data) for p,data in original.items());assert set(derived)-set(original)=={'src/bin/growth_contract_layout.rs'}
            tree=scratch/('layout-'+label+'-'+features+'-'+profile+('-unit'if unit else'-production'));r.extract(derived,tree)
            context='fresh-layout-'+label+'-'+features+'-'+profile+('-unit'if unit else'-production')
            if unit:
                binary,env=compile_context(context,tree,features,profile,'layout',True)
                argv=[binary,'growth_contract_metadata_only','--nocapture','--test-threads=1']
            else:
                target=scratch/('target-source-'+digest)/(features+'-'+profile+'-production-layout');env={'CARGO_TARGET_DIR':str(target)}
                argv=['cargo','build','--locked','--offline','--message-format=json','--bin','growth_contract_layout','--features','experimental-swift-reactor']
                p,_=r.run(context+'-compile',argv,cwd=tree,env=env,source=tree);assert p.returncode==0,p.stderr.decode()
                messages=[json.loads(x) for x in p.stdout.decode().splitlines() if x.startswith('{')];binary=next(x['executable'] for x in messages if x.get('reason')=='compiler-artifact' and x.get('target',{}).get('name')=='growth_contract_layout')
                r.write(r.HERE/'commands'/(context+'-compile')/'artifacts.json',[dict(path=binary,sha256=r.sha(Path(binary).read_bytes()),bytes=Path(binary).stat().st_size)])
                argv=[binary]
            p,_=r.run(context+'-execute',argv,cwd=tree,env=env,source=tree,binary=[binary]);assert p.returncode==0,p.stderr.decode()
            expected=next(v for v in layouts if (v['label'],v['features'],v['profile'],v['unit'])==(label,features,profile,unit))
            value=parse(p.stdout.decode());audit(value,expected,schema);fresh.append(dict(command=context+'-execute',matchesAllRawFields=True,measuredFieldCount=len(value['fields']),totals=value['totals']))
    r.write(r.HERE/'fresh-layout-audit.json',fresh)
    print('PASS independent raw 16 configurations; fresh 4 representative baseline/candidate production/unit configurations')
if __name__=='__main__':main()
