"""Rehash custody and derive selected native constructor CFG correspondence."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

sys.dont_write_bytecode=True
from collect import PINNED, SYMBOLS
from native_model import Native, MASK
import ir_model
D=Path(__file__).resolve().parent;R=D.parents[1];B=R/'verification/swift-guarded-snapshot-resource-binary-correspondence'
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def load(p):return json.loads(p.read_text())
def put(n,x):(D/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def checked(p,row):
    b=p.read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256'],str(p);return b

def custody():
    rows=[]
    for name,h in PINNED.items():
        p=R/'verification'/name;sb=(p/'seal.json').read_bytes();assert sha(sb)==h
        seal=json.loads(sb)
        for row in seal['members']:checked(p/row['path'],row)
        rows.append(dict(path=str(p.relative_to(R)),seal_sha256=h,members=len(seal['members'])))
    accepts={
      'guarded-snapshot-resource-binary-host-acceptance.json':'590b4ae991227b6a44cc21869f7d840c7a3f2855957a287190c83418b8b4ab8e',
      'guarded-snapshot-native-interface-host-acceptance.json':'924da7393c2b438e683a7cf760bab7038c121a50b30cfba00990b4070a018e4b',
      'guarded-snapshot-native-storage-operand-amendment.json':'802b8a717eda708626f43f9ea81844a4679c9f5c5bd12403974d7adfc9b3b63a'}
    for n,h in accepts.items():
        p=R/'verification/swift-semantic-adapter-root-review'/n;assert sha(p.read_bytes())==h;rows.append(dict(path=str(p.relative_to(R)),sha256=h))
    reader=B/'binary_format.py';assert sha(reader.read_bytes())=='0b29a32b12748f2932d838b89bf8fda207c41c436289cc98315b6bc13cc8eea0'
    ns={};exec(compile(reader.read_bytes(),str(reader),'exec'),ns)
    installed=load(B/'installed-inputs.json')['archives'];objects={}
    for n,row in installed.items():
        raw=checked(Path(row['path']),row);members=ns['archive_members'](raw);objs=[m for m in members if m['name'].endswith('.o')];assert len(objs)==1
        obj=objs[0];parsed=ns['macho'](obj['data']);objects[n]=(row,obj,parsed)
    return rows,objects,ns

def native_bodies(objects,ns):
    prior=load(B/'correspondence.json')['native_functions'];selected={}
    for n,row in prior.items():
        if any(k in n for k in ('4File6open_c','4File4open0','run_with_cstr_allocatingNtNtNtB6_2fs4unix4File')):
            selected[n]=copy.deepcopy(row)|dict(symbol=n)
    for name in ('disassembly','cstring-constructor'):
        output=gzip.decompress((D/(name+'.stdout.gz')).read_bytes()).decode();current=None
        for line in output.splitlines():
            m=re.fullmatch(r'([0-9a-f]+) <([^>]+)>:',line)
            if m:
                symbol=m[2];assert symbol not in selected;archive='alloc' if '5alloc' in symbol else 'core' if symbol==SYMBOLS[2] else 'std'
                current=dict(symbol=symbol,address=int(m[1],16),archive=archive,instructions=[],relocations=[],output=name+'.stdout.gz');selected[symbol]=current
            ins=re.match(r'\s*([0-9a-f]+): ([0-9a-f]{8})\s+(.+)',line)
            rel=re.match(r'\s*([0-9a-f]+):\s+(ARM64_RELOC_[A-Z0-9_]+)\s+(.+)',line)
            if ins:current['instructions'].append(dict(address=int(ins[1],16),word=int(ins[2],16),assembly=ins[3]))
            if rel:
                types={'ARM64_RELOC_BRANCH26':2,'ARM64_RELOC_PAGE21':3,'ARM64_RELOC_PAGEOFF12':4,'ARM64_RELOC_GOT_LOAD_PAGE21':5,'ARM64_RELOC_GOT_LOAD_PAGEOFF12':6}
                current['relocations'].append(dict(instruction_address=int(rel[1],16),type=types[rel[2]],target=rel[3]))
    assert len(selected)==7
    for symbol,row in selected.items():
        a,obj,m=objects[row['archive']];native=[s for s in m['symbols'] if s['name']==symbol];assert len(native)==1 and native[0]['value']==row['address']
        ins=row['instructions'];assert [i['address'] for i in ins]==list(range(row['address'],ins[-1]['address']+4,4))
        for i in ins:
            raw,off,_=ns['at_address'](obj['data'],m,i['address'],4);assert int.from_bytes(raw,'little')==i['word'];i['object_offset']=off
        raw=b''.join(struct.pack('<I',i['word']) for i in ins)
        if 'instruction_bytes_hex' in row:assert bytes.fromhex(row['instruction_bytes_hex'])==raw
        row.update(instruction_bytes_hex=raw.hex(),instruction_bytes_sha256=sha(raw),archive_sha256=a['sha256'],archive_member=obj['name'],archive_member_sha256=sha(obj['data']))
        found=[]
        for rel in row['relocations']:
            _,_,section=ns['at_address'](obj['data'],m,rel['instruction_address'],4)
            actual=[r for r in m['relocations'] if r['section']==section['index'] and r['address']==rel['instruction_address']-section['address'] and r['type']==rel['type'] and r['target']==rel['target']]
            assert len(actual)==1
            found.append(actual[0]|dict(instruction_address=rel['instruction_address']))
        actual_in_extent=[r for r in m['relocations'] if r['section']==1 and row['address']<=r['address']<=ins[-1]['address']]
        assert len(actual_in_extent)==len(found)
        row['relocations']=found
    return selected

def sym(functions,needle):
    names=[n for n in functions if needle in n];assert len(names)==1,(needle,names);return names[0]

def run_path(functions,objects,data,write=False,result=7,errno=0,oom=False,words=None,relocations=None):
    vm=Native(functions,objects,words,relocations);path=0x20000000;opts=0x20010000;out=0x20020000
    vm.blob(path,data);vm.blob(opts,bytes(12));vm.blob(out,bytes(16));vm.write(opts+4,438,2)
    vm.write(opts+(7 if write else 6),1,1)
    if write:vm.write(opts+11,1,1)
    vm.regs[0]=opts;vm.regs[1]=path;vm.regs[2]=len(data);vm.regs[8]=out;vm.opens=[-errno] if errno else [result];vm.alloc_fail=oom;vm.path_extent=len(data)+1
    try:vm.run(SYMBOLS[0])
    except StopIteration:pass
    return vm,out

def check_path(functions,objects,n,nul=None,write=False,errno=0,oom=False,words=None,relocations=None):
    data=bytearray(b'x'*n)
    if nul is not None:data[nul]=0
    vm,out=run_path(functions,objects,bytes(data),write=write,errno=errno,oom=oom,words=words,relocations=relocations)
    alloc=[e for e in vm.events if e['kind']=='allocation'];dealloc=[e for e in vm.events if e['kind']=='deallocation'];opens=[e for e in vm.events if e['kind']=='open-interface']
    assert alloc==([dict(kind='allocation',bytes=n+1,alignment=1)] if n>=384 else []),('allocation',n,alloc)
    if oom and n>=384:
        assert vm.noreturn=='allocator-or-capacity-handler' and not opens and not dealloc
    else:
        assert len(opens)==(0 if nul is not None else 1)
        expected=1 if nul is not None or errno else 0;assert vm.read(out,4)==expected
        if opens:
            assert opens[0]['flags']==(0x1000a01 if write else 0x1000000)
            assert opens[0]['promoted_mode']==438 and bytes.fromhex(opens[0]['path_bytes_hex'])==bytes(data)+b'\0'
        if n>=384:
            assert dealloc==[dict(kind='deallocation',pointer=0x60000000,bytes=n+1,alignment=1)]
        else:assert not dealloc
        if nul is not None:
            assert vm.read(out+8,8)==vm.symaddr['l_anon.fe79d0da482d11692d25899e0a8a72b8.79']
        elif errno:assert vm.read(out+8,8)==((errno<<32)|2)
        else:assert vm.read(out+4,4)==7
        assert not any(e['kind']=='out-of-selected-options-custom-error' for e in vm.events)
    return dict(n=n,nul=nul,write=write,errno=errno,allocation_failure=oom,allocations=alloc,deallocations=dealloc,open_calls=len(opens),
      terminal=vm.noreturn or ('static-NUL-Error' if nul is not None else 'Os-Error' if errno else 'File'),steps=len(vm.trace),trace_sha256=sha(canonical(vm.trace))),vm

def evaluate(functions,objects):
    rows=[]
    for n in (0,1,2,14,15,16,17,31,32,127,383,384,385,4095):
        positions=[None]+sorted(set([0,n//2,n-1])) if n else [None]
        for nul in positions:
            for write in (False,True):rows.append(check_path(functions,objects,n,nul,write)[0])
        for write in (False,True):rows.append(check_path(functions,objects,n,None,write,errno=13)[0])
        if n>=384:rows.append(check_path(functions,objects,n,None,False,oom=True)[0])
    return rows

def ir_evidence():
    closure=load(D/'compiled-manifest.json');refs=closure['source_reference_map'];assert len(refs)==146
    plan=load(D/'compiler-plan.json');rec=load(D/'compiler-receipt.json');cleanup=load(D/'compiler-cleanup.json')
    assert sha((D/'compiler-plan.json').read_bytes())=='9c949b21460a3f5343c4b3d23f84f60b57f7fc111dcf159ea58dee329db0310d'
    assert sha((D/'compiled-manifest.json').read_bytes())==plan['compiled_manifest_sha256']
    assert rec['argv']==plan['argv'] and rec['environment']==plan['environment'] and rec['exit_code']==0 and not rec['timed_out']
    assert rec['direct_child_waited'] and rec['owned_group_absent'] and cleanup['owned_scratch_removed']
    assert sha(Path(plan['argv'][0]).read_bytes())==closure['compiler_sha256']==plan['compiler_sha256']
    assert sha((B/'compiler-version.stdout').read_bytes())==closure['compiler_version_stdout_sha256']
    assert closure['source_manifest']['tree_sha256']=='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
    assert sha(canonical(closure['source_manifest']['members']))==closure['source_manifest']['tree_sha256']
    assert sha(canonical(closure['compiled_members']))==closure['compiled_tree_sha256']
    append=(D/'generic-open-append.inc.rs').read_bytes();assert sha(append)==closure['append_sha256']
    actual=[]
    for row in refs:
        b=checked(R/row['source'],row)
        if row['path']==closure['append_path']:b+=append
        actual.append(dict(path=row['path'],bytes=len(b),sha256=sha(b)))
    assert actual==closure['compiled_members']
    raw=gzip.decompress((D/'generic-open.ll.gz').read_bytes());archive=load(D/'generic-open.ll-archive.json')
    assert len(raw)==archive['raw_bytes'] and sha(raw)==archive['raw_sha256']
    functions=ir_model.extract(raw.decode());selected,names=ir_model.select(functions);rows=ir_model.evaluate(selected,names)
    assert all(r['external_native_symbol']==SYMBOLS[0] for r in rows)
    # Retention is an active global operand, never a comment annotation.
    lines=[l for l in raw.decode().splitlines() if l.startswith('@')]
    pointers=[l for l in lines if 'NATIVE_OPEN_READ_PATH_V1' in l or 'NATIVE_OPEN_CREATE_PATH_V1' in l]
    assert len(pointers)==3 and any(l.startswith('@llvm.used =') and all(x in l for x in ('NATIVE_OPEN_READ_PATH_V1','NATIVE_OPEN_CREATE_PATH_V1')) for l in pointers)
    return selected,names,rows

def options_reference(bits,custom,mode):
    read,write,append,truncate,create,new=bits
    if not (read or write or append):return None
    if not write and not append and (truncate or create or new):return None
    if append and truncate and not new:return None
    access=(2 if read else 1) | 8 if append else 2 if read and write else 1 if write else 0
    creation=0xa00 if new else (0x200 if create else 0)|(0x400 if truncate else 0)
    return 0x1000000|access|creation|(custom&0xfffffffc)

def options_cases(functions,objects):
    rows=[];entry=sym(functions,'4File6open_c')
    for mask in range(64):
        bits=[bool(mask&(1<<i)) for i in range(6)]
        for custom in (0,3,0x800,0x403):
            for mode in (0,438,0xffff):
                vm=Native(functions,objects);o=0x21000000;p=0x21010000;out=0x21020000
                vm.blob(o,bytes(12));vm.blob(p,b'x\0');vm.blob(out,bytes(16));vm.path_extent=2
                vm.write(o,custom,4);vm.write(o+4,mode,2)
                for i,b in enumerate(bits):vm.write(o+6+i,b,1)
                vm.regs[0]=out;vm.regs[1]=p;vm.regs[2]=o;vm.run(entry)
                opens=[e for e in vm.events if e['kind']=='open-interface'];errors=[e for e in vm.events if e['kind']=='out-of-selected-options-custom-error']
                expected=options_reference(bits,custom,mode)
                assert len(opens)==int(expected is not None) and len(errors)==int(expected is None),(mask,custom,vm.events)
                if opens:assert opens[0]['flags']==expected and opens[0]['promoted_mode']==mode and vm.read(out,4)==0
                else:assert vm.read(out,4)==1 and errors[0]['kind_discriminant']==20 and errors[0]['message_length'] in (58,61)
                rows.append(dict(option_mask=mask,custom_flags=custom,mode=mode,open_flags=expected,custom_error=bool(errors),steps=len(vm.trace)))
    # Finite hostile sequences test back edges only; they do not prove a private retry cap.
    retry=[]
    for sequence,changed_global in [(s,g) for s in ([7],[-4,7],[-4,-4,7],[-4,-13]) for g in (False,True)]:
        vm=Native(functions,objects);o=0x21000000;p=0x21010000;out=0x21020000
        vm.blob(o,bytes(12));vm.write(o+4,438,2);vm.write(o+6,1,1);vm.blob(p,b'x\0');vm.blob(out,bytes(16));vm.path_extent=2
        vm.regs[0]=out;vm.regs[1]=p;vm.regs[2]=o;vm.opens=list(sequence)
        if changed_global:vm.write(vm.osglobal,0,8)
        vm.run(entry)
        opens=[e for e in vm.events if e['kind']=='open-interface'];assert len(opens)==len(sequence)
        assert vm.read(out,4)==int(sequence[-1]<0)
        if sequence[-1]<0:assert vm.read(out+8,8)==((-sequence[-1]<<32)|2)
        assert all(e['flags']==0x1000000 and e['promoted_mode']==438 for e in opens)
        retry.append(dict(sequence=sequence,synthetic_OS_table_initially_different=changed_global,observed_calls=len(opens),terminal='Os' if sequence[-1]<0 else 'File',private_retry_bound=False))
    return rows,retry

def core_cases(functions,objects):
    rows=[]
    for n in (0,1,2,15,16,17,32,384):
        for alignment in range(8):
            for position in [None]+list(range(n)):
                vm=Native(functions,objects);p=0x24000000+alignment;out=0x24010000;data=bytearray(b'z'*n)
                if position is not None:data[position]=0
                vm.blob(p,data);vm.blob(out,bytes(24));vm.regs[0]=p;vm.regs[1]=n;vm.regs[8]=out;vm.run(SYMBOLS[2])
                valid=position is not None and position==n-1
                assert vm.read(out,8)==int(not valid)
                if valid:assert vm.read(out+8,8)==p and vm.read(out+16,8)==n
                elif position is None:assert vm.read(out+8,8)==1
                else:assert vm.read(out+8,8)==0 and vm.read(out+16,8)==position
                assert not vm.events, 'core validator invokes no external interface in retained body'
                rows.append(dict(length=n,alignment=alignment,first_NUL=position,valid=valid,steps=len(vm.trace)))
    return rows

def special_cases(functions,objects):
    rows=[];spec=sym(functions,'SpecNewImpl13spec_new_impl')
    for n in ((1<<63)-2,(1<<63)-1):
        vm=Native(functions,objects);vm.regs[0]=0x22000000;vm.regs[1]=n;vm.regs[8]=0x22010000;vm.alloc_fail=True
        try:vm.run(spec)
        except StopIteration:pass
        assert vm.noreturn=='allocator-or-capacity-handler'
        alloc=[e for e in vm.events if e['kind']=='allocation']
        assert len(alloc)==int(n==(1<<63)-2)
        if alloc:assert alloc[0]['bytes']==n+1 and alloc[0]['alignment']==1
        rows.append(dict(scope='synthetic register arithmetic only; no actual huge Rust slice or backing constructed',n=n,terminal=vm.noreturn,allocations=alloc))
    # Selected CString callback landingpad state, not a claim about actual unwind-table selection.
    vm=Native(functions,objects);helper=sym(functions,'run_with_cstr_allocating')
    vm.sp-=96;vm.regs[0]=0x23000000;vm.regs[19]=0x60000000;vm.regs[20]=385;vm.blob(0x60000000,b'x'*384+b'\0')
    try:vm.run(helper,entry=0xa43c)
    except StopIteration:pass
    dealloc=[e for e in vm.events if e['kind']=='deallocation'];assert dealloc==[dict(kind='deallocation',pointer=0x60000000,bytes=385,alignment=1)]
    assert vm.read(0x60000000,1)==0 and vm.noreturn=='unwind-resume'
    rows.append(dict(scope='synthetic preserved pointer/length and landingpad entry; private unwinder selection pending',terminal=vm.noreturn,deallocations=dealloc,steps=len(vm.trace)))
    return rows

def source_evidence(objects,ns):
    # The existing source packet is frozen at the exact platform revision. Rehash
    # its whole files and verbatim excerpts rather than trusting its conclusions.
    prior=load(R/'verification/swift-guarded-snapshot-native-interface-bounds/source-evidence.json')['entries'];rows=[]
    for row in prior:
        p=R/row['path'];b=p.read_bytes();assert sha(b)==row['file_sha256']
        excerpt=''.join(b.decode().splitlines(keepends=True)[row['first_line']-1:row['last_line']])
        assert excerpt==row['source'] and sha(excerpt.encode())==row['excerpt_sha256'];rows.append(row)
    custody=load(R/'verification/swift-guarded-snapshot-native-interface-bounds/input-custody.json');assert custody['rust_revision']=='b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
    p=R/'verification/swift-guarded-snapshot-stdlib-resource-source/official-source/library/std/src/fs.rs'
    assert sha(p.read_bytes())=='9d6d8134748d4fa301339478ed6fdeb5fa6f555d4c39a83d66aefbdf744f4054'
    lines=p.read_text().splitlines(keepends=True)
    for first,last,claim in [(568,570,'generic File::open<&Path> selects read true'),(1978,1984,'generic OpenOptions::open borrows Path and calls platform File open')]:
        excerpt=''.join(lines[first-1:last]);rows.append(dict(path=str(p.relative_to(R)),file_sha256=sha(p.read_bytes()),first_line=first,last_line=last,source=excerpt,excerpt_sha256=sha(excerpt.encode()),claim=claim))
    _,obj,m=objects['std'];symbols={s['name']:s for s in m['symbols']};prefix='l_anon.fe79d0da482d11692d25899e0a8a72b8.'
    data,off,sec=ns['at_address'](obj['data'],m,symbols[prefix+'79']['value'],24)
    assert struct.unpack('<3Q',data)==(0,42,20) and symbols[prefix+'79']['value']%4==0
    relocation=[r for r in m['relocations'] if r['section']==sec['index'] and r['address']==symbols[prefix+'79']['value']-sec['address']]
    assert len(relocation)==1 and relocation[0]['target']==prefix+'78' and relocation[0]['type']==0
    message,mo,_=ns['at_address'](obj['data'],m,symbols[prefix+'78']['value'],42);assert message==b'file name contained an unexpected NUL byte'
    literals=[]
    for n,length,text in [('368',58,b'must specify at least one of read, write, or append access'),('369',61,b'creating or truncating a file requires write or append access')]:
        raw,offset,_=ns['at_address'](obj['data'],m,symbols[prefix+n]['value'],length);assert raw==text
        literals.append(dict(symbol=prefix+n,message=raw.decode(),length=length,object_offset=offset))
    static=dict(symbol=prefix+'79',data_hex=data.hex(),object_offset=off,message=message.decode(),message_object_offset=mo,message_relocation=relocation[0],kind=20,tag_bits=0,invalid_options_literals=literals)
    contract=load(R/'verification/swift-guarded-snapshot-native-interface-bounds/contract.json')
    records=contract['open_records'];fixed=sum(r['fixed_bytes'] for r in records);multiplicity=sum(r['path_byte_multiplicity'] for r in records)
    errors=contract['error_records'];assert len(records)+fixed==768 and multiplicity==7 and len(errors)+sum(r['fixed_bytes'] for r in errors)==23
    return rows,static,dict(open='768+7*n',error_native=23,fixed_records=len(records),fixed_operand_bytes=fixed,path_extent_multiplicity=multiplicity,
      price_scope='Inherited logical public interface plus requested backing; private implementation effects, retries, panic/OOM, CPU/time/RSS and physical stack remain outside the unit; no actual root pricing grant.')

def controls(functions,objects,ir,names,ns):
    rows=[]
    def rejected(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,IndexError) as e:rows.append(dict(name=label,rejected=True,reason=str(e)[:600]));return
        raise AssertionError(('hostile-control-escaped',label))
    def native(label,needle,address,value,n,nul=None,write=False,errno=0):
        symbol=sym(functions,needle);assert address in [i['address'] for i in functions[symbol]['instructions']]
        rejected(label,lambda:check_path(functions,objects,n,nul,write,errno=errno,words={(symbol,address):value}))
    native('threshold384-moved-to385','11OpenOptions5__open',0x2ec78,0xf106005f,384)
    native('short-terminator-length-no-plus1','11OpenOptions5__open',0x2eca0,0x91000281,15)
    native('short-native-call-bypasses-validator','11OpenOptions5__open',0x2ecac,0x14000009,3,nul=1)
    native('borrowed-CString-request-is-n-plus2','SpecNewImpl13spec_new_impl',0x6630,0xb1000834,384)
    native('CString-no-NUL-success-branch-inverted','SpecNewImpl13spec_new_impl',0x66a8,0x37000080,384)
    native('samebacking-CString-reserve-branch-inverted','7CString19__from_vec_unchecked',0x5220,0x540002e1,384)
    native('samebacking-CString-shrink-bypass-inverted','7CString19__from_vec_unchecked',0x5234,0x54000448,384)
    native('heap-deallocation-length-register-changed','run_with_cstr_allocating',0xa418,0xaa1503e1,384)
    native('native-read-access-disabled','4File6open_c',0x2d2dc,0x1400001c,3)
    native('native-open-cloexec-removed','4File6open_c',0x2d3ac,0x2a1703e1,3)
    native('native-Os-errno-shift32-removed','4File6open_c',0x2d408,0xaa160108,3,errno=13)
    native('core-terminal-NUL-position-comparison-inverted','CStr19from_bytes_with_nul',0x59b4,0x54000080,3)
    symbol=sym(functions,'11OpenOptions5__open')
    rejected('static-NUL-error-relocation-changed',lambda:check_path(functions,objects,3,1,relocations={(symbol,0x2ecb0):'l_anon.fe79d0da482d11692d25899e0a8a72b8.368',(symbol,0x2ecb4):'l_anon.fe79d0da482d11692d25899e0a8a72b8.368'}))
    # Decoded behavior rejects mutations while disassembler assembly text remains original.
    def changed_ir(label,pattern,before,after):
        changed=copy.deepcopy(ir);symbol=names[pattern];body=changed[symbol]['body'];assert before in body
        changed[symbol]['body']=body.replace(before,after,1)+'; preserved original annotation '+before+'\n'
        rejected(label,lambda:ir_model.evaluate(changed,names))
    changed_ir('IR-read-bit-active-store-removed-comment-retained','_4File4openR','store i8 1, ptr %10, align 2','store i8 0, ptr %10, align 2')
    changed_ir('IR-default-append-bit-changed','_11OpenOptions3new','store i8 0, ptr %2, align 4','store i8 1, ptr %2, align 4')
    changed_ir('IR-output-write-argument-false','26native_open_create_path_v1','ptr align 4 %_7, i1 zeroext true','ptr align 4 %_7, i1 zeroext false')
    changed_ir('IR-create-new-argument-false','26native_open_create_path_v1','ptr align 4 %_5, i1 zeroext true','ptr align 4 %_5, i1 zeroext false')
    changed_ir('IR-generic-native-call-disconnected','_11OpenOptions4openR','br label %bb1','br label %bb2')
    changed_ir('IR-path-length-pointer-load-disconnected','_RNvXNtCsjIpoRzUjyHQ_4core7convertRNt','ptr %self, i64 8','ptr %self, i64 0')
    # Cargo/frozen custody and raw object data are independently checked before semantic evaluation.
    row=load(D/'compiled-manifest.json')['source_reference_map'][0]
    rejected('source-whole-file-digest-tampered',lambda:checked(R/row['source'],row|dict(sha256='0'*64)))
    corrupted=copy.deepcopy(objects);a,obj,m=corrupted['std'];obj['data']=bytearray(obj['data']);offset=functions[SYMBOLS[0]]['instructions'][0]['object_offset'];obj['data'][offset]^=1
    rejected('native-byte-tampered-with-frozen-annotation-preserved',lambda:native_bodies(corrupted,ns))
    corrupted=copy.deepcopy(objects);actual=next(r for r in corrupted['std'][2]['relocations'] if r['section']==1 and r['address']==0x2eca4);actual['target']='_open'
    rejected('native-relocation-tampered-with-original-disassembly-preserved',lambda:native_bodies(corrupted,ns))
    native('unsupported-active-word-fails-closed','11OpenOptions5__open',0x2ec78,0xd4200020,3)
    return rows

def main():
    inputs,objects,ns=custody();functions=native_bodies(objects,ns);rows=evaluate(functions,objects)
    ir,names,ircases=ir_evidence();options,retry=options_cases(functions,objects);hostile=controls(functions,objects,ir,names,ns);special=special_cases(functions,objects);source,static,pricing=source_evidence(objects,ns);core=core_cases(functions,objects)
    put('input-bindings.json',inputs);put('native-bodies.json',functions);put('native-cases.json',rows)
    put('LLVM-bodies.json',ir);put('LLVM-cases.json',ircases);put('options-cases.json',options);put('retry-cases.json',retry);put('controls.json',hostile)
    put('special-cases.json',special);put('source-evidence.json',source);put('static-error.json',static);put('interface.json',pricing)
    put('core-CStr-cases.json',core)
    baseline=gzip.decompress((B/'source146.ll.gz').read_bytes());assert sha(baseline)=='782a8a4c0abe1e47a8e9571fb9370ae52e5e780ef084251a6e98a99d49cea1d0'
    original=ir_model.extract(baseline.decode());assert not any(any(k in symbol for k in ('4File4open','11OpenOptions','small_c_string','SpecNewImpl')) for symbol in original)
    put('baseline-absence.json',dict(frozen_LLVM_raw_sha256=sha(baseline),active_definitions=len(original),generic_File_open_OpenOptions_CString_bodies_present=False,forced_query_closes_only_new_inert_instantiations=True))
    print(json.dumps(dict(functions=len(functions),instructions=sum(len(r['instructions']) for r in functions.values()),cases=len(rows),LLVM_functions=len(ir),options_cases=len(options),core_CStr_cases=len(core),controls=len(hostile))))

if __name__=='__main__':main()
