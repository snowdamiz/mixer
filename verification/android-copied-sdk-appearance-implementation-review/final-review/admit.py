#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, stat, shutil, tarfile

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
PRODUCER=ROOT/'verification/android-copied-sdk-appearance-implementation'
def identity(data): return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def main():
    pins={'handoff.json':'38a6452b9208f0a88ef5a7f745c88a2cc3356b94c6df601280ea42d630164636','members.json':'eeafe9198d06d3c57d9824b05f04da829114403f1e3f917c2b5b3ce4c35a6134','seal.sha256':'267e8a806dc2c22756f9e4ea100119bb457c493b830a83f737476fce60ee9077','owned-source-manifest.json':'417a7665fdf1fc32e4b6cc4bb163531447c703fa21aba1eaf2af148ab52b53f2'}
    assert not (OUT/'admission.json').exists()
    for name,pin in pins.items(): assert identity((PRODUCER/name).read_bytes())['sha256']==pin,name
    pre=ROOT/'verification/android-copied-sdk-appearance-implementation-review/preaccess'
    assert identity((pre/'seal.json').read_bytes())['sha256']=='a9554732573f2d6aa29c22e760bb15ff1fa2643c8507b6bccaca948b3683183c'
    ps=json.loads((pre/'seal.json').read_text())
    for name,expected in ps['files'].items(): assert identity((ROOT/name).read_bytes())==expected,name
    members=json.loads((PRODUCER/'members.json').read_text())
    for name,expected in members.items():
        path=PRODUCER/name; assert stat.S_ISREG(path.lstat().st_mode),name
        data=path.read_bytes(); assert identity(data)==expected,name
        dest=OUT/'producer-inputs'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    for name in ['members.json','seal.sha256']:
        shutil.copyfile(PRODUCER/name,OUT/'producer-inputs'/name)
    for name in ['implementation-preflight.json','implementation-selection.json']:
        shutil.copyfile(ROOT/'verification/android-copied-sdk-appearance-contract-root-review'/name,OUT/name)
    binding=json.loads((OUT/'producer-inputs/source-binding.json').read_text())
    for name,expected in binding['files'].items():
        data=(OUT/'producer-inputs/source-inputs'/name).read_bytes(); assert identity(data)==expected,name
        dest=OUT/'candidate'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    binaries=json.loads((OUT/'producer-inputs/host-compiled-binding.json').read_text())
    with tarfile.open(OUT/'producer-inputs/host-compiled-bindings.tar.gz') as archive:
        for name,expected in binaries.items():
            if not name.startswith(('cli-debug/','cli-release/')):continue
            member=archive.getmember(name);assert member.isfile();data=archive.extractfile(member).read()
            assert identity(data)==expected,name
            dest=OUT/'executables'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);dest.chmod(0o755)
            bundle=dest.parent/'MixerCLI_MixerBuild.bundle/Resources';bundle.mkdir(parents=True)
            shutil.copyfile(OUT/'candidate/cli/Sources/MixerBuild/Resources/android-build.py',bundle/'android-build.py')
    report={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'producer_members':len(members),'producer_bytes':sum(v['bytes'] for v in members.values()),'pins':pins,'source_binding_files':len(binding['files']),'preaccess_members_unchanged':len(ps['files']),'compiled_executables':{k:v for k,v in binaries.items() if k.startswith(('cli-debug/','cli-release/'))},'scope':'Exact copied candidate sources/resources and hash-bound producer-built Debug/Release executable artifacts; no producer helper executed.'}
    (OUT/'admission.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
