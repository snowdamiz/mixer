"""Match every final position to discovery, exact witness type and selected finite layout."""
import collect as c
import json,gzip,re,collections

def display_free(value):
 if isinstance(value,str):return re.sub(r'DefId\(\d+:\d+ ~ ','DefId(<compiler-session-index> ~ ',value)
 if isinstance(value,list):return [display_free(v)for v in value]
 if isinstance(value,dict):return {k:display_free(v)for k,v in value.items()}
 return value

def main():
 original=json.loads((c.HERE/'inventory.json').read_text());final=json.loads((c.HERE/'inventory-final.json').read_text())
 old={r['field']:r for r in original};new={r['field']:r for r in final};assert set(old)==set(new)and len(old)==21364
 additional={r['field']for r in json.loads((c.HERE/'additional-finite-proposal.json').read_text())}
 selected={r['field']:r for r in json.loads((c.HERE/'finite-proposal.json').read_text())}
 selected.update({r['field']:r for r in json.loads((c.HERE/'additional-finite-proposal.json').read_text())})
 assert len(selected)==256
 changes=[];finite_changes=[]
 for name in sorted(old):
  a=old[name];b=new[name]
  for key in ['config','unitOnly','body','binding','kind','position','mirType','ownerClass']:
   assert a[key]==b[key],(name,key,a[key],b[key])
  if name in additional:assert a['method']=='exact-typed'and b['method']=='finite-proposed-private-std'
  else:assert a['method']==b['method'],name
  if a['config']=='source':continue
  assert a['actualIdentity']==b['actualIdentity'],name
  assert display_free(a['layout'])==display_free(b['layout']),(name,'actual layout drift')
  row={'field':name,'config':b['config'],'body':b['body'],'promoted':b['promoted'],'binding':b['binding'],'position':b['position'],'ownerClass':b['ownerClass'],'oldBodySHA256':a['bodySHA256'],'finalBodySHA256':b['bodySHA256'],'oldQuerySHA256':a['querySHA256'],'finalQuerySHA256':b['querySHA256'],'sameActualTypeIdentityAndCompleteLayout':True,'oldSourceInfo':a.get('sourceInfo'),'finalSourceInfo':b.get('sourceInfo'),'sourceInfoChanged':a.get('sourceInfo')!=b.get('sourceInfo'),'compilerDisplayIndexChanged':a['actualType']!=b['actualType'],'methodChangedByExactSupplement':name in additional}
  changes.append(row)
  if name in selected:finite_changes.append(row)
 assert {r['field']for r in final if r['method'].startswith('finite-proposed')}==set(selected)
 headers_old=json.loads((c.HERE/'compiler-headers.json').read_text());headers_final=json.loads((c.HERE/'compiler-headers-final.json').read_text())
 hkey=lambda r:(r['config'],r['path'],r['promoted'])
 ha={hkey(r):r for r in headers_old};hb={hkey(r):r for r in headers_final};assert set(ha)==set(hb)and len(ha)==268
 bodies=[{'config':key[0],'path':key[1],'promoted':key[2],'old':ha[key],'final':hb[key],'bodyChanged':ha[key]['bodySHA256']!=hb[key]['bodySHA256']}for key in sorted(ha,key=lambda k:(k[0],k[1],-1 if k[2]is None else k[2]))]
 witnessed=[]
 for cfg in sorted({r['config']for r in final if r['config']!='source'}):
  q=json.loads((c.HERE/f'exact-query-{cfg}.json').read_text());raw=gzip.decompress((c.HERE/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());assert c.sha(raw)==q['sha256']
  records=[json.loads(line)for line in raw.decode().splitlines()];decl={r['path']:r for r in records if r['kind']=='declaration'}
  all_fields={}
  for path,record in decl.items():
   if not path.rsplit('::',1)[-1].startswith(('LifecycleActivePositions','LifecyclePermanentPositions','LifecycleNeverActivePositions','LifecycleNeverPermanentPositions')):continue
   variant=record['layout']['variants'][0]
   for name,field in zip(variant['fieldNames'],variant['fields']):
    assert name not in all_fields
    all_fields[name]=(path,field)
  for row in final:
   if row['config']not in [cfg,'source']or row['method'].startswith('finite-proposed'):continue
   path,field=all_fields[row['field']]
   if row['config']!='source':
    assert field['identity']==row['actualIdentity'],(cfg,row['field'],'actual witness type mismatch')
    assert field['bytes']==row['layout']['bytes']and field['alignment']==row['layout']['alignment']
   witnessed.append({'config':cfg,'field':row['field'],'sourceConfig':row['config'],'method':row['method'],'ownerClass':row['ownerClass'],'witnessDeclaration':path,'actualWitnessField':field,'actualSourceIdentity':row.get('actualIdentity'),'querySHA256':q['sha256'],'noTypeOrPaddingSubstitution':True})
 expected=sum(not r['method'].startswith('finite-proposed')and r['config']!='source'for r in final)+44*8
 assert len(witnessed)==expected,(len(witnessed),expected)
 numeric=json.loads((c.HERE/'numeric-positions.json').read_text());assert len(numeric)==256
 previous={}
 for row in numeric:
  name=row['field'];assert name in selected
  assert row['actualIdentity']==new[name]['actualIdentity']
  assert display_free(row['layout'])==display_free(new[name]['layout'])
  key=row['component'];assert row['relativeOffset']>=previous.get(key,0)
  assert row['relativeOffset']%row['layout']['alignment']==0
  assert row['exclusiveEnd']==row['relativeOffset']+row['layout']['bytes'];previous[key]=row['exclusiveEnd']
 c.save(c.HERE/'position-reconciliation.json.gz',gzip.compress(c.enc(changes),mtime=0));c.save(c.HERE/'finite-reconciliation.json',finite_changes);c.save(c.HERE/'body-reconciliation.json',bodies);c.save(c.HERE/'exact-typed-witness-proof.json.gz',gzip.compress(c.enc(witnessed),mtime=0))
 summary={'sourceClosure':c.sha(c.enc(c.manifest(c.HERE/'candidate'))),'originalPositions':len(old),'finalPositions':len(new),'newOrRemovedRuntimePositions':0,'runtimeBodies':len(bodies),'bodySHA256Changed':sum(r['bodyChanged']for r in bodies),'sourceInfoPositionsChanged':sum(r['sourceInfoChanged']for r in changes),'actualTypeIdentityOrLayoutChanges':0,'supplementalMethodChanges':len(additional),'exactTypedAndNeverWitnesses':len(witnessed),'finitePositions':len(numeric),'finiteExclusiveComponentEnds':previous,'annotatedConstBodies':384,'allOriginalRolesPreserved':True,'noPriorV7RoleCredit':True,'accountingAccepted':False,'runtimeSelected':False}
 c.save(c.HERE/'reconciliation-summary.json',summary);print(json.dumps(summary,sort_keys=True,indent=2))
if __name__=='__main__':main()
