#!/usr/bin/env python3
"""Independent data/partition/custody/model controls; never imports model.py."""
from __future__ import annotations
import copy
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CAPS={'G1':256,'G7':248,'SS':512,'SF':256,'G128':128,'F42':42}
EXPECTED={
 'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs':'0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8',
 'verification/swift-cache-state-implementation/correction-3/candidate-repo-seal.json':'7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f',
 'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json':'ea00518ce5033b4651460763f1c92533d024fee32a73b182d1684afa65ef80e1',
 'verification/swift-semantic-adapter-root-review/C3-lifetime-selection.json':'ab2e74fa3fa7a6ff967a5c0d000d46336cc42dc5654c6b38fdce008fcafedaf4',
 'verification/swift-cache-state-c3-lifetime-accounting/seal.json':'703bf7ca338dac74574c60a7ac42addcd4d1bc44645d559dd05ca0c4dad56c22',
 'verification/swift-cache-state-c3-lifetime-independent/seal.json':'233d419d128e0806beaafeacdfc567f9ad02098acc2a804f3ce77d55e1c3aa92',
}
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):return json.loads((HERE/n).read_text())
def require(ok,msg):
 if not ok:raise ValueError(msg)
def validate(paths,ops,parts,ownership):
 require(paths['caps']==CAPS,'changed cap')
 require(ownership['selected_here'] is False and ownership['combined_source_work_accepted'] is False,'self acceptance')
 require(ownership['semantic_sum']==sum(ownership['caps']['G'+str(i)] for i in range(1,8))==7680,'semantic sum')
 require(ownership['old_combined_record']==471 and ownership['new_combined_record']==8151 and ownership['preflight']==8192,'changed public record funding')
 require('425*N_B' in ownership['old_public_debit'],'changed old public debit')
 require({r['id'] for r in paths['paths']}==set(ops)==set(parts),'recipe membership')
 for row in paths['paths']:
  name=row['id'];stream=ops[name];ids=[o['id'] for o in stream]
  require(len(ids)==len(set(ids)),'duplicate operation id')
  require(all(o['owner']==row['owner'] for o in stream),'cross owner credit')
  require(all(o['kind'] in ('scalar','copy') for o in stream),'unknown primitive')
  require(all((o['bytes']==0 if o['kind']=='scalar' else 0<o['bytes']<=128) for o in stream),'copy width/primitive')
  s=sum(o['kind']=='scalar' for o in stream);c=len(stream)-s;g=(s+15)//16+c
  require((s,c,g)==(row['scalars'],row['copies'],row['groups']),'summary arithmetic')
  require(sha(json.dumps(stream,separators=(',',':')).encode())==row['operations_sha256'],'ordered source operations changed')
  require(g<=CAPS[row['owner']],'cap overflow')
  p=parts[name];require(p['owner']==row['owner'],'partition owner')
  require(all(1<=len(b)<=16 for b in p['scalar_blocks']),'scalar block overflow')
  require([i for b in p['scalar_blocks'] for i in b]==[o['id'] for o in stream if o['kind']=='scalar'],'missing/reordered scalar partition')
  require(p['payload_copy_groups']==[{'id':o['id'],'bytes':o['bytes']} for o in stream if o['kind']=='copy'],'copy partition')
  if name.startswith('G7.success'):
   final=[o for o in stream if 'snapshot[16] complete Option<usize>16' in o['operation']]
   require(len(final)==1 and final[0]['bytes']==16,'missing final None16')
  if name.startswith(('SF.','F42.')):
   public=[o for o in stream if o['kind']=='copy' and 'public designated Result488 -> external caller' in o['operation']]
   require(sum(o['bytes'] for o in public)==488,'incomplete actual Result488 caller receive')
  if name.startswith('G128.short-arena'):
   guard=[o for o in stream if o['site']=='zero-debit terminal guard prefix']
   require(not any('steps.spent' in o['operation'] for o in guard),'short arena reads private budget')
 for owner in CAPS:
  require(paths['maxima'][owner]['groups']==max(r['groups'] for r in paths['paths'] if r['owner']==owner),'maximum summary')

def main():
 inputs=read('inputs.json');by={r['path']:r for r in inputs['members']}
 for p,h in EXPECTED.items():
  require(p in by,'missing identity '+p);require(by[p]['sha256']==h,'expected frozen identity '+p)
 for row in inputs['members']:
  b=(ROOT/row['path']).read_bytes();require(len(b)==row['bytes'] and sha(b)==row['sha256'],'input drift '+row['path'])
 source=(ROOT/'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs').read_text().splitlines(keepends=True)
 for span in read('source-map.json')['spans']:
  require(sha(''.join(source[span['first_line']-1:span['last_line']]).encode())==span['excerpt_sha256'],'source excerpt drift')
 lifetime=json.loads((ROOT/'verification/swift-semantic-adapter-root-review/C3-lifetime-selection.json').read_text())
 require(lifetime['whole_role_union_accepted'] and lifetime['whole_role_union']==29344,'selected logical union')
 g6=json.loads((ROOT/'verification/swift-semantic-adapter-root-review/G6-correction3-accounting-selection.json').read_text())
 require(g6['production']['groups']==512 and g6['including_private_faults']['groups']==514 and g6['cap']==640,'unchanged selected G6')
 # independently reconstruct selected helper arithmetic from the explicit
 # component grammar. No producer function, collector, or imported code runs.
 templates=read('templates.json')['templates'];actual={r['name']:(r['scalars'],r['copies']) for r in templates}
 selected=json.loads((ROOT/'verification/swift-cache-state-g6-complete/operation-templates.json').read_text())
 selected_by={r['name']:(r['scalars'],r['copies']) for r in selected['templates']}
 expected={'ld Candidate/literal':(71,1),'cq literal':(83,1),'rr literal field':(97,1),'indexed record word':(21,0),'IndexMut p.q literal/value':(22,0),'st slice/literal/value':(71,2)}
 require(actual==expected,'independent helper component formulas')
 for name in ('ld Candidate/literal','cq literal','rr literal field','indexed record word'):require(actual[name]==selected_by[name],'selected primitive mismatch')
 # IndexMut17 + rhs1 + index1 + field2 + final store1 =22. Slice st62
 # plus explicit outer Arena/Vec->slice construction9 =71. Candidate st63
 # differs from the source slice by one actual array coercion component.
 require(actual['IndexMut p.q literal/value'][0]==17+1+1+2+1,'IndexMut component boundary')
 require(actual['st slice/literal/value'][0]==selected_by['st Candidate/value'][0]-1+9,'st caller component boundary')
 paths=read('paths.json');ops=json.loads(gzip.decompress((HERE/'operations.json.gz').read_bytes()));parts=read('partitions.json');ownership=read('ownership.json')
 validate(paths,ops,parts,ownership)
 for family in read('failure-coverage.json')['families']:
  require(all(p in ops for p in family['paths']),'unknown failure coverage recipe')
 funding=read('whole-setup-funding.json')
 require(sum(r['debit'] for r in funding['fixed_source_debits'])==funding['fixed_sum']==4096,'whole fixed setup debit')
 require((funding['STREAM_CAP']+65535)//65536+1==funding['drain_iteration_bound']==8194,'whole drain debit bound')
 require(funding['fixed_sum']+funding['drain_iteration_bound']==funding['whole_setup_debit_upper']==12290<=funding['setup_cap']==65536,'whole setup cap')
 require(6446+256+128==funding['report_reserved_upper']==6830<=funding['report_cap'],'whole report reserve')
 controls=[]
 def reject(name,mutate):
  a,b,c,d=copy.deepcopy((paths,ops,parts,ownership));mutate(a,b,c,d)
  try:validate(a,b,c,d)
  except ValueError as e:controls.append({'control':name,'rejected':True,'reason':str(e)})
  else:raise ValueError('control accepted '+name)
 reject('changed G1 cap',lambda a,b,c,d:a['caps'].__setitem__('G1',257))
 reject('self accepted proof',lambda a,b,c,d:d.__setitem__('selected_here',True))
 reject('cross owner spare',lambda a,b,c,d:next(iter(b.values()))[0].__setitem__('owner','G6'))
 reject('copy wider than128',lambda a,b,c,d:next(o for stream in b.values() for o in stream if o['kind']=='copy').__setitem__('bytes',129))
 reject('duplicate operation',lambda a,b,c,d:next(iter(b.values())).append(next(iter(b.values()))[0]))
 reject('missing scalar partition',lambda a,b,c,d:next(iter(c.values()))['scalar_blocks'][0].pop())
 reject('missing final None Option16',lambda a,b,c,d:next(o for n,s in b.items() if n=='G7.success' for o in s if 'snapshot[16] complete Option<usize>16' in o['operation']).__setitem__('bytes',8))
 reject('Result488 regressed to232',lambda a,b,c,d:next(o for n,s in b.items() if n.startswith('F42.') for o in s if 'public designated Result488 -> external caller' in o['operation']).__setitem__('operation','public Result232 -> external caller'))
 reject('old public record changed',lambda a,b,c,d:d.__setitem__('old_combined_record',472))
 floors=read('necessary-lower-bounds.json')
 for row in floors['rows']:require((row['scalars']+15)//16+row['copies']==row['groups_lower']<=row['cap'],'lower-bound arithmetic')
 result={'passed':True,'checks':'local frozen input custody, independently calibrated helper grammar, ordered operation hashes, payload/scalar partitions, ownership/caps, complete caller488, final None16, lower bounds and nine mutation controls','maxima':{o:paths['maxima'][o]['groups'] for o in CAPS},'controls':controls,'complete_semantic_independent_review':False,'source_cover_proposal_selected':False,'implementation_or_release_acceptance':False}
 print(json.dumps(result,indent=2))

if __name__=='__main__':main()
