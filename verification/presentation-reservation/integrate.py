#!/usr/bin/env python3
"""Link the complete current activation module using verified retained dependencies."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'integration-1'
OUT.mkdir(exist_ok=False)
WORK = HERE / '.build/integration-1'
SOURCE = WORK / 'source'
SOURCE.mkdir(parents=True, exist_ok=False)
PRODUCTS = WORK / 'products'
PRODUCTS.mkdir()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
dependency = ROOT / 'verification/guest-ui-teardown-window/builds/current-caaa005-1/build-receipt.json'
base = json.loads(dependency.read_text())
base_work = Path(base['dylib']).parents[1]
base_source = Path(base['source'])
base_manifest = json.loads((ROOT / base['source_manifest']).read_text())
assert sha(dependency) == '8abd4367111a5cd4f4d4438750bfb24bc588d56e1e98fbe269f781fddd6b799c'
for relative, digest in base['artifacts'].items():
    assert sha(base_work / relative) == digest, relative
for relative, digest in base_manifest['files'].items():
    assert sha(base_source / relative) == digest, relative
    if relative.startswith(('sdk/Sources/', 'updates/Sources/', 'runtime-identity/Sources/', 'experimental-capability-runtime/Sources/')):
        assert sha(ROOT / relative) == digest, relative
paths = sorted((ROOT / 'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
paths += [ROOT / 'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityAttemptReservationTests.swift', Path(__file__)]
files = {}
for path in paths:
    relative = str(path.relative_to(ROOT))
    dest = SOURCE / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(path.read_bytes())
    files[relative] = sha(dest)
    dest.chmod(0o444)
receipt = {'started_utc': datetime.now(timezone.utc).isoformat(), 'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'source_files': files, 'source_tree_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(), 'source': str(SOURCE), 'dependency_receipt': str(dependency.relative_to(ROOT)), 'dependency_receipt_sha256': sha(dependency), 'dependency_artifacts': base['artifacts'], 'dependency_source_manifest_sha256': base['source_manifest_sha256'], 'commands': [], 'scope': 'Full current activation module link plus the complete reservation XCTest against exact retained Swift/C dependency objects and native archive. No second activation module/runtime linked, no source mocks. This runs reservation tests only; full hosted suite and Android binding remain separate.'}
env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')

def save(): (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

def run(name, argv):
    argv = [str(x) for x in argv]
    start = time.monotonic()
    result = subprocess.run(argv, cwd=SOURCE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
    log = OUT / (name + '.log')
    log.write_bytes(result.stdout)
    receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(SOURCE), 'environment': {'DEVELOPER_DIR': env['DEVELOPER_DIR']}, 'seconds': time.monotonic() - start, 'exit': result.returncode, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
    save()
    print(name, result.returncode, flush=True)
    assert result.returncode == 0, name
    for relative, digest in files.items(): assert sha(SOURCE / relative) == digest == sha(ROOT / relative), relative
    return result.stdout.decode(errors='replace')

try:
    run('swift-version', ['xcrun', 'swiftc', '--version'])
    original = next(row['argv'] for row in base['commands'] if row['name'] == 'link-current-runtime')
    library = PRODUCTS / 'libMixerPresentationReservationIntegrated.dylib'
    argv = []
    for arg in original:
        if arg.startswith(str(base_source / 'capability-activation/Sources/MixerCapabilityActivation')):
            arg = str(SOURCE / Path(arg).relative_to(base_source))
        elif arg == base['dylib']: arg = str(library)
        elif arg.endswith('/products/MixerCapabilityActivation.swiftmodule'): arg = str(PRODUCTS / 'MixerCapabilityActivation.swiftmodule')
        elif arg == '@rpath/libMixerGuestUITeardownRuntime.dylib': arg = '@rpath/' + library.name
        argv.append(arg)
    run('full-activation-link', argv)
    prefix = original[:original.index('-emit-library')]
    frameworks = Path(env['DEVELOPER_DIR']) / 'Platforms/MacOSX.platform/Developer/Library/Frameworks'
    overlays = frameworks.parents[1] / 'usr/lib'
    bundle = PRODUCTS / 'MixerPresentationReservationTests.xctest'
    executable = bundle / 'Contents/MacOS/MixerPresentationReservationTests'
    executable.parent.mkdir(parents=True)
    (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': executable.name, 'CFBundleIdentifier': 'dev.mixer.presentation-reservation-integrated', 'CFBundlePackageType': 'BNDL', 'CFBundleVersion': '1'}))
    tests = SOURCE / 'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityAttemptReservationTests.swift'
    run('tests-link', prefix[:2] + ['-I', PRODUCTS] + prefix[2:] + ['-emit-library', '-module-name', 'MixerPresentationReservationTests', '-I', overlays, '-F', frameworks, tests, '-L', PRODUCTS, '-lMixerPresentationReservationIntegrated', '-L', overlays, '-Xlinker', '-rpath', '-Xlinker', PRODUCTS, '-Xlinker', '-rpath', '-Xlinker', frameworks, '-Xlinker', '-rpath', '-Xlinker', overlays, '-o', executable])
    xctest = run('xctest-path', ['xcrun', '--find', 'xctest']).strip()
    output = run('tests', [xctest, bundle])
    assert 'Executed 1 test, with 0 failures' in output
    receipt['artifacts'] = {str(p): sha(p) for p in [library, executable, PRODUCTS / 'MixerCapabilityActivation.swiftmodule']}
    receipt['result'] = 'Complete current activation module linked; reservation XCTest passed.'
except BaseException as error:
    receipt['result'] = 'failed integration preserved'
    receipt['problem'] = str(error)
    raise
finally:
    receipt['completed_utc'] = datetime.now(timezone.utc).isoformat()
    save()
