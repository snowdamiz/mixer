#!/usr/bin/env python3
"""Additional constructor probe independent of the oracle's JSON transport."""
import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'environment-1';OUT.mkdir();BUILD=OUT/'.build';BUILD.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
paths=[HERE/'EnvironmentProbe.java',HERE/'verify_environment.py']+[HERE/'candidate-1/inputs/native/android/app/src/dev/mixer/android'/p for p in ['Json.java','UiPacket.java','AppearanceDescriptorV1.java','AppearanceResolutionV1.java']]
manifest={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
inputs=OUT/'inputs'
for p in paths:
    dest=inputs/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
receipt={'status':'running','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_manifest':manifest,'source_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),
 'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'scope':'Direct Java typed environment admission only. Host JDK; no ART, emulator, device or native UI authority.','commands':[]}
def save():(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv):
    start=time.monotonic();p=subprocess.run([str(x) for x in argv],cwd=inputs,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=os.environ)
    log=OUT/(name+'.log');log.write_bytes(p.stdout);receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'cwd':str(inputs),'exit_code':p.returncode,'seconds':time.monotonic()-start,'output':str(log.relative_to(ROOT)),'output_sha256':sha(p.stdout)})
    save();print(name,p.returncode,p.stdout.decode(),flush=True);assert p.returncode==0
save()
try:
    jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin')
    run('java-version',[jdk/'java','-version']);run('javac-version',[jdk/'javac','-version']);run('python-version',['python3','--version'])
    run('javac',[jdk/'javac','--release','17','-Xlint:all','-Werror','-d',BUILD/'classes',*[inputs/p.relative_to(ROOT) for p in paths if p.suffix=='.java']])
    run('java-default',[jdk/'java','-cp',BUILD/'classes','dev.mixer.android.EnvironmentProbe'])
    run('java-interpreted',[jdk/'java','-Xint','-cp',BUILD/'classes','dev.mixer.android.EnvironmentProbe'])
    receipt['classes']={str(p.relative_to(OUT)):sha(p.read_bytes()) for p in sorted((BUILD/'classes').rglob('*.class'))}
    assert all(int.from_bytes(p.read_bytes()[6:8],'big')==61 for p in (BUILD/'classes').rglob('*.class'))
    for path,digest in manifest.items():assert sha((ROOT/path).read_bytes())==sha((inputs/path).read_bytes())==digest
    receipt['unchanged_source_checks']=2*len(manifest);receipt['status']='passed'
except BaseException as e:
    receipt['status']='failed';receipt['failure']=repr(e);raise
finally:
    receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
