import pathlib,json,hashlib,gzip,collections,datetime
root=pathlib.Path.cwd();p=root/'verification/swift-reactor-lifecycle-accounting';out=root/'verification/swift-reactor-lifecycle-contract-root-review'
sha=lambda b:hashlib.sha256(b).hexdigest();enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
f=json.loads((p/'finite-proposal.json').read_bytes());assert sha((p/'finite-proposal.json').read_bytes())=='d2e3a767f9381edb06df667239562d104a1666c7c0cb503d818f83fa70e59d77';assert len(f)==248
manifest={str(q.relative_to(p/'candidate')):sha(q.read_bytes()) for q in sorted((p/'candidate').rglob('*')) if q.is_file() and 'target' not in q.relative_to(p/'candidate').parts};closure=sha(enc(manifest));assert closure=='779f94a6599e43a12674a7d3b20743e5df1bb23249130ed5af8453b1dd868832'
queries={};bodies={};locals_={};constants=collections.defaultdict(list);receipts=[]
for cfg in sorted(set(x['config'] for x in f)):
 q=json.loads((p/f'exact-query-{cfg}.json').read_bytes());assert q['exitCode']==0 and q['sourceClosure']==closure
 raw=gzip.decompress((p/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());assert sha(raw)==q['sha256'] and len(raw)==q['bytes'];records=[json.loads(x) for x in raw.splitlines()];assert len(records)==q['records'];queries[cfg]=q
 command=json.loads((p/q['attempt']/'command.json').read_bytes());cleanup=json.loads((p/q['attempt']/'cleanup.json').read_bytes());assert command['exitCode']==0 and command['sourceUnchanged'] and not command['remainingGroup'];assert cleanup['removed'] and cleanup['holderCheckEmpty'] and not cleanup['remainingGroup']
 for x in records:
  key=(cfg,x.get('path'),x.get('promoted'))
  if x['kind']=='body':assert key not in bodies;bodies[key]=x
  if x['kind']=='local':assert (*key,x['local']) not in locals_;locals_[(*key,x['local'])]=x
  if x['kind']=='constant-operand':constants[key].append(x)
 receipts.append({'config':cfg,**q,'cleanupPassed':True})
seen=set();roles=collections.defaultdict(set)
for row in f:
 assert row['field'] not in seen;seen.add(row['field']);key=(row['config'],row['body'],row['promoted']);b=bodies[key]
 assert row['querySHA256']==queries[row['config']]['sha256'];assert row['bodyDefPathHash']==b['defPathHash'] and row['bodySHA256']==sha(b['mir'].encode())
 if row['kind']=='canonical':
  actual=locals_[(*key,row['local'])];assert row['binding']=='_'+str(row['local']) and row['sourceInfo']==actual['sourceInfo']
 else:
  assert row['kind']=='constant-operand';idx=int(row['binding'].rsplit(':',1)[1]);actual=constants[key][idx];assert row['binding']==actual['location']+':'+str(idx) and row['source']==actual['constant']
 assert row['layout']==actual['layout'];assert row['actualIdentity']==actual['layout']['identity'] and row['actualType']==actual['layout']['type']
 size=row['layout']['bytes'];align=row['layout']['alignment'];assert size>=0 and align>0 and not align&(align-1)
 assert row['unitOnly']==row['config'].endswith('-unit');assert row['ownerClass']==('active' if '::tests::runtime_' in row['body'] or '::execute_phase' in row['body'] else 'permanent')
 roles[(*key,row['kind'],row['binding'])].add(row['position'])
assert len(queries)==8 and all(x=={'source','argument','returned','caller'} for x in roles.values())
v={'schema':'mixer.swift-lifecycle.finite-position-root-review.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accountableReviewer':'/root','finiteProposalSHA256':sha((p/'finite-proposal.json').read_bytes()),'sourceClosure':closure,'positions':len(f),'independentPositions':len(roles),'completeFourRoleSets':True,'fullBodyIdentityAndLayoutRecordsMatched':True,'freshQueries':receipts,'methods':dict(collections.Counter(x['method'] for x in f)),'classes':[{'ownerClass':key[0],'unitOnly':key[1],'positions':count} for key,count in collections.Counter((x['ownerClass'],x['unitOnly']) for x in f).items()],'status':'finite-numeric-installation-selection-only','accountingAccepted':False,'runtimeSelected':False,'scope':'Exact finite positions matched against original complete compiler body, local/constant and full layout records; final accounting/source and runtime remain unaccepted.'};(out/'finite-position-review.json').write_bytes(enc(v));print(json.dumps({k:x for k,x in v.items() if k!='freshQueries'},indent=2))
