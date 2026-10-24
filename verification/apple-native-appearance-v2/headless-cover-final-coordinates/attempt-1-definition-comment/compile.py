#!/usr/bin/env python3
"""Compile-only closure. Never launch generated host/native programs or devices."""
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
BUILD = pathlib.Path('/tmp/mixer-native-appearance-v2-build')
HOST = pathlib.Path('/tmp/mixer-native-appearance-v2-cover-final-host')
HOST.mkdir(exist_ok=True)
commands = []

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

def run(argv):
    result = subprocess.run(list(map(str, argv)), cwd=ROOT, text=True, capture_output=True)
    commands.append(dict(argv=list(map(str, argv)), exitCode=result.returncode,
                         stdout=result.stdout, stderr=result.stderr))
    write('commands.json', commands)
    if result.returncode:
        raise RuntimeError('Compile/tool command failed: '+str(argv[0]))
    return result.stdout.strip()

inputs = sorted([*(ROOT/'sdk/Sources/MixerCore').glob('*.swift'),
                 *(ROOT/'sdk/Sources/MixerUI').glob('*.swift'),
                 *(ROOT/'sdk/Sources/MixerApple').glob('Appearance*V2.swift'),
                 *(ROOT/'native/apple/appearance-v2').glob('*')])
inputs = [path for path in inputs if path.is_file()]
source = {str(path.relative_to(ROOT)):digest(path) for path in inputs}
source_digest = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
write('source-lock.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      scope='Compile only; generated host/native fixtures were not executed; no device/GUI/capture',
      revision=run(['git','rev-parse','HEAD']), sha256=source, sourceClosureSHA256=source_digest))
write('tool-versions.json', dict(xcode=run(['xcodebuild','-version']),
      swift=run(['xcrun','swiftc','--version']), python=run(['python3','--version'])))

try:
    run(['python3','native/apple/appearance-v2/build-check.py'])
    shutil.copyfile(ROOT/'verification/apple-native-appearance-v2/build-commands.json',OUT/'module-build-commands.json')
    sdk = run(['xcrun','--sdk','iphonesimulator','--show-sdk-path'])
    fixture_sources = [ROOT/'native/apple/appearance-v2/main.swift', ROOT/'native/apple/appearance-v2/Fixture.swift',
                       ROOT/'native/apple/appearance-v2/CoverGeometryRegression.swift']
    binary = BUILD/'headless-cover-final-harness'
    run(['xcrun','swiftc',*fixture_sources,'-o',binary,'-target','arm64-apple-ios17.0-simulator',
         '-sdk',sdk,'-swift-version','6','-I',BUILD,'-L',BUILD,'-lMixerCore','-lMixerUI',
         '-lMixerAppearanceInternal','-framework','UIKit'])
    for module, sources, dependencies in [
        ('MixerCore',sorted((ROOT/'sdk/Sources/MixerCore').glob('*.swift')),[]),
        ('MixerUI',sorted((ROOT/'sdk/Sources/MixerUI').glob('*.swift')),['MixerCore'])]:
        library = HOST/('lib'+module+'.dylib')
        run(['xcrun','swiftc','-swift-version','6','-enable-testing','-emit-library','-emit-module',
             '-module-name',module,'-emit-module-path',HOST/(module+'.swiftmodule'),'-o',library,
             '-I',HOST,'-L',HOST,*sources,*['-l'+name for name in dependencies],
             '-Xlinker','-install_name','-Xlinker',library])
    host_binary = HOST/'cover-geometry-definitions'
    run(['xcrun','swiftc','-swift-version','6',ROOT/'sdk/Sources/MixerApple/AppearanceNativeGeometryV2.swift',
         ROOT/'native/apple/appearance-v2/CoverGeometryRegression.swift',
         ROOT/'native/apple/appearance-v2/cover-geometry-host.swift','-I',HOST,'-L',HOST,
         '-lMixerCore','-lMixerUI','-o',host_binary])
    artifacts = {binary.name:binary, **{('lib'+name+'.dylib'):BUILD/('lib'+name+'.dylib')
                 for name in ['MixerCore','MixerUI','MixerAppearanceInternal']},
                 'host/cover-geometry-definitions':host_binary,
                 **{('host/lib'+name+'.dylib'):HOST/('lib'+name+'.dylib') for name in ['MixerCore','MixerUI']}}
    write('deployment-targets.json', {name:run(['xcrun','vtool','-show-build',path])
          for name,path in artifacts.items() if not name.startswith('host/')})
    manifest = {name:dict(sha256=digest(path),bytes=path.stat().st_size) for name,path in artifacts.items()}
    with tarfile.open(OUT/'compiled-artifacts.tar.gz','w:gz') as archive:
        for name,path in artifacts.items(): archive.add(path,arcname=name,recursive=False)
    write('artifact-members.json',manifest)
    after = {str(path.relative_to(ROOT)):digest(path) for path in inputs}
    if source != after: raise RuntimeError('Source changed during compile')
    write('result.json',dict(productCompiled=True,harnessCompiled=True,hostRegressionCompiled=True,
          generatedProgramsExecuted=False,nativeExecuted=False,guiExecuted=False,visualQualified=False,
          target='arm64-apple-ios17.0-simulator',sourceClosureSHA256=source_digest,
          scope='Exact final-coordinate proof repair; regression definitions compiled only',
          regressionDefinitions='8 pure arithmetic + 2 detached UIKit outcomes; not executed',
          cover='UNQUALIFIED: 12pt glass extent and actual native input/paint remain unproven; RTL exclusions unchanged',
          artifacts=manifest))
except Exception as error:
    write('failure.json',dict(error=str(error),generatedProgramsExecuted=False,nativeExecuted=False,guiExecuted=False))
    raise
