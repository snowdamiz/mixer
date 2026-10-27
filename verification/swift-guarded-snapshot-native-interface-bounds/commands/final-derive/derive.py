"""Rehash frozen inputs and derive interfaces without compiler/native execution."""
import hashlib,json,sys,shutil
from pathlib import Path
from model import *
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V=ROOT/'verification'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())
def encoded(j): return (json.dumps(j,indent=2,sort_keys=True)+'\n').encode()
def save(name,j,check):
    p=HERE/name;d=encoded(j)
    if check: assert p.read_bytes()==d,('changed-derived-output',name)
    else:p.write_bytes(d)

def record(event,fixed,m=0):return {'event':event,'fixed_bytes':fixed,'path_byte_multiplicity':m}

def derive():
    # No reference to the concurrently-owned resource-binary-correspondence lane.
    cust=[]
    def bind(p,expected=None):
        p=ROOT/p if not p.is_absolute() else p
        h=sha(p)
        if expected:assert h==expected,(str(p),h)
        cust.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':h})
        return p
    accepts={
      'guarded-snapshot-child-entry-cost-host-acceptance.json':'2efea9e81115620c4c029267ffdf49457e4d1ca6ffa753051eeed3a1a2336ead',
      'guarded-snapshot-host-storage-host-acceptance.json':'9862bbe187dea2e1c6999218604ec43db3d3c9bc28d4fd815615d81dd98df432',
      'guarded-snapshot-resource-cost-host-acceptance.json':'854c90f7824676cec2483571d5de4fce27965758e7e583186fa2361d965a118f'}
    for name,h in accepts.items():bind(Path('verification/swift-semantic-adapter-root-review')/name,h)
    map_p=bind(Path('verification/swift-guarded-snapshot-loader-work-source146/source-reference-map.json'))
    source=load(map_p)
    assert len(source['members'])==146
    for r in source['members']:
        p=bind(Path(r['source']),r['sha256']);assert p.stat().st_size==r['bytes']
    # Actual source tree identity is accepted data, never reconstructed from a
    # different map delimiter or substituted with a filesystem/Git snapshot.
    sm=load(bind(Path('verification/swift-guarded-snapshot-host-composition/source-manifest.json')))
    assert sm['tree_sha256']==SOURCE and sm['member_count']==146
    assert [{k:r[k] for k in ['path','bytes','sha256']} for r in source['members']]==sm['members']
    host=load(bind(Path('verification/swift-guarded-snapshot-host-composition/host-support-manifest.json')))
    assert host['member_count']==11 and host['tree_sha256']==HOST
    for r in host['members']:
        bind(Path('verification/swift-real-profile-loader-binding/host')/r['path'],r['sha256'])
    packets=['swift-guarded-snapshot-child-entry-cost','swift-guarded-snapshot-host-storage-composition',
      'swift-guarded-snapshot-host-storage-composition-independent','swift-guarded-snapshot-resource-cost',
      'swift-guarded-snapshot-stdlib-resource-source','swift-guarded-snapshot-payload-destruction-cost']
    packet_rows=[]
    for name in packets:
        p=bind(Path('verification')/name/'seal.json');seal=load(p)
        for r in seal['members']:
            q=p.parent/r['path'];assert sha(q)==r['sha256'] and q.stat().st_size==r['bytes']
        packet_rows.append({'path':str(p.parent.relative_to(ROOT)),'seal_sha256':sha(p),'members_verified':len(seal['members'])})
    resource=load(bind(Path('verification/swift-guarded-snapshot-resource-cost/contract.json')))
    inventory=load(bind(Path('verification/swift-guarded-snapshot-payload-destruction-cost/inventory.json')))
    rows=load(bind(Path('verification/swift-guarded-snapshot-resource-cost/rows.json')))
    internal=load(bind(Path('verification/swift-guarded-snapshot-resource-cost/internal-rows.json')))
    storage=load(bind(Path('verification/swift-guarded-snapshot-host-storage-composition/results.json')))
    assert resource['binding']['source_tree_sha256']==SOURCE and resource['binding']['host_tree_sha256']==HOST
    assert resource['Error_provenance']=='closed-file-os-or-static-message'
    # Rehash each new official source using exact commit or Cargo.lock checksum.
    fetch=load(HERE/'fetch-receipt.json');assert fetch['rust_revision']==RUST
    for r in fetch['files']:
        assert r['status']==200 and f'/{RUST}/' in r['url']
        assert sha(ROOT/r['path'])==r['sha256']
    libc=load(HERE/'libc-fetch-receipt.json')
    assert libc['archive_sha256']=='b5b646652bf6661599e1da8901b3b9522896f01e736bad5f723fe7a3a27f899d'
    for r in libc['members']:assert sha(ROOT/r['path'])==r['sha256']
    lock=(HERE/'official-source/Cargo.lock').read_text()
    assert 'name = "libc"\nversion = "0.2.183"' in lock and libc['archive_sha256'] in lock

    contract={'schema':1,'binding':resource['binding'],
      'logical_unit':resource['logical_unit'],
      'private_std_syscall_retry_CPU_kernel_stack_RSS_bounded':False,
      'actual_root_paths_binding_pointees_selected':False,'whole_host_grant':False,
      'open_records':[
        record('File/OpenOptions public result and borrowed inputs',36),
        record('Path/OsStr encoded byte slice interface',16),
        record('length/stack-threshold dispatch operands',17),
        record('short branch fixed MaybeUninit byte array interface',384),
        record('path conversion copied input/output byte extents',0,2),
        record('terminating zero write',1),
        record('CStr validation slice and full terminator-inclusive extent',17,1),
        record('long branch Global pointer/layout and requested byte extent',25,1),
        record('long branch Vec then Box representation interfaces',40),
        record('CStr borrowed native argument interface',16),
        record('valid fixed access/create/flags/promoted-mode operands',24),
        record('one public native open request including path extent',21,1),
        record('errno pointer/raw code/closed Error result',20),
        record('CString/Box drop/deallocation existing backing interface',57,1),
        record('NulError Vec/index/drop/deallocation existing backing interface',57,1),
        record('successful File inline result',4),
        record('static NUL diagnostic borrowed reference',16)],
      'error_records':[record('errno_location borrowed pointer',8),record('errno i32 observation',4),record('closed Error result representation',8)],
      'path_branch_threshold':384,'setup_roles':['input','build','session','rows','snapshot'],
      'setup_options':['read-only','read-only','read-only','write-create_new','write-create_new'],
      'setup_truncate':False,'executable_open_separate':True,
      'closed_error_owned_backing_bytes':0,'file_owned_extra_backing_bytes':0,
      'all_transitive_payload_drop_extra_requested_heap_bytes':0,
      'loader_native_helpers_extra_requested_heap_bytes':0,
      'cstring_allocation_failure':'Global/with_capacity error handler, not returned io::Error; private oom/panic runtime outside unit',
      'valid_drop_conditions':['actual closed source146 ownership graph','Global allocator',
        'Arc<AtomicBool> created by Default/Clone only','no arbitrary Error callbacks',
        'plain element graph and exact nested SwiftSlot frontiers','no product/native reentrant callbacks']}

    # libc s! uses repr(C). Darwin stat aliases are fixed primitive declarations;
    # the native output is one 144-byte inline C object, no allocation request.
    stat_fields=[('dev',4,4),('mode',2,2),('nlink',2,2),('ino',8,8),('uid',4,4),('gid',4,4),('rdev',4,4),
      *[(n,8,8) for n in ['atime','atime_nsec','mtime','mtime_nsec','ctime','ctime_nsec','birthtime','birthtime_nsec','size','blocks']],
      ('blksize',4,4),('flags',4,4),('gen',4,4),('lspare',4,4),('qspare',16,8)]
    offset=0;stat=[]
    for n,s,a in stat_fields:
        offset=(offset+a-1)//a*a;stat.append({'field':n,'bytes':s,'alignment':a,'offset':offset});offset+=s
    stat_size=(offset+7)//8*8;assert stat_size==144
    native=[record('File read fd/buffer-pointer/count/ssize result',28),
      record('File fstat fd/output-pointer/result/stat output',4+8+4+stat_size),
      record('File lseek fd/i64 offset/whence/i64 result',24),
      record('CC_SHA256 input/u32len/digest-pointer/result-pointer/digest output',60),
      record('NSGetArgc returned pointer and observed c_int',12),
      record('NSGetArgv returned pointer slot',8),record('NSGetEnviron returned pointer slot',8),
      record('NSGetExecutablePath pointers/u32 size/result/caller byte buffer',4120),
      record('getcwd pointer/usize/result-pointer/caller byte buffer',4120),
      record('closed Error descriptor/native dispatch allowance',32)]
    native_price=records_price(native)
    # Requested heap is zero. The positive frozen-storage adapter terms below
    # are deliberately separate interface operand envelopes, never heap claims.
    rf={k:sum(sum(r['native_fields'].values()) for r in v['records']) for k,v in resource['interfaces'].items()}
    assert rf=={'Arc<AtomicBool>':149,'Error':32,'File':73}
    allrows=rows['rows'] if isinstance(rows,dict) else rows
    allrows=allrows+internal['rows']
    drop=[]
    def native_drop(row):
        total=natural(row['inline_bytes'])
        for name,count in row['resource_frontiers'].items():
            closed_extra_requests('source146-owned-file-route',{name:count})
            unit=rf[name] if name in rf else 24
            if name=='Vec<SwiftSlot>':
                d=row['dynamic_resource_elements'][name]
                assert d['inline_bytes']==136 and d['resource_frontiers']=={'Vec<DecodedInstruction>':1,'Vec<Type>':1,'Vec<u32>':1}
                unit=add(unit,mul(64,native_drop(d)))
            total=add(total,mul(count,unit))
        return total
    for row in allrows:
        closed_extra_requests('source146-owned-file-route',row['resource_frontiers'])
        drop.append({'type':row['type'],'native_interface_operand_union_bytes':native_drop(row),
          'owned_backing_deallocated_not_allocated':True,'extra_requested_heap_bytes':0,
          'resource_frontiers':row['resource_frontiers']})
    uniform=max(r['native_interface_operand_union_bytes'] for r in drop)
    fixed_inline=add(storage['caller_inline_bytes'],storage['leaf_inline_bytes'],storage['loader_inline_bytes'],storage['full_product_retention'])
    # Every simultaneous owned Error occupies eight distinct source-object
    # bytes. Plain dynamic elements, byte Boxes and AtomicBool add no Errors.
    # Summing complete frame unions and retained named storage double-counts
    # overlaps conservatively. One standard helper original can be in transfer.
    error_count=add(fixed_inline//8,1)
    amendments={'schema':1,'status':'source-backed-positive-interface-envelope-amendment-candidate',
      'changes_frozen_adapter_implementation':False,
      'reason':'frozen positive-only storage cuts cannot represent source-proven zero extra requests; retain positive explicit native operand envelopes without calling them heap',
      'file_resource_backing_each':rf['File'],'error_backing_each':rf['Error'],
      'loader_native_temporaries':native_price['native_operand_and_request_bytes'],
      'all_payload_destructor_temporaries':uniform,
      'exact_extra_requested_heap_bytes_for_each_of_those_four_interfaces':0,
      'error_owner_count':error_count,
      'error_count_derivation':{'complete_fixed_inline_plus_retention_bytes':fixed_inline,
        'compiled_Error_bytes':8,'native_helper_originals_additional':1,'formula':'floor(complete_fixed_inline_plus_retention_bytes/8)+1',
        'future_outer_parent_foreign_Error_not_included':True},
      'uniform_drop_rows':len(drop),'uniform_drop_scope':'all accepted returned/entry/leaf/constructor typed bodies and complete nested SwiftSlot elements',
      'not_physical_stack_or_private_native_frame':True,'already_owned_backing_is_not_extra_allocation':True,
      'P0_binding_minimum':512,
      'P0_actual_data_rule':'five actual encoded lengths n_i and independently bound backing B_i>=n_i; whole binding extent>=512; complete typed immutable identity/diagnostic pointee roster with exact extents/backing; no selected paths or generated identity',
      'executable_path_rule':'observer NUL position gives actual 1<=e<=4095 on this source; CString requested backing e+1 if e>=384; frozen conservative interface4097 remains safe, no setup4096 cap',
      'five_setup_conversion_rule':'max(384,n_i+1) explicit native interface envelope; extra requested heap is zero for n_i<384, n_i+1 otherwise',
      'selection_and_compiled_correspondence_pending':True,'whole_host_grant':False}
    # Every source excerpt is a checked verbatim region bound to entire file SHA.
    sources=[]
    def excerpt(rel,needle,after,claim):
        p=ROOT/rel;lines=p.read_text().splitlines(keepends=True)
        matches=[i for i,line in enumerate(lines) if needle in line];assert len(matches)==1,(rel,needle,matches)
        i=matches[0];block=''.join(lines[i:i+after]);assert block
        sources.append({'claim':claim,'path':rel,'file_sha256':sha(p),'first_line':i+1,'last_line':i+after,
          'excerpt_sha256':hashlib.sha256(block.encode()).hexdigest(),'source':block})
    entries=[
      ('verification/swift-guarded-snapshot-resource-cost/official-source/library/std/src/sys/helpers/small_c_string.rs','const MAX_STACK_ALLOCATION: usize = 384;',59,'path dispatch, stack scratch, interior NUL, allocating CString'),
      ('verification/swift-guarded-snapshot-native-interface-bounds/official-source/library/alloc/src/ffi/c_str.rs','fn spec_new_impl_bytes(bytes:',40,'borrowed-byte specialization allocates n+1 before validation'),
      ('verification/swift-guarded-snapshot-native-interface-bounds/official-source/library/alloc/src/ffi/c_str.rs','unsafe fn _from_vec_unchecked(mut',5,'reserve1 fits exact n+1 capacity; push NUL; Box conversion'),
      ('verification/swift-guarded-snapshot-native-interface-bounds/official-source/library/alloc/src/ffi/c_str.rs','impl Drop for CString {',8,'CString drop writes already owned first byte, no allocation'),
      ('verification/swift-guarded-snapshot-stdlib-resource-source/official-source/library/alloc/src/alloc.rs','fn alloc_impl_runtime(layout:',31,'Global returns requested size; deallocation does not allocate'),
      ('verification/swift-guarded-snapshot-stdlib-resource-source/official-source/library/alloc/src/vec/mod.rs','    pub fn shrink_to_fit(&mut self)',9,'equal capacity avoids shrink allocation'),
      ('verification/swift-guarded-snapshot-stdlib-resource-source/official-source/library/std/src/sys/fs/unix.rs','    fn get_access_mode(&self)',47,'actual two valid fixed option combinations exclude custom errors'),
      ('verification/swift-guarded-snapshot-stdlib-resource-source/official-source/library/std/src/sys/fs/unix.rs','    pub fn open(path: &Path',35,'public open request, cvt_r, inline fstat output'),
      ('verification/swift-guarded-snapshot-resource-cost/official-source/library/std/src/sys/pal/unix/mod.rs','pub fn cvt_r<T, F>',15,'private EINTR loop has no finite syscall attempt bound'),
      ('verification/swift-guarded-snapshot-native-interface-bounds/official-source/library/std/src/sys/io/error/unix.rs','    pub safe fn errno_location()',15,'Apple errno is borrowed __error pointer to c_int'),
      ('verification/swift-guarded-snapshot-native-interface-bounds/official-libc/src/unix/bsd/apple/mod.rs','    pub struct stat {',25,'complete fixed Darwin stat fields'),
      ('verification/swift-guarded-snapshot-native-interface-bounds/official-libc/src/macros.rs','macro_rules! s {',18,'libc s! objects use repr(C)'),
      ('verification/swift-guarded-snapshot-host-composition/overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs','    fn setup_files_once_v1(',27,'actual three input and two create_new output opens, retained failures'),
      ('verification/swift-guarded-snapshot-host-composition/overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs','    fn run_prepaid_fixture_v1(',37,'actual File/Error/Cancellation ownership path'),
      ('verification/swift-guarded-snapshot-host-composition/overlay/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs','        fn CC_SHA256(',8,'native hash/process helper declarations'),
      ('verification/swift-guarded-snapshot-host-composition/overlay/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs','        // Caller-provided4096-byte buffers',63,'fixed caller byte buffers; executable path first NUL and nonempty absolute checks'),
      ('verification/swift-guarded-snapshot-native-interface-bounds/official-source/library/std/src/sys/os_str/bytes.rs','    pub fn as_encoded_bytes(&self)',4,'Unix OsStr encoded bytes are unchanged byte slice')]
    for args in entries:excerpt(*args)
    components=load(bind(Path('verification/swift-guarded-snapshot-resource-cost/components.json')))
    assert components['during_entry_per_visit']==1210256815
    details={'schema':1,'stat_repr_C_fields':stat,'stat_bytes':stat_size,
      'loader_native_records':native,'loader_native_records_price':native_price,
      'payload_drop_rows':drop,'uniform_native_operand_envelope':uniform,
      'entry_destruction_work_per_visit':components['during_entry_per_visit'],
      'entry_work_expression':'123809 + 7*sum(five_actual_encoded_lengths) + 53*1210256815',
      'entry_work_folded_constant':add(123809,mul(53,1210256815)),
      'entry_work_expression_folded':'64143735004 + 7*sum(five_actual_encoded_lengths)',
      'Error_bytes':8,'File_bytes':4,'errno_c_int_bytes':4,
      'Error_representation_evidence':'accepted exact source146 compiler layouts; Os/static closed tags, no custom callbacks',
      'no_panic_hook_or_allocator_oom_failure_handler_bound':True,
      'fresh_allocation_partial_failure':'long CString request n+1 either succeeds or invokes Global/with_capacity failure handler; no returned io::Error/allocation-refusal claim; NUL failure occurs after successful allocation and frees NulError Vec; short NUL uses static error without allocation',
      'scope':'public source/interface operands and explicit requested bytes; no root selection or physical heap/stack/runtime proof'}
    return {'schema':1,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'rust_revision':RUST,
      'files':cust,'frozen_packets':packet_rows},contract,{'schema':1,'entries':sources},amendments,details

def main():
    check='--check-only' in sys.argv
    custody,contract,sources,amendments,details=derive()
    save('input-custody.json',custody,check);save('contract.json',contract,check)
    save('source-evidence.json',sources,check);save('storage-interface-amendment.json',amendments,check)
    save('interface-derivation.json',details,check)
    print(json.dumps({'checked':check,'source_members':146,'official_Rust_files':9,
      'open_formula':{'events':len(contract['open_records']),
      'fixed_native_bytes':sum(r['fixed_bytes'] for r in contract['open_records']),
      'path_byte_multiplicity':sum(r['path_byte_multiplicity'] for r in contract['open_records'])},
      'positive_interface_envelopes':{k:amendments[k] for k in ['file_resource_backing_each','error_backing_each','loader_native_temporaries','all_payload_destructor_temporaries','error_owner_count']},
      'all_passed':True},sort_keys=True))
if __name__=='__main__':main()
