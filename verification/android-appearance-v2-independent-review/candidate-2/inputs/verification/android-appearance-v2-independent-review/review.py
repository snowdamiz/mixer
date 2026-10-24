#!/usr/bin/env python3
"""Independent, immutable-source review of Android V2 data only.

Reuses root's independent schema-admission corpus generator, never Java author tests.
The Java probe traverses every typed field and independently reconstitutes canonical
bytes. Geometry is checked against the frozen contract's arbitrary-precision oracle,
exact Python binary64 rational rounding, and separately compiled actual Swift.
"""
from pathlib import Path
import base64, copy, datetime, hashlib, importlib.util, json, math, os, random, shutil, struct, subprocess, sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUN=HERE/(sys.argv[1] if len(sys.argv)>1 else 'candidate-2')
BUILD=HERE/'build'/RUN.name
SNAP=RUN/'inputs'
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canonical=lambda value:(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
commands=[]
def write(name,value):
    (RUN/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def run(name,argv,payload=None):
    argv=list(map(str,argv))
    result=subprocess.run(argv,cwd=SNAP,env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer'),input=payload,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    log=RUN/(name+'.log'); log.write_bytes(result.stdout)
    commands.append({'name':name,'argv':argv,'cwd':str(SNAP),'exit':result.returncode,'log':str(log.relative_to(ROOT)),'sha256':sha(log),'inputSHA256':hashlib.sha256(payload).hexdigest() if payload is not None else None})
    print(name,result.returncode,flush=True)
    if result.returncode:raise RuntimeError(result.stdout.decode(errors='replace')[-5000:])
    return result.stdout.decode().splitlines()
def freeze():
    RUN.mkdir(exist_ok=False);BUILD.mkdir(parents=True,exist_ok=False);SNAP.mkdir(exist_ok=False)
    receipt_path=ROOT/'verification/android-appearance-v2-data/candidate-3/receipt.json'
    if sha(receipt_path)!='b8a983fe2510f80b508c211b2fb0eed079ae4f3857261ca6f3207ad01f50896f':raise RuntimeError('producer receipt changed')
    receipt=json.loads(receipt_path.read_text());seal_path=ROOT/'verification/android-appearance-v2-data/seal.json';seal=json.loads(seal_path.read_text())
    if seal['receiptSHA256']!=sha(receipt_path):raise RuntimeError('seal receipt mismatch')
    checked=0
    for p,h in receipt['inputManifest'].items():
        for actual in [ROOT/p,receipt_path.parent/'inputs'/p]:
            if sha(actual)!=h:raise RuntimeError('producer frozen/live input mismatch '+str(actual))
            checked+=1
    for p,h in seal['bindings'].items():
        if sha(ROOT/p)!=h:raise RuntimeError('sealed input mismatch '+p)
        checked+=1
    for command in receipt['commands']:
        if command['exit']!=0:raise RuntimeError('producer command failed')
        for stream in ['stdout','stderr']:
            if sha(ROOT/command[stream])!=command[stream+'SHA256']:raise RuntimeError('producer log mismatch')
            checked+=1
    for p,h in receipt['artifacts'].items():
        if sha(ROOT/p)!=h:raise RuntimeError('producer artifact mismatch '+p)
        checked+=1
    paths=set(receipt['inputManifest'])|set(seal['bindings'])|{
        str(receipt_path.relative_to(ROOT)),str(seal_path.relative_to(ROOT)),
        'verification/ui-appearance-descriptor-v2-root-review/review.py',
        'verification/ui-appearance-descriptor-v2-root-review/acceptance.json',
        'verification/ui-measured-appearance-v2-contract/scripts/check-contract.py',
        'verification/android-appearance-v2-independent-review/IndependentProbe.java',
        'verification/android-appearance-v2-independent-review/IndependentProbe.swift',
        'verification/android-appearance-v2-independent-review/review.py',
    }
    manifest={}
    for p in sorted(paths):
        source=ROOT/p;target=SNAP/p;target.parent.mkdir(parents=True,exist_ok=True)
        before=sha(source);shutil.copy2(source,target)
        if before!=sha(target) or before!=sha(source):raise RuntimeError('copy race '+p)
        target.chmod(0o444);manifest[p]=before
    # Build directory is unique to this exact source closure; no old incremental artifacts.
    write('input-manifest.json',manifest)
    write('provenance-check.json',{'producerBindingsAndLogsArtifactsChecked':checked,'producerReceiptSHA256':sha(receipt_path),'producerInputTreeSHA256':receipt['inputTreeSHA256'],'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sourceGitTree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),'snapshotCWD':str(SNAP),'inputTreeSHA256':hashlib.sha256(canonical(manifest)).hexdigest()})
    return manifest

def descriptor_cases(model,contract):
    # Execute only the root-authored generator portion; it has no writes/commands.
    source=(SNAP/'verification/ui-appearance-descriptor-v2-root-review/review.py').read_text()
    generator=source[source.index('def canonical(v):'):source.index('manifest=[')]
    scope={'ROOT':SNAP,'contract':contract,'model':model,'json':json,'copy':copy}
    exec(compile(generator,'frozen-root-independent-corpus-generator','exec'),scope)
    cases=scope['cases'];add=scope['add'];base=scope['base'];wire=scope['wire'];font=scope['font']
    root_count=len(cases)
    if root_count!=5584:raise RuntimeError('root corpus drift '+str(root_count))
    # Java ASCII/lexical attack surface: all byte values in a valid ID position,
    # shortest-escape rules, every syntax prefix, sorted keys and long numerals.
    for byte in range(256):add(f'java-byte-{byte}',wire.replace(b'mixer.measured-candidate.v2',b'a'+bytes([byte])+b'b',1))
    for n in [1,2,18,19,20,21,64,512,513,8192,65536]:
        add(f'java-number-digits-{n}',wire.replace(b'1088',b'9'*n,1))
    for prefix in [b'',b'+',b'-',b'00',b'01',b'0x',b'1.',b'.1',b'1e0',b'1E+0',b'NaN',b'Infinity',b'true',b'null']:
        add('java-number-token-'+prefix.hex(),wire.replace(b'1088',prefix,1))
    for token in [b'\\u0061',b'\\u002f',b'\\/',b'\\n',b'\\t',b'\\u0000',b'\\u007F',b'\\uD800',b'\\x61',b'\\',b'\x7f']:
        add('java-escape-'+token.hex(),canonical(scope['platform']).replace(b'Explicit app design',b'a'+token+b'b',1))
    for n in sorted(set([0,1,2,len(wire)-1,len(wire)]+list(range(0,len(wire),37)))):add(f'java-truncate-{n}',wire[:n])
    for n in [0,1,16,17,63,64,65]:
        d=copy.deepcopy(base);d['resources']=[dict(scope['resource'],kind='iconPNG',id=f'r{i}',path=f'asset/{i}.png') for i in range(n)];add(f'java-catalog-{n}',d)
    for field,value in [('bytes',4194304),('provenance','p'*512)]:
        for count in [4,5,16,17,64]:
            d=copy.deepcopy(base);d['resources']=[dict(scope['resource'],kind='iconPNG',id=f'r{i}',path=f'a/{i}.png',**{field:value}) for i in range(count)];add(f'java-catalog-{field}-{count}',d)
    for weight in [400,500,600,700]:
        d=copy.deepcopy(font);faces=d['theme']['typography']['font']['faces']
        if weight==500:faces.append(dict(faces[0],weight=500))
        faces.append(dict(faces[0],weight=weight,style='italic'));add(f'java-font-italic-with-normal-{weight}',d)
        d2=copy.deepcopy(d);d2['theme']['typography']['font']['faces'].append(copy.deepcopy(faces[-1]));add(f'java-font-duplicate-{weight}',d2)
    manifest=[{'name':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'expected':e} for n,b,e in cases]
    write('descriptor-manifest.json',manifest)
    return cases,root_count,[canonical(base),canonical(font),canonical(scope['platform'])]

def path_text(shape,width,height,commands):
    return f'{shape};{width};{height}'+''.join(';'+c['op']+''.join(f':{x},{y}' for x,y in c['points64']) for c in commands)
def bits(value):return struct.pack('>d',value).hex()
def nearest_binary64(value):
    numerator,denominator=value.as_integer_ratio()
    return (numerator*2+denominator)//(denominator*2)
def geometry_cases(model):
    cases=[]
    def add(name,args,expected,swift=True):cases.append({'name':name,'input':'\t'.join(map(str,args)),'expected':expected,'swift':swift})
    shapes=model.SHAPES
    for shape,op in [('track63x28Continuous2','track'),('thumb37x24Continuous2','thumb')]:
        p=shapes['fixedPaths'][shape];add(op,[op],'ok\t'+path_text(shape,p['width64'],p['height64'],p['commands']))
    for checked in [0,1]:
        for rtl in [False,True]:add(f'origin-{checked}-{rtl}',['origin',checked,'rightToLeft' if rtl else 'leftToRight'],f'ok\t{1536 if bool(checked)!=rtl else 128},128')
    rng=random.Random(0xA24E2)
    groups=[(w,h,r) for w in [0,1,2,3,31,63,64,101,200335,2147483647] for h in [0,1,3,65,1792,2147483647] for r in [0,1,1664,65536]]
    groups += [(rng.randrange(2147483648),rng.randrange(2147483648),rng.randrange(65537)) for _ in range(250)]
    # Radius-clamp transitions around 2*a*r/den, including every low radius.
    for r in range(0,100):
        transition=(3057330*r+999999)//1000000
        groups.extend((max(0,transition+delta),max(0,transition+delta+1),r) for delta in [-1,0,1])
    for i,(w,h,r) in enumerate(groups):
        add(f'group-{i}',['group',w,h,r],'ok\t'+path_text('fullGroupContinuousCubic2',w,h,model.group_path(w,h,r)))
    for i,args in enumerate([(-1,1,1),(1,-1,1),(1,1,-1),(0,0,65537),(2147483648,1,1),(1,2147483648,1),(9223372036854775807,1,1),(1,1,9223372036854775807)]):
        error='extent' if args[0]<0 or args[1]<0 or args[0]>2147483647 or args[1]>2147483647 else 'radius'
        add(f'group-invalid-{i}',['group',*args],'reject\t'+error,all(0<=a<=4294967295 for a in args))
    # Every possible spacing quantization tie; density every possible supported tie.
    for op,scale,low,high,maximum in [('spacing',64,0,256,16384),('density',1024,0.125,16,16384)]:
        values=[-math.inf,-1,-0.0,0.0,math.nextafter(low,-math.inf),low,high,math.nextafter(high,math.inf),math.inf,math.nan]
        for integer in range(int(low*scale),maximum):
            midpoint=(integer+0.5)/scale
            values.extend([math.nextafter(midpoint,-math.inf),midpoint,math.nextafter(midpoint,math.inf)])
        for i,value in enumerate(values):
            expected='ok\t'+str(nearest_binary64(value*scale)) if math.isfinite(value) and low<=value<=high else 'reject\t'+op
            add(f'{op}-{i}',[op,bits(value)],expected)
    extent_values=[-math.inf,-1,-0.0,0.0,math.nextafter(0,math.inf),math.inf,math.nan]
    for n in [1,2,63,64,65,65536,2147483646,2147483647]:
        v=n/64;extent_values.extend([math.nextafter(v,-math.inf),v,math.nextafter(v,math.inf)])
    for i,value in enumerate(extent_values):
        expected='ok\t'+str(math.ceil(value*64)) if math.isfinite(value) and 0<=value<=2147483647/64 else 'reject\textent'
        add(f'extent-{i}',['extent',bits(value)],expected)
    for i in range(1100):
        x=[0,1,2,63,64,65,2147483647][i%7] if i<70 else rng.randrange(2147483648)
        d=[128,129,1024,3072,16384][i%5] if i<70 else rng.randrange(128,16385)
        add(f'edge-{i}',['edge',x,d],'ok\t'+str((x*d+32768)//65536))
        add(f'coordinate-{i}',['coordinate',x,d],'ok\t'+bits(x*d/65536).lstrip('0'))
        if x==0:cases[-1]['expected']='ok\t0'
    for i,(x,d) in enumerate([(-1,1024),(2147483648,1024),(9223372036854775807,1024),(1,127),(1,16385),(1,-1),(1,2147483647)]):
        for op in ['edge','coordinate']:
            add(f'{op}-invalid-{i}',[op,x,d],'reject\t'+('extent' if x<0 or x>2147483647 else 'density'),0<=x<=4294967295 and 0<=d<=65535)
    write('geometry-manifest.json',{'total':len(cases),'javaOnly':sum(not c['swift'] for c in cases),'cases':cases})
    return cases

def parser_errors():
    def tree(count):
        if count==1:return 0
        if count<=65:return [0]*(count-1)
        children=[];remaining=count-1
        while remaining:
            child=min(remaining,128 if count>129 else 64);children.append(tree(child));remaining-=child
        # This construction has at most 64 children for our 8191..8193 targets.
        return children
    cases=[]
    for count in [8191,8192,8193]:
        data=canonical(tree(count));cases.append((f'values-{count}',data,'shape' if count<=8192 else 'valueLimit'))
    for depth in [19,20,21]:cases.append((f'depth-{depth}',b'['*depth+b'0'+b']'*depth+b'\n','shape' if depth<=20 else 'depthLimit'))
    for count in [64,65]:cases.append((f'array-{count}',canonical([0]*count),'shape' if count<=64 else 'arrayLimit'))
    for n in [0,65537]:cases.append((f'bytes-{n}',b' '*n,'byteLimit'))
    cases.extend([('duplicate',b'{"a":0,"a":0}\n','duplicateKey'),('sort',b'{"b":0,"a":0}\n','noncanonical'),('ascii',b'"\xff"\n','invalidEncoding')])
    write('parser-error-manifest.json',[{'name':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'expected':e} for n,b,e in cases])
    return cases

def compare(name,cases,answers):
    if len(cases)!=len(answers):raise RuntimeError(f'{name} output count {len(answers)} != {len(cases)}')
    mismatches=[{'name':n,'expected':e,'actual':a} for (n,e),a in zip(cases,answers) if e!=a]
    if mismatches:write(name+'-mismatches.json',mismatches);raise RuntimeError(str(mismatches[:8]))
    return {'total':len(answers),'accept':answers.count('accept'),'reject':answers.count('reject'),'outputSHA256':hashlib.sha256(('\n'.join(answers)+'\n').encode()).hexdigest()}

def main():
    manifest=freeze();counts={};status='failed'
    try:
        for name,argv in [('java-version',[JDK/'java','-version']),('javac-version',[JDK/'javac','-version']),('swift-version',['xcrun','swiftc','--version']),('python-version',[sys.executable,'--version']),('xcode-version',['xcodebuild','-version'])]:run(name,argv)
        sys.dont_write_bytecode=True
        contract=SNAP/'verification/ui-measured-appearance-v2-contract'
        spec=importlib.util.spec_from_file_location('frozen_contract',contract/'scripts/check-contract.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
        descriptors,root_count,ownership=descriptor_cases(model,contract);geometry=geometry_cases(model);parser=parser_errors()
        payload=b''.join(base64.b64encode(b)+b'\n' for _,b,_ in descriptors)
        parser_payload=b''.join(base64.b64encode(b)+b'\n' for _,b,_ in parser)
        java_geometry=('\n'.join(c['input'] for c in geometry)+'\n').encode()
        swift_geometry=('\n'.join(c['input'] for c in geometry if c['swift'])+'\n').encode()
        own=SNAP/'verification/android-appearance-v2-independent-review'
        java_sources=[SNAP/'native/android/app/src/dev/mixer/android'/n for n in ['AppearanceDescriptorV2.java','AppearanceGeometryV2.java']]+[own/'IndependentProbe.java']
        classes=BUILD/'java-closure-1';classes.mkdir()
        run('javac',['%s/javac'%JDK,'--release','17','-Xlint:all','-Werror','-d',classes,*java_sources])
        for mode,flags in [('default',[]),('interpreted',['-Xint'])]:
            prefix=[JDK/'java',*flags,'-cp',classes,'dev.mixer.android.IndependentProbe']
            counts['java-'+mode+'-descriptors']=compare('java-'+mode+'-descriptors',[(n,e) for n,_,e in descriptors],run('java-'+mode+'-descriptors',prefix+['descriptor'],payload))
            counts['java-'+mode+'-geometry']=compare('java-'+mode+'-geometry',[(c['name'],c['expected']) for c in geometry],run('java-'+mode+'-geometry',prefix+['geometry'],java_geometry))
            counts['java-'+mode+'-parser']=compare('java-'+mode+'-parser',[(n,e) for n,_,e in parser],run('java-'+mode+'-parser',prefix+['parser-errors'],parser_payload))
            counts['java-'+mode+'-ownership']=compare('java-'+mode+'-ownership',[(str(i),'immutable') for i in range(len(ownership))],run('java-'+mode+'-ownership',prefix+['ownership'],b''.join(base64.b64encode(b)+b'\n' for b in ownership)))
        swift_sources=[SNAP/'sdk/Sources/MixerUI'/n for n in ['AppearanceValuesV1.swift','AppearanceDefaultV1.swift','AppearanceDescriptorV1.swift','AppearanceMetricMathV1.swift','SharedTextProfilesV1.swift','AppearanceGeometryV2.swift','AppearanceValuesV2.swift','AppearanceDefaultV2.swift','AppearanceDescriptorV2.swift']]
        for mode,opt in [('debug','-Onone'),('release','-O')]:
            folder=BUILD/('swift-'+mode+'-closure-1');folder.mkdir();exe=folder/'probe'
            run('swift-'+mode+'-compile',['xcrun','swiftc','-swift-version','6','-warnings-as-errors',opt,'-module-cache-path',folder/'cache',*swift_sources,own/'IndependentProbe.swift','-o',exe])
            counts['swift-'+mode+'-descriptors']=compare('swift-'+mode+'-descriptors',[(n,e) for n,_,e in descriptors],run('swift-'+mode+'-descriptors',[exe,'descriptor'],payload))
            counts['swift-'+mode+'-geometry']=compare('swift-'+mode+'-geometry',[(c['name'],c['expected']) for c in geometry if c['swift']],run('swift-'+mode+'-geometry',[exe,'geometry'],swift_geometry))
        for p,h in manifest.items():
            if sha(ROOT/p)!=h or sha(SNAP/p)!=h:raise RuntimeError('frozen or live input drift '+p)
        status='recommended-data-only'
    finally:
        artifacts={str(p.relative_to(ROOT)):sha(p) for p in BUILD.rglob('*') if p.is_file() and (p.suffix=='.class' or p.name=='probe')}
        write('acceptance.json',{'format':'mixer.android-appearance-v2-independent-review.1','status':status,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'independent bounded review agent','sourceClosureManifest':str((RUN/'input-manifest.json').relative_to(ROOT)),'sourceClosureManifestSHA256':sha(RUN/'input-manifest.json'),'producerReceiptSHA256':'b8a983fe2510f80b508c211b2fb0eed079ae4f3857261ca6f3207ad01f50896f','commands':commands,'artifacts':artifacts,'counts':counts,'scope':'Actual sealed Java V2 data reader/geometry compared with frozen closed contract and actual Swift V2 data codec/geometry. Root descriptor corpus reused independently of Java author; extra review-owned Java adversarial/parser/immutability and exhaustive binary64 tie-neighbor probes. No native, font-installation, physical-device, signing, OTA, FieldLog, compiler, store, customer, operational or GA acceptance.'})
    print(status,counts,flush=True)

if __name__=='__main__':main()
