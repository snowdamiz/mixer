#!/usr/bin/env python3
"""Replay captured starter packets against baseline and proposed production renderer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,default=Path.cwd())
parser.add_argument('--evidence',type=Path,required=True,help='New owned output directory')
parser.add_argument('--packet-dir',type=Path,help='Defaults to this checkout own production packet fixtures')
parser.add_argument('--overlay',type=Path,help='Optional candidate source overlay')
parser.add_argument('--baseline-root',type=Path,help='Optional explicit historical baseline checkout; omitted by default')
parser.add_argument('--java-home',type=Path,default=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
args=parser.parse_args()
root=args.root.resolve(); evidence=args.evidence.resolve(); overlay=args.overlay.resolve() if args.overlay else root; packets=args.packet_dir.resolve() if args.packet_dir else root/'native/android/tests/GeneratedAddTransitionPackets';jdk=args.java_home.resolve()
evidence.mkdir(parents=True,exist_ok=False);scratch=evidence/'scratch';scratch.mkdir();commands=[]
env=os.environ.copy()
for key in ['JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH']:env.pop(key,None)
env.update(JAVA_HOME=str(jdk),TMPDIR=str(scratch),JAVA_TOOL_OPTIONS='-XX:ActiveProcessorCount=2')
def run(name,argv):
    argv=list(map(str,argv));remaining=240-sum(c.get('seconds',0) for c in commands)
    if remaining<=0:raise RuntimeError('active command budget exhausted')
    with (evidence/(name+'.stdout')).open('wb') as out,(evidence/(name+'.stderr')).open('wb') as err:
        started=time.monotonic();p=subprocess.Popen(argv,cwd=root,env=env,stdout=out,stderr=err,start_new_session=True)
        row={'name':name,'argv':argv,'pid':p.pid,'pgid':p.pid};commands.append(row)
        (evidence/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        try:code=p.wait(timeout=min(55,remaining))
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,15);p.wait(timeout=10);raise
        row.update(exitCode=code,seconds=time.monotonic()-started)
        try:os.killpg(p.pid,0);row['groupAbsent']=False
        except ProcessLookupError:row['groupAbsent']=True
        (evidence/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        if code or not row['groupAbsent']:raise RuntimeError(name+' failed; inspect raw output')
        print(name+': PASS',flush=True)
def compile_sources(label,sources,classpath=''):
    classes=scratch/label;classes.mkdir()
    (evidence/(label+'-inputs.json')).write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2)+'\n')
    run(label+'-compile',[jdk/'bin/javac','-J-Xmx256m','-J-XX:ActiveProcessorCount=2','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath','','-classpath',classpath,'-d',classes,*sources]);return classes
passed=False
try:
    run('javac-version',[jdk/'bin/javac','-version']);run('java-version',[jdk/'bin/java','-version'])
    version=(evidence/'javac-version.stdout').read_text().strip()
    if not version.startswith('javac 25'):raise RuntimeError('JDK 25 compiler required: '+version)
    closure=json.loads((root/'native/android/tests/private-owner-host-roster.json').read_text())['closures']['B-concrete-renderer-views']
    production=closure['actual_production_sources']+['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']
    leaves=sorted((root/'native/android/tests/NativeOwnerV2ConcreteHostLeaves').rglob('*.java'))
    tests=[Path(__file__).resolve().with_name('GeneratedAddTransitionHostTests.java'),root/'native/android/tests/VerticalReflowHostTests.java']
    candidate_sources=None
    for label in (['baseline','candidate'] if args.baseline_root else ['candidate']):
        selected_root = args.baseline_root.resolve() if label == 'baseline' else root
        sources=[overlay/p if label=='candidate' and (overlay/p).exists() else selected_root/p for p in production]
        if label=='candidate':candidate_sources=sources
        classes=compile_sources(label,sources+leaves+tests)
        run(label+'-packets',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.GeneratedAddTransitionHostTests',packets,label])
        run(label+'-reflow',[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.VerticalReflowHostTests',root/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json','candidate'])
    compile_sources('sdk37',candidate_sources+[root/'native/android/app/src/dev/mixer/android/NativeBridge.java'],Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar'))
    passed=True
finally:
    absent=all(c.get('groupAbsent',False) for c in commands)
    if absent:shutil.rmtree(scratch)
    (evidence/'result.json').write_text(json.dumps({'passed':passed,'scratchRemoved':absent,'commandCount':len(commands),'scope':'Production Java closure B, controlled Android/JNI leaves, exact production C-entry packets; SDK37 source compile; no Android runtime or release qualification'},indent=2)+'\n')
