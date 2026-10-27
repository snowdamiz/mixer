"""Strict active-LLVM evaluator for the eight retained generic wrapper bodies.

Only the actually needed memory, tuple, calls and connected branches are
supported. Unsupported instructions and foreign call edges fail closed.
"""
import hashlib
import re

def sha(b):return hashlib.sha256(b).hexdigest()
def extract(text):
    lines=text.splitlines(keepends=True);out={};i=0
    while i<len(lines):
        if lines[i].startswith('define '):
            j=i+1
            while lines[j]!='}\n':j+=1
            symbol=lines[i].split('@',1)[1].split('(',1)[0];body=''.join(lines[i:j+1])
            out[symbol]=dict(symbol=symbol,start_line=i+1,end_line=j+1,body=body,sha256=sha(body.encode()))
            i=j
        i+=1
    return out

class IR:
    def __init__(self,functions):
        self.functions=functions;self.memory={};self.nextptr=0x100000;self.calls=[];self.trace=[]
    def write(self,a,value,n):
        for i in range(n):self.memory[a+i]=(value>>(i*8))&255
    def read(self,a,n):
        assert all(a+i in self.memory for i in range(n)),('undefined-IR-byte',a,n)
        return int.from_bytes(bytes(self.memory[a+i] for i in range(n)),'little')
    def bytes(self,a,n):return bytes(self.memory[a+i] for i in range(n))
    def run(self,symbol,args):
        if symbol.startswith('llvm.memcpy.'):
            dst,src,n,_=args;b=self.bytes(src,n)
            for i,v in enumerate(b):self.memory[dst+i]=v
            return None
        if symbol.endswith('_11OpenOptions5__open'):
            out,opts,p,n=args;self.calls.append(dict(symbol=symbol,output=out,options_bytes_hex=self.bytes(opts,12).hex(),path=p,length=n));return None
        assert symbol in self.functions,('unretained-IR-call',symbol)
        row=self.functions[symbol];lines=row['body'].splitlines();header=lines[0]
        params=re.findall(r'%[-.\w]+',header.split('(',1)[1].split(')',1)[0])
        # sret attributes have their own parentheses; take the full parameter area.
        params=re.findall(r'%[-.\w]+',header.split('(',1)[1].rsplit(')',1)[0])
        assert len(params)==len(args),(symbol,params,args)
        env=dict(zip(params,args));blocks={};block=None
        for line in lines[1:-1]:
            line=line.split(';',1)[0].strip()
            if not line:continue
            if line.endswith(':'):block=line[:-1];assert block not in blocks;blocks[block]=[]
            else:assert block is not None;blocks[block].append(line)
        def val(token):
            if token.startswith('%'):return env[token]
            if token=='poison':return (None,None)
            if token in ('true','false','null'):return int(token=='true')
            return int(token)
        def operand(text):
            m=re.search(r'(%[-.\w]+|true|false|null|poison|-?\d+)$',text.strip());assert m,text;return val(m[1])
        block='start'
        for _ in range(64):
            assert block in blocks
            jumped=False
            for ins in blocks[block]:
                self.trace.append([symbol,block,ins]);dest=None;rhs=ins
                if ins.startswith('%'):dest,rhs=ins.split(' = ',1)
                result=None
                if rhs.startswith('alloca '):
                    m=re.fullmatch(r'alloca \[(\d+) x i8\], align (\d+)',rhs);assert m,rhs
                    align=int(m[2]);self.nextptr=(self.nextptr+align-1)//align*align;result=self.nextptr;self.nextptr+=int(m[1])+16
                elif rhs.startswith('store '):
                    m=re.fullmatch(r'store (ptr|i\d+) (\S+), ptr (\S+), align \d+',rhs);assert m,rhs
                    self.write(val(m[3]),val(m[2]),8 if m[1]=='ptr' else int(m[1][1:])//8)
                elif rhs.startswith('load '):
                    m=re.fullmatch(r'load (ptr|i\d+), ptr (\S+), align \d+',rhs);assert m,rhs
                    result=self.read(val(m[2]),8 if m[1]=='ptr' else int(m[1][1:])//8)
                elif rhs.startswith('getelementptr '):
                    m=re.fullmatch(r'getelementptr inbounds i8, ptr (\S+), i64 (\S+)',rhs);assert m,rhs
                    result=val(m[1])+val(m[2])
                elif rhs.startswith('call '):
                    m=re.fullmatch(r'call .*?@([^ (]+)\((.*)\)(?: #\d+)?',rhs);assert m,rhs
                    arguments=[operand(a) for a in m[2].split(',')];result=self.run(m[1],arguments)
                elif rhs.startswith('extractvalue '):
                    m=re.fullmatch(r'extractvalue \{ ptr, i64 \} (\S+), ([01])',rhs);assert m,rhs;result=val(m[1])[int(m[2])]
                elif rhs.startswith('insertvalue '):
                    m=re.fullmatch(r'insertvalue \{ ptr, i64 \} (\S+), (?:ptr|i64) (\S+), ([01])',rhs);assert m,rhs
                    result=list(val(m[1]));result[int(m[3])]=val(m[2]);result=tuple(result)
                elif rhs.startswith('zext '):
                    m=re.fullmatch(r'zext i1 (\S+) to i8',rhs);assert m,rhs;result=val(m[1])
                elif rhs.startswith('br label '):block=rhs[len('br label %'):];jumped=True;break
                elif rhs.startswith('ret '):return None if rhs=='ret void' else operand(rhs)
                else:raise AssertionError(('unsupported-active-IR',symbol,block,ins))
                if dest is not None:env[dest]=result
            assert jumped,('IR-block-without-terminal',symbol,block)
        raise AssertionError(('IR-step-ceiling',symbol))

def select(functions):
    patterns=['_4File4openR','_11OpenOptions4openR','_11OpenOptions3new','_11OpenOptions5write','_11OpenOptions10create_new','26native_open_create_path_v1','_RNvXNtCsjIpoRzUjyHQ_4core7convertRNt','_RNvXs1l_NtCs1SSuMAdGM58_3std4pathNt']
    selected={};names={}
    for pattern in patterns:
        found=[s for s in functions if pattern in s];assert len(found)==1,(pattern,found)
        names[pattern]=found[0];selected[found[0]]=functions[found[0]]
    return selected,names

def evaluate(functions,names):
    rows=[]
    for write,pattern in [(False,'_4File4openR'),(True,'26native_open_create_path_v1')]:
        for p,n in [(0x1234000,0),(0x2345000,383),(0x3456000,384),(0x4567000,4095)]:
            vm=IR(functions);vm.run(names[pattern],[0x900000,p,n]);assert len(vm.calls)==1
            call=vm.calls[0];opts=bytes.fromhex(call['options_bytes_hex']);expect=bytearray(12);expect[4:6]=(438).to_bytes(2,'little');expect[7 if write else 6]=1
            if write:expect[11]=1
            assert opts==expect and call['path']==p and call['length']==n and call['output']==0x900000,(write,call)
            rows.append(dict(write=write,path=p,length=n,options_bytes_hex=opts.hex(),external_native_symbol='_'+call['symbol'],active_steps=len(vm.trace)))
    return rows
