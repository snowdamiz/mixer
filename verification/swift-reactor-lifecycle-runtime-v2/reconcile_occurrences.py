#!/usr/bin/env python3
"""Occurrence-complete supplement; never coalesce raw statement operands."""
import collections,gzip,json
import collect as c
import reconcile_runtime as r

summary=c.read_json(c.HERE/'unchanged-runtime-proof.json')
inventory=c.read_json(r.OLD/'inventory-final.json')
old_fnproof=c.read_json(r.OLD/'function-item-proof.json')['records']
all_positions=[];all_roles=[];all_fnroles=[];collisions=[];contexts=[];metadata=[]

def old_key(x):return (x['kind'],x['path'],x.get('promoted'),x.get('local'),x.get('location'),x.get('calleePath'))
def ordered(records,raw):
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
    return out

for context in summary['contexts']:
    cfg=context['config'];aq,ar,af,aa=r.load(r.OLD,cfg);bq,br,bf,ba=r.load(c.HERE,cfg)
    a=ordered(af,ar);b=ordered(bf,br)
    xa={x['key']:x for x in a};xb={x['key']:x for x in b};assert set(xa)==set(xb)and len(a)==len(b)
    mapping=context['finiteAllocationBijection'];hygiene=dict(context['finiteSourceHygieneIndexBijection']);reverse={v:k for k,v in hygiene.items()};before_hygiene=dict(hygiene)
    grouped={}
    for row in a:grouped.setdefault(old_key(row['record']),[]).append(row)
    missing_occurrences=[]
    for key,group in grouped.items():
        if len(group)==1:continue
        omitted=group[:-1];missing_occurrences+=omitted
        collisions.append({'config':cfg,'formerCoalescingKey':list(key),'occurrences':len(group),'oldAllOccurrences':group,'newAllOccurrences':[xb[x['key']]for x in group],'previouslyRetainedLastOccurrenceKey':group[-1]['key'],'previouslyOmittedOccurrences':[x['key']for x in omitted]})
    retained_set={c.sha(c.enc(x[-1]['record']))for x in grouped.values()}
    missing_distinct={c.sha(c.enc(x['record']))for x in a}-retained_set
    repeated_identical_omissions=sum(c.sha(c.enc(x['record']))in retained_set for x in missing_occurrences)
    full_counts=collections.Counter(c.sha(c.enc(x['record']))for x in a)
    duplicate_occurrences=sum(count-1 for count in full_counts.values())
    for key,old in xa.items():
        new=xb[key];assert old['bodyKindOrdinal']==new['bodyKindOrdinal']
        r.finite_metadata(old['record'],new['record'],None,mapping,hygiene,reverse,metadata,[cfg,'raw-occurrence',*key])
        all_positions.append({'config':cfg,'occurrenceKey':list(key),'bodyKindOrdinal':old['bodyKindOrdinal'],'oldRawRecordIndex':old['rawRecordIndex'],'newRawRecordIndex':new['rawRecordIndex'],'old':old['record'],'new':new['record'],'oldQuerySHA256':aq['sha256'],'newQuerySHA256':bq['sha256'],'everyRawOccurrencePreserved':True,'actualConstantValueSourceSpanFullIdentityAndLayoutMatched':True})
    canonical={(x['record']['path'],x['record'].get('promoted'),x['record']['local']):x for x in a if x['record']['kind']=='local'}
    operands={(x['record']['path'],x['record'].get('promoted'),x['bodyKindOrdinal']):x for x in a if x['record']['kind']=='constant-operand'}
    joined=collections.Counter()
    for role in inventory:
        if role['config']!=cfg:continue
        if role['kind']=='constant-operand':
            body_index=int(role['binding'].rsplit(':',1)[1])
            old=operands[(role['body'],role['promoted'],body_index)]
            assert role['source']==old['record']['constant']
            assert role['binding'].rsplit(':',1)[0]==old['record']['location']
            assert r.display_free(role['layout'])==r.display_free(old['record']['layout'])
            actual=xb[old['key']]['record']['layout']
        else:
            old=canonical[(role['body'],role['promoted'],role['local'])]
            assert role['sourceInfo']==old['record']['sourceInfo']
            if role['kind']=='captured-alias':actual=xb[old['key']]['record']['captureLayout']['fields'][role['capture']]
            else:
                assert r.display_free(role['layout'])==r.display_free(old['record']['layout'])
                actual=xb[old['key']]['record']['layout']
        assert role['actualIdentity']==actual['identity']and role['layout']['bytes']==actual['bytes']and role['layout']['alignment']==actual['alignment']
        joined[old['key']]+=1
        all_roles.append({'config':cfg,'field':role['field'],'role':role['position'],'kind':role['kind'],'occurrenceKey':list(old['key']),'bodyKindOrdinal':old['bodyKindOrdinal'],'oldRawRecordIndex':old['rawRecordIndex'],'newRawRecordIndex':xb[old['key']]['rawRecordIndex'],'sourceValueAndSpanJoinExact':True,'actualIdentity':actual['identity'],'bytes':actual['bytes'],'alignment':actual['alignment'],'noNumericCreditAdded':True})
    assert all(joined[x['key']]>=4 and joined[x['key']]%4==0 for x in a if x['record']['kind']in ['local','constant-operand'])
    # Function items retain their separate existing zero-sized four-role audit.
    by_old_fn={}
    for role in old_fnproof:
        if role['config']!=cfg:continue
        key=(role['body'],role.get('promoted'),role['location'],role['calleePath'],role['position'])
        by_old_fn.setdefault(key,[]).append(role)
    seen_fn=collections.Counter()
    for old in a:
        x=old['record']
        if x['kind']!='FnDef':continue
        new=xb[old['key']]['record'];assert x['layout']['bytes']==new['layout']['bytes']==0
        for position in ['source','argument','returned','caller']:
            key=(x['path'],x.get('promoted'),x['location'],x['calleePath'],position)
            candidates=by_old_fn[key];ordinal=seen_fn[key];seen_fn[key]+=1;role=candidates[ordinal]
            assert role['calleeDefPathHash']==x['calleeDefPathHash']==new['calleeDefPathHash']
            assert role['actualIdentity']==x['layout']['identity']==new['layout']['identity']
            all_fnroles.append({'config':cfg,'occurrenceKey':list(old['key']),'position':position,'oldRawRecordIndex':old['rawRecordIndex'],'newRawRecordIndex':xb[old['key']]['rawRecordIndex'],'calleePath':x['calleePath'],'calleeDefPathHash':x['calleeDefPathHash'],'oldActualLayout':x['layout'],'newActualLayout':new['layout'],'actualBytes':0,'noNumericCreditAdded':True})
    assert all(seen_fn[k]==len(v)for k,v in by_old_fn.items())
    counts=dict(collections.Counter(x['record']['kind']for x in a))
    contexts.append({'config':cfg,'rawOccurrences':len(a),'formerDictionaryRecords':len(grouped),'formerlyOmittedOccurrences':len(missing_occurrences),'formerlyOmittedDistinctRecords':len(missing_distinct),'formerlyOmittedOccurrencesIdenticalToRetained':repeated_identical_omissions,'totalIdenticalRawDuplicateOccurrences':duplicate_occurrences,'repeatedOccurrencesOfDistinctOmittedRows':len(missing_occurrences)-len(missing_distinct)-repeated_identical_omissions,'kinds':counts,'allRawOldAndNewOccurrencesMatched':True,'allLocalAndConstantRolesJoined':True,'additionalHygieneMappings':{k:v for k,v in hygiene.items()if k not in before_hygiene},'oldQuerySHA256':aq['sha256'],'newQuerySHA256':bq['sha256']})

assert len(all_roles)==11760
assert sum(x['formerlyOmittedDistinctRecords']for x in contexts)==78
assert sum(x['formerlyOmittedOccurrencesIdenticalToRetained']for x in contexts)==16
assert len(all_positions)==2744
assert sum(x['formerlyOmittedOccurrences']for x in contexts)==108
assert sum(x['totalIdenticalRawDuplicateOccurrences']for x in contexts)==30
c.save(c.HERE/'occurrence-complete-positions.json.gz',gzip.compress(c.enc(all_positions),mtime=0))
c.save(c.HERE/'occurrence-complete-role-joins.json.gz',gzip.compress(c.enc(all_roles),mtime=0))
c.save(c.HERE/'occurrence-complete-function-item-role-joins.json.gz',gzip.compress(c.enc(all_fnroles),mtime=0))
c.save(c.HERE/'former-key-collisions.json.gz',gzip.compress(c.enc(collisions),mtime=0))
c.save(c.HERE/'occurrence-complete-finite-metadata-differences.json.gz',gzip.compress(c.enc(metadata),mtime=0))
result={'schema':'mixer.swift-lifecycle.occurrence-complete-position-supplement.1','sourceClosure':summary['sourceClosure'],'contexts':contexts,'rawOccurrences':len(all_positions),'unitFourRoleJoins':len(all_roles),'functionItemZeroByteRoleJoins':len(all_fnroles),'formerlyOmittedOccurrences':108,'formerlyOmittedDistinctRecords':78,'formerlyOmittedOccurrencesIdenticalToRetained':16,'additionalRepeatedOccurrencesOfDistinctOmittedRows':14,'totalIdenticalRawDuplicateOccurrences':30,'allOriginalFrozenFilesUntouched':True,'newInstructionTypeLayoutOrNumericCredit':False,'compilerOrRuntimeRerun':False,'rootReviewPending':True}
c.save(c.HERE/'occurrence-complete-summary.json',result);print(c.enc(result).decode())
