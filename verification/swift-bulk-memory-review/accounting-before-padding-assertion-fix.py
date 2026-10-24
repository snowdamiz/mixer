from run import *
import collections
schema=json.loads((PACKET/'inventory-schema.json').read_text());old=json.loads((PACKET/'inputs/accepted-memory-schema.json').read_text());layouts=json.loads((PACKET/'layouts.json').read_text())
assert len(schema)==4324 and len(old)==4800
source=(SCRATCH/'candidate/src/experimental_swift_reactor/bulk_memory_operations.rs').read_text().split('// ACCOUNTING_START')[1]
declared=dict(re.findall(r'^    (\w+): (.*),$',source,re.M));assert declared=={r['field']:r['rustType']for r in schema}
roles=collections.defaultdict(list)
for r in schema:roles[r['field'].rsplit('_',1)[0]].append(r)
assert len(roles)==1081
for v in roles.values():assert {r['position']for r in v}=={'source','argument','returned','caller'}and len(v)==4 and len({r['rustType']for r in v})==1
report=[]
for layout in layouts:
 stage='layout-'+('sealed-candidate'if layout['label']=='candidate'else'baseline')+'-'+layout['features']+'-'+layout['profile']+('-unit'if layout['unit']else'-production')
 folder=PACKET/'commands'/stage
 raw=(folder/'stdout').read_bytes()if(folder/'stdout').exists()else gzip.decompress((folder/'stdout.gz').read_bytes())
 receipt=json.loads((folder/'receipt.json').read_text());assert hashlib.sha256(raw).hexdigest()==receipt['stdoutSHA256']and receipt['exitCode']==0
 data={k:{}for k in['types','owners','classes','fields','totals']}
 for line in raw.decode().splitlines():
  at=line.find('BM_')
  if at<0:continue
  kind,key,*values=line[at:].split();v=list(map(int,values));target={'BM_TYPE':'types','BM_OWNER':'owners','BM_CLASS':'classes','BM_FIELD':'fields','BM_TOTAL':'totals'}[kind];assert key not in data[target]
  data[target][key]=dict(bytes=v[0],alignment=v[1])if target in['types','classes']else dict(offset=v[0],bytes=v[1],alignment=v[2])if target=='fields'else v[0]
 assert all(data[k]==layout[k]for k in data)
 if layout['label']=='baseline':continue
 selected=[r for r in schema if layout['unit']or r['config']!='unit'];assert set(data['fields'])=={r['field']for r in selected};end={};sizes=collections.Counter();zero=[]
 for r in sorted(selected,key=lambda r:(r['ownerClass'],data['fields'][r['field']]['offset'])):
  f=data['fields'][r['field']];cls=r['ownerClass'];assert f['offset']%f['alignment']==0 and f['offset']>=end.get(cls,0);end[cls]=f['offset']+f['bytes'];assert end[cls]<=data['classes'][cls]['bytes'];sizes[cls]+=f['bytes']
  if f['bytes']==0:assert r['rustType']=='()';zero.append(r['field'])
 for cls,value in sizes.items():assert value==data['classes'][cls]['bytes'],(cls,value,data['classes'][cls])
 base=next(x for x in layouts if(x['label'],x['features'],x['profile'],x['unit'])==('baseline',layout['features'],layout['profile'],layout['unit']))
 t=data['totals'];assert data['types']==base['types']and data['owners']==base['owners'];assert t['header']==base['totals']['header']+t['bulk_permanent'];assert t['frame']==base['totals']['frame']+t['bulk_active'];assert t['frame']==sum(t[k]for k in['frame_active','control_active','value','accepted_memory_active','bulk_active'])
 assert t['bulk_active']==(1206544 if layout['unit']else 642456)and t['bulk_permanent']==121856
 assert t['header']==(2652896 if layout['unit']else 1758216)and t['frame']==(6299432 if layout['unit']else 3478968)
 assert t['state_limit']==134217728 and t['combined_limit']==268435456
 report.append(dict(features=layout['features'],profile=layout['profile'],unit=layout['unit'],selectedFields=len(selected),zeroSizedUnitFields=len(zero),totals=t,fieldSizeSums=sizes,rawCommand=stage))
assert len(report)==8
(HERE/'accounting-results.json').write_bytes(enc(dict(freshFields=4324,retainedFields=4800,roleGroups=1081,zeroSizePolicy='Actual typed unit places remain named independently at size 0, never reused as another field or subtracted from the bound',layouts=report)))
print('PASS raw outputs16; 4324 distinct typed fields/1081 four-role groups; retained4800; additive whole production/unit bounds')
