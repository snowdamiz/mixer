#!/usr/bin/env python3
"""Select immutable source bytes; never import or execute a historical runner."""
import hashlib,json,pathlib,re,shutil,sys
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P=ROOT/'verification/swift-cache-state-scalar-cursor-implementation'
I=ROOT/'verification/swift-cache-state-scalar-cursor-implementation-independent'
OLD=ROOT/'verification/swift-envelope-ci-pack'
PACK=HERE/'pack'
PRODUCER_SEAL='efc43d467a112522b40b4113bb21aa13086c0669d9d911707a85a148e3d4037c'
INDEPENDENT_SEAL='267905beda1bd6abdb4a83bbfe174c87258a5d432603306946ca88c047ba3f86'
SELECTION='6628509512df7fd4bd69a4f45e4a9374c0b1653079a49236d8a2a0f69e67b0c5'
def need(v,m):
 if not v:raise RuntimeError(m)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def sealed(base,pin):
 need(sha(base/'seal.json')==pin,'seal identity differs')
 m=json.loads((base/'seal.json').read_bytes())
 return {r['path']:r for r in m['members']}
S=sealed(P,PRODUCER_SEAL);IS=sealed(I,INDEPENDENT_SEAL)
def checked(base,rows,name):
 p=base/name;r=rows[name];need(p.is_file()and not p.is_symlink()and p.stat().st_size==r['bytes']and sha(p)==r['sha256'],'selected source differs '+str(p));return p
roster=[]
def copy(base,rows,name,dest):
 p=checked(base,rows,name);q=PACK/dest;need(not q.exists(),'pack must be fresh');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 roster.append({'original':str(p.relative_to(ROOT)),'packed':dest,'bytes':q.stat().st_size,'sha256':sha(q)})
need(not any(PACK.iterdir()),'pack must be empty')
selection=ROOT/'verification/swift-semantic-adapter-root-review/scalar-cursor-implementation-selection.json'
need(sha(selection)==SELECTION,'root selection differs')
qualification=json.loads(checked(P,S,'proofs/fresh-qualification.json').read_bytes())
need(qualification['source_tree_digest']=='860cec7b596e03b1058ecd5ff0a9c843af52e6c021218d1478636c5d9839db4c','source tree selection differs')
for row in qualification['source_rows']:copy(P,S,row['path'],row['path'])
for name in sorted(n for n in S if n.startswith('api/')and n.endswith('.rs')):copy(P,S,name,name)
need(sum(x['packed'].startswith('api/')for x in roster)==25,'API source count')
copy(P,S,'controls/selected_controls.rs','controls/selected_controls.rs')
copy(I,IS,'source/scalar_cursor_independent.rs','controls/scalar_cursor_independent.rs')
need(sha(OLD/'manifest.json')=='4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a','old manifest differs')
oldrows={r['path']:r for r in json.loads((OLD/'manifest.json').read_bytes())['members']}
for name in sorted(n for n in oldrows if n.startswith('inputs/historical/')):copy(OLD,oldrows,name,name)
need(sum(x['packed'].startswith('inputs/historical/')for x in roster)==34,'historical source count')

def stdout(name):return checked(P,S,'evidence/'+name+'.stdout').read_text()
def methods(s):return re.findall(r'^test (\S+) \.\.\. ',s,re.M)
host=methods(stdout('tests-debug'));need(len(host)==len(set(host))==84,'host names')
need(host==methods(stdout('tests-optimized')),'host mode names differ')
reg=json.loads(checked(P,S,'evidence/selected-regression-summary.json').read_bytes())
lanes={}
for label in ['producer','independent']:
 rr=[r for r in reg['runs']if r['label']==label];need(rr[0]['inventory']==rr[1]['inventory'],'reg mode names differ');lanes[label]=rr[0]['inventory']
normalize=lambda names:{n.removeprefix('product::')for n in names}
sets={k:normalize(v)for k,v in {'host':host,**lanes}.items()}
union=set.union(*sets.values());need(len(union)==122,'normalized union')
extra_producer=methods(stdout('changed-controls-debug-tests'))
extra_ind=methods(checked(I,IS,'evidence/tests-debug.stdout').read_text())
need(len(extra_producer)==3 and len(extra_ind)==7,'extra control inventory')
extra_producer=[n.replace('::selected_scalar_controls::','::selected_scalar_controls::')for n in extra_producer]
extra_ind=[n for n in extra_ind]
extra=extra_producer+extra_ind;need(len(set(extra))==10 and not(set(extra)&union),'distinct controls')
rootnames=[n for n in lanes['producer']if not n.startswith('product::')]
embedded=[n for n in lanes['producer']if n.startswith('product::')]
need(len(rootnames)==17 and len(embedded)==91,'partition counts')
pending='failure_record_closed_payload_and_bounds';ordered=[pending]+[n for n in rootnames if n!=pending]
partitions=[{'name':f'root-{i:02}','args':[n,'--exact'],'methods':[n]}for i,n in enumerate(ordered)]+[{'name':'embedded','args':['product::'],'methods':embedded}]
write(PACK/'inventories/methods.json',{'host':sorted(host),'producer':lanes['producer'],'independent':lanes['independent'],'controls':sorted(host+extra),'extra_producer':extra_producer,'extra_independent':extra_ind,'normalized_union':sorted(union),'normalized_union_count':122,'with_controls_union_count':132,'pairwise_overlap':{a+'_'+b:len(sets[a]&sets[b])for a,b in [('host','producer'),('host','independent'),('producer','independent')]},'all_three_overlap':len(set.intersection(*sets.values())),'producer_debug_partition':partitions})
write(PACK/'inventories/layouts.json',{'historical_host':'aarch64-apple-darwin','historical_release':'1.99.0','layouts':qualification['fresh_layouts']['debug'],'count':23})
need(qualification['fresh_layouts']['debug']==qualification['fresh_layouts']['optimized'],'layout modes differ')
cases=[]
for c in qualification['modes']['debug']['cases']:
 peer=next(x for x in qualification['modes']['optimized']['cases']if x['case']==c['case'])
 need(all(c[k]==peer[k]for k in ['raw','actual_complete32','aggregate_present','scope']),'expected case modes differ')
 result=checked(P,S,str(pathlib.Path(c['manifest']).parent/'result.txt')).read_text().splitlines()[0]
 peer_result=checked(P,S,str(pathlib.Path(peer['manifest']).parent/'result.txt')).read_text().splitlines()[0]
 need(result==peer_result,'result modes differ')
 cases.append({k:c[k]for k in ['case','scope','raw','actual_complete32','aggregate_present']}|{'result_first_line':result})
need(len(cases)==31,'case count')
write(PACK/'inventories/file-cases.json',{'count':31,'public':29,'public_full32':27,'public_outer_errors':2,'private_poison':2,'cases':sorted(cases,key=lambda c:c['case'])})
# Production diagnostics are retained as ordinary text by the accepted producer.
# Fixed primary-span obligations are supplied in api-contract.json, derived from
# exact bytes and reviewed independently before any compiler qualification.
write(PACK/'inventories/api-sources.json',{'count':25,'sources':[r for r in roster if r['packed'].startswith('api/')]})
write(PACK/'inventories/bindings.json',{'producer_seal_sha256':PRODUCER_SEAL,'independent_seal_sha256':INDEPENDENT_SEAL,'root_implementation_selection_sha256':SELECTION,'source_tree_sha256':qualification['source_tree_digest'],'library_sha256':qualification['library_sha256'],'original_full_Debug_60s_timeout_remains_failed':True,'performance_equivalence_claimed':False,'selected_expected_bytes_are_historical':True,'new_invocation_must_qualify_all_checks':True})
write(HERE/'inventories/selected-source-roster.json',{'selected_source_count':len(roster),'selected_source_bytes':sum(r['bytes']for r in roster),'rows':sorted(roster,key=lambda r:r['packed']),'no_historical_runner_import_or_execution':True,'no_predecessor_failure_tree_copied':True})
print(json.dumps({'selected_source_count':len(roster),'selected_source_bytes':sum(r['bytes']for r in roster),'method_count':[84,108,98],'overlap':json.loads((PACK/'inventories/methods.json').read_bytes())['pairwise_overlap'],'union':122,'extra':10,'union_with_controls':132}))
