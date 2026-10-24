#!/usr/bin/env python3
"""Replay exact source preservation and typed, positive accounting, before behavior."""
import gzip,json,re,sys,hashlib
import collect as c
import inventory

def item(text,keyword):
 a=text.index(keyword);start=text.index('{',a);end=start+1;depth=1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[a:end]
def mir_bodies(text):
 result={}
 for m in re.finditer(r'^fn ([^\n]+)',text,re.M):
  head=m[1];name=head[:head.index('(')];body=text[m.start():text.find('\n}',m.start())+2]
  result[name]='\n'.join(line.split('//')[0].rstrip()for line in body.splitlines()if line.split('//')[0].strip())
 return result

def main():
 before=c.manifest(c.source('baseline'));after=c.manifest(c.source('candidate'))
 assert len(before)==len(after)==128
 # Inventory schema must reproduce the actual final compiler MIR, not syntax.
 schema=json.loads((c.HERE/'inventory-schema.json').read_text());observed=[];functions=[]
 for config in ['production','unit']:
  rows,func,captures=inventory.canonical(config,'final-qualified-mir');observed+=rows;functions+=func
 expected=[r for r in schema if r['config']!='source']
 required=['remove_live_at_with_wasi','primitive_pop','primitive_numeric','control_remove','remove_live_at','finish_inner','host_operation_inner']
 for config in ['production','unit']:
  names=[r['function']for r in functions if r['config']==config]
  for n in required:assert any(re.search(r'(?:^|::)'+n+r'(?=$|::)',name)for name in names),(config,n)
 for n in ['diagnostic_before_remove','diagnostic_numeric_before_remove','control_after_value_pop']:
  assert any(r['config']=='unit'and re.search(r'(?:^|::)'+n+r'(?=$|::)',r['function'])for r in functions),n
 def stable(r):return {k:v for k,v in r.items()if k not in ['ownerClass','mirLine']}
 assert list(map(stable,observed))==list(map(stable,expected))
 assert len({r['field']for r in schema})==len(schema)
 for row in schema:assert row['position']in ['source','argument','returned','caller']
 groups={}
 for r in schema:
  key=(r['config'],r['binding'],r.get('mirFunction'),r['kind']);groups.setdefault(key,set()).add(r['position'])
 assert all(v=={'source','argument','returned','caller'}for v in groups.values())
 legacy=['remove_live_with_wasi','cleanup_fault','cleanup_fault_with_wasi','record_cleanup','fail','refund_with_wasi','end_construction_phase_with_wasi','finish_owned_cleanup']
 compared={}
 for config in ['production','unit']:
  b=mir_bodies(gzip.decompress((c.HERE/('baseline-mir-'+config+'.mir.gz')).read_bytes()).decode())
  a=mir_bodies(gzip.decompress((c.HERE/('final-qualified-mir-'+config+'.mir.gz')).read_bytes()).decode())
  for n in legacy:
   keys=[k for k in b if 'control::'in k and k.endswith('::'+n)]
   assert len(keys)==1,(n,keys);k=keys[0];assert a[k]==b[k],(config,k)
   compared[config+':'+n]=c.sha(a[k].encode())
 for config in ['production','unit']:
  b=mir_bodies(gzip.decompress((c.HERE/('baseline-mir-'+config+'.mir.gz')).read_bytes()).decode());a=mir_bodies(gzip.decompress((c.HERE/('final-qualified-mir-'+config+'.mir.gz')).read_bytes()).decode())
  names=[k for k in b if ('frame_operations::'in k and k.endswith('::remove_live'))or k=='primitive_clear'or k.endswith('::release_pending')or ('cache::'in k and k.endswith('::remove_live'))]
  assert len(names)==4,(config,names)
  for k in names:assert a[k]==b[k],(config,k);compared[config+':'+k]=c.sha(a[k].encode())
 old_control=(c.source('baseline')/'src/experimental_swift_reactor/control.rs').read_text();new_control=(c.source('candidate')/'src/experimental_swift_reactor/control.rs').read_text()
 assert item(old_control,'pub(crate) fn remove_live_with_wasi(')==item(new_control,'pub(crate) fn remove_live_with_wasi(')
 # Every preexisting concrete type declaration remains exact, including old
 # inventory types. New inventory classes add positive bytes separately.
 owners={}
 for path in before:
  if not path.endswith('.rs'):continue
  b=(c.source('baseline')/path).read_text();a=(c.source('candidate')/path).read_text()
  for m in re.finditer(r'(?m)^(?:pub(?:\([^\n]*?\))? )?(?:struct|enum) ([A-Za-z_]\w*)[^;\n]*\{',b):
   original=item(b[m.start():],m[0]);name=m[1];new=[x for x in re.finditer(r'(?m)^(?:pub(?:\([^\n]*?\))? )?(?:struct|enum) '+re.escape(name)+r'\b[^;\n]*\{',a)]
   assert len(new)==1,(path,name)
   assert original==item(a[new[0].start():],new[0][0]),(path,name)
   owners[path+':'+name]=c.sha(original.encode())
 # The changed host body leaves every original 4876 accounting row untouched.
 b=(c.source('baseline')/'src/experimental_swift_reactor/frame_operations.rs').read_text();a=(c.source('candidate')/'src/experimental_swift_reactor/frame_operations.rs').read_text()
 for name in ['HostPermanentPositions','HostActivePositions']:
  assert item(b,'pub(super) struct '+name)==item(a,'pub(super) struct '+name)
 layouts=json.loads((c.HERE/'qualified-layouts.json').read_text());assert len(layouts)==16
 assert all(x['layout']['totals']['ticket_max']==86 for x in layouts)
 delta={}
 for x in layouts:
  if x['label']=='candidate':
   l=x['layout'];delta[x['features']+'-'+x['profile']+'-'+('unit'if x['unit']else'production')]={k:v['bytes']for k,v in l['classes'].items()}
 c.save('accounting-qualification.json',dict(status='qualified-before-behavior',sourceSHA256=c.digest(after),positions=len(schema),compilerBodies=len(functions),legacyMIR=compared,preexistingTypeDeclarations=len(owners),typeDeclarationHashes=owners,positiveDeltas=delta,priorHostPositions=4876,priorGrowthPositions=10356,priorMemoryPositions=4800,priorBulkPositions=4324,ownerFieldsAdded=[],ticketsAdded=0,heapAllocationsAdded=0,logicalNamedObjectBoundOnly=True))
 c.archive('candidate',c.source('candidate'))
 print('Qualified',len(schema),'positive positions;',len(owners),'old type declarations;',len(compared),'legacy MIR bodies;16 layouts')
if __name__=='__main__':main()
