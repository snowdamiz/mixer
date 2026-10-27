"""Build the finite manual-call-resolution ledger, never execute engine code."""
import hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent; R=D.parents[1]
BASE=R/'verification/swift-guarded-snapshot-funding-implementation/source/vm'
OVER=R/'verification/swift-guarded-snapshot-descriptor-rebinding/overlay/vm'

def sha(b):return hashlib.sha256(b).hexdigest()
def put(name,v):(D/name).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
# Lexer consumes comments and string/character literals before punctuation. It
# is used only for reproducible attribution/overcounting, never source admission.
TOKEN=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|b?"(?:\\.|[^"\\])*"|b?\'(?:\\.|[^\'\\])\'|[A-Za-z_][A-Za-z_0-9]*|[0-9][A-Za-z_0-9]*|[^\s]',re.M)
def masked(s):
    return ''.join(' '*len(m.group()) if m.group().startswith(('//','/*','"','b"',"'","b'")) else m.group() for m in TOKEN.finditer(s))
def body(path,anchor):
    p=OVER/path if (OVER/path).exists() else BASE/path
    text=p.read_text(); start=text.index(anchor); begin=text.index('{',start)
    # Span matching uses a same-length comment/string mask.
    mask=list(text)
    for m in TOKEN.finditer(text):
        if m.group().startswith(('//','/*','"','b"',"'","b'")):
            mask[m.start():m.end()]=' '*len(m.group())
    depth=0
    for at in range(begin,len(text)):
        depth+=(mask[at]=='{')-(mask[at]=='}')
        if depth==0:break
    value=text[start:at+1]
    return dict(path=str(p.relative_to(R)),line=text.count('\n',0,start)+1,end_line=text.count('\n',0,at)+1,sha256=sha(value.encode()),bytes=len(value.encode())),value

nodes={}; source_text={}; resolutions={}
def node(name,path,anchor,copy_leaves=0):
    src,text=body(path,anchor); source_text[name]=text
    tokens=[m.group() for m in TOKEN.finditer(text) if not m.group().startswith(('//','/*'))]
    # Each written token is allocated a possible fetch and store event. This
    # deliberately also allocates unused events for literals, delimiters, type
    # annotations, patterns and non-selected branches. Call expansion is extra.
    # Aggregate leaves are added explicitly; no byte capacity is a work price.
    nodes[name]=dict(status='priced',source=src,parts=dict(entry_return=2,
        occurrence_fetch=len(tokens),occurrence_store=len(tokens),
        explicit_typed_copy_fetch=copy_leaves,explicit_typed_copy_store=copy_leaves),calls=[],bytes=[])
    resolutions[name]=[]
def edge(name,callee,count=1,reason='manual call-DAG occurrence'):
    nodes[name]['calls'].append(dict(node=callee,count=count));resolutions[name].append(dict(callee=callee,count=count,reason=reason))
def occurrence(name,callee,pattern,factor=1):
    count=len(re.findall(pattern,source_text[name]))*factor
    if not count:raise AssertionError((name,callee,pattern))
    edge(name,callee,count,'source pattern '+pattern+('; fixed multiplicity '+str(factor) if factor!=1 else ''))
def native(name,extent,count=1):nodes[name]['bytes'].append(dict(extent=extent,count=count))
L='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
# Complete selected wrapper helpers; no carrier adoption/scope/VM dispatch.
for name,anchor,copies in [
 ('failure','fn new(kind: Refusal',8),('io_failure','fn io(role:',4),
 ('identity_encode','fn encode(self)',8),('bytes_new','fn new() -> Self',0),
 ('bytes_slice','fn slice(&self)',1),('bytes_put','fn put(&mut self',2),('bytes_word','fn word(&mut self',2),
 ('word','fn word(b:',2),('hex','fn parse_hex(',33),('sections','fn sections<',12),
 ('header','fn header(',4),('list','fn validate_list(',4),('build','fn parse_build(',1),
 ('session','fn parse_session(',6),('budget','fn budget_valid(',10),
 ('read_attempt','fn read_request<',8),('identity','fn identity(',10),('retained','fn retained(',13),
 ('hash','pub(super) fn hash(',33),('cstring','pub(super) unsafe fn c_string',1),
 ('observe','pub(super) fn observe(',68),('env','fn encode_environment(',8),
 ('inner','fn load_inner(',64),('final_one','fn check_final_identity_v1(',20),
 ('final_all','fn final_metadata_recheck_v1(',32),('peak','fn record_validation_peak(',13),
 ('equality','fn source_bytes_equal(',1),('loader','pub(super) fn load_selected_retained_profile_v1(',5)]:node(name,L,anchor,copies)
# Leaf counts are intentionally upper-summed across both success/refusal paths.
for name in list(nodes):
    if name!='failure' and 'LoaderFailureV1::new(' in source_text[name]:occurrence(name,'failure',r'LoaderFailureV1::new\(')
    if name!='io_failure' and 'LoaderFailureV1::io(' in source_text[name]:occurrence(name,'io_failure',r'LoaderFailureV1::io\(')
edge('io_failure','failure')
edge('identity_encode','word',8,'eight u64 little-endian word-equivalent primitive calls; covers all encode iterations')
native('identity_encode',64)
edge('bytes_word','bytes_put');native('bytes_word',8)
# Bounded helper bodies with loops represented by closed explicit multiplicities.
# Tokens count the written iteration once; add repeated bodies by expanding that
# same complete helper. This overcovers each setup/return too.
# These local helpers are deliberately repeated in full at the enclosing caller.
for name in ('sections',):edge(name,'word',4)
edge('header','word',3)
edge('list','word',65);native('list',P:=16384,4);native('list',4095,2*64*5)
edge('build','header');edge('build','sections');edge('build','list',2);edge('build','word',5)
native('build',512)
edge('session','header');edge('session','sections');edge('session','list',2);edge('session','word',7);native('session',4096+512)
# C-string's 4096 direct pointer reads/decisions are explicit, not zero-cost max input.
nodes['cstring']['parts']['repeat_pointer_add_deref_compare_branch_loop']=4096*(1+1+1+1+3)
# 32 hex digits, two closed digit decisions each; full tokens once plus repeated
# scalar digit/index/check/store/loop events, and the 32-byte output initializer.
nodes['hex']['parts']['repeat_digit_index_checked_arithmetic_store_loop']=32*(2*(2+4+1)+2+2+1+1+1+3)
native('hex',32)
# read_attempt's full lexical body includes one written attempt; complete it 32
# times per request via retained below (all branches/error constructors retained).
native('read_attempt',4096)
edge('retained','read_attempt',32);edge('retained','identity');native('retained','retained_bytes')
edge('hash','failure');native('hash',32)
edge('observe','bytes_new',5);edge('observe','bytes_word',129);edge('observe','bytes_put',128)
edge('observe','cstring',128);edge('observe','hex',2);edge('observe','env')
native('observe',57344+1536);native('observe',16384,3);native('observe',4096,2)
# Explicit insertion-sort triangular comparison/iteration maximum incl swaps;
# ordinary env count64 covers early failures before the two identities exist.
nodes['env']['parts']['sort_comparison_decision_swap_cursor_and_loops']=2016*(1+1+6+1+1+3)
native('env',8190,2016+64);edge('env','bytes_word',65);edge('env','bytes_put',64);native('env',16384)
edge('inner','budget');edge('inner','observe');edge('inner','identity',4)
# Retained needs a role-specific request count; special wrapper node below prices
# 32 attempts for every 4096-byte block and EOF, and initializes all role bytes.
# No use of retained node here: avoid multiplying all-file bytes per role.
edge('inner','retained',4)
edge('inner','read_attempt','read_requests') # 31 extra copies below make 32 total
nodes['inner']['calls'][-1]['count']='read_attempts_extra'
edge('inner','build');edge('inner','session');edge('inner','hex',5)
edge('inner','hash',12);native('inner','build_sections');native('inner','session_sections')
for n in ('build','session','source','executable'):native('inner',n)
native('inner','source');native('inner',16384,2);native('inner',4096);native('inner',32,5+4+3+3)
edge('inner','identity_encode');edge('inner','peak',2);edge('inner','equality');edge('inner','final_all')
# Every live temporary owner has a terminal drop route (library internals excluded).
nodes['inner']['parts']['temporary_owned_drop_calls']=4+1+8+1
edge('final_one','failure');edge('final_all','final_one',4);edge('final_all','identity',4)
edge('equality','proof_source');edge('loader','inner')
# Validator acyclic expanded source. All positive-credit loops are erased to one
# written iteration. Fixed loops that can repeat without credit are expanded.
V='src/experimental/swift.rs';Q='src/experimental/account.rs';E='src/experimental/reader.rs';M='src/experimental/metadata.rs';T='src/experimental/validate.rs'
spec=[
 ('proof_source',V,'pub fn source(&self)',1),('proof_usage',V,'pub fn usage(&self)',11),
 ('vdefault',V,'fn default() -> Self',5),('vusage',V,'fn usage(raw:',24),('vfailure',V,'fn failure(',44),
 ('validator_entry',V,'pub fn validate_swift_reactor(',5),('vvalidate',V,'fn validate(',68),
 ('vabi',V,'fn exact_abi(',75),('vsegments',V,'fn segments_fit(',6),
 ('meter_new',Q,'pub fn swift(',23),('meter_source',Q,'pub fn source_limit(&self)',1),
 ('meter_usage',Q,'pub fn usage(&self)',8),('meter_error',Q,'pub fn error(&self',26),
 ('meter_check',Q,'pub fn check(&self',3),('meter_work',Q,'pub fn work(&mut',3),
 ('meter_reserve',Q,'pub fn reserve(\n        &mut self,\n        category:',3),('meter_release',Q,'pub fn release(',2),
 ('bnew',Q,'pub fn new(category:',1),('blen',Q,'pub fn len(&self)',1),('bslice',Q,'pub fn as_slice(&self)',1),
 ('bget',Q,'pub fn get(&self',1),('bgetmut',Q,'pub fn get_mut(&mut',1),('blast',Q,'pub fn last(&self',1),
 ('blastmut',Q,'pub fn last_mut(&mut',1),('bpop',Q,'pub fn pop(&mut',6),('btruncate',Q,'pub fn truncate(',1),
 ('bswap',Q,'pub fn swap(',2),('breserve',Q,'pub fn reserve(\n        &mut self,\n        capacity:',3),
 ('bpush',Q,'pub fn push(',6),('bdispose',Q,'pub fn dispose(',1),
 ('rnew',E,'pub fn new(bytes:',3),('rcursor',E,'pub fn cursor(',3),('rerror',E,'pub fn error(',3),
 ('rbyte',E,'pub fn byte(',1),('rtake',E,'pub fn take(',2),('ruint',E,'pub fn uint(',1),
 ('rsigned',E,'pub fn signed(',1),('rcount',E,'pub fn count(',1),('rty',E,'pub fn ty(',1),('rend',E,'pub fn end(',1),
 ('span_slice',M,'pub fn slice(self',2),('mnew',M,'fn new() -> Self',4),('msignature',M,'pub fn signature(',3),
 ('mparams',M,'pub fn params(',3),('moffset',M,'fn u32_offset(',3),('mspan',M,'fn span(',3),
 ('mutf8',M,'fn utf8(',3),('mname',M,'fn name(',3),('mconstant',M,'fn constant(',3),('mlimits',M,'fn limits(',3),
 ('mread',M,'pub(super) fn read<',24),('mcompare',M,'fn compare_names(',3),('msift',M,'fn sift(',3),('mduplicate',M,'fn duplicate_exports(',3),
 ('snew',T,'fn new(function:',9),('serror',T,'fn error(&self',3),('spopany',T,'fn pop_any(',6),
 ('spop',T,'fn pop(\n',2),('spush',T,'fn push(\n',2),('sresult',T,'fn result(',2),('sunreachable',T,'fn unreachable(',3),
 ('slabel',T,'fn label(',3),('scall',T,'fn call(',3),('sdispose',T,'fn dispose(',1),('vall',T,'pub(super) fn all(',18),
 ('resource','src/experimental/mod.rs','fn resource(mut self',26),
 ('cancel','src/execute.rs','pub fn is_cancelled(',1),
 ('numeric','src/validate.rs','pub(crate) fn numeric_type(',3),('shape','src/float.rs','pub(crate) fn shape(',3),
 ('saturating','src/float.rs','pub(crate) fn saturating_shape(',2),
 ('wresolve','src/experimental_wasi/descriptor.rs','pub fn resolve(',4),('wname','src/experimental_wasi/descriptor.rs','pub fn name(',1),
 ('wparams','src/experimental_wasi/descriptor.rs','pub fn parameters(',1),('wresults','src/experimental_wasi/descriptor.rs','pub fn results(',1),
]
for row in spec:node(*row)
# Resolve product calls by receiver/context; each exact match is extra on top of
# local occurrence events. std primitives remain local plus named byte requests.
for name,*_ in spec:
    text=source_text[name]
    patterns=[('meter_error',r'meter\.error\('),('meter_work',r'meter\.work\('),('meter_check',r'meter\.check\('),('meter_release',r'meter\.release\('),('meter_reserve',r'meter\.reserve\('),('meter_usage',r'meter\.usage\('),('meter_source',r'meter\.source_limit\('),('resource',r'\.resource\('),('rcursor',r'\b[rs]\.cursor\('),('rerror',r'\b[rs]\.error\('),('rbyte',r'\b[rs]\.byte\('),('rtake',r'\b[rs]\.take\('),('ruint',r'\b[rs]\.uint\('),('rsigned',r'\b[rs]\.signed\('),('rcount',r'\b[rs]\.count\('),('rty',r'\b[rs]\.ty\('),('rend',r'\b[rs]\.end\('),('mparams',r'm\.params\('),('msignature',r'm\.signature\('),('spop',r'state\.pop\('),('spopany',r'state\.pop_any\('),('spush',r'state\.push\('),('sresult',r'state\.result\('),('sunreachable',r'state\.unreachable\('),('slabel',r'state\.label\('),('scall',r'state\.call\('),('sdispose',r'state\.dispose\('),('serror',r'state\.error\(')]
    for callee,pattern in patterns:
        if re.search(pattern,text):occurrence(name,callee,pattern)
    # Buffer operations through explicit non-self values; all getters have the
    # same conservative max Copy footprint even for references and Option<T>.
    for method,callee in [('len','blen'),('as_slice','bslice'),('get','bget'),('get_mut','bgetmut'),('last','blast'),('last_mut','blastmut'),('pop','bpop'),('truncate','btruncate'),('swap','bswap'),('reserve','breserve'),('push','bpush'),('dispose','bdispose')]:
        pattern=r'\.(?:'+method+r')\('
        count=len(re.findall(pattern,text))
        # Earlier resolution for state.dispose/pop/push are also retained here
        # as conservative extra primitive/getter work, never a discount.
        if count and name not in ('blen','bslice','bget','bgetmut','blast','blastmut','bpop','btruncate','bswap'):
            edge(name,callee,count,'all written .'+method+' sites; includes conservative non-Buffer duplicates')
# Remove self-recursive generic matches: reserve/push/dispose functions expand
# their real nested Buffer calls explicitly, not a self-reference.
nodes['breserve']['calls']=[c for c in nodes['breserve']['calls'] if c['node']!='bpush']
for name in ('breserve','bpush','bdispose'):
    nodes[name]['calls']=[c for c in nodes[name]['calls'] if c['node']!=name]
# Fixed direct callee occurrences and helper self-receiver resolutions.
for n,c,k in [
 ('validator_entry','vvalidate',1),('validator_entry','vfailure',1),('vfailure','vusage',1),('vvalidate','vdefault',1),
 ('vvalidate','meter_new',1),('vvalidate','mread',1),('vvalidate','vabi',1),('vvalidate','vsegments',1),('vvalidate','vall',1),('vvalidate','vusage',1),
 ('vabi','wresolve',1),('vabi','span_slice',3),('vsegments','bslice',2),
 ('meter_check','cancel',1),('meter_work','meter_check',1),('meter_work','meter_error',2),('meter_reserve','meter_check',1),('meter_reserve','meter_error',3),('meter_reserve','meter_source',1),
 ('meter_source','control_source',1),('meter_check','control_expired',1),('meter_reserve','resource',2),
 ('rerror','rcursor',1),('rerror','meter_error',1),('rbyte','meter_work',1),('rbyte','rcursor',1),('rbyte','rerror',1),
 ('rtake','meter_work',1),('rtake','rcursor',1),('rtake','rerror',1),('ruint','rbyte',1),('ruint','rerror',2),
 ('rsigned','rbyte',1),('rsigned','rerror',2),('rcount','ruint',1),('rcount','rerror',1),('rty','rbyte',1),('rty','rerror',1),('rend','rerror',1),
 ('mnew','bnew',8),('msignature','blen',2),('msignature','bget',3),('mparams','bslice',1),('mspan','moffset',2),
 ('mname','mutf8',1),('mname','mspan',1),('mread','rnew',2),('mread','mnew',1),('mread','mname',4),('mread','mconstant',3),('mread','mlimits',2),('mread','moffset',1),('mread','mspan',4),('mread','mduplicate',1),
 ('mcompare','span_slice',2),('msift','mcompare',2),('mduplicate','mcompare',1),('mduplicate','msift',2),('mduplicate','bnew',1),
 ('snew','bnew',3),('serror','meter_error',1),('spopany','meter_work',1),('spopany','serror',2),('spop','spopany',1),('spop','serror',1),
 ('sresult','spop',1),('sunreachable','meter_work',1),('sunreachable','serror',1),('slabel','meter_work',1),('slabel','serror',1),
 ('scall','spop',1),('scall','spush',1),('vall','snew',1),('vall','rnew',1),('vall','span_slice',1),('vall','numeric',1),('vall','saturating',1),
 ('numeric','shape',1),('wresolve','wname',34),('wresolve','wparams',1),('wresolve','wresults',1)]:edge(n,c,k)
# Exact Swift control methods and policy getters; frozen policy branches remain
# source-bound but are unreachable in this selected Swift entry.
for n,a,c in [('control_source','fn source_limit(&self) -> usize {\n        self.source_limit',1),('control_expired','fn expired(&self) -> bool {\n        std::time',1),('control_operand','fn operand(&mut self, n:',1),('control_control','fn control(&mut self, n:',1),('control_locals','fn locals(&mut self, n:',1),('control_body','fn body(&mut self) {\n        self.observations',1)]:node(n,Q,a,c)
for n in ('vvalidate','vall','spush'):
    for method in ('operand','control','locals','body'):
        if 'meter.control.'+method+'(' in source_text[n]:occurrence(n,'control_'+method,r'meter\.control\.'+method+r'\(')
for method in ('swift','legacy_imports','floats','tables','module_bytes','functions','types','type_parameters_total','parameters_per_signature','parameters_plus_locals','local_groups','instructions','operand_stack','control_depth','globals','exports','data_segments','element_segments','name_bytes','table_elements','memory_pages'):
    anchor='pub fn '+method+'('
    node('policy_'+method,'src/experimental/policy.rs',anchor,1)
    for n in list(nodes):
        if n.startswith('policy_'):continue
        pat=r'(?:policy|limits)\.'+method+r'\('
        if re.search(pat,source_text[n]):occurrence(n,'policy_'+method,pat)
edge('vvalidate','policy_swift')
# Each byte request is bounded BEFORE allocation/copy under the exact five
# limits. Zero-capacity requests are still logical primitive calls above.
native('vvalidate','transfer_chunk');native('vvalidate','source');native('breserve','allocation_cap',2);native('bpush','allocation_cap')
native('wresolve','import_name_compare',34);native('wresolve',128*2+2);native('mcompare','name_compare')
# Fixed outer two-way segment scan may be empty (zero credits): two copies of
# its body are included directly, instead of pretending its backedge is metered.
edge('vsegments','meter_work',1,'second segment-category body, fixed count2 even if empty')
# The complete vsegments local body, including both categories, is charged twice.
nodes['vsegments']['parts']['second_fixed_category_occurrence_fetch']=nodes['vsegments']['parts']['occurrence_fetch']
nodes['vsegments']['parts']['second_fixed_category_occurrence_store']=nodes['vsegments']['parts']['occurrence_store']
# Declaration setters and default source helpers are scalar local occurrences
# in mread, with explicit extra stores/call-entry events for both callbacks.
nodes['mread']['parts']['declaration_memory_table_callback_events']=2*(2+2+2)
put('token-candidate-ledger.json',dict(schema=1,unit='named source logical operation plus requested native byte; closed callbacks once',
    wrapper_root='loader',validator_root='validator_entry',nodes=nodes))
put('token-candidate-call-resolution.json',dict(schema=1,resolutions=resolutions,method='source patterns plus manual product-call resolution; independent review required'))
put('cap-geometry.json',dict(source=67108864,build=131072,session=65536,executable=67108864,validator_source=67108864,metadata=16777216,scratch=1048576,credits=512000000,deadline=120000))
print(json.dumps(dict(nodes=len(nodes),body_bytes=sum(x['source']['bytes'] for x in nodes.values()),status='generated-proposal-no-engine-code-executed')))
