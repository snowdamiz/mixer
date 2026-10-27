"""Fail-closed bounded AArch64 dataflow evaluator; ignores assembly annotations.

This evaluates retained words over synthetic bytes. External allocator/libc,
memchr and OS-function callbacks are explicit interface stubs, never executed.
"""
import struct

MASK=(1<<64)-1
def signed(n,b):return n-(1<<b) if n&(1<<(b-1)) else n
def ror(n,r,width):
    r%=width;return ((n>>r)|(n<<(width-r)))&((1<<width)-1)
def bitmask(w,width):
    n=(w>>22)&1;immr=(w>>16)&63;imms=(w>>10)&63
    length=((n<<6)|((~imms)&63)).bit_length()-1
    assert length>=1
    levels=(1<<length)-1;s=imms&levels;r=immr&levels
    assert s!=levels
    esize=1<<length;one=ror((1<<(s+1))-1,r,esize)
    return sum(one<<i for i in range(0,width,esize))

class Native:
    def __init__(self,functions,objects,words=None,relocations=None):
        self.functions=functions;self.objects=objects;self.patch=words or {};self.relocpatch=relocations or {}
        self.regs=[0]*31;self.sp=0x70000000;self.mem={};self.trace=[];self.events=[];self.flags=(False,False,False,False)
        self.nextalloc=0x60000000;self.alloc_fail=False;self.opens=[7];self.interrupted=[];self.noreturn=None
        self.symaddr={};self.addrname={}
        for ai,(name,(_,_,m)) in enumerate(objects.items()):
            for s in m['symbols']:
                if s['section']:
                    address=0x100000000+ai*0x1000000+s['value']
                    self.symaddr[s['name']]=address;self.addrname[address]=s['name']
        self.osglobal=self.symaddr['__RNvNtNtNtCsjIpoRzUjyHQ_4core2io5error12os_functions12OS_FUNCTIONS']
        self.vtable=0x50000000;self.errnoptr=0x50000100;self.interruptedfn=0x50000200
        self.write(self.osglobal,self.symaddr['l_anon.fe79d0da482d11692d25899e0a8a72b8.76'],8)
        self.write(self.vtable+16,self.interruptedfn,8)
        # Synthetic initialized caller stack/register save area. No real stack is read.
        for a in range(self.sp-8192,self.sp+256):self.mem[a]=0
    def read(self,a,n):
        assert n in (1,2,4,8) and all(a+i in self.mem for i in range(n)),('unknown-read',hex(a),n)
        return int.from_bytes(bytes(self.mem[a+i] for i in range(n)),'little')
    def write(self,a,v,n):
        for i in range(n):self.mem[a+i]=(v>>(8*i))&255
    def blob(self,a,b):
        for i,v in enumerate(b):self.mem[a+i]=v
    def bytes(self,a,n):return bytes(self.mem[a+i] for i in range(n))
    def reg(self,i,sp=False):return self.sp if i==31 and sp else (0 if i==31 else self.regs[i])
    def setreg(self,i,v,width=64,sp=False):
        v &= (1<<width)-1
        if i==31:
            if sp:self.sp=v
        else:self.regs[i]=v
    def cmp(self,a,b,width,add=False):
        mask=(1<<width)-1;a&=mask;b&=mask
        result=(a+b if add else a-b)&mask
        carry=a+b>mask if add else a>=b
        overflow=bool((~(a^b) if add else (a^b))&(a^result)&(1<<(width-1)))
        self.flags=(bool(result&(1<<(width-1))),result==0,carry,overflow)
        return result
    def cond(self,c):
        n,z,carry,v=self.flags
        base=[z,carry,n,v,carry and not z,n==v,(n==v) and not z,True][c>>1]
        return not base if c&1 and c!=15 else base
    def relocated(self,f,pc,types=None):
        rows=[r for r in f['relocations'] if r['instruction_address']==pc and (types is None or r['type'] in types)]
        assert len(rows)<=1
        if not rows:return None
        return self.relocpatch.get((f['symbol'],pc),rows[0]['target'])
    def external(self,name):
        r=self.regs;self.events.append(dict(kind='call',symbol=name,args=r[:4].copy()))
        if name in self.functions:
            self.run(name);return
        if name=='_memcpy':self.blob(r[0],self.bytes(r[1],r[2]));return
        if '___rust_no_alloc_shim_' in name:return
        if name.endswith('12___rust_alloc'):
            n,a=r[:2];self.events.append(dict(kind='allocation',bytes=n,alignment=a))
            if self.alloc_fail:r[0]=0
            else:
                r[0]=self.nextalloc;self.nextalloc+=max(16,n+16);self.blob(r[0],bytes([0xcc])*n)
            return
        if name.endswith('14___rust_dealloc'):
            self.events.append(dict(kind='deallocation',pointer=r[0],bytes=r[1],alignment=r[2]));return
        if name.endswith('14___rust_realloc') or '11finish_grow' in name:
            raise AssertionError(('out-of-selected-CString-reserve-shrink-path',name))
        if name.endswith('14memchr_aligned'):
            data=self.bytes(r[1],r[2]);i=data.find(bytes([r[0]&255]));r[0]=int(i>=0);r[1]=0 if i<0 else i
            self.events.append(dict(kind='external-memchr-interface',found=i));return
        if name=='_open':
            assert self.opens, 'finite test stub exhausted; no private retry bound inferred'
            result=self.opens.pop(0)
            self.events.append(dict(kind='open-interface',path=r[0],flags=r[1],promoted_mode=self.read(self.sp,4),result=result))
            if result<0:self.write(self.errnoptr,-result,4);r[0]=(1<<32)-1
            else:r[0]=result
            return
        if name=='___error':r[0]=self.errnoptr;return
        if name.endswith('19set_functions_inner'):
            self.write(self.osglobal,r[0],8);return
        if name.endswith('16get_os_functions'):r[0]=self.vtable;return
        if name=='external-is-interrupted':
            value=self.interrupted.pop(0) if self.interrupted else r[0]==4
            self.events.append(dict(kind='external-interruption-classification',errno=r[0],interrupted=value));r[0]=int(value);return
        if '5Error3new' in name:
            self.events.append(dict(kind='out-of-selected-options-custom-error',kind_discriminant=r[0],message_pointer=r[1],message_length=r[2]));r[0]=0x40000003;return
        if name.endswith('12handle_error'):
            self.noreturn='allocator-or-capacity-handler';raise StopIteration(self.noreturn)
        if name=='__Unwind_Resume':self.noreturn='unwind-resume';raise StopIteration(self.noreturn)
        raise AssertionError(('unapproved-external-edge',name))
    def run(self,symbol,entry=None,budget=20000):
        f=self.functions[symbol];ins={x['address']:x['word'] for x in f['instructions']};pc=f['address'] if entry is None else entry
        startsp=self.sp
        for _ in range(budget):
            assert pc in ins,('branch-outside-retained-body',symbol,hex(pc))
            w=self.patch.get((symbol,pc),ins[pc]);self.trace.append([symbol,pc,w]);rd=w&31;rn=(w>>5)&31;rm=(w>>16)&31;width=64 if w>>31 else 32
            nextpc=pc+4
            if w==0xd65f03c0:
                assert self.sp==startsp,('stack-not-restored',symbol);return
            elif w==0xd503201f:pass
            elif w&0xfc000000 in (0x14000000,0x94000000):
                target=self.relocated(f,pc,{2})
                if target:
                    self.external(target)
                    if w&0xfc000000==0x14000000:
                        assert self.sp==startsp;return
                else:nextpc=pc+signed(w&0x3ffffff,26)*4
            elif w&0xff000010==0x54000000:
                if self.cond(w&15):nextpc=pc+signed((w>>5)&0x7ffff,19)*4
            elif w&0x7e000000==0x34000000:
                value=self.reg(rd)&((1<<width)-1);take=(value!=0) if (w>>24)&1 else value==0
                if take:nextpc=pc+signed((w>>5)&0x7ffff,19)*4
            elif w&0x7e000000==0x36000000:
                bit=((w>>31)<<5)|((w>>19)&31);take=bool(self.reg(rd)&(1<<bit))==bool((w>>24)&1)
                if take:nextpc=pc+signed((w>>5)&0x3fff,14)*4
            elif w&0xfffffc1f==0xd63f0000:
                target=self.reg(rn)
                self.external('external-is-interrupted' if target==self.interruptedfn else self.addrname[target])
            elif w&0x9f000000==0x90000000:
                target=self.relocated(f,pc,{3,5});assert target
                address=self.symaddr[target]
                # GOT page pairs name the slot, whose content is the symbol address.
                if any(r['instruction_address']==pc and r['type']==5 for r in f['relocations']):
                    slot=0x300000000+address;self.write(slot,address,8);address=slot
                self.setreg(rd,address&~4095)
            elif w&0x1f000000==0x11000000:
                imm=((w>>10)&4095)<<(12 if (w>>22)&1 else 0)
                target=self.relocated(f,pc,{4})
                if target:imm=self.symaddr[target]&4095
                a=self.reg(rn,True);is_sub=bool((w>>30)&1);flags=bool((w>>29)&1)
                val=self.cmp(a,imm,width,not is_sub) if flags else (a-imm if is_sub else a+imm)
                self.setreg(rd,val,width,not flags)
            elif w&0x1f200000==0x0b000000:
                shift=(w>>22)&3;amount=(w>>10)&63;b=self.reg(rm)&((1<<width)-1)
                b=(b<<amount if shift==0 else b>>amount if shift==1 else signed(b,width)>>amount)
                assert shift!=3
                a=self.reg(rn);sub=bool((w>>30)&1);flags=bool((w>>29)&1)
                val=self.cmp(a,b,width,not sub) if flags else (a-b if sub else a+b);self.setreg(rd,val,width)
            elif w&0x1f800000==0x12800000:
                op=(w>>29)&3;imm=((w>>5)&65535)<<(((w>>21)&3)*16)
                if op==0:val=~imm
                elif op==2:val=imm
                else:
                    assert op==3;mask=65535<<(((w>>21)&3)*16);val=(self.reg(rd)&~mask)|imm
                self.setreg(rd,val,width)
            elif w&0x1f800000==0x12000000:
                mask=bitmask(w,width);op=(w>>29)&3;a=self.reg(rn)
                val=(a&mask if op in (0,3) else a|mask if op==1 else a^mask)
                self.setreg(rd,val,width)
                if op==3:self.flags=(bool(val&(1<<(width-1))),val==0,False,False)
            elif w&0x1f000000==0x0a000000:
                amount=(w>>10)&63;shift=(w>>22)&3;b=self.reg(rm)&((1<<width)-1)
                b=b<<amount if shift==0 else b>>amount if shift==1 else signed(b,width)>>amount if shift==2 else ror(b,amount,width)
                if (w>>21)&1:b=~b
                op=(w>>29)&3;a=self.reg(rn);val=(a&b if op in (0,3) else a|b if op==1 else a^b)&((1<<width)-1)
                self.setreg(rd,val,width)
                if op==3:self.flags=(bool(val&(1<<(width-1))),val==0,False,False)
            elif w&0x1fe00c00==0x1a800000:
                assert not (w>>30)&1 and not (w>>10)&1
                self.setreg(rd,self.reg(rn) if self.cond((w>>12)&15) else self.reg(rm),width)
            elif w&0x3b000000==0x39000000:
                size=1<<((w>>30)&3);op=(w>>22)&3;imm=((w>>10)&4095)*size
                target=self.relocated(f,pc,{6})
                if target:imm=(0x300000000+self.symaddr[target])&4095
                address=self.reg(rn,True)+imm
                if op==0:self.write(address,self.reg(rd),size)
                else:
                    v=self.read(address,size)
                    if op==2:v=signed(v,size*8)
                    self.setreg(rd,v,64 if op==2 or size==8 else 32)
            elif w&0x3b200c00==0x38000000:
                size=1<<((w>>30)&3);op=(w>>22)&3;address=self.reg(rn,True)+signed((w>>12)&511,9)
                if op==0:self.write(address,self.reg(rd),size)
                else:self.setreg(rd,self.read(address,size),64 if size==8 else 32)
            elif w&0x3b200c00==0x38200800:
                size=1<<((w>>30)&3);assert ((w>>13)&7)==3
                address=self.reg(rn,True)+(self.reg(rm)<<(((w>>12)&1)*((w>>30)&3)))
                if (w>>22)&1:self.setreg(rd,self.read(address,size),64 if size==8 else 32)
                else:self.write(address,self.reg(rd),size)
            elif w&0x3a000000==0x28000000:
                assert (w>>30)&3==2
                mode=(w>>23)&3;off=signed((w>>15)&127,7)*8;base=self.reg(rn,True);address=base if mode==1 else base+off;rt2=(w>>10)&31
                if (w>>22)&1:self.setreg(rd,self.read(address,8));self.setreg(rt2,self.read(address+8,8))
                else:self.write(address,self.reg(rd),8);self.write(address+8,self.reg(rt2),8)
                if mode in (1,3):self.setreg(rn,base+off,sp=True)
            else:raise AssertionError(('unsupported-active-instruction',symbol,hex(pc),hex(w)))
            pc=nextpc
        raise AssertionError(('bounded-offline-budget-exceeded',symbol,budget))
