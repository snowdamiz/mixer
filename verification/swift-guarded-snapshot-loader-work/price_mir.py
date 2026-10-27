"""Finite, compiler-bound MIR operation/callee envelope; no engine execution."""
import collections,json,re
from pathlib import Path
D=Path(__file__).resolve().parent
X=json.loads((D/'mir-extraction.json').read_text());F=X['functions']
# Source-visible scalar leaves; opaque standard resources are one logical
# primitive place. Product fields are recursively expanded, never opaque1.
FIELDS={
 'SwiftValidationBudget':[1]*5,'ValidationBudget':[1]*3,'Usage':[1]*7,
 'SwiftValidationUsage':[1]*10,'SwiftValidationFailure':[1,1,2,1,2,1,1,10],
 'Failure':[1,1,2,1,2,1,1,7],'Cursor':[2,1], 'BodyObservations':[1]*4,
 'SwiftControl':[1,1,4], 'Meter':[3,7,1,6], 'Buffer':[1,1,1],
 'Span':[1,1],'Signature':[1,1,2],'Import':[2,2,1], 'Function':[2,1],
 'Global':[1,1,2],'Export':[2,1,1],'Segment':[2,1,1],
 'SwiftDeclaration':[2,2,1,1], 'Metadata':[3]*8+[3,3,6,1],
 'Reader':[1,1,1,2], 'Control':[1,1,2,1,1], 'BodyState':[3,3,3,3,1],
 'SwiftReactorObservations':[1]*18+[1,1],'ValidatedSwiftReactor':[1,37,2,34,10,20],
 'FileIdentityV1':[1]*8,'LoaderUsageV1':[4,4,1,1,1],
 'LoaderFailureV1':[1,1,1,1,2,20], 'ReturnedLoaderFilesV1':[1,1,1,2],
 'LoaderProvenanceV1':[5,1,32,32,32,32,32,32,32],
 'SelectedValidatedProfileV1':[104,230], 'LoaderOutcomeV1':[335,5,11],
 'ProcessObservationV1':[16385,16385,4097,4097,32,32],
 'Section':[1], 'BuildView':[4,1,6], 'SessionView':[4,1,5,1,1,1,1,4],
 'Policy':[1,1],
}
ATOMS=set('Type BlockKind Profile Resource FailureKind SwiftValidationFailureKind SwiftValidationResource WasiFunction ResolveError Role Refusal TryFromIntError TryReserveError Instant Ordering Infallible T D C R bool char u8 u16 u32 u64 u128 usize i8 i16 i32 i64 i128 isize f32 f64'.split())
PARAMETRIC={'T':6,'D':6,'C':6,'R':1}
opaque=set();unknown=set();closure_leaves={}
def split_top(s,sep=','):
 out=[];at=0;stack=[]
 for i,c in enumerate(s):
  if c in '<[(':stack.append(c)
  elif c in '>])' and stack:stack.pop()
  elif c==sep and not stack:out.append(s[at:i].strip());at=i+1
 out.append(s[at:].strip());return out

def leaves(t):
 t=t.strip()
 if t.startswith(('&','*')):return 1
 if t in ('()','!'):return 1 # explicit unit/control place, conservative
 if t.startswith('{closure@'):return closure_leaves.get(t,1)
 if t.startswith('(') and t.endswith(')'):return sum(leaves(x) for x in split_top(t[1:-1]) if x)
 if t.startswith('[') and t.endswith(']'):
  ps=split_top(t[1:-1],';')
  if len(ps)!=2:unknown.add(t);return 0
  count=16384 if ps[1]=='N' else int(ps[1]);return count*leaves(ps[0])
 base=t.split('<',1)[0].rsplit('::',1)[-1]
 inner=t[t.index('<')+1:-1] if '<' in t and t.endswith('>') else ''
 if base in ('Option','Result','ControlFlow'):
  return 1+max(leaves(x) for x in split_top(inner))
 if base in ('Range','RangeInclusive'):return 2*leaves(inner)+(base=='RangeInclusive')
 if base=='Bytes':return (16384 if inner=='N' else int(inner))+1
 if base in FIELDS:return sum(FIELDS[base])
 if base in PARAMETRIC:return PARAMETRIC[base]
 if base in ATOMS:return 1
 if t.startswith(('std::','Vec<','Box<','Option<','Result<','ControlFlow<','TryFromIntError','TryReserveError')):
  opaque.add(t);return 1
 unknown.add(t);return 0
# Closure captures are bounded by actual MIR closure-constructor operands. The
# complete parent aggregate/locals are also separately paid at the constructor.
for f in F.values():
 for statement in f['statements']:
  m=re.search(r'= (\{closure@.+?\}) \{(.*?)\};',statement)
  if m:
   total=sum(leaves(f['locals'][v]) for v in re.findall(r'\b(?:copy|move) (_\d+)\b',m[2]))
   closure_leaves[m[1]]=max(1,total)
# All authored source method targets are resolved by explicit receiver family.
METHODS={
 'LoaderFailureV1':{'new':'failure','io':'io_failure'},'FileIdentityV1':{'encode':'identity_encode'},
 'Bytes':{'new':'bytes_new','slice':'bytes_slice','put':'bytes_put','word':'bytes_word'},
 'SwiftValidationBudget':{'default':'vdefault'},'ValidatedSwiftReactor':{'source':'proof_source','usage':'proof_usage'},
 'Meter':{'swift':'meter_new','source_limit':'meter_source','usage':'meter_usage','error':'meter_error','check':'meter_check','work':'meter_work','reserve':'meter_reserve','release':'meter_release'},
 'Buffer':{'new':'bnew','len':'blen','as_slice':'bslice','get':'bget','get_mut':'bgetmut','last':'blast','last_mut':'blastmut','pop':'bpop','truncate':'btruncate','swap':'bswap','reserve':'breserve','push':'bpush','dispose':'bdispose'},
 'Reader':{n:'r'+n for n in ('new','cursor','error','byte','take','uint','signed','count','ty','end')},
 'Metadata':{'new':'mnew','signature':'msignature','params':'mparams'},'Span':{'slice':'span_slice'},
 'BodyState':{'new':'snew','error':'serror','pop_any':'spopany','pop':'spop','push':'spush','result':'sresult','unreachable':'sunreachable','label':'slabel','call':'scall','dispose':'sdispose'},
 'Failure':{'resource':'resource'},'Cancellation':{'is_cancelled':'cancel'},
 'WasiFunction':{'resolve':'wresolve','name':'wname','parameters':'wparams','results':'wresults'},
 'Profile':{'floats':'profile_floats'},
 'SwiftControl':{'source_limit':'control_source','expired':'control_expired','operand':'control_operand','control':'control_control','locals':'control_locals','body':'control_body'},
 'Policy':{n:'policy_'+n for n in ('swift','legacy_imports','floats','tables','module_bytes','functions','types','type_parameters_total','parameters_per_signature','parameters_plus_locals','local_groups','instructions','operand_stack','control_depth','globals','exports','data_segments','element_segments','name_bytes','table_elements','memory_pages')},
}
FREE={'load_selected_retained_profile_v1':'loader','load_inner':'inner','budget_valid':'budget','sections':'sections','header':'header','validate_list':'list','parse_build':'build','parse_session':'session','read_request':'read_attempt','retained':'retained','c_string':'cstring','observe':'observe','check_final_identity_v1':'final_one','final_metadata_recheck_v1':'final_all','record_validation_peak':'peak','source_bytes_equal':'equality','encode_environment':'env','parse_hex':'hex','word':'word','identity':'identity','hash':'hash','validate_swift_reactor':'validator_entry','validate':'vvalidate','exact_abi':'vabi','segments_fit':'vsegments','read':'mread','all':'vall','u32_offset':'moffset','span':'mspan','utf8':'mutf8','name':'mname','constant':'mconstant','limits':'mlimits','compare_names':'mcompare','sift':'msift','duplicate_exports':'mduplicate','usage':'vusage','failure':'vfailure','numeric_type':'numeric','shape':'shape','saturating_shape':'saturating'}
BYOWNER=collections.defaultdict(list)
for n,f in F.items():
 if '{closure#' not in n:BYOWNER[f['owner']].append(n)
def primary(owner):
 v=BYOWNER[owner]
 if len(v)!=1:raise ValueError(('primary',owner,v))
 return v[0]

def target_of(statement):
 rhs=statement.split(' = ',1)[1];depth=0
 for i,c in enumerate(rhs):
  if c=='<':depth+=1
  elif c=='>' and (i==0 or rhs[i-1]!='-'):depth-=1
  elif c=='(' and depth==0:return rhs[:i]
 raise ValueError(('unsupported call target',rhs))

def resolve(target):
 methods=re.findall(r'::([A-Za-z_][A-Za-z_0-9]*)(?=::<|$)',target)
 method=methods[-1] if methods else target.split('::<',1)[0].rsplit('::',1)[-1]
 if ' as Declaration>' in target:
  return next(n for n,f in F.items() if f['owner']=='declaration_setter' and f['declared_name'].endswith('::'+method))
 if re.search(r' as (?:experimental::account::)?MeterControl>',target):
  if method in ('source_limit','expired','operand','control','locals','body'):return primary('control_'+('source' if method=='source_limit' else method))
 if method in ('eq','ne'):
  # Actual authored PartialEq bodies (including the std default ne callback).
  candidates=[n for n,f in F.items() if f['owner']=='derived_eq' and any(t in target for t in re.findall(r'_1: &([^,)]+)',f['head']))]
  if len(candidates)==1:return candidates[0]
 if method=='default':
  for name,f in F.items():
   if f['owner']=='derived_default':
    ret=re.search(r' -> (.+) \{',f['head'])[1]
    if re.search(r'\b'+re.escape(ret.rsplit('::',1)[-1])+r'\b',target):return name
  if 'D as Default' in target:
   return next(n for n,f in F.items() if f['owner']=='derived_default' and 'SwiftDeclaration' in f['head'])
 for receiver,methods in METHODS.items():
  if re.search(r'\b'+receiver+r'(?:<|::|\s|>)',target) and method in methods:return primary(methods[method])
 if target.startswith(('swift::','experimental::swift::','metadata::','experimental::metadata::','experimental::validate::','float::','validate::','retained_profile_loader_v1::')) and method in FREE:return primary(FREE[method])
 if method in FREE and ('::' not in target.split('::<',1)[0] or target.startswith('experimental_swift_reactor::retained_profile_loader_v1::')):return primary(FREE[method])
 return None
rows={};unknown_calls=[];standard=collections.Counter()
# The maximum repeat factor is per particular basic-block occurrence. Sequential
# loops do not multiply one another. Whole-body factors deliberately overpay
# setup, return and failure blocks, preserving all written alternatives.
LOOPS={'identity_encode':9,'hex':33,'sections':5,'list':65,'build':5,'session':5,'read_attempt':33,'retained':'retained_visits','cstring':4097,'observe':66,'env':2080,'inner':11,'final_all':5}
for n,f in F.items():
 local_types=f['locals'];counts=collections.Counter();actions=2 # entry+return allowance in addition to explicit Return
 params=set(re.findall(r'(_\d+):',f['head'].split(' -> ',1)[0]))
 actions+=2*sum(leaves(local_types[v]) for v in params)
 counts['parameter_leaf_fetch_store']=2*sum(leaves(local_types[v]) for v in params)
 calls=[];std=0
 for st in f['statements']:
  # One assignment/rvalue or terminator/primitive event and one control event;
  # destination/operand mentions separately pay both fetch and store per leaf.
  # Every projection punctuation is an extra dereference/index/coercion event.
  mentions=re.findall(r'\b_\d+\b',st)
  amount=2*sum(leaves(local_types[v]) for v in mentions)
  projections=sum(st.count(c) for c in '.*[]')
  base=2+projections
  counts['local_leaf_fetch_store']+=amount;counts['statement_rvalue_control_projection']+=base
  actions+=amount+base
  if ' = ' in st and ') -> [' in st:
   target=target_of(st);callee=resolve(target)
   if callee:calls.append(dict(target=target,callee=callee,multiplicity=1))
   else:
    std+=1;standard[target]+=1
    if not any(target.endswith('::'+ffi) for ffi in ('_NSGetArgc','_NSGetArgv','_NSGetEnviron','_NSGetExecutablePath','getcwd','CC_SHA256')) and target.startswith(('experimental::','retained_profile_loader_v1::','Loader','Reader','Buffer','Metadata','BodyState','Swift','FileIdentity','Policy','<experimental::','<D as')):unknown_calls.append((n,target))
 # Exact compiler closure identities in primitive call type arguments close
 # callback ownership. Dynamic scans/array map/find have explicit finite caps;
 # all other map/error/option/Fn callbacks are one invocation per callsite.
 callback_bound=1
 for st in f['calls']:
  target=target_of(st)
  for closure_type in re.findall(r'\{closure@[^}]+\}',target):
   candidates=[k for k,g in F.items() if '{closure#' in k and closure_type in g['head']]
   if len(candidates)!=1:raise ValueError(('closure resolution',target,candidates))
   count=1
   if '::position::<' in target or '::any::<' in target:
    count=5 if f['owner']=='list' and '::any::<' in target else 4096
   if '::find::<' in target:count=34
   if target.startswith(('array::','std::array::')) and '::map::<' in target:count=5
   calls.append(dict(target=target,callee=candidates[0],multiplicity=count))
   callback_bound=max(callback_bound,count)
 # Standard Type-slice comparisons can invoke the authored Type equality up to
 # the selected128 parameters. Other primitive scalar comparisons have no
 # authored callback; direct product PartialEq/Default calls resolved above.
 if f['owner']!='derived_eq':
  eq_type=next(k for k,g in F.items() if g['owner']=='derived_eq' and '_1: &Type,' in g['head'])
  for st in f['calls']:
   target=target_of(st)
   if 'PartialEq' in target and re.search(r'\bType\b',target) and resolve(target) is None:
    calls.append(dict(target='Type-slice equality closed callbacks: '+target,callee=eq_type,multiplicity=128))
 rows[n]=dict(owner=f['owner'],mir_sha256=f['sha256'],local_actions=actions,parts=dict(counts),calls=calls,standard_calls=std,callback_bound=callback_bound,repeat=1 if '{closure#' in n else LOOPS.get(f['owner'],1),native=[])
# Name all requested-byte primitive families; no storage union is turned into work.
NATIVE={'read_attempt':[('read_buffer',1)],'hash':[('maximum_file',1),(32,1)],'bytes_put':[(16384,1)],'bytes_word':[(8,1)],'word':[(8,1)],'identity_encode':[(64,1)],'list':[(16384,3),(8190,7)],'build':[(512,1)],'session':[(4096,1),(512,1)],'observe':[(4096,2)],'env':[(8190,2)],'inner':[('maximum_file',3),(16384,2),(4096,1),(64,1),(32,16)],'retained':[('maximum_file',2)],'equality':[('source',2)],'vvalidate':[('validator_source',1),(16384,1)],'breserve':[('allocation_cap',2)],'bpush':[('allocation_cap',1)],'mcompare':[(8192,1)],'wresolve':[(8192,34),(256,1)],'vabi':[(8192,3)],'vfailure':[(4096,1)]}
for n,row in rows.items():
 if '{closure#' not in n:row['native']=[dict(extent=e,count=k) for e,k in NATIVE.get(row['owner'],[])]
# Fixed no-credit segment categories: multiply the complete vsegments body2,
# including empty inner scan setup/exit and every callee/copy alternative.
rows[primary('vsegments')]['validator_fixed_repeat']=2
if unknown or unknown_calls:
 put=lambda n,v:(D/n).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
 put('mir-unresolved.json',dict(types=sorted(unknown),calls=unknown_calls));raise SystemExit('unresolved types/calls; quote unavailable')
(D/'mir-ledger.json').write_text(json.dumps(dict(schema=1,parent_mir_sha256=X['parent_mir_sha256'],source_tree_sha256='450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a',fields=FIELDS,parametric_copy_leaves=PARAMETRIC,opaque_standard_types=sorted(opaque),closure_leaves=closure_leaves,roots=dict(loader=primary('loader'),validator=primary('validator_entry')),nodes=rows,standard_targets=dict(standard)),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status='MIR-priced-proposal',nodes=len(rows),primitive_targets=len(standard))))
