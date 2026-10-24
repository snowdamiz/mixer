#!/usr/bin/env python3
"""Independent rejection inputs authored from the selected field contract.
No SQL or Elixir encoder output is used. The original hand-authored valid vector
is retained as input, unchanged; these are typed/canonical mutations only.
"""
import copy,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
base=json.loads((HERE/'probe/golden-vectors.json').read_text())['expected_display']
invalid=[];valid=[]
def put(d,path,value):
 x=d
 for k in path[:-1]:x=x[k]
 x[path[-1]]=value
 return d
def bad(label,path,value): invalid.append({'label':label,'display':put(copy.deepcopy(base),path,value)})
def good(label,changes):
 d=copy.deepcopy(base)
 for path,value in changes:put(d,path,value)
 valid.append({'label':label,'display':d})
# Every root required key: absence, JSON null, wrong JSON type.
for key,value in base.items():
 d=copy.deepcopy(base);d.pop(key);invalid.append({'label':f'root/{key}/missing','display':d})
 if key!='source_ip':bad(f'root/{key}/null',[key],None)
 bad(f'root/{key}/wrong-type',[key], {} if not isinstance(value,dict) else [])
d=copy.deepcopy(base);d.pop('source_ip');d['replacement']=None
invalid.append({'label':'same-count-missing-null-extra-key','display':d})
d=copy.deepcopy(base);d['extra']=None;invalid.append({'label':'extra-root-key','display':d})
# Every fixed array and every primitive nested slot rejects null and wrong type.
for name,n in [('tenant',2),('actor',11),('decision',7),('target',7)]:
 bad(f'{name}/short',[name],base[name][:-1]);bad(f'{name}/long',[name],base[name]+[None])
 for i in range(n):
  bad(f'{name}/{i}/null',[name,i],None)
  bad(f'{name}/{i}/type',[name,i],17)
for i in range(3):
 bad(f'membership/{i}/null',['decision',6,0,i],None)
 bad(f'membership/{i}/type',['decision',6,0,i],True)
for value in [[],[base['decision'][6][0][:-1]],[base['decision'][6][0]+['extra']],[base['decision'][6][0]]*65,[base['decision'][6][0]]*2]:
 bad('membership/shape-order-count',['decision',6],value)
m1=base['decision'][6][0];m2=['00000000-0000-0000-0000-000000000002','viewer','1']
bad('membership/reverse',['decision',6],[m2,m1])
for role in ['publisher','Developer','', 'release_manager','viewer','billing_manager']:
 bad('membership/unsupported-or-upload-ceiling/'+role,['decision',6,0,1],role)
# Every bounded decimal class: spelling, sign, fractional/exponent, zero, overmax.
nums=[(['id'],1,2**64-1),(['actor',4],1,2**31-1),(['actor',10],0,2**53-1),(['decision',0],0,2**53-1),(['recorded_at'],0,2**53-1)]
nums += [(['decision',i],1,2**63-1) for i in range(1,6)] + [(['decision',6,0,2],1,2**63-1)]
for path,lo,hi in nums:
 for value in ['01','+1','-1','1.0','1e0',' 1','1 ','NaN','Infinity','',str(hi+1),str(lo-1),1,True]:
  bad('decimal/'+str(path)+'/'+repr(value),path,value)
# Canonical UUID in all four classes and member ID.
for path in [['actor',0],['actor',2],['actor',9],['request_id'],['decision',6,0,0]]:
 for value in ['00000000000000000000000000000001','{00000000-0000-0000-0000-000000000001}','AAAAAAAA-0000-0000-0000-000000000001','00000000-0000-0000-0000-00000000001','x'*36]:
  bad('uuid/'+str(path)+'/'+value,path,value)
# All byte classes require exact lower-case length.
for path in [['actor',i] for i in range(5,9)]+[['target',5],['target',6]]+[[k] for k in ['previous_state','current_state','request_hash','hash']]:
 for value in ['','00'*31,'00'*33,'AB'*32,'zz'*32,'0'*63,'0'*65,'00 '*32]:bad('hex/'+str(path)+'/'+str(len(value))+value[:2],path,value)
for value in ['00','00'*31,'00'*32,'ab'*33]:bad('event1/previous-hash',['previous_hash'],value)
for path in [['tenant',0],['tenant',1]]+[['target',i] for i in range(4)]:
 for value in ['', 'x'*129,'has space','é','*','a/../b']:
  bad('ValidID/'+str(path)+'/'+value[:4],path,value)
for value in ['', 'x'*129]:bad('profile/bound',['actor',3],value)
for value in ['service','Human','']:bad('identity-class',['actor',1],value)
for value in ['web','IOS','']:bad('platform',['target',4],value)
for value in ['audit.read','artifact.read','']:bad('action',['action'],value)
for value in ['1',1.5,True]:bad('schema/type',['audit_schema'],value)
for value in ['a'*513,'é'*257]:bad('reason/byte-bound',['reason'],value)
for value in ['127.000.0.1','127.0.0.1/32','::1/128','fe80::1%en0','2001:DB8::1','2001:0db8::1','','x'*46]:bad('source-ip',['source_ip'],value)
bad('target/tenant-mismatch',['target',0],'other')
bad('completion/stale46',['actor',10],'54');bad('completion/future31',['actor',10],'131');bad('recorded/before-decision',['recorded_at'],'99')
# Valid typed boundaries. Hash consistency is checked separately by the row oracle.
good('golden',[])
good('auth-future30',[(['actor',10],'130')]);good('auth-age45',[(['actor',10],'55')])
good('zero-seconds',[(['actor',10],'0'),(['decision',0],'0'),(['recorded_at'],'0')])
good('maximum-seconds',[(['actor',10],str(2**53-1)),(['decision',0],str(2**53-1)),(['recorded_at'],str(2**53-1))])
good('event-u64max',[(['id'],str(2**64-1)),(['previous_hash'],'00'*32)])
good('profile-version-max',[(['actor',4],str(2**31-1))])
for i in range(1,6):good(f'revision-{i}-max',[(['decision',i],str(2**63-1))])
good('member-revision-max',[(['decision',6,0,2],str(2**63-1))])
good('utf8-profile128-reason512',[(['actor',3],'é'*64),(['reason'],'é'*256)])
good('profile-min1',[(['actor',3],'x')])
good('ip-mapped',[(['source_ip'],'::ffff:192.0.2.1')])
good('ascii-profile128',[(['actor',3],'p'*128)])
good('ip-v4',[(['source_ip'],'127.0.0.1')]);good('ip-v6',[(['source_ip'],'2001:db8::1')]);good('platform-android',[(['target',4],'android')])
for role in ['owner','administrator','developer']:good('upload-role/'+role,[(['decision',6,0,1],role)])
members=[[f'00000000-0000-0000-0000-{i:012x}', 'developer' if i==1 else ['owner','administrator','developer','release_manager','billing_manager','viewer'][i%6],str(2**63-1)] for i in range(1,65)]
good('64-unique-sorted-all-six-roles',[(['decision',6],members)])
for size in [1,128]:good(f'ValidID-{size}',[(['tenant',0],'O'*size),(['tenant',1],'P'*size),(['target',0],'O'*size),(['target',1],'P'*size),(['target',2],'A'*size),(['target',3],'E'*size)])
# Standard definite CBOR oracle, separately implemented in Python integers/bytes.
def head(major,n):
 if n<24:return bytes([major*32+n])
 for width,tag in [(1,24),(2,25),(4,26),(8,27)]:
  if n<1<<(width*8):return bytes([major*32+tag])+n.to_bytes(width,'big')
 raise ValueError('u64')
def cbor(v):
 if v is None:return b'\xf6'
 if type(v)==int:return head(0,v)
 if isinstance(v,bytes):return head(2,len(v))+v
 if isinstance(v,str):
  b=v.encode();return head(3,len(b))+b
 return head(4,len(v))+b''.join(map(cbor,v))
def uid(v):return bytes.fromhex(v.replace('-',''))
def event(d):
 a=d['actor'];de=d['decision'];t=d['target']
 return [1,int(d['id']),d['tenant'],[uid(a[0]),a[1],uid(a[2]),a[3],int(a[4]),*[bytes.fromhex(x) for x in a[5:9]],uid(a[9]),int(a[10])],
 [*[int(x) for x in de[:6]],[[uid(m[0]),m[1],int(m[2])] for m in de[6]]],
 [*t[:5],bytes.fromhex(t[5]),bytes.fromhex(t[6])],d['action'],d['reason'],uid(d['request_id']),d['source_ip'],int(d['recorded_at']),
 *[bytes.fromhex(d[k]) for k in ['previous_state','current_state','previous_hash','request_hash']]]
for row in valid:row['expected_cbor_hex']=cbor(event(row['display'])).hex()
(HERE/'probe/display-corpus.json').write_text(json.dumps({'schema':1,'authorship':'Selected field/range/canonicality contract; no candidate encoder consulted','invalid':invalid,'valid':valid},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'invalid':len(invalid),'valid':len(valid)}))
