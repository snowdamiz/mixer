"""Independent byte builder from genuine Wasm + actual retained host facts.

This data comparison does not validate Wasm or manufacture authority.
"""
import ast,hashlib,re,struct
from pathlib import Path
def words(v):return struct.pack('<'+'Q'*len(v),*v)
class Reader:
 def __init__(self,b,at=0):self.b=b;self.at=at
 def byte(self):v=self.b[self.at];self.at+=1;return v
 def uint(self):
  n=0;s=0
  while True:
   b=self.byte();n|=(b&127)<<s;s+=7
   if b<128:return n
 def span(self):
  n=self.uint();at=self.at;self.at+=n;return[at,n]
 def constant(self):
  start=self.at;assert self.byte()==0x41;n=self.uint();assert self.byte()==11;return start,self.at-start,n
TYPE={0x7f:1,0x7e:2,0x7d:3,0x7c:4}
def wasm(b):
 r=Reader(b,8);parts=[[],[],[],[],[],[],[],[]];memory=table=None;mo=to=None;md=td=None
 while r.at<len(b):
  sid=r.byte();n=r.uint();end=r.at+n;count=r.uint()
  if sid==1:
   for _ in range(count):
    assert r.byte()==0x60;first=len(parts[1]);n=r.uint();parts[1].extend([[TYPE[r.byte()]]for _ in range(n)])
    result=r.uint();assert result<=1;parts[0].append([first,n,TYPE[r.byte()]if result else 0])
  elif sid==2:
   for _ in range(count):
    module=r.span();name=r.span();assert r.byte()==0;parts[2].append(module+name+[r.uint()])
  elif sid==3:parts[3]=[[0,0,r.uint()]for _ in range(count)]
  elif sid in(4,5):
   assert count==1
   if sid==4:assert r.byte()==0x70
   offset=r.at;flag=r.uint();minimum=r.uint();declared=r.uint()if flag else None
   if sid==4:table=(minimum,declared if flag else 65536);to=offset;td=declared
   else:memory=(minimum,declared if flag else 768);mo=offset;md=declared
  elif sid==6:
   for _ in range(count):
    ty=TYPE[r.byte()];mutable=r.byte();at,n,_=r.constant();parts[4].append([ty,mutable,at,n])
  elif sid==7:
   for _ in range(count):parts[5].append(r.span()+[r.byte(),r.uint()])
  elif sid==9:
   for _ in range(count):
    assert r.uint()==0;_,_,dest=r.constant();n=r.uint();start=r.at
    for _ in range(n):r.uint()
    parts[7].append([start,r.at-start,dest,n])
  elif sid==10:
   assert count==len(parts[3])
   for i in range(count):
    n=r.uint();at=r.at;r.at+=n;parts[3][i][:2]=[at,n]
  elif sid==11:
   for _ in range(count):
    assert r.uint()==0;_,_,dest=r.constant();n=r.uint();at=r.at;r.at+=n;parts[6].append([at,n,dest,n])
  else:raise AssertionError(('unexpected test section',sid))
  assert r.at==end,(sid,r.at,end)
 return parts,memory,table,mo,to,md,td
def named(text):
 return {k:int(v)for k,v in re.findall(r'(\w+): (\d+)',text)}
def observations(text):
 result=[]
 for _,value in re.findall(r'(\w+): (Some\(\d+\)|None|\d+)',text):
  if value=='None':result.extend([0,0])
  elif value.startswith('Some'):result.extend([1,int(value[5:-1])])
  else:result.append(int(value))
 assert len(result)==20;return result
def build(directory,context):
 directory=Path(directory);b=(directory/'source.wasm').read_bytes();facts=(directory/'actual.facts').read_text().splitlines()
 data={line.split('\t')[0]:line.split('\t',1)[1]for line in facts if not line.startswith('BUFFER\t')}
 buffers={int(line.split('\t')[1]):ast.literal_eval(line.split('\t')[2].replace('Metadata','2'))for line in facts if line.startswith('BUFFER\t')}
 records,memory,table,mo,to,md,td=wasm(b);bodies=[b]+[b''.join(words(row)for row in section)for section in records]
 h=bytearray(2560);h[:8]=b'MIXSNB02';extent=2560+sum(map(len,bodies));u=list(named(data['USAGE']).values());o=observations(data['OBS'])
 h[8:96]=words([2,2560,extent,9,1,1,34,len(b),o[5],8,664]);limits=[67108864,16777216,1048576,512000000,120000]
 h[96:136]=words(limits);h[144:224]=words(u);h[224:384]=words(o)
 opt=lambda v:[0,0]if v is None else[1,v]
 h[384:488]=words([1,*memory,1,*table,*opt(md),*opt(td),mo,to,o[5]])
 h[512:520]=b'MIXLPR01';h[520:584]=words([1,576,len(b),*limits])
 source_identity=bytes.fromhex(context['source_identity_hex']);session=(directory/'session.bin').read_bytes();buildbytes=(directory/'build.bin').read_bytes()
 retained=[hashlib.sha256(b).digest(),bytes.fromhex(context['manifest_sha256']),hashlib.sha256(buildbytes).digest(),hashlib.sha256(session).digest(),bytes.fromhex(context['executable_sha256']),bytes.fromhex(context['nonce_hex'])]
 h[584:776]=b''.join(retained)
 h[776:1032]=source_identity+bytes.fromhex(context['build_identity_hex'])+bytes.fromhex(context['session_identity_hex'])+bytes.fromhex(context['executable_identity_hex'])
 h[1088:1096]=b'MIXRTB01';wasi=data['WASI'];present=int(wasi!='None')
 h[1096:1128]=words([1,512,present,int(data['OWNER'])]);h[1128:1264]=words(list(named(data['RUN']).values()))
 if present:
  h[1264:1320]=words(list(named(wasi).values()))
  h[1320:1360]=words([int(v=='true')for _,v in re.findall(r'(\w+): (true|false)',wasi)])
 h[1360:1424]=words(ast.literal_eval(data['SCALARS']))
 at=2560
 for sid,body in enumerate(bodies):
  if sid==0:n=c=charge=len(b);native=1;category=1
  else:n,c,native,charge,category=buffers[sid];assert n==len(records[sid-1])
  h[1600+sid*64:1664+sid*64]=words([sid,n,c,native,charge,category,at,len(body)]);at+=len(body)
 h[2176:2448]=words(list(range(1,35)))
 expected=bytes(h)+b''.join(bodies);actual=(directory/'actual.mixsnb02').read_bytes()
 assert expected==actual,('byte mismatch',next((i for i,(a,z)in enumerate(zip(actual,expected))if a!=z),None),len(actual),len(expected))
 return {'bytes':len(actual),'sha256':hashlib.sha256(actual).hexdigest(),'all_bytes_equal':True,'logical_counts':[len(b)]+[len(s)for s in records],'capacity_slack':[buffers[i][1]-buffers[i][0]for i in range(1,9)]}
