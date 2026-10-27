"""Exact retained-source/MIR transport; never calls a compiler or product code.

The accepted finite typed contracts are replayed against the current production
MIR. Whole constructs, not names or counts, establish the transport precondition.
"""
from common import *
import difflib
M,T,S=accepted_modules()
SCRATCH = [str(V/'swift-guarded-snapshot-loader-work-source146/owned-work/vm'),
 str(V/'swift-guarded-snapshot-outer-parent-independent/owned-work/compiler-metadata-mir/vm'),
 str(V/'swift-guarded-snapshot-scoped-binding-source/owned-work/positive/vm'),
 str(V/'swift-guarded-snapshot-owned-provider-work-storage/owned-work/capture-layout/vm')]
SHORTS=['ReviewedFixtureBindingV1','FrozenFixtureV1','ImmutableIdentityPreimageV1','ImmutableFixtureIdentitiesV1','PreexistingImmutableBindingV1','OneFixtureOuterRequestV1']
BASE='experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1'
TYPE_PATHS=SHORTS+[BASE+'::'+n for n in SHORTS[:2]]+[BASE+'::outer_parent_v1::'+n for n in SHORTS[2:]]
LIFE=re.compile(r'(?<![\w:])('+'|'.join(map(re.escape,sorted(TYPE_PATHS,key=len,reverse=True)))+r")(?:::)?<'_>")
SPAN=re.compile(r'(?<=<impl at )<SOURCE>/([^\s:]+):\d+:\d+: \d+:\d+(?=>)')
PROBES=[[],['outer_parent_account_layout_query_v1','outer_parent_layout_query_v1'],
 ['outer_parent_account_layout_query_v1','outer_parent_layout_query_v1','scoped_result_layout_query_v1','scoped_local_binding_compiles_v1'],
 ['owned_provider_remaining_layout_query_v1']]
def project(block,span=True,oldroot=False):
 if block.startswith('alloc'):return block
 def change(text):
  for prefix in SCRATCH:text=text.replace(prefix,SCRATCH[0] if oldroot else '<SOURCE>')
  if span and not oldroot:text=SPAN.sub(r'<SOURCE>/\1:<DISPLAY-SPAN>',text)
  text=LIFE.sub(r'\1',text)
  # Only this source-declared function has the added lifetime turbofish.
  text=text.replace("selected_outer_request_v1::<'_>",'selected_outer_request_v1')
  return text
 text=S.outside_literals(block,change,remove_comments=True)
 return '\n'.join(x.rstrip() for x in text.splitlines() if x.strip())
def probe(block,stage):
 header=block.splitlines()[0]
 if stage==3 and header.startswith(('static OWNED_PROVIDER_LAYOUT_FORCE_V1:', 'const OWNED_PROVIDER_LAYOUT_FORCE_V1::{constant#')):return True
 return any(header.startswith('fn '+n+'(') or header.startswith(n+'::{constant#') or header.startswith('const '+n+'::{constant#') for n in PROBES[stage])
def provider(block):
 return block.startswith(('fn describe_existing_owner_candidate_v1(', 'fn describe_existing_owner_candidate_v1::', 'const describe_existing_owner_candidate_v1', 'const InputBackingDescriptionV1::'))
def shape(block):return S.allocation_parts(project(block))[0]
def counts(blocks):return dict(collections.Counter('function' if b.startswith('fn ') else 'allocation' if b.startswith('alloc') else 'singleline_constant' if '\n' not in b else 'braced_constant_static_anonymous' for b in blocks))
def source_lineage(tables):
 a,b,c,d=tables
 for x,y in zip(tables,tables[1:]):require([n for n in x if x[n]!=y[n]]==[PROFILE],'only reviewed profile source changed')
 outer=(V/'swift-guarded-snapshot-outer-parent-source/outer-parent.inc.rs').read_bytes()
 require(b[PROFILE]==a[PROFILE][:-2]+b'\n\n    // Private outer caller candidate; all prior bodies remain exact.\n'+outer+b'}\n','exact original to outer source append')
 edits=load(V/'swift-guarded-snapshot-scoped-binding-source/exact-edits.json');text=b[PROFILE].decode()
 for e in edits:
  require(text.count(e['before'])==e['occurrences'],'exact lifetime source edit count')
  text=text.replace(e['before'],e['after'])
 require(text.encode()==c[PROFILE],'all lifetime source edits and no others')
 boundary=S.lifetime_boundary(b[PROFILE].decode(),c[PROFILE].decode())
 fragment=(V/'swift-guarded-snapshot-owned-binding-provider/existing-owner-candidate.inc.rs').read_bytes()
 suffix=b'\n}\n}\n';require(c[PROFILE].endswith(suffix),'scoped provider insertion anchor')
 require(d[PROFILE]==c[PROFILE][:-len(suffix)]+b'\n\n// Isolated unqualified existing-owner preparation proposal.\n'+fragment+b'\n}\n}\n','exact provider source append')
 return {'trees':TREES,'each_members':146,'unchanged_files_per_transition':145,'lifetime_boundary':boundary,'exact_lifetime_edits':edits,'original_outer_append':row('outer-parent.inc.rs',outer),'provider_append':row('existing-owner-candidate.inc.rs',fragment),'no_production_body_rewrite':True}
def query_source(tables):
 # Reconstruct every compiler input from production bytes plus exact inert
 # tails. This is source attribution, never execution of preparation scripts.
 a,b,c,d=tables;queries=[]
 old=dict(b);outer=(V/'swift-guarded-snapshot-outer-parent-source/outer-parent.inc.rs').read_bytes()
 old[PROFILE]=old[PROFILE].replace(outer,outer[:-2]+b'\n'+(V/'swift-guarded-snapshot-outer-parent-independent/query-layout.inc.rs').read_bytes()+b'}\n',1)
 old[ACCOUNT]+=b'\n'+(V/'swift-guarded-snapshot-outer-parent-independent/query-account-layout.inc.rs').read_bytes()
 scoped=dict(c);folder=V/'swift-guarded-snapshot-scoped-binding-source'
 tail=b'\n'.join((folder/n).read_bytes() for n in ('query-layout.inc.rs','query-result-layout.inc.rs','positive.inc.rs'))
 scoped[PROFILE]=scoped[PROFILE][:-4]+b'\n'+tail+b'}\n}\n'
 scoped[ACCOUNT]+=b'\n'+(folder/'query-account-layout.inc.rs').read_bytes()
 current=dict(d);folder=V/'swift-guarded-snapshot-owned-provider-work-storage'
 fragment=(V/'swift-guarded-snapshot-owned-binding-provider/existing-owner-candidate.inc.rs').read_bytes();needle=fragment+b'\n}\n}\n'
 require(current[PROFILE].endswith(needle),'current query source anchor')
 current[PROFILE]=current[PROFILE][:-len(needle)]+fragment[:-2]+(folder/'query-layout.inc.rs').read_bytes()+fragment[-2:]+b'\n}\n}\n'
 require(current[PROFILE]==(folder/'query-profile.rs').read_bytes(),'complete current query profile')
 for stage,table,manifest in [(1,old,V/'swift-guarded-snapshot-outer-parent-independent/query-source-manifest.json'),(2,scoped,V/'swift-guarded-snapshot-scoped-binding-source/positive-source-manifest.json'),(3,current,folder/'query-source-manifest.json')]:
  rows=[row(n,table[n]) for n in sorted(table,key=Path)];expected=load(manifest)
  require(rows==expected['members'] and sha(canon(rows))==expected['tree_sha256'],'full146 compiler query source:'+str(stage))
  queries.append({'stage':stage,'source_tree_sha256':sha(canon(rows)),'source_members':len(rows),'production_tree_sha256':TREES[stage],'tail_files':[row(p.relative_to(R),p.read_bytes()) for p in sorted((manifest.parent).glob('*.inc.rs'))]})
 return queries
def full_base_correspondence(blocks):
 # Import the independently reviewed allocation graph matcher. All literals,
 # payload bytes, extents, alignment and relocation roles remain exact.
 old=[b for b in blocks[2] if not probe(b,2)]
 new=[b for b in blocks[3] if not probe(b,3) and not provider(b)]
 priornorm,priorinert=S.norm,S.inert
 try:
  S.norm=project;S.inert=lambda b:False
  comparison=S.compare_blocks(old,new)
 finally:S.norm,S.inert=priornorm,priorinert
 require(comparison['production_total']==6006 and counts(old)['singleline_constant']==1785,'mandatory full6006 singleline1785 amendment')
 comparison['standalone_rows']=[{'base_header':a,'current_header':b,'same_projected_bytes':project(a)==project(b)} for a,b in zip(old,new) if '\n' not in a]
 require(all(r['same_projected_bytes'] for r in comparison['standalone_rows']),'every singleline constant bound')
 return comparison
def map_original(blocks):
 # Identity includes the full path/receiver/trait/generics/parameters/result;
 # only reviewed scratch coordinates and six lifetime parameters project away.
 originals=[b for b in blocks[0] if not b.startswith('alloc')]
 current=[b for b in blocks[3] if not b.startswith('alloc') and not probe(b,3)]
 index=collections.defaultdict(list)
 for i,b in enumerate(current):index[project(b).splitlines()[0]].append((i,b))
 rows=[];unmatched=[];used=set()
 for i,a in enumerate(originals):
  key=project(a).splitlines()[0];options=[(j,b) for j,b in index[key] if j not in used and shape(a)==shape(b)]
  if not options:
   unmatched.append({'old_header':a.splitlines()[0],'candidate_headers':[b.splitlines()[0] for _,b in index[key]],'first_difference':''.join(difflib.unified_diff(shape(a).splitlines(True),shape(index[key][0][1]).splitlines(True)))[:4500] if index[key] else ''});continue
  j,b=options[0];used.add(j)
  # Duplicate constructors remain occurrences, never a deduplicated name set.
  rows.append({'old_nonallocation_ordinal':i,'current_nonallocation_ordinal':j,'old_header':a.splitlines()[0],'current_header':b.splitlines()[0],'old_raw_sha256':sha(a.encode()),'current_raw_sha256':sha(b.encode()),'full_semantic_shape_sha256':sha(shape(a).encode()),'matching_occurrences':len(options)})
 return {'rows':rows,'unmatched':unmatched,'new_nonallocation_rows':[{'ordinal':i,'header':b.splitlines()[0],'raw_sha256':sha(b.encode())} for i,b in enumerate(current) if i not in used]}
def census(blocks):
 out=[]
 for stage,pool in enumerate(blocks):
  production=[b for b in pool if not probe(b,stage)];query=[b for b in pool if probe(b,stage)]
  def scan(bs):
   text='\n'.join(bs)+'\n';alloc=[]
   for b in bs:
    if b.startswith('alloc'):
     match=re.fullmatch(r'(alloc\w+) \((.*?)size: (\d+), align: (\d+)\) \{',b.splitlines()[0]);require(match is not None,'complete allocation header')
     alloc.append({'id':match[1],'bytes':int(match[3]),'alignment':int(match[4]),'raw_sha256':sha(b.encode()),'raw_header':b.splitlines()[0]})
   ids={r['id'] for r in alloc};refs=set()
   for b in bs:refs.update(S.allocation_parts(b)[1])
   unresolved=sorted(refs-ids)
   lits=M.literal_tokens(text);values=sorted(set(r['value'] for r in lits))
   maxlit=max((len(v.encode()) for v in values),default=0);maxalloc=max((r['bytes'] for r in alloc),default=0)
   return {'constructs':len(bs),'counts':counts(bs),'literal_occurrences':len(lits),'literal_unique':len(values),'max_literal_utf8_bytes':maxlit,'literal_values':values,'allocations':len(alloc),'unique_allocation_ids':len(ids),'allocation_members':alloc,'unresolved_ids':unresolved,'max_allocation_extent':maxalloc,'conditional_conservative_envelope':max(maxlit,maxalloc)}
  out.append({'tree':TREES[stage],'production':scan(production),'query_suffix':scan(query),'query_constructs':[{'header':b.splitlines()[0],'raw_sha256':sha(b.encode()),'raw_text':b} for b in query]})
 return out
def prepare(check=False):
 tables=source_tables();texts=mir_texts();blocks=[];coverage=[]
 for text in texts:
  b,c=S.parse_mir(text);blocks.append(b);coverage.append(c)
 lineage=source_lineage(tables);queries=query_source(tables)
 save('source-lineage.json',dict(lineage,compiler_query_source=queries),check)
 save('full-base-correspondence.json',full_base_correspondence(blocks),check)
 mapping=map_original(blocks);save('original-current-construct-map.json',mapping,check)
 save('constant-census.json',{'schema':1,'stages':census(blocks),'full_raw_coverage':coverage},check)
 print(json.dumps({'matched':len(mapping['rows']),'substantive_unmatched':len(mapping['unmatched']),'new_nonallocation':len(mapping['new_nonallocation_rows']),'complete_source_census':True},sort_keys=True))
if __name__=='__main__':prepare('--check' in sys.argv)
