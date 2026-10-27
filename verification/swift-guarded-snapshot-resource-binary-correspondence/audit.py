"""Read-only independent custody, LLVM, native-byte and relocation checks."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from binary_format import archive_members, macho, at_address

D=Path(__file__).resolve().parent
R=D.parents[1]
TREE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
DEALLOC='_RNvMs3_NtCs6zY7rJBZy9D_5alloc7raw_vecNtB5_11RawVecInner10deallocateCsfhX9oYWaTAx_5gimli'
RAWU8='_RNvXs1_NtCs6zY7rJBZy9D_5alloc7raw_vecINtB5_6RawVechENtNtNtCsjIpoRzUjyHQ_4core3ops4drop4Drop4dropCsfhX9oYWaTAx_5gimli'
SHIM='__RNvCsdtSMxSA38aw_7___rustc14___rust_dealloc'
VECTORS={'mixer_vm::experimental_swift_reactor::cache::SwiftSlot':(136,8),'mixer_vm::experimental::cache::decode::Patch':(32,8),'core::option::Option<mixer_vm::experimental_swift_reactor::cache::ScanPlan>':(56,8)}

def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def read(n): return json.loads((D/n).read_text())
def raw(n): return gzip.decompress((D/(n+'.gz')).read_bytes())
def put(n,x): (D/n).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def counted(data):
    pos=8;count=struct.unpack_from('<Q',data)[0];assert count<=64;out=[]
    for _ in range(count):
        size=struct.unpack_from('<Q',data,pos)[0];pos+=8;assert size<4096
        b=data[pos:pos+size];assert len(b)==size and b'\0' not in b;out.append(b.decode());pos+=size
    assert pos==len(data) and len(data)<=16384
    return out
def checked(row,path):
    if 'resolved_path' in row:assert str(path.resolve())==row['resolved_path']
    else:assert not path.is_symlink()
    b=path.read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256'],str(path)
    return b

def frozen(path,digest):
    data=(R/path/'seal.json').read_bytes();assert sha(data)==digest
    rows=json.loads(data)['members']
    for row in rows: checked(row,R/path/row['path'])
    return dict(path=str(path),seal_sha256=digest,members=len(rows),bytes=sum(x['bytes'] for x in rows))

def functions(text):
    lines=text.splitlines(keepends=True);result={};last=None;i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('; ') and not line.startswith(('; call ','; invoke ','; Function Attrs:')): last=(i,line[2:].rstrip())
        if line.startswith('define '):
            j=i+1
            while lines[j]!='}\n': j+=1
            symbol=line.split('@',1)[1].split('(',1)[0]
            start,name=last if last and i-last[0]<=3 else (i,'@'+symbol)
            body=''.join(lines[start:j+1]);assert name not in result,name
            result[name]=dict(symbol=symbol,body=body,start_line=start+1,end_line=j+1,sha256=sha(body.encode()))
            last=None
            i=j
        i+=1
    return result

def calls(body):
    instructions='\n'.join(line for line in body.splitlines() if not line.lstrip().startswith(';'))
    return re.findall(r'\b(?:call|invoke)\b[^\n]*?@([^ (]+)',instructions)

def check_ir(f):
    selected={}
    def get(name):
        row=f[name];selected[name]=row;return row['body']
    for ty,(size,align) in VECTORS.items():
        vec='alloc::vec::Vec<'+ty+'>';rv='alloc::raw_vec::RawVec<'+ty+'>'
        body=get('<'+rv+' as core::ops::drop::Drop>::drop')
        assert calls(body)==[DEALLOC] and f'i64 {align}, i64 {size})' in body
        drop=get('<'+vec+' as core::ops::drop::Drop>::drop')
        assert 'i64 16' in drop and '%len = load i64' in drop
        glue=get('core::ptr::drop_glue::<'+vec+'>')
        assert f['<'+vec+' as core::ops::drop::Drop>::drop']['symbol'] in calls(glue)
        assert f['core::ptr::drop_glue::<'+rv+'>']['symbol'] in calls(glue)
        get('core::ptr::drop_glue::<'+rv+'>')
        if ty.endswith('SwiftSlot'):
            sl=get('core::ptr::drop_glue::<['+ty+']>')
            assert f['core::ptr::drop_glue::<['+ty+']>']['symbol'] in calls(drop)
            assert '%_7 = icmp eq i64 %1, %_1.1' in sl and 'add i64 %3, 1' in sl
            # Normal and unwind paths visit only the live slice length.
            assert sl.count('getelementptr inbounds nuw %"experimental_swift_reactor::cache::SwiftSlot"')==2
            pending=[f['core::ptr::drop_glue::<'+ty+'>']['symbol']];seen=set()
            bysymbol={r['symbol']:(n,r) for n,r in f.items()}
            while pending:
                symbol=pending.pop()
                if symbol in seen or symbol not in bysymbol:continue
                seen.add(symbol);name,row=bysymbol[symbol]
                if not name.startswith('core::ptr::drop_glue::<'): continue
                selected[name]=row;pending+=calls(row['body'])
            nested=[n for n in selected if n.startswith('core::ptr::drop_glue::<alloc::vec::Vec<') and n!= 'core::ptr::drop_glue::<'+vec+'>']
            assert any('DecodedInstruction' in n for n in nested)
            assert any('Vec<mixer_vm::Type>' in n for n in nested)
            assert any('Vec<u32>' in n for n in nested)
        else:
            # Patch and Option<ScanPlan> carry no drop payload in this exact tree.
            assert calls(drop)==[]
    chain=['std::fs::File','std::sys::fs::unix::File','std::sys::fd::unix::FileDesc','std::os::fd::owned::OwnedFd']
    for a,b in zip(chain,chain[1:]):
        assert calls(get('core::ptr::drop_glue::<'+a+'>'))==[f['core::ptr::drop_glue::<'+b+'>']['symbol']]
    owned='<std::os::fd::owned::OwnedFd as core::ops::drop::Drop>::drop'
    assert calls(get('core::ptr::drop_glue::<'+chain[-1]+'>'))==[f[owned]['symbol']]
    body=get(owned);pre='std::sys::fs::unix::debug_assert_fd_is_open'
    assert calls(body)==[f[pre]['symbol'],'close'] and body.count('@close(')==1
    assert '%_5 = call i32 @close(i32 %self2)' in body and 'ret void' in body
    prebody=get(pre)
    assert 'call i32 (i32, i32, ...) @fcntl(i32 %fd, i32 1)' in prebody
    assert 'icmp eq i32 %_2, -1' in prebody and '@__error()' in prebody and 'icmp eq i32 %_3, 9' in prebody
    assert '@_RNvNtCs1SSuMAdGM58_3std7process5abort()' in prebody and 'unreachable' in prebody
    assert prebody.count('@fcntl(')==1 and prebody.count('@__error(')==1
    return selected

def native_inputs():
    inputs=read('installed-inputs.json')['archives']|read('additional-installed-inputs.json')['archives']
    parsed={}
    for name,row in inputs.items():
        data=checked(row,Path(row['path']));members=archive_members(data)
        objects=[m for m in members if m['name'].endswith('.o')];assert len(objects)==1
        obj=objects[0];m=macho(obj['data']);parsed[name]=(row,obj,m)
        text=next(s for s in m['sections'] if s['segment']=='__TEXT' and s['name']=='__text')
        assert text['size']>0 and any(s['name']=='__bitcode' for s in m['sections'])
    return parsed

RELOCS={'ARM64_RELOC_UNSIGNED':0,'ARM64_RELOC_BRANCH26':2,'ARM64_RELOC_PAGE21':3,'ARM64_RELOC_PAGEOFF12':4,'ARM64_RELOC_GOT_LOAD_PAGE21':5,'ARM64_RELOC_GOT_LOAD_PAGEOFF12':6}
def native_selection(parsed):
    selected={};checks=0
    for label,selection in [('disassembly','native-symbol-selection.json'),('supplementary-disassembly','supplementary-native-symbol-selection.json'),('abort-internal-disassembly','abort-internal-native-symbol-selection.json'),('file-origin-disassembly','file-origin-native-symbol-selection.json')]:
        for archive,symbols in read(selection)['llvm_symbols'].items():
            output=raw(label+'-'+archive+'.stdout').decode();_,obj,m=parsed[archive]
            # Validate every emitted instruction and relocation against independently parsed bytes.
            blocks={};current=None
            for line in output.splitlines():
                match=re.fullmatch(r'([0-9a-f]+) <([^>]+)>:',line)
                if match:
                    current=match[2];assert current not in blocks
                    blocks[current]=dict(address=int(match[1],16),instructions=[],relocations=[])
                ins=re.match(r'\s*([0-9a-f]+): ([0-9a-f]{8})\s+(.+)',line)
                rel=re.match(r'\s*([0-9a-f]+):\s+(ARM64_RELOC_[A-Z0-9_]+)\s+(.+)',line)
                if ins:
                    assert current;address=int(ins[1],16);word=int(ins[2],16)
                    data,offset,section=at_address(obj['data'],m,address,4)
                    assert struct.unpack('<I',data)[0]==word
                    blocks[current]['instructions'].append(dict(address=address,word=word,assembly=ins[3],object_offset=offset));checks+=1
                if rel:
                    assert current;address=int(rel[1],16);_,_,section=at_address(obj['data'],m,address,4)
                    rows=[r for r in m['relocations'] if r['section']==section['index'] and r['address']==address-section['address'] and r['type']==RELOCS[rel[2]] and r['target']==rel[3]]
                    assert len(rows)==1
                    blocks[current]['relocations'].append(rows[0]|dict(instruction_address=address));checks+=1
            assert set(blocks)=={'_'+s for s in symbols}
            for symbol,block in blocks.items():
                ns=[s for s in m['symbols'] if s['name']==symbol];assert len(ns)==1 and ns[0]['value']==block['address']
                ins=block['instructions'];assert ins and [r['address'] for r in ins]==list(range(block['address'],ins[-1]['address']+4,4))
                b=b''.join(struct.pack('<I',i['word']) for i in ins)
                selected[symbol]=block|dict(archive=archive,archive_sha256=parsed[archive][0]['sha256'],archive_member=obj['name'],archive_member_offset=obj['offset'],archive_member_sha256=sha(obj['data']),instruction_bytes_hex=b.hex(),instruction_bytes_sha256=sha(b),output=label+'-'+archive+'.stdout.gz')
    return selected,checks

def signed(n,bits): return n-(1<<bits) if n&(1<<(bits-1)) else n
def eval_rawvec(parsed,symbol,capacity,element_size,alignment,changed_words=None,changed_relocations=None):
    """Bounded offline dataflow evaluation of the two selected native RawVec bodies."""
    _,obj,m=parsed['gimli'];sym={r['name']:r['value'] for r in m['symbols']};pc=sym[symbol]
    regs=[0]*31;regs[0]=0x1000;regs[1]=alignment;regs[2]=element_size;sp=0x10000
    memory={0x1000:capacity,0x1008:0x2000};trace=[];changed_words=changed_words or {};changed_relocations=changed_relocations or {}
    reloc={r['address']:r['target'] for r in m['relocations'] if r['section']==1 and r['type']==2}
    reloc.update(changed_relocations)
    def reg(i):return sp if i==31 else regs[i]
    for step in range(64):
        rawword,_,_=at_address(obj['data'],m,pc,4);w=changed_words.get(pc,struct.unpack('<I',rawword)[0]);trace.append(pc)
        rd=w&31;rn=(w>>5)&31
        if w==0xd65f03c0:return dict(request=None,steps=step+1,trace=trace)
        if (w&0xff000000) in (0x91000000,0xd1000000):
            imm=(w>>10)&0xfff;assert not ((w>>22)&1)
            value=reg(rn)+(imm if w&0xff000000==0x91000000 else -imm)
            if rd==31:sp=value
            else:regs[rd]=value
        elif (w&0xffc00000) in (0xf9400000,0xf9000000):
            address=reg(rn)+8*((w>>10)&0xfff)
            if w&0xffc00000==0xf9400000:regs[rd]=memory[address]
            else:memory[address]=reg(rd)
        elif w&0xffe0fc00==0x9b007c00:
            regs[rd]=(reg(rn)*reg((w>>16)&31))&((1<<64)-1)
        elif w&0x7f800000==0x52800000:
            assert ((w>>21)&3)==0;regs[rd]=(w>>5)&0xffff
        elif w&0x7f000000==0x34000000:
            if reg(rd)==0:pc+=signed((w>>5)&0x7ffff,19)*4;continue
        elif w&0xfc000000==0x14000000:
            target=reloc.get(pc)
            if target==SHIM:return dict(request=[regs[0],regs[1],regs[2]],steps=step+1,trace=trace)
            if target:
                assert target=='_'+DEALLOC;pc=sym[target];continue
            pc+=signed(w&0x3ffffff,26)*4;continue
        else:raise AssertionError('Unsupported native instruction '+hex(w))
        pc+=4
    raise AssertionError('RawVec native control flow exceeded64 steps')

def check_native_semantics(selected,parsed):
    r=selected['_'+RAWU8];assert [i['word'] for i in r['instructions'][:2]]==[0x52800021,0x52800022]
    assert [x['target'] for x in r['relocations']]==['_'+DEALLOC]
    d=selected['_'+DEALLOC];assert [x['target'] for x in d['relocations']]==[SHIM]
    vectors=[]
    for size,align in ((0,1),(1,1),(4,4),(32,8),(40,8),(56,8),(136,8)):
        for cap in (0,1,2,7,64,65536):
            got=eval_rawvec(parsed,'_'+DEALLOC,cap,size,align)
            expected=[0x2000,cap*size,align] if cap and size else None
            assert got['request']==expected
            vectors.append(dict(capacity=cap,element_size=size,alignment=align,expected_request=expected,**got))
    for cap in (0,1,17,65536):
        got=eval_rawvec(parsed,'_'+RAWU8,cap,999,999)
        assert got['request']==([0x2000,cap,1] if cap else None)
    close=next(v for n,v in selected.items() if 'drop_glue' in n and 'FileDesc' in n)
    assert [r['word'] for r in close['instructions']]==[0xb9400000,0x14000000]
    assert [r['target'] for r in close['relocations']]==['_close']
    os_functions='__RNvNtNtNtCsjIpoRzUjyHQ_4core2io5error12os_functions12OS_FUNCTIONS'
    os_rows=[]
    for name,row in selected.items():
        if row['archive']!='std' or not any(k in name for k in ('4File4read','Read4read','4File8read_buf','4File8metadata','Write5write','Seek15stream_position')):continue
        edges=[r['target'] for r in row['relocations']]
        assert '___error' in edges and os_functions in edges
        assert any(i['assembly'].startswith('orr\t') and 'lsl #32' in i['assembly'] for i in row['instructions'])
        assert any(i['word']==0x52800048 for i in row['instructions']) # mov w8,#2 => TAG_OS
        assert not any('alloc' in x for x in edges)
        os_rows.append(name)
    assert len(os_rows)==6
    setter=next(v for n,v in selected.items() if 'set_functions_inner' in n)
    assert len(setter['instructions'])==3 and len(setter['relocations'])==2
    assert all(r['target']==os_functions for r in setter['relocations'])
    assert any(r['target']=='_abort' for n,v in selected.items() if 'abort_internal' in n for r in v['relocations'])
    return dict(native_request_cases=vectors,additional_u8_cases=4,File_origin_Os_bodies=os_rows,FileDesc_installed_release_has_precheck_elided=True,query_File_precheck_retained=True)

def static_error_data(parsed,selected):
    _,obj,m=parsed['std'];syms={r['name']:r for r in m['symbols']}
    prefix='l_anon.fe79d0da482d11692d25899e0a8a72b8.';sym=syms[prefix+'79']
    data,off,section=at_address(obj['data'],m,sym['value'],24)
    rel=[r for r in m['relocations'] if r['section']==section['index'] and r['address']==sym['value']-section['address']]
    assert len(rel)==1 and rel[0]['target']==prefix+'78'
    _,length,kind=struct.unpack('<3Q',data);assert (length,kind)==(42,20) and sym['value']%4==0
    string,soff,_=at_address(obj['data'],m,syms[prefix+'78']['value'],length)
    assert string==b'file name contained an unexpected NUL byte'
    constructor=next(v for n,v in selected.items() if 'small_c_string24run_with_cstr_allocating' in n)
    assert any(r['target']==sym['name'] for r in constructor['relocations'])
    return dict(symbol=sym,object_offset=off,raw_bytes_hex=data.hex(),relocation=rel[0],message_symbol=prefix+'78',message_object_offset=soff,message=string.decode(),length=length,ErrorKind_discriminant=kind,tag_bits=0,scope='Installed allocating File path helper returns this static message on NUL; its dynamic callback path is outside the closed error constructor branch.')

def main(write=False):
    packets=[frozen(Path('verification/swift-guarded-snapshot-resource-cost-independent'),'649a6005543ea8bc147a70a4fc17a62c455ae9192d1d8d72197a5b86cb711ddc'),frozen(Path('verification/swift-guarded-snapshot-source146-closure-layouts'),'d630481ae157d9b406334031d6592a24fa8e96da5b9fb298f255edfa70782e9b')]
    acceptance=R/'verification/swift-semantic-adapter-root-review/guarded-snapshot-resource-cost-host-acceptance.json'
    assert sha(acceptance.read_bytes())=='854c90f7824676cec2483571d5de4fce27965758e7e583186fa2361d965a118f'
    source_bindings=read('source-bindings.json')
    checked(source_bindings['inherited_source_semantic_review'],R/source_bindings['inherited_source_semantic_review']['path'])
    for row in source_bindings['proof_spans']:
        b=(R/row['path']).read_bytes();assert sha(b)==row['file_sha256']
        assert ''.join(b.decode().splitlines(keepends=True)[row['start']-1:row['end']])==row['source']
    manifest=read('compiled-manifest.json');binding=read('binding.json');receipt=read('compiler-receipt.json')
    assert binding['source_tree_sha256']==TREE and binding['host_tree_sha256']==HOST
    assert manifest['original_source146_bodies_and_lines_unchanged']
    original=manifest['source_manifest']['members'];assert len(original)==146 and sha(canon(original))==TREE
    assert [(x['path'],x['bytes'],x['sha256']) for x in manifest['source_reference_map']]==[(x['path'],x['bytes'],x['sha256']) for x in original]
    new={r['path']:r for r in manifest['compiled_source_members']};assert sha(canon(manifest['compiled_source_members']))==manifest['compiled_tree_sha256']
    assert set(new)=={r['path'] for r in original} and len(new)==146
    changed=[]
    for row in manifest['source_reference_map']:
        b=checked(row,R/row['source']);name=row['path']
        if name in manifest['additions']:
            extra=checked(manifest['additions'][name],D/(Path(name).stem+'-append.inc.rs'));b+=extra;changed.append(name)
        assert len(b)==new[name]['bytes'] and sha(b)==new[name]['sha256']
    assert len(changed)==2 and set(changed)==set(manifest['additions'])
    assert manifest['host_support']['tree_sha256']==HOST and len(manifest['host_support']['members'])==11 and sha(canon(manifest['host_support']['members']))==HOST
    for row in manifest['host_support']['members']:checked(row,R/'verification/swift-real-profile-loader-binding/host'/row['path'])
    for key,name in [('MIXER_LOADER_MANIFEST_SHA256','compiled-manifest.json'),('MIXER_LOADER_COMMAND_SHA256','argv.bin'),('MIXER_LOADER_COMPILE_ENV_SHA256','environment.bin'),('MIXER_LOADER_COMPILER_VERSION_SHA256','compiler-version.stdout')]:
        assert sha((D/name).read_bytes())==binding['compile_identity_keys'][key]==receipt['environment'][key]
    compiler=Path(receipt['argv'][0]);assert sha(compiler.read_bytes())==binding['compile_identity_keys']['MIXER_LOADER_COMPILER_SHA256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
    assert binding['compile_identity_keys']['MIXER_LOADER_COMPILER_VERSION_SHA256']=='352d6857968e80a6357a926ac685b9b07f77c479aaafde33e73a53945e802909'
    assert sha((D/'compile-once.py').read_bytes())==manifest['script_sha256']
    assert sha((R/'verification/swift-guarded-snapshot-source146-callee-storage-layouts/query-named.py').read_bytes())==manifest['frozen_helper_sha256']
    assert counted((D/'argv.bin').read_bytes())==receipt['argv']
    assert dict(x.split('=',1) for x in counted((D/'environment.bin').read_bytes()))=={k:v for k,v in receipt['environment'].items() if k not in binding['compile_identity_keys']}
    argv=receipt['argv'];assert [x for x in argv if x.startswith('--emit=')]==['--emit=llvm-ir='+str(D/'compiler-owned-work/source146.ll')]
    assert all(x in argv for x in ('opt-level=0','codegen-units=1','overflow-checks=yes','panic=unwind','-Zmir-opt-level=0','-Zprint-type-sizes','aarch64-apple-darwin'))
    assert not receipt['timed_out'] and receipt['exit_code']==0 and receipt['elapsed_seconds']<60 and receipt['direct_child_waited'] and receipt['owned_group_absent']
    assert read('compiler-cleanup.json')['owned_scratch_removed'] and not (D/'compiler-owned-work').exists()
    for name in ('source146.ll','compiler.stdout'):
        a=read(name+'-archive.json');b=raw(name);assert len(b)==a['raw_bytes'] and sha(b)==a['raw_sha256']
        packed=(D/(name+'.gz')).read_bytes();assert len(packed)==a['archive_bytes'] and sha(packed)==a['archive_sha256']
    for path in D.glob('*-receipt.json'):
        r=json.loads(path.read_text());assert r['direct_child_waited'] and r['owned_group_absent'] and not r['timed_out']
        label=path.name.removesuffix('-receipt.json')
        for kind,row in r['outputs'].items():
            gz=D/(label+'.'+kind+'.gz');b=gzip.decompress(gz.read_bytes()) if gz.exists() else (D/(label+'.'+kind)).read_bytes()
            assert len(b)==row['bytes'] and sha(b)==row['sha256']
    for inputs in ('installed-inputs.json','compatible-installed-tools.json'):
        for row in read(inputs)['tools'].values():checked(row,Path(row['path']))
    checked(read('compatible-installed-tools.json')['libLLVM'],Path(read('compatible-installed-tools.json')['libLLVM']['path']))
    f=functions(raw('source146.ll').decode());selected_ir=check_ir(f)
    parsed=native_inputs();native,checks=native_selection(parsed);semantics=check_native_semantics(native,parsed);static=static_error_data(parsed,native)
    if (D/'seal.json').exists():
        for row in read('seal.json')['members']:checked(row,D/row['path'])
    report=dict(schema=1,status='passes-bounded-offline-correspondence-with-caller-binding-pending',source_tree_sha256=TREE,host_tree_sha256=HOST,packets=packets,compiler_identity=binding['compile_identity_keys'],LLVM_raw_sha256=sha(raw('source146.ll')),original_source_members=146,append_only_members=2,used_drop_pointers=4,LLVM_functions=selected_ir,native_functions=native,native_byte_and_relocation_checks=checks,native_semantics=semantics,static_File_error=static,source_prices_unchanged=True,whole_host_funding_or_runtime_or_GA=False)
    if (D/'review.json').exists():
        review=read('review.json');assert review['source_tree_sha256']==TREE and review['host_tree_sha256']==HOST
        assert review['evidence']==dict(LLVM_functions=len(selected_ir),installed_native_functions=len(native),native_instruction_byte_and_relocation_checks=checks,bounded_native_RawVec_dataflow_cases=46,hostile_controls=24)
        assert review['native_runtime']=='paused' and not review['root_acceptance_selected_here']
        assert not any(review[k] for k in ('compiled_std_correspondence_complete','source_prices_changed','whole_host_storage_or_work_funded','genuine_loader_writer_or_constructor_execution','healthy_cleanup_close_flush_retirement_refund','FieldLog_OTA_GA_accepted'))
        assert review['inherited_prices_unchanged']==json.loads(acceptance.read_text())['accepted_prices']
    if write:put('correspondence.json',report)
    elif (D/'correspondence.json').exists():assert canon(report)==canon(read('correspondence.json'))
    print(json.dumps(dict(status='passed',LLVM_functions=len(selected_ir),native_functions=len(native),native_byte_and_relocation_checks=checks,rawvec_native_dataflow_cases=len(semantics['native_request_cases'])+4,compiler_runs=1,product_or_native_runtime=False)))
    return report,parsed,f

if __name__=='__main__':main('--write-report' in sys.argv)
