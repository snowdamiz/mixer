#!/usr/bin/env python3
"""Offline integrity/completeness replay only; never runs an engine or Cargo."""
from pathlib import Path
import collections,gzip,hashlib,importlib.util,json,re,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def content(directory,stream,record):
 p=directory/record.get(stream+'Path',stream);data=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
 assert hashlib.sha256(data).hexdigest()==record[stream+'SHA256']
 return data

def archive_manifest(archive):
 with tarfile.open(archive,'r:gz') as t:
  rows={}
  for member in t.getmembers():
   assert member.isfile() and member.name.startswith('vm/') and '..' not in Path(member.name).parts
   name=member.name[3:];assert name not in rows
   rows[name]=hashlib.sha256(t.extractfile(member).read()).hexdigest()
  return rows

def verify():
 receipt=json.loads((HERE/'receipt.json').read_text());seal=json.loads((HERE/'seal.json').read_text());assert sha(HERE/'receipt.json')==seal['receiptSHA256']
 for path,digest in receipt['bindings'].items():assert sha(ROOT/path)==digest,('binding',path)
 expected={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p not in [HERE/'receipt.json',HERE/'seal.json',HERE/'offline-verify.log'] and '__pycache__' not in p.parts}|{'docs/swift-memory-helper-contract.md'}
 assert set(receipt['bindings'])==expected,('unbound or stale files',expected-set(receipt['bindings']),set(receipt['bindings'])-expected)
 assert len(receipt['qualifyingCommands'])==34
 assert receipt['status']=='candidate-frozen-for-independent-contract-review'
 for name in ['behaviorAccepted','runtimeAccepted','nativeRuntime','physicalRuntime','fullTargetExecuted','fullDispatcher','Ready','publicInvocation','gaAcceptance','liveVMEdited','committed','pushed']:assert receipt[name] is False,name
 assert receipt['compiledPrerequisitePassed'] is True
 inputs=json.loads((HERE/'input-bindings.json').read_text())
 with tarfile.open(HERE/'inputs.tar.gz','r:gz') as t:
  observed={m.name:hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in t.getmembers() if m.isfile()}
 assert observed==inputs
 with tarfile.open(HERE/'inputs.tar.gz','r:gz') as t:
  accepted=json.loads(t.extractfile('verification/swift-control-behavior-root-review/acceptance.json').read())
 assert accepted['liveIntegrated'] and accepted['implementationAccepted'] and accepted['integratedSourceDigest']==receipt['baseSourceClosure']
 for label in receipt['sourceArchives']:
  manifest=json.loads((HERE/(label+'-source-manifest.json')).read_text());assert archive_manifest(HERE/(label+'-source.tar.gz'))==manifest
  assert hashlib.sha256(enc(manifest)).hexdigest()==receipt['sourceArchives'][label]
 assert receipt['sourceArchives']['baseline']==receipt['baseSourceClosure']=='241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5'
 assert receipt['sourceArchives']['candidate']==receipt['candidateSourceClosure']=='b0922009f9fbb9b2b1091ec4b62607cff456288e8d044217481c31bfe826596c'
 for name in receipt['qualifyingCommands']:
  directory=HERE/'commands'/name;r=json.loads((directory/'receipt.json').read_text());assert r['exitCode']==0 and r['sourceUnchanged'],name
  for stream in ['stdout','stderr']:content(directory,stream,r)
  if r['sourceTreeSHA256']:
   m=json.loads((directory/'source-manifest.json').read_text());assert hashlib.sha256(enc(m)).hexdigest()==r['sourceTreeSHA256']
   assert r['sourceTreeSHA256'] in set(receipt['sourceArchives'].values())
 schema=json.loads((HERE/'inventory-schema.json').read_text());assert len(schema)==4688
 assert collections.Counter((r['config'],r['envelope']) for r in schema)=={('production','active'):2116,('unit','active'):2116,('source','active'):404,('source','permanent'):52}
 assert len({r['field'] for r in schema})==len(schema)
 groups=collections.defaultdict(set)
 for r in schema:groups[(r['field'].rsplit('_',1)[0],r['rustType'])].add(r['position'])
 assert all(v=={'source','argument','returned','caller'} for v in groups.values())
 inv=module('contract_inventory',HERE/'inventory.py')
 for config in ['production','unit']:
  rows,defs,captures=inv.canonical(HERE/('promoted-final-accounted-'+config+'.mir.gz'),config)
  expected=[r for r in schema if r['config']==config];keys=['envelope','window','field','rustType','binding','sourceNames','position','config','kind','mirType'];identity=lambda r:{k:r[k] for k in keys}
  assert list(map(identity,rows))==list(map(identity,expected)),config
  assert len(defs)==20 and sum('::promoted[' in d['function'] for d in defs)==2
 layouts=json.loads((HERE/'layouts.json').read_text());assert len(layouts)==16
 metadata=module('contract_metadata',HERE/'metadata.py')
 # metadata.py's optional CLI stage is irrelevant to its pure output parser.
 for layout in layouts:
  name='layout-'+('promoted-' if layout['label']=='candidate' else '')+layout['label']+'-'+layout['features']+'-'+layout['profile']+('-unit' if layout['unit'] else '-production')
  directory=HERE/'commands'/name;record=json.loads((directory/'receipt.json').read_text());raw=content(directory,'stdout',record)
  parsed=metadata.parse(raw.decode());assert all(parsed[k]==layout[k] for k in ['types','classes','fields','totals','owners'])
  if layout['unit']:assert re.search(r'1 passed; 0 failed; 0 ignored;',raw.decode())
  if layout['features']=='all':assert layout['totals']['frozen_header']==2912
  if layout['label']=='candidate':
   old=next(v for v in layouts if (v['label'],v['features'],v['profile'],v['unit'])==('baseline',layout['features'],layout['profile'],layout['unit']))
   assert layout['types']==old['types'] and layout['owners']==old['owners']
   expected=[r for r in schema if layout['unit'] or r['config']!='unit'];assert set(layout['fields'])=={r['field'] for r in expected}
   seen={}
   for row in sorted(expected,key=lambda r:(r['ownerClass'],layout['fields'][r['field']]['offset'])):
    field=layout['fields'][row['field']];cls=row['ownerClass'];assert field['offset']%field['alignment']==0 and field['offset']>=seen.get(cls,0)
    seen[cls]=field['offset']+field['bytes'];assert seen[cls]<=layout['classes'][cls]['bytes']
   totals=layout['totals'];assert totals['memory_permanent']==121856 and totals['memory_active']==(1153832 if layout['unit'] else 618896)
   assert totals['header']==old['totals']['header']+totals['memory_permanent']==(2531040 if layout['unit'] else 1636360)
   assert totals['frame']==old['totals']['frame']+totals['memory_active']==(5103960 if layout['unit'] else 2830864)
   assert totals['state_limit']==134217728 and totals['combined_limit']==268435456
 def frozen_map(label):
  directory=HERE/'commands'/('final-expanded-'+label);record=json.loads((directory/'receipt.json').read_text());text=content(directory,'stdout',record).decode();at=text.index('impl SpanInstance {');s=text[at:];brace=s.index('{');i=brace+1;depth=1
  while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
  s=s[:i];builder=module('contract_builder',HERE/'build_overlay.py');return {n:builder.method(s,n) for n in re.findall(r'^\s+(?:pub )?fn (\w+)\(',s,re.M)}
 frozen=frozen_map('baseline');assert frozen==frozen_map('candidate') and len(frozen)==39
 identity=json.loads((HERE/'frozen-identity.json').read_text());assert identity['methods']=={n:hashlib.sha256(v.encode()).hexdigest() for n,v in frozen.items()} and identity['reservationBytes']==2912
 matrix=json.loads((HERE/'acceptance-matrix.json').read_text());assert matrix['status']=='behavior-not-run' and len(matrix['cases'])==16
 assert all(c['status']=='pending-behavior-lane' and c['phoneOrUI'] is False for c in matrix['cases'])
 cleanup=json.loads((HERE/'cleanup.json').read_text());assert cleanup['ownedScratchRemoved'] and not Path(cleanup['scratch']).exists() and cleanup['deviceInstancesCreated']==0
 print('PASS: frozen candidate contract packet only; 4688 positive fields, 16 layouts, 39 unchanged Frozen methods, 34 qualifying commands; behavior/native/target/Ready/public/GA pending.')
if __name__=='__main__':verify()
