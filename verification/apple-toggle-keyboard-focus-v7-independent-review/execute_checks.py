#!/usr/bin/env python3
"""Bounded independent host-only review command recorder."""
import datetime
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P=ROOT/'verification/apple-toggle-keyboard-focus-v7-preparation'
DEVELOPER=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    attempt=sys.argv[1] if len(sys.argv)>1 else 'attempt-1'
    commands=[]
    output=HERE/'commands'/attempt
    output.mkdir(parents=True,exist_ok=False)
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','DEVELOPER_DIR':str(DEVELOPER),'MIXER_REVIEW_ATTEMPT':attempt}
    def command(name,argv,timeout=60):
        start=time.monotonic(); value=subprocess.run([str(x) for x in argv],cwd=ROOT,env=env,capture_output=True,timeout=timeout)
        out=output/(name+'.stdout'); err=output/(name+'.stderr'); out.write_bytes(value.stdout);err.write_bytes(value.stderr)
        commands.append(dict(name=name,argv=[str(x) for x in argv],cwd=str(ROOT),observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsedSeconds=time.monotonic()-start,exitCode=value.returncode,
                             stdout=str(out.relative_to(ROOT)),stdoutSHA256=sha(out),stderr=str(err.relative_to(ROOT)),stderrSHA256=sha(err),scope='host-only; no instance queries',environment={key:env[key] for key in ['PYTHONDONTWRITEBYTECODE','DEVELOPER_DIR','MIXER_REVIEW_ATTEMPT']}))
        (output/'commands.json').write_text(json.dumps(commands,indent=2,sort_keys=True)+'\n')
        print(name,value.returncode,flush=True)
        return value.returncode
    command('python-version',[sys.executable,'--version'])
    command('swift-version',[DEVELOPER/'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc','--version'])
    command('producer-readonly-preflight',[sys.executable,'-B',P/'run.py','verify'])
    scratch=HERE/'host-build-scratch';scratch.mkdir(exist_ok=False)
    sdk=DEVELOPER/'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'
    compiler=DEVELOPER/'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc'
    code=command('independent-resolver-compile',[compiler,'-sdk',sdk,'-target','arm64-apple-macosx26.0','-module-cache-path',scratch/'ModuleCache',P/'harness/UITests/PublicSwitchSelection.swift',HERE/'ResolverChecks.swift','-o',HERE/'resolver-checks'])
    if code==0:
        command('independent-resolver-execute',[HERE/'resolver-checks',HERE/'swift-independent-witness.json'])
    command('independent-actual-host-checks',[sys.executable,'-B',HERE/'host_checks.py'])
    command('independent-persistence-probes',[sys.executable,'-B',HERE/'persistence_probes.py'])
    command('unchanged-transport-controls',[ROOT/'verification/apple-toggle-keyboard-focus-v6-preparation/host-tools/transport-controls'])
    command('unchanged-transport-adversarial',[ROOT/'verification/apple-toggle-keyboard-focus-v6-preparation/host-tools/transport-adversarial'])
    for name in ['MixerToggleUITests-Runner.app/MixerToggleUITests-Runner','MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests']:
        binary=P/'build/Build/Products/Debug-iphonesimulator'/name
        prefix='runner' if name.count('/')==1 else 'test-bundle'
        command(prefix+'-vtool',['/usr/bin/xcrun','vtool','-show-build',binary])
        command(prefix+'-lipo',['/usr/bin/xcrun','lipo','-info',binary])
    size=sum(path.stat().st_size for path in scratch.rglob('*') if path.is_file())
    assert scratch.resolve()==scratch and scratch.parent==HERE
    shutil.rmtree(scratch)
    (output/'cleanup.json').write_text(json.dumps(dict(path=str(scratch.relative_to(ROOT)),bytesRemoved=size,absentAfter=not scratch.exists(),nativeInstanceCreated=False,nativeInstanceQueried=False,otherProjectProcessesOrDataTouched=False),indent=2,sort_keys=True)+'\n')
    result=dict(attempt=attempt,commands=commands,allCommandsExitZero=all(c['exitCode']==0 for c in commands),python=sys.version,platform=platform.platform(),pythonExecutable=str(pathlib.Path(sys.executable).resolve()),pythonSHA256=sha(pathlib.Path(sys.executable).resolve()),swiftCompilerSHA256=sha(compiler),
                sourceFiles={str(path.relative_to(ROOT)):sha(path) for path in [P/'settings_telemetry.py',P/'run.py',P/'replay.py',P/'harness/UITests/PublicSwitchSelection.swift',HERE/'ResolverChecks.swift',HERE/'host_checks.py',HERE/'persistence_probes.py',HERE/'execute_checks.py']},nativeExecuted=False,nativeInstancesQueried=False)
    (HERE/(attempt+'-summary.json')).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')


if __name__=='__main__':main()
