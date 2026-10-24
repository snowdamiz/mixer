#!/usr/bin/env python3
"""Compile exact internal UIKit consumer source closure, iOS17 deployment target."""
import pathlib, subprocess, json, hashlib, shutil, sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=ROOT/'verification/apple-native-appearance-v2'
BUILD=pathlib.Path('/tmp/mixer-native-appearance-v2-build')
BUILD.mkdir(exist_ok=True)
commands=[]
def run(args):
    r=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    commands.append(dict(argv=list(map(str,args)),exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr))
    (OUT/'build-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    if r.returncode: print(r.stdout+r.stderr); sys.exit(r.returncode)
    return r.stdout.strip()
sdk=run(['xcrun','--sdk','iphonesimulator','--show-sdk-path'])
common=['xcrun','swiftc','-target','arm64-apple-ios17.0-simulator','-sdk',sdk,'-swift-version','6','-enable-testing','-emit-library','-emit-module','-I',str(BUILD),'-L',str(BUILD)]
for module, sources, libraries in [
 ('MixerCore', sorted((ROOT/'sdk/Sources/MixerCore').glob('*.swift')), []),
 ('MixerUI', sorted((ROOT/'sdk/Sources/MixerUI').glob('*.swift')), ['MixerCore']),
 ('MixerAppearanceInternal', sorted((ROOT/'sdk/Sources/MixerApple').glob('Appearance*V2.swift')), ['MixerCore','MixerUI'])]:
    run(common+['-module-name',module,'-emit-module-path',str(BUILD/(module+'.swiftmodule')),'-o',str(BUILD/('lib'+module+'.dylib'))]+list(map(str,sources))+['-l'+x for x in libraries]+['-Xlinker','-install_name','-Xlinker','@rpath/lib'+module+'.dylib'])
print(BUILD)
