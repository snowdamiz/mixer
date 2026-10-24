#!/usr/bin/env python3
"""Finite whole-body allocation-graph isomorphism and exact position proof."""
from pathlib import Path
import collections,gzip,hashlib,importlib.util,json,re
import collect as c

OLD=c.ROOT/'verification/swift-reactor-lifecycle-accounting'
spec=importlib.util.spec_from_file_location('sealed_partition_annotations',OLD/'partition_annotations.py')
partition=importlib.util.module_from_spec(spec);spec.loader.exec_module(partition)

def load(root,cfg):
    query=c.read_json(root/f'exact-query-{cfg}.json')
    raw=gzip.decompress((root/query['attempt']/'exact-layouts.jsonl.gz').read_bytes())
    assert c.sha(raw)==query['sha256']
    records=[json.loads(line)for line in raw.splitlines()]
    filtered,annotations=partition.partition(records,cfg,query['sha256'])
    return query,records,filtered,annotations

def footer(body):
    # Actual declarations, never labels guessed from counts or arbitrary tokens.
    starts=list(re.finditer(r'^alloc\d+ \(size: \d+, align: \d+\) \{',body,re.M))
    return [(m.group().split(' ',1)[0],body[m.start():starts[i+1].start()if i+1<len(starts)else len(body)])for i,m in enumerate(starts)]

def rename(text,mapping):
    identifiers=re.findall(r'\balloc\d+\b',text)
    assert set(identifiers)<=set(mapping),'unbound allocation reference'
    return re.sub(r'\balloc\d+\b',lambda m:mapping[m[0]],text)

def display_free(value):
    # Session numeric DefIds retain every actual displayed definition path.
    if isinstance(value,str):return re.sub(r'DefId\(\d+:\d+ ~ ','DefId(<session-index> ~ ',value)
    if isinstance(value,list):return [display_free(x)for x in value]
    if isinstance(value,dict):return {k:display_free(v)for k,v in value.items()}
    return value

def finite_metadata(x,y,label,mapping,hygiene,hygiene_reverse,evidence,where):
    assert type(x)is type(y),(where,'metadata shape change')
    if isinstance(x,dict):
        assert set(x)==set(y)
        for k in x:finite_metadata(x[k],y[k],k,mapping,hygiene,hygiene_reverse,evidence,where+[k])
    elif isinstance(x,list):
        assert len(x)==len(y)
        for i,(a,b)in enumerate(zip(x,y)):finite_metadata(a,b,label,mapping,hygiene,hygiene_reverse,evidence,where+[i])
    elif isinstance(x,str)and x==y:
        if label in ['span','sourceInfo']:
            for index in re.findall(r'\(#(\d+)\)',x):
                assert index not in hygiene or hygiene[index]==index
                assert index not in hygiene_reverse or hygiene_reverse[index]==index
                hygiene[index]=index;hygiene_reverse[index]=index
    elif isinstance(x,str)and x!=y:
        if label=='constant':
            assert display_free(rename(x,mapping))==display_free(y),(where,'constant value changed')
            evidence.append({'field':where,'kind':'finite-allocation-reference-or-session-display','old':x,'new':y})
        elif label in ['span','sourceInfo']:
            old=re.findall(r'\(#(\d+)\)',x);new=re.findall(r'\(#(\d+)\)',y)
            assert len(old)==len(new)>0 and re.sub(r'\(#\d+\)','(#bound-context)',x)==re.sub(r'\(#\d+\)','(#bound-context)',y),(where,'source coordinates or scope changed')
            for a,b in zip(old,new):
                assert a not in hygiene or hygiene[a]==b
                assert b not in hygiene_reverse or hygiene_reverse[b]==a
                hygiene[a]=b;hygiene_reverse[b]=a
            evidence.append({'field':where,'kind':'finite-source-hygiene-index','old':x,'new':y,'sameFullFileCoordinatesAndScope':True,'fullExpansionChainQueried':False})
        else:
            assert display_free(x)==display_free(y),(where,'unexplained metadata change')
            evidence.append({'field':where,'kind':'compiler-session-display-index','old':x,'new':y,'sameDisplayedDefinitionPath':True})
    else:assert x==y,(where,'actual metadata scalar changed')

def main():
    all_bodies=[];all_positions=[];all_declarations=[];all_graphs=[];all_annotations=[];all_contexts=[];all_displays=[];all_metadata=[]
    for features in ['swift','all']:
        for profile in ['debug','release']:
            cfg=features+'-'+profile+'-unit'
            aq,ar,af,aa=load(OLD,cfg);bq,br,bf,ba=load(c.HERE,cfg)
            assert len(aa)==len(ba)==64
            key=lambda r:(r.get('path'),r.get('promoted'))
            a={key(r):r for r in af if r['kind']=='body'}
            b={key(r):r for r in bf if r['kind']=='body'}
            assert set(a)==set(b)
            mapping={};reverse={};body_footers={};hygiene={};hygiene_reverse={};metadata=[]
            for k in a:
                x=footer(a[k]['mir']);y=footer(b[k]['mir']);assert len(x)==len(y)
                body_footers[k]=(x,y)
                for (old,oldbody),(new,newbody) in zip(x,y):
                    assert old not in mapping or mapping[old]==new
                    assert new not in reverse or reverse[new]==old
                    mapping[old]=new;reverse[new]=old
            assert len(mapping)==len(reverse)
            body_rows=[]
            for k in sorted(a,key=lambda k:(k[0],-1 if k[1]is None else k[1])):
                x=a[k];y=b[k]
                assert x['defPathHash']==y['defPathHash']
                assert rename(x['mir'],mapping)==y['mir'],(cfg,k,'unexplained full-body change')
                oldfoot,newfoot=body_footers[k]
                graphs=[]
                for (oi,op),(ni,np)in zip(oldfoot,newfoot):
                    assert rename(op,mapping)==np
                    graphs.append({'oldID':oi,'newID':ni,'oldFullAllocation':op,'newFullAllocation':np,'payloadTextBytesAlignmentOffsetsAndRelocationsIdenticalAfterFiniteBijection':True,'oldReferences':re.findall(r'\balloc\d+\b',op),'newReferences':re.findall(r'\balloc\d+\b',np)})
                row={'config':cfg,'path':k[0],'promoted':k[1],'oldBody':x,'newBody':y,'oldFullBodySHA256':c.sha(x['mir'].encode()),'newFullBodySHA256':c.sha(y['mir'].encode()),'rawBodyChanged':x['mir']!=y['mir'],'fullBodyEqualAfterExactAllocationBijection':True,'oldOccurrences':re.findall(r'\balloc\d+\b',x['mir']),'newOccurrences':re.findall(r'\balloc\d+\b',y['mir']),'allocationGraphProof':graphs,'oldQuerySHA256':aq['sha256'],'newQuerySHA256':bq['sha256']}
                all_bodies.append(row);body_rows.append(row)
            # Local and constant/callee positions include every actual source span.
            def position_key(r):return (r['kind'],r['path'],r.get('promoted'),r.get('local'),r.get('location'),r.get('calleePath'))
            kinds=['local','constant-operand','FnDef']
            ap={position_key(r):r for r in af if r['kind']in kinds};bp={position_key(r):r for r in bf if r['kind']in kinds}
            assert set(ap)==set(bp)
            for k,x in ap.items():
                y=bp[k];finite_metadata(x,y,None,mapping,hygiene,hygiene_reverse,metadata,['position',*k])
                row={'config':cfg,'key':list(k),'old':x,'new':y,'rawDisplayChanged':x!=y,'sourceInfoChanged':x.get('sourceInfo')!=y.get('sourceInfo'),'actualIdentityFullLayoutCarrierAndSourceCoordinatesScopeEqual':True,'oldQuerySHA256':aq['sha256'],'newQuerySHA256':bq['sha256']}
                all_positions.append(row)
                if x!=y:all_displays.append(row)
            for kind in ['declaration','type-layout','type-graph']:
                ident=lambda r:r['path']if kind=='declaration'else r['identity']
                x={ident(r):r for r in ar if r['kind']==kind};y={ident(r):r for r in br if r['kind']==kind}
                assert set(x)==set(y),(cfg,kind,'new or missing actual type/carrier')
                for name,old in x.items():
                    new=y[name];finite_metadata(old,new,None,mapping,hygiene,hygiene_reverse,metadata,[kind,name])
                    row={'config':cfg,'kind':kind,'identity':name,'old':old,'new':new,'rawDisplayChanged':old!=new,'actualFullIdentityAndAllFieldsPreserved':True}
                    (all_declarations if kind=='declaration'else all_graphs).append(row)
                    if old!=new:all_displays.append(row)
            for x,y in zip(sorted(aa,key=lambda r:r['body']['path']),sorted(ba,key=lambda r:r['body']['path'])):
                for field in ['body','fieldName','actualParentFieldLayout','actualParentFieldGraph','actualLength','actualReturnLocal','actualConstantOperand','noFunctionItemOrCall','runtimeByteCredit']:
                    finite_metadata(x[field],y[field],field,mapping,hygiene,hygiene_reverse,metadata,['annotation',x['body']['path'],field])
                all_annotations.append({'config':cfg,'old':x,'new':y,'exactBodyParentFieldAndNoRuntimeCreditUnchanged':True})
            for row in metadata:row['config']=cfg
            all_metadata.extend(metadata)
            context={'config':cfg,'runtimeBodies':len(a),'rawBodyDifferences':sum(r['rawBodyChanged']for r in body_rows),'finiteAllocationBijection':mapping,'oldAndNewIdentifierSetsDistinct':len(mapping)==len(reverse),'everyOccurrenceAndAllocationGraphMatched':True,'finiteSourceHygieneIndexBijection':hygiene,'hygieneFullExpansionChainQueried':False,'positions':len(ap),'sourceInfoChanges':sum(r['config']==cfg and r['sourceInfoChanged']for r in all_positions),'sourceCoordinatesAndScopeChanges':0,'actualTypesLayoutsInstructionsOrCarriersChanged':False,'oldQuerySHA256':aq['sha256'],'newQuerySHA256':bq['sha256']}
            all_contexts.append(context)
    c.save(c.HERE/'runtime-body-reconciliation.json.gz',gzip.compress(c.enc(all_bodies),mtime=0))
    c.save(c.HERE/'runtime-position-reconciliation.json.gz',gzip.compress(c.enc(all_positions),mtime=0))
    c.save(c.HERE/'owner-carrier-layout-reconciliation.json.gz',gzip.compress(c.enc(all_declarations),mtime=0))
    c.save(c.HERE/'actual-type-graph-reconciliation.json.gz',gzip.compress(c.enc(all_graphs),mtime=0))
    c.save(c.HERE/'annotation-reconciliation.json.gz',gzip.compress(c.enc(all_annotations),mtime=0))
    c.save(c.HERE/'compiler-session-display-differences.json.gz',gzip.compress(c.enc(all_displays),mtime=0))
    c.save(c.HERE/'finite-metadata-differences.json.gz',gzip.compress(c.enc(all_metadata),mtime=0))
    summary={'schema':'mixer.swift-lifecycle.test-repair-unchanged-runtime-proof.1','sourceClosure':c.read_json(c.HERE/'source-delta.json')['candidateClosure'],'contexts':all_contexts,'runtimeBodies':len(all_bodies),'rawBodyDifferences':sum(r['rawBodyChanged']for r in all_bodies),'canonicalActualBodyChanges':0,'positions':len(all_positions),'sourceInfoChanges':sum(r['sourceInfoChanged']for r in all_positions),'sourceCoordinatesAndScopeChanges':0,'newOrMissingRuntimePositions':0,'fullOwnerCarrierDeclarations':len(all_declarations),'fullTypeGraphAndLayoutRecords':len(all_graphs),'ctfeAnnotations':len(all_annotations),'rawDifferingPositionOrTypeRecords':len(all_displays),'finiteMetadataDifferenceKinds':dict(collections.Counter(r['kind']for r in all_metadata)),'finiteAllocationAndHygieneRepresentationSelectionPending':True,'hygieneFullExpansionChainQueried':False,'numericAccountingChanged':False,'runtimeRun':False}
    c.save(c.HERE/'unchanged-runtime-proof.json',summary);print(c.enc(summary).decode())

if __name__=='__main__':main()
