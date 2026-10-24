#!/usr/bin/env python3
"""Independent frozen-source execution and differential contract review.

No devices or network access. Only this review directory is written.
"""
from pathlib import Path
import datetime, gzip, hashlib, json, os, shutil, subprocess, sys, time
import oracle
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    label=sys.argv[1] if len(sys.argv)>1 else 'candidate-1'
    out=HERE/label;out.mkdir(exist_ok=False)
    producer_path=ROOT/'verification/ui-appearance-resolution-v2/candidate-1/receipt.json'
    producer=json.loads(producer_path.read_bytes());manifest=producer['inputManifest']
    actual={}
    for relative,digest in manifest.items():
        data=(ROOT/relative).read_bytes()
        if sha(data)!=digest:raise RuntimeError('producer/live source drift: '+relative)
        target=out/'inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);actual[relative]=sha(data)
    source_digest=sha(json.dumps(actual,sort_keys=True,separators=(',',':')).encode())
    if source_digest!=producer['sourceTreeSHA256']:raise RuntimeError('producer source digest mismatch')
    harness={p.name:sha(p.read_bytes()) for p in HERE.glob('*') if p.is_file()}
    for name in harness:
        target=out/'harness'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(HERE/name,target)
    receipt=dict(format='mixer.ui-appearance-resolution-v2-independent-review.1',status='running',startedUTC=utc(),sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sourceGitTree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),sourceTreeSHA256=source_digest,inputManifest=actual,harnessManifest=harness,
        producerBindings={str(producer_path.relative_to(ROOT)):sha(producer_path.read_bytes())},commands=[],outputs={},scope='Independent host-only pure-data differential and adversarial resolution review; native consumers/resources/transactions/signing/display/device/GA authority not exercised',
        physicalDevices=dict(discovered=False,used=False,reconnectionRequested=False),findings=[],pending=['native resource capture and build support','native layout/measurement/widget/transaction/stale-environment enforcement','physical iOS/Android parity','published separate-repository FieldLog qualification','signed appearance/display/input/health closure','store/customer/operational/GA evidence'])
    for file in ['count-audit.json']:
        path=producer_path.parent/file;receipt['producerBindings'][str(path.relative_to(ROOT))]=sha(path.read_bytes())
        target=out/'producer'/file;target.parent.mkdir(exist_ok=True);shutil.copyfile(path,target)
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    def bind(path):receipt['outputs'][str(path.relative_to(ROOT))]=dict(bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
    def run(name,args,cwd=out,expected=0,timeout=600):
        args=list(map(str,args));started=time.monotonic();p=subprocess.run(args,cwd=cwd,env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        log=out/(name+'.log');log.write_bytes(p.stdout)
        receipt['commands'].append(dict(name=name,argv=args,cwd=str(cwd),environmentOverrides={'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},exitCode=p.returncode,expectedExitCode=expected,elapsedSeconds=time.monotonic()-started,log=str(log.relative_to(ROOT)),sha256=sha(p.stdout)));save();print(name,p.returncode,flush=True)
        if p.returncode!=expected:raise RuntimeError(name+'\n'+p.stdout.decode(errors='replace')[-6000:])
        return p.stdout.decode(errors='replace')
    def packed(path):
        data=path.read_bytes();target=path.with_suffix(path.suffix+'.gz');target.write_bytes(gzip.compress(data,mtime=0));bind(target)
        receipt.setdefault('packedArtifacts',{})[str(path.relative_to(ROOT))]=dict(uncompressedBytes=len(data),uncompressedSHA256=sha(data),gzip=str(target.relative_to(ROOT)))
        path.unlink()
    save()
    try:
        receipt['toolVersions']={name:run(name,args).strip() for name,args in [('python-version',['python3','--version']),('swift-version',['swiftc','--version']),('xcode-version',['xcodebuild','-version'])]}
        default=json.loads((out/'inputs/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json').read_bytes())
        cases=oracle.build_cases(default);expected=[oracle.expected(c) for c in cases]
        case_file=out/'cases.json';case_file.write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':'))+'\n')
        expectation_file=out/'expected.json';expectation_file.write_text(json.dumps(expected,ensure_ascii=False,separators=(',',':'))+'\n')
        receipt['caseCounts']=dict(total=len(cases),accepted=sum('error' not in e for e in expected),rejected=sum('error' in e for e in expected),combinedThemeProfileSchemeDirectionPlatform=96,
            acceptedNodes=sum(len(e.get('nodes',[])) for e in expected),stylesCompared=sum(4*len(e.get('nodes',[])) for e in expected))
        results={}
        source=(out/'inputs/sdk/Sources/MixerUI/AppearanceResolutionV2.swift').read_text()
        mutations={
            'disabled-inheritance':('let disabled = ancestorDisabled || node.properties["disabled"]?.bool == true','let disabled = (ancestorDisabled && false) || node.properties["disabled"]?.bool == true'),
            'caption-gap-hardcode':('theme.stacks.bodyCaptionGap64 : theme.stacks.defaultGap64','UInt32(128) : theme.stacks.defaultGap64'),
            'final-separator':('separatorAfter: rowIndex + 1 < rows.count','separatorAfter: true'),
            'nested-list-admission':('!(node.kind == .list && insideList)','true'),
            'profile-collapse':('switch profile {','switch UISharedTextProfileV1.l {'),
            'text-alpha-loss':('foreground: rolePaint(text.role),','foreground: UIRGBA8V1(red: rolePaint(text.role).red, green: rolePaint(text.role).green, blue: rolePaint(text.role).blue, alpha: 255),'),
        }
        variants=[('baseline-debug',None,'-Onone'),('baseline-release',None,'-O')]+[(k,v,'-Onone') for k,v in mutations.items()]
        for name,mutation,opt in variants:
            folder=out/'.build'/name;folder.mkdir(parents=True)
            sources=out/'inputs/sdk/Sources'
            if mutation:
                sources=folder/'variant-sources';shutil.copytree(out/'inputs/sdk/Sources',sources)
                before,after=mutation
                if before not in source:raise RuntimeError('mutation anchor missing '+name)
                changed=source.replace(before,after);(sources/'MixerUI/AppearanceResolutionV2.swift').write_text(changed)
                retained=out/'mutations'/name/'AppearanceResolutionV2.swift';retained.parent.mkdir(parents=True);retained.write_text(changed);bind(retained)
                receipt.setdefault('mutations',{})[name]=dict(before=before,after=after,replacements=source.count(before),mutatedSourceSHA256=sha(changed.encode()),allOtherInputsUnchanged=True)
            common=['-swift-version','6','-warnings-as-errors','-parse-as-library','-module-cache-path',folder/'cache','-I',folder,opt]
            for module in ['MixerCore','MixerUI']:
                args=['swiftc',*common,'-enable-testing','-emit-module','-module-name',module,'-emit-module-path',folder/(module+'.swiftmodule'),'-emit-library','-o',folder/('lib'+module+'.dylib'),'-L',folder]
                if module=='MixerUI':args+=['-lMixerCore','-Xlinker','-rpath','-Xlinker',folder]
                run(name+'-'+module,[*args,*sorted((sources/module).glob('*.swift'))]);bind(folder/(module+'.swiftmodule'));bind(folder/('lib'+module+'.dylib'))
            binary=folder/'probe'
            run(name+'-probe-compile',['swiftc',*common,HERE/'Probe.swift','-L',folder,'-lMixerUI','-lMixerCore','-Xlinker','-rpath','-Xlinker',folder,'-o',binary]);bind(binary)
            actual_file=out/(name+'-actual.json')
            run(name+'-probe-runtime',[binary,case_file,actual_file]);observed=json.loads(actual_file.read_bytes())
            failures=[]
            for want,got in zip(expected,observed):
                failure=oracle.mismatch(want,got)
                if failure:failures.append(dict(name=want['name'],mismatch=failure))
            if len(expected)!=len(observed):raise RuntimeError('case count mismatch')
            results[name]=dict(passed=len(expected)-len(failures),failed=len(failures),firstFailures=failures[:5]);receipt['results']=results;packed(actual_file);save()
            if not mutation and failures:raise RuntimeError('independent oracle mismatch '+json.dumps(failures[:5]))
            if mutation and not failures:raise RuntimeError('oracle failed to detect '+name)
        # Independent public value-semantics/reconciliation checks and internal
        # malformed snapshot admission do not share the differential oracle.
        for mode in ['baseline-debug','baseline-release']:
            folder=out/'.build'/mode;binary=folder/'adversarial'
            run(mode+'-adversarial-compile',['swiftc','-swift-version','6','-warnings-as-errors','-parse-as-library','-I',folder,'-L',folder,'-lMixerUI','-lMixerCore','-Xlinker','-rpath','-Xlinker',folder,HERE/'Adversarial.swift','-o',binary]);bind(binary)
            run(mode+'-adversarial-runtime',[binary])
        # V1 unchanged against both candidate freeze and current repository HEAD.
        v1=[r for r in actual if r.startswith('sdk/') and ('V1.swift' in r or r.endswith('/AppearanceV1Tests.swift'))]
        v1_check={}
        for relative in v1:
            p=subprocess.run(['git','show','HEAD:'+relative],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            v1_check[relative]=dict(candidateSHA256=actual[relative],headSHA256=sha(p.stdout),matches=p.returncode==0 and sha(p.stdout)==actual[relative])
        if not all(v['matches'] for v in v1_check.values()):raise RuntimeError('V1 drift')
        receipt['v1Unchanged']=v1_check
        # Final freeze recheck makes input drift visible; a later root commit is
        # not itself a source-byte change and does not invalidate the capture.
        for relative,digest in actual.items():
            if sha((ROOT/relative).read_bytes())!=digest or sha((out/'inputs'/relative).read_bytes())!=digest:raise RuntimeError('final source drift '+relative)
        for name,digest in harness.items():
            if sha((HERE/name).read_bytes())!=digest or sha((out/'harness'/name).read_bytes())!=digest:raise RuntimeError('harness drift '+name)
        packed(case_file);packed(expectation_file)
        receipt.update(status='passed-independent-pure-data-review',completedUTC=utc(),liveAndFrozenChecks=len(actual)*2)
    except Exception as error:
        receipt.update(status='failed',error=str(error),completedUTC=utc());raise
    finally:save()
if __name__=='__main__':main()
