#!/usr/bin/env python3
"""Official generic simulator build-for-testing only; no native runtime."""
import datetime
import json
import pathlib
import sys
import run

b, h = run.BASE, run.h
assert not (b / 'packet-seal.json').exists(), 'Sealed preparation is immutable'
attempt = len(list(b.glob('runner-build-attempt-*.json'))) + 1
commands = h.Commands(b / f'runner-build-attempt-{attempt}.json')
versions = {}
for key, argv in [('xcode', [h.DEVELOPER / 'usr/bin/xcodebuild', '-version']), ('swift', [h.DEVELOPER / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc', '--version']), ('python', [sys.executable, '--version'])]:
    versions[key] = commands.run(argv)[1]
run.require(versions['xcode'].startswith('Xcode 26.6\n'), 'Pinned Xcode required')
sources = {str(p.relative_to(run.ROOT)): run.sha(p) for p in sorted((b / 'harness').rglob('*')) if p.is_file()}
argv = [h.DEVELOPER / 'usr/bin/xcodebuild', 'build-for-testing', '-project', b / 'harness/MixerToggleUITests.xcodeproj', '-scheme', 'MixerToggleUITests', '-sdk', 'iphonesimulator', '-destination', 'generic/platform=iOS Simulator', '-derivedDataPath', b / 'build', 'CODE_SIGNING_ALLOWED=NO', 'ARCHS=arm64']
commands.run(argv, timeout=180)
run.require(all(run.sha(run.ROOT / name) == digest for name, digest in sources.items()), 'Runner source changed during build')
products = h.tree(h.PRODUCTS)
tools = [h.DEVELOPER / 'usr/bin/xcodebuild', h.DEVELOPER / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc', pathlib.Path('/usr/bin/xcrun'), h.DEVELOPER / 'Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk/SDKSettings.json']
manifest = {'schema': 'mixer.apple-toggle.xctest-build.1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'sourceRevisionContext': h.SOURCE_REVISION_CONTEXT, 'sourceFiles': sources, 'sourceTreeSHA256': run.hashlib.sha256(h.json_bytes(sources)).hexdigest(), 'products': products, 'productTreeSHA256': run.hashlib.sha256(h.json_bytes(products)).hexdigest(), 'productArchiveSHA256': h.archive_products(products), 'versions': versions, 'toolFiles': {str(p): run.sha(p) for p in tools}, 'buildCommands': f'runner-build-attempt-{attempt}.json', 'nativeBootInstallRun': False, 'physicalDeviceCommands': False}
h.write(b / 'build-products-manifest.json', manifest)
print(json.dumps({'status': 'build-for-testing-succeeded-DIAGNOSTIC_ONLY', 'productTreeSHA256': manifest['productTreeSHA256'], 'archiveSHA256': manifest['productArchiveSHA256']}))
