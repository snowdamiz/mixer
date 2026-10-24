#!/usr/bin/env python3
"""Fresh inventory replay plus independent raw binding/alias enumeration."""
from pathlib import Path
from collections import Counter
import gzip,importlib.util,json,re,sys
import run as r
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def split_top(text):
    out=[];start=0;depth=0
    for i,ch in enumerate(text):
        depth+=(ch in '(<[{')-(ch in ')>]}')
        if ch==',' and depth==0:out.append(text[start:i].strip());start=i+1
    out.append(text[start:].strip());return [x for x in out if x]
def raw_functions(text):
    # MIR emits each item's closing delimiter at column zero. Parse every raw
    # item before choosing the growth namespace and exact free-function family.
    free={'growth_operation','growth_unsupported','growth_operation_inner','growth_pinned_caller','growth_pinned_step','release_growth_pending','complete_growth'}
    out=[]
    for match in re.finditer(r'^(fn|const) ([^\n]+)',text,re.M):
        kind,head=match.groups()
        if kind=='const':
            if '::promoted[' not in head:continue
            name=head.split(': &',1)[0];params=''
        else:
            at=head.index('(');end=at+1;depth=1
            while depth:depth+=(head[end]=='(')-(head[end]==')');end+=1
            name=head[:at];params=head[at+1:end-1]
        selected=('memory_growth_operations::' in name or name.split('::')[0] in free) and '::tests::' not in name and '::tests}' not in name
        if not selected:continue
        body=text[match.start():text.index('\n}',match.start())+2]
        decl={m.group(1):m.group(2) for m in re.finditer(r'^\s+let (?:mut )?(_\d+): (.*);\s*(?://[^\n]*)?$',body,re.M)}
        for arg in split_top(params):
            key,ty=arg.split(': ',1);decl[key]=ty
        aliases={}
        for m in re.finditer(r'^\s+debug (\w+) => (_\d+);',body,re.M):aliases.setdefault(m.group(2),[]).append(m.group(1))
        out.append((name,decl,aliases))
    return out
def projection(rows,qualify=False):
    keys=['field','rustType','binding','sourceNames','mirFunction','position','config','kind','envelope','window']
    out=[{k:x.get(k) for k in keys} for x in rows]
    if qualify:
        prefix='experimental_swift_reactor::execution::frame_operations::'
        for x in out:
            if x['mirFunction'] and x['mirFunction'].startswith(prefix+'memory_operations::'):x['mirFunction']=x['mirFunction'][len(prefix):]
    return out
def main():
    new=load('review_producer_growth_inventory',r.PRODUCER/'inventory.py');schema=json.loads((r.PRODUCER/'inventory-schema.json').read_text());reports=[]
    for features in ['all','swift']:
        for config in ['production','unit']:
            path=r.HERE/('fresh-'+features+'-'+config+'.mir.gz');text=gzip.decompress(path.read_bytes()).decode()
            rows,methods,_=new.canonical(path,config);expected=[x for x in schema if x['config']==config]
            assert projection(rows)==projection(expected)
            raw=raw_functions(text);assert {x[0]for x in raw}=={x['function']for x in methods}
            canonical=[x for x in expected if x['kind']=='canonical'];aliases=[x for x in expected if x['kind']=='authored-alias']
            for name,decl,debug in raw:
                bound=[x for x in canonical if x['mirFunction']==name]
                assert {(x['binding'],x['mirType'],x['position'])for x in bound}=={(binding,ty,role)for binding,ty in decl.items() for role in ['source','argument','returned','caller']}
                captured=[x for x in aliases if x['mirFunction']==name]
                assert len(captured)==4*sum(map(len,debug.values()))
                assert Counter((x['binding'],x['mirType'],x['position'])for x in captured)==Counter((alias,decl[binding],role)for binding,names in debug.items()for alias in names for role in ['source','argument','returned','caller'])
            old_counts={}
            for family,count in [('memory',4800),('bulk',4324)]:
                collector=load('review_old_'+family,r.PRODUCER/'inputs'/('accepted-'+family+'-inventory.py'));collector.promoted_constants=new.promoted_constants
                prior=json.loads((r.PRODUCER/'inputs'/('accepted-'+family+'-schema.json')).read_text());old,_,_=collector.canonical(path,config)
                assert len(prior)==count and projection(old,family=='memory')==projection([x for x in prior if x['config']==config],family=='memory');old_counts[family]=len(old)
            reports.append(dict(features=features,config=config,canonicalFields=len(canonical),canonicalBindings=len(canonical)//4,aliasFields=len(aliases),selectedItems=len(raw),items=[x[0]for x in raw],oldFields=old_counts))
    scratch=Path(json.loads((r.HERE/'scratch.json').read_text())['path']);source=(scratch/'candidate/src/experimental_swift_reactor/memory_growth_operations.rs').read_text()
    fields=re.findall(r'^    (\w+): ([^\n]+),$',source.split('// ACCOUNTING_START')[1],re.M)
    assert len(fields)==len(schema)==10356 and dict(fields)=={x['field']:x['rustType']for x in schema}
    authored=[x for x in schema if x['config']=='source'];assert len(authored)==808
    groups={}
    for x in authored:groups.setdefault((x['window'],x['binding'],x['rustType']),[]).append(x['position'])
    assert all(sorted(v)==['argument','caller','returned','source'] for v in groups.values())
    unit_raw=raw_functions(gzip.decompress((r.HERE/'fresh-all-unit.mir.gz').read_bytes()).decode())
    assert any(name=='growth_pinned_step::promoted[0]' for name,_,_ in unit_raw)
    assert any(name.rsplit('::',1)[-1]=='release_growth_pending' for name,_,_ in unit_raw)
    production_raw=raw_functions(gzip.decompress((r.HERE/'fresh-all-production.mir.gz').read_bytes()).decode())
    assert any(name=='release_growth_pending' for name,_,_ in production_raw)
    assert any('::preflight::promoted[0]' in name for name,_,_ in unit_raw)
    r.write(r.HERE/'inventory-audit.json',dict(totalFields=len(schema),authoredFields=len(authored),authoredObjects=len(groups),canonicalProductionFields=sum(x['config']=='production'for x in schema),canonicalUnitFields=sum(x['config']=='unit'for x in schema),rawCrossChecks=reports))
    print('PASS: fresh four MIR exact inventories, independent raw binding and alias cross-enumeration, all10356 schema fields, standalone promotions, old4800memory+4324bulk')
if __name__=='__main__':main()
