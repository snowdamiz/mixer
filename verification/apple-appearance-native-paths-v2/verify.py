from pathlib import Path
import datetime, hashlib, json, os, re, shutil, subprocess, sys, time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
label = sys.argv[1]
if not label or '/' in label or label in ('.', '..'): raise ValueError('candidate label required')
out = HERE / label
out.mkdir(exist_ok=False)
archive = out / 'inputs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
paths = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--',
    'sdk/Package.swift','sdk/Sources','sdk/Tests',
    'docs/ui-measured-appearance-v2-contract.md',
    'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
    'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
    'verification/ui-appearance-foundation/design-corpus.json',
    str(Path(__file__).relative_to(ROOT))],cwd=ROOT,text=True).splitlines()
manifest = {}
for relative in sorted(set(paths)):
    source = ROOT / relative
    destination = archive / relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,destination)
    manifest[relative] = sha(source)
receipt = dict(schema=1,status='running',sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    sourceTreeSHA256=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    inputManifest=manifest,commands=[],outputs={},testCounts={},
    environmentOverrides={'DEVELOPER_DIR':env['DEVELOPER_DIR']},
    scope='Actual macOS CoreGraphics closed-path conversion, independent ownership, fill/clip checks, full SDK host regression and iOS17 module compilation. Not native UI consumption, physical iOS/Android, visual parity, signed or GA qualification.')
def save(): (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
def run(name,args,cwd=archive):
    start=time.monotonic()
    result=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900)
    log=out/(name+'.log');log.write_bytes(result.stdout)
    receipt['commands'].append(dict(name=name,argv=list(map(str,args)),cwd=str(cwd),exit=result.returncode,
        log=str(log.relative_to(ROOT)),sha256=sha(log),elapsedSeconds=time.monotonic()-start));save()
    print(name,result.returncode,flush=True)
    if result.returncode: raise RuntimeError(name+'\n'+result.stdout.decode(errors='replace')[-6000:])
    return result.stdout.decode()
def bind(path): receipt['outputs'][str(path.relative_to(ROOT))]=dict(bytes=path.stat().st_size,sha256=sha(path))
save()
try:
    run('python-version',['python3','--version']);run('swift-version',['swift','--version']);run('xcode-version',['xcodebuild','-version'])
    ios=run('ios-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path']).strip()
    for mode in ['debug','release']:
        scratch=out/'.build'/mode
        text=run('sdk-'+mode,['swift','test','--package-path',archive/'sdk','--scratch-path',scratch,'-c',mode,'-Xswiftc','-warnings-as-errors'])
        swift=re.findall(r'✔ Test (\w+)\([^\n]*\) passed',text)
        xctest=re.findall(r"Test Case '-\[([\w]+)\.([^\]]+)\]' passed",text)
        summaries=list(map(int,re.findall(r'✔ Test run with (\d+) tests .*passed',text)))
        assert len(swift)==len(set(swift))==sum(summaries)
        assert len(xctest)==len(set(xctest))
        new=[name for name in swift if name.startswith('nativeSharedPaths')]
        assert len(new)==4 and len(swift)+len(xctest)==131
        receipt['testCounts'][mode]=dict(swiftTesting=len(swift),xctest=len(xctest),total=len(swift)+len(xctest),newTests=new)
        for binary in scratch.rglob('*.xctest'):
            if binary.is_file(): bind(binary)
    folder=out/'.build'/'ios';folder.mkdir(parents=True)
    for module in ['MixerCore','MixerUI','MixerApple']:
        target=folder/(module+'.swiftmodule')
        args=['swiftc','-swift-version','6','-warnings-as-errors','-parse-as-library','-target','arm64-apple-ios17.0',
              '-sdk',ios,'-module-cache-path',folder/'cache','-I',folder,'-emit-module','-module-name',module,'-emit-module-path',target]
        run('ios-'+module,[*args,*sorted((archive/'sdk/Sources'/module).glob('*.swift'))]);bind(target)
    for relative, expected in manifest.items():
        assert sha(ROOT/relative)==sha(archive/relative)==expected,relative
    receipt['status']='passed-native-primitive-host-and-ios-compilation'
except Exception as error:
    receipt.update(status='failed',error=str(error));raise
finally:
    receipt['completedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
