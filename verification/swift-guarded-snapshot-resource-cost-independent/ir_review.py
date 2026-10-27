#!/usr/bin/env python3
"""Read the root's released compiler-only IR; never run a compiler."""
import gzip,hashlib,json,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
P=V/'swift-guarded-snapshot-source146-closure-layouts'
SOURCE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
inputs={};checks=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
    b=p.read_bytes();inputs[str(p.relative_to(R))]={'bytes':len(b),'sha256':sha(b)};return b
def load(p):return json.loads(read(p))
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
def write(n,obj):(D/n).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
raw=read(P/'seal.json');check('released-IR-seal',sha(raw)=='d630481ae157d9b406334031d6592a24fa8e96da5b9fb298f255edfa70782e9b')
seal=json.loads(raw);check('packet-count-bytes',len(seal['members'])==21 and sum(m['bytes'] for m in seal['members'])==1685237)
for m in seal['members']:
    p=Path(m['path']);check('safe:'+str(p),not p.is_absolute() and '..' not in p.parts)
    b=read(P/p);check('member:'+str(p),len(b)==m['bytes'] and sha(b)==m['sha256'])
check('IR-root-release',sha(read(V/'swift-semantic-adapter-root-review/guarded-snapshot-source146-closure-layout-release.json'))=='a227230401e302ade845702f88a10bb33110486a9cb0b157bfc69424053b09c7')
manifest=load(P/'compiled-manifest.json');refs=load(P/'original-source-reference-map.json')['members'];binding=load(P/'binding.json');receipt=load(P/'compiler-receipt.json')
original={m['path']:m for m in manifest['source_manifest']['members']};compiled={m['path']:m for m in manifest['compiled_source_members']}
check('original146-tree',len(original)==len(compiled)==len(refs)==146 and sha(json.dumps(manifest['source_manifest']['members'],sort_keys=True,separators=(',',':')).encode())==SOURCE)
check('only-two-additive-files',set(k for k in original if original[k]!=compiled[k])==set(manifest['additions']) and len(manifest['additions'])==2)
for ref in refs:
    b=read(R/ref['source']);check('original:'+ref['path'],len(b)==ref['bytes'] and sha(b)==ref['sha256'] and original[ref['path']]=={k:ref[k] for k in ('path','bytes','sha256')})
    if ref['path'] in manifest['additions']:
        fragment=read(P/(Path(ref['path']).stem+'-append.inc.rs'));addition=manifest['additions'][ref['path']]
        check('append-only:'+ref['path'],len(fragment)==addition['bytes'] and sha(fragment)==addition['sha256']);b+=fragment
    check('compiled-original-plus-append:'+ref['path'],len(b)==compiled[ref['path']]['bytes'] and sha(b)==compiled[ref['path']]['sha256'])
for key,name in [('MIXER_LOADER_MANIFEST_SHA256','compiled-manifest.json'),('MIXER_LOADER_COMMAND_SHA256','argv.bin'),('MIXER_LOADER_COMPILE_ENV_SHA256','environment.bin'),('MIXER_LOADER_COMPILER_VERSION_SHA256','compiler-version.stdout')]:
    check('compile-key:'+key,sha(read(P/name))==binding['compile_identity_keys'][key]==receipt['environment'][key])
check('compiler-key',binding['compile_identity_keys']['MIXER_LOADER_COMPILER_SHA256']==manifest['compiler_sha256']==receipt['environment']['MIXER_LOADER_COMPILER_SHA256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0')
check('separate-IR-context',receipt['exit_code']==0 and receipt['direct_child_waited'] and receipt['owned_group_absent'] and not receipt['product_runtime'] and not receipt['timed_out'] and 'opt-level=0' in receipt['argv'] and 'codegen-units=1' in receipt['argv'] and '--emit=llvm-ir=' in '\n'.join(receipt['argv']))
archive=load(P/'llvm-archive.json');packed=read(P/'source146.ll.gz');raw=gzip.decompress(packed)
check('complete12614465B-IR',len(raw)==archive['raw_bytes']==12614465 and sha(raw)==archive['raw_sha256']=='dbea191c3bd7239d9b97472e2993e74928c14985f0ec085cb7718d1e10b3acef' and len(packed)==archive['archive_bytes'] and sha(packed)==archive['archive_sha256'])
ir=raw.decode();definitions={};symbols={}
for m in re.finditer(r'^; ([^\n]+)\n; Function Attrs:[^\n]*\n(define [^\n]+)\n',ir,re.M):
    end=ir.index('\n}\n',m.end())+3;body=ir[m.start():end];label=m.group(1);symbol=re.search(r'@([^ (]+)\(',m.group(2)).group(1)
    check('unique-IR-definition:'+label,label not in definitions)
    definitions[label]={'symbol':symbol,'start_line':ir.count('\n',0,m.start())+1,'end_line':ir.count('\n',0,end),'sha256':sha(body.encode()),'body':body};symbols[symbol]=label
def want(label,anchors):
    check('definition-present:'+label,label in definitions);d=definitions[label]
    for a in anchors:check('IR-edge:'+label+':'+a,a in d['body'])
    return d
arc='<alloc::sync::Arc<core::sync::atomic::Atomic<bool>> as core::ops::drop::Drop>::drop'
weak='<alloc::sync::Weak<core::sync::atomic::Atomic<bool>, &alloc::alloc::Global> as core::ops::drop::Drop>::drop'
slow='<alloc::sync::Arc<core::sync::atomic::Atomic<bool>>>::drop_slow'
global_drop='<alloc::alloc::Global as core::alloc::Allocator>::deallocate'
selected={}
selected[arc]=want(arc,['atomicrmw sub','i64 1 release','icmp eq i64','i8 2','>::drop_slow'])
selected[weak]=want(weak,['atomicrmw sub','i64 1 release','i64 24, i64 8','i64 8, i64 24','<&alloc::alloc::Global as core::alloc::Allocator>::deallocate'])
selected[slow]=want(slow,['i64 16','Weak<core::sync::atomic::Atomic<bool>, &alloc::alloc::Global>'])
selected[global_drop]=want(global_drop,['icmp eq i64 %layout.1, 0','__rust_dealloc(ptr %ptr, i64 %layout.1, i64 %layout.0)'])
selected['<&alloc::alloc::Global as core::alloc::Allocator>::deallocate']=want('<&alloc::alloc::Global as core::alloc::Allocator>::deallocate',[global_drop])
for label in ('core::ptr::drop_glue::<core::io::error::Error>','core::ptr::drop_glue::<core::io::error::repr::Repr>','<core::io::error::repr::Repr as core::ops::drop::Drop>::drop'):
    selected[label]=want(label,['drop'])
decode='core::io::error::repr::decode_repr::<core::io::error::CustomOwner, <core::io::error::repr::Repr as core::ops::drop::Drop>::drop::{closure#0}>'
selected[decode]=want(decode,['and i64 %bits, 3','switch i64','i64 2, label %bb5','i64 0, label %bb3','i64 1, label %bb2'])
error_data='core::ptr::drop_glue::<core::io::error::ErrorData<core::io::error::CustomOwner>>'
selected[error_data]=want(error_data,['CustomOwner'])
box='<alloc::boxed::Box<[u8]> as core::ops::drop::Drop>::drop'
selected[box]=want(box,['mul nuw nsw i64 %ptr.1, 1','i64 %size, i64 1',global_drop,'i64 1, i64 %size'])
vector_types={'Type':'mixer_vm::Type','Signature':'mixer_vm::experimental::metadata::Signature','Import':'mixer_vm::experimental::metadata::Import','Function':'mixer_vm::experimental::metadata::Function','Global':'mixer_vm::experimental::metadata::Global','Export':'mixer_vm::experimental::metadata::Export','Segment':'mixer_vm::experimental::metadata::Segment','PinRecord':'mixer_vm::experimental::cache::PinRecord','DecodedInstruction':'mixer_vm::experimental::cache::DecodedInstruction','u32':'u32'}
vector_extents={'Type':(1,1),'Signature':(4,12),'Import':(4,20),'Function':(4,12),'Global':(4,12),'Export':(4,16),'Segment':(4,16),'PinRecord':(8,16),'DecodedInstruction':(8,40),'u32':(4,4)}
for key,ty in vector_types.items():
    vg='core::ptr::drop_glue::<alloc::vec::Vec<'+ty+'>>';vd='<alloc::vec::Vec<'+ty+'> as core::ops::drop::Drop>::drop';rd='<alloc::raw_vec::RawVec<'+ty+'> as core::ops::drop::Drop>::drop'
    selected[vg]=want(vg,[vd,'RawVec<'+ty+'>']);selected[vd]=want(vd,['ret void']);a,b=vector_extents[key]
    selected[rd]=want(rd,['RawVecInner>::deallocate','i64 '+str(a)+', i64 '+str(b)])
missing=['<alloc::vec::Vec<mixer_vm::experimental_swift_reactor::cache::SwiftSlot> as core::ops::drop::Drop>::drop','<alloc::vec::Vec<mixer_vm::experimental::cache::decode::Patch> as core::ops::drop::Drop>::drop','<alloc::vec::Vec<core::option::Option<mixer_vm::experimental_swift_reactor::cache::ScanPlan>> as core::ops::drop::Drop>::drop','core::ptr::drop_glue::<std::fs::File>','<std::os::fd::owned::OwnedFd as core::ops::drop::Drop>::drop','<alloc::raw_vec::RawVec<u8> as core::ops::drop::Drop>::drop','<alloc::raw_vec::RawVecInner>::deallocate']
for label in missing:check('unresolved-definition-absent:'+label,label not in definitions)
external=[]
for label,d in selected.items():
    for symbol in re.findall(r'^\s*(?:%[^=]+ = )?(?:call|invoke) [^@\n]*@([^ (]+)\(',d['body'],re.M):
        if symbol not in symbols:
            declaration=next((line for line in ir.splitlines() if line.startswith('declare ') and '@'+symbol+'(' in line),None)
            external.append({'caller':label,'symbol':symbol,'declaration':declaration})
check('external-RawVecInner-deallocate-retained',any('11RawVecInner10deallocate' in x['symbol'] and x['declaration'] for x in external))
check('external-allocator-shim-retained',any('___rust_dealloc' in x['symbol'] and x['declaration'] for x in external))
write('compiled-IR-correspondence.json',{'schema':1,'status':'partial-correspondence-in-separate-recorded-compiler-context','source_tree_sha256':SOURCE,'compile_identity_keys':binding['compile_identity_keys'],'raw_IR_sha256':sha(raw),'checks':len(checks),'functions':selected,'missing_definitions':missing,'external_edges':external,'closed_here':['Arc<AtomicBool> strong and implicit Weak release/final-owner/acquire edges with concrete size24 align8 deallocation to Global and allocator shim','Error Repr tag dispatch and explicit Custom callback boundary; Os/static branches have no owned dynamic payload','Box<[u8]> size=len and alignment1 deallocation request','ten concrete Vec/RawVec destructor wrappers and element size/alignment operands listed in functions'],'still_pending':['File/OwnedFd conditional UB check/fcntl/errno/abort/close nongeneric installed bodies and File-origin error constructors','Vec<SwiftSlot>, Vec<Patch>, Vec<Option<ScanPlan>> destructor instantiations','RawVec<u8>::Drop and shared RawVecInner::deallocate external precompiled bodies','actual caller/executable composition and compiler context binding; this query changes compilation identity keys','external allocator implementation and physical footprint stay outside inherited logical unit; no close/refund/healthy cleanup or product runtime observed'],'source_prices_unchanged':True,'no_new_compiler_runtime':True,'whole_host_funding_or_GA':False})
write('ir-input-custody.json',{'schema':1,'files':inputs})
write('ir-controls.json',{'schema':1,'assertions':len(checks),'controls':checks,'all_passed':True})
print(json.dumps({'status':'passed','assertions':len(checks),'selected_IR_functions':len(selected),'external_edges':len(external),'new_compiler_runtime':False},sort_keys=True))
