#!/usr/bin/env python3
"""Complete-descriptor byte-limit supplement with fresh build products."""
from pathlib import Path
import base64,copy,datetime,gzip,hashlib,importlib.util,json,os,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
RUN=HERE/'byte-boundaries';RUN.mkdir(exist_ok=False)
SNAP=HERE/'candidate-2/inputs';BUILD=HERE/'build/byte-boundaries';BUILD.mkdir(exist_ok=False)
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canonical=lambda v:(json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode()
manifest=json.loads((HERE/'candidate-2/input-manifest.json').read_text());commands=[];status='failed';results={}
for p,h in manifest.items():
    if sha(ROOT/p)!=h or sha(SNAP/p)!=h:raise RuntimeError('frozen/live input mismatch '+p)
script=Path(__file__).resolve();copy_path=RUN/'byte-boundaries.py';shutil.copy2(script,copy_path);copy_path.chmod(0o444)
if sha(script)!=sha(copy_path):raise RuntimeError('script copy mismatch')
sources={str((SNAP/p).relative_to(ROOT)):h for p,h in manifest.items()}
sources[str(copy_path.relative_to(ROOT))]=sha(script)
(RUN/'input-manifest.json').write_text(json.dumps(sources,indent=2,sort_keys=True)+'\n')
contract=SNAP/'verification/ui-measured-appearance-v2-contract'
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('frozen_contract',contract/'scripts/check-contract.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
base=json.loads((contract/'mixer-measured-default-v2.json').read_text())
cases=[]
for target in [65535,65536,65537]:
    d=copy.deepcopy(base)
    d['resources']=[{'id':f'r{i}','path':f'asset/{i}.png','kind':'iconPNG','sha256':'a'*64,'bytes':1,'scale':1,'locale':'und','direction':'neutral','provenance':'p'} for i in range(64)]
    remaining=target-len(canonical(d))
    for r in d['resources']:
        for key,limit in [('provenance',512),('path',256)]:
            growth=min(remaining,limit-len(r[key]));r[key]+='x'*growth;remaining-=growth
    if remaining:raise RuntimeError('insufficient filling capacity')
    wire=canonical(d)
    if len(wire)!=target:raise RuntimeError('wrong byte length')
    try:model.read(wire);expected='accept'
    except ValueError:expected='reject'
    if expected!=('reject' if target==65537 else 'accept'):raise RuntimeError('boundary oracle mismatch')
    cases.append((target,wire,expected))
payload=b''.join(base64.b64encode(b)+b'\n' for _,b,_ in cases)
(RUN/'descriptor-payload.gz').write_bytes(gzip.compress(payload,mtime=0))
(RUN/'corpus-manifest.json').write_text(json.dumps([{'bytes':n,'sha256':hashlib.sha256(b).hexdigest(),'expected':e} for n,b,e in cases],indent=2)+'\n')
def run(name,argv,input=None):
    argv=list(map(str,argv));p=subprocess.run(argv,cwd=SNAP,env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer'),input=input,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    log=RUN/(name+'.log');log.write_bytes(p.stdout)
    commands.append({'name':name,'argv':argv,'cwd':str(SNAP),'exit':p.returncode,'log':str(log.relative_to(ROOT)),'sha256':sha(log),'inputSHA256':hashlib.sha256(input).hexdigest() if input is not None else None})
    print(name,p.returncode,flush=True)
    if p.returncode:raise RuntimeError(p.stdout.decode(errors='replace')[-5000:])
    return p.stdout.decode().splitlines()
def check(name,answers):
    if answers!=[e for _,_,e in cases]:raise RuntimeError((name,answers))
    results[name]={'total':len(answers),'accept':answers.count('accept'),'reject':answers.count('reject')}
try:
    for name,argv in [('java-version',[JDK/'java','-version']),('javac-version',[JDK/'javac','-version']),('swift-version',['xcrun','swiftc','--version'])]:run(name,argv)
    own=SNAP/'verification/android-appearance-v2-independent-review'
    classes=BUILD/'java';classes.mkdir()
    run('javac',[JDK/'javac','--release','17','-Xlint:all','-Werror','-d',classes,*[SNAP/'native/android/app/src/dev/mixer/android'/n for n in ['AppearanceDescriptorV2.java','AppearanceGeometryV2.java']],own/'IndependentProbe.java'])
    for mode,flags in [('default',[]),('interpreted',['-Xint'])]:
        name='java-'+mode;check(name,run(name,[JDK/'java',*flags,'-cp',classes,'dev.mixer.android.IndependentProbe','descriptor'],payload))
    swift_sources=[SNAP/'sdk/Sources/MixerUI'/n for n in ['AppearanceValuesV1.swift','AppearanceDefaultV1.swift','AppearanceDescriptorV1.swift','AppearanceMetricMathV1.swift','SharedTextProfilesV1.swift','AppearanceGeometryV2.swift','AppearanceValuesV2.swift','AppearanceDefaultV2.swift','AppearanceDescriptorV2.swift']]
    for mode,opt in [('debug','-Onone'),('release','-O')]:
        folder=BUILD/('swift-'+mode);folder.mkdir();exe=folder/'probe'
        run('swift-'+mode+'-compile',['xcrun','swiftc','-swift-version','6','-warnings-as-errors',opt,'-module-cache-path',folder/'cache',*swift_sources,own/'IndependentProbe.swift','-o',exe])
        check('swift-'+mode,run('swift-'+mode,[exe,'descriptor'],payload))
    for p,h in sources.items():
        if sha(ROOT/p)!=h:raise RuntimeError('supplement input changed '+p)
    for p,h in manifest.items():
        if sha(ROOT/p)!=h:raise RuntimeError('live source changed '+p)
    if sha(script)!=sha(copy_path):raise RuntimeError('supplement script changed')
    status='passed-byte-boundary-data-only'
finally:
    artifacts={str(p.relative_to(ROOT)):sha(p) for p in BUILD.rglob('*') if p.is_file() and (p.suffix=='.class' or p.name=='probe')}
    evidence={str(p.relative_to(ROOT)):sha(p) for p in RUN.iterdir() if p.is_file() and p.name!='receipt.json'}
    receipt={'status':status,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'results':results,'artifacts':artifacts,'evidence':evidence,'scope':'Complete canonical icon-metadata descriptors at 65,535/65,536/65,537 bytes; host Java/Swift data only. No actual resource bytes, installation, native, physical, signed or release claims.'}
    (RUN/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(status,results)
