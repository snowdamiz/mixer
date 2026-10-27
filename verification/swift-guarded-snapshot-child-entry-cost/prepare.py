#!/usr/bin/env python3
"""Produce a source146 entry-shell cost candidate from frozen data only."""
from pathlib import Path
import collections,gzip,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent;V=ROOT/'verification'
COMP=V/'swift-guarded-snapshot-host-composition';IND=V/'swift-guarded-snapshot-host-composition-independent'
HELP=V/'swift-guarded-snapshot-loader-work-source146';BASE=V/'swift-guarded-snapshot-funding-implementation/source/vm'
checks=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def check(name,yes):
    if not yes:raise AssertionError(name)
    checks.append(name)
def put(name,obj):(D/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
release=V/'swift-semantic-adapter-root-review/guarded-snapshot-host-child-entry-cost-source-release.json'
check('root-source-release',sha(release.read_bytes())=='4a3dbe46c4737fd9c443d587ec2de613c70d13d62025cf8df1de171d9441d0b5')
helper_release=V/'swift-semantic-adapter-root-review/guarded-snapshot-loader-work-source146-independent-release.json'
check('root-helper-release',sha(helper_release.read_bytes())=='bfac9857159e1ca070e08f6698d8a27d124abf0279e9657b19c1fd5e5104ec30')
custody=[]
for p,expected in [(COMP,'2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e'),(IND,'c9ccf4649a4dd5c11ac62d403e6443f58dd018562d667f76d16dc422354f3e63'),(HELP,'1aacaaff5795625739811b2502476c22567c2b5a3bcc9fb096e61fa5c147c976')]:
    check('seal:'+p.name,sha((p/'seal.json').read_bytes())==expected)
    members=json.loads((p/'seal.json').read_text())['members']
    for m in members:
        b=(p/m['path']).read_bytes();check('member:'+p.name+':'+m['path'],len(b)==m['bytes'] and sha(b)==m['sha256'])
    custody.append(dict(path=str(p.relative_to(ROOT)),seal_sha256=expected,members=len(members)))
source=COMP/'overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs'
check('source-exact',len(source.read_bytes())==49980 and sha(source.read_bytes())=='04c5e5895586f5270c3d2bcaeaa1cfa451872d75b5b9260dbf3a1c9beb7d5876')
raw=gzip.decompress((IND/'entry-and-account.mir.gz').read_bytes()).decode()
check('exact19-MIR',sha(raw.encode())=='0b7a43a36357f67f98303a20b1a103a768125679330cc1201fe27c4dbbf2d945')
full=gzip.decompress((HELP/'whole-source146.mir.gz').read_bytes()).decode()
check('exact146-helper-MIR',len(full.encode())==76655228 and sha(full.encode())=='e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2')
names=['setup_files_once_v1','copy_claims_v1','run_prepaid_fixture_v1','invoke_loaded_leaf_once_v1']
functions={}
for name in names:
    m=re.search(r'^fn '+name+r'\(',raw,re.M);check('complete-source-function:'+name,m is not None)
    functions[name]=raw[m.start():raw.index('\n}\n',m.start())+3]
for method in ('default','clone'):
    candidates=[m for m in re.finditer(r'^fn [^\n]+',full,re.M) if '::'+method+'(' in m[0] and 'Cancellation' in m[0]]
    check('exact-one-Cancellation-helper:'+method,len(candidates)==1)
    m=candidates[0];functions['cancellation_'+method]=full[m.start():full.index('\n}\n',m.start())+3]
selected='\n\n'.join(functions.values())+'\n'
(D/'selected-six.mir.gz').write_bytes(gzip.compress(selected.encode(),mtime=0))
layout=json.loads((IND/'fresh-layout-results.json').read_text())
check('fresh90-layout-context',len(layout['queries'])==90 and layout['source_tree']=='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185')
native_sizes=layout['actual_type_sizes']

# Original source-visible type declarations are data from the frozen independent
# loader review. Added concrete child-result shapes are derived below from actual
# accepted146 source declarations, including nested error/retirement variants.
prior=V/'swift-guarded-snapshot-loader-work-independent/review'
prior_seal=json.loads((prior/'seal.json').read_text());entry=next(x for x in prior_seal['members'] if x['path']=='source-shapes.json')
check('frozen-prior-shapes',sha((prior/'source-shapes.json').read_bytes())==entry['sha256'])
old_shapes=json.loads((prior/'source-shapes.json').read_text())['structs']
structs={n:[(a,b) for a,b in row.get('fields',[])] for n,row in old_shapes.items() if 'fields' in row}
enums={};origin={}
control=COMP/'overlay/vm/src/experimental_swift_reactor/control.rs'
wasi=BASE/'src/experimental_wasi/mod.rs';diag=BASE/'src/experimental_swift_reactor/diagnostic_profile.rs';swift=BASE/'src/experimental/swift.rs'
registry={source:['ReviewedFixtureBindingV1','FrozenFixtureV1','SetupOutcomeV1','PrimaryOutcomeV1','OwnedFixtureOutcomeV1','UnverifiedProfileDigestBytesV1','UnverifiedProfileHeaderV1','ProfileHeaderErrorV1','SnapshotPrimaryRetirementV1','SnapshotAttemptV1','SnapshotObservationV1','SnapshotExportErrorV1','SnapshotCauseV1','SnapshotProgressV1'],control:['SwiftRunBudget','SwiftReservationUsage','SwiftReservations','SwiftLiveUsage','SwiftRunUsage','SwiftRunFailure','SwiftRunResource','SwiftReservationCategory','SwiftDeadlineOrigin','SwiftRunStage','SwiftRunFailureKind','SwiftCleanupInvariant','SnapshotPreScopeFailureV1','SnapshotScopeFinishV1','SnapshotWasiAttachmentV1','SnapshotStopV1','SnapshotAdmissionErrorV1'],wasi:['WasiUsage','WasiReservations','WasiFailure'],diag:['ProfileRowsObservationV1','ProfileAdapterErrorV1'],swift:['SnapshotEncodeErrorV2']}
def split(s,sep=','):
    depth=0;out=[];at=0
    for i,c in enumerate(s):
        if c in '<[({':depth+=1
        elif c in '>])}':depth-=1
        elif c==sep and depth==0:out.append(s[at:i].strip());at=i+1
    out.append(s[at:].strip());return [p for p in out if p]
def brace_end(s,start):
    level=0
    for i in range(start,len(s)):
        if s[i]=='{':level+=1
        elif s[i]=='}':
            level-=1
            if level==0:return i
    raise ValueError('unbalanced declaration')
def field_types(body):
    result=[]
    for field in split(body):
        field=re.sub(r'^pub(?:\([^)]*\))?\s+','',field.strip())
        m=re.match(r'([A-Za-z_][A-Za-z_0-9]*):\s*(.+)',field,re.S)
        check('field-declaration:'+field[:35],m is not None)
        result.append((m[1],m[2].strip()))
    return result
for path,requested in registry.items():
    text=re.sub(r'//[^\n]*','',path.read_text())
    for name in requested:
        m=re.search(r'\b(struct|enum)\s+'+name+r'\b[^\{;]*\{',text)
        check('actual-type-declaration:'+name,m is not None)
        body=text[m.end():brace_end(text,m.end()-1)]
        origin[name]=dict(path=str(path.relative_to(ROOT)),declaration_sha256=sha(text[m.start():brace_end(text,m.end()-1)+1].encode()))
        if m[1]=='struct':structs[name]=field_types(body)
        else:
            variants=[]
            for variant in split(body):
                if '{' in variant:payload=field_types(variant[variant.index('{')+1:variant.rindex('}')]);types=[t for _,t in payload]
                elif '(' in variant:types=split(variant[variant.index('(')+1:variant.rindex(')')])
                else:types=[]
                variants.append(dict(name=re.match(r'\w+',variant)[0],types=types))
            enums[name]=variants
atoms=set('bool char u8 u16 u32 u64 u128 usize i8 i16 i32 i64 i128 isize f32 f64 Type BlockKind Profile Resource FailureKind SwiftValidationFailureKind SwiftValidationResource WasiFunction ResolveError Role Refusal TryFromIntError TryReserveError Instant'.split())
opaque=set()
def leaves(t,stack=()):
    t=t.strip()
    if t.startswith(('&','*')):return 1
    if t in ('()','!'):return 1
    if t.startswith('(') and t.endswith(')'):return sum(leaves(x,stack) for x in split(t[1:-1]))
    if t.startswith('[') and t.endswith(']'):
        a,n=split(t[1:-1],';');return int(n)*leaves(a,stack)
    base=t.split('<',1)[0].rsplit('::',1)[-1];inner=t[t.index('<')+1:-1] if '<' in t and t.endswith('>') else ''
    if base=='SwiftMetadata':base='Metadata'
    if base=='Stop':base='SnapshotStopV1'
    if base=='AError':base='SnapshotAdmissionErrorV1'
    if base in ('Option','Result','ControlFlow'):return 1+max(leaves(v,stack) for v in split(inner))
    if base in ('Range','RangeInclusive'):return 2*leaves(inner,stack)+int(base=='RangeInclusive')
    if base=='Bytes':return int(inner)+1
    if base=='Policy':return 2
    if base in ('T','C','D'):return 6
    if base in atoms:return 1
    if base=='Cancellation':return 1 # actual source is one opaque Arc handle; backing separately observed
    if base in stack:raise ValueError('cyclic value shape:'+base)
    if base in structs:return sum(leaves(v,stack+(base,)) for _,v in structs[base])
    if base in enums:return 1+max((sum(leaves(v,stack+(base,)) for v in row['types']) for row in enums[base]),default=0)
    if t.startswith(('std::','io::','Vec<','Box<','Arc<')) or base in ('File','OpenOptions'):opaque.add(t);return 1
    raise ValueError('unknown product type:'+t)
shapes={n:dict(fields=fields,leaves=leaves(n),origin=origin.get(n,'frozen prior source shape')) for n,fields in structs.items() if n in origin}
shapes.update({n:dict(variants=variants,leaves=leaves(n),origin=origin[n]) for n,variants in enums.items()})
check('claims256',leaves('UnverifiedProfileDigestBytesV1')==256)
check('SwiftRunBudget17',leaves('SwiftRunBudget')==17)
def parse(body):
    head=body.splitlines()[0];locals_=dict(re.findall(r'^\s*let (?:mut )?(_\d+): (.+?);(?:\s*//|$)',body,re.M))
    sig=head[head.index('(')+1:]
    for m in re.finditer(r'(_\d+): ',sig):
        start=m.end();depth=0;i=start
        while i<len(sig):
            c=sig[i]
            if c in '<[(':depth+=1
            elif c in '>])':
                if not depth:break
                depth-=1
            elif c==',' and not depth:break
            i+=1
        locals_[m[1]]=sig[start:i]
    statements=[];block=False
    for line in body.splitlines():
        if re.match(r'    bb\d+(?: \(cleanup\))?: \{',line):block=True;continue
        if block and line=='    }':block=False;continue
        if block:
            code=line.split(' // ',1)[0].strip()
            if code:statements.append(code)
    return head,locals_,statements
def target(st):
    rhs=st.split(' = ',1)[1];depth=0
    for i,c in enumerate(rhs):
        if c=='<':depth+=1
        elif c=='>' and rhs[i-1:i]!='-':depth-=1
        elif c=='(' and not depth:return rhs[:i]
    raise ValueError('unknown call syntax')
ledger={};drop_sites=[];local_types={};native_layout_attribution=[]
for name,body in functions.items():
    head,locals_,statements=parse(body);params=set(re.findall(r'(_\d+):',head.split(' -> ',1)[0]))
    parts=dict(parameter_leaf_fetch_store=2*sum(leaves(locals_[p]) for p in params),local_leaf_fetch_store=0,primitive_control_projection=0)
    calls=[];transfers=[];local_types[name]=locals_
    for st in statements:
        if ' = ' not in st and not st.startswith(('StorageLive(','StorageDead(','goto ->','switchInt(','assert(','drop(','return;','unreachable;','resume;','terminate(')):raise ValueError('unsupported MIR statement:'+st)
        mentions=re.findall(r'\b_\d+\b',st)
        amount=2*sum(leaves(locals_[v]) for v in mentions)
        parts['local_leaf_fetch_store']+=amount
        parts['primitive_control_projection']+=2+sum(st.count(c) for c in '.*[]')
        if '*_' in st:transfers.append(dict(statement=st,source_leaf_mentions_paid=amount,locals={v:dict(type=locals_[v],leaves=leaves(locals_[v])) for v in mentions}))
        if ') -> [' in st and ' = ' in st:calls.append(dict(target=target(st)))
        if st.startswith('drop('):drop_sites.append(dict(function=name,statement=st,repeat=6 if name=='setup_files_once_v1' else 1))
    repeat=6 if name=='setup_files_once_v1' else 1
    ledger[name]=dict(head=head,mir_sha256=sha(body.encode()),local_count=len(locals_),local_types=locals_,statements=statements,parts=parts,local_actions=2+sum(parts.values()),repeat=repeat,calls=calls,dereference_statements=transfers)
    if name in names:
        for local,ty in locals_.items():
            if ty not in native_sizes:raise ValueError('missing actual90 layout:'+ty)
            native_layout_attribution.append(dict(function=name,local=local,type=ty,bytes=native_sizes[ty],source_leaves=leaves(ty)))
check('original-four188-roles',sum(ledger[n]['local_count'] for n in names)==188)
check('original-four76696-bytes',sum(v['bytes'] for v in native_layout_attribution)==76696)
# Actual aggregate reads through references are paid using their complete typed
# destinations; a pointer-base charge alone is never taken as pointee coverage.
copy_witnesses=[]
for name,row in ledger.items():
    for witness in row['dereference_statements']:
        st=witness['statement'];m=re.match(r'(_\d+) = copy ',st)
        if not m:continue
        destination=m[1];width=leaves(row['local_types'][destination])
        check('actual-dereference-Copy-value-covered:'+name+':'+destination,witness['source_leaf_mentions_paid']>=2*width)
        copy_witnesses.append(dict(function=name,statement=st,destination_type=row['local_types'][destination],pointee_value_transfer_leaves=2*width,all_applicable_mention_charge=witness['source_leaf_mentions_paid']))
check('twelve-deref-copy-values',len(copy_witnesses)==12)
resolved_calls={
 'setup_files_once_v1':{'<std::ops::Range<usize> as IntoIterator>::into_iter':'primitive','<std::ops::Range<usize> as Iterator>::next':'primitive','std::fs::File::open::<&Path>':'native_open_cut','OpenOptions::new':'primitive','OpenOptions::write':'primitive','OpenOptions::create_new':'primitive','OpenOptions::open::<&Path>':'native_open_cut'},
 'copy_claims_v1':{},
 'run_prepaid_fixture_v1':{'setup_files_once_v1':'setup_files_once_v1','<execute::Cancellation as Default>::default':'cancellation_default','load_selected_retained_profile_v1':'loader_payload_cut','copy_claims_v1':'copy_claims_v1','Instant::now':'primitive','<execute::Cancellation as Clone>::clone':'cancellation_clone','invoke_loaded_leaf_once_v1':'invoke_loaded_leaf_once_v1'},
 'invoke_loaded_leaf_once_v1':{'run_one_loaded_fixture_v1':'leaf_payload_cut'},
 'cancellation_default':{'<Arc<Atomic<bool>> as Default>::default':'primitive_with_observed_24B_allocation'},
 'cancellation_clone':{'<Arc<Atomic<bool>> as Clone>::clone':'primitive_no_new_allocation_observed'},
}
for name,row in ledger.items():
    for call in row['calls']:
        if call['target'] not in resolved_calls[name]:raise ValueError('unclassified callee:'+call['target'])
        call['role']=resolved_calls[name][call['target']]
def core(name,stack=()):
    if name in stack:raise ValueError('call cycle')
    row=ledger[name];value=row['local_actions']
    for call in row['calls']:
        if call['role'] in ledger:value+=core(call['role'],stack+(name,))
    return value*row['repeat']
setup=core('setup_files_once_v1');entry=core('run_prepaid_fixture_v1')
drop_count=sum(v['repeat'] for v in drop_sites)
probe=json.loads((D/'probe-receipt.json').read_text());ir=(D/'cancellation-backing-probe.ll').read_text();out=(D/'probe.stdout').read_text()
check('probe-succeeded-without-run',probe['exit_code']==0 and not probe['timed_out'] and not probe['product_or_probe_executed'])
check('ArcInner-observed24-align8','`alloc::sync::ArcInner<std::sync::atomic::Atomic<bool>>`: 24 bytes, alignment: 8 bytes' in out)
check('actual-default-layout-argument',bool(re.search(r'box_new_uninit[^\n]*\(i64 8, i64 24\)',ir)))
check('default-allocator-unzeroed-branch','__rust_alloc(i64 %layout.1, i64 %layout.0)' in ir)
put('source-shapes.json',dict(source_tree='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',new_shapes=shapes,all_opaque_standard_types=sorted(opaque),prior_source_shape_seal_sha256='28d14ca65eed39ac22b01f562ccc74178f3ee361c2c0a73d16e0da9b122f4be5'))
put('ledger.json',dict(schema=1,functions=ledger,core_root='run_prepaid_fixture_v1',setup_source_work=setup,complete_four_plus_helpers_source_work=entry,remaining_caller_and_argument_source_work=entry-setup,drop_sites=drop_sites,during_entry_drop_visit_bound=drop_count,dereference_Copy_coverage=copy_witnesses,actual_native_layouts_as_data=native_layout_attribution,original_role_inventory_bytes=76696,original_role_inventory_count=188,inventory_is_not_work=True,requested_Cancellation_allocation_bytes=24,requested_Cancellation_allocation_alignment=8,clone_additional_allocation_bytes=0,scope='producer candidate only; mandatory nonzero path/native/error/destructor/payload cuts remain unselected; no full component or host acceptance'))
put('bindings.json',dict(source_tree='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',source_members=146,host_members=11,custody=custody,selected_MIR_sha256=sha(selected.encode()),selected_gzip_sha256=sha((D/'selected-six.mir.gz').read_bytes()),entry_and_account_MIR_sha256=sha(raw.encode()),helper_whole_MIR_sha256=sha(full.encode()),probe_receipt_sha256=sha((D/'probe-receipt.json').read_bytes()),prepare_checks=len(checks),python=sys.version,compiler_invocations_in_prepare=0,product_execution=False))
print(json.dumps(dict(prepare_checks=len(checks),source_work_core=entry,setup_source_work=setup,drop_visits=drop_count,helper_default_work=core('cancellation_default'),helper_clone_work=core('cancellation_clone'),candidate_complete=False)))
