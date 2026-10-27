"""Small independent JVM classfile reader; no dependencies, class loading, or source parsing."""
import struct
class Reader:
 def __init__(self,b):self.b=b;self.p=0
 def u(self,n):v=int.from_bytes(self.b[self.p:self.p+n],'big');self.p+=n;return v
 def take(self,n):v=self.b[self.p:self.p+n];self.p+=n;return v
 def attrs(self,cp):return {cp[self.u(2)][1]:self.take(self.u(4)) for _ in range(self.u(2))}
NAMES={0xb2:'getstatic',0xb3:'putstatic',0xb4:'getfield',0xb5:'putfield',0xb6:'invokevirtual',0xb7:'invokespecial',0xb8:'invokestatic',0xb9:'invokeinterface',0xba:'invokedynamic',0xbb:'new',0xbf:'athrow',0xb0:'areturn',0xac:'ireturn',0xad:'lreturn',0xae:'freturn',0xaf:'dreturn',0xb1:'return'}
LENGTH={**{x:2 for x in [0x10,0x12,*range(0x15,0x1a),*range(0x36,0x3b),0xa9,0xbc]},**{x:3 for x in [0x11,0x13,0x14,0x84,*range(0x99,0xa9),*range(0xb2,0xb9),0xbb,0xbd,0xc0,0xc1,0xc6,0xc7]},0xb9:5,0xba:5,0xc5:4,0xc8:5,0xc9:5}
def parse(data):
 r=Reader(data);assert r.u(4)==0xcafebabe
 minor,major=r.u(2),r.u(2);cp=[None];n=r.u(2)
 while len(cp)<n:
  tag=r.u(1)
  if tag==1:cp.append((tag,r.take(r.u(2)).decode('utf-8',errors='replace')))
  elif tag in (3,4):cp.append((tag,r.take(4).hex()))
  elif tag in (5,6):cp.append((tag,r.take(8).hex()));cp.append(None)
  elif tag in (7,8,16,19,20):cp.append((tag,r.u(2)))
  elif tag in (9,10,11,12,17,18):cp.append((tag,r.u(2),r.u(2)))
  elif tag==15:cp.append((tag,r.u(1),r.u(2)))
  else:raise ValueError(('constant pool tag',tag))
 def utf(i):return cp[i][1]
 def cls(i):return utf(cp[i][1])
 def ref(i):
  a=cp[i]
  if a[0] in (9,10,11):
   nt=cp[a[2]];return {'owner':cls(a[1]),'name':utf(nt[1]),'descriptor':utf(nt[2])}
  if a[0] in (17,18):
   nt=cp[a[2]];return {'owner':'<dynamic>','name':utf(nt[1]),'descriptor':utf(nt[2]),'bootstrap_index':a[1]}
  return {'constant_index':i,'constant_tag':a[0]}
 flags=r.u(2);name=cls(r.u(2));si=r.u(2);supername=cls(si) if si else None;interfaces=[cls(r.u(2)) for _ in range(r.u(2))]
 for _ in range(r.u(2)):r.take(6);r.attrs(cp)
 methods=[]
 for _ in range(r.u(2)):
  acc=r.u(2);mn=utf(r.u(2));md=utf(r.u(2));attrs=r.attrs(cp);m={'name':mn,'descriptor':md,'access':acc,'instructions':[],'lines':[],'exceptions':[]}
  if 'Code' in attrs:
   c=Reader(attrs['Code']);m['max_stack']=c.u(2);m['max_locals']=c.u(2);code=c.take(c.u(4));m['code_bytes']=len(code)
   m['exceptions']=[{'start':c.u(2),'end':c.u(2),'handler':c.u(2),'type_index':c.u(2)} for _ in range(c.u(2))];ca=c.attrs(cp)
   if 'LineNumberTable' in ca:
    l=Reader(ca['LineNumberTable']);m['lines']=[{'bci':l.u(2),'line':l.u(2)} for _ in range(l.u(2))]
   p=0
   while p<len(code):
    op=code[p];size=LENGTH.get(op,1);a={'bci':p,'opcode':op,'mnemonic':NAMES.get(op,f'op_{op:02x}')}
    a['line']=next((v['line'] for v in reversed(m['lines']) if v['bci']<=p),None)
    if op in (0xaa,0xab):
     q=(p+4)//4*4
     if op==0xaa:low=int.from_bytes(code[q+4:q+8],'big',signed=True);high=int.from_bytes(code[q+8:q+12],'big',signed=True);size=q-p+12+(high-low+1)*4
     else:count=int.from_bytes(code[q+4:q+8],'big',signed=True);size=q-p+8+count*8
    elif op==0xc4:size=6 if code[p+1]==0x84 else 4
    elif op in range(0xb2,0xbb):a['target']=ref(int.from_bytes(code[p+1:p+3],'big'))
    a['bytes']=code[p:p+size].hex();assert len(bytes.fromhex(a['bytes']))==size and size>0
    m['instructions'].append(a);p+=size
   assert p==len(code)
  methods.append(m)
 attrs=r.attrs(cp);assert r.p==len(data)
 boot=[]
 if 'BootstrapMethods' in attrs:
  b=Reader(attrs['BootstrapMethods'])
  for _ in range(b.u(2)):
   mr=b.u(2);args=[b.u(2) for _ in range(b.u(2))];handle=cp[mr]
   boot.append({'method':ref(handle[2]),'arguments':[{'handle_kind':cp[a][1],**ref(cp[a][2])} if cp[a][0]==15 else {'constant_tag':cp[a][0],'value':utf(cp[a][1]) if cp[a][0]==16 else cp[a][1]} for a in args]})
 for m in methods:
  for ins in m['instructions']:
   if ins['opcode']==0xba:ins['bootstrap']=boot[ins['target']['bootstrap_index']]
 return {'class':name,'super':supername,'interfaces':interfaces,'source_file':utf(int.from_bytes(attrs['SourceFile'],'big')) if 'SourceFile' in attrs else None,'major':major,'minor':minor,'access':flags,'methods':methods,'bootstrap_methods':boot}
