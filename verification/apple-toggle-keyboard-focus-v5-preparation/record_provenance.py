#!/usr/bin/env python3
"""Bind official tool/header/binary outputs and unchanged v2 host regression."""
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import run as r
b, h = r.BASE, r.h
assert not (b / 'packet-seal.json').exists(), 'Sealed preparation is immutable'
manifest = r.read(b / 'build-products-manifest.json')
payload = h.product_archive_payload(manifest)
commands = h.Commands(b / 'binary-provenance-commands.json')
binaries = {}
for name in ['Debug-iphonesimulator/MixerToggleUITests-Runner.app/MixerToggleUITests-Runner', 'Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests']:
    path = h.PRODUCTS / name
    build = commands.run(['/usr/bin/xcrun', 'vtool', '-show-build', path])[1]
    architecture = commands.run(['/usr/bin/xcrun', 'lipo', '-info', path])[1]
    r.require('platform IOSSIMULATOR' in build, 'Simulator binary required')
    binaries[name] = {'sha256': hashlib.sha256(payload[name]).hexdigest(), 'officialBuildVersionOutput': build, 'officialArchitectureOutput': architecture}
official = b / 'official'
official.mkdir(exist_ok=True)
headers = []
root = h.DEVELOPER / 'Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks/XCTest.framework/Headers'
for name in ['XCTestObservation.h', 'XCTestObservationCenter.h', 'XCTestCase.h', 'XCUIScreenshot.h', 'XCUIElement.h', 'XCUIElementAttributes.h']:
    source = root / name
    shutil.copy2(source, official / name)
    headers.append({'source': str(source), 'snapshot': name, 'sha256': r.sha(source)})
for name in ['XCUIScreenshot.h', 'XCUIElementTypes.h', 'XCUIApplication.h']:
    source = root.parent.parent / 'XCUIAutomation.framework/Headers' / name
    target = 'XCUIAutomation-' + name
    shutil.copy2(source, official / target)
    headers.append({'source': str(source), 'snapshot': target, 'sha256': r.sha(source)})
(official / 'manifest.json').write_text(json.dumps({'installedOfficialHeaders': headers}, indent=2) + '\n')
record = {'schema': 'mixer.apple-toggle.keyboard-v5-runner-binary.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve().relative_to(r.ROOT))], 'sourceRevisionContext': h.SOURCE_REVISION_CONTEXT, 'sourceTreeSHA256': manifest['sourceTreeSHA256'], 'productTreeSHA256': manifest['productTreeSHA256'], 'archiveSHA256': manifest['productArchiveSHA256'], 'binaries': binaries, 'versions': manifest['versions'], 'buildCommands': manifest['buildCommands'], 'nativeExecuted': False, 'scope': 'One public Settings diagnostic XCTest method; no application keyboard case or native input qualification. Official runner launcher has its own build SDK/minimum, recorded separately.'}
(b / 'runner-binary-receipt.json').write_text(json.dumps(record, indent=2) + '\n')
argv = [sys.executable, '-B', str(r.V2 / 'test_keyboard.py')]
p = subprocess.run(argv, cwd=r.ROOT, capture_output=True, text=True, timeout=60)
regression = {'schema': 'mixer.apple-toggle.keyboard-v5-v2-regression.1', 'command': argv, 'exitCode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr, 'expectedTestsRun': 29, 'oracleSHA256': r.sha(r.V2 / 'keyboard_oracle.py'), 'controlSHA256': r.sha(r.V2 / 'test_keyboard.py'), 'nativeExecuted': False}
(b / 'unchanged-v2-host-regression.json').write_text(json.dumps(regression, indent=2) + '\n')
r.require(p.returncode == 0 and 'Ran 29 tests' in p.stderr and p.stderr.rstrip().endswith('OK'), 'Unchanged v2 controls failed')
print(json.dumps({'status': 'official-provenance-and-v2-regression-recorded', 'v2HostTestsRun': 29, 'productTreeSHA256': manifest['productTreeSHA256'], 'archiveSHA256': manifest['productArchiveSHA256'], 'nativeExecuted': False}))
