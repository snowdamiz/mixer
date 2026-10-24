"""Compile the committed complete Android Java closure without device access."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = HERE / 'build/dex'
OUT = HERE / 'dex-compile'
BUILD.mkdir(parents=True, exist_ok=False)
OUT.mkdir(exist_ok=False)
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
D8 = SDK / 'build-tools/37.0.0/d8'
JAR = SDK / 'platforms/android-37.0/android.jar'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
names = subprocess.check_output(['git','ls-tree','-r','--name-only',revision,'--','native/android/app/src'],cwd=ROOT,text=True).splitlines()
manifest = {}
sources = []
for name in names:
    if not name.endswith('.java'):
        continue
    data = subprocess.check_output(['git','show',revision+':'+name],cwd=ROOT)
    path = BUILD / 'source' / name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    manifest[name] = sha(path)
    sources.append(path)
env = dict(os.environ, JAVA_HOME=str(JDK), PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'])
commands = []
status = 'failed'
def run(name, argv):
    p = subprocess.run(list(map(str,argv)),cwd=BUILD,env=env,capture_output=True,text=True,timeout=120)
    log = OUT / (name+'.log')
    log.write_text(p.stdout+p.stderr)
    commands.append(dict(name=name,argv=list(map(str,argv)),cwd=str(BUILD),exit=p.returncode,log=str(log.relative_to(ROOT)),sha256=sha(log)))
    print(name,p.returncode,flush=True)
    if p.returncode:
        raise RuntimeError(log.read_text()[-4000:])
try:
    run('javac-version',[JDK/'bin/javac','--version'])
    run('d8-version',[D8,'--version'])
    (BUILD/'classes').mkdir(); (BUILD/'dex').mkdir()
    run('compile-java',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-classpath',JAR,'-d',BUILD/'classes',*sources])
    run('compile-dex',[D8,'--min-api','28','--lib',JAR,'--output',BUILD/'dex',*sorted((BUILD/'classes').rglob('*.class'))])
    status='passed-android-java-dex-compile'
finally:
    for name,digest in manifest.items():
        assert sha(BUILD/'source'/name)==digest
    artifacts={str(p.relative_to(HERE)):sha(p) for suffix in ['*.class','*.dex'] for p in BUILD.rglob(suffix)}
    receipt=dict(status=status,sourceRevision=revision,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 sourceManifest=manifest,commands=commands,artifacts=artifacts,
                 androidJarSHA256=sha(JAR),d8JarSHA256=sha(SDK/'build-tools/37.0.0/lib/d8.jar'),
                 collectorSHA256=sha(Path(__file__)),scope='Complete committed Java application sources compiled with Android API37 library and D8 minimum API28, including V2 data types. No app execution, native appearance consumption, install/device, signing or GA proof.')
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(status,len(manifest),'sources',len(artifacts),'artifacts',flush=True)
