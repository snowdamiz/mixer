import pathlib,json,hashlib,struct,zlib,zipfile,sys,datetime,types,io,contextlib
B=pathlib.Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-53f259fe/verification/plan-continuation-2026-11-07/android-api28-packaging-fix')
ROOT=B.parents[2]; OUT=pathlib.Path(__file__).parent
R={'python':sys.version,'command':'python3 -B '+str(pathlib.Path(__file__)),'checks':{}}
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def fid(p):return ident(pathlib.Path(p).read_bytes())
def j(p):return json.loads(pathlib.Path(p).read_text())
def u(b,p):return struct.unpack_from('<I',b,p)[0]
def lp(b,p=0):n=u(b,p);assert p+4+n<=len(b);return b[p+4:p+4+n],p+4+n
def seq(b):
 p=0
 while p<len(b):v,p=lp(b,p);yield v
 assert p==len(b)
def dex(b):
 assert b[:8]==b'dex\n039\0' and u(b,32)==len(b) and u(b,36)==112
 assert b[12:32]==hashlib.sha1(b[32:]).digest() and u(b,8)==zlib.adler32(b[12:])&0xffffffff
 sn,so,tn,to=struct.unpack_from('<4I',b,56); cn,co=struct.unpack_from('<2I',b,96)
 strings=[]
 for i in range(sn):
  p=u(b,so+4*i)
  for _ in range(5):
   v=b[p];p+=1
   if v<128:break
  strings.append(b[p:b.index(0,p)].decode('utf-8',errors='replace'))
 types=[strings[u(b,to+4*i)] for i in range(tn)]
 defs=[types[u(b,co+32*i)] for i in range(cn)]
 assert len(defs)==len(set(defs))
 return set(defs),set(types),strings
M=j(B/'frozen-ready-input-manifest.json'); old=j(B/'prior-evidence/prepared.json')
for rel,w in M['retainedFiles'].items():assert fid(B/rel)==w,rel
R['checks']['frozenFiles']=len(M['retainedFiles'])
for rel,w in M['sourceInputs'].items():assert fid(ROOT/rel)==w
for name in ['compile-1','compile-2']:
 d=j(B/name/'prepared.json')
 for c in d['commands']:
  assert fid(B/name/c['output'])==c['outputIdentity'];assert c['cleanup']['groupAbsent'] and c['cleanup']['leaderReaped']
  assert c['exitCode']==0
 for rel,w in d['sourceInputs'].items():assert fid(B/name/'inputs'/rel)==w
 for rel,w in d['harnessClassfiles'].items():
  f=B/name/'harness-classfiles'/rel;assert fid(f)==w;assert struct.unpack_from('>H',f.read_bytes(),6)[0]==61
 assert d['retained215Classfiles']==old['retained215Classfiles']==M['productClassfiles']
 for rel,w in d['retained215Classfiles'].items():assert fid(B/name/'product-classfiles'/rel)==w
 with zipfile.ZipFile(B/name/'work/product-classpath.jar') as z:
  assert len(z.namelist())==215 and set(z.namelist())==set(M['productClassfiles'])
  for rel,w in M['productClassfiles'].items():assert ident(z.read(rel))==w
 R['checks'][name]={'commandsVerified':len(d['commands']),'classfiles':215,'harnessClassfilesJava17':len(d['harnessClassfiles']),'status':d['status']}
product=(B/'compile-2/classes.dex').read_bytes(); rejected=(B/'compile-1/classes2.dex').read_bytes();test=(B/'compile-2/classes2.dex').read_bytes()
pd,pt,ps=dex(product);rd,rt,rs=dex(rejected);td,tt,ts=dex(test)
assert ident(product)=={'bytes':417304,'sha256':'5ab1fbfcb805ee0ce43a8c131ffe51ef66f64d4614d9c13bffe7f86283e65c67'} and len(pd)==387
assert pd&rd=={'Lcom/android/tools/r8/annotations/LambdaMethod;'} and len(rd)==13
assert not pd&td and len(td)==12
for name,defs in [('compile-1/product',pd),('compile-1/test',rd),('compile-2/product',pd),('compile-2/test',td)]:
 lines=(B/(name+'-dexdump.log')).read_text().splitlines();assert {s.split("'",2)[1] for s in lines if s.strip().startswith('Class descriptor')}==defs
R['checks']['dex']={'product':ident(product),'rejected':ident(rejected),'fixed':ident(test),'definitions':[len(pd),len(rd),len(td)],'reproducedOverlap':sorted(pd&rd),'fixedOverlap':sorted(pd&td),'sharedReferencedTypes':len(pt&tt),'testDefinitions':sorted(td)}
with zipfile.ZipFile(B/M['apk']['relativePath']) as z:
 assert len(z.namelist())==len(set(z.namelist())) and {n for n in z.namelist() if n.endswith('.dex')}=={'classes.dex','classes2.dex'}
 assert z.read('classes.dex')==product and z.read('classes2.dex')==test
 assert {n for n in z.namelist() if n.startswith('lib/')}==set(M['nativeLibraries'])
 for rel,w in M['nativeLibraries'].items():assert ident(z.read(rel))==w
 axml=z.read('AndroidManifest.xml'); infos=z.infolist()
 # Parse binary Android XML, without using dumped text.
 strings=[];nodes=[];p=8
 while p<len(axml):
  kind,hs,size=struct.unpack_from('<HHI',axml,p);assert size>=hs and p+size<=len(axml)
  if kind==1:
   count,styles,flags,start,sty=struct.unpack_from('<5I',axml,p+8)
   def length(pos,utf8):
    if utf8:
     v=axml[pos];return (((v&127)<<8)|axml[pos+1],pos+2) if v&128 else (v,pos+1)
    v=struct.unpack_from('<H',axml,pos)[0];return (((v&32767)<<16)|struct.unpack_from('<H',axml,pos+2)[0],pos+4) if v&32768 else (v,pos+2)
   for i in range(count):
    at=p+start+u(axml,p+hs+4*i);n,at=length(at,bool(flags&256))
    if flags&256:n,at=length(at,True);strings.append(axml[at:at+n].decode('utf-8'))
    else:strings.append(axml[at:at+2*n].decode('utf-16le'))
  elif kind==0x102:
   name=strings[u(axml,p+20)];ast,asz,ac=struct.unpack_from('<3H',axml,p+24);attrs={}
   for i in range(ac):
    at=p+16+ast+asz*i;ns,ni,raw=struct.unpack_from('<3I',axml,at);typ=axml[at+15];val=u(axml,at+16)
    attrs[strings[ni]]=strings[val] if typ==3 else (bool(val) if typ==18 else val)
   nodes.append({'tag':name,'attrs':attrs})
  p+=size
 assert p==len(axml)
 by={n['tag']:n['attrs'] for n in nodes};assert by['manifest']['package']==by['instrumentation']['targetPackage']==M['package']
 assert by['uses-sdk']['minSdkVersion']==by['uses-sdk']['targetSdkVersion']==28
 assert by['instrumentation']['name']==M['instrumentation']
 activities=[n['attrs'] for n in nodes if n['tag']=='activity'];assert {a['name'] for a in activities}=={'dev.mixer.android.MixerActivity','dev.mixer.android.NativeLowerApiCompatibilityActivity'}
 assert all(a['exported']==False for a in activities)
 assert all('L'+a['name'].replace('.','/')+';' in pd|td for a in activities)
 assert by['application']['extractNativeLibs'] and by['application']['hasCode'] and by['application']['debuggable']
 R['checks']['binaryManifest']=nodes
# APK v3 signature and chunked content digest, independent pure Python RSA verification.
apk=(B/M['apk']['relativePath']).read_bytes();eocd=apk.rfind(b'PK\x05\x06');assert eocd+22+struct.unpack_from('<H',apk,eocd+20)[0]==len(apk)
cd=u(apk,eocd+16);assert apk[cd-16:cd]==b'APK Sig Block 42';sz=struct.unpack_from('<Q',apk,cd-24)[0];start=cd-sz-8;assert struct.unpack_from('<Q',apk,start)[0]==sz
p=start+8;blocks={}
while p<cd-24:
 n=struct.unpack_from('<Q',apk,p)[0];p+=8;kind=u(apk,p);blocks[kind]=apk[p+4:p+n];p+=n
assert p==cd-24
signers,pend=lp(blocks[0xf05368c0]);assert pend==len(blocks[0xf05368c0]);signer=list(seq(signers));assert len(signer)==1
s=signer[0];signed,p=lp(s);lo,hi=struct.unpack_from('<II',s,p);p+=8;sigs,p=lp(s,p);pub,p=lp(s,p);assert p==len(s) and lo<=28<=hi
digests,p=lp(signed);certs,p=lp(signed,p);assert struct.unpack_from('<II',signed,p)==(lo,hi)
cert=list(seq(certs))[0];siglist=list(seq(sigs));assert len(siglist)==1;algorithm=u(siglist[0],0);signature,end=lp(siglist[0],4);assert algorithm==0x103
# Minimal DER parser for SPKI RSA public key, no crypto library or executable.
def der(b,p=0):
 tag=b[p];n=b[p+1];q=p+2
 if n&128:k=n&127;n=int.from_bytes(b[q:q+k],'big');q+=k
 assert q+n<=len(b);return tag,b[q:q+n],q+n
_,spki,_=der(pub);_,alg,p=der(spki);_,bits,p=der(spki,p);assert bits[0]==0
_,key,_=der(bits[1:]);_,mod,p=der(key);_,exp,p=der(key,p);n=int.from_bytes(mod,'big');e=int.from_bytes(exp,'big')
encoded=pow(int.from_bytes(signature,'big'),e,n).to_bytes((n.bit_length()+7)//8,'big');di=bytes.fromhex('3031300d060960864801650304020105000420')+hashlib.sha256(signed).digest();assert encoded==b'\0\x01'+b'\xff'*(len(encoded)-len(di)-3)+b'\0'+di
# Certificate must contain the exact signer SPKI; certificate identity agrees with retained SDK verification.
assert pub in cert;assert hashlib.sha256(cert).hexdigest()=='997bcdaa0749d8c34316c4537a6f2d31cbece3f2a22c11deb69f30abc81fb0ee'
patched=bytearray(apk[eocd:]);struct.pack_into('<I',patched,16,start);chunks=[]
for section in [apk[:start],apk[cd:eocd],patched]:
 for off in range(0,len(section),1048576):
  chunk=section[off:off+1048576];chunks.append(hashlib.sha256(b'\xa5'+struct.pack('<I',len(chunk))+chunk).digest())
computed=hashlib.sha256(b'\x5a'+struct.pack('<I',len(chunks))+b''.join(chunks)).digest();dg=list(seq(digests));assert len(dg)==1 and u(dg[0],0)==algorithm;wanted,_=lp(dg[0],4);assert wanted==computed
for info in infos:
 if info.filename.startswith('lib/'):
  at=info.header_offset;nl,xl=struct.unpack_from('<HH',apk,at+26);assert (at+30+nl+xl)%16384==0 and info.compress_type==0
R['checks']['apk']={**ident(apk),'v3RSA2048SHA256Signature':True,'chunkedContentDigest':computed.hex(),'certificateSHA256':hashlib.sha256(cert).hexdigest(),'signerSDKRange':[lo,hi],'nativeLibrariesStored16KiBAligned':18}
# Run only audited pure functions on retained control archives, under no-bytecode mode.
mod=types.ModuleType('dex_reader');exec(compile((B/'dex_reader.py').read_text(),str(B/'dex_reader.py'),'exec'),mod.__dict__);sys.modules['dex_reader']=mod
payload={};exec(compile((B/'payload.py').read_text(),str(B/'payload.py'),'exec'),payload)
controls=j(B/'controls/result.json');outcomes={}
with zipfile.ZipFile(B/M['apk']['relativePath']) as z:payload['validate_payload'](product,test,M['nativeLibraries'],z)
for name,c in controls['controls'].items():
 assert fid(c['path'])=={k:c[k] for k in ['bytes','sha256']}
 try:
  with zipfile.ZipFile(c['path']) as z:payload['validate_payload'](product,test,M['nativeLibraries'],z)
 except ValueError as error:
  assert str(error).startswith(c['expectedRefusal']);outcomes[name]=str(error)
 else:raise AssertionError('accepted '+name)
R['checks']['sixRetainedControls']=outcomes
# Verify upstream provenance, retained native package, source closure and tool bytes, without executing tools.
prov=j(B/'provenance.json')
for p,w in prov['priorEvidence'].items():assert fid(p)==w and fid(B/'prior-evidence'/pathlib.Path(p).name)==w
reuse=j(B/'accepted-bindings/native-reuse.json')
assert fid(B/'accepted-bindings/build-receipt.json')['sha256']==reuse['buildReceiptSHA256'];assert fid(B/'accepted-bindings/source-lock.json')['sha256']==reuse['sourceLockSHA256']
assert fid(reuse['retainedAPK'])['sha256']==reuse['retainedAPKSHA256']
with zipfile.ZipFile(reuse['retainedAPK']) as z:
 for rel,w in M['nativeLibraries'].items():assert ident(z.read(rel))==w==reuse['nativeLibraries'][rel]
external={}
for rel,h in M['nativeReuse']['nativeSourceFiles'].items():
 p=ROOT/rel;assert fid(p)['sha256']==h;external[str(p)]=fid(p)
for path,w in M['nativeReuse']['toolsChecked'].items():
 p=pathlib.Path(path);assert fid(p)['sha256']==w['sha256'] and str(p.resolve())==w['realPath'];external[path]=fid(p)
for path,w in M['tools'].items():
 p=pathlib.Path(path);assert fid(p)['sha256']==w['sha256'] and str(p.resolve())==w['realPath'];external[path]=fid(p)
for rel,w in M['sourceInputs'].items():external[str(ROOT/rel)]=fid(ROOT/rel)
for p in prov['priorEvidence']:external[p]=fid(p)
accept=j(B/'accepted-bindings/pair8-acceptance.json');assert fid(accept['actualReceipt']['path'])['sha256']==accept['actualReceipt']['sha256']
R['checks']['provenance']={'nativeSourceFiles':len(M['nativeReuse']['nativeSourceFiles']),'nativeReuseTools':len(M['nativeReuse']['toolsChecked']),'compilerTools':len(M['tools']),'priorEvidenceFiles':len(prov['priorEvidence']),'pair8ReceiptHashBound':True}
(OUT/'external-before.json').write_text(json.dumps(external,indent=2)+'\n')
R['finishedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();R['status']='PASS'
(OUT/'independent-checks.json').write_text(json.dumps(R,indent=2)+'\n')
print(json.dumps(R,indent=2))
