#!/usr/bin/env python3
"""Build coherent-hash schema boundary cases with the separate reviewed oracle."""
import copy, hashlib, importlib.util, json, pathlib
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
oracle_path=ROOT/'verification/hosted-atomic-display-review/byte-oracle.py'
spec=importlib.util.spec_from_file_location('independent_audit_oracle',oracle_path)
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
base=json.loads((HERE/'candidate/test/fixtures/audit/retained-chains.json').read_text())['chains'][0]['rows'][0]['display_json']
cases=[]
def add(label, path, value, accepted=False):
    d=copy.deepcopy(base);node=d
    for p in path[:-1]:node=node[p]
    node[path[-1]]=value
    b=oracle.cbor(oracle.typed_event(d));d['hash']=oracle.domain_hash('mixer.hosted.audit.v1',b).hex()
    cases.append({'label':label,'accepted':accepted,'display':d,'event_cbor_hex':b.hex(),'display_bytes_hex':oracle.pg_json(d).encode().hex()})
for path in [['id'],['recorded_at'],['actor',4],['actor',10],*([ 'decision',i] for i in range(6))]:
    v=base
    for key in path:v=v[key]
    for form in ['0'+v,'+'+v,' '+v,v+'\n']:
        add('noncanonical decimal '+str(path)+' '+repr(form),path,form)
for path,value in [(['id'],'0'),(['actor',4],'2147483648'),(['actor',4],'0'),(['decision',1],'9223372036854775808'),(['decision',1],'0'),(['recorded_at'],'9007199254740992'),(['actor',10],'9007199254740992'),(['reason'],'x'*513),(['actor',3],'x'*129),(['actor',3],'\0'),(['reason'],'\0'),(['target',0],'different'),(['tenant',0],'different'),(['target',2],'bad/path'),(['target',3],'bad\n'),(['target',4],'windows'),(['target',5],'ab'),(['target',6],'00'*31),(['source_ip'],'127.000.0.1'),(['source_ip'],'127.0.0.1/32'),(['source_ip'],'2001:0DB8::1'),(['source_ip'],'bad.invalid'),(['actor',5],'AB'*32),(['request_id'],base['request_id'].upper())]:
    if value==base.get(path[0]) or (path==['request_id'] and value==base['request_id']):continue
    add('closed boundary '+str(path)+' '+repr(value),path,value)
member=base['decision'][6][0]
for role in ['publisher','Developer','viewer','billing_manager']:
    m=copy.deepcopy(member);m[1]=role;add('role '+role,['decision',6],[m])
add('65 members',['decision',6],[member]*65)
add('duplicate member',['decision',6],[member,member])
second=copy.deepcopy(member);second[0]='ffffffff-ffff-ffff-ffff-ffffffffffff'
add('descending members',['decision',6],[second,member])
for path,value in [(['reason'],'x'*512),(['reason'],'\x0b\\u000b\n水😀'),(['actor',3],'é'*64),(['source_ip'],'2001:db8::1'),(['source_ip'],'127.0.0.1'),(['source_ip'],None),(['actor',4],'2147483647'),(['decision',1],'9223372036854775807')]:
    add('valid boundary '+str(path)+' '+repr(value),path,value,True)
d=copy.deepcopy(base);d['id']='18446744073709551615';d['previous_hash']='11'*32;d['recorded_at']='9007199254740991';d['actor'][10]=d['recorded_at'];d['decision'][0]=d['recorded_at']
b=oracle.cbor(oracle.typed_event(d));d['hash']=oracle.domain_hash('mixer.hosted.audit.v1',b).hex()
cases.append({'label':'maximum uint64 id and safe-integer time','accepted':True,'display':d,'event_cbor_hex':b.hex(),'display_bytes_hex':oracle.pg_json(d).encode().hex()})
d=copy.deepcopy(base);d['tenant']=['foreign-org','foreign-project'];d['target'][:2]=d['tenant']
d['previous_state']=oracle.domain_hash('mixer.hosted.state.v1',oracle.cbor([1,*d['tenant']])).hex()
b=oracle.cbor(oracle.typed_event(d));d['hash']=oracle.domain_hash('mixer.hosted.audit.v1',b).hex()
cases.append({'label':'valid foreign tenant first row','accepted':True,'display':d,'event_cbor_hex':b.hex(),'display_bytes_hex':oracle.pg_json(d).encode().hex()})
(HERE/'candidate/test/fixtures/audit/coherent-vectors.json').write_text(json.dumps({'oracle_sha256':hashlib.sha256(oracle_path.read_bytes()).hexdigest(),'cases':cases},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'total':len(cases),'accepted':sum(x['accepted'] for x in cases),'rejected':sum(not x['accepted'] for x in cases)}))
