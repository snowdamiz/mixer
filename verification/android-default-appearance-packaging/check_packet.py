#!/usr/bin/env python3
"""Read-only producer packet binding checks; executes no product or collector code."""
import hashlib
import json
import pathlib
import tarfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKET = pathlib.Path(__file__).resolve().parent
RUN = PACKET / 'run-2'


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def file_identity(path):
    return identity(path.read_bytes())


receipt = json.loads((RUN / 'receipt.json').read_text())
assert receipt['status'] == 'passed-producer-evidence-awaiting-independent-review'
assert receipt['collector_sha256'] == file_identity(RUN / 'collector.py')['sha256']
assert (RUN / 'collector.py').read_bytes() == (PACKET / 'run.py').read_bytes()
assert receipt['cleanup'] == {'owned_process_groups_remaining': [], 'scratch_removed': True}
for command in receipt['commands']:
    assert command['exit'] == 0 and command['stop_reason'] is None
    assert command['child_returned'] and command['group_gone']
    for stream in ['stdout', 'stderr']:
        binding = command[stream]
        assert file_identity(RUN / binding['path']) == {k: binding[k] for k in ['bytes', 'sha256']}
before = json.loads((RUN / 'product-before.json').read_text())
after = json.loads((RUN / 'product-after.json').read_text())
assert before == after
assert before['sha256'] == receipt['product_before_sha256'] == receipt['product_after_sha256']
assert hashlib.sha256(json.dumps(before['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest() == before['sha256']
for path, expected in before['files'].items():
    assert file_identity(ROOT / path) == expected, path
with tarfile.open(PACKET / 'product-inputs.tar.gz') as archive:
    captured = {m.name: identity(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
assert captured == before['files']
descriptor = (RUN / 'final-descriptor.json').read_bytes()
assert descriptor == (RUN / 'created-descriptor.json').read_bytes()
assert identity(descriptor) == receipt['created_descriptor'] == receipt['final_descriptor']
apk = RUN / 'AppearanceConsumer-unsigned.apk'
assert file_identity(apk) == receipt['apk']
inventory = json.loads((RUN / 'apk-inventory.json').read_text())
with zipfile.ZipFile(apk) as archive:
    names = archive.namelist()
    assert len(names) == len(set(names))
    assert [n for n in names if n == 'assets' or n.startswith('assets/')] == ['assets/MixerAppearanceV2/descriptor.json']
    assert archive.read('assets/MixerAppearanceV2/descriptor.json') == descriptor
    assert {n: identity(archive.read(n)) for n in names} == inventory
    apk_dex = {n: archive.read(n) for n in names if n.endswith('.dex')}
build = json.loads((RUN / 'generated-build-receipt.json').read_text())
assert build['apk_sha256'] == receipt['apk']['sha256'] and build['apk_bytes'] == receipt['apk']['bytes']
assert build['source_tree_sha256'] == build['source_tree_after_sha256']
assert build['appearance_descriptor']['sha256'] == receipt['final_descriptor']['sha256']
assert build['appearance_descriptor']['bytes'] == len(descriptor)
assert build['apk_entries'] == {n: v['sha256'] for n, v in inventory.items()}
assert any(c['command'][1] == 'link' and '-A' in c['command'] for c in build['commands'] if c['command'][0].endswith('/aapt2'))
for command in build['commands']: assert command['exit_code'] == 0
source_archive = RUN / 'generated-source-and-classes.tar.gz'
assert file_identity(source_archive) == receipt['retained_sources_and_classes']
with tarfile.open(source_archive) as archive:
    contents = {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
generated = {k.removeprefix('AppearanceConsumer/'): identity(v) for k, v in contents.items() if k.startswith('AppearanceConsumer/')}
assert generated == receipt['generated_project']
assert contents['AppearanceConsumer/Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'] == descriptor
assert {k.removeprefix('classes/'): identity(v) for k, v in contents.items() if k.startswith('classes/')} == receipt['classes']
assert {k.removeprefix('dex/'): v for k, v in contents.items() if k.startswith('dex/')} == apk_dex
prior = ROOT / receipt['accepted_java_binding']['prior_receipt']
assert file_identity(prior) == receipt['accepted_java_binding']['prior_receipt_identity']
old = json.loads(prior.read_text())
old_archive = prior.parent / 'generated-and-compiled.tar.gz'
assert file_identity(old_archive) == old['retained_archive']
with tarfile.open(old_archive) as archive:
    old_classes = {m.name.removeprefix('classes/'): identity(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile() and m.name.startswith('classes/') and m.name.endswith('.class')}
assert old_classes == receipt['classes']
assert {pathlib.PurePosixPath(k).name: identity(v) for k, v in contents.items() if k.startswith('AppearanceConsumer/Generated/MixerAndroid/app/src/') and k.endswith('.java')} == old['exported_java']
selection = ROOT / 'verification/android-default-appearance-packaging-root-review/implementation-selection.json'
assert file_identity(selection)['sha256'] == '30171f00f98ed7e27c8f9654f0c997a7c9672e282697a7a4c8fa7bfca1d98582'
assert not receipt['native_runtime_or_capture_started'] and not receipt['GA_qualified']
print(json.dumps({'status': 'producer-offline-bindings-pass-awaiting-independent-review',
                  'commands_bound': len(receipt['commands']), 'first_party_files_bound': len(before['files']),
                  'generated_source_files_bound': len(generated), 'accepted_java_sources': len(old['exported_java']),
                  'accepted_classes_bound': len(old_classes), 'apk_members_bound': len(inventory),
                  'descriptor': receipt['final_descriptor'], 'native_runtime_or_capture_started': False, 'GA_qualified': False}, indent=2))
