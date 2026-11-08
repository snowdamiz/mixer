#!/usr/bin/env python3
"""Read-only package controls. No subprocesses, imports of build drivers, or device access."""
import contextlib
import datetime
import hashlib
import io
import json
from pathlib import Path
import runpy
import struct
import sys
import time
import traceback
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
B = HERE.parent / 'api32-33-motion-package'
START = time.monotonic()
R = {'status': 'RUNNING', 'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
     'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'python': sys.version,
     'childProcessesCreated': 0, 'runtimeAttempts': 0, 'deviceQueries': 0, 'networkCalls': 0,
     'writesRestrictedTo': str(HERE), 'checks': {}}

def need(ok, label):
    if not ok:
        raise ValueError(label)
    if time.monotonic() - START > 120:
        raise TimeoutError('120-second artifact control bound')

def sha(b):
    return hashlib.sha256(b).hexdigest()

def ident(p):
    p = Path(p)
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return {'bytes': p.stat().st_size, 'sha256': h.hexdigest()}

def load(p):
    return json.loads(Path(p).read_text())

def digest(files):
    return sha(''.join(k+'\0'+v['sha256']+'\n' for k,v in sorted(files.items())).encode())

def lp(b, p=0):
    need(p+4 <= len(b), 'truncated length')
    n = struct.unpack_from('<I', b, p)[0]
    need(p+4+n <= len(b), 'truncated payload')
    return b[p+4:p+4+n], p+4+n

def seq(b):
    p = 0
    while p < len(b):
        value, p = lp(b, p)
        yield value
    need(p == len(b), 'sequence end')

def der(b, p=0):
    start = p
    tag, n = b[p:p+2]; p += 2
    if n & 128:
        size = n & 127
        need(0 < size <= 4, 'DER length width')
        n = int.from_bytes(b[p:p+size], 'big'); p += size
    need(p+n <= len(b), 'DER truncated')
    return tag, b[p:p+n], p+n, b[start:p+n]

def der_children(b):
    p = 0; out = []
    while p < len(b):
        tag, value, p, full = der(b,p); out.append((tag,value,full))
    return out

def signature(apk):
    eocd = apk.rfind(b'PK\x05\x06', max(0,len(apk)-65557))
    need(eocd >= 0 and eocd+22+struct.unpack_from('<H',apk,eocd+20)[0] == len(apk), 'EOCD')
    cd = struct.unpack_from('<I',apk,eocd+16)[0]
    need(cd+struct.unpack_from('<I',apk,eocd+12)[0] == eocd, 'central directory length')
    need(apk[cd-16:cd] == b'APK Sig Block 42', 'APK signing magic')
    size = struct.unpack_from('<Q',apk,cd-24)[0]; start = cd-size-8
    need(start >= 0 and struct.unpack_from('<Q',apk,start)[0] == size, 'signing block sizes')
    p = start+8; pairs = {}
    while p < cd-24:
        n = struct.unpack_from('<Q',apk,p)[0]; p += 8
        need(n >= 4 and p+n <= cd-24, 'signing entry bounds')
        kind = struct.unpack_from('<I',apk,p)[0]
        need(kind not in pairs, 'duplicate signing entry')
        pairs[kind] = apk[p+4:p+n]; p += n
    need(p == cd-24 and 0xf05368c0 in pairs, 'v3 present')
    signers_blob, end = lp(pairs[0xf05368c0])
    need(end == len(pairs[0xf05368c0]), 'v3 envelope')
    signers = list(seq(signers_blob)); need(len(signers)==1, 'one v3 signer')
    signer = signers[0]; signed,p = lp(signer)
    min_sdk,max_sdk = struct.unpack_from('<II',signer,p); p += 8
    signatures,p = lp(signer,p); spki,p = lp(signer,p)
    need(p==len(signer) and min_sdk<=32<=33<=max_sdk, 'signer API coverage')
    digests,q = lp(signed); certs,q = lp(signed,q)
    inner_min,inner_max = struct.unpack_from('<II',signed,q); q += 8
    attrs,q = lp(signed,q)
    need(q==len(signed) and (inner_min,inner_max)==(min_sdk,max_sdk), 'signed SDK binding')
    cert_list = list(seq(certs)); need(len(cert_list)==1, 'one certificate')
    cert = cert_list[0]
    need(sha(cert)=='affc7b3a7651ee3014580c9a75f3621ec4afa7dbf8ed2032820d05d53595271f', 'certificate hash')
    outer = der_children(der(cert)[1]); tbs = der_children(outer[0][1])
    spki_index = 6 if tbs[0][0]==0xa0 else 5
    need(tbs[spki_index][2]==spki, 'certificate matches signer public key')
    pub = der_children(der(spki)[1])
    need(pub[1][0]==3 and pub[1][1][0]==0, 'public key bit string')
    rsa = der_children(der(pub[1][1][1:])[1])
    n,e = [int.from_bytes(x[1],'big') for x in rsa]
    need(n.bit_length()==2048 and e==65537, 'RSA2048 public key')
    sigs = list(seq(signatures)); ds = list(seq(digests))
    need(len(sigs)==len(ds)==1, 'one signature/digest')
    need(struct.unpack_from('<I',sigs[0])[0]==struct.unpack_from('<I',ds[0])[0]==0x0103, 'RSA PKCS1 SHA256 algorithm')
    sig,end = lp(sigs[0],4); need(end==len(sigs[0]),'signature end')
    digest_bytes,end = lp(ds[0],4); need(end==len(ds[0]),'digest end')
    decoded = pow(int.from_bytes(sig,'big'),e,n).to_bytes(256,'big')
    suffix = bytes.fromhex('3031300d060960864801650304020105000420')+hashlib.sha256(signed).digest()
    need(decoded==b'\0\1'+b'\xff'*(256-len(suffix)-3)+b'\0'+suffix, 'RSA signed-data verification')
    tail = bytearray(apk[eocd:]); struct.pack_into('<I',tail,16,start)
    chunks = []
    for section in (apk[:start],apk[cd:eocd],tail):
        for offset in range(0,len(section),1048576):
            chunk = section[offset:offset+1048576]
            chunks.append(hashlib.sha256(b'\xa5'+struct.pack('<I',len(chunk))+chunk).digest())
    computed = hashlib.sha256(b'\x5a'+struct.pack('<I',len(chunks))+b''.join(chunks)).digest()
    need(computed==digest_bytes,'APK signed content digest')
    return {'scheme':'v3','RSA2048SHA256Verified':True,'contentDigestVerified':True,
            'certificateSHA256':sha(cert),'minSDK':min_sdk,'maxSDK':max_sdk,
            'signingEntryIDs':[hex(x) for x in pairs], 'chunks':len(chunks)}

def class_name(b):
    need(b[:4]==bytes.fromhex('cafebabe') and struct.unpack_from('>H',b,6)[0]==61,'Java17 classfile')
    count = struct.unpack_from('>H',b,8)[0]; p=10; i=1; cp={}
    while i<count:
        tag=b[p]; p+=1
        if tag==1:
            n=struct.unpack_from('>H',b,p)[0]; p+=2; cp[i]=b[p:p+n]; p+=n
        elif tag==7:
            cp[i]=struct.unpack_from('>H',b,p)[0]; p+=2
        elif tag in (3,4,9,10,11,12,17,18): p+=4
        elif tag in (5,6): p+=8; i+=1
        elif tag in (8,16,19,20): p+=2
        elif tag==15: p+=3
        else: raise ValueError('class tag '+str(tag))
        i+=1
    return 'L'+cp[cp[struct.unpack_from('>H',b,p+2)[0]]].decode('ascii')+';'

def main():
    M=load(B/'frozen-ready-input-manifest.json'); F=load(B/'frozen-inputs.json')
    seal=load(B/'delivery-seal.json')
    for rel,w in seal['files'].items():
        need(ident(B/rel)==w,'seal '+rel)
    R['checks']['deliverySeal']={'files':len(seal['files']),'identity':ident(B/'delivery-seal.json')}
    need(ident(B/'cleanup_control.py')['sha256']=='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df','accepted custody controller')
    sys.path.insert(0,str(B))
    from dex_reader import descriptors, official_descriptors
    from payload import validate_payload
    captured=io.StringIO()
    with contextlib.redirect_stdout(captured):
        runpy.run_path(str(B/'verify_ready.py'),run_name='__main__')
    (HERE/'producer-verifier-output.json').write_text(captured.getvalue())
    R['checks']['producerVerifier']=json.loads(captured.getvalue())
    actual={rel:ident(B/'frozen/source101'/rel) for rel in M['sourceInputs']}
    need(len(actual)==101 and digest(actual)=='a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca','source101')
    policy=(B/'frozen/source101/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
    profile=json.loads(policy.split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
    need(profile['id']=='mixer.android-source-pair.9','pair9 policy')
    projected={}
    for kind,prefix,count,want in [('sdk','sdk',22,'bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0'),('adapter','native/android',24,'ee9414d3b68f9d66ba275c93339018e5eaebb161a7dc25d7056538c652305d89')]:
        inventory={rel:ident(B/'frozen/source101'/prefix/rel) for rel in profile[kind+'_files']}
        need(inventory==profile[kind+'_files'] and len(inventory)==count and digest(inventory)==want,kind+' projection')
        projected[kind]={'files':count,'sha256':digest(inventory)}
    R['checks']['sourceIdentities']={'canonical101':digest(actual),'projections':projected,'revision':M['sourceRevision'],'tree':M['sourceTree']}
    apk_path=B/M['apk']['relativePath']; apk=apk_path.read_bytes()
    need(sha(apk)=='155c54e3ca3f359d52ac40456253b35bbbacb09c838d2cd25ae7c2a5e72341d5','requested APK')
    R['checks']['apk']=ident(apk_path); R['checks']['signature']=signature(apk)
    product=(B/'attempt-2/classes.dex').read_bytes(); test=(B/'attempt-2/classes2.dex').read_bytes()
    pd,td=descriptors(product),descriptors(test)
    for label,defs in [('product',pd),('harness',td)]:
        filename='009-product-dexdump.stdout' if label=='product' else '010-harness-dexdump.stdout'
        need(official_descriptors((B/'attempt-2/commands'/filename).read_text())==defs,'official dexdump '+label)
    product_classes={class_name(p.read_bytes()) for p in (B/'frozen/product-classfiles').rglob('*.class')}
    harness_classes={class_name(p.read_bytes()) for p in (B/'attempt-2/harness-classfiles').rglob('*.class')}
    need(len(product_classes)==216 and product_classes<=pd,'216 binary class names in DEX')
    need(len(harness_classes)==23 and harness_classes<=td and td-harness_classes=={'Ldev/mixer/android/NativeMotionBoundaryInstrumentation-IA;'},'exact harness D8 access class')
    with zipfile.ZipFile(apk_path) as z, zipfile.ZipFile(F['donorAPK']['path']) as donor:
        need(ident(F['donorAPK']['path'])=={k:F['donorAPK'][k] for k in ('bytes','sha256')},'donor APK hash')
        need(z.read('classes.dex')==donor.read('classes.dex')==product,'donor product DEX reuse')
        for name in M['nativeLibraries']:
            data=z.read(name)
            need(data==donor.read(name)==(B/'frozen'/name).read_bytes(),'native reuse '+name)
            need(data[:4]==b'\x7fELF' and data[4:6]==b'\x02\x01' and struct.unpack_from('<H',data,18)[0]==183,'ARM64 ELF '+name)
        R['checks']['payload']=validate_payload(product,test,M['nativeLibraries'],z)
    R['checks']['classes']={'productClassfiles':len(product_classes),'testClassfiles':len(harness_classes),'extraTestDEX':sorted(td-harness_classes)}
    negative={}
    for label,c in load(B/'controls/result.json')['controls'].items():
        need(ident(c['path'])=={k:c[k] for k in ('bytes','sha256')},'negative archive identity '+label)
        try:
            with zipfile.ZipFile(c['path']) as z: validate_payload(product,test,M['nativeLibraries'],z)
        except ValueError as e:
            need(str(e).startswith(c['expectedRefusal']), 'negative refusal '+label)
            negative[label]=str(e)
        else: raise ValueError('negative accepted '+label)
    R['checks']['sixRetainedNegativeArchives']=negative
    for name in ('NativeMotionBoundaryActivity.java','NativeMotionBoundaryInstrumentation.java','AndroidManifest.xml'):
        need((B/'candidate'/name).read_bytes()==(B/'attempt-2/inputs'/name).read_bytes()==(B/'attempt-1/inputs'/name).read_bytes(),'unchanged source '+name)
    need('no D8 injected shared or unexpected definitions' in (B/'attempt-1/failure.log').read_text(),'baseline failure preserved')
    receipts=[]
    for rel in ['attempt-1/commands/commands.json','attempt-2/commands/commands.json','final-check-commands/commands.json']:
        cs=load(B/rel)
        need(all(all(c[k] for k in ['terminal_custody','direct_child_reaped','stdout_eof','stderr_eof','owned_group_absent']) and not c['cleanup_errors'] for c in cs),'recorded custody '+rel)
        receipts.append({'path':rel,'commands':len(cs),'identity':ident(B/rel)})
    R['checks']['recordedCustody']=receipts
    R['checks']['toolBindings']={'count':len(M['tools']),'tools':M['tools'],'basis':'Current bytes and realpaths checked; retained version output only; no tool executed'}
    line_specs={'candidate/NativeMotionBoundaryInstrumentation.java':[(47,73),(75,118),(128,187),(228,249),(250,275),(279,340)],
        'frozen/source101/native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java':[(134,140),(158,163),(188,260)],
        'frozen/source101/native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java':[(84,94)],
        'frozen/source101/native/android/app/src/dev/mixer/android/NativeRenderer.java':[(923,928)],
        'build.py':[(76,103),(135,170)], 'REPORT.md':[(1,25)],'runtime-packet.json':[(1,143)]}
    evidence=[]
    for rel,ranges in line_specs.items():
        lines=(B/rel).read_bytes().splitlines(keepends=True)
        for lo,hi in ranges:
            hi=min(hi,len(lines))
            evidence.append({'file':str(B/rel),'fileIdentity':ident(B/rel),'firstLine':lo,'lastLine':hi,
                             'lineRangeSHA256':sha(b''.join(lines[lo-1:hi]))})
    (HERE/'linehash-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    R['checks']['linehashEvidence']=ident(HERE/'linehash-evidence.json')
    R['checks']['imageReceipt']=ident(HERE.parent/'android-api32-33-image-install/receipt.json')
    R['status']='PASS_ARTIFACT_CONTROLS_RUNTIME_UNRUN'

try:
    main()
except BaseException as failure:
    R['status']='CONTROL_FAILED'; R['failure']=repr(failure); R['traceback']=traceback.format_exc()
finally:
    R['elapsedSeconds']=round(time.monotonic()-START,3)
    R['auditIdentity']=ident(__file__)
    R['cleanup']='No test children or temporary directories created; review outputs retained; no process probes/signals.'
    (HERE/'control-result.json').write_text(json.dumps(R,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':R['status'],'elapsedSeconds':R['elapsedSeconds'],'failure':R.get('failure'),'checks':list(R['checks'])},indent=2))
if R['status']=='CONTROL_FAILED':
    raise SystemExit(1)
