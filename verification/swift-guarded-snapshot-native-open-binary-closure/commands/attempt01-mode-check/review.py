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
    vm.regs[0]=opts;vm.regs[1]=path;vm.regs[2]=len(data);vm.regs[8]=out;vm.opens=[-errno] if errno else [result];vm.alloc_fail=oom
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
            assert opens[0]['promoted_mode']==438 and vm.bytes(opens[0]['path'],n+1)==bytes(data)+b'\0'
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

def main():
    inputs,objects,ns=custody();functions=native_bodies(objects,ns);rows=evaluate(functions,objects)
    put('native-bodies.json',functions);put('native-cases.json',rows)
    print(json.dumps(dict(functions=len(functions),instructions=sum(len(r['instructions']) for r in functions.values()),cases=len(rows))))

if __name__=='__main__':main()
