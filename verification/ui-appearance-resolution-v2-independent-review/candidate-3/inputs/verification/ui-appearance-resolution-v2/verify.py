#!/usr/bin/env python3
"""Freeze actual SDK/data contracts, then test/compile without device access."""
from pathlib import Path
import datetime, hashlib, json, os, re, subprocess, sys, time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OFFICIAL = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc')
ANDROID = Path('/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android')
def sha(data): return hashlib.sha256(data).hexdigest()
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    label = sys.argv[1] if len(sys.argv) == 2 else 'candidate-1'
    if not label or '/' in label or label in ('.','..'): raise ValueError('single unique candidate label required')
    out = HERE / label; out.mkdir(exist_ok=False)
    archive = out / 'inputs'
    files = [ROOT / p for p in ['AGENTS.md','mixer-product-plan.md','docs/ui-measured-appearance-v2-contract.md',
        'docs/ui-appearance-resolution-v2.md','sdk/Package.swift',
        'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
        'verification/ui-measured-appearance-v2-contract/descriptor-schema.json',
        'verification/ui-measured-appearance-v2-contract/shape-definitions.json',
        'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json',
        'verification/ui-appearance-foundation/design-corpus.json']]
    files += [p for folder in ['sdk/Sources','sdk/Tests'] for p in (ROOT / folder).rglob('*') if p.is_file()]
    files += [HERE / p for p in ['verify.py','PublicConsumer.swift','NegativeConsumer.swift']]
    manifest = {}
    for path in sorted(files):
        relative = str(path.relative_to(ROOT)); data = path.read_bytes(); manifest[relative] = sha(data)
        target = archive / relative; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
    digest = sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode())
    receipt = dict(format='mixer.ui-appearance-resolution-v2-evidence.1',status='running',startedUTC=utc(),
        sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sourceGitTree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
        sourceTreeSHA256=digest,inputManifest=manifest,commands=[],outputs={},
        scope='Pure public untrusted V2 appearance resolution for all10 current kinds; frozen complete SDK Debug/Release tests, separately compiled runtime public consumers, iOS and official Android module/public API compilation. No native resource capture/support/measurement/widget/signed/display/physical/GA authority.',
        pending=['independent root acceptance','internal native capture and concrete build support','native measurement/layout/widget consumption',
            'atomic native transaction and stale-environment enforcement','physical iOS/Android parity','immutable published separate-repository FieldLog packages',
            'signed display/input/health integration','signing/store/customer/operational/GA receipts'],
        physicalDevices=dict(discovered=False,used=False,reconnectionRequested=False))
    def save(): (out / 'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    def run(name,args,env,cwd=archive,expected=False,timeout=600):
        args = list(map(str,args)); start = time.monotonic()
        result = subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        log = out / (name+'.log'); log.write_bytes(result.stdout)
        receipt['commands'].append(dict(name=name,argv=args,cwd=str(cwd),exitCode=result.returncode,
            expectedFailure=expected,elapsedSeconds=time.monotonic()-start,environmentOverrides={'DEVELOPER_DIR':env['DEVELOPER_DIR']},
            log=str(log.relative_to(ROOT)),sha256=sha(result.stdout)));save();print(name,result.returncode,flush=True)
        if (result.returncode == 0) == expected: raise RuntimeError(name+'\n'+result.stdout.decode(errors='replace')[-6000:])
        return result.stdout.decode(errors='replace').strip()
    def output(path):
        receipt['outputs'][str(path.relative_to(ROOT))] = dict(bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
    save()
    apple = dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    android = dict(os.environ,DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
    try:
        run('python-version',['python3','--version'],apple)
        run('host-swift-version',['swift','--version'],apple)
        run('apple-xcode-version',['xcodebuild','-version'],apple)
        run('android-swift-version',[OFFICIAL,'--version'],android)
        run('android-xcode-version',['xcodebuild','-version'],android)
        ios = run('iphoneos-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path'],apple)
        for mode in ['debug','release']:
            scratch = out / '.build' / ('sdk-'+mode)
            result = run('sdk-'+mode,['swift','test','--package-path','sdk','--scratch-path',scratch,'-c',mode,'-Xswiftc','-warnings-as-errors'],apple)
            match = re.search(r'Test run with ([1-9][0-9]*) tests .*passed',result)
            if not match: raise RuntimeError('missing nonzero SDK test evidence')
            receipt.setdefault('sdkTestCounts',{})[mode] = int(match.group(1))
            for path in sorted(scratch.rglob('*.xctest')):
                if path.is_file(): output(path)
        receipt['androidSDKMetadata'] = {str(p):sha(p.read_bytes()) for p in [ANDROID/'swift-sdk.json',ANDROID/'swift-toolset.json']}
        for name,compiler,flags,env,runtime in [
            ('host-debug','swiftc',['-Onone'],apple,True),('host-release','swiftc',['-O'],apple,True),
            ('ios','swiftc',['-target','arm64-apple-ios17.0','-sdk',ios],apple,False),
            ('android',OFFICIAL,['-target','aarch64-unknown-linux-android30','-sdk',ANDROID/'ndk-sysroot',
                '-resource-dir',ANDROID/'swift-resources/usr/lib/swift-aarch64'],android,False)]:
            folder = out / '.build' / name; folder.mkdir(parents=True)
            common = ['-swift-version','6','-warnings-as-errors','-parse-as-library','-module-cache-path',folder/'cache','-I',folder,*flags]
            for module in ['MixerCore','MixerUI']:
                target = folder/(module+'.swiftmodule')
                args = [compiler,*common,'-emit-module','-module-name',module,'-emit-module-path',target]
                if runtime:
                    args += ['-emit-library','-o',folder/('lib'+module+'.dylib'),'-L',folder]
                    if module == 'MixerUI': args += ['-lMixerCore','-Xlinker','-rpath','-Xlinker',folder]
                run(name+'-'+module,[*args,*sorted((archive/'sdk/Sources'/module).glob('*.swift'))],env)
                output(target)
                if runtime: output(folder/('lib'+module+'.dylib'))
            probes = archive/'verification/ui-appearance-resolution-v2'
            if runtime:
                executable = folder/'public-consumer'
                run(name+'-public-compile',[compiler,*common,probes/'PublicConsumer.swift','-L',folder,'-lMixerUI','-lMixerCore',
                    '-Xlinker','-rpath','-Xlinker',folder,'-o',executable],env);output(executable)
                result = run(name+'-public-runtime',[executable],env)
                if not result.startswith('PASS public V2 resolver:'): raise RuntimeError('public runtime incomplete')
            else: run(name+'-public-typecheck',[compiler,*common,'-typecheck',probes/'PublicConsumer.swift'],env)
            failure = run(name+'-negative-immutable',[compiler,*common,'-typecheck',probes/'NegativeConsumer.swift'],env,expected=True)
            if 'nodes' not in failure or 'generation' not in failure or "'let'" not in failure: raise RuntimeError('unexpected negative probe failure')
        for relative,expected in manifest.items():
            if sha((ROOT/relative).read_bytes()) != expected or sha((archive/relative).read_bytes()) != expected:
                raise RuntimeError('input drift '+relative)
        receipt.update(status='passed-pure-v2-data-and-compilation-only',liveAndFrozenChecks=len(manifest)*2)
    except Exception as error:
        receipt.update(status='failed',error=str(error));raise
    finally:
        receipt['completedUTC']=utc();save()
if __name__ == '__main__': main()
