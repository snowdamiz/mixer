#!/usr/bin/env python3
"""Qualify a test-only array-expression split without rebuilding production."""
import base64
import hashlib
import json
import os
import plistlib
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = 'capability-activation/Tests/MixerCapabilityActivationTests/ConcreteAttemptTests.swift'
REVISION = '36c55799fa8518fc7110911ae396e9a7cf72916a'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
work = HERE / '.build'
work.mkdir(exist_ok=False)
old = subprocess.check_output(['git', 'show', REVISION + ':' + SOURCE], cwd=ROOT)
new = (ROOT / SOURCE).read_bytes()
(work / 'ConcreteAttemptTests.swift').write_bytes(new)
owner_path = ROOT / 'verification/capability-cold-start-runtime/2026-10-23-candidate-1/receipt.json'
owner = json.loads(owner_path.read_text())
assert hashlib.sha256(old).hexdigest() == owner['source_files'][SOURCE]
record = {
    'status': 'running', 'source': SOURCE, 'failed_revision': REVISION,
    'failed_job': 120367174277,
    'old_sha256': hashlib.sha256(old).hexdigest(), 'new_sha256': sha(ROOT / SOURCE),
    'owner_receipt_sha256': sha(owner_path), 'driver_sha256': sha(Path(__file__)),
    'commands': [],
    'scope': 'Test fixture expressions only; full two-value Bool input domain has identical Wasm bytes. Production remains exact frozen coordinator candidate1. Local Xcode27 XCTest replay does not qualify hosted Swift6.2.4; hosted confirmation pending.'
}


def save():
    (HERE / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')


def run(label, command, extra=None):
    env = os.environ | {'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'} | (extra or {})
    value = subprocess.run(command, env=env, capture_output=True, timeout=90)
    log = HERE / (label + '.log')
    log.write_bytes(value.stdout + value.stderr)
    record['commands'].append({'name': label, 'command': command, 'environment': {'DEVELOPER_DIR': env['DEVELOPER_DIR']} | (extra or {}), 'exit_code': value.returncode, 'log': log.name, 'log_sha256': sha(log)})
    save()
    if value.returncode:
        raise RuntimeError(label + ' failed; log preserved')
    return value.stdout.decode()


def method(raw):
    text = raw.decode()
    begin = text.index('    static func wasm(')
    end = text.index('\n}\n\nfinal class ConcreteAttemptTests', begin)
    return text[begin:end]


parity = HERE / 'fixture-parity.swift'
parity.write_text('import Foundation\nenum Before {\n' + method(old) + '\n}\nenum After {\n' + method(new) + '\n}\nfor flag in [false, true] {\n    let before = Before.wasm(badInitialData: flag), after = After.wasm(badInitialData: flag)\n    precondition(before == after)\n    print("\\(flag) \\(after.base64EncodedString())")\n}\n')
record['probe_sha256'] = sha(parity)
run('swift-version', ['swift', '--version'])
run('parity-compile', ['swiftc', '-warnings-as-errors', str(parity), '-o', str(work / 'parity')])
output = run('parity-run', [str(work / 'parity')])
record['fixture_bytes'] = {}
for line in output.splitlines():
    name, encoded = line.split(' ')
    data = base64.b64decode(encoded, validate=True)
    record['fixture_bytes'][name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
assert set(record['fixture_bytes']) == {'false', 'true'}
bundle = work / 'ConcreteTests.xctest'
binary = bundle / 'Contents/MacOS/ConcreteTests'
binary.parent.mkdir(parents=True)
(bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': 'ConcreteTests', 'CFBundleIdentifier': 'org.mixer.tests.concrete-ci-fix', 'CFBundlePackageType': 'BNDL', 'CFBundleVersion': '1'}))
link = next(c['command'] for c in owner['commands'] if c['name'] == 'debug-test-link')
args = [x for x in link if not x.endswith('.swift')]
args[args.index('-o') + 1] = str(binary)
args += [str(work / 'ConcreteAttemptTests.swift'), str(Path(owner['export']) / 'verification/capability-cold-start-runtime/Bundle.swift')]
run('xctest-link', args)
for item in owner['artifacts']['debug'].values():
    assert sha(Path(item['path'])) == item['sha256']
xctest = subprocess.check_output(['xcrun', '--find', 'xctest'], text=True).strip()
resources = ROOT / 'capability-activation/.build/transitions-qualified-2026-10-23-candidate-3/retained-debug/products/MixerCapabilityActivation_MixerCapabilityActivationTests.bundle'
output = run('xctest-run', [xctest, str(bundle)], {'MIXER_COLD_START_TEST_BUNDLE': str(resources)})
assert re.findall(r'Executed (\d+) tests?, with 0 failures', output)[-1] == '6'
symbols = run('defined-symbols', ['nm', '-gU', str(binary)])
assert re.search(r'\b_mixer_vm_\w+$', symbols, re.M) is None
assert sha(ROOT / SOURCE) == record['new_sha256']
record.update(status='both Wasm fixture variants byte-identical and six XCTest functions passed', tests=6, artifact={'path': str(binary), 'sha256': sha(binary)}, production_artifacts=owner['artifacts']['debug'])
save()
print(json.dumps({'status': record['status'], 'receipt_sha256': sha(HERE / 'receipt.json')}))
