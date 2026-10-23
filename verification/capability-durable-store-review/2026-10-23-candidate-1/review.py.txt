#!/usr/bin/env python3
"""Original review probes using the owner's frozen retained products, no SwiftPM."""
from pathlib import Path
import argparse, datetime, difflib, hashlib, json, os, re, subprocess, time

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('--name', required=True)
p.add_argument('--owner', type=Path, default=ROOT / 'verification/capability-durable-store/2026-10-23-candidate-1/receipt.json')
p.add_argument('--modes', default='debug,release,tsan')
a = p.parse_args()
assert re.fullmatch('[a-z0-9-]{1,64}', a.name)
OUT = OWN / a.name
OUT.mkdir(exist_ok=False)
SCRATCH = OWN / '.build' / a.name
SCRATCH.mkdir(parents=True, exist_ok=False)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
owner = json.loads(a.owner.read_text())
source = Path(owner['export'])
native = Path(owner['native_copy'])
for name, digest in owner['source_files'].items():
    assert sha(source / name) == digest, name
for name, digest in owner['baseline_files'].items():
    raw = subprocess.check_output(['git', 'show', owner['dependency_revision'] + ':' + name], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == digest, name
for name, digest in owner['native_files'].items():
    assert sha(native / name) == digest, name
assert owner['native_files']['lib/libmixer_vm_capability_experimental.a'] == 'a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72'
inputs = [OWN / name for name in ['RetirementProbe.swift', 'StoreFixture.swift', 'StoreProbe.swift', 'IngressTailProbe.swift', 'review.py']]
input_hashes = {str(v.relative_to(ROOT)): sha(v) for v in inputs}
for path in inputs:
    (OUT / (path.name + '.txt')).write_bytes(path.read_bytes())
record = {'status': 'running', 'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope': 'Independent internal original probes directly linked to retained frozen library. Only ingress-tail probe recompiles captured Store with a recorded scheduling gate after actual worker return; not an unmodified public reproduction.',
    'ownerReceipt': str(a.owner), 'ownerReceiptSHA256': sha(a.owner), 'sourceManifestSHA256': owner['source_manifest_sha256'],
    'sourceFiles': owner['source_files'], 'dependencyRevision': owner['dependency_revision'],
    'nativeFiles': owner['native_files'], 'programInputs': input_hashes, 'commands': [], 'products': {},
    'limitations': ['Internal @testable review, not a new public updater or authority API',
        'Reused inert installed descriptor/bridge templates are pinned; Wasm, signing context, envelopes and assertions are original',
        'Fault and async gates are scheduling controls around real file operations/native validate, not device or power-loss evidence',
        'Logical owned-frame and retained-owner release boundaries do not prove Task/allocator destruction or total RSS/OOM bounds',
        'TSan excludes Rust/platform framework internals; local Xcode27.1/Swift6.3.3 is not hosted Xcode26.3 qualification',
        'No adapter/session/selection/effects/health/release/device authority or execution is qualified']}
def save(): (OUT / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
def run(name, command, fragment=None):
    began = time.monotonic()
    try:
        r = subprocess.run(command, cwd=ROOT, env=os.environ | {'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
        code, raw = r.returncode, r.stdout
    except subprocess.TimeoutExpired as error:
        code, raw = 124, (error.stdout or b'') + b'\nReview timeout\n'
    path = OUT / (name + '.log'); path.write_bytes(raw)
    record['commands'].append({'name': name, 'command': command, 'cwd': str(ROOT),
        'environment': {'DEVELOPER_DIR': '/Applications/Xcode.app/Contents/Developer'}, 'exitCode': code,
        'elapsedSeconds': time.monotonic() - began, 'requiredFragment': fragment, 'fragmentPresent': fragment is None or fragment.encode() in raw,
        'log': path.name, 'logSHA256': sha(path)})
    save(); print(name, code, flush=True)
    return code == 0 and (fragment is None or fragment.encode() in raw)
save()
run('swift-version', ['swift', '--version'])
run('xcode-version', ['xcodebuild', '-version'])
templates = source / 'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures'
store_source = source / 'capability-activation/Sources/MixerCapabilityActivation/CapabilityRecoveryStore.swift'
before = store_source.read_text()
anchor = '        try await withTaskCancellationHandler { try await worker.append(snapshot, offset: offset, op) } onCancel: { op.cancel() }'
assert before.count(anchor) == 1
after = '@testable import MixerCapabilityActivation\n' + before.replace(anchor, anchor + '\n        await ReviewIngressGate.shared.hold()')
derived = SCRATCH / 'CapabilityRecoveryStore.swift'; derived.write_text(after)
(OUT / 'derived-CapabilityRecoveryStore.swift.txt').write_text(after)
(OUT / 'test-only.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='base/CapabilityRecoveryStore.swift', tofile='derived/CapabilityRecoveryStore.swift')))
record['derived'] = {'baseSHA256': sha(store_source), 'sourceSHA256': sha(derived), 'patchSHA256': sha(OUT / 'test-only.patch')}

for mode in a.modes.split(','):
    if mode == 'tsan':
        assert any(v['name'] == 'new-tsan' and v['exit_code'] == 0 for v in owner['commands'])
        work = source.parent
        products = work / 'host/out/Products/Debug'
        maps = work / 'host/out/Intermediates.noindex/GeneratedModuleMaps'
    else:
        retained = owner['retained_products'][mode]
        base = Path(retained['directory'])
        for name, digest in retained['files'].items(): assert sha(base / name) == digest, name
        products, maps = base / 'products', base / 'modulemaps'
    files = {str(v): sha(v) for folder in [products, maps] for v in sorted(folder.rglob('*')) if v.is_file() and not v.is_symlink()}
    record['products'][mode] = files
    flags = ['-swift-version', '6', '-warnings-as-errors', '-parse-as-library', '-I' + str(products), '-L' + str(products), '-lMixerCapabilityActivation', '-L' + str(native / 'lib'), '-lmixer_vm_capability_experimental', '-Xcc', '-I' + str(native / 'include')]
    if mode == 'release': flags += ['-O']
    if mode == 'tsan': flags += ['-sanitize=thread']
    for module in ['CMixerVMCapability', 'MixerCapabilityDurableIO', 'MixerCapabilityIO', 'MixerDurableIO']:
        flags += ['-Xcc', '-fmodule-map-file=' + str(maps / (module + '.modulemap'))]
    binaries = {}
    for label, paths in [('retirement', [OWN / 'RetirementProbe.swift']), ('store', [OWN / 'StoreFixture.swift', OWN / 'StoreProbe.swift']), ('ingress-derived', [OWN / 'StoreFixture.swift', OWN / 'IngressTailProbe.swift', derived])]:
        binary = SCRATCH / (mode + '-' + label)
        if run(mode + '-' + label + '-compile', ['swiftc'] + flags + [str(v) for v in paths] + ['-o', str(binary)]):
            binaries[label] = binary
            record.setdefault('binaries', {})[mode + '-' + label] = {'path': str(binary), 'sha256': sha(binary), 'bytes': binary.stat().st_size}
    if 'retirement' in binaries:
        for argument in ['store-first', 'adapter-first', 'replacement']:
            fragment = 'adapter replacement waits' if argument == 'replacement' else 'concurrent retained-owner destruction is included'
            run(mode + '-retirement-' + argument, [str(binaries['retirement']), argument], fragment)
    if 'store' in binaries:
        for argument in ['uncertain-stage', 'signed-highwater', 'cancel-close', 'host-mismatch']:
            run(mode + '-store-' + argument, [str(binaries['store']), argument, str(templates)], 'REVIEW_PASS ' + argument)
    if 'ingress-derived' in binaries:
        run(mode + '-ingress-derived', [str(binaries['ingress-derived']), str(templates)], 'owned ingress tail participates in actual-close retirement')
    assert all(sha(Path(name)) == digest for name, digest in files.items()), 'products changed during probe'
record['sourceUnchanged'] = all(sha(source / name) == digest for name, digest in owner['source_files'].items())
record['nativeUnchanged'] = all(sha(native / name) == digest for name, digest in owner['native_files'].items())
record['programsUnchanged'] = all(sha(ROOT / name) == digest for name, digest in input_hashes.items()) and sha(derived) == record['derived']['sourceSHA256']
record['expectedProbeExecutions'] = len(a.modes.split(',')) * 8
record['observedProbeExecutions'] = sum('-compile' not in v['name'] and v['name'] not in ['swift-version', 'xcode-version'] for v in record['commands'])
record['completedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
record['status'] = 'passed' if all(v['exitCode'] == 0 and v['fragmentPresent'] for v in record['commands']) and record['observedProbeExecutions'] == record['expectedProbeExecutions'] and record['sourceUnchanged'] and record['nativeUnchanged'] and record['programsUnchanged'] else 'failed_check_preserved'
save()
raise SystemExit(0 if record['status'] == 'passed' else 1)
