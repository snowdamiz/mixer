#!/usr/bin/env python3
"""Fresh accepted packet binding; historical dispatcher grants no authority."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile

HERE = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/apple-settings-runtime-r2')
ROOT = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4')
BASE = Path('/private/tmp/mixer-20261107-apple-settings-runtime-agcvpnc6')
ROOT_SELECTION = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/apple-settings-root-selection.json')
ROOT_SELECTION_SHA = '952ba83a47f0bd93d86670acf225058349fe56da27b8a7ca0631233e36d8d99c'
BUILD_ATTEMPT = Path('/Users/andreyyurlov/Documents/dev/mixer/verification/apple-passive-lifecycle-sendable-correction/build-attempt-1/products.tar.gz').parent
PRODUCT = '495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904'
OUTPUT_PREFIX = 'native-run-v9-'
PINS = {'candidatePacket': '76d499c09102741e1975ef6dd8a48b7c4b4897c3dc6a5a8fa64dfb7dd2345618', 'review': 'c81db0d3c29f21d629f127358178d7592060a1980a4109561fa20fa8082261b6', 'runtimeArchive': '4adaecd0194bfef54f293c0939d7489c19f81c8fe5df03dff83439445dacc7e9', 'selectionTemplate': '4468517e8ad7b6e8ad7914fe725db1115dbfc0987a15f1fa8f60c9d5009cd202', 'retainedProducts': '495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904'}

def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def row(path):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            'Canonical single-link regular file required: ' + str(path))
    raw = path.read_bytes()
    return {'kind': 'file', 'mode': stat.S_IMODE(info.st_mode), 'bytes': len(raw), 'sha256': sha(raw)}


def safe_name(name):
    path = PurePosixPath(name)
    require(type(name) is str and name and not path.is_absolute() and '..' not in path.parts
            and str(path) == name, 'Canonical relative archive path required')
    return path


def archive_payload(path, rows, expected_sha, prefix='', explicit_directories=True):
    require(row(path)['sha256'] == expected_sha, 'Archive SHA-256 changed: ' + str(path))
    expected_dirs = {prefix.rstrip('/')} if prefix else set()
    for name in rows:
        safe_name(name)
        expected_dirs.update(str(parent) for parent in PurePosixPath(prefix + name).parents
                             if str(parent) != '.')
    payload, directories, seen = {}, set(), set()
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive.getmembers():
            name = member.name
            safe_name(name)
            require(name not in seen, 'Duplicate archive member')
            seen.add(name)
            if member.isdir():
                require(member.mode == 0o755, 'Archive directory mode differs')
                directories.add(name)
                continue
            require(member.isfile() and name.startswith(prefix), 'Unexpected archive member type/path')
            relative = name[len(prefix):]
            require(relative in rows, 'Unlisted archive file: ' + relative)
            raw = archive.extractfile(member).read()
            require({'kind': 'file', 'mode': member.mode, 'bytes': len(raw), 'sha256': sha(raw)} == rows[relative],
                    'Archive file differs: ' + relative)
            payload[relative] = raw
    require(set(payload) == set(rows) and directories == (expected_dirs if explicit_directories else set()),
            'Exact archive inventory required')
    return payload


def tree(path):
    require(path.resolve() == path and path.is_dir() and not path.is_symlink()
            and stat.S_IMODE(path.stat().st_mode) == 0o755, 'Canonical product/source root required')
    rows, directories = {}, set()
    for item in sorted(path.rglob('*')):
        require(not item.is_symlink(), 'Archive tree redirection refused')
        if item.is_file():
            rows[str(item.relative_to(path))] = row(item)
        else:
            require(item.is_dir() and stat.S_IMODE(item.stat().st_mode) == 0o755, 'Unexpected tree directory')
            directories.add(str(item.relative_to(path)))
    implied = {str(parent) for name in rows for parent in PurePosixPath(name).parents if str(parent) != '.'}
    require(directories == implied, 'Tree directory inventory differs')
    return rows


def materialize(destination, rows, payload):
    require(not destination.exists() and not destination.is_symlink()
            and destination.resolve() == destination, 'Fresh canonical materialization required')
    require(set(rows) == set(payload), 'Materialization inventory differs')
    destination.mkdir(mode=0o755)
    for name, expected in sorted(rows.items()):
        safe_name(name)
        raw = payload[name]
        require(expected['kind'] == 'file' and len(raw) == expected['bytes'] and sha(raw) == expected['sha256'],
                'Materialization bytes differ: ' + name)
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        for directory in [path.parent, *path.parent.parents]:
            if directory == destination.parent:
                break
            directory.chmod(0o755)
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(expected['mode'])
    require(tree(destination) == rows, 'Materialization changed bytes/modes')


def load_baseline():
    path = HERE/'sealed-inputs/verification/apple-passive-lifecycle-runtime-preparation/prepare.py'
    spec = importlib.util.spec_from_file_location('_sealed_baseline_verify', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.BUILD_ATTEMPT = BUILD_ATTEMPT
    return module

def verify():
    require(row(ROOT_SELECTION)['sha256'] == ROOT_SELECTION_SHA, 'Root selection changed')
    selected = json.loads(ROOT_SELECTION.read_bytes())
    for name, digest in PINS.items():
        require(selected[name]['sha256'] == digest and row(ROOT/selected[name]['path'])['sha256'] == digest,
                'Accepted root artifact changed: '+name)
    require(selected['nativeAttemptBudget']['selectedNow'] == 1 and not selected['nativeAttemptBudget']['automaticRetry']
            and selected['fixedSettingsBudgetSeconds'] == 29 and selected['rebuild'] is False
            and selected['tests'] == ['test000PublicSettingsFullKeyboardAccess','test010ReferenceFirstTab'],
            'Exact root attempt/budget/test selection required')
    packet_raw = (HERE/'packet.json').read_bytes()
    require((BASE/'packet.json').read_bytes() == packet_raw, 'Concrete packet changed')
    packet = json.loads(packet_raw)
    require(packet['rootSelectionSHA256'] == ROOT_SELECTION_SHA and packet['acceptedBindings'] == selected,
            'Successor packet root authorization differs')
    for name, expected in packet['files'].items():
        require(row(HERE/name) == expected, 'Successor driver changed: '+name)
    baseline = load_baseline()
    baseline_verified = baseline.verify()
    require(baseline_verified['packetSHA256'] == packet['baselinePacketSHA256'], 'Baseline source/product safeguards changed')
    candidate = json.loads((ROOT/selected['candidatePacket']['path']).read_bytes())
    review = json.loads((ROOT/selected['review']['path']).read_bytes())
    require(review['blockingFindings'] == [] and review['candidatePacketSHA256'] == PINS['candidatePacket']
            and review['candidateRuntimeArchiveSHA256'] == PINS['runtimeArchive']
            and review['candidateSelectionTemplateSHA256'] == PINS['selectionTemplate'], 'Independent acceptance differs')
    for key in ['baselineCompileArchive','baselineNativeHandoff','baselineNativeResult','baselineRuntimeArchive',
                'candidateSelectionTemplate','productArchive','runtimeArchive']:
        binding = candidate[key]
        actual = row(ROOT/binding['path'])
        require(actual['sha256'] == binding['sha256'] and actual['bytes'] == binding['bytes'], 'Candidate artifact changed: '+key)
    source = json.loads((BASE/'runtime-source-manifest.json').read_bytes())
    require(source['files'] == candidate['runtimeFiles'] and len(source['files']) == 32
            and sha(stable(source['files'])) == source['treeSHA256']
            and source['archive']['sha256'] == PINS['runtimeArchive'], 'Accepted runtime manifest differs')
    payload = archive_payload(BASE/'runtime-sources.tar.gz',source['files'],PINS['runtimeArchive'],'selected/',explicit_directories=False)
    old_manifest = json.loads((baseline.BASE/'runtime-source-manifest.json').read_bytes())
    old_payload = baseline.archive_payload(baseline.BASE/'runtime-sources.tar.gz', old_manifest['files'],
                                          old_manifest['archive']['sha256'],'selected/')
    changed = [n for n in sorted(payload) if payload[n] != old_payload[n]]
    require(set(payload) == set(old_payload) and changed == candidate['changedRuntimeFiles']
            and len(changed) == 1 and len(payload)-len(changed) == 31, 'Only accepted Python receiver delta allowed')
    template_raw = (ROOT/selected['selectionTemplate']['path']).read_bytes()
    require((BASE/'selection-template.json').read_bytes() == template_raw, 'Exact accepted selection bytes required')
    template = json.loads(template_raw)
    old_template = json.loads((baseline.BASE/'selection-template.json').read_bytes())
    old_template['files'] = {n:sha(raw) for n,raw in payload.items()}
    require(template == old_template, 'Template changed beyond accepted source binding')
    require((BASE/'importer.py').read_bytes() == payload['importer.py'], 'Original importer differs')
    products = json.loads((BUILD_ATTEMPT/'product-manifest.json').read_bytes())
    require(template['productManifest'] == products and products['sourceTreeSHA256'] == candidate['sourceTreeSHA256']
            and len(products['products']) == 55 and candidate['compileSourceFilesByteIdentical'] == 42
            and candidate['settingsBudgetSeconds'] == 29 and candidate['observationBudgetSeconds'] == 3
            and candidate['originalSettingsOracleUnchanged'] and candidate['originalTabOracleUnchanged']
            and candidate['appAndUITestRunnerRebuildRequired'] is False, 'Retained product/oracle/budget contracts differ')
    archive_payload(BUILD_ATTEMPT/'products.tar.gz',products['products'],PRODUCT,explicit_directories=False)
    return dict(packetSHA256=sha(packet_raw), nativeExecuted=False,
                scope='Fresh root-selected accepted receiver; exact baseline safeguards and retained products')

def dispatch(reviewed_packet, selection_path, selected_sha):
    """This explicit root action is never called without host recorders in controls."""
    verified = verify()
    require(reviewed_packet == verified['packetSHA256'], 'Root reviewed packet hash differs')
    spec = importlib.util.spec_from_file_location('_root_selection_guard', BASE / 'importer.py')
    importer = importlib.util.module_from_spec(spec); spec.loader.exec_module(importer)
    selection_path = Path(selection_path)
    require(row(selection_path)['sha256'] == selected_sha, 'Out-of-band root selection hash differs')
    root = importer.validate_root(importer.parse(selection_path.read_bytes()), reviewed_packet, fresh=True)
    output = BASE / (OUTPUT_PREFIX + root['runID'])
    require(not output.exists() and not output.is_symlink(), 'Fresh output required; never replay a run')
    # A durable no-retry marker precedes product/source materialization and import.
    markers = BASE / 'dispatch-attempts'
    markers.mkdir(exist_ok=True, mode=0o755)
    require(markers.resolve() == markers and not markers.is_symlink() and markers.is_dir(), 'Canonical attempt marker directory required')
    marker = markers / (root['runID'] + '.json')
    descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(stable({'schema': 1, 'runID': root['runID'], 'packetSHA256': reviewed_packet,
                             'rootSelectionSHA256': selected_sha, 'oneAttemptOnly': True})); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(markers, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    output.mkdir(mode=0o755)
    source = json.loads((BASE / 'runtime-source-manifest.json').read_bytes())
    products = json.loads((BUILD_ATTEMPT / 'product-manifest.json').read_bytes())
    payload = archive_payload(BASE / 'runtime-sources.tar.gz', source['files'], source['archive']['sha256'], 'selected/', explicit_directories=False)
    product_payload = archive_payload(BUILD_ATTEMPT / 'products.tar.gz', products['products'], PRODUCT, explicit_directories=False)
    materialize(output / 'selected', source['files'], payload)
    materialize(output / 'products', products['products'], product_payload)
    selection = json.loads((BASE / 'selection-template.json').read_bytes())
    selection.update(repositoryRoot=str(ROOT), outputBase=str(output), productsRoot=str(output / 'products'),
                     trustedRootSelection=root)
    with (output / 'selected/runtime-selection.json').open('xb') as stream:
        stream.write(stable(selection))
    with (output / 'root-selection.json').open('xb') as stream:
        stream.write(selection_path.read_bytes())
    sys.path.insert(0, str(output / 'selected'))
    spec = importlib.util.spec_from_file_location('composition', output / 'selected/composition.py')
    module = importlib.util.module_from_spec(spec); sys.modules['composition'] = module
    try:
        spec.loader.exec_module(module)
        return module.h.run(sha((output / 'selected/runtime-selection.json').read_bytes()))
    finally:
        good = (tree(output / 'products') == products['products']
                and all((output / 'selected' / name).read_bytes() == raw for name, raw in payload.items()))
        receipt = {'verifiedBeforeRemoval': good, 'paths': [str(output / 'products'), str(output / 'selected')],
                   'scope': 'Packet-owned source/product scratch only; results and observations retained'}
        if good:
            shutil.rmtree(output / 'products'); shutil.rmtree(output / 'selected')
        receipt['scratchAbsent'] = not (output / 'products').exists() and not (output / 'selected').exists()
        with (output / 'scratch-cleanup.json').open('xb') as stream:
            stream.write(stable(receipt))

