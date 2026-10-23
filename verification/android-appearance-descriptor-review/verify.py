#!/usr/bin/env python3
"""Snapshot and independently qualify only the private descriptor data reader."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,time
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OUT=HERE/'candidate-1';INPUTS=OUT/'inputs';BUILD=OUT/'build'
assert not OUT.exists(), 'Preserve completed/failed attempts.'
INPUTS.mkdir(parents=True);BUILD.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
paths=['native/android/app/src/dev/mixer/android/AppearanceDescriptorV1.java','native/android/tests/AppearanceDescriptorTests.java',*[f'sdk/Sources/MixerUI/Appearance{x}V1.swift' for x in ['Values','Descriptor','MetricMath','Default']], 'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json','verification/ui-shared-appearance-contract/v2/descriptor-schema.json','verification/ui-shared-appearance-contract/v2/foundation-seam.md','docs/ui-shared-appearance-contract.md',*[str((HERE/f).relative_to(ROOT)) for f in ['IndependentProbe.java','IndependentSwiftProbe.swift','generate_cases.py','verify.py']]]
manifest={p:sha((ROOT/p).read_bytes()) for p in paths}
for p in paths:dest=INPUTS/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dest)
receipt={'scope':'Independent Java/Swift host-only descriptor acceptance, retained-data parity and immutable ownership review. No Android runtime, renderer, native resources/fonts, installed authority, devices, store, release or GA qualification.','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_manifest':manifest,'source_manifest_sha256':sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':[],'status':'running'}
def save():(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,args,cwd=INPUTS):
    started=time.monotonic();proc=subprocess.run([str(a) for a in args],cwd=cwd,env={**os.environ,'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log=OUT/(name+'.log');log.write_bytes(proc.stdout)
    receipt['commands'].append(dict(name=name,argv=[str(a) for a in args],cwd=str(cwd),exit_code=proc.returncode,seconds=time.monotonic()-started,output=str(log.relative_to(ROOT)),output_sha256=sha(proc.stdout)));save();print(name,proc.returncode,proc.stdout.decode(errors='replace')[-800:],flush=True)
    if proc.returncode:receipt['status']='failed';save();raise SystemExit(1)
    return proc.stdout
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
for name,args in [('java-version',[jdk/'java','-version']),('javac-version',[jdk/'javac','-version']),('swift-version',['swiftc','--version']),('xcode-version',['xcodebuild','-version']),('python-version',['python3','--version'])]:run(name,args)
run('generate-cases',['python3','-B',INPUTS/'verification/android-appearance-descriptor-review/generate_cases.py',INPUTS,OUT])
java=[INPUTS/'native/android/app/src/dev/mixer/android/AppearanceDescriptorV1.java',INPUTS/'verification/android-appearance-descriptor-review/IndependentProbe.java',INPUTS/'native/android/tests/AppearanceDescriptorTests.java']
run('javac',[jdk/'javac','--release','17','-Xlint:all','-Werror','-d',BUILD/'classes',*java])
for label,flags in [('java-default',[]),('java-interpreted',['-Xint'])]:
    run(label,[jdk/'java',*flags,'-cp',BUILD/'classes','dev.mixer.android.IndependentProbe',BUILD/'cases.tsv'])
run('java-product-tests',[jdk/'java','-cp',BUILD/'classes','dev.mixer.android.AppearanceDescriptorTests',BUILD/'cases.tsv'])
swift=[INPUTS/p for p in paths if p.endswith('.swift')]
for label,flags in [('debug',['-Onone','-g']),('release',['-O'])]:
    exe=BUILD/('swift-'+label);run('swift-compile-'+label,['swiftc','-swift-version','6','-warnings-as-errors','-parse-as-library',*flags,*swift,'-o',exe]);run('swift-run-'+label,[exe,BUILD/'cases.tsv'])
for p,digest in manifest.items():assert sha((ROOT/p).read_bytes())==sha((INPUTS/p).read_bytes())==digest,p
receipt['unchanged_source_checks']=2*len(manifest);receipt['corpus']={p:sha((OUT/p).read_bytes()) for p in ['independent-corpus.json.gz','cases.tsv.gz']};receipt['status']='passed';receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
