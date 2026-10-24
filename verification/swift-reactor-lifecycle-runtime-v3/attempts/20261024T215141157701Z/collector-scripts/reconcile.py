#!/usr/bin/env python3
"""Finite whole-body allocation-graph isomorphism and exact position proof."""
from pathlib import Path
import collections,gzip,hashlib,importlib.util,json,re
import collect as c

OLD=c.ROOT/'verification/swift-reactor-lifecycle-runtime-v2'
import partition_annotations as partition
from finite_metadata import footer,rename,display_free,finite_metadata
import role_joins

def load(root,cfg):
    query=c.read_json(root/f'exact-query-{cfg}.json')
    raw=gzip.decompress((root/query['attempt']/'exact-layouts.jsonl.gz').read_bytes())
    assert c.sha(raw)==query['sha256']
    records=[json.loads(line)for line in raw.splitlines()]
    filtered,annotations=partition.partition(records,cfg,query['sha256'])
    return query,records,filtered,annotations

def ordered(records,raw):
    # Object identity retains exact raw indices even for byte-identical duplicate rows.
    indices={id(x):i for i,x in enumerate(raw)}
    seen=collections.Counter();body_ord=collections.Counter();out=[]
    for x in records:
        if x['kind']not in ['local','constant-operand','FnDef']:continue
        location=x.get('location')if x['kind']!='local'else 'local:'+str(x['local'])
        stem=(x['path'],x.get('promoted'),x['kind'],location)
        key=(*stem,seen[stem]);seen[stem]+=1
        bk=(x['path'],x.get('promoted'),x['kind']);ordinal=body_ord[bk];body_ord[bk]+=1
        out.append({'key':key,'bodyKindOrdinal':ordinal,'rawRecordIndex':indices[id(x)],'record':x})
    assert len({x['key']for x in out})==len(out)
    assert collections.Counter(c.enc(x['record'])for x in out)==collections.Counter(c.enc(x)for x in records if x['kind']in ['local','constant-operand','FnDef'])
    return out

def build():
    outputs={}
    all_bodies=[];all_positions=[];all_declarations=[];all_graphs=[];all_annotations=[];all_contexts=[];all_displays=[];all_metadata=[]
    for features in ['swift','all']:
        for profile in ['debug','release']:
            cfg=features+'-'+profile+'-unit'
            aq,ar,af,aa=load(OLD,cfg);bq,br,bf,ba=load(c.HERE,cfg)
            assert len(aa)==len(ba)==64
            key=lambda r:(r.get('path'),r.get('promoted'))
            a={key(r):r for r in af if r['kind']=='body'}
            b={key(r):r for r in bf if r['kind']=='body'}
            assert len(a)==sum(x['kind']=='body'for x in af) and len(b)==sum(x['kind']=='body'for x in bf)
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
            # Ordered occurrences from the original raw stream: never collapse operands.
            ap=ordered(af,ar);bp=ordered(bf,br)
            assert len(ap)==len(bp) and [x['key']for x in ap]==[x['key']for x in bp]
            for old,new in zip(ap,bp):
                k=old['key'];x=old['record'];y=new['record']
                assert old['bodyKindOrdinal']==new['bodyKindOrdinal']
                finite_metadata(x,y,None,mapping,hygiene,hygiene_reverse,metadata,['raw-occurrence',*k])
                row={'config':cfg,'occurrenceKey':list(k),'bodyKindOrdinal':old['bodyKindOrdinal'],'oldRawRecordIndex':old['rawRecordIndex'],'newRawRecordIndex':new['rawRecordIndex'],'old':x,'new':y,'rawDisplayChanged':x!=y,'sourceInfoChanged':x.get('sourceInfo')!=y.get('sourceInfo'),'actualIdentityFullLayoutCarrierAndSourceCoordinatesScopeEqual':True,'oldQuerySHA256':aq['sha256'],'newQuerySHA256':bq['sha256']}
                all_positions.append(row)
                if x!=y:all_displays.append(row)
            for kind in ['declaration','type-layout','type-graph']:
                ident=lambda r:r['path']if kind=='declaration'else r['identity']
                x={ident(r):r for r in ar if r['kind']==kind};y={ident(r):r for r in br if r['kind']==kind}
                assert len(x)==sum(r['kind']==kind for r in ar)and len(y)==sum(r['kind']==kind for r in br)
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
    outputs['runtime-body-reconciliation.json.gz']=gzip.compress(c.enc(all_bodies),mtime=0)
    outputs['runtime-position-reconciliation.json.gz']=gzip.compress(c.enc(all_positions),mtime=0)
    outputs['owner-carrier-layout-reconciliation.json.gz']=gzip.compress(c.enc(all_declarations),mtime=0)
    outputs['actual-type-graph-reconciliation.json.gz']=gzip.compress(c.enc(all_graphs),mtime=0)
    outputs['annotation-reconciliation.json.gz']=gzip.compress(c.enc(all_annotations),mtime=0)
    outputs['compiler-session-display-differences.json.gz']=gzip.compress(c.enc(all_displays),mtime=0)
    outputs['finite-metadata-differences.json.gz']=gzip.compress(c.enc(all_metadata),mtime=0)
    summary={'schema':'mixer.swift-lifecycle.test-repair-unchanged-runtime-proof.1','sourceClosure':c.read_json(c.HERE/'source-delta.json')['candidateClosure'],'contexts':all_contexts,'runtimeBodies':len(all_bodies),'rawBodyDifferences':sum(r['rawBodyChanged']for r in all_bodies),'canonicalActualBodyChanges':0,'positions':len(all_positions),'sourceInfoChanges':sum(r['sourceInfoChanged']for r in all_positions),'sourceCoordinatesAndScopeChanges':0,'newOrMissingRuntimePositions':0,'fullOwnerCarrierDeclarations':len(all_declarations),'fullTypeGraphAndLayoutRecords':len(all_graphs),'ctfeAnnotations':len(all_annotations),'rawDifferingPositionOrTypeRecords':len(all_displays),'finiteMetadataDifferenceKinds':dict(collections.Counter(r['kind']for r in all_metadata)),'finiteAllocationAndHygieneRepresentationSelectionPending':True,'hygieneFullExpansionChainQueried':False,'numericAccountingChanged':False,'runtimeRun':False}
    outputs['unchanged-runtime-proof.json']=summary);print(c.enc(summary).decode()

if __name__=='__main__':
    outputs=build()
    for name,raw in outputs.items():c.save(c.HERE/name,raw)
    print(outputs['unchanged-runtime-proof.json'].decode())
