from pathlib import Path
import hashlib, json, shutil, difflib, datetime

H=Path(__file__).resolve().parent
R=H.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(v): return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def write(n,v): (H/n).write_bytes(enc(v))
manifest_path=R/'verification/swift-cache-resident-index/candidate-source-manifest.json'
assert sha(manifest_path)=='02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d'
original=json.loads(manifest_path.read_text())
assert len(original)==132
assert all(sha(R/'vm'/n)==s for n,s in original.items())
S=H/'owned-scratch'
assert not S.exists()
for kind in ('baseline','grouped'):
    for n in original:
        dst=S/kind/n; dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(R/'vm'/n,dst)
    (S/'targets'/kind).mkdir(parents=True)
(S/'tmp').mkdir()
for n in ('AGENTS.md','docs/swift-cache-resident-index-contract.md','docs/swift-cache-resident-index-integration.md','docs/swift-cache-resident-index-review.md','verification/swift-exact-reactor-after-resident-index/result.md','verification/swift-exact-reactor-after-resident-index/ticket-headroom-observation.md'):
    dst=H/'inputs'/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/n,dst)
write('input-source-manifest.json',original)
p=S/'grouped/src/experimental_swift_reactor/cache.rs'
before=p.read_text(); t=before
def replace(a,b,count=1):
    global t
    assert t.count(a)==count,(a,t.count(a),count)
    t=t.replace(a,b)
replace('buffers: [Option<ReservationTicket>; 4]','buffers: [Option<ReservationTicket>; 3]',2)
replace('''        if let Some(ticket) = self.buffers[3].take() {
            let _ = control.drop_reserved(take(&mut self.index), ticket);
        }''','''        // The header admitted the index payload before its allocation. Keep it
        // charged while the entire Vec and every transfer are destroyed.
        drop(take(&mut self.index));''')
replace('    exclusive.checked_add(cleanup)\n','    exclusive.checked_add(cleanup)?.checked_add(RESIDENT_INDEX_BYTES)\n')
# The above ? is not const-stable on this toolchain: use the existing explicit style.
replace('    exclusive.checked_add(cleanup)?.checked_add(RESIDENT_INDEX_BYTES)\n','''    let Some(header) = exclusive.checked_add(cleanup) else { return None; };
    header.checked_add(RESIDENT_INDEX_BYTES)
''')
replace('''        if let Some(ticket) = cache.buffers[3].take() {
            capture(
                &mut failure,
                control.drop_reserved_with_wasi(
                    take(&mut cache.index),
                    ticket,
                    wasi.map(AccountedWasi::usage),
                ),
            );
        }''','''        // Destroy index payload before the header moves into its cleanup tail.
        drop(take(&mut cache.index));''')
replace('        partial.buffers[3] = Some(self.control.admit(RESIDENT_INDEX_BYTES)?);\n','')
replace('''            + PATCH_CAPACITY * size_of::<decode::Patch>()
            + RESIDENT_INDEX_BYTES;''','''            + PATCH_CAPACITY * size_of::<decode::Patch>();''')
p.write_text(t)
(H/'grouped-prototype.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),t.splitlines(True),fromfile='a/src/experimental_swift_reactor/cache.rs',tofile='b/src/experimental_swift_reactor/cache.rs')))
for kind in ('baseline','grouped'):
    # Common controls appended to copied actual-cache tests only.
    p=S/kind/'src/experimental_swift_reactor/cache_tests.rs'
    tests=p.read_text()
    if kind=='grouped':
        old='cache_header_bytes().unwrap() + expected'
        assert tests.count(old)==1
        tests=tests.replace(old,'cache_header_bytes().unwrap() + expected - 192')
    tests+='\n'+(H/'controls.rs').read_text()
    p.write_text(tests)
    # Layout-only array alternatives: no array value is initialized or executed.
    p=S/kind/'src/experimental_swift_reactor/cache.rs'
    source=p.read_text()
    owner=source[source.index('pub(crate) struct SwiftFunctionCache {'):source.index('/// A wrapper exists only')]
    owner=owner.replace('SwiftFunctionCache','InlineLayoutOwner').replace('index: Vec<u8>','index: [u8; RESIDENT_INDEX_BYTES]').replace('buffers: [Option<ReservationTicket>; 4]','buffers: [Option<ReservationTicket>; 3]')
    partial=source[source.index('struct Partial {'):source.index('impl Partial {')]
    partial=partial.replace('struct Partial','struct InlineLayoutPartial').replace('index: Vec<u8>','index: Option<[u8; RESIDENT_INDEX_BYTES]>').replace('buffers: [Option<ReservationTicket>; 4]','buffers: [Option<ReservationTicket>; 3]')
    cstart=source.index('const fn compute_cache_cleanup_temporary_bytes()')
    cend=source.index('const fn compute_cache_operation_bytes()')
    formula=source[cstart:cend]
    formula=formula.replace('compute_cache_cleanup_temporary_bytes','inline_layout_cleanup').replace('compute_cache_header_bytes','inline_layout_header').replace('compute_cache_construction_bytes','inline_layout_construction')
    formula=formula.replace('SwiftFunctionCache','InlineLayoutOwner').replace('size_of::<Partial>()','size_of::<InlineLayoutPartial>()').replace('size_of::<ConstructionReturnSlot>()','size_of::<Option<Result<InlineLayoutOwner, CacheConstructionFailure>>>()')
    # Inline array bytes are inside each measured owner/return, not extra heap payload.
    formula=formula.replace('''    let Some(header) = exclusive.checked_add(cleanup) else { return None; };
    header.checked_add(RESIDENT_INDEX_BYTES)''','''    exclusive.checked_add(cleanup)''')
    # No Vec index transfer objects exist in the array alternative; include array transfers.
    formula=formula.replace('size_of::<Vec<u8>>()','size_of::<[u8; RESIDENT_INDEX_BYTES]>()')
    extra='\n#[cfg(test)] mod diagnosis_layout {\nuse super::*;\n'+owner+partial+formula+'''
pub(super) fn report() {
println!("DIAG_LAYOUT actual_owner={} actual_partial={} actual_cleanup={} actual_header={} actual_construction={} actual_operation={} actual_foundation={} inline_owner={} inline_partial={} inline_cleanup_min={} inline_header_min={} inline_construction_min={}", size_of::<SwiftFunctionCache>(),size_of::<Partial>(),cache_cleanup_temporary_bytes().unwrap(),cache_header_bytes().unwrap(),cache_construction_bytes().unwrap(),cache_operation_bytes().unwrap(),foundation_construction_bytes().unwrap(),size_of::<InlineLayoutOwner>(),size_of::<InlineLayoutPartial>(),inline_layout_cleanup().unwrap(),inline_layout_header().unwrap(),inline_layout_construction().unwrap());
}
}
#[cfg(test)] pub(super) fn diagnosis_layout_report() {diagnosis_layout::report();}
#[cfg(test)] pub(super) fn diagnosis_tail_cache_reserved(tail:&CacheCleanupTail<'_>) -> usize { tail.control.usage(tail.wasi.map(AccountedWasi::usage)).reservations.cache.current }
'''
    p.write_text(source+extra)
    current={n:sha(S/kind/n) for n in original}
    write(kind+'-prototype-source-manifest.json',current)
write('preparation.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputCommitReportedBySelectedPacket':'be472ce6424a691de5673e3438d2768264827d23','inputClosureSHA256':sha(manifest_path),'liveMembersVerified':132,'liveEdits':False,'gitCommands':False,'fullTargetOrNative':False,'prototypeOnly':True,'groupedPatchSHA256':sha(H/'grouped-prototype.patch')})
print('Prepared two copied 132-file closures; live source unchanged.')
