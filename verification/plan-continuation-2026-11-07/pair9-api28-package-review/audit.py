#!/usr/bin/env python3
"""Bounded data-only independent audit. Never import or execute candidate code.

Run: python3 -B verification/plan-continuation-2026-11-07/pair9-api28-package-review/audit.py
Writes only alongside this script. No subprocesses, process probes, network or
recursive reads outside the explicitly selected packaging namespace.
"""
from pathlib import Path
import datetime, difflib, hashlib, json, struct, sys, time, zipfile, zlib
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BASE = OUT.parent
B = BASE / 'pair9-api28-packaging'
START = time.monotonic()
FILES = {}
CHECKS = []
FACTS = {}

def check(ok, label):
    CHECKS.append({'check': label, 'passed': bool(ok)})
    if not ok:
        raise ValueError(label)

def bound():
    if time.monotonic() - START > 640:
        raise TimeoutError('640-second audit bound')

def ident_bytes(b):
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def ident(p):
    bound()
    p = Path(p)
    h = hashlib.sha256()
    size = 0
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            bound(); h.update(chunk); size += len(chunk)
    return {'bytes': size, 'sha256': h.hexdigest()}

def remember(p):
    p = str(Path(p).absolute())
    value = ident(p)
    if p in FILES:
        check(FILES[p] == value, 'Repeated read stable: ' + p)
    FILES[p] = value
    return value

def expect(p, w):
    check(remember(p) == {k: w[k] for k in ('bytes', 'sha256')}, 'File binding: ' + str(p))

def readj(p):
    remember(p)
    return json.loads(Path(p).read_text())

def projection(files):
    return hashlib.sha256(''.join(k+'\0'+v['sha256']+'\n' for k,v in sorted(files.items())).encode()).hexdigest()

def u(b, p):
    return struct.unpack_from('<I', b, p)[0]

def lp(b, p=0):
    n = u(b,p)
    assert p+4+n <= len(b)
    return b[p+4:p+4+n], p+4+n

def seq(b):
    p=0
    while p<len(b):
        v,p=lp(b,p); yield v
    assert p==len(b)

def dex(b):
    # Independent class_def reader, adapted from the previous binary-review pattern.
    if len(b)<112 or b[:8]!=b'dex\n039\0' or u(b,32)!=len(b) or u(b,36)!=112 or u(b,40)!=0x12345678:
        raise ValueError('invalid DEX header')
    if hashlib.sha1(b[32:]).digest()!=b[12:32]:
        raise ValueError('DEX SHA1 mismatch')
    if zlib.adler32(b[12:])&0xffffffff != u(b,8):
        raise ValueError('DEX Adler32 mismatch')
    sn,so,tn,to=struct.unpack_from('<4I',b,56);cn,co=struct.unpack_from('<2I',b,96)
    for n,o,w in [(sn,so,4),(tn,to,4),(cn,co,32)]:
        assert o%4==0 and 0<=o<=len(b) and n<=(len(b)-o)//w
    strings=[]
    for i in range(sn):
        p=u(b,so+4*i)
        for _ in range(5):
            v=b[p];p+=1
            if v<128: break
        else: raise ValueError('invalid DEX string length')
        strings.append(b[p:b.index(0,p)].decode('utf-8',errors='replace'))
    types=[strings[u(b,to+4*i)] for i in range(tn)]
    defs=[types[u(b,co+32*i)] for i in range(cn)]
    assert len(defs)==len(set(defs)) and all(d.startswith('L') and d.endswith(';') for d in defs)
    return set(defs)

def classfile(b):
    assert b[:4]==bytes.fromhex('cafebabe') and struct.unpack_from('>HH',b,4)==(0,61)
    n=struct.unpack_from('>H',b,8)[0];cp={};p=10;i=1;members=0
    while i<n:
        tag=b[p];p+=1
        if tag==1:
            length=struct.unpack_from('>H',b,p)[0];p+=2
            cp[i]=b[p:p+length].decode('utf8');p+=length
        elif tag==7: cp[i]=struct.unpack_from('>H',b,p)[0];p+=2
        elif tag in (3,4,9,10,11,12,17,18):
            p+=4;members+=int(tag in (9,10,11))
        elif tag in (5,6): p+=8;i+=1
        elif tag in (8,16,19,20): p+=2
        elif tag==15: p+=3
        else: raise ValueError('unknown classfile constant tag')
        i+=1
    return 'L'+cp[cp[struct.unpack_from('>H',b,p+2)[0]]]+';',members

def manifest(b):
    assert struct.unpack_from('<HHI',b,0)==(3,8,len(b))
    strings=[];nodes=[];p=8
    while p<len(b):
        kind,hs,size=struct.unpack_from('<HHI',b,p);assert size>=hs and p+size<=len(b)
        if kind==1:
            count,styles,flags,start,sty=struct.unpack_from('<5I',b,p+8)
            def length(pos,utf8):
                if utf8:
                    v=b[pos];return (((v&127)<<8)|b[pos+1],pos+2) if v&128 else (v,pos+1)
                v=struct.unpack_from('<H',b,pos)[0]
                return (((v&32767)<<16)|struct.unpack_from('<H',b,pos+2)[0],pos+4) if v&32768 else (v,pos+2)
            for i in range(count):
                at=p+start+u(b,p+hs+4*i);n,at=length(at,bool(flags&256))
                if flags&256:n,at=length(at,True);strings.append(b[at:at+n].decode('utf8'))
                else:strings.append(b[at:at+2*n].decode('utf-16le'))
        elif kind==0x102:
            name=strings[u(b,p+20)];ast,asz,ac=struct.unpack_from('<3H',b,p+24);attrs={}
            for i in range(ac):
                at=p+16+ast+asz*i;ns,ni,raw=struct.unpack_from('<3I',b,at);typ=b[at+15];val=u(b,at+16)
                assert strings[ni] not in attrs
                attrs[strings[ni]]=strings[val] if typ==3 else (bool(val) if typ==18 else val)
            nodes.append({'tag':name,'attrs':attrs})
        p+=size
    assert p==len(b)
    return nodes

def signature(apk):
    eocd=apk.rfind(b'PK\x05\x06');assert eocd+22+struct.unpack_from('<H',apk,eocd+20)[0]==len(apk)
    cd=u(apk,eocd+16);assert apk[cd-16:cd]==b'APK Sig Block 42'
    size=struct.unpack_from('<Q',apk,cd-24)[0];start=cd-size-8
    assert struct.unpack_from('<Q',apk,start)[0]==size
    p=start+8;blocks={}
    while p<cd-24:
        n=struct.unpack_from('<Q',apk,p)[0];p+=8;kind=u(apk,p)
        assert kind not in blocks;blocks[kind]=apk[p+4:p+n];p+=n
    assert p==cd-24
    signers,end=lp(blocks[0xf05368c0]);assert end==len(blocks[0xf05368c0])
    items=list(seq(signers));assert len(items)==1
    s=items[0];signed,p=lp(s);lo,hi=struct.unpack_from('<II',s,p);p+=8
    sigs,p=lp(s,p);pub,p=lp(s,p);assert p==len(s) and lo<=28<=hi
    digests,p=lp(signed);certs,p=lp(signed,p);assert struct.unpack_from('<II',signed,p)==(lo,hi)
    attrs,end=lp(signed,p+8);assert end==len(signed)
    certificates=list(seq(certs));assert len(certificates)==1;cert=certificates[0]
    signatures=list(seq(sigs));assert len(signatures)==1
    algorithm=u(signatures[0],0);sig,end=lp(signatures[0],4);assert end==len(signatures[0]) and algorithm==0x103
    def der(b,p=0):
        begin=p;tag=b[p];n=b[p+1];q=p+2
        if n&128:k=n&127;n=int.from_bytes(b[q:q+k],'big');q+=k
        assert q+n<=len(b)
        return tag,b[q:q+n],q+n,b[begin:q+n]
    def children(b):
        p=0;out=[]
        while p<len(b):
            tag,val,p,raw=der(b,p);out.append((tag,val,raw))
        return out
    _,spki,_,_=der(pub);pubitems=children(spki);assert pubitems[1][0]==3 and pubitems[1][1][0]==0
    _,key,_,_=der(pubitems[1][1][1:]);keys=children(key)
    modulus=int.from_bytes(keys[0][1],'big');exponent=int.from_bytes(keys[1][1],'big')
    assert modulus.bit_length()==2048
    encoded=pow(int.from_bytes(sig,'big'),exponent,modulus).to_bytes(256,'big')
    di=bytes.fromhex('3031300d060960864801650304020105000420')+hashlib.sha256(signed).digest()
    assert encoded==b'\0\x01'+b'\xff'*(len(encoded)-len(di)-3)+b'\0'+di
    _,certificate,_,_=der(cert);certitems=children(certificate);tbs=children(certitems[0][1])
    spkiindex=6 if tbs[0][0]==0xa0 else 5
    assert tbs[spkiindex][2]==pub
    patched=bytearray(apk[eocd:]);struct.pack_into('<I',patched,16,start);chunks=[]
    for section in [apk[:start],apk[cd:eocd],patched]:
        for off in range(0,len(section),1048576):
            chunk=section[off:off+1048576]
            chunks.append(hashlib.sha256(b'\xa5'+struct.pack('<I',len(chunk))+chunk).digest())
    computed=hashlib.sha256(b'\x5a'+struct.pack('<I',len(chunks))+b''.join(chunks)).digest()
    ds=list(seq(digests));assert len(ds)==1 and u(ds[0],0)==algorithm
    wanted,end=lp(ds[0],4);assert end==len(ds[0]) and computed==wanted
    return {'scheme':'v3','RSA2048SHA256':True,'contentDigestSHA256':computed.hex(),
            'certificateSHA256':hashlib.sha256(cert).hexdigest(),'publicKeySHA256':hashlib.sha256(pub).hexdigest(),
            'signerSDKRange':[lo,hi],'certificateSPKIMatchesSigner':True}

def payload(product,test,native,z):
    def require(ok,message):
        if not ok:raise ValueError(message)
    names=z.namelist();require(len(names)==len(set(names)),'duplicate ZIP member')
    require({n for n in names if n.endswith('.dex')}=={'classes.dex','classes2.dex'},'unexpected DEX inventory')
    ap=z.read('classes.dex');at=z.read('classes2.dex')
    require(ident_bytes(ap)==ident_bytes(product),'product DEX binding mismatch')
    pd,td=dex(ap),dex(at)
    require(not pd&td,'overlapping defined classes: '+repr(sorted(pd&td)))
    require(at==test,'test DEX binding mismatch')
    require(len(pd)==389 and len(td)==12,'DEX count mismatch')
    require(all(n.startswith('Ldev/mixer/android/NativeLowerApiCompatibility') for n in td),'unexpected harness owner')
    require({n for n in names if n.startswith('lib/')}==set(native),'native inventory mismatch')
    for name,w in native.items():require(ident_bytes(z.read(name))==w,'native library binding mismatch: '+name)
    return pd,td

def audit():
    m=readj(B/'frozen-ready-input-manifest.json');initial=readj(B/'initial-frozen-ready-input-manifest.json')
    prepared=readj(B/'attempt-1/prepared.json');packet=readj(B/'runtime-packet.json');summary=readj(B/'result.json')
    # Hash actual files, not merely manifest assertions; no APK/evidence copying.
    inventory={str(p.relative_to(B)):remember(p) for p in sorted(B.rglob('*')) if p.is_file()}
    for rel,w in m['retainedFiles'].items():check(inventory[rel]==w,'Retained: '+rel)
    check(len(m['retainedFiles'])==334,'334 retained bindings')
    for rel,w in m['sourceInputs'].items():expect(ROOT/rel,w)
    for p,w in m['externalBindings'].items():expect(p,w)
    for p,w in m['tools'].items():
        expect(p,w);check(str(Path(p).resolve())==w['realPath'],'Tool realpath: '+p)
    image=Path(m['installedImage']['path'])
    for rel,w in m['installedImage']['files'].items():expect(image/rel,w)
    install=readj(BASE/'android-api28-image-install/receipt.json')
    check(m['installedImage']['files']==install['installedFiles']==packet['image']['files'],'15 image file maps equal')
    check(len(packet['image']['files'])==15 and packet['image']['packageXMLRevision']==2 and packet['image']['sourcePropertiesRevision']==1,'Image discrepancy preserved')
    imagexml=ET.fromstring((image/'package.xml').read_bytes())
    package=[e for e in imagexml.iter() if e.tag.rsplit('}',1)[-1]=='localPackage']
    check(len(package)==1 and package[0].attrib['path']=='system-images;android-28;default;arm64-v8a','Actual image XML package identity')
    revision=[e for e in package[0] if e.tag.rsplit('}',1)[-1]=='revision'][0]
    major=[e.text for e in revision if e.tag.rsplit('}',1)[-1]=='major']
    props=dict(line.split('=',1) for line in (image/'source.properties').read_text().splitlines() if '=' in line)
    check(major==['2'] and props['Pkg.Revision']=='1' and props['AndroidVersion.ApiLevel']=='28' and props['SystemImage.Abi']=='arm64-v8a','Actual raw image revision discrepancy and declared API/ABI')
    for p,w in install['protectedTools'].items():expect(p,w)
    FACTS['installedImage']={'files':15,'bytes':sum(w['bytes'] for w in packet['image']['files'].values()),'discrepancy':packet['image']['metadataDiscrepancy']}
    raw=Path('/tmp/mixer-20261107-generated-java-pair9-r2-01');rr=readj(raw/'receipt.json')
    local=readj(BASE/'generated-java-pair9-r2-actual-review/result.json')
    hosted=readj(BASE/'pair9-generated-hosted-review/result.json')
    check(local['verdict']==hosted['verdict']=='ACCEPT','Exact local and hosted evidence independently accepted')
    check(m['sourceRevision']==hosted['reviewed_revision']=='96f03ab65966a6374e958e780fa09a3eed814c0b' and m['sourceTree']==hosted['reviewed_git_tree']=='6dacea5d2f5cd55d6934142cce556a4bd0fcd1c0','Exact current revision and tree match hosted accepted source')
    check(len(rr['source_inputs'])==101 and projection(rr['source_inputs'])==m['sourceDigest101']==hosted['source_digest']==local['candidate']['sourceInputsSHA256'],'Exact source101 digest')
    check(all(m['sourceInputs'][p]==w for p,w in rr['source_inputs'].items()),'All101 remain guarded')
    check(local['candidate']['sdkFileCount']==22 and local['candidate']['adapterFileCount']==24 and local['candidate']['adapterSHA256']==hosted['adapter']['sha256']==m['adapter24Digest'],'SDK22 and adapter24')
    policy=(ROOT/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
    profile=json.loads(policy.split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
    check(profile['id']=='mixer.android-source-pair.9','Actual profile pair9 identity')
    for kind,count in [('sdk',22),('adapter',24)]:
        check(len(profile[kind+'_files'])==count and projection(profile[kind+'_files'])==profile[kind+'_compatibility_sha256'],'Actual profile projection: '+kind)
        for rel,w in profile[kind+'_files'].items():
            source=ROOT/('sdk' if kind=='sdk' else 'native/android')
            if kind=='adapter' and rel.startswith('Sources/'):source=source/'engine'
            expect(source/rel,w)
    check(profile['sdk_compatibility_sha256']==local['candidate']['sdkSHA256'] and profile['adapter_compatibility_sha256']==m['adapter24Digest'],'Profile equals accepted SDK22/adapter24 digests')
    FACTS['profile']={'id':profile['id'],'sdk22SHA256':profile['sdk_compatibility_sha256'],'adapter24SHA256':profile['adapter_compatibility_sha256']}
    expect(raw/'receipt.json',local['evidence']['rawReceipt'])
    cr=readj(raw/'debug-original/receipt.json')
    check(cr['classes']==m['productClassfiles'] and projection(cr['classes'])==local['evidence']['classInventorySHA256']==hosted['class_inventory_sha256'],'216 local/hosted binary class identities')
    check(cr['dex']==hosted['dex']==local['evidence']['dex'],'Identical hosted/local DEX')
    for consumer in rr['consumers']:
        r=readj(raw/consumer/'receipt.json');check(r['classes']==cr['classes'] and r['dex']==cr['dex'],'Six consumer inventories: '+consumer)
        expect(raw/consumer/'dex/classes.dex',cr['dex']['classes.dex'])
    hostedraw=BASE/'ci96-generated-java-actual/artifact/integration'
    for consumer in rr['consumers']:
        hr=readj(hostedraw/consumer/'receipt.json')
        check(hr['classes']==cr['classes'] and hr['dex']==cr['dex'],'Actual hosted class/DEX inventories: '+consumer)
        expect(hostedraw/consumer/'dex/classes.dex',cr['dex']['classes.dex'])
        for rel,w in cr['classes'].items():expect(hostedraw/consumer/'classes'/rel,w)
    FACTS['hostedComparison']={'consumers':6,'actualClassfilesHashed':1296,'DEXFilesHashed':6,'sourceRevision':hosted['reviewed_revision'],'runSnapshot':hosted['run'],'liveNetworkRefresh':False}
    product=(B/m['productDEX']['relativePath']).read_bytes();test=(B/m['testDEX']['relativePath']).read_bytes()
    members=0;classes=set()
    for rel,w in m['productClassfiles'].items():
        expect(B/'attempt-1/product-classfiles'/rel,w)
        name,n=classfile((B/'attempt-1/product-classfiles'/rel).read_bytes());members+=n;classes.add(name)
        check(name=='L'+rel.removesuffix('.class')+';','Class descriptor: '+rel)
    check(len(classes)==216 and members==4976 and classes<=dex(product),'All216 Java17 classes and4976 binary member references')
    with zipfile.ZipFile(B/'attempt-1/work/product-classpath.jar') as z:
        check(len(z.namelist())==216 and set(z.namelist())==set(m['productClassfiles']),'Classpath complete inventory')
        for rel,w in m['productClassfiles'].items():check(ident_bytes(z.read(rel))==w,'Classpath member: '+rel)
    for rel,w in prepared['harnessClassfiles'].items():
        expect(B/'attempt-1/harness-classfiles'/rel,w);classfile((B/'attempt-1/harness-classfiles'/rel).read_bytes())
    apkpath=B/m['apk']['relativePath'];expect(apkpath,packet['apk']);check(packet['apk']==summary['apk'],'Summary APK matches packet')
    apk=apkpath.read_bytes()
    with zipfile.ZipFile(apkpath) as z:
        pd,td=payload(product,test,m['nativeLibraries'],z);nodes=manifest(z.read('AndroidManifest.xml'))
        by={n['tag']:n['attrs'] for n in nodes};activities=[n['attrs'] for n in nodes if n['tag']=='activity']
        check(by['manifest']['package']==by['instrumentation']['targetPackage']==packet['package'],'Binary package/instrumentation target')
        check(by['instrumentation']['name']==packet['instrumentation'],'Binary instrumentation class')
        check(by['uses-sdk']['minSdkVersion']==by['uses-sdk']['targetSdkVersion']==28 and by['manifest']['compileSdkVersion']==37,'Binary API28/SDK37')
        check({a['name'] for a in activities}=={'dev.mixer.android.MixerActivity','dev.mixer.android.NativeLowerApiCompatibilityActivity'} and all(a['exported'] is False for a in activities),'Real non-exported activities')
        check(all('L'+a['name'].replace('.','/')+';' in pd|td for a in activities),'Activity definitions exist')
        check(all(by['application'][k] for k in ['extractNativeLibs','hasCode','debuggable']),'Binary application flags')
        for info in z.infolist():
            if info.filename.startswith('lib/'):
                nl,xl=struct.unpack_from('<HH',apk,info.header_offset+26)
                check(info.compress_type==0 and (info.header_offset+30+nl+xl)%16384==0,'Stored16KiB native alignment: '+info.filename)
    FACTS['binaryManifest']=nodes;FACTS['apk']=ident_bytes(apk);FACTS['signature']=signature(apk)
    check(FACTS['signature']['certificateSHA256']=='aa75cc8d620f67e2e137318ec7e995f0dd4eb364b3d3aec1c3d8aa5c69226371','Current certificate equals retained SDK signature receipt')
    check(FACTS['signature']['certificateSHA256'] in prepared['signatureVerification'],'SDK corroborates actual signature')
    FACTS['DEX']={'product':ident_bytes(product),'harness':ident_bytes(test),'productDefinitions':len(pd),'harnessDefinitions':len(td),'intersection':sorted(pd&td),'classes':len(classes),'memberReferences':members}
    controls=readj(B/'controls/result.json');outcomes={}
    for name,c in controls['controls'].items():
        expect(c['path'],c)
        try:
            with zipfile.ZipFile(c['path']) as z:payload(product,test,m['nativeLibraries'],z)
        except ValueError as e:
            outcomes[name]=str(e);check(str(e)==c['observedRefusal'] and str(e).startswith(c['expectedRefusal']),'Independent refusal: '+name)
        else:raise ValueError('Accepted tamper: '+name)
    check(len(outcomes)==6,'All six independent actual-archive tamper refusals');FACTS['controls']=outcomes
    reuse=prepared['nativeReuse'];lock=readj(BASE/'android-runtime/source-lock.json')
    historical=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-5c87cbc0/verification/plan-continuation-2026-11-07/android-toggle-oracle/native-reuse.json')
    motionpath=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-0f4ec327/verification/plan-continuation-2026-11-07/android-motion-r2-native-runtime/native-reuse.json')
    hist=readj(historical);motion=readj(motionpath)
    check(remember(BASE/'android-runtime/source-lock.json')['sha256']==hist['sourceLockSHA256'] and remember(BASE/'android-runtime/build-receipt.json')['sha256']==hist['buildReceiptSHA256'],'Original source lock and build receipt proof chain')
    check(remember(historical)==reuse['historicalProof']=={k:motion['historicalProof'][k] for k in ['bytes','sha256']} and remember(motionpath)==reuse['motionProof'],'Historical/motion proof identities')
    check(hist['matchingTools']==reuse['tools']==motion['currentToolsEqualOriginalBuildTools'],'Native reuse tool proof maps agree')
    check(hist['nativeLibraries']==motion['nativeLibraries']==reuse['libraries']==m['nativeLibraries'],'Native reuse library proof maps agree')
    for rel,sha in reuse['nativeSourceFiles'].items():
        check(remember(ROOT/rel)['sha256']==sha==lock['files'][rel],'Native source: '+rel)
    for p,w in reuse['tools'].items():
        expect(p,w);check(str(Path(p).resolve())==w['realPath'],'Native tool realpath: '+p)
    check(len(reuse['nativeSourceFiles'])==57 and len(reuse['tools'])==33,'Native57/tool33 bindings')
    expect(reuse['originalAPK']['path'],reuse['originalAPK'])
    with zipfile.ZipFile(reuse['originalAPK']['path']) as z:
        for name,w in m['nativeLibraries'].items():check(ident_bytes(z.read(name))==w,'Original native library: '+name)
    old=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-53f259fe/verification/plan-continuation-2026-11-07/android-api28-packaging-fix')
    prior=readj(old/'compile-2/prepared.json')
    for rel,w in prior['sourceInputs'].items():
        expect(ROOT/rel,w);expect(B/'attempt-1/inputs'/rel,w);expect(old/'compile-2/inputs'/rel,w)
    check(len(prior['sourceInputs'])==3 and prior['sourceInputs']==prepared['sourceInputs'],'Three harness files exactly previous accepted package')
    removed=set(initial['sourceInputs'])-set(m['sourceInputs'])
    check(removed=={'AGENTS.md','PLAN.md','STATUS.md','work-graph.json','mixer-product-plan.md','THIRD_PARTY.yml'},'Only six non-owning metadata observations excluded')
    check(not set(m['sourceInputs'])-set(initial['sourceInputs']) and all(v==initial['sourceInputs'][k] for k,v in m['sourceInputs'].items()),'No owning source guard changed')
    for key in ['externalBindings','tools','productClassfiles','nativeLibraries','installedImage','apk','productDEX','testDEX']:
        check(m[key]==initial[key],'Unchanged manifest guard: '+key)
    check(m['observedMetadataPreflight']=={k:initial['sourceInputs'][k] for k in removed},'Excluded observations preserved')
    # Reconstruct exactly the pre-drift AGENTS bytes by removing only the newly added hold.
    live=(ROOT/'AGENTS.md').read_text();remember(ROOT/'AGENTS.md')
    addition="The Android controller host controls also left PGIDs 40708, 40709, and 40711\nwith unresolved custody. Preserve both retained scratch directories; do not\nprobe, signal, or retry these groups. The receipt is\nverification/plan-continuation-2026-11-07/android-controller-custody-holds/receipt.json.\n"
    check(live.count(addition)==1,'Live AGENTS explicitly preserves three new holds')
    before=live.replace(addition,'');drift=readj(B/'shared-metadata-drift.json')['changes']['AGENTS.md']
    check(ident_bytes(before.encode())==drift['before'] and ident_bytes(live.encode())==drift['after'],'Exact AGENTS drift contains only added custody hold')
    (OUT/'policy-drift.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),live.splitlines(True),fromfile='AGENTS.before',tofile='AGENTS.current')))
    metadata_current={rel:remember(ROOT/rel) for rel in removed-{'AGENTS.md'}}
    # These are concurrent parent-owned observations, not executable inputs.
    # Product scope/dependency declarations are stable; execution/status records
    # may advance while this read-only review is in progress.
    for rel in ['mixer-product-plan.md','THIRD_PARTY.yml']:
        check(metadata_current[rel]==initial['sourceInputs'][rel],'Scope/dependency metadata unchanged: '+rel)
    check('23663' in live and 'All earlier process and custody holds remain in force.' in live and 'Keep native' in live,'Prior holds and explicit native resumption remain')
    hold=readj(BASE/'android-controller-custody-holds/receipt.json')
    check(hold['groups']==[40708,40709,40711] and hold['probeSignalRetryAllowed'] is False,'New holds remain HELD_UNKNOWN')
    FACTS['metadata']={'removedObservations':sorted(removed),'owningBindings':len(m['sourceInputs']),'drift':drift,'newHeldGroups':hold['groups'],'currentOtherMetadata':metadata_current,'concurrentParentMetadataChanges':[rel for rel,v in metadata_current.items() if v!=initial['sourceInputs'][rel]]}
    holds={23663,20745,20770,20780,20817,20842,20851,20866,2424,40708,40709,40711}
    allcommands=[]
    for rel,n,want in [('attempt-1/commands/commands.json',20,0),('final-check-commands/commands.json',1,1),('final-check-commands-r2/commands.json',1,0),('final-check-commands-r3/commands.json',1,0)]:
        cs=readj(B/rel);check(len(cs)==n,'Command count: '+rel)
        for c in cs:
            check(all(c[k] for k in ['terminal_custody','direct_child_reaped','stdout_eof','stderr_eof','owned_group_absent']) and not c['cleanup_errors'],'Separate custody fields: '+c['label'])
            check(c['exit_code']==want and c['stop'] is None and c['owned_pgid']==c['pid'] and c['owned_pgid'] not in holds,'Exit and owned group: '+c['label'])
            check(c['group_observation']['outcome']=='absent' and c['signal']['outcome']=='already-absent','Positive historical absence: '+c['label'])
            for log in c['logs'].values():expect(log['path'],log)
        allcommands.extend(cs)
    check(prepared['commands']==allcommands[:20],'Prepared commands exact ledger')
    cs={c['label']:c for c in allcommands[:20]}
    for label,key in [('source-head','sourceRevision'),('source-tree','sourceTree')]:
        check(Path(cs[label]['logs']['stdout']['path']).read_text().strip()==m[key],'Recorded Git command equals exact binding: '+label)
    compileargv=cs['harness-javac']['argv'];d8argv=cs['harness-only-d8']['argv']
    check(compileargv[1:7]==['--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath'] and compileargv[7]==str(B/'attempt-1/work/empty'),'Exact strict Java17 harness flags and empty sourcepath')
    check(compileargv[-2:]==[str(B/'attempt-1/inputs'/rel) for rel in sorted(prepared['sourceInputs']) if rel.endswith('.java')],'Only the two canonical harness source inputs compiled')
    check(d8argv[1:9]==['--min-api','28','--lib','/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar','--classpath',str(B/'attempt-1/work/product-classpath.jar'),'--output',str(B/'attempt-1/work/dex')],'Exact D8 API28/SDK37 classpath flags')
    check(d8argv[9:]==[str(B/'attempt-1/work/test-classes'/rel) for rel in sorted(prepared['harnessClassfiles'])],'D8 program inputs are only all12 harness classfiles')
    check(all(c['stream_output_limits']=={'stdout':4194304,'stderr':4194304} and c['total_output_limit']==67108864 for c in allcommands),'All23 commands retain finite output bounds')
    check(sum(log['bytes'] for c in allcommands for log in c['logs'].values())==summary['aggregateOutputBytes'],'Exact aggregate output accounting')
    check('AssertionError: AGENTS.md' in (B/'final-check-commands/000-read-only-verify-ready.stderr').read_text(),'Original verifier refusal retained')
    # Compare source bytes, not execute this custody controller.
    check((B/'sources/canonical_commands.py').read_bytes()==(ROOT/'scripts/ci/check-android-generated-java.py').read_bytes(),'Frozen canonical controller exactly current owning runner')
    check(not (B/'attempt-1/work/private.keystore').exists() and (B/'attempt-1/work').stat().st_mode&0o777==0o700,'Private key absent and scratch0700')
    check(prepared['cleanup']==packet['cleanup']==m['cleanup'] and prepared['cleanup']['privateSigningKeyRemovedAfterTerminalCustody'],'Recorded key removal only after terminal custody')
    FACTS['custody']={'commands':len(allcommands),'packaging':20,'finalVerifiers':3,'expectedFailures':1,'heldGroupsNotOwned':sorted(holds),'privateKeyAbsent':True,'historicalReceiptsOnly':True}
    for name,args in packet['prospectiveCommands'].items():
        check(args[0]=='/opt/homebrew/share/android-commandlinetools/platform-tools/adb' and args[1]=='-P' and args[3]=='-s','Private ADB port and exact serial slots: '+name)
        check(args[2].startswith('<') and args[4].startswith('<'),'Unassigned root-owned slots: '+name)
    check(packet['prospectiveCommands']['install'][5:]==['install',str(apkpath)],'Exact prospective APK install')
    check(packet['prospectiveCommands']['instrument'][5:]==['shell','am','instrument','-w','-r',packet['package']+'/'+packet['instrumentation']],'Exact prospective instrumentation')
    check(packet['expectedRuntime']=={'api':28,'abi':'arm64-v8a','notObserved':True},'Runtime remains unobserved')
    check(packet['physicalPhones']=='DISCONNECTED' and packet['image']['runtimeAPIAndABI']=='UNRUN','Phones and runtime gates remain pending')
    FACTS['runtimePacket']={'commands':packet['prospectiveCommands'],'allocated':False,'controllerAccepted':False,'runtimeAccepted':False}
    harness=(ROOT/'native/android/tests/NativeLowerApiCompatibilityInstrumentation.java').read_text()
    check(all(stage in harness for stage in packet['instrumentationStageLiterals']),'Packet stage literals match unchanged actual harness')
    FACTS['runtimePacket']['historicalPair8ResultLabelsRemain']=True
    FACTS['toolsRecordedVersions']=prepared['toolVersions']
    FACTS['source']={k:m[k] for k in ['sourceRevision','sourceTree','sourceDigest101','adapter24Digest']}
    FACTS['candidateInventory']={'files':len(inventory),'bytes':sum(v['bytes'] for v in inventory.values()),'manifestBound':334,'projectionSHA256':projection(inventory)}
    # Postflight rereads the whole finite selected set; never traverse any held scratch.
    for p,w in list(FILES.items()):check(ident(p)==w,'Postflight stable: '+p)
    check({str(p.relative_to(B)) for p in B.rglob('*') if p.is_file()}==set(inventory),'Candidate file set stable')
    (OUT/'file-bindings.json').write_text(json.dumps(FILES,indent=2,sort_keys=True)+'\n')

report={'schema':1,'reviewer':'Independent pair9 API28 package review sub-agent','scope':'Exact artifact and prospective packet only','startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':'python3 -B '+str(Path(__file__).resolve()),'python':sys.version,'productCodeExecuted':False,'processProbesOrSignals':0,'network':0,'children':0,'nativeCompilerJVMDeviceUI':0,'commits':0,'pushes':0,'writesOnly':str(OUT)}
try:
    audit();report['verdict']='ACCEPT';report['blockingFindings']=[]
except Exception as e:
    import traceback
    report['verdict']='REQUEST_CHANGES';report['error']=repr(e);report['traceback']=traceback.format_exc()
finally:
    report.update(finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsedSeconds=round(time.monotonic()-START,3),checks=CHECKS,facts=FACTS,filesRead=len(FILES),auditScript=ident(Path(__file__)))
    (OUT/'audit.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k] for k in ['verdict','elapsedSeconds','filesRead']}|{'checks':len(CHECKS),'error':report.get('error')},indent=2))
