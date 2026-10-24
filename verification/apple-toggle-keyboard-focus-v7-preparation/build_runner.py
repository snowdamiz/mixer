#!/usr/bin/env python3
"""Build one generic iOS Simulator runner; no native instance query/launch."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import run as r
b=r.BASE;h=r.h
r.require(not (b/'packet-seal.json').exists(),'Sealed preparation cannot be rebuilt')
sources={str(p.relative_to(r.ROOT)):r.sha(p) for p in sorted((b/'harness').rglob('*')) if p.is_file()}
revision=subprocess.run(['git','rev-parse','HEAD'],cwd=r.ROOT,capture_output=True,text=True,check=True).stdout.strip()
commands=h.Commands(b/'runner-build-attempt-1.json');versions={}
for key,argv in {'xcode':[str(h.DEVELOPER/'usr/bin/xcodebuild'),'-version'],'swift':[str(h.DEVELOPER/'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc'),'--version'],'python':[sys.executable,'--version']}.items():versions[key]=commands.run(argv)[1]
argv=[str(h.DEVELOPER/'usr/bin/xcodebuild'),'build-for-testing','-project',str(b/'harness/MixerToggleUITests.xcodeproj'),'-scheme','MixerToggleUITests','-sdk','iphonesimulator','-destination','generic/platform=iOS Simulator','-derivedDataPath',str(b/'build'),'CODE_SIGNING_ALLOWED=NO','ARCHS=arm64']
commands.run(argv,timeout=180)
r.require(sources=={str(p.relative_to(r.ROOT)):r.sha(p) for p in sorted((b/'harness').rglob('*')) if p.is_file()},'Runner sources changed during build')
products=h.tree(h.PRODUCTS)
tools=[h.DEVELOPER/'usr/bin/xcodebuild',h.DEVELOPER/'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc',h.DEVELOPER/'Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk/SDKSettings.json',pathlib.Path('/usr/bin/xcrun'),pathlib.Path('/usr/bin/codesign'),pathlib.Path(sys.executable).resolve()]
manifest=dict(schema='mixer.apple-toggle.xctest-build.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceRevisionContext=revision,sourceFiles=sources,sourceTreeSHA256=hashlib.sha256(h.json_bytes(sources)).hexdigest(),products=products,productTreeSHA256=hashlib.sha256(h.json_bytes(products)).hexdigest(),productArchiveSHA256=h.archive_products(products),versions=versions,toolFiles={str(p):r.sha(p) for p in tools},nativeBootInstallRun=False,physicalDeviceCommands=False,buildCommands='runner-build-attempt-1.json')
h.write(b/'build-products-manifest.json',manifest)
print(json.dumps(dict(status='fresh-official-generic-runner-build-only',sourceTreeSHA256=manifest['sourceTreeSHA256'],productTreeSHA256=manifest['productTreeSHA256'],productArchiveSHA256=manifest['productArchiveSHA256'])))
