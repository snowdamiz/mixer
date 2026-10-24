#!/usr/bin/env python3
"""Conservative named whole-object preflight supplement, compiler-assisted types.

This is a logical object reservation proposal, not a stack/RSS measurement.
All selected whole values get separate fields, including sequential branches;
there is no lifetime/padding/diagnostic-class reuse or subtraction. MIR is used
to check closure capture and return/receiver shapes, not to infer acceptance.
"""
from pathlib import Path
import re,json,hashlib
out=Path(__file__).resolve().parent
mirpath=out/'target/debug/deps/mixer_vm.mir'
mir=mirpath.read_text()
functions=[]
for match in re.finditer(r'^fn (.*?) \{\n(.*?)^\}',mir,re.M|re.S):
    functions.append({'header':match.group(1),'body':match.group(2),'start':mir.count('\n',0,match.start())+1,'text':match.group(0)})
selectors=[
 ('constructor_prelude',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:1430:1:.*>::construct\(',35),
 ('state_prepare',r'^experimental_swift_reactor::execution::<impl at src/experimental_swift_reactor/execution.rs:881:1:.*>::prepare\(',None),
 ('construction_bytes',r'^construction_bytes\(',None),
 ('checked',r'^checked\(',None),
 ('construction_failure',r'^construction_failure\(',None),
 ('layout_failure',r'^experimental_swift_reactor::execution::layout_failure\(',None),
 ('cache_owner',r'^experimental_swift_reactor::cache::<impl at src/experimental_swift_reactor/cache.rs:1291:1:.*>::check_owner\(',None),
 ('cache_header',r'^experimental_swift_reactor::cache::<impl at src/experimental_swift_reactor/cache.rs:1178:1:.*>::check_header\(',None),
 ('cache_pairing',r'^pairing\(',None),
 ('cache_error',r'^experimental_swift_reactor::cache::<impl at src/experimental_swift_reactor/cache.rs:1178:1:.*>::error\(',None),
 ('cache_observation',r'^experimental_swift_reactor::cache::<impl at src/experimental_swift_reactor/cache.rs:1178:1:.*>::observation\(',None),
 ('cache_usage',r'^experimental_swift_reactor::cache::<impl at src/experimental_swift_reactor/cache.rs:1291:1:.*>::usage\(',None),
 ('wasi_checked_usage',r'^accounted::<impl .*>::checked_usage\(',None),
 ('wasi_usage',r'^accounted::<impl .*>::usage\(',None),
 ('context_usage',r'^experimental_wasi::<impl .*>::usage\(',None),
 ('adopted_owner',r'^control::<impl .*>::check_adopted_owner\(',None),
 ('reservation_matches',r'^control::<impl .*>::reservation_owner_matches\(',None),
 ('reservation_owner',r'^control::<impl .*>::check_reservation_owner\(',None),
 ('enlarge_plain',r'^control::<impl .*>::enlarge_construction\(',None),
 ('enlarge_observed',r'^control::<impl .*>::enlarge_construction_with_wasi\(',None),
 ('control_check',r'^control::<impl .*>::check_with_wasi\(',None),
 ('control_usage',r'^control::<impl .*>::usage\(',None),
 ('control_fail',r'^control::<impl .*>::fail\(',None),
 ('bytes_preflight',r'^control::<impl .*>::preflight_bytes\(',None),
 ('bytes_commit',r'^control::<impl .*>::commit_bytes\(',None),
 ('category_limit',r'^control::<impl .*>::category_limit\(',None),
 ('category_ref',r'^control::<impl .*>::category\(',None),
 ('category_mut',r'^control::<impl .*>::category_mut\(',None),
 ('fault_new',r'^control::<impl .*>::new\(',None),
 ('fault_limit',r'^control::<impl .*>::limit\(',None),
 ('micros',r'^micros\(',None),
 ('cancelled',r'^execute::<impl .*>::is_cancelled\(',None),
]
# Resolve names by suffix when rustc uses a module-qualified prefix for collision.
fallbacks={
 'cache_owner':r'^.*::<impl at src/experimental_swift_reactor/cache.rs:1291:1:.*>::check_owner\(',
 'cache_header':r'^.*::<impl at src/experimental_swift_reactor/cache.rs:1178:1:.*>::check_header\(',
 'cache_error':r'^.*::<impl at src/experimental_swift_reactor/cache.rs:1178:1:.*>::error\(',
 'cache_observation':r'^.*::<impl at src/experimental_swift_reactor/cache.rs:1178:1:.*>::observation\(',
 'cache_usage':r'^.*::<impl at src/experimental_swift_reactor/cache.rs:1291:1:.*>::usage\(',
}
# Extract actual closure capture types from their own compiler-generated bodies.
closures={}
for f in functions:
    m=re.search(r'\{closure@([^}]+)\}',f['header'])
    if not m:continue
    captures={int(idx):ty for idx,ty in re.findall(r'_1\.(\d+): ([^\n]+?)\)\)',f['body'])}
    if not captures:
        captures={int(idx):ty for idx,ty in re.findall(r'_1\.(\d+): ([^\n]+?)\);',f['body'])}
    # All actual captured fields are named individually in debug bindings.
    ct=[captures[i] for i in sorted(captures)]
    closures[m.group(1)]={'capture_types':ct,'function':f['header'],'line':f['start']}

def rust_type(ty):
    ty=ty.replace("'_","'static").replace("std::sync::atomic::Atomic<bool>","std::sync::atomic::AtomicBool")
    ty=re.sub(r'(?<![\w:])Duration\b','std::time::Duration',ty)
    def closure(m):
        key=m.group(1);assert key in closures,key
        types=[rust_type(t) for t in closures[key]['capture_types']]
        return '('+','.join(types)+(',' if len(types)==1 else '')+')'
    ty=re.sub(r'\{closure@([^}]+)\}',closure,ty)
    ty=re.sub(r'(?<![\w:])experimental_swift_reactor::','crate::experimental_swift_reactor::',ty)
    ty=re.sub(r'(?<![\w:])experimental_wasi::','crate::experimental_wasi::',ty)
    ty=re.sub(r'(?<![\w:])experimental::','crate::experimental::',ty)
    ty=re.sub(r'(?<![\w:])control::','super::control::',ty)
    ty=re.sub(r'(?<![\w:])execute::','crate::execute::',ty)
    ty=re.sub(r'(?<![\w:])WasiContext\b','crate::experimental_wasi::WasiContext',ty)
    ty=re.sub(r'(?<![\w:])SwiftCacheUsage\b','super::cache::SwiftCacheUsage',ty)
    ty=re.sub(r"&(?!'static)(mut\s+)?",lambda m:"&'static "+('mut ' if m.group(1) else ''),ty)
    return ty

selected=[]
for role,pat,cutoff in selectors:
    found=[f for f in functions if re.search(pat,f['header'])]
    if len(found)!=1:
        if role in fallbacks:found=[f for f in functions if re.search(fallbacks[role],f['header'])]
    if len(found)!=1:
        # report exact candidate definitions for adapting only type-disambiguation
        print(role,pat,'matches',len(found));
        print('\n'.join(f['header'] for f in functions if ('::'+role.split('_')[-1]+'(') in f['header'])[:4000]);raise SystemExit(1)
    f=found[0]
    # Arguments have nested generic commas. Signature -> outer argument text ends at ) ->.
    args=f['header'].split('(',1)[1].rsplit(') ->',1)[0]
    decls={int(n):ty for n,ty in re.findall(r'let(?: mut)? _(\d+): ([^\n]+);',f['body'])}
    argmatches=list(re.finditer(r'_(\d+): ',args))
    for i,m in enumerate(argmatches):decls[int(m.group(1))]=args[m.end():argmatches[i+1].start()-2 if i+1<len(argmatches) else len(args)]
    aliases={int(n):name for name,n in re.findall(r'debug (\w+) => _(\d+);',f['body'])}
    # Constructor prelude ends at the first enlarge return; _35 is that ? residual.
    fields=[]
    for n,ty in sorted(decls.items()):
        if cutoff is not None and n>cutoff:continue
        fields.append({'field':'object_'+str(n),'type':rust_type(ty),'mir_type':ty,'mir_local':'_'+str(n),'source_binding':aliases.get(n),'role':('whole return slot' if n==0 else 'argument' if n<=len(argmatches) else 'named binding' if n in aliases else 'whole explicit receiver/return/branch/closure/scalar object')})
    selected.append({'role':role,'function':f['header'],'mir_line':f['start'],'cutoff':cutoff,'fields':fields})
    # Include callback function frame fields separately; closure object remains in caller.
    for callback in functions:
        if callback['header'].startswith(f['header'].split('(',1)[0]+'::{closure#'):
            sig=callback['header'];cbargs=sig.split('(',1)[1].rsplit(') ->',1)[0]
            cbdecl={int(n):ty for n,ty in re.findall(r'let(?: mut)? _(\d+): ([^\n]+);',callback['body'])}
            am=list(re.finditer(r'_(\d+): ',cbargs))
            for i,m in enumerate(am):cbdecl[int(m.group(1))]=cbargs[m.end():am[i+1].start()-2 if i+1<len(am) else len(cbargs)]
            fields=[{'field':'object_'+str(n),'type':rust_type(ty),'mir_type':ty,'mir_local':'_'+str(n),'source_binding':None,'role':'whole callback argument/receiver/return/scalar'} for n,ty in sorted(cbdecl.items())]
            selected.append({'role':role+'_callback_'+str(len([x for x in selected if x['role'].startswith(role+'_callback_')])),'function':sig,'mir_line':callback['start'],'cutoff':None,'fields':fields})

src=['// Independently authored supplemental logical whole-object inventory.\n// Conservative sum of complete authored preflight call frames; no old slot is reclaimed.\n']
for group in selected:
    name='PreflightSupplement'+''.join(x.title() for x in group['role'].split('_'))
    group['struct']=name
    src.append('#[allow(dead_code)]\nstruct '+name+' {\n')
    for field in group['fields']:src.append('    '+field['field']+': '+field['type']+',\n')
    src.append('}\n')
src.append('#[allow(dead_code)]\npub(super) struct ConstructionPreflightSupplement {\n')
for g in selected:src.append('    '+g['role']+': '+g['struct']+',\n')
src.append('}\n')
src.append('pub(super) const CONSTRUCTION_PREFLIGHT_SUPPLEMENT_BYTES: usize = std::mem::size_of::<ConstructionPreflightSupplement>();\n')
src.append('pub(crate) fn independent_preflight_supplement_probe(){\n use std::mem::{size_of,align_of,offset_of};\n')
for group in selected:
    src.append('println!("isupplement|'+group['role']+'|{}|{}",size_of::<'+group['struct']+'>(),align_of::<'+group['struct']+'>());\n')
    for f in group['fields']:src.append('println!("isupplementfield|'+group['role']+'|'+f['field']+'|{}|{}|{}",offset_of!('+group['struct']+','+f['field']+'),size_of::<'+f['type']+'>(),align_of::<'+f['type']+'>());\n')
src.append('println!("isupplementtotal|{}|{}",size_of::<ConstructionPreflightSupplement>(),align_of::<ConstructionPreflightSupplement>());\n}\n')
(out/'preflight-supplement.rs').write_text(''.join(src))
manifest={'schema':'mixer-swift-construction-independent-preflight-supplement-v1','status':'proposal for source/shape review; measured only after compilation','source_mir_sha256':hashlib.sha256(mir.encode()).hexdigest(),'policy':'Whole fields summed including mutually exclusive branches; no liveness optimization or old-slot credit. Actual closure field tuples come from MIR type evidence. Compiler branch/residual values are included positively; this is not physical stack or RSS. Native standard-library implementation internals remain outside authored inventory, but every authored receiver, argument and returned whole shape is present.','selected_call_frames':selected,'closures':closures}
(out/'preflight-supplement-map.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'groups':len(selected),'fields':sum(len(g['fields'])for g in selected),'source_sha256':hashlib.sha256((''.join(src)).encode()).hexdigest()}))
