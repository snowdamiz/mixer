#!/usr/bin/env python3
"""Adversarial tests of the frozen arithmetic API, never input qualification.

Only model.py is imported as the system under test. Arithmetic expectations,
storage formulas, source/MIR binding and route checks are reviewer-authored.
"""
import dataclasses as DC
import importlib.util
import itertools
import json
import random
import re
import sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
C=ROOT/'verification/swift-guarded-snapshot-outer-parent-work-storage'
spec=importlib.util.spec_from_file_location('frozen_candidate_under_test',C/'model.py')
M=importlib.util.module_from_spec(spec);sys.modules[spec.name]=M;spec.loader.exec_module(M)
import review as R
cases=[]
H='7'*64
def check(name, condition):
    if not condition:raise AssertionError(name)
    cases.append(dict(name=name,result='pass'))
def rejects(name, action, exception=ValueError):
    try:action()
    except exception as error:cases.append(dict(name=name,result='rejected-as-required',reason=str(error)))
    else:raise AssertionError('accepted adverse case: '+name)
def B(n,unit='bytes'):return M.Bound(n,'synthetic arithmetic obligation only',M.TREE,H,unit)
def replace_at(values,index,**changes):
    a=list(values);a[index]=DC.replace(a[index],**changes);return tuple(a)
def synthetic(rng):
    source=(ROOT/'verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm').read_bytes()
    identities=[]
    for name in M.IDENTITIES:
        body=source if name=='source' else bytes(rng.randrange(256) for _ in range(rng.randrange(1,96)))
        identities.append(M.Identity(name,body,M.digest(body),B(len(body)+rng.randrange(19))))
    paths=[]
    for i in range(5):
        body=b'/review-synthetic/'+bytes([65+i])*rng.randrange(1,19)
        paths.append(M.PathInput(body,body,B(len(body)+rng.randrange(19)),B(len(body)+rng.randrange(19)),B(len(body)+1+rng.randrange(19)),H))
    budget={name:rng.randrange(1,1000) for name in M.BUDGET_FIELDS}
    budget.update(execution_work=1000000000,combined_bytes=268435456)
    return M.BindingInput(M.TREE,tuple(identities),tuple(paths),tuple(bytes([i])*32 for i in range(8)),budget,H,
                          B(rng.randrange(1,999)),B(rng.randrange(1,999)),B(rng.randrange(1,999)),
                          B(8572+rng.randrange(99)),B(4097+rng.randrange(99)),B(73+rng.randrange(99)),
                          B(32+rng.randrange(99)),B(396924+rng.randrange(99),'count'),B(29394+rng.randrange(99)))
def oracle(v):
    geometry={x.name:len(x.preimage) for x in v.identities}
    immutable=sum(x.backing.value for x in v.identities)+sum(x.byte_preimage_backing.value for x in v.paths)+v.immutable_diagnostic_backing.value
    p0=292037+v.future_root_inline.value+v.future_root_owned_backing.value+immutable+sum(x.native_backing.value for x in v.paths)
    parts=dict(P1_setup=59695+561+6*v.file_resource_backing_each.value+sum(x.open_temporary.value for x in v.paths),
       P1_loader=644008+geometry['build']+geometry['session']+max(geometry['executable'],1947+1947+1000000+65536)+v.loader_native_temporaries.value+v.executable_open_temporary.value,
       P2_arguments=544,P3_shell=224916,P4_leaf=15920+95850+1899541+54976,
       P5_returned=v.error_owner_count.value*v.error_backing_each.value+v.all_payload_destructor_temporaries.value)
    return p0,parts,sum(parts.values())

def arithmetic():
    for bad in (True,False,-1,1.0,'1',None,2**64):rejects('not u64 '+repr(bad),lambda bad=bad:M.natural(bad))
    for f,args in [(M.add,(M.U64,1)),(M.mul,(M.U64,2))]:rejects('checked overflow '+f.__name__,lambda f=f,args=args:f(*args))
    check('u64 inclusive endpoint',M.add(M.U64,0)==M.U64 and M.mul(M.U64,1)==M.U64)
    for unit in ['bytes','work','count']:
        for bad in [0,True,False,-1,2**64,1.5]:rejects(f'{unit} bad positive {bad!r}',lambda bad=bad,unit=unit:B(bad,unit).checked(unit=unit))
    for change in [dict(source_tree=M.OLD_TREE),dict(obligation=''),dict(obligation=' '),dict(evidence_sha256='a'*63),dict(evidence_sha256='A'*64),dict(unit='work')]:
        rejects('bound schema '+str(change),lambda change=change:M.bound(DC.replace(B(1),**change)))
    terms={name:B(i+1,'work') for i,name in enumerate(M.WORK_TERMS)}
    expected=895084428325956794+sum(M.WORK_TERMS[name]*b.value for name,b in terms.items())
    w=M.work(terms)
    check('independent linear work oracle',w['whole_work']==expected and not w['accepted_bound'] and not w['operational_grant'])
    for name in terms:
        bad=dict(terms);bad.pop(name);rejects('work omission '+name,lambda bad=bad:M.work(bad))
        for invalid in [B(0,'work'),B(True,'work'),B(M.U64,'work'),B(1),DC.replace(B(1,'work'),source_tree=M.OLD_TREE)]:
            bad=dict(terms);bad[name]=invalid;rejects('work bad bound '+name+' '+str(invalid.value)+' '+invalid.unit,lambda bad=bad:M.work(bad))
    rejects('unknown work obligation',lambda:M.work({**terms,'private_zero':B(1,'work')}))

def bindings():
    rng=random.Random(271027);v=synthetic(rng)
    source_snippet=(ROOT/'verification/swift-guarded-snapshot-outer-parent-source/outer-parent.inc.rs').read_text()
    identity_body=source_snippet.split('struct ImmutableFixtureIdentitiesV1 {',1)[1].split('}',1)[0]
    identity_fields=tuple(re.findall(r'(\w+): ImmutableIdentityPreimageV1',identity_body))
    check('model identity positions equal12 actual source fields',M.IDENTITIES==identity_fields and len(identity_fields)==12)
    budget_source=(ROOT/'verification/swift-guarded-snapshot-funding-implementation/source/vm/src/experimental_swift_reactor/control.rs').read_text()
    budget_body=budget_source.split('pub struct SwiftRunBudget {',1)[1].split('}',1)[0]
    budget_fields=tuple(re.findall(r'pub (\w+):',budget_body))
    check('model17 product fields equal actual source',M.BUDGET_FIELDS==budget_fields and len(budget_fields)==17)
    for index in range(64):
        value=synthetic(rng);actual=M.storage(value);p0,parts,child=oracle(value)
        check('random independent storage oracle '+str(index),actual['P0_preexisting']==p0 and actual['inherited_six_child_storage_parts']==parts and actual['inherited_child_prepaid']==child and actual['whole_external_storage']==p0+child)
        check('random positive labels never qualify '+str(index),not actual['binding_reviewed_or_accepted'] and not actual['actual_fixture_or_root_policy_selected'] and not actual['healthy_cleanup_native_OTA_GA'] and actual['arithmetic_only_not_receipt_validator'] and not actual['self_embedding_or_static_provider_proven'])
    for i,name in enumerate(M.IDENTITIES):
        for change in [dict(preimage=b''),dict(preimage=bytearray(v.identities[i].preimage)),dict(sha256='b'*64),dict(backing=B(0)),dict(backing=B(True)),dict(backing=B(max(0,len(v.identities[i].preimage)-1))),dict(backing=DC.replace(v.identities[i].backing,source_tree=M.OLD_TREE)),dict(backing=B(1,'work'))]:
            rejects('identity '+name+' '+str(list(change)),lambda i=i,change=change:M.storage(DC.replace(v,identities=replace_at(v.identities,i,**change))))
    for ids in [v.identities[:-1],v.identities+(v.identities[0],),tuple(reversed(v.identities)),(v.identities[0],)*12,list(v.identities)]:rejects('all12 positions '+str(type(ids))+str(len(ids)),lambda ids=ids:M.storage(DC.replace(v,identities=ids)))
    ids=replace_at(v.identities,0,preimage=b'x'*1947,sha256=M.digest(b'x'*1947))
    rejects('same-size wrong selected source',lambda:M.storage(DC.replace(v,identities=ids)))
    for name,cap in [('build',128*1024),('session',64*1024),('executable',64*1024**2)]:
        # The large executable byte body is unnecessary for endpoint arithmetic;
        # limits are checked directly for build/session and retained as source
        # constraints for the64MiB executable cap rather than allocating it.
        if name=='executable':continue
        i=M.IDENTITIES.index(name);body=b'x'*(cap+1);ids=replace_at(v.identities,i,preimage=body,sha256=M.digest(body),backing=B(len(body)))
        rejects('file cap '+name,lambda ids=ids:M.storage(DC.replace(v,identities=ids)))
    for i in range(5):
        path=v.paths[i]
        for change in [dict(native_body=b''),dict(retained_byte_preimage=b''),dict(retained_byte_preimage=b'/different'),dict(native_body=bytearray(path.native_body)),dict(native_backing=B(len(path.native_body)-1)),dict(byte_preimage_backing=B(len(path.native_body)-1)),dict(open_temporary=B(len(path.native_body))),dict(open_temporary=B(True)),dict(correspondence_sha256=''),dict(native_backing=B(1,'count'))]:
            rejects('path '+str(i)+' '+str(list(change)),lambda i=i,change=change:M.storage(DC.replace(v,paths=replace_at(v.paths,i,**change))))
    for paths in [v.paths[:-1],v.paths+(v.paths[0],),list(v.paths)]:rejects('five typed path positions '+str(len(paths)),lambda paths=paths:M.storage(DC.replace(v,paths=paths)))
    equal=M.storage(DC.replace(v,paths=(v.paths[0],)*5))
    check('same PathInput object has five native charges',equal['five_native_Path_pointee_backing']==5*v.paths[0].native_backing.value)
    check('same byte content has five separate retained charges',equal['five_separate_retained_byte_body_backing']==5*v.paths[0].byte_preimage_backing.value)
    for i in range(8):
        claims=list(v.claims);claims[i]=b'x'*31
        rejects('claim width '+str(i),lambda claims=claims:M.storage(DC.replace(v,claims=tuple(claims))))
    rejects('claim omission',lambda:M.storage(DC.replace(v,claims=v.claims[:-1])))
    for name in M.BUDGET_FIELDS:
        b=dict(v.product_budget);b.pop(name);rejects('product omission '+name,lambda b=b:M.storage(DC.replace(v,product_budget=b)))
        for bad in (0,True,-1,M.U64+1):
            b=dict(v.product_budget);b[name]=bad;rejects('product invalid '+name+' '+str(bad),lambda b=b:M.storage(DC.replace(v,product_budget=b)))
    for name in ('execution_work','combined_bytes'):
        b=dict(v.product_budget);b[name]+=1;rejects('selected constraint '+name,lambda b=b:M.storage(DC.replace(v,product_budget=b)))
    rejects('unknown product field',lambda:M.storage(DC.replace(v,product_budget={**v.product_budget,'extra':1})))
    for field in ('future_root_inline','future_root_owned_backing','immutable_diagnostic_backing','loader_native_temporaries','executable_open_temporary','file_resource_backing_each','error_backing_each','all_payload_destructor_temporaries'):
        for bad in [None,B(0),B(True),B(1,'work'),DC.replace(getattr(v,field),source_tree=M.OLD_TREE),B(M.U64)]:
            rejects('storage obligation '+field+' '+str(bad),lambda field=field,bad=bad:M.storage(DC.replace(v,**{field:bad})))
    for field,floor in dict(loader_native_temporaries=8572,executable_open_temporary=4097,file_resource_backing_each=73,error_backing_each=32,error_owner_count=396924,all_payload_destructor_temporaries=29394).items():
        unit='count' if field=='error_owner_count' else 'bytes'
        rejects('inherited lower envelope '+field,lambda field=field,floor=floor,unit=unit:M.storage(DC.replace(v,**{field:B(floor-1,unit)})))
    for bad in [None,B(396924),B(True,'count'),B(M.U64,'count')]:rejects('error owner count typing/overflow '+str(bad),lambda bad=bad:M.storage(DC.replace(v,error_owner_count=bad)))
    for field,bad in [('source_tree',M.OLD_TREE),('binding_review_sha256','')]:rejects('binding schema '+field,lambda field=field,bad=bad:M.storage(DC.replace(v,**{field:bad})))
    # Positive deliberately fake hashes/labels/claims do pass arithmetic. It is
    # essential to demonstrate that this does not authenticate actual evidence.
    check('arbitrary positive evidence remains explicitly unqualified',M.storage(v)['binding_reviewed_or_accepted'] is False)

def ownership():
    def active():
        r=M.Retirement();r.provision_p0();r.enter();return r
    rejects('entry before P0',lambda:M.Retirement().enter())
    r=active();rejects('refund before destruction',r.release)
    for route in ('some','none','unwind'):
        r=active();r.borrow();rejects('destroy during shared view '+route,lambda r=r,route=route:r.destroy(route));rejects('result borrow escape '+route,r.final_result)
        r.end_view();rejects('second inspection '+route,r.borrow);r.destroy(route)
        rejects('second affine destruction '+route,lambda r=r:r.destroy('some'))
        if route=='some':
            r.release();check('some release preserves P0',r.p0 and not r.held and not r.token)
            rejects('duplicate release',r.release);r.final_result();r.consume_result();check('P0 through final result',r.p0)
        else:
            rejects('none/unwind no refund '+route,r.release);check('none/unwind charge held '+route,r.held)
        rejects('re-entry after original route '+route,r.enter)
    r=active();r.borrow();r.end_view();r.destroy('some');r.unwind();rejects('unwind after token no release',r.release)
    r=active();r.destroy('some');r.release();r.final_result();r.p0=False;rejects('result disposal after losing P0',r.consume_result)
    # The toy model's mutable booleans are not an authority/security API. Do
    # not conflate finite controls with arbitrary Python object tamper proof.
    for bad in [{'bb0':['goto -> bb0;']},{'bb0':['new_terminal;']}]:rejects('path fail closed '+str(bad),lambda bad=bad:R.paths(bad),ValueError)
    rejects('unknown native layout',lambda:R.extent('NewUnpricedType',{}),ValueError)
    rejects('unknown unsized reference',lambda:R.extent('&[u8]',{}),ValueError)

def binding_and_path_mutations():
    """Independent gates anchored in full bytes/sets, not positive summaries."""
    old=b'mod prior { fn kept() {}\n}\n';addition=b'mod outer { fn pending() {} }\n'
    prefix=b'\n\n    // Private outer caller candidate; all prior bodies remain exact.\n'
    new=old[:-2]+prefix+addition+b'}\n'
    def exact_addition(before,after,insert):
        if not before.endswith(b'\n}\n') or after!=before[:-2]+prefix+insert+b'}\n':raise ValueError('source rebind must preserve every original byte')
    exact_addition(old,new,addition);check('independent source rebind positive fixture',True)
    for after in [new.replace(b'kept',b'lost'),new+b'x',new[1:],new.replace(b'fn pending',b'pub fn pending'),new.replace(prefix,b'\n'),new[:-1]]:
        rejects('independent source binding byte mutation '+str(len(after)),lambda after=after:exact_addition(old,after,addition))
    expected=json.loads((C/'seal.json').read_bytes())['members']
    def frozen_rows(rows):
        if type(rows) is not list or len(rows)!=44:raise ValueError('exact44 rows')
        if any(type(x) is not dict or set(x)!={'path','bytes','sha256'} or type(x['bytes']) is not int for x in rows):raise ValueError('typed member row')
        if len({x['path'] for x in rows})!=44:raise ValueError('unique complete member identities')
        if rows!=expected:raise ValueError('root-frozen exact paths/bytes/hashes required')
    frozen_rows(expected);check('exact frozen44 rows',True)
    for rows in [expected[:-1],expected+[expected[0]],list(reversed(expected)),[expected[0]]*44]:rejects('member count or identity mutation '+str(len(rows)),lambda rows=rows:frozen_rows(rows))
    for key,bad in [('bytes',True),('bytes',0),('sha256','a'*64),('path','other-source')]:
        rows=[dict(x) for x in expected];rows[0][key]=bad
        rejects('typed frozen member mutation '+key+' '+str(bad),lambda rows=rows:frozen_rows(rows))
    all_paths=json.loads((HERE/'terminal-paths.json').read_bytes())
    for name,original in all_paths.items():
        expected_set={(tuple(x['blocks']),x['terminal']) for x in original}
        def exact_paths(paths):
            actual={(tuple(x['blocks']),x['terminal']) for x in paths}
            if len(actual)!=len(paths) or actual!=expected_set:raise ValueError('exact explicit terminal alternatives required')
        for changed in [original[:-1],original+[original[0]],original+[dict(blocks=['bb0','bb_unfunded'],terminal='return')]]:
            rejects('exact path omission/count/source '+name,lambda changed=changed:exact_paths(changed))
        changed=[dict(x) for x in original];changed[0]=dict(blocks=changed[0]['blocks'],terminal='claimed-healthy-completion')
        rejects('terminal claim not actual MIR '+name,lambda changed=changed:exact_paths(changed))

def mir_ownership():
    raw=(ROOT/'verification/swift-guarded-snapshot-outer-parent-independent/commands/compiler-metadata-mir/outer-and-query.mir').read_text()
    body=R.function(raw,'consume_outer_request_v1');blocks={};current=None
    for line in body.splitlines():
        line=line.partition('//')[0].rstrip();m=re.fullmatch(r'    (bb\d+)(?: \(cleanup\))?: \{',line)
        if m:current=m[1];blocks[current]=[]
        elif line=='    }':current=None
        elif current and line.strip():blocks[current].append(line.strip())
    paths=R.paths(blocks);feasible=[];pruned=[]
    for path,terminal in paths:
        flag=False;valid=True;destructions=0;view=False;released=0
        for i,b in enumerate(path):
            for op in blocks[b]:
                if op=='_50 = const true;':flag=True
                if op=='_50 = const false;':flag=False
                if 'borrow_original_diagnostics_once_v1(' in op:
                    # A borrowed result exists only on the return edge. If the
                    # call unwinds, no caller-owned view was materialized.
                    view=i+1<len(path) and path[i+1]=='bb11'
                if 'observe_borrowed_originals_v1(' in op:
                    # The view moves into the finite observer; both its return
                    # and completed unwind end that callee's shared references
                    # before any caller cleanup payload destruction.
                    view=False
                if op=='StorageDead(_31);':view=False
                if 'destroy_returned_fixture_v1(' in op or op.startswith('drop(_14)'):
                    check('view ended before destruction '+','.join(path),not view)
                    destructions+=1
                if 'release_after_retirement_v1(' in op:
                    released+=1;check('Some token extracted before release '+','.join(path),'bb15' in path and path.index('bb15')>path.index('bb13'))
            if b=='bb23' and i+1<len(path) and path[i+1] != ('bb22' if flag else 'bb21'):valid=False
        (feasible if valid else pruned).append(dict(blocks=list(path),terminal=terminal,destruction_attempts=destructions,releases=released))
        if valid:check('actual drop flag prevents duplicate payload teardown '+','.join(path),destructions<=1 and released<=1)
    check('MIR32 graph paths retained',len(paths)==32)
    # Exact snippets are checked only as source-rebind evidence, alongside the
    # previously accepted compiler pass and actual MIR owner movement above.
    host=(ROOT/'verification/swift-guarded-snapshot-host-composition/overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs').read_text()
    clean='\n'.join(x.partition('//')[0] for x in host.splitlines())
    check('take-before-drop and carrier-before-token retained', 'if let Some(owned) = self.owned.take() { drop(owned); }\n        let reservation = self.reservation.take();\n        drop(self);\n        match reservation {' in clean)
    check('both explicit and fallback Drop take original once',clean.count('if let Some(owned) = self.owned.take() { drop(owned); }')==2)
    snippet=(ROOT/'verification/swift-guarded-snapshot-outer-parent-source/outer-parent.inc.rs').read_text()
    view=snippet.split("enum BorrowedOriginalDiagnosticsV1<'a>",1)[1].split('fn borrow_original_diagnostics_once_v1',1)[0]
    check('all8 borrowed diagnostic positions are shared original borrows',view.count("&'a ")==8 and '&mut' not in view)
    clean_snippet='\n'.join(x.partition('//')[0] for x in snippet.splitlines())
    check('actual static provider requirement preserved',"preexisting: &'static PreexistingImmutableBindingV1" in clean_snippet and "bytes: &'static [u8]" in clean_snippet)
    check('selected immutable binding still pending','Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)' in clean_snippet)
    check('no source allocation or clone in new outer candidate',not any(x in clean_snippet for x in ['Box::','Vec::','String::','clone(','leak(','unsafe']))
    R.out('mir-lifetime-controls.json',dict(all_conservative_graph_paths=32,drop_flag_compatible_paths=sorted(feasible,key=lambda p:p['blocks']),
        infeasible_drop_flag_alternatives=sorted(pruned,key=lambda p:p['blocks']),
        compatible_paths_still_include_unreachable_discriminant_alternatives=True,
        all_written_blocks_charged_without_pruning_credit=True,
        original_owners_remain_in_payload=True,healthy_destruction_or_close_observed=False,
        static_provider_demonstrated=False))

def main():
    arithmetic();bindings();ownership();binding_and_path_mutations();mir_ownership()
    R.out('adversarial-controls.json',dict(schema=1,passed=True,cases=len(cases),results=cases,
          synthetic_values_are_not_actual_evidence=True,account_or_policy_created=False,
          model_scope='Typed arithmetic and finite order controls; no receipt, provenance, binary, funding or provider authority'))
    print(json.dumps(dict(passed=True,cases=len(cases),compiler_or_native_processes=0)))
if __name__=='__main__':main()
