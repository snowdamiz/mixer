"""Finite source/interface/requested-byte contracts; never runtime authority.

Private std implementation, lowering, allocator, kernel, retry and CPU work are
outside this inherited logical unit. Callback-bearing errors are refused.
"""
from __future__ import annotations

U64 = (1 << 64) - 1
SOURCE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
RUST = 'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'

class Refused(ValueError): pass

def natural(n):
    if type(n) is not int or not 0 <= n <= U64: raise Refused('not-u64')
    return n

def positive(n):
    if natural(n) == 0: raise Refused('required-positive')
    return n

def add(*ns):
    result = 0
    for n in ns:
        if natural(n) > U64-result: raise Refused('add-overflow')
        result += n
    return result

def mul(a,b):
    natural(a);natural(b)
    if a and b > U64//a: raise Refused('mul-overflow')
    return a*b

def identity(binding):
    if binding != {'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,
                   'rust_revision':RUST,'target':'aarch64-apple-darwin',
                   'allocator':'alloc::alloc::Global','route':'source146-owned-file-route'}:
        raise Refused('unqualified-source-target-allocator-route')

def record_price(records, backing=0):
    """One unit per named boundary event; native fields are explicit byte slots.

    Branch union, including abort alternatives, deliberately overcovers a visit.
    These records do not count private implementation instructions or stack.
    """
    if not records: raise Refused('empty-interface')
    names=set();native=natural(backing)
    for r in records:
        if set(r) != {'event','native_fields'} or r['event'] in names: raise Refused('bad-event')
        names.add(r['event'])
        for size in r['native_fields'].values(): native=add(native,positive(size))
    return {'interface_work':positive(len(records)), 'native_resource_backing':positive(native)}

def plain_vector(bound):
    if set(bound) != {'max_requested_bytes','max_live_elements','element_nodes'}:
        raise Refused('incomplete-vector-bound')
    b=natural(bound['max_requested_bytes']);l=natural(bound['max_live_elements']);n=positive(bound['element_nodes'])
    # Every selected concrete T is nonzero-sized. L*size(T) <= B and size(T)>=1.
    if l>b: raise Refused('live-exceeds-requested-byte-bound')
    # Source entry, element-slice interface, RawVec entry, optional deallocation.
    # Native descriptor consists of pointer/size/alignment, three 64-bit fields.
    # N*B bounds sum over all live element structural native surcharges, even
    # without selecting an element layout: sum(size(T)) <= actual backing <= B.
    return {'interface_work':add(4,mul(n,l)),
            'native_resource_backing':add(24,b,mul(n,b))}

def byte_box(bound):
    if set(bound) != {'max_requested_bytes','max_live_elements'}: raise Refused('incomplete-box-bound')
    b=natural(bound['max_requested_bytes']);l=natural(bound['max_live_elements'])
    if l>b: raise Refused('box-live-exceeds-bytes')
    # Box entry, slice interface, optional deallocate; u8 source nodes=1.
    return {'interface_work':add(3,l),'native_resource_backing':add(24,b,b)}

def source_ceiling_cuts(contract,binding,error_provenance):
    identity(binding)
    if error_provenance != 'closed-file-os-or-static-message': raise Refused('unbounded-error-callback')
    if contract['binding'] != binding: raise Refused('contract-binding')
    cuts={}
    for name in ('File','Arc<AtomicBool>','Error'):
        c=contract['interfaces'][name]
        cuts[name]=record_price(c['records'],c['requested_backing_bytes'])
    for name,bound in contract['vectors'].items():
        if name != 'Vec<SwiftSlot>': cuts[name]=plain_vector(bound)
    cuts['Box<[u8]>']=byte_box(contract['byte_box'])
    slots=contract['vectors']['Vec<SwiftSlot>']
    if slots != {'max_requested_bytes':8704,'max_live_elements':64,'element_nodes':19}:
        raise Refused('unqualified-slot-bound')
    cuts['Vec<SwiftSlot>']={'interface_work':4,'native_resource_backing':24+8704,
        'max_live_elements':64,'element_inline_bytes':136,
        'element_cuts':{k:cuts[k] for k in ('Vec<Type>','Vec<DecodedInstruction>','Vec<u32>')}}
    return cuts

def evaluate_row(row,cuts):
    expected=set(row['resource_frontiers'])
    if set(cuts)!=expected: raise Refused('missing-or-unknown-cut')
    result=mul(positive(row['structural_occurrence_allowance']),add(1,positive(row['inline_bytes'])))
    for name,count in row['resource_frontiers'].items():
        c=cuts[name];dynamic=row.get('dynamic_resource_elements',{}).get(name)
        fields={'interface_work','native_resource_backing'}
        if dynamic is not None: fields|={'max_live_elements','element_inline_bytes','element_cuts'}
        if set(c)!=fields: raise Refused('incomplete-cut')
        part=add(positive(c['interface_work']),positive(c['native_resource_backing']))
        if dynamic is not None:
            if c['element_inline_bytes']!=136 or dynamic['inline_bytes']!=136: raise Refused('wrong-SwiftSlot-layout')
            if c['max_live_elements']!=64: raise Refused('wrong-slot-live-bound')
            part=add(part,mul(64,evaluate_row(dynamic,c['element_cuts'])))
        result=add(result,mul(positive(count),part))
    return positive(result)

def components(rows,cuts,entry_types):
    evaluated={row['type']:evaluate_row(row,{n:cuts[n] for n in row['resource_frontiers']}) for row in rows}
    if set(entry_types)!={'File','Option<File>','ReturnedLoaderFilesV1','SetupOutcomeV1','SelectedValidatedProfileV1','LoaderFailureV1','Cancellation'}:
        raise Refused('wrong-entry-domain')
    return {'returned_payload':evaluated['OwnedFixtureOutcomeV1'],
            'during_entry_per_visit':max(evaluated[n] for n in entry_types),
            'child53_multiplier_applied':False,'rows':evaluated}
