#!/usr/bin/env python3
"""Freeze and run data-only Java/Swift parity. Does not access physical devices."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,shutil,subprocess,time
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OUT=HERE/'candidate-1';INPUTS=OUT/'inputs';BUILD=OUT/'build'
assert not OUT.exists(), 'Preserve completed or failed attempts; choose a new candidate.'
INPUTS.mkdir(parents=True);BUILD.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
paths=['native/android/app/src/dev/mixer/android/AppearanceDescriptorV1.java','native/android/tests/AppearanceDescriptorTests.java',*[f'sdk/Sources/MixerUI/Appearance{x}V1.swift' for x in ['Values','Descriptor','MetricMath','Default']], 'verification/android-appearance-descriptor/SwiftDecodeProbe.swift','verification/android-appearance-descriptor/make_cases.py','verification/android-appearance-descriptor/qualify.py','verification/ui-appearance-foundation/design-corpus.json','verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json','verification/ui-shared-appearance-contract/v2/descriptor-schema.json','verification/ui-appearance-foundation-review/candidate-2/independent-corpus.json.gz']
manifest={}
for path in paths:
 data=(ROOT/path).read_bytes();manifest[path]=sha(data);dest=INPUTS/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
receipt={'scope':'Private Android immutable descriptor data reader only. Java17 strict compilation, Java default/interpreted runs, Swift Debug/Release data-codec parity; no Android runtime, resources/fonts/widgets/rendering, installed authority, JNI, physical parity, release or GA qualification.','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_manifest':manifest,'source_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':[],'status':'running'}
def save(): (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv,cwd=INPUTS):
 start=time.monotonic();p=subprocess.run([str(x) for x in argv],cwd=cwd,env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 path=OUT/(name+'.log');path.write_bytes(p.stdout);receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'cwd':str(cwd),'exit_code':p.returncode,'seconds':time.monotonic()-start,'output':str(path.relative_to(ROOT)),'output_sha256':sha(p.stdout)});save();print(name,p.returncode,p.stdout.decode(errors='replace')[-400:],flush=True)
 if p.returncode:raise SystemExit(1)
 return p.stdout
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
run('java-version',[jdk/'java','-version']);run('javac-version',[jdk/'javac','-version']);run('swift-version',['swiftc','--version']);run('xcode-version',['xcodebuild','-version']);run('python-version',['python3','--version'])
run('generate-cases',['python3','-B',INPUTS/'verification/android-appearance-descriptor/make_cases.py'])
cases=(INPUTS/'verification/android-appearance-descriptor/cases.tsv').read_bytes()
root_cases=json.loads((INPUTS/'verification/android-appearance-descriptor/cases.json').read_text())
review_cases=json.loads(gzip.decompress((INPUTS/'verification/ui-appearance-foundation-review/candidate-2/independent-corpus.json.gz').read_bytes()))
for i,case in enumerate(review_cases):
 name=case['name'].replace('\t',' ').replace('\n',' ')
 cases+=f"independent-{i}-{name}\t{int(case['accepted'])}\t{case['base64']}\n".encode('ascii')
case_file=BUILD/'cases.tsv';case_file.write_bytes(cases)
(OUT/'cases.tsv.gz').write_bytes(gzip.compress(cases,mtime=0));receipt['corpus']={'root_cases':len(root_cases),'independent_cases':len(review_cases),'total':len(root_cases)+len(review_cases),'accepted':sum(c['accepted'] for c in root_cases+review_cases),'sha256':sha(cases),'archive_sha256':sha((OUT/'cases.tsv.gz').read_bytes()),'independent_source':'verification/ui-appearance-foundation-review/candidate-2/independent-corpus.json.gz'}
# Generated uncompressed case files are transient; the exact combined corpus is archived.
(INPUTS/'verification/android-appearance-descriptor/cases.tsv').unlink();(INPUTS/'verification/android-appearance-descriptor/cases.json').unlink()
java_sources=[INPUTS/p for p in paths if p.endswith('.java')]
run('javac',[jdk/'javac','--release','17','-Xlint:all','-Werror','-d',BUILD/'classes',*java_sources])
for name,flags in [('java-default',[]),('java-interpreted',['-Xint'])]:run(name,[jdk/'java',*flags,'-cp',BUILD/'classes','dev.mixer.android.AppearanceDescriptorTests',case_file])
swift_sources=[INPUTS/p for p in paths if p.endswith('.swift')]
for mode,flags in [('debug',['-Onone','-g']),('release',['-O'])]:
 exe=BUILD/('swift-'+mode)
 run('swift-compile-'+mode,['swiftc','-swift-version','6','-warnings-as-errors','-parse-as-library',*flags,*swift_sources,'-o',exe])
 run('swift-run-'+mode,[exe,case_file])
for path,digest in manifest.items():assert sha((ROOT/path).read_bytes())==sha((INPUTS/path).read_bytes())==digest,path
receipt['unchanged_source_checks']=2*len(manifest);receipt['status']='passed';receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
