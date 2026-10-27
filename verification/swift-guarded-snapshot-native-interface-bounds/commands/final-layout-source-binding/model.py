"""Source146 public native/requested-byte interfaces, never execution authority.

All extents are logical operands or explicit Global requests. Private std/native
implementation, retry counts, allocator overhead, physical stack, CPU and RSS are
outside the unit. Actual immutable root data still needs a custody binding.
"""
from dataclasses import dataclass
import hashlib,json

U64 = (1 << 64) - 1
ISIZE_MAX = (1 << 63) - 1
SOURCE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
RUST = 'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
CONTRACT_SHA256 = 'c4f20dd50cfcf795d2b7ebf11dd90543c1acb546223f50634d5b2e8abef3fef2'

class Refused(ValueError): pass

def natural(n):
    if type(n) is not int or not 0 <= n <= U64: raise Refused('not-u64')
    return n

def positive(n):
    if not natural(n): raise Refused('not-positive')
    return n

def add(*ns):
    v = 0
    for n in ns:
        if natural(n) > U64-v: raise Refused('add-overflow')
        v += n
    return v

def mul(a,b):
    natural(a); natural(b)
    if a and b > U64//a: raise Refused('mul-overflow')
    return a*b

def evidence(s):
    if type(s) is not str or not s.strip(): raise Refused('missing-custody-obligation')
    return s

@dataclass(frozen=True)
class PathExtent:
    encoded_bytes: int
    p0_backing_bytes: int
    custody: str
    def checked(self):
        n = natural(self.encoded_bytes); b = natural(self.p0_backing_bytes)
        evidence(self.custody)
        if b < n: raise Refused('p0-backing-understates-encoded-path')
        # The allocating CString success/failure contract requires representable
        # Layout::array<u8>(n+1). The overflow/oom handler is not an io::Error.
        if n >= ISIZE_MAX: raise Refused('cstring-layout-overflow-outside-return-contract')
        return n,b

def records_price(records, n=0):
    natural(n)
    total=0; names=set()
    for r in records:
        if set(r) != {'event','fixed_bytes','path_byte_multiplicity'}: raise Refused('bad-record')
        if r['event'] in names: raise Refused('duplicate-record')
        names.add(r['event'])
        total=add(total,natural(r['fixed_bytes']),mul(n,natural(r['path_byte_multiplicity'])))
    return {'interface_events':positive(len(records)), 'native_operand_and_request_bytes':positive(total),
            'price':add(len(records),total)}

def path_bounds(path, contract):
    raw=(json.dumps(contract,indent=2,sort_keys=True)+'\n').encode()
    if hashlib.sha256(raw).hexdigest()!=CONTRACT_SHA256: raise Refused('unbound-native-contract')
    if type(path) is not PathExtent: raise Refused('typed-path-required')
    n,b=path.checked()
    p=records_price(contract['open_records'],n)
    return dict(p,encoded_bytes=n,p0_backing_bytes=b,native_path_span=add(n,1),
                heap_allocation_requests_max=0 if n<384 else 1,
                extra_requested_heap_bytes_max=0 if n<384 else add(n,1),
                short_path_inline_scratch_bytes=384 if n<384 else 0,
                # Frozen adapter requires a positive path temporary term >=n+1.
                # This explicit interface envelope includes stack scratch as an
                # operand extent, not measured physical stack or extra heap.
                positive_conversion_interface_envelope=max(384,add(n,1)),
                semantic_open_requests_max=1,
                finite_private_open_syscall_attempt_bound=False)

def path_case(raw):
    """Pure source-case classifier. It opens no file and calls no native API."""
    if type(raw) is not bytes: raise Refused('raw-unix-bytes-required')
    n=len(raw)
    if n>=ISIZE_MAX: raise Refused('cstring-layout-overflow-outside-return-contract')
    nul=b'\0' in raw
    return {'encoded_bytes':n,'utf8_required':False,'allocation_before_nul_validation':n>=384,
            'heap_request_bytes':n+1 if n>=384 else 0,
            'semantic_open_requests':0 if nul else 1,
            'conversion_result':'static-NUL-error' if nul else 'borrowed-CStr-to-open',
            'empty_path_native_result':'OS-decides' if not raw else None,
            'retained_error_heap_bytes':0}

@dataclass(frozen=True)
class Pointee:
    name: str
    extent: int
    backing_extent: int
    custody: str
    def checked(self):
        evidence(self.name); evidence(self.custody)
        n=natural(self.extent);b=natural(self.backing_extent)
        if b<n: raise Refused('pointee-backing-understated')
        return b

def p0_bounds(paths,binding_extent,pointees):
    if type(paths) is not tuple or len(paths)!=5: raise Refused('five-setup-paths-required')
    ps=[p.checked() if type(p) is PathExtent else (_ for _ in ()).throw(Refused('typed-path-required')) for p in paths]
    if natural(binding_extent)<512: raise Refused('complete-binding-object-required')
    if type(pointees) is not tuple or not pointees: raise Refused('complete-pointee-roster-required')
    if any(type(p) is not Pointee for p in pointees): raise Refused('typed-pointee-required')
    if len({p.name for p in pointees})!=len(pointees): raise Refused('duplicate-pointee')
    return {'path_p0_backing_bytes':add(*(b for n,b in ps)),
            'reviewed_binding_object_bytes':binding_extent,
            'identity_diagnostic_pointee_backing_bytes':add(*(p.checked() for p in pointees))}

def child_entry(paths,contract,entry_destructor_price):
    if type(paths) is not tuple or len(paths)!=5: raise Refused('five-setup-paths-required')
    opens=[path_bounds(p,contract) for p in paths]
    err=records_price(contract['error_records'])
    return {'source_core':119922,'cancellation_requested_backing':24,
            'five_native_open_prices':[p['price'] for p in opens],
            'error_native_price':err['price'],
            'entry_destructor_price':positive(entry_destructor_price),
            'entry_destructor_visits':53,
            'entry_price':add(119922,24,*(p['price'] for p in opens),err['price'],mul(53,entry_destructor_price)),
            'whole_host_grant':False}

def closed_extra_requests(route,frontiers):
    if route!='source146-owned-file-route': raise Refused('foreign-error-or-resource-route')
    allowed={'File','Error','Arc<AtomicBool>','Box<[u8]>','Vec<SwiftSlot>','Vec<DecodedInstruction>',
             'Vec<Type>','Vec<u32>','Vec<Export>','Vec<Function>','Vec<Global>','Vec<Import>',
             'Vec<Segment>','Vec<Signature>','Vec<PinRecord>','Vec<Patch>','Vec<Option<ScanPlan>>','Vec<u8>'}
    if type(frontiers) is not dict or set(frontiers)-allowed: raise Refused('unclosed-transitive-resource')
    for count in frontiers.values(): positive(count)
    return {'extra_allocation_requests':0,'extra_requested_heap_bytes':0,
            'already_owned_deallocation_backing_is_extra':False,
            'private_allocator_native_or_panic_runtime_bounded':False}
