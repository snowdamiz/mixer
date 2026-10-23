#!/usr/bin/env python3
"""Freeze and qualify metadata-only v3 durable SPI; never execute Wasm or devices."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = '61f34bf3834a81d47b6e3a9b191ede5a5743ea9e'
OLD_V3 = '96c8cb21dceb2fe50334f279d3b2656b3ed92efb101fd62f5765ffe4e83d8cd1'
OFFICIAL = '/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(ok, why):
    if not ok: raise RuntimeError(why)
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def source_paths():
    excluded = {'.build', '.swiftpm', '__pycache__'}
    result = [p for p in (ROOT/'updates').rglob('*') if p.is_file() and not excluded.intersection(p.relative_to(ROOT).parts)]
    result += list((ROOT/'contracts').glob('*.json'))
    result += [HERE/'run.py', ROOT/'docs/capability-durable-updater-api-design.md']
    for folder in ['Consumer', 'CompileNegative']:
        result += [p for p in (HERE/folder).rglob('*') if p.is_file()]
    result += [ROOT/'verification/release-v3-swift/PublicClient/Sources/proof-client/main.swift']
    return sorted(set(result))

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--label', required=True)
    args = ap.parse_args()
    require(re.fullmatch('[a-z0-9-]+', args.label), 'simple fresh label required')
    out = HERE/args.label; out.mkdir(exist_ok=False)
    work = ROOT/'updates/.build'/('durable-spi-'+args.label); work.mkdir(exist_ok=False)
    source = work/'source'; source.mkdir()
    records = {}
    for p in source_paths():
        require(not p.is_symlink(), 'symlink source '+str(p))
        relative = str(p.relative_to(ROOT)); raw = p.read_bytes(); records[relative] = sha(raw)
        destination = source/relative; destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(raw)
    manifest = ''.join(d+'  '+p+'\n' for p,d in sorted(records.items())).encode()
    (out/'source-manifest.sha256').write_bytes(manifest)
    changed = (source/'updates/Sources/MixerUpdates/VerifierV3.swift').read_text()
    restored = re.sub(r'(?m)^[ \t]*// BEGIN additive CapabilityDurableV3 metadata SPI\.\n[\s\S]*?^[ \t]*// END additive CapabilityDurableV3 metadata SPI\.\n\n?', '', changed).encode()
    old = subprocess.check_output(['git','show',BASELINE+':updates/Sources/MixerUpdates/VerifierV3.swift'],cwd=ROOT)
    require(sha(old)==OLD_V3 and restored==old, 'existing v3 bytes changed outside three additive blocks')
    old_paths = subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'--','updates'],cwd=ROOT,text=True).splitlines()
    preserved = {}
    for relative in old_paths:
        if relative=='updates/Sources/MixerUpdates/VerifierV3.swift': continue
        baseline = subprocess.check_output(['git','show',BASELINE+':'+relative],cwd=ROOT)
        require((ROOT/relative).read_bytes()==baseline, 'old updates bytes changed '+relative)
        preserved[relative]=sha(baseline)
    receipt = {'status':'running','started_at':utc(),'head_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'baseline_revision':BASELINE,'baseline_v3_sha256':OLD_V3,'baseline_v3_restored_exact':True,
        'preserved_old_updates_files':preserved,'source_files':records,'source_manifest_sha256':sha(manifest),
        'immutable_source_export':str(source),'driver_sha256':sha(Path(__file__).read_bytes()),'commands':[],
        'scope':'Metadata-only SPI. No durable-health provenance, Wasm admission/execution, adapter/coordinator, device, hosted/publication or GA claim.',
        'limitations':['Retained SPI is a trusted metadata helper, not proof of committed health or execution authority.',
            'Synchronous verification has per-argument bounds but no global call/concurrency/total-RSS/OOM recovery claim.',
            'TSan instruments owned Swift/C shim, not system CryptoKit/platform frameworks.',
            'Official cross SDK compilation is module/object evidence, not final app link or platform run.',
            'Validation/adapter lifetime and coordinator designs are independent pending work.']}
    def save(): (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def unchanged():
        for relative,digest in records.items():
            require(sha((ROOT/relative).read_bytes())==digest, 'live input changed '+relative)
            require(sha((source/relative).read_bytes())==digest, 'export input changed '+relative)
    apple = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    official = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer')
    def run(name, argv, scope, expected=0, tests=None, diagnostic=None, env=apple, timeout=300):
        unchanged(); began=time.monotonic()
        try:
            r=subprocess.run(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
            raw,code=r.stdout,r.returncode
        except subprocess.TimeoutExpired as e: raw,code=(e.stdout or b'')+b'\nBounded qualification command timed out\n',124
        log=out/(name+'.log');log.write_bytes(raw)
        row={'name':name,'argv':argv,'cwd':str(source),'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']},
             'exit_code':code,'expected_exit':expected,'elapsed_seconds':time.monotonic()-began,
             'log':str(log.relative_to(ROOT)),'sha256':sha(raw),'scope':scope}
        if tests is not None:
            seen=[int(n) for n in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed',raw)]
            row.update(expected_tests=tests,observed_tests=seen)
        if diagnostic:row['required_diagnostic_fragment']=diagnostic
        receipt['commands'].append(row);save();unchanged()
        print(name+': '+str(code),flush=True)
        require(code==expected, name+': unexpected status '+str(code))
        if tests is not None:require(seen==[tests],name+': wrong test count')
        if diagnostic:require(diagnostic.encode() in raw,name+': wrong intentional rejection')
        return raw
    save()
    try:
        for name,cmd in [('swift-version',['swift','--version']),('xcode-version',['xcodebuild','-version']),('host-version',['uname','-a']),('python-version',['python3','--version'])]:run(name,cmd,'Observed tools')
        run('official-swift-version',[OFFICIAL,'--version'],'Official cross compiler version',env=official)
        base=['swift','test','--package-path',str(source/'updates'),'--scratch-path',str(work/'host'),'-Xswiftc','-warnings-as-errors']
        for mode in ['debug','release']:
            run('all-'+mode,base+['-c',mode],'All55 unchanged original and14 new SPI test functions',tests=69)
        products=work/'host/out/Products/Debug'
        require((products/'libMixerUpdates.a').is_file(),'actual static host library')
        module=work/'host/out/Intermediates.noindex/GeneratedModuleMaps/MixerDurableIO.modulemap'
        common=['swiftc','-swift-version','6','-warnings-as-errors','-I',str(products),'-Xcc','-fmodule-map-file='+str(module)]
        consumer=work/'spi-consumer'
        run('spi-consumer-link',common+['-L',str(products),'-lMixerUpdates',str(source/'verification/release-v3-durable-spi/Consumer/main.swift'),'-o',str(consumer)],'External non-testable SPI consumer compile and static link')
        fixture=source/'updates/Tests/MixerUpdatesTests/Fixtures/signed-release-v3.json'
        run('spi-consumer-run',[str(consumer),str(fixture)],'Actual externally linked SPI metadata calls and strict ordinary expiry/context checks')
        oldconsumer=work/'old-public-consumer'
        run('old-public-consumer-link',common+['-L',str(products),'-lMixerUpdates',str(source/'verification/release-v3-swift/PublicClient/Sources/proof-client/main.swift'),'-o',str(oldconsumer)],'Unchanged non-SPI public consumer preservation')
        run('old-public-consumer-run',[str(oldconsumer),str(fixture)],'Unchanged v3 public consumer behavior')
        negatives=source/'verification/release-v3-durable-spi/CompileNegative'
        run('public-typecheck-control',common+['-typecheck',str(negatives/'public-positive.swift')],'Positive non-SPI import control')
        fragments={'public-offer':'cannot find type','public-retained':'cannot find type','public-method':'inaccessible',
            'offer-constructor':'inaccessible','retained-constructor':'inaccessible','offer-decoder':"conform to 'Decodable'",'retained-decoder':"conform to 'Decodable'",
            'retained-as-artifact':"to expected argument type 'VerifiedArtifactV3'",'offer-as-retained':"to expected argument type 'RetainedHealthyEvidenceV3'",
            'private-context':'inaccessible','no-artifact-getter':"has no member 'artifact'",'immutable-snapshot':"is a 'let' constant"}
        for name,fragment in fragments.items():run('reject-'+name,common+['-typecheck',str(negatives/(name+'.swift'))],'Intentional external public/SPI opacity rejection',expected=1,diagnostic=fragment)
        run('spi-tsan',base+['-c','debug','--sanitize','thread','--filter','durableV3'],'14new functions incl32 concurrent immutable verification calls under Swift/C-shim TSan',tests=14)
        ios=run('iphoneos-sdk',['xcrun','--sdk','iphoneos','--show-sdk-path'],'Observed official iOS SDK').decode().strip()
        sim=run('simulator-sdk',['xcrun','--sdk','iphonesimulator','--show-sdk-path'],'Observed official simulator SDK').decode().strip()
        run('android-sdk-list',[OFFICIAL,'sdk','list','--swift-sdks-path','/Users/andreyyurlov/.swiftpm/swift-sdks'],'Observed installed official Swift SDKs',env=official)
        crosses=[('ios',['swift','build','--triple','arm64-apple-ios17.0','--sdk',ios],apple),
                 ('simulator',['swift','build','--triple','arm64-apple-ios17.0-simulator','--sdk',sim],apple),
                 ('android',[OFFICIAL,'build','--swift-sdks-path','/Users/andreyyurlov/.swiftpm/swift-sdks','--swift-sdk','aarch64-unknown-linux-android28'],official)]
        artifacts={}
        for target,cmd,env in crosses:
            scratch=work/(target+'-module')
            run(target+'-module',cmd+['--package-path',str(source/'updates'),'--scratch-path',str(scratch),'-c','release','--target','MixerUpdates','-Xswiftc','-warnings-as-errors'],'Official SDK MixerUpdates module/object compile, no final app/device',env=env)
            modules=sorted(p for p in scratch.rglob('*.swiftmodule') if p.is_file() and (p.name=='MixerUpdates.swiftmodule' or p.parent.name=='MixerUpdates.swiftmodule'))
            objects=sorted(p for p in scratch.rglob('*.o') if p.name in ['MixerUpdates.o','VerifierV3.o','VerifierV3.swift.o'])
            require(modules and objects,target+' expected module/object outputs')
            artifacts[target]=[{'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(set(modules+objects))]
        artifacts['host']=[{'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in [consumer,oldconsumer]]
        unchanged();receipt.update(status='scoped metadata SPI qualification passed; independent review pending',completed_at=utc(),artifacts=artifacts,source_and_export_unchanged=True)
    except BaseException as e:
        receipt.update(status='failed check preserved',completed_at=utc(),problem=str(e));save();raise
    save();print(json.dumps({'source_manifest_sha256':sha(manifest),'receipt_sha256':sha((out/'receipt.json').read_bytes())}))

if __name__=='__main__':main()
