"""Substantive compiler-constant, exact source-origin and caller review."""
from replay import *
LOADER='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
ENV_KEYS=['MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256']
def compiled_constant(blocks,source):
 old=next(b for b in blocks[0] if b.startswith('const COMPILED:'))
 cur=next(b for b in blocks[3] if b.startswith('const COMPILED:'))
 oldreceipt=load(V/'swift-guarded-snapshot-loader-work-source146/compiler-receipt.json')
 receipt=load(V/'swift-guarded-snapshot-owned-provider-work-storage/commands/capture-layout/receipt.json')
 values=[x['value'] for x in M.literal_tokens(old)]
 require(values==[oldreceipt['environment'][k] for k in ENV_KEYS],'five original baked compiler values and exact receipt environment')
 require(not set(ENV_KEYS)&receipt['environment'].keys(),'current query has no injected five build identities')
 expected='''const COMPILED: [Option<&str>; 5] = {
    let mut _0: [std::option::Option<&str>; 5];
    let mut _1: std::option::Option<&str>;
    let mut _2: std::option::Option<&str>;
    let mut _3: std::option::Option<&str>;
    let mut _4: std::option::Option<&str>;
    let mut _5: std::option::Option<&str>;
    bb0: {
        StorageLive(_1);
        _1 = Option::<&str>::None;
        StorageLive(_2);
        _2 = Option::<&str>::None;
        StorageLive(_3);
        _3 = Option::<&str>::None;
        StorageLive(_4);
        _4 = Option::<&str>::None;
        StorageLive(_5);
        _5 = Option::<&str>::None;
        _0 = [move _1, move _2, move _3, move _4, move _5];
        StorageDead(_5);
        StorageDead(_4);
        StorageDead(_3);
        StorageDead(_2);
        StorageDead(_1);
        return;
    }
}'''
 require(project(cur)==expected,'current COMPILED exact five-None typed semantics')
 src=source[LOADER].decode();decl=src[src.index('const COMPILED:'):src.index('\n];',src.index('const COMPILED:'))+3]
 require(decl=='const COMPILED: [Option<&str>; 5] = [\n'+''.join('    option_env!("'+k+'"),\n' for k in ENV_KEYS)+'];','exact source compiler-origin declaration')
 def raw_bytes(block):
  if not block.startswith('alloc'):return None
  raw=[]
  for line in block.splitlines()[1:-1]:
   parts=line.split('│')
   if len(parts)!=3:return None
   tokens=parts[1].split()
   if not all(re.fullmatch('[0-9a-f]{2}',x) for x in tokens):return None
   raw.extend(int(x,16) for x in tokens)
  return bytes(raw)
 removed=[b for b in blocks[0] if raw_bytes(b) in {v.encode() for v in values}]
 require(len(removed)==5 and len({raw_bytes(b) for b in removed})==5,'exact five original baked string allocations removed')
 return {'source_path':LOADER,'source_declaration':decl,'source_sha256':sha(source[LOADER]),'original_typed_constant':project(old),'current_typed_constant':project(cur),
  'old_values':values,'environment_keys':ENV_KEYS,'current_values':[None]*5,'removed_allocation_headers':[b.splitlines()[0] for b in removed],
  'substantive_compile_input_change_not_normalization':True,
  'effect':'COMPILED.map preserves None through each and_then callback. embedded.iter().any(Option::is_none) is true, so a call reaching the check returns UnsupportedBuild before a successful SelectedValidatedProfileV1. Earlier loader refusals are possible. The potential-success graph is retained in full for the conditional proof, never pruned on this early refusal.',
  'future_input_obligation':'A future compiler invocation injecting any identity, including the five original strings, requires fresh exact compiler/source/constant/executable/session correspondence and a fresh envelope census. This metadata query is not a linked fixture executable; 5080 does not bound arbitrary future option_env values.',
  'current_successful_authenticated_loader_result':False},removed
def original_allocation_transport(blocks,removed):
 mapping=load(D/'original-current-construct-map.json');require(len(mapping['unmatched'])==1 and mapping['unmatched'][0]['old_header']=='const COMPILED: [Option<&str>; 5] = {','only substantive old constant change')
 added={x['ordinal'] for x in mapping['new_nonallocation_rows']};ordinal=-1;new=[]
 for b in blocks[3]:
  if probe(b,3):continue
  if not b.startswith('alloc'):ordinal+=1
  if b.startswith('alloc') or ordinal not in added:new.append(b)
 old=[b for b in blocks[0] if b not in removed and not b.startswith('const COMPILED: ')]
 pn,pi=S.norm,S.inert
 try:S.norm=project;S.inert=lambda b:False;result=S.compare_blocks(old,new)
 finally:S.norm,S.inert=pn,pi
 require(result['production_total']==5987 and result['production_functions']==2009,'complete original common construct conservation')
 result['removed_five_baked_identity_allocations_only']=[b.splitlines()[0] for b in removed]
 return result
def source_origins(tables):
 accepted=load(V/'swift-guarded-snapshot-string-exact-binding-independent/origin-and-type-review.json');current=tables[3];aliases=[];targets=[];constants=[]
 for item in accepted['alias_declaration_evidence']:
  sites=[]
  if 'actual_declaration_sites' not in item:
   require(item.get('standard_compiler_path')==T.ALIASES[item['compiler_alias']]==item['canonical_path'] and item['canonical_path'].startswith('std::'),'exact finite standard alias')
  for site in item.get('actual_declaration_sites',[]):
   line=current[site['path']].decode().splitlines()[site['line']-1]
   require(S.source_projection(line)==S.source_projection(site['declaration']),'source alias actual owner declaration:'+item['compiler_alias'])
   sites.append(dict(site,current_declaration=line,source_sha256=sha(current[site['path']])))
  aliases.append(dict(item,current_sites=sites))
 for item in accepted['authored_destination_origins']:
  site=item['source_origin']
  if site:
   line=current[site['path']].decode().splitlines()[site['line']-1]
   oldline=tables[0][site['path']].decode().splitlines()[site['line']-1]
   require(S.source_projection(line)==S.source_projection(site.get('text',oldline)),'complete target source owner:'+item['target'])
   targets.append(dict(item,current_source_origin=dict(site,text=line,source_sha256=sha(current[site['path']]))))
  else:targets.append(item)
 for item in accepted['typed_constant_actual_declarations']:
  if 'source_path' not in item:
   require(item['constant'] in ('core::num::<impl u64>::MAX','core::num::<impl usize>::MAX') and item['type']==T.CONSTANT_TYPES[item['constant']],'exact compiler primitive MAX origin')
   constants.append(item);continue
  require(item['declaration'] in current[item['source_path']].decode(),'constant source origin:'+item['constant'])
  constants.append(dict(item,current_source_sha256=sha(current[item['source_path']])))
 return {'source_aliases':aliases,'complete_authored_destinations':targets,'typed_constant_origins':constants,'specialization_source_preconditions':accepted['specialization_source_preconditions']}
def provider_reachability(blocks,source):
 new=[b for b in blocks[3] if provider(b)];require(len(new)==11,'all11 provider constructs included')
 current='\n'.join(project(b,span=False,oldroot=True) for b in blocks[3] if b.startswith('fn ') and not probe(b,3))+'\n'
 f,_,_=M.parse_functions(current,{p:b.decode() for p,b in source.items() if p.endswith('.rs')})
 incoming=[]
 for key,body in f.items():
  for call in body['calls']:
   if 'describe_existing_owner_candidate_v1' in call['target'] or any('describe_existing_owner_candidate_v1' in x for x in call['named_callbacks']):incoming.append({'caller':key,'call':call})
 require(not incoming,'new incoming production call or function item to provider')
 # Source-level item-use scan complements full compiler callsite inventory;
 # comments are removed while bytes/string literal contents remain exact.
 mentions=[]
 for p,data in source.items():
  if not p.endswith('.rs'):continue
  for n,line in enumerate(data.decode().splitlines(),1):
   if re.search(r'\bdescribe_existing_owner_candidate_v1\b',M.code_only(line)):mentions.append({'path':p,'line':n,'text':line})
 require(len(mentions)==1 and mentions[0]['path']==PROFILE and 'pub(super) fn describe_existing_owner_candidate_v1' in mentions[0]['text'],'only provider declaration in complete source146')
 force=next(b for b in blocks[3] if b.startswith('static OWNED_PROVIDER_LAYOUT_FORCE_V1:'))
 require('::describe_existing_owner_candidate_v1 as for<' in project(force) and 'PointerCoercion(ReifyFnPointer(Safe), Implicit)' in project(force),'exact inert query function pointer reference')
 # All added bodies/types are retained, including the numeric-only callback.
 body=next(b for b in new if b.startswith('fn describe_existing_owner_candidate_v1('));closure=next(b for b in new if b.startswith('fn describe_existing_owner_candidate_v1::'))
 require('-> Option<usize> {' in closure.splitlines()[0] and 'usize::checked_add' in closure,'provider closure scalar addition only')
 provider_function=next(v for v in f.values() if v['name']=='describe_existing_owner_candidate_v1')
 require(not provider_function['str_assignments'] and not any(re.search(r'\bstr\b',t) for t in provider_function['local_types'].values()) and '-> Result<UnqualifiedExistingOwnerCandidateV1' in body.splitlines()[0],'provider accepts borrowed bytes and returns shape result; no primitive str-valued local producer')
 return {'constructs':[{'header':b.splitlines()[0],'raw_sha256':sha(b.encode()),'typed_semantics':project(b)} for b in new],
  'compiler_assertion_literals_retained_in_complete_census':M.literal_tokens(body),
  'source_declaration_mentions':mentions,'incoming_production_calls_or_named_function_items':incoming,'query_only_forced_pointer':project(force),
  'conclusion':'The currently compiled provider is uncalled from production; its only extra function-pointer use belongs to the source-reconstructed query suffix. It has no edge out of the conservative selected roots and no production caller supplies it. This disconnection says nothing about the premises of a future admitted provider caller.',
  'outer_caller_review':'consume_outer_request_v1 builds FrozenFixtureV1 from the unchanged shared preexisting.binding, uses the selected account, keeps originals through inspect/observe, destroys the same actual payload and releases only Some destroyed token. The lifetime-bearing borrow ends before final result consumption. It adds no incoming authored str/Fault/failure/custom callback, but its binding/account/quote selectors are Pending; no actual authenticated owner or funded invocation follows.',
  'potential_future_caller_obligation':'A future provider caller must supply actual immutable owner/preimages/native backing, authenticated correspondence, acquisition and P0 accounting, and re-review all new reachable typed bodies/constant origins. Borrowed lifetime/shape/digest-claim checks cannot establish these facts.'}
def caller_contract(source):
 account=source[ACCOUNT].decode();profile=source[PROFILE].decode()
 for name,pending in [('selected_whole_quote_v1','WholeQuotePending'),('selected_parent_account_v1','RootPolicyPending')]:
  b=account.split('fn '+name+'()',1)[1].split('}',1)[0];require('Err(RefusalV1::'+pending+')' in b,'caller selector still pending:'+name)
 require('Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)' in profile,'binding selection Pending')
 old=load(OLD/'caller-contract.json')
 return dict(old,source_tree_sha256=TREES[3],host_tree_sha256='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2',
  shared_lifetime_owner_requirement='Exact shared immutable ReviewedFixtureBindingV1 and all nested identity/native/retained byte owners live through consuming outer call and final result consumption. No intervening mutation, arbitrary callback, incoming control/failure/Fault/str or substitute policy/trait/Read implementation.',
  current_metadata_query_is_final_fixture_executable=False,current_compiled_five_identity_values_present=False,
  current_success_path_executed=False,potential_success_graph_preserved=True,
  authenticated_owner_created_by_provider=False,actual_acquisition_implemented=False,
  actual_P0_root_caller_and_fixture_binding_selected=False,L_str_selected=False,whole_host_funding=False,operational_grant=False,OTA=False,GA=False,
  future_compiler_identity_change_requires_fresh_rebind=True,
  pending=['actual acquired immutable authenticated owner and native/retained backing','root policy/account/whole quote and whole-host funding','source/compiler/build/session/linked-executable identity correspondence with actual option_env values','successful loader/writer/destructor/healthy cleanup evidence','paused native/runtime/phone/UI/capture checks','separate published immutable FieldLog package; OTA and GA'])
def bind_caller(proposed,expected):
 require(canon(proposed)==canon(expected),'exact current caller conditions and no authority changes')
 return {'conditional_source_rebind_only':True,'actual_caller_or_operational_authority':False}
def main(check=False):
 tables=source_tables();blocks=[S.parse_mir(t)[0] for t in mir_texts()]
 compiled,removed=compiled_constant(blocks,tables[3]);allocation=original_allocation_transport(blocks,removed)
 for name,obj in [('compiler-constant-review.json',compiled),('original-allocation-transport.json',allocation),('source-owner-alias-rebind.json',source_origins(tables)),('provider-reachability-review.json',provider_reachability(blocks,tables[3])),('caller-contract.json',caller_contract(tables[3]))]:save(name,obj,check)
 print(json.dumps({'substantive_constant_reviewed':True,'common_original_constructs':allocation['production_total'],'common_allocation_ids':len(allocation['allocation_mapping']),'source_aliases':len(source_origins(tables)['source_aliases']),'operational_grant':False}))
if __name__=='__main__':main('--check' in sys.argv)
