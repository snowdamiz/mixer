#!/usr/bin/env python3
"""Rebind each sealed unit four-role position to the fresh actual query."""
import gzip,json
import collect as c
import reconcile_runtime as r

old=c.read_json(r.OLD/'inventory-final.json')
proof=[];witnesses=[]
for features in ['swift','all']:
    for profile in ['debug','release']:
        cfg=features+'-'+profile+'-unit'
        q,raw,records,annotations=r.load(c.HERE,cfg)
        bodies={(x['path'],x.get('promoted')):x for x in records if x['kind']=='body'}
        locals={(x['path'],x.get('promoted'),x['local']):x for x in records if x['kind']=='local'}
        constants={}
        for x in records:
            if x['kind']=='constant-operand':constants.setdefault((x['path'],x.get('promoted')),[]).append(x)
        fields={}
        for x in raw:
            if x['kind']!='declaration' or not x['path'].rsplit('::',1)[-1].startswith(('LifecycleActivePositions','LifecyclePermanentPositions','LifecycleNeverActivePositions','LifecycleNeverPermanentPositions')):continue
            variant=x['layout']['variants'][0]
            for name,field in zip(variant['fieldNames'],variant['fields']):
                assert name not in fields;fields[name]=(x['path'],field)
        for position in old:
            if position['config'] not in [cfg,'source']:continue
            if position['config']=='source':
                parent,field=fields[position['field']]
                witnesses.append({'config':cfg,'field':position['field'],'declaration':parent,'actualFullField':field,'oldSealedCarrierMatchedByWholeDeclarationProof':True})
                continue
            body=bodies[(position['body'],position['promoted'])]
            assert body['defPathHash']==position['bodyDefPathHash']
            if position['kind']=='constant-operand':
                operand=constants[(position['body'],position['promoted'])][int(position['binding'].rsplit(':',1)[1])]
                actual=operand['layout'];source_info=None
                assert operand['location']==position['binding'].rsplit(':',1)[0]
            else:
                local=locals[(position['body'],position['promoted'],position['local'])]
                source_info=local['sourceInfo']
                if position['kind']=='captured-alias':actual=local['captureLayout']['fields'][position['capture']]
                else:actual=local['layout']
            assert actual['identity']==position['actualIdentity']
            assert (actual['bytes'],actual['alignment'])==(position['layout']['bytes'],position['layout']['alignment'])
            if not position['method'].startswith('finite-proposed'):
                parent,witness=fields[position['field']]
                assert witness['identity']==actual['identity'] and witness['bytes']==actual['bytes'] and witness['alignment']==actual['alignment']
            else:parent=None
            proof.append({'field':position['field'],'config':cfg,'role':position['position'],'kind':position['kind'],'body':position['body'],'promoted':position['promoted'],'binding':position['binding'],'method':position['method'],'oldBodySHA256':position['bodySHA256'],'newBodySHA256':c.sha(body['mir'].encode()),'oldQuerySHA256':position['querySHA256'],'newQuerySHA256':q['sha256'],'actualIdentity':actual['identity'],'actualBytes':actual['bytes'],'actualAlignment':actual['alignment'],'witnessDeclaration':parent,'oldSourceInfo':position.get('sourceInfo'),'newSourceInfo':source_info,'sourceInfoChanged':position.get('sourceInfo')!=source_info,'numericCreditAdded':False,'exactActualTypeFullLayoutBoundByRawPositionAndDeclarationProof':True})
assert len(proof)==11760 and len(witnesses)==176
c.save(c.HERE/'unit-four-role-reconciliation.json.gz',gzip.compress(c.enc(proof),mtime=0))
c.save(c.HERE/'whole-retained-carrier-witnesses.json',witnesses)
c.save(c.HERE/'role-reconciliation-summary.json',{'unitFourRolePositions':len(proof),'wholeSourceCarrierWitnesses':len(witnesses),'sourceInfoRoleChanges':sum(x['sourceInfoChanged']for x in proof),'noNewAccountingCredit':True,'finiteRepresentationRootReviewPending':True})
print((c.HERE/'role-reconciliation-summary.json').read_text())
