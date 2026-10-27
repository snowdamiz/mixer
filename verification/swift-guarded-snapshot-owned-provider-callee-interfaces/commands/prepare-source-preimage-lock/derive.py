#!/usr/bin/env python3
"""Deterministic host-only typed source accounting and retained LLVM binding."""
from pathlib import Path
import collections, gzip, hashlib, importlib.util, json, re, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V=ROOT/'verification'
BASE=V/'swift-guarded-snapshot-owned-provider-work-storage'
TREE='acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
RUST='b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
COMPILER='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
ACCEPTANCE='64f53d4ee70bb98b7684bc3dcf1f53b5e5b86c34c1a82a2930d362cdcc9d647a'
ROOT_ACCEPTANCES=['guarded-snapshot-owned-provider-work-storage-host-acceptance.json','guarded-snapshot-remaining-work-host-acceptance.json','guarded-snapshot-remaining-work-contract-amendment.json','guarded-snapshot-resource-cost-host-acceptance.json','guarded-snapshot-resource-binary-host-acceptance.json','guarded-snapshot-native-interface-host-acceptance.json','guarded-snapshot-native-open-binary-host-acceptance.json']
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def need(ok,label):
    if not ok:raise ValueError(label)
def row(p):
    b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)}
def load(p):return json.loads(p.read_bytes())
def module(p,name):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
ledger=module(HERE/'ledger.py','provider_callee_ledger')
def source_path(s):return HERE/s if s.startswith('official-source/') else ROOT/s
def input_roster():
    paths=set(); seals=[]
    def packet(p,expected):
        sp=p/'seal.json';b=sp.read_bytes();need(sha(b)==expected,'accepted seal:'+str(p));x=json.loads(b)
        actual={str(f.relative_to(p)) for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
        members={m['path'] for m in x['members']}
        need(actual==members|{'seal.json'},'complete packet membership:'+str(p))
        paths.add(sp)
        for m in x['members']:
            q=p/m['path'];a=row(q);need(all(a[k]==m[k] for k in ('bytes','sha256')),'sealed member:'+str(q));paths.add(q)
        seals.append({'path':str(p.relative_to(ROOT)),'seal_sha256':sha(b),'members':len(x['members']),'bytes':sum(r['bytes'] for r in x['members'])})
    for name in ROOT_ACCEPTANCES:
        p=V/'swift-semantic-adapter-root-review'/name;paths.add(p);x=load(p)
        if name==ROOT_ACCEPTANCES[0]:need(sha(p.read_bytes())==ACCEPTANCE,'exact new source-work root acceptance')
        for item in ([x[k] for k in ('producer','independent') if k in x]+x.get('custody',[])):
            if item['path'].startswith('verification/') and 'seal_sha256' in item:packet(ROOT/item['path'],item['seal_sha256'])
    # Complete source146 byte membership, never the live canonical tree.
    p=V/'swift-guarded-snapshot-owned-binding-provider/proposed-source-custody.json';paths.add(p)
    source=[]
    for item in load(p):
        q=ROOT/item['origin'];a=row(q);need(all(a[k]==item[k] for k in ('bytes','sha256')),'source146 member');paths.add(q);source.append({k:item[k] for k in ('path','bytes','sha256')})
    need(len(source)==146 and sha(canon(source))==TREE,'exact source146 tree')
    # The earlier accepted native aggregate query resolves (usize,bool) directly.
    p=V/'swift-guarded-snapshot-source146-callee-storage-layouts';b=(p/'seal.json').read_bytes();packet(p,sha(b))
    # Root caller costs, immutable backing/storage obligations and inherited phases.
    for name in ['swift-guarded-snapshot-outer-parent-work-storage','swift-guarded-snapshot-host-storage-composition']:
        p=V/name;packet(p,sha((p/'seal.json').read_bytes()))
    for f in ['AGENTS.md','PLAN.md','mixer-product-plan.md']:paths.add(ROOT/f)
    genuine=V/'swift-real-profile-loader-binding/source-preimages/genuine.wasm'
    need(len(genuine.read_bytes())==1947 and sha(genuine.read_bytes())=='9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806','inherited selected source preimage')
    paths.add(genuine)
    # Exact source retrieval membership and compiler/source revision relation.
    p=HERE/'official-source-custody.json';paths.add(p);fetch=load(p);need(fetch['revision']==RUST,'exact official revision')
    need(len(fetch['members'])==22 and all(x['success'] for x in fetch['members']),'complete22 exact-source retrieval')
    for x in fetch['members']:
        q=HERE/'official-source'/x['path'];a=row(q);need(a['bytes']==x['bytes'] and a['sha256']==x['sha256'],'official source member');paths.add(q)
    return {'schema':1,'source_tree_sha256':TREE,'rust_revision':RUST,'frozen_packets':sorted({x['path']:x for x in seals}.values(),key=lambda x:x['path']),'files':[row(p) for p in sorted(paths)]}
def llvm_functions(text):
    lines=text.splitlines();out={}
    for i,line in enumerate(lines):
        if not line.startswith('define '):continue
        name='';j=i-1
        while j>=0 and lines[j].startswith(';'):
            if not lines[j].startswith('; Function Attrs'):name=lines[j][2:]
            j-=1
        end=i+1
        while end<len(lines) and lines[end]!='}':end+=1
        need(end<len(lines),'complete LLVM function')
        symbol=re.search(r'@([^ (]+)',line)[1]
        out[symbol]={'symbol':symbol,'name':name,'header':line,'text':'\n'.join(lines[i:end+1])}
    need(len(out)==len(re.findall(r'^define ',text,re.M)) and bool(out),'complete retained LLVM definition partition')
    return out
def active_cfg(function):
    body=function['text'];blocks={};current=None
    for line in body.splitlines()[1:-1]:
        if re.match(r'^[A-Za-z0-9_.]+:',line):current=line.split(':',1)[0];blocks[current]=[]
        elif current and line.strip() and not line.startswith(';'):blocks[current].append(line.strip())
    need('start' in blocks,'LLVM entry')
    edges={k:re.findall(r'label %([A-Za-z0-9_.]+)', ' '.join(v)) for k,v in blocks.items()}
    seen=set();queue=['start']
    for b in queue:
        if b in seen:continue
        seen.add(b);need(b in blocks,'closed LLVM successor');queue.extend(edges[b])
    active='\n'.join(line for k,v in blocks.items() if k in seen for line in v)
    return {'blocks':blocks,'edges':edges,'reachable':sorted(seen),'unreachable':sorted(set(blocks)-seen),'active':active,'calls':re.findall(r'\b(?:call|invoke)\b[^\n@]*@([^ (]+)',active)}
def poly(f=0,b=0,q=0):return {'fixed':f,'B':b,'B2':q}
def plus(*xs):return {k:sum(x[k] for x in xs) for k in ('fixed','B','B2')}
def times(x,n):return {k:x[k]*n for k in x}
def body_plus_one(x):
    need(x['B2']==0,'higher than declared quadratic source envelope');return poly(x['fixed'],x['B']+x['fixed'],x['B'])
def val(x,b):return x['fixed']+x['B']*b+x['B2']*b*b
def type_table():
    obs=load(BASE/'layouts.json')['named_observations'];sizes={x['name']:(x['size'],x['align']) for x in obs}
    out={}
    def t(name,size,align,leaves,evidence,body=False,pointee=None):out[name]={'bytes':size,'align':align,'leaves':leaves,'evidence':evidence,'pointee':pointee,'body':body}
    for name,size,align in [('usize',8,8),('isize',8,8),('u8',1,1),('i32',4,4),('bool',1,1),('()',0,1)]:t(name,size,align,1,'exact aarch64 target scalar primitive; inherited provider/native scalar dimensions')
    mapping={'Range<usize>':('range',2),'Option<usize>':('option_usize',2),'Result<usize,CandidateShapeRefusalV1>':('result_usize',3),'Residual':('residual',3),'ControlFlow<Residual,usize>':('control_flow',4),'&mut Range<usize>':('range_ref',1),'&[u8]':('slice_ref',1),'&Path':('path_ref',1),'&OsStr':('osstr_ref',1),'&&[u8]':('slice_header_ref',1),'&u8':('byte_ref',1),'&[u8;32]':('digest_ref',1)}
    for name,(key,leaves) in mapping.items():t(name,*sizes[key],leaves,'exact retained production named size/alignment query:'+key,body=name in ('&[u8]','&Path','&OsStr'),pointee={'&mut Range<usize>':(16,2),'&&[u8]':(16,1),'&u8':(1,1),'&[u8;32]':(32,32)}.get(name))
    stdout=(BASE/'commands/capture-layout/stdout').read_text()
    expected=[('CandidateShapeRefusalV1',16,8,2),('CandidateResult',1352,8,714)]
    for name,size,align,leaves in expected:
        exact='experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::outer_parent_v1::existing_owner_candidate_v1::CandidateShapeRefusalV1' if name=='CandidateShapeRefusalV1' else 'std::result::Result<experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::outer_parent_v1::existing_owner_candidate_v1::UnqualifiedExistingOwnerCandidateV1<\'_>, experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::outer_parent_v1::existing_owner_candidate_v1::CandidateShapeRefusalV1>'
        need('print-type-size type: `'+exact+'`: '+str(size)+' bytes, alignment: '+str(align)+' bytes' in stdout,'exact production aggregate extent:'+name)
        t(name,size,align,leaves,'exact fully-qualified print-type-size aggregate observation; provider accepted source-shape leaves')
    closure=load(BASE/'layouts.json')['anonymous_capture'];need((closure['bytes'],closure['alignment'])==(16,8),'actual closure extent')
    t('ProductionClosure',16,8,2,'exact production span1185:27 actual aggregate16/8 and capture types; no field sum')
    tup=load(V/'swift-guarded-snapshot-source146-callee-storage-layouts/results.json')
    matches=[r for r in tup['queries'] if r.get('key')=='(usize, bool)']
    need(len(matches)==1 and matches[0]['size']==16 and matches[0]['alignment']==8 and tup['compiler_sha256']==COMPILER and tup['target']=='aarch64-apple-darwin','exact earlier tuple aggregate query')
    t('(usize, bool)',16,8,2,'exact retained same-compiler/target source146 query, full aggregate16/8')
    # Guaranteed transparent/reference-to-raw coercion representations, not field-size sums.
    # Private Unix Slice is repr(transparent) [u8] at this exact source revision.
    os=(V/'swift-guarded-snapshot-native-interface-bounds/official-source/library/std/src/ffi/os_str.rs').read_text()
    bs=(V/'swift-guarded-snapshot-native-interface-bounds/official-source/library/std/src/sys/os_str/bytes.rs').read_text()
    need('#[repr(transparent)]\npub struct Slice {\n    pub inner: [u8],\n}' in bs and '#[repr(transparent)]\npub struct OsStr {\n    inner: Slice,\n}' in os,'exact transparent private view')
    t('&UnixOsSlice',*sizes['osstr_ref'],1,'exact transparent OsStr→Slice→[u8] source projection and as_bytes LLVM ABI; inherited &OsStr observation',body=True)
    t('*const [u8]',*sizes['slice_ref'],1,'exact reference-to-raw pointer coercion representation of observed &[u8], ptr_metadata intrinsic; not arbitrary pointer/catalog pricing',body=True)
    t('*const u8',*sizes['byte_ref'],1,'exact &u8→*const u8 coercion representation, selected slice::as_ptr source and LLVM pointer operand',body=True)
    return out
def typed_role(role,types):
    need(set(role)=={'id','type','kind'} and role['type'] in types,'known exact typed source place')
    t=types[role['type']];p=poly(b=1) if t['body'] else poly(t['pointee'][0]) if t['pointee'] else poly();s=poly(b=1) if t['body'] else poly(t['pointee'][1]) if t['pointee'] else poly()
    return role|t|{'pointee_bytes':p,'pointee_leaves':s,'source_ledger_place_not_compiler_MIR':True}
def operation(code,by):
    mentions=re.findall(r'\b_\d+\b',code);need(all(x in by for x in mentions),'unbound source typed operand')
    constants=[]
    for m in re.finditer(r'(?<!\*)\bconst\s+',code):
        match=re.match(r'(\d+)_(usize|isize|u8|i32)|true\b|false\b|\(\)',code[m.end():]);need(match is not None,'unknown source constant')
        text=match[0];width=0 if text=='()' else 1 if text in ('true','false') or text.endswith('_u8') else 4 if text.endswith('_i32') else 8
        constants.append({'text':text,'bytes':width,'leaves':1})
    base=2+sum(code.count(c) for c in '()[].*&')+len(re.findall(r'\bas\b',code))
    source=poly(base+2*sum(by[n]['leaves'] for n in mentions)+2*len(constants))
    native=poly(2*sum(by[n]['bytes'] for n in mentions)+2*sum(c['bytes'] for c in constants))
    source=plus(source,*[times(by[n]['pointee_leaves'],2) for n in mentions]);native=plus(native,*[times(by[n]['pointee_bytes'],2) for n in mentions])
    if code=='return;':
        source=plus(source,poly(2*by['_0']['leaves']),times(by['_0']['pointee_leaves'],2));native=plus(native,poly(2*by['_0']['bytes']),times(by['_0']['pointee_bytes'],2))
    return {'code':code,'mentions':mentions,'constants':constants,'source_action_units':source,'native_typed_bytes':native,'combined':plus(source,native)}
def validate_ledger(nodes,types):
    need(type(nodes)is list and len(nodes)==len(ledger.nodes()),'complete source-node roster')
    expected={x['id']:x for x in ledger.nodes()};seen=set()
    for n in nodes:
        need(n['id'] in expected and n['id'] not in seen,'unknown or duplicated callee');seen.add(n['id'])
        need(n==expected[n['id']],'exact reviewed target/type/arity/source/row/callback contract')
        need(len({r['id'] for r in n['roles']})==len(n['roles']),'unique source roles')
        by={r['id']:typed_role(r,types) for r in n['roles']}
        for r in n['rows']:
            need(n['first']<=r['line']<=n['last'] and type(r['body_iterations'])is bool,'exact source line or iteration')
            operation(r['code'],by)
    return True
def derive():
    lock=input_roster();need(load(HERE/'input-lock.json')==lock,'full exact frozen input membership')
    candidate=load(BASE/'candidate.json');calls=load(BASE/'required-input-contracts.json');counts={x['name']:x['count'] for x in calls['std_interfaces']}
    need(counts==ledger.COUNTS==candidate['new_required_std_interface_terms'],'exact14 accepted call caps')
    plan=load(BASE/'compiler-plan.json');need(plan['compiler_sha256']==COMPILER and RUST in plan['compiler_version_preimage'] and plan['candidate_tree_sha256']==TREE,'compiler revision/target binding')
    need(candidate['provider_source_work']=={'fixed':276580,'input_operand_bytes':1324} and candidate['provider_inline_addition']==9696 and candidate['conditional_P0_fixed']==301733,'provider terms intact')
    raw=gzip.decompress((BASE/'commands/capture-layout/query.ll.gz').read_bytes());fs=llvm_functions(raw.decode());names=collections.defaultdict(list)
    for sym,f in fs.items():names[f['name']].append(sym)
    types=type_table();ns=ledger.nodes();validate_ledger(ns,types);source=[];priced={};llvm=[]
    for n in ns:
        data=source_path(n['source']).read_bytes();lines=data.decode().splitlines();segment='\n'.join(lines[n['first']-1:n['last']])+'\n'
        roles=[typed_role(r,types) for r in n['roles']];by={r['id']:r for r in roles};rows=[]
        for r in n['rows']:
            p=operation(r['code'],by);p.update(r);p['source_text']=lines[r['line']-1]
            if r['body_iterations']:p['combined_weighted']=body_plus_one(p['combined'])
            else:p['combined_weighted']=p['combined']
            rows.append(p)
        params=[r for r in roles if r['kind']=='parameter']
        entry=plus(poly(2+2*sum(r['leaves']+r['bytes'] for r in params)),*[times(plus(r['pointee_bytes'],r['pointee_leaves']),2) for r in params])
        end=poly(sum(2+2*r['leaves']+2*r['bytes'] for r in roles))
        own=plus(entry,end,*[r['combined_weighted'] for r in rows])
        item=n|{'source_sha256':sha(data),'source_segment':segment,'source_segment_sha256':sha(segment.encode()),'roles':roles,'rows':rows,'entry':entry,'finite_role_end':end,'own_work':own,'logical_source_places_bytes':sum(r['bytes'] for r in roles)}
        source.append(item);priced[n['id']]=item
        if n['llvm_name']:
            found=names[n['llvm_name']];need(len(found)==1,'one exact retained LLVM specialization:'+n['id']);f=fs[found[0]];cfg=active_cfg(f)
            llvm.append({'node':n['id'],'name':f['name'],'symbol':f['symbol'],'header':f['header'],'sha256':sha(f['text'].encode()),'bytes':len(f['text'].encode()),'calls':cfg['calls'],'reachable':cfg['reachable'],'unreachable':cfg['unreachable'],'edges':cfg['edges'],'body':f['text']})
    lm={x['node']:x for x in llvm}
    need('i64 32' in lm['array_spec_ne32']['body'] and '@memcmp' in lm['array_spec_ne32']['body'],'exact digest32 external target')
    need('@memcmp' in lm['bytewise_eq']['body'] and 'i64 %len' in lm['bytewise_eq']['body'],'exact variable-length external comparison')
    contains=active_cfg(fs[lm['u8_contains_shell']['symbol']]);need(not any('Iterator3any' in x for x in contains['calls']),'u8 unreachable generic callback not selected')
    need(any('memchr6memchr' in x for x in contains['calls']) and {'bb3','bb15','bb16','bb7'}<=set(contains['unreachable']),'exact constant-selected byte branch')
    mem=lm['memchr_shell'];need(ledger.FRONTIERS['CONTAINS_RESIDUAL_FRONTIER']['native_target'] in mem['body'] and ledger.FRONTIERS['CONTAINS_RESIDUAL_FRONTIER']['native_target'] not in fs,'true missing installed memchr_aligned body')
    need('icmp ult i64 %text.1, 16' in mem['body'] and 'add i64 %17, 1' in mem['body'],'exact short-loop threshold/increment')
    andthen=lm['option_and_then_excluding_authored_callback'];ac=active_cfg(fs[andthen['symbol']])['calls'];need(len(ac)==1 and fs[ac[0]]['name']==ledger.CALLBACK,'exact direct authored callback, no hidden FnOnce wrapper')
    for key in ('option_ok_or_shape_refusal','result_try_branch','candidate_result_from_residual'):
        need(not lm[key]['calls'],'Copy enum/reflexive conversion has no unknown active call/drop')
    # Full retained IR gets exact active ABI operands, independent from source prices.
    # These are typed native interface fields, not instruction counts or Rust sizeof guesses.
    abi=[]
    for x in llvm:
        header=x['header'];argtext=header.split('(',1)[1].rsplit(')',1)[0]
        native=0;formals=[]
        for token in re.split(r', (?=(?:ptr|i\d+)\b)',argtext):
            if not token.strip():continue
            m=re.match(r'(ptr|i\d+)\b',token);need(m is not None,'closed selected LLVM ABI formal')
            width=8 if m[1]=='ptr' else (int(m[1][1:])+7)//8
            pointee=re.search(r'sret\(\[(\d+) x i8\]\)',token);payload=int(pointee[1]) if pointee else 0
            formals.append({'formal':token,'native_field_bytes':width,'sret_logical_result_payload_bytes':payload});native+=width+payload
        ret=header.split('@',1)[0]
        if ' void ' in ret:result=0
        else:
            bits=re.findall(r'\bi(\d+)\b',ret);result=sum((int(z)+7)//8 for z in bits)
            if re.search(r'\bptr\b',ret):result+=8
        # Entry and exit/forwarding each occurrence, just as source typed native allowances.
        supplement=2*(native+result)
        abi.append({'node':x['node'],'symbol':x['symbol'],'header':header,'formals':formals,'result_native_field_bytes':result,'logical_native_boundary_supplement':supplement,'additional_reserved_native_interface_fields':native+result,'not_Rust_aggregate_size_or_instruction_price':True})
        priced[x['node']]['own_work']=plus(priced[x['node']]['own_work'],poly(supplement))
    def compose(name,stack=()):
        need(name not in stack and name in priced,'closed acyclic source helper graph')
        n=priced[name];work=n['own_work'];front=collections.Counter();closure=0;visits=collections.Counter({name:1})
        for edge in n['calls']:
            child=edge['node'];count=edge['count']
            if child=='AUTHORED_CALLBACK':closure+=count;continue
            if child in ledger.FRONTIERS:front[child]+=count;continue
            w,f,c,v=compose(child,stack+(name,))
            if count=='body+1':
                need(not f and not c,'dynamic unknown/helper callback requires explicit bound');work=plus(work,body_plus_one(w));visits.update({k:('body+1' if value==1 else 'unsupported') for k,value in []})
                # Source places are one set, retained across the loop; work multiplies.
                visits.update(v)
            else:work=plus(work,times(w,count));front.update({k:v*count for k,v in f.items()});closure+=c*count;visits.update({k:v*count for k,v in v.items()})
        return work,front,closure,visits
    interfaces=[];whole=poly();all_visits=collections.Counter();source_slots=0;abi_slots=0
    for name,count in sorted(counts.items()):
        work,front,callback,visits=compose(name)
        need(front==(collections.Counter({ledger.PARTIAL[name]:1}) if name in ledger.PARTIAL else collections.Counter()),'only exact positive partial frontiers')
        need(callback==(1 if name=='option_and_then_excluding_authored_callback' else 0),'authored callback conservation')
        # One set per source helper context per conservative invocation, including all
        # mutually exclusive branches. This deliberately exceeds shared-source storage.
        slots=sum(priced[k]['logical_source_places_bytes']*v for k,v in visits.items())*count
        abis=sum(next((a['additional_reserved_native_interface_fields'] for a in abi if a['node']==k),0)*v for k,v in visits.items())*count
        source_slots+=slots;abi_slots+=abis;weighted=times(work,count);whole=plus(whole,weighted);all_visits.update({k:v*count for k,v in visits.items()})
        interfaces.append({'name':name,'call_cap':count,'status':'partial-shell-strict-positive-residual-required' if front else 'closed-conditional-logical-interface','per_call_source_and_native_shell':work,'per_request_shell':weighted,'source_helpers':dict(sorted(visits.items())),'positive_residuals_per_call':dict(front),'authored_callback_body_inherited_per_call':callback,'callback_body_added_again':False,'reserved_distinct_source_places':slots,'reserved_distinct_native_ABI_fields':abis,'result_return_and_finite_end_charged':True})
    phases=load(BASE/'phase-roster.json')['P0_new_total_each_phase'];need(len(phases)==15 and set(phases.values())=={9696},'all15 accepted phases9696')
    oldmap=load(BASE/'source-typed-MIR-map.json');callback=next(x for x in oldmap['functions'] if x['header'].startswith('fn describe_existing_owner_candidate_v1::{closure#0}'))
    need(callback['per_request_invocation_cap']==5,'base authored callback5')
    proposal={'schema':1,'status':'separate-proposed-source-ledger-amendment-needs-independent-review-and-root-price-selection','source_tree_sha256':TREE,'target':'aarch64-apple-darwin','compiler_sha256':COMPILER,'rust_revision':RUST,'unit':'Inherited logical source/typed aggregate/finite-end occurrences plus native typed-byte allowances; source-ledger places are not compiler MIR places; LLVM is specialization correspondence only.','counts':counts,'closed_interfaces':[x['name'] for x in interfaces if not x['positive_residuals_per_call']],'partial_interfaces':ledger.PARTIAL,'interfaces':interfaces,'callee_source_shell_work':whole,'provider_source_work_unchanged':candidate['provider_source_work'],'provider_slots_unchanged':9696,'prior_conditional_P0_fixed_unchanged':301733,'additional_source_ledger_slots':source_slots,'additional_native_ABI_field_reservations':abi_slots,'additional_total_slots':source_slots+abi_slots,'proposed_conditional_P0_fixed_excluding_positive_residual_storage':301733+source_slots+abi_slots,'prior_conditional_whole_fixed':candidate['conditional_whole_fixed_excluding_dynamic_operands_and_new_std_or_upstream_terms'],'proposed_conditional_whole_fixed_excluding_all_dynamic_and_external_terms':candidate['conditional_whole_fixed_excluding_dynamic_operands_and_new_std_or_upstream_terms']+whole['fixed'],'proposed_dynamic_work':{'B':1324+whole['B'],'B2':whole['B2']},'B':'max all12 actual identity preimage lengths plus5 actual native path lengths plus5 actual separately retained path lengths, exactly inherited provider B; no selected maximum','positive_residual_contracts':ledger.FRONTIERS,'positive_residual_storage_required':True,'all10_inherited_terms':candidate['inherited_residual_work_terms'],'upstream2_work_terms':candidate['new_required_upstream_work_terms'],'all_six_upstream':'Pending','all_three_selectors':'Pending','authored_callback_body_work_inherited':callback['work_per_request'],'authored_callback_body_cap_inherited':5,'authored_callback_adapter_calls':5,'authored_callback_body_new_charge':0,'authored_callback_not_free':'Its full source body and roles remain in provider276580+1324B and9696; zero NEW body charge avoids duplicating an already mandatory charge. Adapter entry/operands/return/end/ABI fields are charged.','preserved':['all6006 prior MIR constructs including1785 standalone constants','all15 phases','original binding1168','all12 full preimage +5 native +5 separate retained backing','future root inline/backing and immutable diagnostics','all6 original child components','original payload/carrier/destructor/error/native operand obligations','no alias/move/refund credit; None/refusal/unwind retain full reservation'],'CPU_private_implementation_or_physical_stack_bound':False,'actual_acquisition_authenticated_owner_funding_or_operational_grant':False,'compiler_invocations':0,'runtime_native_FieldLog_OTA_GA':False,'fresh_independent_review_required':True}
    analyses={'schema':1,'digests':'Exact array32 uses BytewiseEq specialization → raw_eq → external memcmp32. Generic array/slice equality loops are not selected.','slice_equality':'Reference ne→slice default ne→slice eq checks lengths→BytewiseEq<u8>::equal_same_length→compare_bytes→external memcmp. No selected element loop or vector loop; 5 residual reservations kept across unequal lengths/refusal/unwind.','contains':'u8 size1 constant branch excludes Iter::any blocksbb3/bb15/bb16 and non-u8 vector macro. Active branch transmute_copy/from_raw_parts→memchr; n<16 uses monotone naive scan, n>=16 calls missing installed memchr_aligned. All precondition helpers/assert_unchecked and missing aligned work/slots remain in positive composite residual.','short_loop':'i starts0, guard i<n, increment1, early Some; every ledger loop row uses B+1 and byte-body allowances use B. Both n actual and B are input-derived; resulting conservative B² term is explicit. No arbitrary selected maximum or syscall/CPU bound.','aligned_source':'Exact official source53..109 reads two usize words per body iteration with initial alignment and final naive tail. This source is retained for scope, but its installed runtime body/correspondence remains missing and its work is not selected.','normal_refusal_unwind':'Both result branches and every finite source place/end are reserved. No panic path is called healthy refusal; any native/private panic/unwinder implementation remains outside logical unit and is never assigned zero. No result shape authenticates backing or funding.','compile_runtime_pause':'No compiler, product executable, Rust tests, phone/simulator/emulator, UI/capture or global process inventory executed.'}
    return {'proposal.json':proposal,'source-ledger.json':{'schema':1,'nodes':source,'types':types},'native-ABI-boundaries.json':{'schema':1,'rows':abi},'LLVM-correspondence.json':{'schema':1,'functions':llvm,'artifact':row(BASE/'commands/capture-layout/query.ll.gz'),'compiler_plan_sha256':sha((BASE/'compiler-plan.json').read_bytes())},'phase-reservations.json':{'schema':1,'phases':{k:{'provider_9696_retained':9696,'new_source_ledger_places':source_slots,'new_native_ABI_fields':abi_slots,'new_total':source_slots+abi_slots,'positive_external_residual_storage':'mandatory, exact11 invocation contexts, no default or refund'} for k in phases},'no_alias_move_or_refund_credit':True},'analysis.json':analyses,'input-custody.json':lock}
def main():
    if sys.argv[1:]==['--extend-input-lock']:
        old=load(HERE/'input-lock.json');new=input_roster();old_by={x['path']:x for x in old['files']};new_by={x['path']:x for x in new['files']}
        need(set(old_by)<set(new_by) and all(new_by[k]==v for k,v in old_by.items()),'only explicit input addition; no old custody rewrite')
        saved=HERE/'attempts/input-lock-initial.json';saved.parent.mkdir(exist_ok=True);need(not saved.exists(),'initial membership retained once');saved.write_bytes((HERE/'input-lock.json').read_bytes());(HERE/'input-lock.json').write_text(json.dumps(new,sort_keys=True,indent=2)+'\n');print(json.dumps({'preparation_input_additions':sorted(set(new_by)-set(old_by))}));return
    if sys.argv[1:]==['--prepare']:
        need(not (HERE/'input-lock.json').exists(),'one-time locked input manifest');x=input_roster();(HERE/'input-lock.json').write_text(json.dumps(x,sort_keys=True,indent=2)+'\n');print(json.dumps({'locked_input_members':len(x['files']),'frozen_packets':len(x['frozen_packets'])}));return
    result=derive()
    if sys.argv[1:]==['--check']:
        for name,value in result.items():need(load(HERE/name)==value,'stale derived artifact:'+name)
    else:
        need(not (HERE/'seal.json').exists(),'immutable sealed packet')
        for name,value in result.items():(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    p=result['proposal.json'];print(json.dumps({k:p[k] for k in ('closed_interfaces','partial_interfaces','callee_source_shell_work','additional_total_slots','proposed_conditional_P0_fixed_excluding_positive_residual_storage')}))
if __name__=='__main__':main()
