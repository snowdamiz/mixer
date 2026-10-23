#!/usr/bin/env python3
"""Consume immutable qualified host module and existing cross dependency modules."""
import argparse, datetime, hashlib, json, os, re, subprocess, time
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def need(ok,message):
    if not ok:raise RuntimeError(message)
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--candidate',required=True);a=p.parse_args()
    need(re.fullmatch('[a-z0-9-]{1,64}',a.name),'bounded name')
    out=HERE/a.name;out.mkdir(exist_ok=False);work=HERE/'.build'/a.name;work.mkdir(exist_ok=False)
    proof=HERE/a.candidate/'receipt.json';candidate=json.loads(proof.read_text());source=Path(candidate['export'])
    need(candidate['status']=='scoped tests passed; independent review pending','successful frozen candidate')
    depfile=Path(candidate['dependency_receipt']['path']);dep=json.loads(depfile.read_text());depbase=Path(dep['export']).parent;native=Path(candidate['native_directory'])
    own=['supplemental.py','PublicEmbedding.swift','Opacity.swift','OpacityInvoke.swift','OpacitySelection.swift'];owned={n:sha(HERE/n) for n in own}
    for name in own:(out/name).write_bytes((HERE/name).read_bytes())
    receipt={'status':'running','began_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_receipt':{'path':str(proof),'sha256':sha(proof)},'candidate_source_manifest_sha256':candidate['source_manifest_sha256'],'source_files':candidate['source_files'],'supplemental_files':owned,'commands':[],'artifacts':{},'dependency_inputs':{},'scope':'Public ordinary-import consumer link/run, three opacity negatives, official target-only iOS/Android module+object compile using immutable composed sources and retained dependency modules. No package graph/native rebuild/device/UI observation.'}
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def unchanged():
        need(sha(proof)==receipt['candidate_receipt']['sha256'],'candidate receipt unchanged')
        for name,digest in candidate['source_files'].items():need(sha(source/name)==digest,'composed source '+name)
        for name,digest in owned.items():need(sha(HERE/name)==digest,'supplemental source '+name)
        for name,digest in receipt['dependency_inputs'].items():need(sha(Path(name))==digest,'dependency module '+name)
    def record(path):
        path=Path(path)
        if path.is_file():receipt['dependency_inputs'][str(path)]=sha(path)
    def run(name,cmd,expected=0,env=None,timeout=120):
        unchanged();start=time.monotonic();environment=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}|(env or {})
        try:r=subprocess.run(cmd,cwd=source,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);raw,code=r.stdout,r.returncode
        except subprocess.TimeoutExpired as e:raw,code=(e.stdout or b'')+b'\ncommand timeout\n',124
        log=out/(name+'.log');log.write_bytes(raw);receipt['commands'].append({'name':name,'command':cmd,'cwd':str(source),'environment':{'DEVELOPER_DIR':environment['DEVELOPER_DIR']},'exit_code':code,'expected_exit':expected,'seconds':time.monotonic()-start,'log':log.name,'log_sha256':sha(log)});save();print(name,code,flush=True)
        need(code==expected,name+' failed (preserved log)');unchanged();return raw
    try:
        for mode in ['debug','release']:
            current=Path(candidate['artifacts'][mode]['module']['path']).parent
            products=Path(candidate['retained_products'][mode]['directory'])/'products';maps=products.parent/'modulemaps'
            flags=['swiftc','-parse-as-library','-swift-version','6','-warnings-as-errors','-I',str(current),'-I',str(products)]
            for name in ['CMixerVMCapability','MixerCapabilityDurableIO','MixerCapabilityIO','MixerDurableIO']:
                path=maps/(name+'.modulemap');record(path);flags+=['-Xcc','-fmodule-map-file='+str(path)]
            flags+=['-Xcc','-I'+str(native/'include')]
            for path in current.glob('*'):record(path)
            if mode=='release':flags+=['-O']
            binary=work/(mode+'-public');run(mode+'-public-link',flags+[str(out/'PublicEmbedding.swift'),'-L',str(current),'-lMixerCapabilityActivationColdStart','-Xlinker','-rpath','-Xlinker',str(current),'-o',str(binary)])
            userdir=work/(mode+'-private');userdir.mkdir();fixtures=source/'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures'
            run(mode+'-public-run',[str(binary),str(fixtures),str(userdir)]);receipt['artifacts'][mode+'-public']={'path':str(binary),'sha256':sha(binary)};save()
            for name,diagnostic in [('Opacity.swift',b'argument'),('OpacityInvoke.swift',b'no member'),('OpacitySelection.swift',b'cannot find')]:
                raw=run(mode+'-'+name.removesuffix('.swift').lower(),flags+['-typecheck',str(out/name)],expected=1)
                need(diagnostic in raw,'expected opacity diagnostic '+name)
        swift_sources=sorted(str(p) for p in (source/'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
        ios=depbase/'ios/out';products=ios/'Products/Release-iphoneos';maps=ios/'Intermediates.noindex/GeneratedModuleMaps'
        flags=['swiftc','-swift-version','6','-warnings-as-errors','-parse-as-library','-O','-whole-module-optimization','-target','arm64-apple-ios17.0','-sdk',subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip(),'-I',str(products),'-Xcc','-I'+str(native/'include')]
        for directory in products.glob('*.swiftmodule'):
            if directory.name!='MixerCapabilityActivation.swiftmodule':
                for file in directory.rglob('*'):record(file)
        for name in ['CMixerVMCapability','MixerCapabilityDurableIO','MixerCapabilityIO','MixerDurableIO']:
            path=maps/(name+'.modulemap');record(path);flags+=['-Xcc','-fmodule-map-file='+str(path)]
        target=work/'ios';target.mkdir();run('ios-module-object',flags+['-module-name','MixerCapabilityActivation','-emit-module','-emit-module-path',str(target/'MixerCapabilityActivation.swiftmodule'),'-emit-object','-o',str(target/'MixerCapabilityActivation.o')]+swift_sources)
        android=depbase/'android/aarch64-unknown-linux-android28/release';desc=android/'description.json';record(desc)
        command=next(v for v in json.loads(desc.read_text())['swiftCommands'].values() if v.get('moduleName')=='MixerCapabilityActivation')
        args=command['otherArguments'];filtered=[];index=0
        while index<len(args):
            value=args[index]
            if value in ['-emit-objc-header-path','-module-cache-path','-num-threads','-j']:index+=2;continue
            if value in ['-emit-objc-header','-serialize-diagnostics','-parseable-output'] or re.fullmatch(r'-j\d+',value):index+=1;continue
            filtered.append(value);index+=1
        modules=android/'Modules'
        for path in modules.glob('*.swiftmodule'):
            if path.name!='MixerCapabilityActivation.swiftmodule':record(path)
        for index,value in enumerate(filtered):
            if value.startswith('-fmodule-map-file='):record(value.split('=',1)[1])
        target=work/'android';target.mkdir()
        run('official-swift-version',[command['executable'],'--version'],env={'DEVELOPER_DIR':'/Applications/Xcode_26.6.app/Contents/Developer'})
        run('android-module-object',[command['executable']]+filtered+['-num-threads','2','-module-cache-path',str(target/'module-cache'),'-I',str(modules),'-module-name','MixerCapabilityActivation','-emit-module','-emit-module-path',str(target/'MixerCapabilityActivation.swiftmodule'),'-emit-object','-o',str(target/'MixerCapabilityActivation.o')]+swift_sources,env={'DEVELOPER_DIR':'/Applications/Xcode_26.6.app/Contents/Developer'})
        for platform in ['ios','android']:
            receipt['artifacts'][platform]={str(p.relative_to(work/platform)):sha(p) for p in (work/platform).glob('*') if p.is_file()}
        receipt.update(status='scoped consumer/opacity/cross checks passed',completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_and_dependencies_unchanged=True)
    except Exception as error:receipt.update(status='failed experiment preserved',problem=str(error));save();raise
    save();print('RECEIPT',sha(out/'receipt.json'),flush=True)
if __name__=='__main__':main()
