#!/usr/bin/env python3
"""Freeze owned data resolver and public Swift oracle; no device access."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
name=sys.argv[1] if len(sys.argv)>1 else 'candidate-1'
assert name.startswith('candidate-') and '/' not in name
OUT=HERE/name;INPUTS=OUT/'inputs';BUILD=OUT/'.build'
assert not OUT.exists(),'Preserve previous attempts; select a fresh candidate.'
INPUTS.mkdir(parents=True);BUILD.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
paths=['AGENTS.md','docs/ui-appearance-resolution-v1.md','docs/ui-shared-appearance-contract.md','docs/android-appearance-resolution-v1.md',
'native/android/app/src/dev/mixer/android/AppearanceDescriptorV1.java','native/android/app/src/dev/mixer/android/AppearanceResolutionV1.java',
'native/android/app/src/dev/mixer/android/UiPacket.java','native/android/app/src/dev/mixer/android/Json.java','native/android/tests/AppearanceResolutionTests.java',
'verification/android-appearance-resolution/SwiftOracle.swift','verification/android-appearance-resolution/make_cases.py','verification/android-appearance-resolution/verify.py',
'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json','verification/ui-appearance-resolution-root-review/acceptance.json']
paths += [str(p.relative_to(ROOT)) for component in ['MixerCore','MixerUI'] for p in sorted((ROOT/'sdk/Sources'/component).glob('*.swift'))]
manifest={}
for path in paths:
    data=(ROOT/path).read_bytes();manifest[path]=sha(data);dest=INPUTS/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
receipt={'status':'running','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
'scope':'Private immutable Android appearance data only; complete Swift public API differential on actual reconciler packets, excluding named existing packet-admission boundaries. No native widgets, resources/fonts, signed installation, display, geometry/raster, devices, release, FieldLog or GA authority.',
'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
'source_manifest':manifest,'source_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'commands':[]}
def save():(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv,cwd=INPUTS):
    started=time.monotonic();p=subprocess.run([str(v) for v in argv],cwd=cwd,env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=OUT/(name+'.log');log.write_bytes(p.stdout);receipt['commands'].append({'name':name,'argv':[str(v) for v in argv],'cwd':str(cwd),'exit_code':p.returncode,'seconds':time.monotonic()-started,'output':str(log.relative_to(ROOT)),'output_sha256':sha(p.stdout)});save()
    print(name,p.returncode,p.stdout.decode(errors='replace')[-1200:],flush=True)
    if p.returncode:raise RuntimeError(name+' failed')
    return p.stdout
save()
try:
    jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
    run('python-version',['python3','--version']);run('java-version',[jdk/'java','-version']);run('javac-version',[jdk/'javac','-version']);run('swift-version',['swiftc','--version']);run('xcode-version',['xcodebuild','-version'])
    cases=BUILD/'cases.jsonl';run('generate-cases',['python3','-B',INPUTS/'verification/android-appearance-resolution/make_cases.py',cases])
    raw=cases.read_bytes();(OUT/'cases.jsonl.gz').write_bytes(gzip.compress(raw,mtime=0))
    receipt['corpus']={'cases':len(raw.splitlines()),'sha256':sha(raw),'archive_sha256':sha((OUT/'cases.jsonl.gz').read_bytes())};save()
    java=[INPUTS/p for p in paths if p.endswith('.java')]
    run('javac',[jdk/'javac','--release','17','-Xlint:all','-Werror','-d',BUILD/'classes',*java])
    oracle_bytes=[]
    for mode,flags in [('debug',['-Onone','-g']),('release',['-O'])]:
        modules=BUILD/mode;modules.mkdir()
        for component,dependencies in [('MixerCore',[]),('MixerUI',['-I',modules,'-L',modules,'-lMixerCore'])]:
            sources=sorted((INPUTS/'sdk/Sources'/component).glob('*.swift'))
            run('swift-'+mode+'-'+component,['swiftc','-swift-version','6','-warnings-as-errors','-parse-as-library',*flags,'-emit-module','-emit-library','-module-name',component,'-emit-module-path',modules/(component+'.swiftmodule'),*dependencies,*sources,'-o',modules/('lib'+component+'.dylib')])
        executable=modules/'oracle'
        run('swift-'+mode+'-oracle-compile',['swiftc','-swift-version','6','-warnings-as-errors','-parse-as-library',*flags,'-I',modules,'-L',modules,'-lMixerCore','-lMixerUI','-Xlinker','-rpath','-Xlinker',modules,INPUTS/'verification/android-appearance-resolution/SwiftOracle.swift','-o',executable])
        oracle=BUILD/(mode+'-oracle.tsv');run('swift-'+mode+'-oracle',[executable,cases,oracle])
        values=Path(str(oracle)+'.values.jsonl').read_bytes();(OUT/(mode+'-oracle.values.jsonl.gz')).write_bytes(gzip.compress(values,mtime=0))
        data=oracle.read_bytes();oracle_bytes.append(data);(OUT/(mode+'-oracle.tsv.gz')).write_bytes(gzip.compress(data,mtime=0))
        receipt[mode+'_oracle']={'values_sha256':sha(values),'values_archive_sha256':sha((OUT/(mode+'-oracle.values.jsonl.gz')).read_bytes()),'sha256':sha(data),'archive_sha256':sha((OUT/(mode+'-oracle.tsv.gz')).read_bytes())};save()
        for execution,options in [('default',[]),('interpreted',['-Xint'])]:
            run('java-'+mode+'-'+execution,[jdk/'java',*options,'-cp',BUILD/'classes','dev.mixer.android.AppearanceResolutionTests',oracle])
    assert oracle_bytes[0]==oracle_bytes[1],'Swift Debug/Release oracle mismatch'
    for path,digest in manifest.items():assert sha((ROOT/path).read_bytes())==sha((INPUTS/path).read_bytes())==digest,path
    receipt['unchanged_source_checks']=2*len(manifest);receipt['swift_debug_release_equal']=True;receipt['status']='passed'
except BaseException as error:
    receipt['status']='failed';receipt['failure']=repr(error);raise
finally:
    receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
