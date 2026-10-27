#!/usr/bin/env python3
"""Independent finite source/interface audit. No compiler or product execution.

The scanner is deliberately limited to these rehashed released declarations.
It is not a Rust validator and supplies no OTA, execution or funding authority.
"""
from __future__ import annotations
import collections, copy, gzip, hashlib, importlib.util, json, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
R = D.parents[1]
V = R / 'verification'
C = V / 'swift-guarded-snapshot-resource-cost'
SOURCE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
REV = 'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
inputs, controls, snippets = {}, [], []

def sha(b): return hashlib.sha256(b).hexdigest()
def read(p):
    b = p.read_bytes()
    inputs[str(p.relative_to(R))] = {'sha256': sha(b), 'bytes': len(b)}
    return b
def load(p): return json.loads(read(p))
def out(name, data): (D / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
def check(name, value):
    if not value: raise AssertionError(name)
    controls.append(name)
def seal(path, expected, count, size):
    raw = read(path / 'seal.json'); check('seal:' + path.name, sha(raw) == expected)
    obj = json.loads(raw); members = obj['members']; names = set()
    for m in members:
        p = Path(m['path'])
        check('safe:' + str(p), not p.is_absolute() and '..' not in p.parts and str(p) not in names)
        names.add(str(p)); b = read(path / p)
        check('sealed-member:' + path.name + '/' + str(p), len(b) == m['bytes'] and sha(b) == m['sha256'])
    check('sealed-count:' + path.name, len(members) == count)
    check('sealed-bytes:' + path.name, sum(m['bytes'] for m in members) == size)

def split(s, delimiter=','):
    stack, pieces, start = [], [], 0
    for n, ch in enumerate(s):
        if ch in '(<[{': stack.append({'(': ')', '<': '>', '[': ']', '{': '}'}[ch])
        elif ch in ')>]}':
            if not stack or stack.pop() != ch: raise ValueError('unbalanced')
        elif ch == delimiter and not stack: pieces.append(s[start:n].strip()); start = n + 1
    if stack: raise ValueError('unclosed')
    return [s for s in pieces + [s[start:].strip()] if s]
def strip_comments(s):
    return re.sub(r'/\*.*?\*/', '', '\n'.join(line.split('//', 1)[0] for line in s.splitlines()), flags=re.S)
def close(s, n):
    opens = {'(': ')', '{': '}', '<': '>'}; stack = [opens[s[n]]]
    for k in range(n+1, len(s)):
        if s[k] in opens: stack.append(opens[s[k]])
        elif s[k] in ')>}':
            if stack.pop() != s[k]: raise ValueError('bad declaration')
            if not stack: return k+1
    raise ValueError('unfinished declaration')
def declaration(source, name, expected=None):
    text = strip_comments(source); matches = []
    for m in re.finditer(r'\b(struct|enum)\s+' + re.escape(name) + r'\b', text):
        n = m.end()
        if text[n:n+1] == '<': n = close(text, n)
        while text[n:n+1].isspace(): n += 1
        if text[n:n+1] not in ('{', '('): continue
        end = close(text, n); raw = text[m.start():end]
        if expected is None or sha(raw.encode()) == expected: matches.append((m.group(1), text[n], raw, text[n+1:end-1]))
    if len(matches) != 1: raise ValueError('declaration ambiguity: ' + name)
    kind, delimiter, raw, body = matches[0]
    def fields(body, named):
        result = []
        for field in split(body):
            if '#[cfg(test)]' in field: continue
            field = re.sub(r'#\[[^]]*\]', '', field).strip()
            field = re.sub(r'^pub(?:\([^)]*\))?\s+', '', field)
            result.append(field.split(':', 1)[1].strip() if named else field)
        return result
    answer = {'kind': kind, 'declaration_sha256': sha(raw.encode()), 'source_bytes': len(raw.encode())}
    if kind == 'struct': answer['fields'] = fields(body, delimiter == '{')
    else:
        variants = []
        for variant in split(body):
            variant = re.sub(r'#\[[^]]*\]', '', variant).strip()
            m = re.match(r'(\w+)\s*(.*)', variant, re.S); vn, rest = m.groups()
            fs = fields(rest[1:close(rest, 0)-1], rest[0] == '{') if rest[:1] in ('(', '{') else []
            variants.append({'name': vn, 'fields': fs})
        answer['variants'] = variants
    return answer

def norm(t):
    t = t.strip()
    t = {'SwiftMetadata':'Metadata<SwiftDeclaration>', 'AError':'SnapshotAdmissionErrorV1', 'Stop':'SnapshotStopV1'}.get(t, t)
    return re.sub(r'\b(?:\w+::)+', '', t)
class Algebra:
    def __init__(self, declarations):
        self.decls = {d['name']:d for d in declarations}; self.active = set()
        if len(self.decls) != len(declarations): raise ValueError('duplicate type key')
    def walk(self, t):
        t = norm(t)
        if t in self.active: raise ValueError('owned recursion')
        self.active.add(t)
        try:
            if t.startswith(('&', '*const ', '*mut ')): return 1, collections.Counter()
            if t in ('()', '!', 'bool', 'char', 'Duration', 'Instant') or re.fullmatch(r'[uif](?:8|16|32|64|128|size)', t): return 1, collections.Counter()
            if t.startswith('['):
                ty, size = split(t[1:-1], ';'); count = int(size.replace('_',''))
                if count < 0 or count > 8192: raise ValueError('unsupported array')
                n, cuts = self.walk(ty); return 1 + count*n, collections.Counter({k:v*count for k,v in cuts.items()})
            if t.startswith('('): return self.struct(split(t[1:-1]))
            head = t.split('<',1)[0]; args = split(t[len(head)+1:-1]) if '<' in t else []
            if head in ('Vec','Box','Arc','File','Error'):
                if len(args) != (0 if head in ('File','Error') else 1): raise ValueError('resource arity')
                return 1, collections.Counter({t.replace(' ',''):1})
            if head == 'Option':
                if len(args) != 1: raise ValueError('option arity')
                return self.enum([[], args])
            if head == 'Result':
                if len(args) != 2: raise ValueError('result arity')
                return self.enum([[a] for a in args])
            d = self.decls[head]
            def subst(xs):
                for x in xs:
                    if head == 'Metadata':
                        if args != ['SwiftDeclaration']: raise ValueError('metadata type')
                        x = re.sub(r'\bD\b', args[0], x)
                    if head == 'Buffer':
                        if len(args) != 1: raise ValueError('buffer type')
                        x = re.sub(r'\bT\b', args[0], x)
                    yield x
            return self.struct(list(subst(d['fields']))) if d['kind'] == 'struct' else self.enum([list(subst(v['fields'])) for v in d['variants']])
        finally: self.active.remove(t)
    def struct(self, fields):
        n = 1; cuts = collections.Counter()
        for field in fields:
            fn, fc = self.walk(field); n += fn; cuts.update(fc)
        return n, cuts
    def enum(self, variants):
        # Independent componentwise union: branches need not be simultaneous.
        parts = [self.struct(v) for v in variants]; cuts = collections.Counter()
        for _, c in parts: cuts |= c
        return 1 + max([0] + [n for n,_ in parts]), cuts

def quote(row, cuts):
    n = row['structural_occurrence_allowance']; size = row['inline_bytes']
    value = n*(1+size)
    for kind, count in row['resource_frontiers'].items():
        c = cuts[kind]; cost = c['interface_work'] + c['native_resource_backing']
        if kind == 'Vec<SwiftSlot>':
            dynamic = row['dynamic_resource_elements'][kind]
            cost += 64*quote(dynamic,c['element_cuts'])
        value += count*cost
    return value

def excerpt(path, start, end, clause, anchors):
    b = read(path); text = '\n'.join(b.decode().splitlines()[start-1:end]) + '\n'
    for anchor in anchors: check('source:' + clause + ':' + anchor, anchor in text)
    snippets.append({'path':str(path.relative_to(R)), 'start':start, 'end':end, 'file_sha256':sha(b), 'clause':clause, 'source':text})

def main():
    seal(C,'4bc0e376abb3f3db0f6b7ea7b8045b730ec2717247d082014c1f7d41e1f12259',132,903284)
    rosterpath=V/'swift-guarded-snapshot-leaf-callee-cost/constructor-destructor-roster'
    seal(rosterpath,'183bf0311de870bf6986b44e9ccfad9f035d9eb41e1f5f0470433f09bd09fc24',3,875750)
    for fn,digest in [('guarded-snapshot-callee-resource-frozen-data-release.json','63dac924ace5b80d9911fef329cf88340c1b1adcb43329a7b35b6fb66be00ee4'),('guarded-snapshot-full-source146-layout-data-release.json','7e9a1d8e2602e5b8eb8dfdad61da7f4c816ecd52b6e9beebd8759f173346e7ad')]:
        check('root-release:'+fn,sha(read(V/'swift-semantic-adapter-root-review'/fn))==digest)
    # Independently rehash the complete declared frozen-input custody, restricting
    # the concurrent callee lane to its explicitly released roster subpacket.
    for rel,desc in load(C/'input-custody.json')['files'].items():
        if rel.startswith('verification/swift-guarded-snapshot-leaf-callee-cost/'):
            check('active-lane-release-only',rel.startswith(str(rosterpath.relative_to(R))+'/'))
        b=read(R/rel); check('input:'+rel,len(b)==desc['bytes'] and sha(b)==desc['sha256'])
    comp=V/'swift-guarded-snapshot-host-composition'; base=V/'swift-guarded-snapshot-funding-implementation/source/vm'
    manifest=load(comp/'source-manifest.json')['members']
    check('source146-identity',len(manifest)==146 and sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode())==SOURCE)
    sources={}
    for m in manifest:
        p=comp/'overlay/vm'/m['path']; p=p if p.is_file() else base/m['path']; b=read(p)
        check('actual-source:'+m['path'],len(b)==m['bytes'] and sha(b)==m['sha256']); sources[m['path']]=(p,b.decode())
    host=load(comp/'host-support-manifest.json')['members']
    check('host11-identity',len(host)==11 and sha(json.dumps(host,sort_keys=True,separators=(',',':')).encode())==HOST)
    for m in host:
        b=read(V/'swift-real-profile-loader-binding/host'/m['path'])
        check('actual-host:'+m['path'],len(b)==m['bytes'] and sha(b)==m['sha256'])

    inv=load(V/'swift-guarded-snapshot-payload-destruction-cost/inventory.json')
    check('inherited-source-host',inv['source_tree_sha256']==SOURCE and inv['host_tree_sha256']==HOST)
    declared=[]
    for d in inv['declarations']:
        realname={'MetaSpan':'Span','WasiSpan':'Span','ValidatorResource':'Resource'}.get(d['name'],d['name'])
        actual=declaration(sources[d['path']][1],realname,d['declaration_sha256'])
        def rename(xs):
            return [re.sub(r'\bSpan\b','MetaSpan',x) if d['path']=='src/experimental/metadata.rs' else re.sub(r'\bResource\b','ValidatorResource',x) if d['path']=='src/experimental/account.rs' else re.sub(r'\bSpan\b','WasiSpan',x) if d['path']=='src/experimental_wasi/mod.rs' else x for x in xs]
        if 'fields' in actual: actual['fields']=rename(actual['fields'])
        else:
            for variant in actual['variants']: variant['fields']=rename(variant['fields'])
        check('actual-declaration:'+d['name'],all(d[k]==v for k,v in actual.items()))
        declared.append(d)
    internal=load(C/'internal-rows.json')
    for d in internal['declarations_added']:
        rel=d['source_path'].split('/overlay/vm/')[-1] if '/overlay/vm/' in d['source_path'] else d['source_path'].split('/source/vm/')[-1]
        actual=declaration(sources[rel][1],d['name'])
        check('extra-source-declaration:'+d['name'],actual['fields']==d['fields'])
        declared.append({'name':d['name'],**actual})
    algebra=Algebra(declared); rows=load(C/'rows.json')
    for row in rows+internal['rows']:
        n,front=algebra.walk(row['type'])
        check('complete-source-graph:'+row['type'],n==row['structural_occurrence_allowance'] and dict(front)==row['resource_frontiers'])
        if 'Vec<SwiftSlot>' in front:
            dynamic=row['dynamic_resource_elements']['Vec<SwiftSlot>']; dn,df=algebra.walk('SwiftSlot')
            check('complete-nested-slot:'+row['type'],dn==dynamic['structural_occurrence_allowance'] and dict(df)==dynamic['resource_frontiers'] and dynamic['inline_bytes']==136)
    for ty,schema in inv['dynamic_element_destructor_schemas'].items():
        n,front=algebra.walk(ty)
        check('plain-element-closure:'+ty,n==schema['nodes'] and dict(front)==schema['resources'])
    out('source-declaration-review.json',{'declarations':declared,'source_tree_sha256':SOURCE,'source_graph_roots':33,'all_fields_reextracted':True,'scanner_is_closed_source_only':True})

    raw=gzip.decompress(read(V/'swift-guarded-snapshot-host-composition-independent/commands/exact146-metadata-mir/stdout.gz'))
    check('full-layout-raw',sha(raw)=='6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a' and len(raw)==7641979)
    obs={}
    for line in raw.decode().splitlines():
        m=re.fullmatch(r'print-type-size type: `(.+)`: (\d+) bytes, alignment: (\d+) bytes',line)
        if m:
            name,sz,align=m.groups(); row={'size':int(sz),'alignment':int(align)}
            check('unique-layout:'+name,name not in obs); obs[name]=row
    check('full-layout-count',len(obs)==3072)
    applicability=load(C/'full-layout-applicability.json')
    for name,row in applicability['rows_used'].items():
        check('actual-qualified-layout:'+name,obs[name]=={k:row[k] for k in ('size','alignment')})
    expected_layouts={'experimental_swift_reactor::cache::Partial':1432,'experimental_wasi::accounted::Partial':216,'experimental_swift_reactor::cache::CacheConstructionFailure':2312,'experimental_swift_reactor::cache::initial_profile_v1::InitialProfileConstructionOutcomeV1':3416,'experimental_swift_reactor::cache::initial_profile_v1::SnapshotAttemptV1':2248,'experimental_swift_reactor::cache::initial_profile_v1::SnapshotPhaseStorageV1':5328}
    for name,sz in expected_layouts.items():check('disambiguated-layout:'+name,obs[name]=={'size':sz,'alignment':8})
    # Both Partial rows exist. Only cache::Partial matches these eight fields;
    # applying the unrelated WASI 216-byte Partial would be a false substitution.
    check('Partial-module-qualified',dict(algebra.walk('Partial')[1])==next(r['resource_frontiers'] for r in internal['rows'] if r['type']=='Partial'))

    contract=load(C/'contract.json'); cuts=load(C/'resource-cuts.json')
    check('exact-inherited-unit',contract['logical_unit']=='source/aggregate/destructor-interface occurrences plus explicit native-sized/requested-backing allowance')
    expected_interfaces={
        'File':[(8,),(8,),(8,),(8,),(1,),(4,4,4),(4,),(16,),(4,4)],
        'Arc<AtomicBool>':[(8,),(8,8,8),(1,),(8,),(1,),(16,),(8,),(1,),(8,),(8,8,8),(1,),(8,),(1,),(16,),(8,8,8)],
        'Error':[(8,),(8,),(8,8)]}
    independent_cuts={}
    for name,events in expected_interfaces.items():
        actual=contract['interfaces'][name]
        # Order within native field maps is immaterial; event order and each
        # event's complete width multiset are independently compared.
        check('interface-width-roster:'+name,[sorted(r['native_fields'].values()) for r in actual['records']]==[sorted(e) for e in events])
        backing=24 if name=='Arc<AtomicBool>' else 0
        independent_cuts[name]={'interface_work':len(events),'native_resource_backing':backing+sum(map(sum,events))}
        check('independent-interface-sum:'+name,independent_cuts[name]==cuts[name])
    sizes={'Signature':12,'Type':1,'Import':20,'Function':12,'Global':12,'Export':16,'Segment':16,'PinRecord':16,'Patch':32,'Option<ScanPlan>':56,'DecodedInstruction':40,'u32':4,'u8':1,'SwiftSlot':136}
    # Limits are from actual narrowed product defaults and concrete callsites,
    # checked in source-semantic-review.json, not policy inferred from manifests.
    limits={t:(16*1024*1024)//sizes[t] for t in ('Signature','Type','Import','Function','Global','Export','Segment')}
    limits.update({'PinRecord':64,'Patch':512,'Option<ScanPlan>':512,'DecodedInstruction':(8*1024*1024)//40,'u32':(8*1024*1024)//4,'u8':65536})
    for name,max_live in limits.items():
        frontier='Vec<'+name+'>'; n=algebra.walk(name)[0]
        requested=16*1024*1024 if name in ('Signature','Type','Import','Function','Global','Export','Segment') else 8*1024*1024 if name in ('DecodedInstruction','u32') else max_live*sizes[name]
        bound={'element_nodes':n,'max_live_elements':max_live,'max_requested_bytes':requested}
        check('source-derived-cap:'+frontier,contract['vectors'][frontier]==bound)
        independent_cuts[frontier]={'interface_work':4+n*max_live,'native_resource_backing':24+(n+1)*requested}
        check('independent-vector-sum:'+frontier,independent_cuts[frontier]==cuts[frontier])
    b=64*1024*1024
    independent_cuts['Box<[u8]>']={'interface_work':3+b,'native_resource_backing':24+2*b}
    check('independent-box',independent_cuts['Box<[u8]>']==cuts['Box<[u8]>'])
    independent_cuts['Vec<SwiftSlot>']={'interface_work':4,'native_resource_backing':24+64*136,'max_live_elements':64,'element_inline_bytes':136,'element_cuts':{k:independent_cuts[k] for k in ('Vec<Type>','Vec<DecodedInstruction>','Vec<u32>')}}
    check('independent-slot-complete',independent_cuts['Vec<SwiftSlot>']==cuts['Vec<SwiftSlot>'])
    values={r['type']:quote(r,independent_cuts) for r in rows}
    internal_values={r['type']:quote(r,independent_cuts) for r in internal['rows']}
    check('all20-complete-values',values==load(C/'components.json')['rows'])
    check('all13-internal-values',internal_values==internal['prices_per_one'])
    domain=inv['entry_per_visit_types'];check('entry-domain-exact',set(domain)=={'File','Option<File>','ReturnedLoaderFilesV1','SetupOutcomeV1','SelectedValidatedProfileV1','LoaderFailureV1','Cancellation'})
    check('returned45196204',values['OwnedFixtureOutcomeV1']==45196204)
    check('entry1210256815',max(values[x] for x in domain)==1210256815)
    roster=load(rosterpath/'roster.json'); multipliers={k.replace(' ',''):v for k,v in roster['typed_cuts'].items()}
    check('constructor-exact12-domain',set(multipliers)==set(internal_values)-{'SnapshotPhaseStorageV1'} and len(multipliers)==12)
    total=sum(internal_values[k]*v for k,v in multipliers.items());check('constructor134288951629',total==134288951629)
    check('constructor-price-import',load(C/'constructor-roster-composition.json')['typed_body_price_sum']==total)
    check('no-child53-application',load(C/'components.json')['child53_multiplier_applied'] is False)
    out('independent-prices.json',{'unit':contract['logical_unit'],'cuts':independent_cuts,'rows':values,'internal_rows':internal_values,'returned':45196204,'during_entry_per_visit':1210256815,'child53_multiplier_applied':False,'constructor_multipliers':multipliers,'constructor_body_sum':total,'constructor_shell_separate':True,'SnapshotPhaseStorageV1_multiplier_unselected':True,'compiled_std_correspondence':False})
    return sources,algebra,rows,internal,independent_cuts,roster

def semantic_controls(sources,algebra,rows,internal,cuts,roster):
    platform=V/'swift-guarded-snapshot-stdlib-resource-source/official-source/library'
    product={k:v[0] for k,v in sources.items()}
    spans=[
        (platform/'std/src/fs.rs',134,137,'File owns platform File',['inner: fs_imp::File']),
        (platform/'std/src/sys/fs/mod.rs',8,22,'Darwin selects Unix File',['target_family = "unix"','use unix as imp']),
        (platform/'std/src/sys/fd/mod.rs',5,10,'Darwin selects Unix fd',['target_family = "unix"','pub use unix::*']),
        (platform/'std/src/sys/fs/unix.rs',90,94,'platform File owns FileDesc',['pub struct File(FileDesc)']),
        (platform/'std/src/sys/fd/unix.rs',70,74,'FileDesc owns OwnedFd',['pub struct FileDesc(OwnedFd)']),
        (platform/'std/src/os/fd/owned.rs',199,226,'OwnedFd precheck then one ignored close',['debug_assert_fd_is_open','let _ = libc::close']),
        (platform/'std/src/sys/fs/unix.rs',962,972,'conditional fcntl errno abort union',['check_library_ub()','libc::F_GETFD','errno() == libc::EBADF','rtabort!']),
        (platform/'alloc/src/sync.rs',387,408,'Arc backing layout',['repr(C, align(2))','strong: Atomic<usize>','weak: Atomic<usize>','data: T']),
        (platform/'alloc/src/sync.rs',2136,2151,'last strong drops value and implicit Weak',['let _weak = Weak','ptr::drop_in_place']),
        (platform/'alloc/src/sync.rs',2864,2915,'strong decrement acquire assertion slow path',['strong.fetch_sub(1, Release)','acquire!','self.drop_slow()']),
        (platform/'alloc/src/sync.rs',3533,3565,'weak decrement and final deallocation',['weak.fetch_sub(1, Release)','Layout::for_value_raw','self.alloc.deallocate']),
        (platform/'alloc/src/alloc.rs',294,323,'Global publishes requested byte extent',['Ok(ptr.cast_slice(size))','never returns a larger']),
        (platform/'alloc/src/raw_vec/mod.rs',782,807,'grow_exact and commit after success',['len.checked_add(additional)','self.finish_grow(cap','self.set_ptr_and_cap(ptr, cap)']),
        (platform/'alloc/src/raw_vec/mod.rs',632,657,'RawVec dealloc capacity times element layout',['elem_layout.size().unchecked_mul(self.cap.as_inner())']),
        (platform/'alloc/src/vec/mod.rs',4350,4365,'Vec visits live slice before backing release',['cast_slice(self.len).drop_in_place()']),
        (platform/'alloc/src/boxed.rs',1990,2007,'Box pointee then allocation',['T in the Box is dropped by the compiler','Layout::for_value_raw']),
        (platform/'core/src/io/error/repr_bitpacked.rs',229,302,'Error tag closed or arbitrary Custom',['impl Drop for Repr','TAG_CUSTOM','CustomOwner::from_raw']),
        (platform/'core/src/io/error.rs',614,622,'Custom inner dynamic callback',['(self.error_drop)(self.error)']),
        (platform/'core/src/io/error.rs',681,688,'Custom outer dynamic callback',['outer_drop']),
        (platform/'alloc/src/io/error.rs',248,286,'alloc Box callback source',['Box<dyn core::error::Error + Send + Sync>','drop_box_raw::<Custom>']),
        (platform/'std/src/io/error.rs',42,86,'last_os_error constructs Os tag',['Error::from_raw_os_error(errno())','from_raw_os_error_with_functions']),
        (C/'official-source/library/std/src/sys/helpers/small_c_string.rs',12,75,'NUL path retains static message tag',['const NUL_ERR','Err(NUL_ERR)']),
        (C/'official-source/library/std/src/sys/pal/unix/mod.rs',238,255,'cvt and cvt_r use Os errors',['Error::last_os_error()']),
        (platform/'std/src/sys/fs/unix.rs',1151,1246,'OpenOptions custom branches excluded by actual options',['get_access_mode','get_creation_mode','io::Error::new','cvt_r(|| unsafe { open64']),
        (platform/'std/src/sys/fd/unix.rs',137,147,'FileDesc read OS error',['libc::read','cvt(']),
        (platform/'std/src/sys/fd/unix.rs',374,386,'FileDesc write OS error',['libc::write','cvt(']),
        (platform/'std/src/sys/fs/unix.rs',1246,1264,'File metadata OS error',['fstat64','cvt(']),
        (platform/'std/src/sys/fs/unix.rs',1524,1550,'File position OS error',['libc::SEEK_CUR','cvt(unsafe { lseek64']),
        (product['src/execute.rs'],1,34,'private cancellation closed to Default Clone and AtomicBool',['#[derive(Clone, Default)]','pub struct Cancellation(Arc<AtomicBool>);','self.0.store','self.0.load','counts: [std::sync::atomic::AtomicUsize; 2]']),
        (product['src/experimental_swift_reactor/cache/initial_profile_v1.rs'],761,780,'setup original valid options and retained errors',['File::open(binding.paths[stage])','write(true).create_new(true)','SetupOutcomeV1::Refused { stage, original, files }']),
        (product['src/experimental_swift_reactor/cache/initial_profile_v1.rs'],437,507,'writer actual File source and original errors',['output:&mut File','output.metadata()','output.stream_position()','output.write(requested)','Some(error)']),
        (product['src/experimental_swift_reactor/retained_profile_loader_v1.rs'],524,578,'generic reader only preserves originating error',['input.read(','LoaderFailureV1::io(role, base + used, attempt, error)']),
        (product['src/experimental_swift_reactor/retained_profile_loader_v1.rs'],600,650,'loader uses File and bounds fresh reserve before allocation',['file: &mut File','if count > cap','Vec::new()','try_reserve_exact(count)','read_request(file,']),
        (product['src/experimental_swift_reactor/retained_profile_loader_v1.rs'],818,849,'getcwd original OS error',['io::Error::last_os_error()']),
        (product['src/experimental_swift_reactor/retained_profile_loader_v1.rs'],925,950,'loader executable File original error',['let executable = File::open']),
        (product['src/experimental/swift.rs'],21,32,'validation default maxima',['source_bytes: 64 * 1024 * 1024','metadata_bytes: 16 * 1024 * 1024','scratch_bytes: 1024 * 1024']),
        (product['src/experimental/swift.rs'],377,403,'validation rejects widened budgets before allocation',['budget.source_bytes > max.source_bytes','budget.metadata_bytes > max.metadata_bytes','budget.scratch_bytes > max.scratch_bytes','InvalidBudget']),
        (product['src/experimental/swift.rs'],424,465,'source Box limit and successful or partial Vec requests',['input.len() > budget.source_bytes','meter.reserve(Resource::Source, input.len()','try_reserve_exact(input.len())','source.capacity() != input.len()','source.into_boxed_slice()']),
        (product['src/experimental/account.rs'],159,194,'metadata scratch reserve rejects category overflow before allocation',['Resource::Metadata','Resource::Scratch','if attempted > limit','metadata_reserved = attempted']),
        (product['src/experimental/account.rs'],259,318,'fresh growing buffer reserves overlap first and bounds refusal cleanup',['meter.reserve(self.category, bytes, cursor)?','let mut next = Vec::new()','next.try_reserve_exact(capacity)','next.capacity() != capacity','drop(next)','drop(old)','self.values.push(value)']),
        (product['src/experimental_swift_reactor/control.rs'],41,61,'runtime default scalar limits',['cache_entry_bytes: 8 * MIB','cache_entries: 64','active_pins: 64']),
        (product['src/experimental_swift_reactor/control.rs'],675,704,'runtime budget narrowed during actual adoption',['control.check_budget(cursor)?']),
        (product['src/experimental_swift_reactor/control.rs'],778,880,'runtime per field rejects widening',['self.budget.cache_entry_bytes','self.budget.cache_entries','self.budget.active_pins','if attempted > limit']),
        (product['src/experimental_swift_reactor/cache.rs'],14,46,'cache source constants',['PATCH_CAPACITY: usize = 512','PLAN_CAPACITY: usize = 512','RESIDENT_LINKS: usize = 64']),
        (product['src/experimental_swift_reactor/cache.rs'],321,355,'Partial fresh vectors and cleanup path',['slots: Vec::new()','pins: Vec::new()','patches: Vec::new()','index: Vec::new()','plans: Vec::new()','drop_reserved(take(&mut self.slots)','drop(take(&mut self.index))','drop_reserved(self, header)']),
        (product['src/experimental_swift_reactor/cache.rs'],1808,1877,'cache actual bounded reserve requests and partial fill',['budget.cache_entries.min(','reserve(&mut partial.slots, entries','reserve(&mut partial.pins, budget.active_pins','reserve(&mut partial.patches, PATCH_CAPACITY','reserve(&mut partial.index, RESIDENT_INDEX_BYTES','reserve(&mut partial.plans, PLAN_CAPACITY']),
        (product['src/experimental_swift_reactor/cache.rs'],1909,1923,'cache exact capacity refusal after requested allocator interface',['values.try_reserve_exact(requested)','control.exact(requested, values.capacity())']),
        (product['src/experimental/cache/borrowed.rs'],219,231,'resident fresh reserve can fail or reject cap',['let mut values = Vec::new()','try_reserve_exact(capacity)','meter.exact_capacity(capacity, values.capacity())']),
        (product['src/experimental/cache/borrowed.rs'],790,812,'resident sum checked before build',['let bytes = counts.bytes(meter)?','if bytes > meter.entry_capacity()']),
        (product['src/experimental/cache/decode.rs'],497,530,'resident allocates exactly three admitted vector counts',['borrowed::allocate(counts.locals','borrowed::allocate(counts.instructions','borrowed::allocate(counts.targets']),
        (product['src/experimental/cache/decode.rs'],150,165,'resident pushes cannot grow',['values.len() == values.capacity()']),
        (product['src/experimental_wasi/mod.rs'],50,82,'WASI individual maxima and rejection',['one_transfer_bytes: 65_536','log_bytes: 65_536','self.one_transfer_bytes > max.one_transfer_bytes','self.log_bytes > max.log_bytes']),
        (product['src/experimental_swift_reactor/control.rs'],896,929,'actual WASI budget validated before deadline returned',['if let Err(error) = budget.check()','Ok(self.deadline)']),
        (product['src/experimental_wasi/accounted.rs'],241,318,'WASI budget validation before allocation and cleanup on error',['carry_wasi_deadline(started, budget','let mut partial = Partial::empty()','budget.one_transfer_bytes as usize','budget.log_bytes as usize','try_reserve_exact(bytes)','exact_capacity(bytes','partial.cleanup(self.control)']),
    ]
    for args in spans: excerpt(*args)
    # Verify the complete original MIR supplies only the actual File reader
    # specialization. Source genericity alone cannot justify Os/static errors.
    mir=gzip.decompress(read(V/'swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz')).decode()
    readcalls=[l.strip() for l in mir.splitlines() if '= read_request::<' in l]
    check('File-specialized-original-MIR',len(readcalls)==2 and all('read_request::<std::fs::File>' in line for line in readcalls))
    roster_mir=read(V/'swift-guarded-snapshot-leaf-callee-cost/constructor-destructor-roster/selected-constructor.mir').decode()
    # This verifies the roster's cited raw lines occur in released MIR and every
    # complete body is exactly present in the original source146 MIR.
    for body in roster['body_occurrences']:
        start=mir.index(body['header']); end=mir.index('\n}\n',start)+3; full=mir[start:end]
        check('constructor-body-source:'+body['header'].split('(')[0],sha(full.encode())==body['MIR_sha256'])
        check('constructor-body-in-subpacket:'+body['header'].split('(')[0],full in roster_mir)
        for site in body['sites']:check('constructor-actual-site:'+str(site['line']),site['code'] in full)
    # Typed counts conservatively preserve written normal/unwind alternatives;
    # these are body occurrences, not ownership counts or storage discounts.
    check('constructor-typed12-multipliers',roster['typed_cuts']=={'Partial':5,'Vec<SwiftSlot>':2,'Vec<PinRecord>':2,'Vec<Patch>':2,'Vec<u8>':2,'Vec<Option<ScanPlan>>':2,'AdoptedProof':4,'AdoptionBodyV1':1,'CacheConstructionFailure':1,'Option<Result<SwiftFunctionCache, CacheConstructionFailure>>':1,'InitialProfileConstructionOutcomeV1':1,'SnapshotAttemptV1':2})
    out('source-semantic-review.json',{'schema':1,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'platform_revision':REV,'proof_spans':snippets,'File_specialized_original_MIR_calls':readcalls,'File_one_close_request_only':True,'close_flush_descriptor_retirement_refund_observed':False,'Error_closed_route_only':True,'custom_Error_callbacks_unbounded_and_refused':True,'Global_requested_capacity_only':True,'refusal_partial_cleanup_covered_by_same_request_ceiling':True,'Vec_u8_payload_cut_not_loader_temporary_cut':True,'binary_correspondence_pending':['File/OwnedFd selected check_library_ub/fcntl/errno/abort and close call edges in installed nongeneric std bodies','Arc/Weak AtomicBool instantiated strong and weak final-owner/acquire/drop/deallocation bodies and concrete 24-byte alignment8 deallocation request','Error compiled Os/static tag representation and no selected custom callback path','Global/RawVec/Vec and Box concrete teardown instantiations, live-element traversal and requested size/alignment at deallocation'],'private_std_allocator_kernel_retry_lowering_CPU_time_RSS_stack_outside_unit':True,'all_authority_gates_pending':True})

    spec=importlib.util.spec_from_file_location('resource_model_under_review',C/'model.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    contract=load(C/'contract.json')
    def refuses(name,fn):
        try:fn()
        except (ValueError,KeyError,OverflowError):check('hostile:'+name,True)
        else:raise AssertionError('accepted hostile:'+name)
    for name in contract['binding']:
        bad=copy.deepcopy(contract['binding']);bad[name]='foreign'
        refuses('identity-'+name,lambda:mod.source_ceiling_cuts(contract,bad,'closed-file-os-or-static-message'))
    for provenance in ('custom','generic','arbitrary-positive','unknown','Os-or-Custom',None,False):
        refuses('error-origin-'+str(provenance),lambda:mod.source_ceiling_cuts(contract,contract['binding'],provenance))
    for name,bound in contract['vectors'].items():
        for field in bound:
            bad=copy.deepcopy(contract);bad['vectors'][name][field]+=1
            refuses('contract-tamper-'+name+'-'+field,lambda:mod.source_ceiling_cuts(bad,contract['binding'],'closed-file-os-or-static-message'))
    for ty in ('SwiftFunctionCache','SnapshotScopeV1','Partial'):
        row=next(r for r in rows+internal['rows'] if r['type']==ty)
        for frontier in row['resource_frontiers']:
            selected={k:copy.deepcopy(cuts[k]) for k in row['resource_frontiers']};selected.pop(frontier)
            refuses('missing-'+ty+'-'+frontier,lambda:mod.evaluate_row(row,selected))
        for nested in ('Vec<Type>','Vec<DecodedInstruction>','Vec<u32>'):
            selected={k:copy.deepcopy(cuts[k]) for k in row['resource_frontiers']};selected['Vec<SwiftSlot>']['element_cuts'].pop(nested)
            refuses('nested-'+ty+'-'+nested,lambda:mod.evaluate_row(row,selected))
    for frontier,cut in cuts.items():
        if frontier=='Vec<SwiftSlot>':continue
        row={'type':'hostile','inline_bytes':4,'structural_occurrence_allowance':1,'resource_frontiers':{frontier:1}}
        for field in ('interface_work','native_resource_backing'):
            bad=copy.deepcopy(cut);bad[field]=0
            refuses('zero-'+frontier+'-'+field,lambda:mod.evaluate_row(row,{frontier:bad}))
    for bad in (-1,True,False,1.25,'1',None,2**64):
        refuses('not-u64-'+str(bad),lambda:mod.add(bad))
    refuses('add-overflow',lambda:mod.add(2**64-1,1));refuses('mul-overflow',lambda:mod.mul(2**63,2))
    for ty in ('Unknown','Option<File,Error>','Result<File>','Vec<Error,File>','[File;8193]'):
        refuses('unqualified-type-'+ty,lambda:algebra.walk(ty))
    refuses('borrowed-width-is-not-pointee-layout',lambda:mod.evaluate_row({'type':'File','inline_bytes':0,'structural_occurrence_allowance':1,'resource_frontiers':{'File':1}},{'File':cuts['File']}))

    # Independently enumerate fully live, partial, empty and post-reserve refusal
    # states. This is an arithmetic law over source ceilings, not runtime proof.
    for element,nodes in [('u8',1),('Type',2),('Signature',7),('Import',8),('PinRecord',3),('Patch',7),('Option<ScanPlan>',11),('DecodedInstruction',14)]:
        extent={'u8':1,'Type':1,'Signature':12,'Import':20,'PinRecord':16,'Patch':32,'Option<ScanPlan>':56,'DecodedInstruction':40}[element]
        for capacity in range(33):
            b=capacity*extent
            for live in range(capacity+1):
                candidate=mod.plain_vector({'element_nodes':nodes,'max_live_elements':live,'max_requested_bytes':b})
                check('finite-vector-source:'+element,candidate['interface_work']==4+sum(nodes for _ in range(live)))
                check('finite-vector-request-native:'+element,candidate['native_resource_backing']>=24+b+sum(nodes*extent for _ in range(live)))
                # A successful reserve followed by capacity/stop refusal may
                # destroy length zero with nonzero backing; it stays included.
                check('finite-refusal-backing:'+element,candidate['native_resource_backing']>=24+b)
                # Allocation failure on a fresh vector leaves capacity zero.
                check('finite-failed-allocation:'+element,24<=candidate['native_resource_backing'])
    for b in range(257):
        for live in (0,b//2,b):
            box=mod.byte_box({'max_requested_bytes':b,'max_live_elements':live})
            check('finite-byte-box',box=={'interface_work':3+live,'native_resource_backing':24+2*b})

if __name__=='__main__':
    state=main()
    # Functions below are appended before executing the complete review.
    if 'semantic_controls' in globals(): semantic_controls(*state)
    out('input-custody.json',{'schema':1,'files':inputs})
    out('controls.json',{'schema':1,'assertions':len(controls),'groups':dict(collections.Counter(c.split(':',1)[0] for c in controls)),'all_passed':True,'controls':controls})
    print(json.dumps({'assertions':len(controls),'status':'passed','source_tree_sha256':SOURCE,'compiler_product_native_UI_capture_started':False},sort_keys=True))
