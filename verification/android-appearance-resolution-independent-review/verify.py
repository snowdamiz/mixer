#!/usr/bin/env python3
"""Freeze review inputs; execute independent corpus in Swift Debug/Release and Java."""
import datetime, gzip, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
name=sys.argv[1] if len(sys.argv)>1 else 'candidate-1'
assert re.fullmatch(r'candidate-[1-9][0-9]*',name)
OUT=HERE/name;INPUTS=OUT/'inputs';BUILD=OUT/'.build'
assert not OUT.exists(),'Retain previous attempts and choose another candidate'
INPUTS.mkdir(parents=True);BUILD.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
producer=json.loads((ROOT/'verification/android-appearance-resolution/candidate-3/receipt.json').read_bytes())
assert producer['status']=='passed'
assert producer['source_manifest_sha256']==sha(json.dumps(producer['source_manifest'],sort_keys=True).encode())
paths=list(producer['source_manifest'])+['mixer-product-plan.md','verification/android-appearance-resolution/README.md','verification/android-appearance-resolution/handoff-summary.json','verification/android-appearance-resolution/candidate-3/receipt.json']
paths += [str(p.relative_to(ROOT)) for p in sorted(HERE.glob('*')) if p.is_file()]
manifest={}
for p in paths:
    data=(ROOT/p).read_bytes();manifest[p]=sha(data)
    if p in producer['source_manifest']:assert manifest[p]==producer['source_manifest'][p],p
    dest=INPUTS/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
assert manifest['native/android/app/src/dev/mixer/android/AppearanceResolutionV1.java']=='c3737cbd05d71fb13cd4e105a212b67c946c4ebc9fbf020ba2e9bf5ceccf2934'
assert manifest['sdk/Sources/MixerUI/AppearanceResolutionV1.swift']=='cbaaeebad2ef3c4015ab4f917df3a35ed68541e52b8b12c8a27a3be07211fcf0'
producerBindings={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted((ROOT/'verification/android-appearance-resolution/candidate-3').rglob('*')) if p.is_file() and '.build' not in p.parts}
(OUT/'producer-evidence-bindings.json').write_text(json.dumps(producerBindings,indent=2,sort_keys=True)+'\n')
for label in ['debug','release']:
    for field in ['sha256','values_sha256']:
        filename=label+'-oracle'+('.tsv.gz' if field=='sha256' else '.values.jsonl.gz')
        assert sha(gzip.decompress((ROOT/'verification/android-appearance-resolution/candidate-3'/filename).read_bytes()))==producer[label+'_oracle'][field]
assert producer['debug_oracle']==producer['release_oracle']
assert all(c['exit_code']==0 for c in producer['commands'])
for c in producer['commands']:
    assert sha((ROOT/c['output']).read_bytes())==c['output_sha256']
receipt={'status':'running','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'Independent host-only immutable Android appearance data review. No native widget consumption, resource/file/font validation, ART, UI/render parity, signed installation, physical devices, FieldLog publication or GA authority.',
 'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'source_manifest':manifest,'source_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),
 'producer_evidence_files_bound':len(producerBindings),'producer_source_inputs_rechecked':len(producer['source_manifest']),
 'commands':[]}
def save():(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv,cwd=INPUTS):
    started=time.monotonic();p=subprocess.run([str(x) for x in argv],cwd=cwd,env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=OUT/(name+'.log');log.write_bytes(p.stdout)
    receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'cwd':str(cwd),'exit_code':p.returncode,'seconds':time.monotonic()-started,'output':str(log.relative_to(ROOT)),'output_sha256':sha(p.stdout)})
    save();print(name,p.returncode,p.stdout.decode(errors='replace')[-1800:],flush=True)
    if p.returncode:raise RuntimeError(name+' failed')
    return p.stdout
def archive(path,destination):
    data=path.read_bytes();target=OUT/destination;target.write_bytes(gzip.compress(data,mtime=0))
    return {'bytes':len(data),'sha256':sha(data),'archive_sha256':sha(target.read_bytes())}
save()
try:
    jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
    run('python-version',['python3','--version']);run('java-version',[jdk/'java','-version']);run('javac-version',[jdk/'javac','-version']);run('swift-version',['swiftc','--version']);run('xcode-version',['xcodebuild','-version'])
    relative=HERE.relative_to(ROOT);review=INPUTS/relative
    cases=BUILD/'cases.jsonl';run('generate-review-cases',['python3','-B',review/'make_review_cases.py',cases])
    receipt['corpus']=archive(cases,'cases.jsonl.gz');receipt['corpus']['cases']=len(cases.read_bytes().splitlines());save()
    java=[INPUTS/'native/android/app/src/dev/mixer/android'/p for p in ['Json.java','UiPacket.java','AppearanceDescriptorV1.java','AppearanceResolutionV1.java']]
    run('javac',[jdk/'javac','--release','17','-Xlint:all','-Werror','-d',BUILD/'classes',*java,review/'ReviewProbe.java',INPUTS/'native/android/tests/AppearanceResolutionTests.java'])
    classPaths=sorted((BUILD/'classes').rglob('*.class'));majors={int.from_bytes(p.read_bytes()[6:8],'big') for p in classPaths};assert majors=={61}
    receipt['java_class_major_versions']=sorted(majors);receipt['java_class_count']=len(classPaths)
    oracleOutputs=[];actualOutputs=[]
    for mode,flags in [('debug',['-Onone','-g']),('release',['-O'])]:
        modules=BUILD/mode;modules.mkdir()
        for component,dependencies in [('MixerCore',[]),('MixerUI',['-I',modules,'-L',modules,'-lMixerCore'])]:
            sources=sorted((INPUTS/'sdk/Sources'/component).glob('*.swift'))
            run('swift-'+mode+'-'+component,['swiftc','-swift-version','6','-warnings-as-errors','-parse-as-library',*flags,'-emit-module','-emit-library','-module-name',component,'-emit-module-path',modules/(component+'.swiftmodule'),*dependencies,*sources,'-o',modules/('lib'+component+'.dylib')])
        executable=modules/'oracle'
        run('swift-'+mode+'-oracle-compile',['swiftc','-swift-version','6','-warnings-as-errors','-parse-as-library',*flags,'-I',modules,'-L',modules,'-lMixerCore','-lMixerUI','-Xlinker','-rpath','-Xlinker',modules,review/'ReviewOracle.swift','-o',executable])
        oracle=BUILD/(mode+'-oracle.tsv');run('swift-'+mode+'-oracle',[executable,cases,oracle]);oracleOutputs.append(oracle.read_bytes())
        receipt[mode+'_oracle']={'tsv':archive(oracle,mode+'-oracle.tsv.gz'),'values':archive(Path(str(oracle)+'.values.jsonl'),mode+'-oracle.values.jsonl.gz')};save()
        for execution,options in [('default',[]),('interpreted',['-Xint'])]:
            actual=BUILD/(mode+'-'+execution+'.jsonl')
            run('java-'+mode+'-'+execution,[jdk/'java',*options,'-cp',BUILD/'classes','dev.mixer.android.ReviewProbe',oracle,actual])
            run('contract-'+mode+'-'+execution,['python3','-B',review/'check_review_outputs.py',cases,oracle,actual])
            actualOutputs.append(actual.read_bytes());receipt[mode+'_'+execution]=archive(actual,mode+'-'+execution+'.jsonl.gz');save()
    assert oracleOutputs[0]==oracleOutputs[1],'Swift Debug/Release differ'
    assert all(x==actualOutputs[0] for x in actualOutputs),'Java mode outputs differ'
    for p,digest in manifest.items():assert sha((ROOT/p).read_bytes())==sha((INPUTS/p).read_bytes())==digest,p
    for p,digest in producerBindings.items():assert sha((ROOT/p).read_bytes())==digest,p
    receipt['unchanged_source_checks']=2*len(manifest);receipt['unchanged_producer_evidence_checks']=len(producerBindings)
    receipt['swift_debug_release_equal']=True;receipt['all_java_mode_outputs_equal']=True
    receipt['compiled_artifacts']={str(p.relative_to(OUT)):sha(p.read_bytes()) for p in sorted(BUILD.rglob('*')) if p.is_file() and (p.suffix in ['.class','.swiftmodule','.dylib'] or p.name=='oracle')}
    receipt['status']='passed'
except BaseException as e:
    receipt['status']='failed';receipt['failure']=repr(e);raise
finally:
    receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
