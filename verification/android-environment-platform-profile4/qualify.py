#!/usr/bin/env python3
"""Fresh host qualification of the exact profile4 policy and consumers."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SWIFT = '/usr/bin/swift'


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')


demand(not (HERE / 'run.json').exists(), 'One-shot qualification already started')
scratch = Path(tempfile.mkdtemp(prefix='mixer-platform-profile4-', dir='/tmp'))
commands = []
products = []
profile = json.loads((HERE / 'proposed-profile4.json').read_text())
names = set()
for base in ['cli/Sources', 'cli/Tests', 'cli/build-tests', 'sdk/Sources', 'sdk/Tests']:
    names.update(str(p.relative_to(ROOT)) for p in (ROOT / base).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
names.update(['cli/Package.swift', 'sdk/Package.swift', 'contracts/ui-v1.json',
              'verification/android-default-appearance-packaging/run-2/created-descriptor.json'])
for relative in profile['adapter_files']:
    names.add('native/android/' + ('engine/' if relative.startswith('Sources/') else '') + relative)
source_map = {n: identity((ROOT / n).read_bytes()) for n in sorted(names)}
save('source-map.json', source_map)
save('run.json', {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'argv': sys.argv,
                  'python': sys.version, 'scratch': str(scratch), 'status': 'running',
                  'source_map': identity((HERE / 'source-map.json').read_bytes())})


def run(label, argv, timeout=600):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    process = subprocess.Popen([str(a) for a in argv], cwd=ROOT, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    (HERE / (label + '.stdout')).write_bytes(stdout)
    (HERE / (label + '.stderr')).write_bytes(stderr)
    commands.append({'label': label, 'argv': [str(a) for a in argv], 'cwd': str(ROOT),
                     'started': start, 'ended': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'exit': process.returncode, 'timed_out': timed_out, 'child_reaped': True,
                     'stdout': identity(stdout), 'stderr': identity(stderr)})
    save('commands.json', commands)
    demand(process.returncode == 0 and not timed_out, 'Command failed: ' + label)
    return stdout


status = 'failed'
try:
    run('swift-version', [SWIFT, '--version'])
    run('revision', ['git', 'rev-parse', 'HEAD'])
    for mode, flags in [('normal', []), ('optimized', ['-O'])]:
        for name in ['test_android_sdk_compatibility', 'test_android_staging', 'test_android_appearance']:
            run(mode + '-' + name, [sys.executable, '-B', *flags, ROOT / 'cli/build-tests' / (name + '.py')], 180)
    clis = {}
    for mode in ['debug', 'release']:
        common = ['--package-path', ROOT / 'cli', '--scratch-path', scratch / ('cli-' + mode),
                  '--disable-automatic-resolution', '--jobs', '2', '-c', mode]
        run(mode + '-build', [SWIFT, 'build', *common, '--product', 'mixer'])
        binary = Path(run(mode + '-bin-path', [SWIFT, 'build', *common, '--show-bin-path']).decode().strip()) / 'mixer'
        products.append({'role': mode + '-before-tests', 'path': str(binary), **identity(binary.read_bytes())})
        run(mode + '-tests', [SWIFT, 'test', *common, '--filter',
            'androidCompatibility|androidSnapshotOwns|androidDefaultAppearance|androidCoordinatorAndAuthoredToggle'])
        products.append({'role': mode + '-consumer-binary', 'path': str(binary), **identity(binary.read_bytes())})
        clis[mode] = binary
    app = scratch / 'PlatformConsumer'
    run('create', [clis['debug'], 'create', 'PlatformConsumer', '--directory', app,
        '--application', 'dev.mixer.platformconsumer', '--platform', 'android',
        '--sdk-path', ROOT / 'sdk', '--android-adapter-path', ROOT / 'native/android'])
    exported = scratch / 'CopiedConsumer'
    run('export', [clis['release'], 'export', exported, '--directory', app])
    driver = exported / 'Generated/MixerAndroid/android-build.py'
    spec = importlib.util.spec_from_file_location('actual_profile4_driver', driver)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    demand(module.source_profile() == profile, 'Actual rendered profile')
    for path in [app, exported]:
        demand(identity(module.admit_source_pair(path, profile)) == profile['default_descriptor'], 'Actual source-pair admission')
        demand(json.loads((path / 'mixer.lock').read_text())['android']['profile']['id'] == profile['id'], 'Actual lock')
    for name, path in [('shared', exported), ('session', exported / 'Platforms/Android')]:
        run('copied-' + name + '-tests', [SWIFT, 'test', '--package-path', path,
            '--scratch-path', scratch / ('copied-' + name), '--disable-automatic-resolution', '--jobs', '2'])
    consumer_files = {}
    for label, path in [('created', app), ('exported', exported)]:
        consumer_files[label] = {str(p.relative_to(path)): identity(p.read_bytes()) for p in sorted(path.rglob('*'))
                                 if p.is_file() and '.build' not in p.parts and '__pycache__' not in p.parts}
    save('consumers.json', consumer_files)
    for name, value in source_map.items():
        demand(identity((ROOT / name).read_bytes()) == value, 'Source changed during qualification: ' + name)
    status = 'passed-host-only'
finally:
    for path in sorted(scratch.rglob('*')):
        if path.is_file() and (path.name.endswith('.xctest') or path.name == 'mixer'):
            products.append({'role': 'retired-owned-product', 'path': str(path), **identity(path.read_bytes())})
    shutil.rmtree(scratch)
    save('receipt.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': status, 'python': sys.version, 'argv': sys.argv, 'profile': profile['id'],
        'adapter_projection': profile['adapter_compatibility_sha256'], 'source_files': len(source_map),
        'source_map': identity((HERE / 'source-map.json').read_bytes()), 'commands': len(commands),
        'products': products, 'owned_children_reaped': all(c['child_reaped'] for c in commands),
        'owned_scratch_removed': not scratch.exists(), 'native_or_capture_started': False,
        'independent_profile_acceptance': False, 'native_runtime_public_V2_or_GA_qualified': False})
print(json.dumps({'status': status, 'commands': len(commands), 'source_files': len(source_map), 'scratch_removed': True}))
