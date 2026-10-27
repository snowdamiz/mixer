"""Independent offline raw-object review. No imports from producer helpers.

All writes are confined to this directory. The AArch64 evaluator handles only
the retained integer subset, with checked external interface stubs. Assembly
annotation strings never enter decoding, execution, branch or call decisions.
"""
import copy
import datetime
import gzip
import hashlib
import json
import re
import struct
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/swift-guarded-snapshot-native-open-binary-closure'
B = R / 'verification/swift-guarded-snapshot-resource-binary-correspondence'
SEAL = '7b5762f1955fefa2060b0d4fdb4dd393cb8b38c94078159ddf6bc538a22c67f5'
RELEASE = 'f29e7b47e5be01e24cccdf8474ddc5c76bdc1ba0d071197970b9310bff83a6ed'
SOURCE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
MASK = (1 << 64) - 1

def digest(b): return hashlib.sha256(b).hexdigest()
def canon(v): return json.dumps(v, sort_keys=True, separators=(',', ':')).encode()
def load(p): return json.loads(p.read_bytes())
def put(name, value):
    (D / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def exact(p, r):
    b = p.read_bytes()
    assert len(b) == r['bytes'] and digest(b) == r['sha256'], ('digest', str(p))
    return b
def sx(x, n): return (x ^ (1 << (n - 1))) - (1 << (n - 1))
def unique(rows):
    assert len(rows) == 1, rows
    return rows[0]
def named(fs, s): return unique([n for n in fs if s in n])

def sealed(path, expected):
    raw = (path / 'seal.json').read_bytes()
    assert digest(raw) == expected, ('seal', str(path))
    seal = json.loads(raw)
    listed = set()
    for m in seal['members']:
        p = path / m['path']
        assert not p.is_symlink() and '__pycache__' not in p.parts
        exact(p, m); listed.add(m['path'])
    actual = {str(p.relative_to(path)) for p in path.rglob('*') if p.is_file() and p.name != 'seal.json'}
    assert actual == listed, ('unsealed-members', str(path), actual ^ listed)
    return {'path': str(path.relative_to(R)), 'seal_sha256': expected,
            'members': len(listed), 'bytes': sum(m['bytes'] for m in seal['members'])}

def ar_object(raw):
    assert raw[:8] == b'!<arch>\n'
    cursor = 8; found = []
    while cursor < len(raw):
        h = raw[cursor:cursor+60]
        assert len(h) == 60 and h[-2:] == b'`\n'
        size = int(h[48:58]); start = cursor+60; body = raw[start:start+size]
        assert len(body) == size
        name = h[:16].decode().strip()
        if name.startswith('#1/'):
            k = int(name[3:]); name = body[:k].rstrip(b'\0').decode(); body = body[k:]; start += k
        else: name = name.rstrip('/')
        if name.endswith('.o'): found.append((name, body, start))
        cursor += 60 + size + size % 2
    assert cursor == len(raw)
    return unique(found)

def macho(raw):
    # Explicit little-endian MH_OBJECT arm64 header, section, nlist and relocation reader.
    magic, cpu, subtype, kind, commands, cmdbytes, flags, reserved = struct.unpack_from('<8I', raw)
    assert magic == 0xfeedfacf and cpu == 0x100000c and kind == 1
    pos = 32; sections = []; sym = None
    for i in range(commands):
        op, size = struct.unpack_from('<II', raw, pos)
        assert size >= 8 and pos+size <= 32+cmdbytes
        if op == 0x19:
            nsects = struct.unpack_from('<I', raw, pos+64)[0]
            assert size == 72 + nsects*80
            for j in range(nsects):
                v = struct.unpack_from('<16s16sQQIIIIIIII', raw, pos+72+j*80)
                sections.append(dict(index=len(sections)+1, name=v[0].rstrip(b'\0').decode(), address=v[2],
                  size=v[3], offset=v[4], align=v[5], reloff=v[6], nreloc=v[7]))
        if op == 2: sym = struct.unpack_from('<4I', raw, pos+8)
        pos += size
    assert pos == 32+cmdbytes and sym is not None
    off, count, stroff, strlen = sym; strings = raw[stroff:stroff+strlen]
    assert len(strings) == strlen and off+16*count <= len(raw)
    symbols = []
    for i in range(count):
        si, typ, sec, desc, value = struct.unpack_from('<IBBHQ', raw, off+16*i)
        assert si < len(strings)
        symbols.append(dict(name=strings[si:strings.index(0, si)].decode(), section=sec, value=value, type=typ))
    relocs = []
    for s in sections:
        assert s['reloff']+s['nreloc']*8 <= len(raw)
        for i in range(s['nreloc']):
            at = s['reloff']+8*i; addr, info = struct.unpack_from('<iI', raw, at)
            assert 0 <= addr < s['size']
            typ = info >> 28; ext = bool(info & (1 << 27)); idx = info & 0xffffff
            if typ == 10:
                assert not ext; target = 'addend:' + str(sx(idx, 24))
            elif ext: target = symbols[idx]['name']
            elif idx: target = sections[idx-1]['name']
            else: target = 'absolute'
            relocs.append(dict(section=s['index'], address=addr, type=typ, target=target,
              pc_relative=bool(info & (1 << 24)), width_power=(info >> 25) & 3,
              external=ext, record_offset=at))
    return dict(raw=raw, sections=sections, symbols=symbols, relocs=relocs)

def at_address(obj, addr, count):
    sec = unique([s for s in obj['sections'] if s['offset'] and s['address'] <= addr and addr+count <= s['address']+s['size']])
    off = sec['offset'] + addr-sec['address']
    raw = obj['raw'][off:off+count]; assert len(raw) == count
    return raw, off, sec

def objects_and_bodies():
    objects = {}
    for kind, r in load(B / 'installed-inputs.json')['archives'].items():
        name, raw, offset = ar_object(exact(Path(r['path']), r)); obj = macho(raw)
        obj.update(member=name, archive_sha256=r['sha256']); objects[kind] = obj
    fs = load(P / 'native-bodies.json')
    verify_bodies(objects,fs)
    return objects, fs

def verify_bodies(objects,fs):
    for name, f in fs.items():
        o = objects[f['archive']]
        s = unique([s for s in o['symbols'] if s['name'] == name]); assert s['value'] == f['address']
        rows = f['instructions']; first = rows[0]['address']; end = rows[-1]['address']+4
        assert first == f['address'] and [r['address'] for r in rows] == list(range(first, end, 4))
        raw, off, sec = at_address(o, first, end-first)
        assert raw.hex() == f['instruction_bytes_hex'] and digest(raw) == f['instruction_bytes_sha256']
        assert digest(o['raw']) == f['archive_member_sha256'] and o['member'] == f['archive_member']
        assert o['archive_sha256'] == f['archive_sha256']
        for i, r in enumerate(rows):
            assert struct.unpack_from('<I', raw, i*4)[0] == r['word'] and off+i*4 == r['object_offset']
        actual = [r | dict(instruction_address=r['address']+sec['address']) for r in o['relocs']
                  if r['section'] == sec['index'] and first <= r['address']+sec['address'] < end]
        assert sorted(actual, key=lambda r: r['record_offset']) == sorted(f['relocations'], key=lambda r: r['record_offset'])
        nxt = min([v['value'] for v in o['symbols'] if v['section'] == sec['index'] and v['value'] > first], default=sec['address']+sec['size'])
        assert end <= nxt and nxt-end <= 16, ('body-extent', name, end, nxt)
        if nxt != end:
            padding, _, _ = at_address(o, end, nxt-end)
            assert set(padding) <= {0}, ('nonzero-omitted-tail', name, padding.hex())
    assert len(fs) == 7 and sum(len(f['instructions']) for f in fs.values()) == 438
    assert sum(len(f['relocations']) for f in fs.values()) == 46
    return True

def rotate(v, r, width):
    r %= width; return ((v >> r) | (v << (width-r))) & ((1 << width)-1)
def mask_immediate(w):
    width = 64 if w >> 31 else 32
    n, r, s = (w >> 22) & 1, (w >> 16) & 63, (w >> 10) & 63
    assert width == 64 or n == 0
    length = ((n << 6) | ((~s) & 63)).bit_length()-1
    assert length >= 1
    size = 1 << length; levels = size-1
    assert s & levels != levels and size <= width
    part = rotate((1 << ((s & levels)+1))-1, r & levels, size)
    return sum(part << i for i in range(0, width, size))

def decode(w):
    # Each tuple is a semantic instruction; invalid/reserved variants reject.
    d, n, m = w & 31, (w >> 5) & 31, (w >> 16) & 31; width = 64 if w >> 31 else 32
    if w == 0xd65f03c0: return ('return',)
    if w == 0xd503201f: return ('nop',)
    if w == 0xd4200020: return ('trap',)
    if w & 0x7c000000 == 0x14000000: return ('branch', bool(w >> 31), sx(w & 0x3ffffff, 26)*4)
    if w & 0xff000010 == 0x54000000: return ('condition', w & 15, sx((w >> 5) & 0x7ffff, 19)*4)
    if w & 0x7e000000 == 0x34000000: return ('zero', d, width, bool(w & (1 << 24)), sx((w >> 5) & 0x7ffff, 19)*4)
    if w & 0x7e000000 == 0x36000000: return ('bit', d, ((w >> 31) << 5) | ((w >> 19) & 31), bool(w & (1 << 24)), sx((w >> 5) & 0x3fff, 14)*4)
    if w & 0xfffffc1f == 0xd63f0000: return ('indirect', n)
    if w & 0x9f000000 == 0x90000000: return ('page', d)
    if w & 0x1f000000 == 0x11000000:
        assert not w & (1 << 23)
        return ('arithimm', d, n, width, bool(w & (1 << 30)), bool(w & (1 << 29)), ((w >> 10) & 4095) << (12 if w & (1 << 22) else 0))
    if w & 0x1f200000 == 0x0b000000:
        shift, amount = (w >> 22) & 3, (w >> 10) & 63
        assert shift < 3 and amount < width
        return ('arithreg', d, n, m, width, bool(w & (1 << 30)), bool(w & (1 << 29)), shift, amount)
    if w & 0x1f800000 == 0x12800000:
        op, h = (w >> 29) & 3, (w >> 21) & 3
        assert op != 1 and (width == 64 or h < 2)
        return ('wide', d, width, op, ((w >> 5) & 65535), h*16)
    if w & 0x1f800000 == 0x12000000: return ('logicimm', d, n, width, (w >> 29) & 3, mask_immediate(w))
    if w & 0x1f000000 == 0x0a000000:
        amount = (w >> 10) & 63; assert amount < width
        return ('logicreg', d, n, m, width, (w >> 29) & 3, bool(w & (1 << 21)), (w >> 22) & 3, amount)
    if w & 0x1fe00c00 == 0x1a800000:
        assert not w & ((1 << 30) | (1 << 10))
        return ('select', d, n, m, width, (w >> 12) & 15)
    if w & 0x3b000000 == 0x39000000:
        assert not w & (1 << 26)
        size, op = 1 << ((w >> 30) & 3), (w >> 22) & 3
        assert op in (0, 1, 2) and (op != 2 or size == 4)
        return ('memory', d, n, size, op, ((w >> 10) & 4095)*size)
    if w & 0x3b200c00 == 0x38000000:
        assert not w & (1 << 26) and ((w >> 22) & 3) in (0, 1)
        return ('memory', d, n, 1 << ((w >> 30) & 3), (w >> 22) & 3, sx((w >> 12) & 511, 9))
    if w & 0x3b200c00 == 0x38200800:
        assert not w & (1 << 26) and ((w >> 13) & 7) == 3 and ((w >> 22) & 3) in (0, 1)
        return ('memreg', d, n, m, 1 << ((w >> 30) & 3), (w >> 22) & 3, (w >> 12) & 1)
    if w & 0x3a000000 == 0x28000000:
        assert not w & (1 << 26) and (w >> 30) & 3 == 2
        mode = (w >> 23) & 3; assert mode in (1, 2, 3)
        return ('pair', d, (w >> 10) & 31, n, bool(w & (1 << 22)), mode, sx((w >> 15) & 127, 7)*8)
    raise AssertionError(('unsupported-word', hex(w)))

class Terminal(Exception): pass
class Machine:
    maps=[]
    def __init__(self, fs, objects, patch=None, relocpatch=None):
        self.fs=fs; self.objects=objects; self.patch=patch or {}; self.relocpatch=relocpatch or {}
        self.x=[0]*31; self.sp=0x70000000; self.memory={}; self.nzcv=(0,0,0,0)
        self.trace=[]; self.edges=set(); self.calls=[]; self.events=[]; self.open_results=[7]; self.classifications=[]
        self.fail_alloc=False; self.alloc=0x60000000; self.allocations={}; self.noreturn=None; self.extent=0
        cached=[row for row in self.maps if row[0] is objects]
        if cached:self.address,self.reverse=cached[0][1:]
        else:
            self.address={}; self.reverse={}
            for index, obj in enumerate(objects.values()):
                for s in obj['symbols']:
                    if s['section']:
                        a=0x100000000+index*0x1000000+s['value']; self.address[s['name']]=a; self.reverse[a]=s['name']
            self.maps.append((objects,self.address,self.reverse))
        self.errno=0x50000100; self.vtable=0x50000000; self.interrupt=0x50000200
        self.global_addr=self.address[named(self.address, '12os_functions12OS_FUNCTIONS')]
        self.record=self.address['l_anon.fe79d0da482d11692d25899e0a8a72b8.76']
        self.write(self.global_addr,self.record,8); self.write(self.vtable+16,self.interrupt,8)
        # Poison synthetic stack bytes so a missing NUL store cannot pass by
        # inheriting a zero from the test harness. Callee saves restore actual x values.
        self.blob(self.sp-8192, b'\xa5'*8448)
    def blob(self,a,data):
        for i,b in enumerate(data): self.memory[a+i]=b
    def data(self,a,n):
        assert all(a+i in self.memory for i in range(n)), ('undefined-read',hex(a),n)
        return bytes(self.memory[a+i] for i in range(n))
    def read(self,a,n): return int.from_bytes(self.data(a,n),'little')
    def write(self,a,v,n):
        for i in range(n): self.memory[a+i]=(v >> (8*i)) & 255
    def get(self,i,sp=False): return self.sp if i==31 and sp else 0 if i==31 else self.x[i]
    def set(self,i,v,width=64,sp=False):
        v &= (1 << width)-1
        if i==31:
            if sp: self.sp=v
        else: self.x[i]=v
    def condition(self,c):
        n,z,carry,v=self.nzcv
        yes=(z,carry,n,v,carry and not z,n==v,n==v and not z,True)[c//2]
        return not yes if c%2 and c!=15 else yes
    def arith(self,a,b,width,sub,flags):
        mask=(1 << width)-1; a &= mask; b &= mask; total=a-b if sub else a+b; out=total & mask
        if flags:
            self.nzcv=(bool(out & (1 << (width-1))),out==0,a>=b if sub else total>mask,
                       bool(((a^b) if sub else ~(a^b)) & (a^out) & (1 << (width-1))))
        return out
    def shifted(self,v,width,shift,amount):
        v &= (1 << width)-1
        return v << amount if shift==0 else v >> amount if shift==1 else sx(v,width) >> amount if shift==2 else rotate(v,amount,width)
    def relocation(self,f,pc,allowed):
        rs=[r for r in f['relocations'] if r['instruction_address']==pc]
        assert len(rs)<=1
        if not rs:return None
        assert rs[0]['type'] in allowed, ('wrong-relocation-kind',pc,rs)
        return self.relocpatch.get((f['symbol'],pc),rs[0]['target'])
    def external(self,s):
        self.calls.append((s,self.x[:4].copy()))
        if s in self.fs: self.run(s);return
        if s=='_memcpy':
            a,b,n=self.x[:3]; self.events.append(('copy',a,b,n)); self.blob(a,self.data(b,n)); self.x[0]=a; return
        if s.endswith('35___rust_no_alloc_shim_is_unstable_v2'): self.events.append(('allocator-marker',));return
        if s.endswith('12___rust_alloc'):
            n,a=self.x[:2];self.events.append(('allocate',n,a));assert n<=8192 or self.fail_alloc
            if self.fail_alloc:self.x[0]=0
            else:
                assert a==1;self.x[0]=self.alloc;self.allocations[self.alloc]=n;self.blob(self.alloc,b'\xcc'*n)
            return
        if s.endswith('14___rust_dealloc'):
            p,n,a=self.x[:3];self.events.append(('free',p,n,a,self.read(p,1)))
            assert p in self.allocations and self.allocations.pop(p)==n and a==1,('free-contract',p,n,a)
            return
        if s.endswith('14memchr_aligned'):
            byte,p,n=self.x[:3];i=self.data(p,n).find(bytes([byte & 255]));self.events.append(('memchr',byte,p,n,i));self.x[0]=int(i>=0);self.x[1]=max(0,i);return
        if s=='_open':
            assert self.open_results, 'finite-test-retry-exhaustion'
            v=self.open_results.pop(0);self.events.append(('open',self.x[0],self.data(self.x[0],self.extent).hex(),self.x[1],self.read(self.sp,4),v))
            self.x[0]=v & 0xffffffff
            if v==-1: self.write(self.errno,self.errno_value,4)
            return
        if s=='___error':self.x[0]=self.errno;return
        if s.endswith('16get_os_functions'):self.x[0]=self.vtable;return
        if s.endswith('19set_functions_inner'):self.write(self.global_addr,self.x[0],8);return
        if s=='explicit-interruption-interface':
            val=self.classifications.pop(0) if self.classifications else self.x[0]==4
            self.events.append(('interrupted',self.x[0],val));self.x[0]=int(val);return
        if s.endswith('12handle_error'):self.noreturn='capacity-or-OOM';raise Terminal(self.noreturn)
        if s=='__Unwind_Resume':self.noreturn='unwind-resume';raise Terminal(self.noreturn)
        if '5Error3new' in s:
            self.events.append(('dynamic-error',*self.x[:3]));self.x[0]=0x40000003;return
        raise AssertionError(('unsupported-call',s))
    def run(self,symbol,entry=None):
        f=self.fs[symbol];words={r['address']:r['word'] for r in f['instructions']};pc=f['address'] if entry is None else entry;sp=self.sp
        for step in range(20000):
            assert pc in words,('out-of-body',symbol,hex(pc))
            w=self.patch.get((symbol,pc),words[pc]);ins=decode(w);op=ins[0];self.trace.append((symbol,pc,w));dest=pc+4
            if op=='return':assert sp==self.sp,('stack-balance',symbol);return
            elif op=='nop':pass
            elif op=='trap':raise AssertionError(('active-trap',symbol,hex(pc)))
            elif op=='branch':
                _,link,delta=ins;t=self.relocation(f,pc,{2})
                if t:
                    assert delta==0,('unsupported-relocation-addend',symbol,pc,delta)
                    self.external(t)
                    if not link:assert sp==self.sp;return
                elif link:raise AssertionError(('unrelocated-call',symbol,pc))
                else:dest=pc+delta
            elif op=='condition':
                if self.condition(ins[1]):dest=pc+ins[2]
            elif op=='zero':
                _,r,width,nonzero,delta=ins
                if bool(self.get(r)&((1<<width)-1))==nonzero:dest=pc+delta
            elif op=='bit':
                _,r,bit,nonzero,delta=ins
                if bool(self.get(r)&(1<<bit))==nonzero:dest=pc+delta
            elif op=='indirect':
                a=self.get(ins[1]);assert a==self.interrupt or a in self.reverse,('unknown-indirect-target',hex(a))
                self.external('explicit-interruption-interface' if a==self.interrupt else self.reverse[a])
            elif op=='page':
                t=self.relocation(f,pc,{3,5});assert t is not None;a=self.address[t]
                assert ((w>>5)&0x7ffff)==0 and ((w>>29)&3)==0,('unsupported-page-addend',pc)
                if next(r for r in f['relocations'] if r['instruction_address']==pc)['type']==5:
                    slot=0x300000000+a;self.write(slot,a,8);a=slot
                self.set(ins[1],a & ~4095)
            elif op=='arithimm':
                _,d,n,width,sub,flags,imm=ins;t=self.relocation(f,pc,{4})
                if t is not None:
                    assert imm==0 and width==64 and not sub and not flags,('unsupported-pageoff-addend-or-opcode',pc,ins)
                    imm=self.address[t]&4095
                self.set(d,self.arith(self.get(n,True),imm,width,sub,flags),width,not flags)
            elif op=='arithreg':
                _,d,n,m,width,sub,flags,shift,amount=ins
                self.set(d,self.arith(self.get(n),self.shifted(self.get(m),width,shift,amount),width,sub,flags),width)
            elif op=='wide':
                _,d,width,kind,imm,shift=ins
                v=~(imm<<shift) if kind==0 else imm<<shift if kind==2 else (self.get(d)&~(65535<<shift))|(imm<<shift)
                self.set(d,v,width)
            elif op in ('logicimm','logicreg'):
                d,n,width,kind=(ins[1],ins[2],ins[3],ins[4]) if op=='logicimm' else (ins[1],ins[2],ins[4],ins[5])
                a=self.get(n);b=ins[5] if op=='logicimm' else self.shifted(self.get(ins[3]),width,ins[7],ins[8])
                if op=='logicreg' and ins[6]:b=~b
                v=(a&b if kind in (0,3) else a|b if kind==1 else a^b)&((1<<width)-1);self.set(d,v,width)
                if kind==3:self.nzcv=(bool(v&(1<<(width-1))),v==0,False,False)
            elif op=='select':_,d,n,m,width,c=ins;self.set(d,self.get(n if self.condition(c) else m),width)
            elif op in ('memory','memreg'):
                if op=='memory':
                    _,d,n,size,kind,offset=ins;t=self.relocation(f,pc,{6})
                    if t is not None:
                        assert offset==0 and size==8 and kind==1,('unsupported-GOT-addend-or-opcode',pc,ins)
                        offset=(0x300000000+self.address[t])&4095
                else:
                    _,d,n,m,size,kind,shift=ins;offset=self.get(m)*(size if shift else 1)
                a=self.get(n,True)+offset
                if kind==0:self.write(a,self.get(d),size)
                else:self.set(d,sx(self.read(a,size),8*size) if kind==2 else self.read(a,size),64 if size==8 or kind==2 else 32)
            elif op=='pair':
                _,d,t,n,read,mode,offset=ins;base=self.get(n,True);a=base if mode==1 else base+offset
                if read:
                    v1,v2=self.read(a,8),self.read(a+8,8);self.set(d,v1);self.set(t,v2)
                else:self.write(a,self.get(d),8);self.write(a+8,self.get(t),8)
                if mode in (1,3):self.set(n,base+offset,sp=True)
            else:raise AssertionError(('missing-semantics',ins))
            self.edges.add((symbol,pc,dest));pc=dest
        raise AssertionError(('offline-budget',symbol))

def custody():
    rows=[sealed(P,SEAL)]
    assert rows[0]['members']==112 and rows[0]['bytes']==2855785
    release=R/'verification/swift-semantic-adapter-root-review/guarded-snapshot-native-open-binary-frozen-release.json'
    assert digest(release.read_bytes())==RELEASE
    for b in load(P/'input-bindings.json'):
        p=R/b['path']
        if 'seal_sha256' in b:rows.append(sealed(p,b['seal_sha256']))
        else:assert digest(p.read_bytes())==b['sha256'];rows.append(b)
    manifest=load(P/'compiled-manifest.json');plan=load(P/'compiler-plan.json');receipt=load(P/'compiler-receipt.json')
    assert digest((P/'compiler-plan.json').read_bytes())=='9c949b21460a3f5343c4b3d23f84f60b57f7fc111dcf159ea58dee329db0310d'
    assert digest((P/'compiled-manifest.json').read_bytes())==plan['compiled_manifest_sha256']
    members=manifest['source_manifest']['members'];assert len(members)==146 and digest(canon(members))==SOURCE
    append=(P/'generic-open-append.inc.rs').read_bytes()
    assert len(append)==646 and digest(append)==manifest['append_sha256']==plan['append_sha256']
    assert plan['append_bytes'].encode()==append and manifest['append_bytes']==646
    calculated=[]
    assert [{k:r[k] for k in ('path','bytes','sha256')} for r in manifest['source_reference_map']]==members
    for row in manifest['source_reference_map']:
        raw=exact(R/row['source'],row)
        if row['path']==manifest['append_path']:raw+=append
        calculated.append(dict(path=row['path'],bytes=len(raw),sha256=digest(raw)))
    assert len(calculated)==146 and calculated==manifest['compiled_members']
    assert digest(canon(calculated))==manifest['compiled_tree_sha256']==plan['compiled_tree_sha256']
    assert digest(Path(plan['argv'][0]).read_bytes())==plan['compiler_sha256']==manifest['compiler_sha256']
    assert digest((B/'compiler-version.stdout').read_bytes())==manifest['compiler_version_stdout_sha256']
    assert plan['version'].startswith('rustc 1.99.0 (b940084d7 2026-09-28)')
    assert 'commit-hash: b940084d7eb6a299eb4bfeb8e34901bc051e7ac4\n' in plan['version'] and 'LLVM version: 23.1.1\n' in plan['version']
    assert receipt['argv']==plan['argv'] and receipt['environment']==plan['environment']
    assert plan['argv'][:-2]==load(B/'compiler-receipt.json')['argv'][:-2]
    assert digest((P/'query.py').read_bytes())==manifest['query_script_sha256']
    def counted(raw):
        count=struct.unpack_from('<Q',raw)[0];at=8;out=[]
        for i in range(count):
            n=struct.unpack_from('<Q',raw,at)[0];at+=8;b=raw[at:at+n];assert len(b)==n and b'\0' not in b;out.append(b.decode());at+=n
        assert at==len(raw);return out
    assert counted((P/'argv.bin').read_bytes())==plan['argv']
    baseenv={k:v for k,v in plan['environment'].items() if not k.startswith('MIXER_LOADER_')}
    assert counted((P/'environment.bin').read_bytes())==[k+'='+v for k,v in sorted(baseenv.items())]
    assert digest((P/'argv.bin').read_bytes())==plan['environment']['MIXER_LOADER_COMMAND_SHA256']
    assert digest((P/'environment.bin').read_bytes())==plan['environment']['MIXER_LOADER_COMPILE_ENV_SHA256']
    assert plan['environment']['MIXER_LOADER_MANIFEST_SHA256']==plan['compiled_manifest_sha256']
    assert receipt['direct_child_waited'] and receipt['owned_group_absent'] and receipt['exit_code']==0 and not receipt['timed_out']
    assert receipt['elapsed_seconds']<15 and not receipt['product_runtime']
    assert [a for a in plan['argv'] if a.startswith('--emit=')]==[plan['argv'][-1]] and plan['argv'][-1].startswith('--emit=llvm-ir=')
    for label,r in receipt['outputs'].items():
        raw=gzip.decompress((P/r['path']).read_bytes());assert len(raw)==r['bytes'] and digest(raw)==r['sha256']
    assert load(P/'compiler-cleanup.json')['owned_scratch_removed'] and not (P/'compiler-owned-work').exists()
    cleanup=load(P/'compiler-cleanup.json');assert cleanup['complete'] and cleanup['owned_children_waited_and_groups_absent']
    removed={r['path']:r for r in cleanup['removed_files']}
    for r in manifest['compiled_members']:assert removed['vm/'+r['path']]==r|dict(path='vm/'+r['path'])
    llvm_raw=gzip.decompress((P/'generic-open.ll.gz').read_bytes());assert removed['generic-open.ll']['sha256']==digest(llvm_raw) and removed['generic-open.ll']['bytes']==len(llvm_raw)
    for name in ('disassembly','cstring-constructor'):
        rec=load(P/(name+'-receipt.json')); assert rec['direct_child_waited'] and rec['owned_group_absent'] and rec['exit_code']==0 and not rec['timed_out']
        queryplan=load(P/(name+'-plan.json'));assert rec['argv']==queryplan['argv']
        for tool in ('tool','libLLVM'):exact(Path(queryplan[tool]['path']),queryplan[tool])
        for label,r in rec['outputs'].items():
            raw=gzip.decompress((P/r.get('archive',r.get('path'))).read_bytes());assert len(raw)==r['bytes'] and digest(raw)==r['sha256']
    for r in load(P/'source-evidence.json'):
        raw=(R/r['path']).read_bytes();excerpt=''.join(raw.decode().splitlines(keepends=True)[r['first_line']-1:r['last_line']])
        assert digest(raw)==r['file_sha256'] and excerpt==r['source'] and digest(excerpt.encode())==r['excerpt_sha256']
    attempts=load(P/'attempt-history.json')
    for row in attempts['attempts']:
        for label in ('stdout','stderr'):
            p=P/row['path']/(label+'.txt')
            if not p.exists():p=P/row['path']/label
            assert digest(p.read_bytes())==row[label+'_sha256']
    return rows,dict(source_tree_sha256=SOURCE,original_members=146,append_bytes=646,compiled_tree_sha256=manifest['compiled_tree_sha256'],
      compiler_sha256=plan['compiler_sha256'],compiler_version=plan['version'],historical_compiler_elapsed_seconds=receipt['elapsed_seconds'],
      compiler_invoked_in_review=False,contexts_separate=True,prior_observer_failure_preserved=True,
      pyc_cleanup_incident=load(P/'cleanup-import-incident.json'),actual_immutable_caller_or_executable_bound=False)

class LLVM:
    """Separate, strict statement evaluator. Every active opcode/call is checked."""
    def __init__(self,functions):
        self.fs=functions;self.memory={};self.cursor=0x100000;self.calls=[];self.trace=[]
    def write(self,a,v,n):
        for i in range(n):self.memory[a+i]=(v>>(i*8))&255
    def data(self,a,n):
        assert all(a+i in self.memory for i in range(n)),('LLVM-uninitialized',a,n)
        return bytes(self.memory[a+i] for i in range(n))
    def run(self,symbol,args):
        if symbol=='llvm.memcpy.p0.p0.i64':
            dst,src,n,volatile=args;assert volatile==0
            for i,v in enumerate(self.data(src,n)):self.memory[dst+i]=v
            return
        if symbol=='_RNvMsj_NtCs1SSuMAdGM58_3std2fsNtB5_11OpenOptions5__open':
            out,opts,p,n=args;self.calls.append((out,self.data(opts,12).hex(),p,n));return
        assert symbol in self.fs,('LLVM-foreign-call',symbol)
        body=self.fs[symbol]['body'].splitlines();header=body[0]
        params=re.findall(r'%[-\w.]+',header[header.index('('):header.rindex(')')]);assert len(params)==len(args)
        env=dict(zip(params,args));blocks={};current=None
        for line in body[1:-1]:
            line=line.split(';')[0].strip()
            if not line:continue
            if line.endswith(':'):current=line[:-1];assert current not in blocks;blocks[current]=[]
            else:assert current is not None;blocks[current].append(line)
        def val(x):
            if x in env:return env[x]
            if x=='poison':return (None,None)
            if x in ('true','false','null'):return int(x=='true')
            return int(x)
        def last(x):return val(x.strip().split()[-1])
        block='start'
        for step in range(64):
            assert block in blocks
            jump=False
            for full in blocks[block]:
                self.trace.append((symbol,block,full));target=None;ins=full
                if ' = ' in full:target,ins=full.split(' = ',1)
                op=ins.split(' ',1)[0];result=None
                if op=='alloca':
                    m=re.fullmatch(r'alloca \[(\d+) x i8\], align (\d+)',ins);assert m
                    n,a=map(int,m.groups());self.cursor=(self.cursor+a-1)//a*a;result=self.cursor;self.cursor+=n+16
                elif op=='store':
                    m=re.fullmatch(r'store (ptr|i8|i16|i32|i64) (\S+), ptr (\S+), align \d+',ins);assert m
                    typ,v,p=m.groups();self.write(val(p),val(v),8 if typ=='ptr' else int(typ[1:])//8)
                elif op=='load':
                    m=re.fullmatch(r'load (ptr|i64), ptr (\S+), align \d+',ins);assert m
                    result=int.from_bytes(self.data(val(m[2]),8),'little')
                elif op=='getelementptr':
                    m=re.fullmatch(r'getelementptr inbounds i8, ptr (\S+), i64 (\S+)',ins);assert m;result=val(m[1])+val(m[2])
                elif op=='call':
                    m=re.fullmatch(r'call .*?@([^ (]+)\((.*)\)(?: #\d+)?',ins);assert m
                    result=self.run(m[1],[last(v) for v in m[2].split(',')])
                elif op=='extractvalue':
                    m=re.fullmatch(r'extractvalue \{ ptr, i64 \} (\S+), ([01])',ins);assert m;result=val(m[1])[int(m[2])]
                elif op=='insertvalue':
                    m=re.fullmatch(r'insertvalue \{ ptr, i64 \} (\S+), (?:ptr|i64) (\S+), ([01])',ins);assert m
                    result=list(val(m[1]));result[int(m[3])]=val(m[2]);result=tuple(result)
                elif op=='zext':
                    m=re.fullmatch(r'zext i1 (\S+) to i8',ins);assert m;result=val(m[1]);assert result in (0,1)
                elif op=='br':
                    m=re.fullmatch(r'br label %(\S+)',ins);assert m;block=m[1];jump=True;break
                elif op=='ret':return None if ins=='ret void' else last(ins)
                else:raise AssertionError(('unsupported-LLVM',symbol,block,ins))
                if target is not None:env[target]=result
            assert jump,('LLVM-no-terminal',symbol,block)
        raise AssertionError(('LLVM-budget',symbol))

def llvm_checks():
    raw=gzip.decompress((P/'generic-open.ll.gz').read_bytes());archive=load(P/'generic-open.ll-archive.json')
    assert len(raw)==archive['raw_bytes'] and digest(raw)==archive['raw_sha256']
    # Retained function bodies must equal actual definitions, including full unreachable blocks.
    parsed={};lines=raw.decode().splitlines(keepends=True);i=0
    while i<len(lines):
        if lines[i].startswith('define '):
            end=i+1
            while lines[end]!='}\n':end+=1
            name=lines[i].split('@')[1].split('(')[0];parsed[name]=''.join(lines[i:end+1]);i=end
        i+=1
    fs=load(P/'LLVM-bodies.json');assert len(fs)==8
    for name,r in fs.items():assert r['body']==parsed[name] and digest(r['body'].encode())==r['sha256']
    read=named(fs,'_4File4openR');write=named(fs,'26native_open_create_path_v1')
    globals=[l for l in raw.decode().splitlines() if l.startswith('@')]
    readptr=unique([l for l in globals if 'NATIVE_OPEN_READ_PATH_V1 =' in l]);writeptr=unique([l for l in globals if 'NATIVE_OPEN_CREATE_PATH_V1 =' in l])
    assert ' = constant ptr @'+read+', align 8,' in readptr and ' = constant ptr @'+write+', align 8,' in writeptr
    used=unique([l for l in globals if l.startswith('@llvm.used =')]);assert '[2 x ptr]' in used
    assert readptr.split(' =')[0] in used and writeptr.split(' =')[0] in used
    rows=[]
    for mode,entry in ((False,read),(True,write)):
        for pointer,n in ((0x1234001,0),(0x2345002,383),(0x3456003,384),(0x4567004,4095),(0x5678005,(1<<63)-1)):
            v=LLVM(fs);v.run(entry,[0x900000,pointer,n]);expected=bytearray(12);expected[4:6]=(438).to_bytes(2,'little');expected[7 if mode else 6]=1
            if mode:expected[11]=1
            assert v.calls==[(0x900000,expected.hex(),pointer,n)],v.calls
            rows.append(dict(write=mode,pointer=pointer,n=n,options=expected.hex(),steps=len(v.trace),trace_sha256=digest(canon(v.trace))))
    baseline=gzip.decompress((B/'source146.ll.gz').read_bytes());assert digest(baseline)=='782a8a4c0abe1e47a8e9571fb9370ae52e5e780ef084251a6e98a99d49cea1d0'
    assert not any(l.startswith('define ') and any(p in l for p in ('4File4open','11OpenOptions','small_c_string','SpecNewImpl')) for l in baseline.decode().splitlines())
    return fs,rows

def path_case(fs,objects,n,position=None,write=False,errno=None,alignment=0,patch=None,relocpatch=None,oom=False):
    v=Machine(fs,objects,patch,relocpatch);path=0x20000000+alignment;options=0x21000000;out=0x22000000
    data=bytearray(b'z'*n)
    if position is not None:data[position]=0
    v.blob(path,data);v.blob(options,bytes(12));v.blob(out,bytes(16));v.write(options+4,438,2);v.write(options+(7 if write else 6),1,1)
    if write:v.write(options+11,1,1)
    v.x[0:3]=[options,path,n];v.x[8]=out;v.extent=n+1;v.errno_value=13 if errno is None else errno
    v.open_results=[7 if errno is None else -1];v.fail_alloc=oom
    try:v.run(named(fs,'11OpenOptions5__open'))
    except Terminal:pass
    allocations=[e for e in v.events if e[0]=='allocate'];frees=[e for e in v.events if e[0]=='free'];opens=[e for e in v.events if e[0]=='open']
    assert allocations==([('allocate',n+1,1)] if n>=384 else []),('allocation-contract',n,allocations)
    if oom and n>=384:
        assert not frees and not opens and v.noreturn=='capacity-or-OOM'
    else:
        assert not v.allocations and v.noreturn is None
        assert len(opens)==int(position is None),('NUL-gating',n,position,opens)
        assert v.read(out,4)==int(position is not None or errno is not None)
        if position is not None:
            assert v.read(out+8,8)==v.address['l_anon.fe79d0da482d11692d25899e0a8a72b8.79']
        elif errno is not None:assert v.read(out+8,8)==((errno&0xffffffff)<<32)|2
        else:assert v.read(out+4,4)==7
        if opens:
            _,p,hexdata,flags,mode,result=opens[0];assert hexdata==(data+b'\0').hex() and flags==(0x1000a01 if write else 0x1000000) and mode==438
            assert p==(v.alloc if n>=384 else 0x70000000-496+24)
        if n>=384:
            assert len(frees)==1 and frees[0][1:4]==(v.alloc,n+1,1)
            # Valid CString drop clears first byte before deallocation; NulError is a Vec drop.
            assert frees[0][4]==(0 if position is None or position==0 else ord('z'))
            kinds=[e[0] for e in v.events]
            assert kinds.index('allocate') < kinds.index('copy') < kinds.index('memchr') < kinds.index('free')
        else:assert not frees
        assert not any(e[0]=='dynamic-error' for e in v.events)
    return dict(n=n,first_NUL=position,write=write,errno=errno,alignment=alignment,OOM=oom,steps=len(v.trace),
      trace_sha256=digest(canon(v.trace)),events_sha256=digest(canon(v.events))),v

def expected_flags(mask,custom):
    r,w,a,t,c,x=[bool(mask&(1<<i)) for i in range(6)]
    if not (r or w or a) or (not w and not a and (t or c or x)) or (a and t and not x):return None
    access=(10 if r else 9) if a else 2 if r and w else 1 if w else 0
    create=0xa00 if x else (0x200 if c else 0)|(0x400 if t else 0)
    return 0x1000000|access|create|(custom&0xfffffffc)

def native_checks(fs,objects):
    rows=[];coverage=set();edges=set();calls=set()
    def absorb(v):
        coverage.update((s,pc) for s,pc,w in v.trace);edges.update(v.edges);calls.update(s for s,a in v.calls)
    # Full-path first-NUL positions straddle both routes. Separate core tests cover all eight alignments.
    for n in (0,1,2,15,16,17,31,32,127,383,384,385,768,4095):
        positions=[None]+sorted({0,n//2,n-1}) if n else [None]
        for pos in positions:
            for write in (False,True):
                for align in (0,7):
                    row,v=path_case(fs,objects,n,pos,write,alignment=align);rows.append(row);absorb(v)
        for errno in (0,4,13,2147483647,-1,-2147483648):
            # Explicit classification avoids treating errno4 as retry, and checks sign extension.
            if errno==4:continue
            row,v=path_case(fs,objects,n,errno=errno);rows.append(row);absorb(v)
        if n>=384:
            row,v=path_case(fs,objects,n,oom=True);rows.append(row);absorb(v)
    core=[];entry=named(fs,'CStr19from_bytes_with_nul')
    for n in (0,1,2,15,16,17,31,32,33,383,384,385):
        for align in range(8):
            for pos in [None]+list(range(n)):
                v=Machine(fs,objects);p=0x25000000+align;out=0x26000000;data=bytearray(b'q'*n)
                if pos is not None:data[pos]=0
                v.blob(p,data);v.blob(out,bytes(24));v.x[0:2]=[p,n];v.x[8]=out;v.run(entry)
                valid=pos is not None and pos==n-1;assert v.read(out,8)==int(not valid)
                if valid:assert (v.read(out+8,8),v.read(out+16,8))==(p,n)
                elif pos is None:assert v.read(out+8,8)==1
                else:assert (v.read(out+8,8),v.read(out+16,8))==(0,pos)
                assert not v.events;absorb(v)
                core.append(dict(n=n,alignment=align,first_NUL=pos,valid=valid,steps=len(v.trace)))
    opts=[];entry=named(fs,'4File6open_c')
    for mask in range(64):
        for custom in (0,3,0x800,0x403,0x80000000,0xffffffff):
            for mode in (0,438,65535):
                v=Machine(fs,objects);o,p,out=0x27000000,0x27010000,0x27020000
                v.blob(o,bytes(12));v.write(o,custom,4);v.write(o+4,mode,2)
                for i in range(6):v.write(o+6+i,(mask>>i)&1,1)
                v.blob(p,b'x\0');v.blob(out,bytes(16));v.x[:3]=[out,p,o];v.extent=2;v.run(entry);absorb(v)
                opened=[e for e in v.events if e[0]=='open'];err=[e for e in v.events if e[0]=='dynamic-error'];expected=expected_flags(mask,custom)
                assert len(opened)==int(expected is not None) and len(err)==int(expected is None)
                if opened:assert opened[0][3:5]==(expected,mode) and v.read(out,4)==0
                else:assert err[0][1]==20 and err[0][3] in (58,61) and v.read(out,4)==1
                opts.append(dict(option_mask=mask,custom=custom,mode=mode,flags=expected))
    retry=[]
    for count in (0,1,2,5):
        for last in (7,-1):
            for changed in (False,True):
                v=Machine(fs,objects);o,p,out=0x27000000,0x27010000,0x27020000
                v.blob(o,bytes(12));v.write(o+4,438,2);v.write(o+6,1,1);v.blob(p,b'x\0');v.blob(out,bytes(16));v.x[:3]=[out,p,o];v.extent=2
                v.open_results=[-1]*count+[last];v.classifications=[True]*count+([False] if last==-1 else []);v.errno_value=13
                if changed:v.write(v.global_addr,0,8)
                v.run(entry);absorb(v);opened=[e for e in v.events if e[0]=='open']
                assert len(opened)==count+1 and v.read(out,4)==int(last==-1)
                if last==-1:assert v.read(out+8,8)==(13<<32)|2
                retry.append(dict(private_retry_bound=False,finite_calls=len(opened),last=last,changed_OS_table=changed))
    special=[];spec=named(fs,'SpecNewImpl13spec_new_impl')
    for n in ((1<<63)-2,(1<<63)-1):
        v=Machine(fs,objects);v.x[0:2]=[0x28000000,n];v.x[8]=0x28010000;v.fail_alloc=True
        try:v.run(spec)
        except Terminal:pass
        assert v.noreturn=='capacity-or-OOM';alloc=[e for e in v.events if e[0]=='allocate'];assert len(alloc)==int(n==(1<<63)-2)
        assert not any(e[0] in ('copy','memchr','open','free') for e in v.events);absorb(v);special.append(dict(n=n,events=v.events,terminal=v.noreturn))
    v=Machine(fs,objects);v.sp-=96;v.x[0]=0x29000000;v.x[19]=v.alloc;v.x[20]=385;v.blob(v.alloc,b'x'*384+b'\0');v.allocations[v.alloc]=385
    try:v.run(named(fs,'run_with_cstr_allocating'),entry=0xa43c)
    except Terminal:pass
    assert v.noreturn=='unwind-resume' and not v.allocations and ('free',v.alloc,385,1,0) in v.events;absorb(v)
    special.append(dict(scope='synthetic landingpad only; real unwind selection pending',terminal=v.noreturn,events=v.events))
    return dict(paths=rows,core=core,options=opts,retry=retry,special=special),coverage,edges,calls

def static_error(objects):
    o=objects['std'];prefix='l_anon.fe79d0da482d11692d25899e0a8a72b8.'
    s=unique([s for s in o['symbols'] if s['name']==prefix+'79']);assert s['value']%4==0
    raw,off,sec=at_address(o,s['value'],24);assert struct.unpack('<3Q',raw)==(0,42,20)
    rel=unique([r for r in o['relocs'] if r['section']==sec['index'] and r['address']==s['value']-sec['address']])
    assert rel['type']==0 and rel['external'] and not rel['pc_relative'] and rel['width_power']==3 and rel['target']==prefix+'78'
    msgsym=unique([s for s in o['symbols'] if s['name']==rel['target']]);msg,msg_off,_=at_address(o,msgsym['value'],42)
    assert msg==b'file name contained an unexpected NUL byte'
    return dict(record_object_offset=off,record_raw_hex=raw.hex(),message=msg.decode(),message_object_offset=msg_off,relocation=rel)

def frontier(fs,coverage,edges,calls):
    entries=[];external=[];indirect=[];instructions=[]
    for symbol,f in fs.items():
        pcs={i['address'] for i in f['instructions']};rels={r['instruction_address']:r for r in f['relocations']}
        for i in f['instructions']:
            pc=i['address'];ins=decode(i['word']);op=ins[0];succ=[];r=rels.get(pc)
            if r:
                expected={'branch':{2},'page':{3,5},'arithimm':{4},'memory':{6}}
                assert op in expected and r['type'] in expected[op],('relocation-opcode',pc,ins,r)
                assert r['external'] and r['width_power']==2 and r['pc_relative']==(r['type'] in (2,3,5))
            if op=='branch':
                if r:
                    assert r['type']==2 and r['pc_relative'] and r['width_power']==2 and r['external']
                    target=r['target']
                    category='retained internal body' if target in fs else (
                        'nonreturning allocator/capacity boundary' if target.endswith('12handle_error') else
                        'nonreturning unwind boundary' if target=='__Unwind_Resume' else
                        'out-of-selected options dynamic Error::new interface stub' if '5Error3new' in target else
                        'selected-route interface stub' if target in calls else
                        'out-of-selected CString growth/shrink boundary' if ('finish_grow' in target or '___rust_realloc' in target) else
                        'out-of-selected open_c exceptional cleanup boundary' if ('drop_glue' in target or 'panic_in_cleanup' in target) else 'unclassified')
                    assert category!='unclassified',target
                    external.append(dict(from_symbol=symbol,pc=pc,target=target,category=category,
                      observed_in_synthetic_tests=(symbol,pc) in coverage,private_implementation_proved=False))
                    if ins[1] and not (target.endswith('12handle_error') or target in ('__Unwind_Resume',) or 'panic_in_cleanup' in target):succ=[pc+4]
                else:
                    assert not ins[1],('unrelocated-call',symbol,pc)
                    succ=[pc+ins[2]]
            elif op in ('condition','zero','bit'):
                succ=[pc+4,pc+ins[-1]]
            elif op=='indirect':
                assert (pc,ins[1]) in ((0xa408,21),(0x2d3e0,8))
                indirect.append(dict(symbol=symbol,pc=pc,register=ins[1],contract='retained File closure loaded from _open x4 then saved x21' if pc==0xa408 else 'explicit OS table +16 interruption classifier stub',foreign_target_fails_closed=True))
                succ=[pc+4]
            elif op not in ('return','trap'):succ=[pc+4]
            for target in succ:assert target in pcs,('incomplete-CFG',symbol,pc,target)
            entries.extend(dict(symbol=symbol,source=pc,target=t,observed=(symbol,pc,t) in edges) for t in succ)
            instructions.append(dict(symbol=symbol,address=pc,word=hex(i['word']),operation=op,
              operands=ins[1:],observed=(symbol,pc) in coverage,raw_relocation=r))
    return dict(instructions=instructions,edges=entries,calls=external,indirect=indirect,
      instructions_total=len(instructions),instructions_observed=sum(i['observed'] for i in instructions),
      edge_total=len(entries),edges_observed=sum(e['observed'] for e in entries),
      scope='Every retained word decodes independently; selected-route and explicit synthetic exceptional traces only. Unobserved edges listed without claiming feasible selected routes or actual unwinder selection.')

def critical_contracts(fs,objects):
    def words(pattern,expected):
        s=named(fs,pattern);actual={i['address']:i['word'] for i in fs[s]['instructions']};out=[]
        for pc,word in expected:
            assert actual[pc]==word;out.append(dict(symbol=s,address=pc,raw_word=hex(word),decoded=decode(word)))
        return out
    guard=words('11OpenOptions5__open',[(0x2ec54,0xd107c3ff),(0x2ec6c,0xaa0203f4),(0x2ec78,0xf105fc5f),(0x2ec7c,0x540003e8),
      (0x2ec84,0x910063f6),(0x2ec94,0x38346adf),(0x2eca0,0x91000681),(0x2ecac,0xb4000128)])
    allocate=words('SpecNewImpl13spec_new_impl',[(0x6630,0xb1000434),(0x6634,0x540005c4),(0x664c,0xaa1403e0),(0x6650,0x52800021),
      (0x6658,0xb40004c0),(0x665c,0xaa0003f6),(0x666c,0xaa1503e2),(0x66a0,0xaa1503e2),(0x66a8,0x36000080),
      (0x66ac,0xa9005a74),(0x66b8,0xa900dbf4),(0x66bc,0xf9000ff5),(0x66c8,0xa9008660),(0x66cc,0x92800008),(0x66d0,0xf9000268)])
    constructor=words('7CString19__from_vec_unchecked',[(0x5214,0xf9400815),(0x5218,0xf9400013),(0x521c,0xeb15027f),(0x5220,0x540002e0),
      (0x5224,0xf9400414),(0x5228,0x38356a9f),(0x522c,0x910006b5),(0x5230,0xeb15027f),(0x5234,0x54000449),(0x52bc,0xaa1403e0),(0x52c0,0xaa1503e1)])
    cleanup=words('run_with_cstr_allocating',[(0xa3c8,0xf94003e1),(0xa3cc,0xb100043f),(0xa3d0,0x54000120),(0xa3ec,0xf94007e0),
      (0xa3f4,0xa940d3f3),(0xa400,0xaa1303e1),(0xa404,0xaa1403e2),(0xa408,0xd63f02a0),(0xa40c,0x3900027f),
      (0xa414,0xaa1303e0),(0xa418,0xaa1403e1),(0xa41c,0x52800022),(0xa440,0x3900027f),(0xa448,0xaa1303e0),(0xa44c,0xaa1403e1)])
    error=words('4File6open_c',[(0x2d2d0,0x3940184a),(0x2d2d4,0x39401c49),(0x2d2d8,0x39402048),(0x2d394,0x79400858),
      (0x2d3a8,0xf90003f8),(0x2d3ac,0x320802e1),(0x2d3b8,0x3100041f),(0x2d3c4,0xb9800016),(0x2d3e4,0x3707fe20),
      (0x2d404,0x52800048),(0x2d408,0xaa168108)])
    same=[];ctor=named(fs,'7CString19__from_vec_unchecked')
    for n in (0,15,383,384,385,4095,(1<<63)-2):
        v=Machine(fs,objects);vec,p=0x2a000000,0x60000000;v.blob(vec,bytes(24));v.write(vec,n+1,8);v.write(vec+8,p,8);v.write(vec+16,n,8)
        v.write(p+n,0xcc,1);v.x[0]=vec;v.run(ctor)
        assert v.x[:2]==[p,n+1] and v.read(p+n,1)==0 and not v.calls and not v.events
        same.append(dict(n=n,pointer=p,capacity=n+1,returned_pointer=v.x[0],returned_length=v.x[1],external_calls=0))
    return dict(short_route=dict(raw_operands=guard,argument='With unsigned n<384, n<=383; scratch sp+24 has room for n copied bytes and terminal byte at n. Physical frame496 is distinct from source logical scratch384. Nonzero initial scratch prevents missing termination from passing.'),
      allocation=dict(raw_operands=allocate,argument='For slice n<=isize::MAX, ADDS n+1 then B.MI excludes n=isize::MAX before allocation. For representable n>=384 allocator receives n+1,align1 before memcpy and external memchr. NulError returns original n+1 capacity and pointer; success enters CString with [capacity,pointer,len]=[n+1,p,n]. OOM/capacity boundary never returns io::Error.'),
      same_backing=dict(raw_operands=constructor,argument='capacity n+1 differs from old len n: B.EQ reserve edge not taken. Store0 at p[n], len increments to n+1. Unsigned capacity<=newlen holds at equality: B.LS bypasses shrink, returns same p,n+1. Algebra applies to all representable selected n; synthetic boundary cases do not allocate huge backing.',synthetic_cases=same),
      destruction=dict(raw_operands=cleanup,argument='Discriminant -1 selects callback with same CString pointer/length. Normal callback return executes STRB WZR,[x19] before original-pointer/n+1/align1 dealloc. NulError uses Vec pointer at sp+8 and capacity in x1, without a CString first-byte clear. Synthetic callback landingpad clears/deallocates the same saved pointer once and resumes unwind; actual unwind-table selection unproved.'),
      options_and_errors=dict(raw_operands=error,argument='12 bytes map custom_flags@0,mode@4,read/write/append/truncate/create/new@6..11. Defaults and two setters are separately evaluated from active LLVM. Selected masks1 and34 reach open without Error::new; full64 boolean masks match independent reference. CLOEXEC=0x1000000; mode u16 promoted in stack arg. Returned -1 borrows errno i32; external classifier controls retry; tag2 | (errno32 <<32) is retained. Finite traces impose no retry bound. Static NUL record/message/relocation are checked from raw data.'),
      interface=dict(open='768+7*n',error_native=23,new_policy_grant=False,private_effects_included=False))

def hostile(fs,objects,llvm):
    rows=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,IndexError,ValueError,Terminal) as e:
            last=traceback.extract_tb(e.__traceback__)[-1]
            rows.append(dict(name=name,rejected=True,reason=str(e)[:700],exception_type=type(e).__name__,
              rejection_site=dict(function=last.name,line=last.lineno,source=last.line)));return
        raise AssertionError(('independent-hostile-escaped',name))
    def patch(name,pattern,pc,w,n=384,pos=None,write=False,errno=None):
        s=named(fs,pattern);assert any(i['address']==pc for i in fs[s]['instructions'])
        reject(name,lambda:path_case(fs,objects,n,pos,write,errno,patch={(s,pc):w}))
    patch('threshold384-to385','11OpenOptions5__open',0x2ec78,0xf106005f)
    patch('threshold-bypasses-long-heap-route','11OpenOptions5__open',0x2ec7c,0xd503201f)
    patch('stack-terminal-position-offset','11OpenOptions5__open',0x2ec94,0x38356adf,n=17)
    patch('short-CStr-extent-loses-terminal','11OpenOptions5__open',0x2eca0,0x91000281,n=17)
    patch('short-validator-bypass','11OpenOptions5__open',0x2ecac,0x14000009,n=17,pos=8)
    patch('CString-request-n-plus2','SpecNewImpl13spec_new_impl',0x6630,0xb1000834)
    patch('CString-allocation-alignment8','SpecNewImpl13spec_new_impl',0x6650,0x52800101)
    patch('CString-NUL-success-guard-inverted','SpecNewImpl13spec_new_impl',0x66a8,0x37000080)
    patch('CString-NUL-return-pointer-register','SpecNewImpl13spec_new_impl',0x66ac,0xa9005e74,pos=2)
    patch('CString-reserve-guard-inverted','7CString19__from_vec_unchecked',0x5220,0x540002e1)
    patch('CString-capacity-load-uses-length','7CString19__from_vec_unchecked',0x5218,0xf9400813)
    patch('CString-shrink-bypass-inverted','7CString19__from_vec_unchecked',0x5234,0x54000448)
    patch('CString-terminator-store-omitted','7CString19__from_vec_unchecked',0x5228,0xd503201f)
    patch('CString-normal-drop-clear-omitted','run_with_cstr_allocating',0xa40c,0xd503201f)
    patch('CString-normal-free-length-register','run_with_cstr_allocating',0xa418,0xaa1503e1)
    patch('CString-normal-free-align2','run_with_cstr_allocating',0xa41c,0x52800042)
    patch('open-read-test-bypassed','4File6open_c',0x2d2dc,0x1400001c,n=17)
    patch('open-CLOEXEC-omitted','4File6open_c',0x2d3ac,0x2a1703e1,n=17)
    patch('open-mode-offset-shifted','4File6open_c',0x2d394,0x79400c58,n=17,write=True)
    patch('Os-error-shift32-lost','4File6open_c',0x2d408,0xaa160108,n=17,errno=13)
    patch('Os-error-tag3','4File6open_c',0x2d404,0x52800068,n=17,errno=-1)
    patch('core-terminal-position-guard-inverted','CStr19from_bytes_with_nul',0x59b4,0x54000080,n=17)
    patch('unsupported-active-SVC','11OpenOptions5__open',0x2ec78,0xd4000001,n=17)
    patch('unsupported-active-BRK','11OpenOptions5__open',0x2ec78,0xd4200020,n=17)
    patch('unsupported-PAGEOFF-addend','11OpenOptions5__open',0x2ecfc,0x91000484)
    patch('unknown-callback-pointer-base-register','11OpenOptions5__open',0x2ecfc,0x91000064)
    entry=named(fs,'11OpenOptions5__open')
    reject('foreign-direct-call-target',lambda:path_case(fs,objects,17,relocpatch={(entry,0x2eca4):'_unapproved_foreign'}))
    reject('static-NUL-record-relocation-pair-retargeted',lambda:path_case(fs,objects,17,8,relocpatch={(entry,0x2ecb0):'l_anon.fe79d0da482d11692d25899e0a8a72b8.368',(entry,0x2ecb4):'l_anon.fe79d0da482d11692d25899e0a8a72b8.368'}))
    def unwind_mutation(pc,w):
        s=named(fs,'run_with_cstr_allocating');v=Machine(fs,objects,{(s,pc):w});v.sp-=96;v.x[19]=v.alloc;v.x[20]=385;v.x[0]=0x29000000;v.blob(v.alloc,b'x'*384+b'\0');v.allocations[v.alloc]=385
        try:v.run(s,entry=0xa43c)
        except Terminal:pass
        assert v.noreturn=='unwind-resume' and ('free',v.alloc,385,1,0) in v.events and not v.allocations
    reject('unwind-drop-first-byte-clear-omitted',lambda:unwind_mutation(0xa440,0xd503201f))
    reject('unwind-deallocation-length-register',lambda:unwind_mutation(0xa44c,0xaa1503e1))
    def raw_mutation(kind):
        mutated=copy.deepcopy(objects);o=mutated['std'];raw=bytearray(o['raw'])
        if kind=='word':
            r=fs[entry]['instructions'][9];raw[r['object_offset']]^=1
        else:
            r=unique([r for r in o['relocs'] if r['section']==1 and r['address']==0x2eca4])
            info=struct.unpack_from('<I',raw,r['record_offset']+4)[0];wrong=unique([i for i,s in enumerate(o['symbols']) if s['name']=='_open'])
            struct.pack_into('<I',raw,r['record_offset']+4,(info&0xff000000)|wrong)
        p=macho(bytes(raw));p.update(member=o['member'],archive_sha256=o['archive_sha256']);mutated['std']=p
        bodies=copy.deepcopy(fs)
        # Let the outer member checksum agree, so the relocation control must
        # reject the raw decoded relocation itself rather than only a checksum.
        if kind=='relocation':
            for f in bodies.values():
                if f['archive']=='std':f['archive_member_sha256']=digest(bytes(raw))
        verify_bodies(mutated,bodies)
    reject('raw-word-mutated-original-annotations-preserved',lambda:raw_mutation('word'))
    reject('raw-relocation-symbol-index-mutated-original-annotations-preserved',lambda:raw_mutation('relocation'))
    def static_mutation():
        mutated=copy.deepcopy(objects);r=static_error(objects);raw=bytearray(mutated['std']['raw']);raw[r['record_object_offset']+8]^=1;mutated['std']['raw']=bytes(raw);static_error(mutated)
    reject('raw-NUL-static-record-length-changed',static_mutation)
    def ir_mutation(pattern,before,after):
        changed=copy.deepcopy(llvm);s=named(changed,pattern);assert before in changed[s]['body'];changed[s]['body']=changed[s]['body'].replace(before,after,1)+'; COMMENT DECOY '+before+'\n'
        mode='26native_open_create_path_v1' in pattern;entry=named(changed,'26native_open_create_path_v1' if mode else '_4File4openR');v=LLVM(changed);v.run(entry,[0x900000,0x200000,384])
        exp=bytearray(12);exp[4:6]=(438).to_bytes(2,'little');exp[7 if mode else 6]=1
        if mode:exp[11]=1
        assert v.calls==[(0x900000,exp.hex(),0x200000,384)]
    reject('LLVM-active-read-store-zero-comment-decoy',lambda:ir_mutation('_4File4openR','store i8 1, ptr %10, align 2','store i8 0, ptr %10, align 2'))
    reject('LLVM-active-read-route-disconnected-comment-decoy',lambda:ir_mutation('_4File4openR','br label %bb1','br label %bb2'))
    reject('LLVM-active-write-false-comment-decoy',lambda:ir_mutation('26native_open_create_path_v1','ptr align 4 %_7, i1 zeroext true','ptr align 4 %_7, i1 zeroext false'))
    reject('LLVM-active-create-new-false-comment-decoy',lambda:ir_mutation('26native_open_create_path_v1','ptr align 4 %_5, i1 zeroext true','ptr align 4 %_5, i1 zeroext false'))
    reject('LLVM-active-unsupported-opcode-comment-decoy',lambda:ir_mutation('_4File4openR','store i8 1, ptr %10, align 2','fence seq_cst'))
    reject('LLVM-active-path-length-load-rebound-comment-decoy',lambda:ir_mutation('_RNvXNtCsjIpoRzUjyHQ_4core7convertRNt','ptr %self, i64 8','ptr %self, i64 0'))
    # Positive decoy control: bogus annotation opcode, branch and external target must not alter behavior.
    changed=copy.deepcopy(fs)
    for f in changed.values():
        for i in f['instructions']:i['assembly']='svc #0; br x0; bl _unapproved_foreign; says n+2/alignment8'
    a,va=path_case(fs,objects,385);b,vb=path_case(changed,objects,385)
    assert a==b and va.trace==vb.trace and va.events==vb.events
    rows.append(dict(name='all-native-annotation-decoys-ignored',rejected=False,positive_control=True,identical_raw_trace_and_events=True))
    changed=copy.deepcopy(llvm)
    for f in changed.values():f['body']=f['body'].replace('start:\n','start:\n; fence seq_cst\n; call void @_unapproved_foreign()\n')
    a=LLVM(llvm);b=LLVM(changed);s=named(llvm,'_4File4openR');a.run(s,[9,19,384]);b.run(s,[9,19,384]);assert a.calls==b.calls and a.trace==b.trace
    rows.append(dict(name='LLVM-injected-comment-decoys-ignored',rejected=False,positive_control=True,identical_active_trace=True))
    return rows

def main():
    inputs,compiler=custody();objects,fs=objects_and_bodies();llvm,llvmrows=llvm_checks();error=static_error(objects)
    cases,coverage,edges,calls=native_checks(fs,objects);control=hostile(fs,objects,llvm);front=frontier(fs,coverage,edges,calls);critical=critical_contracts(fs,objects)
    # Exact inherited interface arithmetic; no policy/pricing reauthorization.
    contract=load(R/'verification/swift-guarded-snapshot-native-interface-bounds/contract.json')
    op=contract['open_records'];er=contract['error_records']
    assert len(op)+sum(r['fixed_bytes'] for r in op)==768 and sum(r['path_byte_multiplicity'] for r in op)==7
    assert len(er)+sum(r['fixed_bytes'] for r in er)==23
    put('input-custody.json',inputs);put('source-compiler.json',compiler);put('LLVM-cases.json',llvmrows)
    put('cases.json',cases);put('frontier.json',front);put('hostile-controls.json',control);put('static-error.json',error)
    put('critical-contracts.json',critical)
    counts={k:len(v) for k,v in cases.items()}
    summary=dict(schema=1,status='independently-reviewed-conditional-native-open-interface-pending-root-selection',
      candidate_seal_sha256=SEAL,root_release_sha256=RELEASE,source_tree_sha256=SOURCE,counts=counts,
      LLVM_cases=len(llvmrows),hostile_rejected=sum(r['rejected'] for r in control),positive_decoy_controls=sum(r.get('positive_control',False) for r in control),
      native_functions=7,native_instructions=438,native_relocations=46,instructions_observed=front['instructions_observed'],
      CFG_edges=front['edge_total'],CFG_edges_observed=front['edges_observed'],inherited_interface='768+7*n',inherited_error_native=23,
      independent_raw_archive_parser=True,independent_decoder_and_evaluator=True,producer_emulator_imported=False,
      source146_compiled_context_separate_from_installed_optimized_std=True,findings=[],
      actual_immutable_caller_or_executable_bound=False,P0_identity_pointee_extent_authority=False,actual_pricing_policy_grant=False,
      product_runtime=False,native_runtime=False,compiler_or_disassembler_invoked=False,OTA_release=False,GA_verified=False,
      pending=['Root acceptance and selection of this exact frozen candidate.','Actual immutable caller/build/session/executable and source-to-linked-executable composition.',
        'Actual P0/path/identity/diagnostic pointee extents and policy/pricing authority.',
        'Private allocator/memchr/memcpy/libc/kernel/OS callback/OOM/panic/unwinder effects; no finite EINTR retry bound.',
        'Healthy refusal/cleanup, successful fixture, native/device/store/customer/operational/FieldLog/OTA/GA qualification.'])
    put('summary.json',summary);print(json.dumps(summary,sort_keys=True))

if __name__=='__main__':main()
