#!/usr/bin/env python3
"""Read-only frozen inputs; write only this source resource packet.

Exact-source assertions support a manual closed-route proof. They do not parse
arbitrary Rust, establish binary std correspondence or authorize any execution.
"""
import copy, gzip, hashlib, json, sys
from pathlib import Path
sys.dont_write_bytecode=True
from model import SOURCE,HOST,RUST,Refused,source_ceiling_cuts,components

D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification'
S=V/'swift-guarded-snapshot-stdlib-resource-source'
P=V/'swift-guarded-snapshot-payload-destruction-cost'
I=V/'swift-guarded-snapshot-payload-destruction-independent'
C=V/'swift-guarded-snapshot-host-composition'
BASE=V/'swift-guarded-snapshot-funding-implementation/source/vm'
inputs={};checks=[];evidence=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def read(p):
    raw=p.read_bytes();inputs[str(p.relative_to(R))]={'bytes':len(raw),'sha256':sha(raw)};return raw
def load(p):return json.loads(read(p))
def require(name,ok):
    if not ok:raise AssertionError(name)
    checks.append(name)
def write(name,value):
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode();p=D/name
    if '--check-only' in sys.argv:require('current:'+name,p.read_bytes()==raw)
    else:p.write_bytes(raw)
def packet(path,digest,count):
    raw=read(path/'seal.json');require('seal:'+path.name,sha(raw)==digest);seal=json.loads(raw)
    require('count:'+path.name,len(seal['members'])==count)
    for m in seal['members']:
        p=Path(m['path']);require('safe:'+path.name+'/'+str(p),not p.is_absolute() and '..' not in p.parts)
        raw=read(path/p);require('member:'+path.name+'/'+str(p),len(raw)==m['bytes'] and sha(raw)==m['sha256'])
def release(name,digest):require('release:'+name,sha(read(V/'swift-semantic-adapter-root-review'/name))==digest)
def text(path):return read(path).decode()
def cite(path,start,end,claim,anchors=()):
    raw=read(path);lines=raw.decode().splitlines();excerpt='\n'.join(lines[start-1:end])+'\n'
    for a in anchors:require('anchor:'+claim+':'+a,a in excerpt)
    evidence.append({'path':str(path.relative_to(R)),'first_line':start,'last_line':end,
                     'file_sha256':sha(raw),'excerpt_sha256':sha(excerpt.encode()),
                     'claim':claim,'source':excerpt})

def build():
    packet(S,'3e78720975acacfcc9efc35ed8069649be6ddeae6ce9a7d4dcbe236f7b46419f24',24)
    packet(P,'8378e706ba0d262b935114fca8cc2d1a995286f8eedce4bfa524ac5c8c6ce72f75',75)
    packet(I,'6f1bf241613a843417a7ec19b1d6657aed57844250c922b5f5cc485a423d75a054',54)
    release('guarded-snapshot-payload-destruction-host-acceptance.json','89cbab409dc2944861f29520149f52b9a2447cc88ded1f1cad4a8e08ef204195')
    release('guarded-snapshot-stdlib-resource-source-release.json','5bc848d64ac667bc22f7c407f0a912d6651dae1ab6a73e90bc79b0a0c7fdd0b0')
    manifest=load(C/'source-manifest.json');source={}
    require('source146-manifest',len(manifest['members'])==146 and sha(canonical(manifest['members']))==SOURCE)
    for m in manifest['members']:
        path=C/'overlay/vm'/m['path'];path=path if path.is_file() else BASE/m['path']
        raw=read(path);require('source146:'+m['path'],len(raw)==m['bytes'] and sha(raw)==m['sha256']);source[m['path']]=path
    host=load(C/'host-support-manifest.json')
    require('host11-manifest',len(host['members'])==11 and sha(canonical(host['members']))==HOST)
    for m in host['members']:
        raw=read(V/'swift-real-profile-loader-binding/host'/m['path']);require('host11:'+m['path'],len(raw)==m['bytes'] and sha(raw)==m['sha256'])
    fetched=load(D/'fetch-receipt.json')
    require('official-revision',fetched['revision']==RUST)
    for m in fetched['files']:
        raw=read(D/'official-source'/m['path']);require('extra-official:'+m['path'],m['status']==200 and len(raw)==m['bytes'] and sha(raw)==m['sha256'] and '/'+RUST+'/' in m['url'])
    require('no-toolchain-mutation',fetched['installed_toolchain_mutated'] is False)
    raw=read(V/'swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz')
    require('MIR-archive',sha(raw)=='03b5265c5ae85b3a444f847f1b65af8f31e9fee7697845d6f9699ddf2d8e87e7')
    mir=gzip.decompress(raw);require('MIR-raw',sha(mir)=='e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2')
    calls=[l.strip() for l in mir.decode().splitlines() if '= read_request::<' in l]
    require('closed-File-read-specialization',len(calls)==2 and all('read_request::<std::fs::File>' in l for l in calls))
    write('MIR-binding.json',{'archive_sha256':sha(raw),'raw_sha256':sha(mir),'typed_read_calls':calls,
        'source_tree_sha256':SOURCE,'not_std_body_evidence':True})
    inv=load(P/'inventory.json');layouts=load(I/'layout-substitution.json');conditions=load(I/'bound-conditions.json')
    require('payload-identities',inv['source_tree_sha256']==SOURCE and inv['host_tree_sha256']==HOST)
    require('layout-identities',layouts['source_tree_sha256']==SOURCE and layouts['all13_symbolic_extents_closed'])
    by={r['type']:r for r in layouts['source14613observations']}
    rows=copy.deepcopy(inv['rows'])
    for r in rows:
        if r['inline_bytes'] is None:r['inline_bytes']=by[r['type']]['size']
        for dynamic in r.get('dynamic_resource_elements',{}).values():
            dynamic['inline_bytes']=by[dynamic['type']]['size']
    require('SwiftSlot136',by['SwiftSlot']['size']==136 and by['SwiftSlot']['structural_occurrence_allowance']==19)
    probe=load(V/'swift-guarded-snapshot-child-entry-cost/probe-analysis.json')
    require('Arc-probe',probe['requested_default_allocation']=={'alignment':8,'bytes':24,'count':1} and probe['clone_new_allocation_count']==0)
    # Frozen exact compiler layout data are inspected, not recomputed.
    layout55=load(V/'swift-guarded-snapshot-source146-leaf-payload-layouts/results.json')
    require('actual55-layout',len(layout55['queries'])==55 and layout55['diagnostic_count']==110 and not layout55['product_executed'])
    layout90=load(V/'swift-guarded-snapshot-host-composition-independent/fresh-layout-results.json')
    require('File4-layout',layout90['actual_type_sizes']['std::fs::File']==4)

    # Every quoted span is retained with the full immutable file hash.
    std=S/'official-source/library'
    cite(std/'std/src/fs.rs',134,137,'File owns sys File',('inner: fs_imp::File',))
    cite(std/'std/src/sys/fs/unix.rs',90,94,'sys File owns FileDesc',('pub struct File(FileDesc)',))
    cite(std/'std/src/sys/fd/unix.rs',70,74,'FileDesc owns OwnedFd',('pub struct FileDesc(OwnedFd)',))
    cite(std/'std/src/os/fd/owned.rs',199,226,'OwnedFd conditional check and close request; errors ignored',('debug_assert_fd_is_open','let _ = libc::close'))
    cite(std/'std/src/sys/fs/unix.rs',962,972,'optional UB fcntl errno abort branch',('check_library_ub()','libc::F_GETFD','errno() == libc::EBADF','rtabort!'))
    cite(std/'alloc/src/sync.rs',2136,2151,'last strong destroys AtomicBool and implicit Weak',('let _weak = Weak','ptr::drop_in_place'))
    cite(std/'alloc/src/sync.rs',2864,2915,'Arc refcount final-owner branch',('strong.fetch_sub(1, Release)','acquire!','self.drop_slow()'))
    cite(std/'alloc/src/sync.rs',3533,3565,'Weak refcount final-owner deallocation layout',('weak.fetch_sub(1, Release)','Layout::for_value_raw','self.alloc.deallocate'))
    cite(std/'alloc/src/alloc.rs',294,321,'Global exact requested size and deallocate layout',('Ok(ptr.cast_slice(size))','never returns a larger'))
    cite(std/'alloc/src/raw_vec/mod.rs',738,770,'RawVec stores requested cap',('self.cap = unsafe { Cap::new_unchecked(cap) }',))
    cite(std/'alloc/src/raw_vec/mod.rs',782,807,'RawVec exact reserve cap length plus additional',('len.checked_add(additional)','self.finish_grow(cap','self.set_ptr_and_cap(ptr, cap)'))
    cite(std/'alloc/src/raw_vec/mod.rs',632,657,'RawVec requested teardown layout capacity times element size',('elem_layout.size().unchecked_mul(self.cap.as_inner())',))
    cite(std/'alloc/src/vec/mod.rs',4350,4365,'Vec elements and RawVec teardown boundary',('cast_slice(self.len).drop_in_place()',))
    cite(std/'alloc/src/boxed.rs',1990,2007,'Box pointee teardown then exact deallocation',('T in the Box is dropped by the compiler','Layout::for_value_raw'))
    cite(std/'core/src/io/error/repr_bitpacked.rs',229,302,'Error tag split and Custom callback hazard',('impl Drop for Repr','TAG_CUSTOM','CustomOwner::from_raw'))
    cite(std/'core/src/io/error.rs',614,622,'Custom inner dynamic callback',('(self.error_drop)(self.error)',))
    cite(std/'core/src/io/error.rs',681,688,'CustomOwner outer dynamic callback',('outer_drop',))
    cite(std/'alloc/src/io/error.rs',248,286,'alloc arbitrary Error Box callbacks',('Box<dyn core::error::Error + Send + Sync>','drop_box_raw::<Custom>'))
    cite(std/'std/src/io/error.rs',42,86,'OS Error source constructs Os tag',('Error::from_raw_os_error(errno())','from_raw_os_error_with_functions'))
    cite(D/'official-source/library/std/src/sys/pal/unix/mod.rs',238,255,'cvt and cvt_r retain only OS errors',('Error::last_os_error()',))
    cite(D/'official-source/library/std/src/sys/helpers/small_c_string.rs',12,75,'path conversion returns static NUL Error or closure File error',('const NUL_ERR','Err(NUL_ERR)',))
    cite(std/'std/src/sys/fs/unix.rs',1158,1246,'valid read-only or write/create_new options avoid custom option errors',('get_access_mode','get_creation_mode','cvt_r(|| unsafe { open64'))
    cite(std/'std/src/sys/fd/unix.rs',137,147,'FileDesc read yields cvt OS error',('libc::read','cvt('))
    # Complete selected product provenance, not arbitrary generic io::Result.
    initial=source['src/experimental_swift_reactor/cache/initial_profile_v1.rs']
    loader=source['src/experimental_swift_reactor/retained_profile_loader_v1.rs']
    cache=source['src/experimental_swift_reactor/cache.rs'];control=source['src/experimental_swift_reactor/control.rs']
    swift=source['src/experimental/swift.rs'];account=source['src/experimental/account.rs']
    decode=source['src/experimental/cache/decode.rs'];borrowed=source['src/experimental/cache/borrowed.rs']
    wasi=source['src/experimental_wasi/accounted.rs'];wasimod=source['src/experimental_wasi/mod.rs']
    cite(initial,759,785,'closed setup File options',('File::open(binding.paths[stage])','write(true).create_new(true)'))
    cite(initial,437,507,'closed writer File metadata position and write Error origin',('output:&mut File','output.write(requested)','output.metadata()','output.stream_position()'))
    cite(loader,523,650,'loader File read and position origins; bounded exact fresh allocation',('fn retained(','file: &mut File','try_reserve_exact(count)','if count > cap'))
    cite(loader,818,849,'getcwd OS Error origin',('io::Error::last_os_error()',))
    cite(loader,925,950,'executable File open Error origin',('let executable = File::open',))
    cite(swift,21,32,'validation default maxima64MiB16MiB1MiB',('source_bytes: 64 * 1024 * 1024','metadata_bytes: 16 * 1024 * 1024','scratch_bytes: 1024 * 1024'))
    cite(swift,377,398,'validation widening rejected before allocation',('budget.metadata_bytes > max.metadata_bytes',))
    cite(swift,424,469,'source Box allocation maximum and exact conversion',('input.len() > budget.source_bytes','source.into_boxed_slice()'))
    cite(account,159,194,'metadata and scratch reserve enforce category maximum before allocation',('if attempted > limit','Resource::Metadata'))
    cite(account,253,304,'metadata fresh exact Vec including failed capacity branch',('next.try_reserve_exact(capacity)','next.capacity() != capacity','drop(next)'))
    cite(control,41,61,'runtime default maxima',('cache_entry_bytes: 8 * MIB','cache_entries: 64','active_pins: 64'))
    cite(control,778,883,'runtime narrowing check',('self.budget.cache_entry_bytes','if attempted > limit'))
    cite(cache,14,46,'cache fixed vector counts',('PATCH_CAPACITY: usize = 512','PLAN_CAPACITY: usize = 512','RESIDENT_LINKS: usize = 64'))
    cite(cache,1120,1137,'cache header includes index and plan backing before admission',('RESIDENT_INDEX_BYTES','PLAN_CAPACITY * size_of::<Option<ScanPlan>>()'))
    cite(cache,1807,1879,'cache vector request and live counts',('reserve(&mut partial.slots, entries','reserve(&mut partial.plans, PLAN_CAPACITY'))
    cite(cache,1909,1927,'cache fresh exact reserve includes refusal',('try_reserve_exact(requested)','control.exact(requested, values.capacity())'))
    cite(borrowed,790,812,'resident Counts byte bound before build',('if bytes > meter.entry_capacity()',))
    cite(decode,497,530,'all three resident vectors allocated by admitted Counts',('borrowed::allocate(counts.locals','borrowed::allocate(counts.instructions','borrowed::allocate(counts.targets'))
    cite(borrowed,217,233,'resident fresh exact request includes refusal',('try_reserve_exact(capacity)','meter.exact_capacity(capacity, values.capacity())'))
    cite(decode,150,165,'resident push never reallocates',('values.len() == values.capacity()',))
    cite(wasimod,51,78,'WASI65536 defaults narrowing',('one_transfer_bytes: 65_536','log_bytes: 65_536','self.one_transfer_bytes > max.one_transfer_bytes'))
    cite(wasi,275,318,'WASI fresh exact four allocations including refusal',('budget.one_transfer_bytes','budget.log_bytes','try_reserve_exact(bytes)','exact_capacity(bytes'))
    # The frozen graph closes plain element shapes and absence of authored Drop.
    schemas=inv['dynamic_element_destructor_schemas'];nodes={k:v['nodes'] for k,v in schemas.items()}
    expected_nodes={'Signature':7,'Type':2,'Import':8,'Function':5,'Global':7,'Export':6,'Segment':6,'PinRecord':3,'Patch':7,'Option<ScanPlan>':11,'DecodedInstruction':14}
    require('plain-element-source-nodes',all(nodes[k]==n and not schemas[k]['resources'] for k,n in expected_nodes.items()))
    vectors={}
    for t in ('Signature','Type','Import','Function','Global','Export','Segment'):
        vectors['Vec<'+t+'>']={'max_requested_bytes':16*1024*1024,'max_live_elements':16*1024*1024,'element_nodes':nodes[t]}
    for t,l in [('PinRecord',64),('Patch',512),('Option<ScanPlan>',512)]:
        vectors['Vec<'+t+'>']={'max_requested_bytes':16*1024*1024,'max_live_elements':l,'element_nodes':nodes[t]}
    vectors['Vec<u8>']={'max_requested_bytes':65536,'max_live_elements':65536,'element_nodes':1}
    vectors['Vec<DecodedInstruction>']={'max_requested_bytes':8*1024*1024,'max_live_elements':8*1024*1024,'element_nodes':14}
    vectors['Vec<u32>']={'max_requested_bytes':8*1024*1024,'max_live_elements':(8*1024*1024)//4,'element_nodes':1}
    vectors['Vec<SwiftSlot>']={'max_requested_bytes':64*136,'max_live_elements':64,'element_nodes':19}
    binding={'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'rust_revision':RUST,
        'target':'aarch64-apple-darwin','allocator':'alloc::alloc::Global','route':'source146-owned-file-route'}
    def event(name,**fields):return {'event':name,'native_fields':fields}
    file=[event('File destructor interface',receiver=8),event('sys File ownership interface',receiver=8),
          event('FileDesc ownership interface',receiver=8),event('OwnedFd destructor interface',receiver=8),
          event('library UB predicate',boolean=1),event('conditional fcntl request',fd=4,command=4,result=4),
          event('conditional errno observation',result=4),event('conditional abort interface',static_message_reference=16),
          event('close request ignored result',fd=4,result=4)]
    arc=[event('Arc destructor interface',receiver=8),event('strong decrement',pointer=8,decrement=8,previous=8),
         event('strong final-owner predicate',boolean=1),event('strong acquire interface',pointer=8),
         event('strong static-backing assertion',boolean=1),event('strong assertion failure interface',static_message_reference=16),
         event('drop_slow interface',receiver=8),event('AtomicBool payload destruction interface',value=1),
         event('implicit Weak destructor interface',receiver=8),event('weak decrement',pointer=8,decrement=8,previous=8),
         event('weak final-owner predicate',boolean=1),event('weak acquire interface',pointer=8),
         event('weak static-backing assertion',boolean=1),event('weak assertion failure interface',static_message_reference=16),
         event('Global deallocation request',pointer=8,bytes=8,alignment=8)]
    error=[event('Error destruction interface',receiver=8),event('Repr destruction interface',receiver=8),
           event('closed Os or static tag dispatch',tag_word=8,max_inline_payload=8)]
    contract={'schema':1,'status':'source-interface-price-candidate-no-execution-authority','binding':binding,
        'logical_unit':'source/aggregate/destructor-interface occurrences plus explicit native-sized/requested-backing allowance',
        'outside_unit':['private standard-library implementation','compiler lowering','allocator implementation and physical overhead','kernel implementation','private retries','CPU instructions/time/RSS/stack'],
        'interfaces':{'File':{'records':file,'requested_backing_bytes':0},
                      'Arc<AtomicBool>':{'records':arc,'requested_backing_bytes':24},
                      'Error':{'records':error,'requested_backing_bytes':0}},
        'vectors':vectors,'byte_box':{'max_requested_bytes':64*1024*1024,'max_live_elements':64*1024*1024},
        'Error_provenance':'closed-file-os-or-static-message','arbitrary_custom_error_accepted':False,
        'actual_capacities_observed':False,'maxima_are_source_ceilings_not_new_policy':True,
        'compiled_standard_library_correspondence_verified':False,
        'resource_cleanup_close_flush_refund_verified':False,'whole_host_quote_or_grant':False,
        'native_runtime':'paused','OTA_GA_accepted':False}
    cuts=source_ceiling_cuts(contract,binding,'closed-file-os-or-static-message')
    result=components(rows,cuts,inv['entry_per_visit_types'])
    write('contract.json',contract);write('rows.json',rows);write('resource-cuts.json',cuts)
    write('components.json',result);write('source-evidence.json',{'schema':1,'entries':evidence})
    write('bound-conditions.json',{'schema':1,'status':'source-specific-finite-interface-component-candidate',
        'binding':binding,'Error_only_for_closed_route':True,
        'qualification_conditions':[
            'Rehash exact source146/host11, accepted payload/layout and official Rust source inputs.',
            'These native slots and event counts are logical interface prices, not private std instructions or observed stack.',
            'Bind the compiled std specialization/correspondence before treating source-only Rust paths as binary evidence.',
            'Do not apply these Error cuts to generic Read/Write implementations, io::Error::new, custom options or foreign errors.',
            'Plain non-ZST element sum(size(T)) <= requested backing; N*B is an upper bound without choosing a fake element extent.',
            'The shared Vec<Type> cap conservatively covers both metadata and per-resident locals; all three nested cuts are retained.',
            'Per-occurrence backing/surcharge in work cuts is deliberate overcoverage and is not storage ownership/refund evidence.',
            'Child53 entry visits and P0/P5 carriers are separate; no multiplier applied here.',
            'Require full parent/child storage/work quote and grant before fixture entry; no execution authority here.'],
        'native_runtime':'paused','whole_host_funded':False,'healthy_cleanup':False,'OTA_GA':False})
    write('input-custody.json',{'schema':1,'files':inputs})
    write('derivation-results.json',{'schema':1,'checks':sum(not c.startswith('current:') for c in checks),'all_passed':True,
        'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'source_evidence_spans':len(evidence),
        'returned_payload':result['returned_payload'],'during_entry_per_visit':result['during_entry_per_visit'],
        'no_compiler_or_product_execution':True})
    print(json.dumps({'checks':len(checks),'source_spans':len(evidence),'returned_payload':result['returned_payload'],
        'during_entry_per_visit':result['during_entry_per_visit'],'status':'passed'},sort_keys=True))

if __name__=='__main__':build()
