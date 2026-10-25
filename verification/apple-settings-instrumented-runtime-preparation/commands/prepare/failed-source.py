#!/usr/bin/env python3
"""Prepare/verify without native activity; dispatch requires separate root review."""
import argparse
import contextlib
import datetime
import difflib
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile
import tempfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRIOR = ROOT / 'verification/apple-focus-reference-runtime-v5-namespace-correction'
BUILD = ROOT / 'verification/apple-settings-instrumented-native-build'
BUILD_ATTEMPT = BUILD / 'attempt-1'
BUILD_HANDOFF = '246f5e9486f804d2ab784ba474696bcf7905873aa5a1200117b570bd66933e91'
PRIOR_PACKET = '6c57bc5552a4f7e0e21ff1fdd589b270aa98b483f366f78bd88de2e26c0fd7dc'
ACCEPTANCE = '9956f0384828da9cdd8082ca387716c439131f6a2f0c4fcde4065cc5c96995ff'
PRODUCT = 'c3e696b102d0a5daefa928e2941437739c5c418eb876dc31a65f0acef8e6e924'
SOURCE = '2b44b02dbd702becefa8b609435928890ad7c1a5f7cb11b3cc0fd1f5000ca101'
OLD_SOURCE = '696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a'
OLD_PRODUCT = '0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8'
OUTPUT_PREFIX = 'native-run-v6-'
SOURCES = ['prepare.py', 'run_controls.py', 'record_command.py', 'seal.py', 'local_first_failure.py']
ARTIFACTS = ['adapter.py', 'importer.py', 'selection-template.json', 'source-delta.patch',
             'runtime-source-manifest.json', 'runtime-sources.tar.gz']

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


def manifest(payload):
    return {name: {'kind': 'file', 'mode': 0o644, 'bytes': len(raw), 'sha256': sha(raw)}
            for name, raw in sorted(payload.items())}


def archive_payload(path, rows, expected_sha, prefix=''):
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
    require(set(payload) == set(rows) and directories == expected_dirs, 'Exact archive inventory required')
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


def archive_sources(path, source, rows):
    require(tree(source) == rows and not path.exists(), 'Exact fresh archive source required')
    directories = {'selected'} | {str(parent) for name in rows
                                  for parent in PurePosixPath('selected/' + name).parents if str(parent) != '.'}
    with path.open('xb') as target, gzip.GzipFile(fileobj=target, mode='wb', filename='', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as archive:
            for name in sorted(directories):
                info = tarfile.TarInfo(name); info.type = tarfile.DIRTYPE; info.mode = 0o755
                archive.addfile(info)
            for name, expected in sorted(rows.items()):
                raw = (source / name).read_bytes()
                info = tarfile.TarInfo('selected/' + name); info.mode = expected['mode']; info.size = len(raw)
                archive.addfile(info, io.BytesIO(raw))
    result = {'schema': 1, 'scope': 'Instrumented Settings runtime selected source closure',
              'files': rows, 'treeSHA256': sha(stable(rows)), 'archive': row(path),
              'directories': sorted(directories), 'directoryMode': 0o755}
    require(archive_payload(path, rows, result['archive']['sha256'], 'selected/')
            == {name: (source / name).read_bytes() for name in rows}, 'Archive round-trip differs')
    return result


def references():
    """Verify only direct accepted inputs; never load a historical producer."""
    bindings = {}
    def bind(path, expected=None):
        value = row(path)
        require(expected is None or value['sha256'] == expected, 'Accepted input identity differs: ' + str(path))
        bindings[str(path.relative_to(ROOT))] = value
        return value
    bind(BUILD / 'handoff.json', BUILD_HANDOFF)
    build = json.loads((BUILD / 'handoff.json').read_bytes())
    require(build['status'] == 'compiled-generic-simulator-runner-only'
            and build['nativeExecuted'] is False and build['originalApplicationFilesUnchanged'] == 13,
            'Fresh build scope differs')
    require(len(build['members']) == 22, 'Exact 22-member fresh build handoff required')
    for name, expected in build['members'].items():
        safe_name(name)
        require(row(ROOT / name) == expected, 'Fresh build member changed: ' + name)
        bindings[name] = expected
    bind(ROOT / 'verification/apple-settings-failure-instrumentation-root-review/acceptance.json', ACCEPTANCE)
    acceptance = json.loads((ROOT / 'verification/apple-settings-failure-instrumentation-root-review/acceptance.json').read_bytes())
    require(acceptance['status'] == 'accepted-diagnostic-source-host-and-full-uikit-typecheck'
            and acceptance['nativeRuntimeExecuted'] is False, 'Instrumentation acceptance differs')
    bind(PRIOR / 'packet.json', PRIOR_PACKET)
    prior = json.loads((PRIOR / 'packet.json').read_bytes())
    for name in ['runtime-source-manifest.json', 'runtime-sources.tar.gz', 'adapter.py',
                 'importer.py', 'selection-template.json']:
        require(row(PRIOR / name) == prior['files'][name], 'Prior runtime selected artifact changed: ' + name)
        bindings[str((PRIOR / name).relative_to(ROOT))] = prior['files'][name]
    decision_path = ROOT / 'verification/apple-focus-reference-runtime-v5-namespace-root-review/decision.json'
    bind(decision_path, '28f15af5591522df9c9708c1ade1619df8df65ab5bebc6eb34d44c27d65a807f')
    decision = json.loads(decision_path.read_bytes())
    require(decision['status'] == 'source-and-host-packaging-accepted'
            and decision['packetSHA256'] == PRIOR_PACKET, 'Prior root runtime review differs')
    source = json.loads((BUILD_ATTEMPT / 'source-manifest.json').read_bytes())
    require(len(source['sources']) == 40 and sha(stable(source['sources'])) == SOURCE,
            'Exact fresh compile source identity differs')
    accepted = archive_payload(BUILD_ATTEMPT / 'accepted-sources.tar.gz', source['sources'], source['archive']['sha256'])
    for name, digest in acceptance['sourceFiles'].items():
        require(sha(accepted['accepted/harness/UITests/' + name]) == digest,
                'Fresh runner source differs from root acceptance: ' + name)
    products = json.loads((BUILD_ATTEMPT / 'product-manifest.json').read_bytes())
    require(len(products['products']) == 55 and products['archive']['sha256'] == PRODUCT
            and products['originalApplicationFilesUnchanged'] == 13 and products['runnerRebuilt'] is True,
            'Fresh native product manifest differs')
    require(sha(stable(products['products'])) == products['productTreeSHA256'], 'Fresh product tree digest differs')
    archive_payload(BUILD_ATTEMPT / 'products.tar.gz', products['products'], PRODUCT)
    return bindings


def prior_payload():
    source = json.loads((PRIOR / 'runtime-source-manifest.json').read_bytes())
    return archive_payload(PRIOR / 'runtime-sources.tar.gz', source['files'], source['archive']['sha256'], 'selected/')


def replace_once(raw, before, after):
    require(raw.count(before) == 1, 'Exactly one bound source replacement required')
    return raw.replace(before, after, 1)


def derived_payload():
    original = prior_payload()
    selected = dict(original)
    # Closed identity updates only. No importer arithmetic or evidence predicate changes.
    selected['importer.py'] = original['importer.py']
    for before, after in [(OLD_SOURCE, SOURCE), (OLD_PRODUCT, PRODUCT),
                          ('mixer.apple-focus-reference-root-selection.5', 'mixer.apple-focus-reference-root-selection.6'),
                          ('MixerFocusReferenceV5-', 'MixerFocusReferenceV6-'),
                          ('mixer.apple-focus-reference-runtime-import.5', 'mixer.apple-focus-reference-runtime-import.6')]:
        selected['importer.py'] = replace_once(selected['importer.py'], before.encode(), after.encode())
    adapter = (PRIOR / 'adapter.py').read_bytes()
    adapter = replace_once(adapter, b"'native-run-v5-'", b"'native-run-v6-'")
    adapter = replace_once(adapter, b"'mixer.apple-focus-reference-runtime.5'", b"'mixer.apple-focus-reference-runtime.6'")
    adapter = replace_once(adapter, b'import auxiliary_inventory\n', b'import auxiliary_inventory\nimport local_first_failure\n')
    old = b'    result = _ORIGINAL_RUN_OBSERVED(commands,argv,timeout,check,retained_stdout_filter)\n'
    new = (b'    try:\n        result = _ORIGINAL_RUN_OBSERVED(commands,argv,timeout,check,retained_stdout_filter)\n'
           b'    finally:\n        local_first_failure.capture(_selected[\'session\'],_ROOT)\n')
    adapter = replace_once(adapter, old, new)
    require(original['join_support.py'].endswith((PRIOR / 'adapter.py').read_bytes()), 'Prior selected adapter suffix differs')
    selected['join_support.py'] = original['join_support.py'][:-len((PRIOR / 'adapter.py').read_bytes())] + adapter
    selected['local_first_failure.py'] = (BASE / 'local_first_failure.py').read_bytes()
    composition = selected['composition.py']
    composition = replace_once(composition, b'import auxiliary_inventory\n', b'import auxiliary_inventory\nimport local_first_failure\n')
    composition = replace_once(composition, b',reference_contract,auxiliary_inventory]', b',reference_contract,auxiliary_inventory,local_first_failure]')
    selected['composition.py'] = composition
    return selected, adapter


def selection_template(selected):
    selection = json.loads((PRIOR / 'selection-template.json').read_bytes())
    # These fields are overwritten with exact owned dispatch paths at staging.
    selection['productArchive'] = str(BUILD_ATTEMPT / 'products.tar.gz')
    selection['productManifest'] = json.loads((BUILD_ATTEMPT / 'product-manifest.json').read_bytes())
    selection['files'] = {name: sha(raw) for name, raw in selected.items()}
    selection['moduleAliases']['local_first_failure'] = 'local_first_failure.py'
    return selection


def prepare():
    require(not (BASE / 'packet.json').exists(), 'Preserve the first prepared packet')
    bound = references()
    selected, adapter = derived_payload()
    scratch = Path(tempfile.mkdtemp(prefix='prepare-owned-', dir=BASE))
    try:
        rows = manifest(selected)
        materialize(scratch / 'selected', rows, selected)
        archive = archive_sources(BASE / 'runtime-sources.tar.gz', scratch / 'selected', rows)
    finally:
        shutil.rmtree(scratch)
    patch = ''
    original = prior_payload()
    for name in sorted(selected):
        if selected[name] != original.get(name):
            patch += ''.join(difflib.unified_diff(original.get(name, b'').decode().splitlines(True),
                              selected[name].decode().splitlines(True), fromfile='accepted-v5/' + name,
                              tofile='instrumented-v6/' + name))
    for name, raw in [('adapter.py', adapter), ('importer.py', selected['importer.py']),
                      ('selection-template.json', stable(selection_template(selected))),
                      ('source-delta.patch', patch.encode()), ('runtime-source-manifest.json', stable(archive))]:
        with (BASE / name).open('xb') as stream:
            stream.write(raw)
    changed = sorted(name for name in selected if selected[name] != original.get(name))
    packet = {'schema': 'mixer.apple-settings-instrumented-runtime-packet.1',
              'scope': 'Host preparation only; separate source review and fresh root selection required',
              'references': bound, 'sourceRevisionContext': '8b9b4950d23fd4595018deb751395e6bcc27d3e4',
              'sourceRevisionMeaning': 'Inherited fresh-build receipt label; no Git query; exact hashes authoritative',
              'sourceTreeSHA256': SOURCE, 'sourceTreeMeaning': 'SHA256 of stable 40-member fresh source manifest sources',
              'nativeProductArchiveSHA256': PRODUCT, 'runtimeSourceTreeSHA256': archive['treeSHA256'],
              'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.6',
              'simulatorNamePrefix': 'MixerFocusReferenceV6-', 'changedSelectedFiles': changed,
              'unchangedSelectedFiles': len(original) - len([n for n in original if selected[n] != original[n]]),
              'selectedFiles': len(selected), 'files': {name: row(BASE / name) for name in SOURCES + ARTIFACTS},
              'nativeExecuted': False, 'runtimeSelected': False, 'compileRerun': False,
              'gaAccepted': False, 'physicalPhones': 'disconnected-deferred'}
    with (BASE / 'packet.json').open('xb') as stream:
        stream.write(stable(packet))
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'packetSHA256': sha(stable(packet)), 'referencesVerified': len(bound),
               'sourceTreeSHA256': SOURCE, 'runtimeSourceTreeSHA256': archive['treeSHA256'],
               'selectedFiles': len(selected), 'changedSelectedFiles': changed,
               'ownedPreparationScratchAbsent': not scratch.exists(), 'nativeInstancesCreatedOrQueried': 0,
               'nativeExecuted': False, 'compilerExecuted': False, 'listenerStarted': False,
               'output': 'PASS: instrumented Settings runtime packet prepared; no native execution'}
    with (BASE / 'preparation-receipt.json').open('xb') as stream:
        stream.write(stable(receipt))
    print(receipt['output'])


def verify():
    packet = json.loads((BASE / 'packet.json').read_bytes())
    require(references() == packet['references'], 'Accepted input bindings changed')
    for name, expected in packet['files'].items():
        require(row(BASE / name) == expected, 'Prepared member changed: ' + name)
    source = json.loads((BASE / 'runtime-source-manifest.json').read_bytes())
    selected = archive_payload(BASE / 'runtime-sources.tar.gz', source['files'], source['archive']['sha256'], 'selected/')
    expected, adapter = derived_payload()
    require(selected == expected and (BASE / 'adapter.py').read_bytes() == adapter,
            'Selected derivation differs')
    require((BASE / 'importer.py').read_bytes() == selected['importer.py'], 'Local importer differs')
    require(json.loads((BASE / 'selection-template.json').read_bytes()) == selection_template(selected),
            'Exact fresh selection template differs')
    require(sha(stable(source['files'])) == source['treeSHA256'] == packet['runtimeSourceTreeSHA256'],
            'Runtime source tree digest differs')
    return {'packetSHA256': sha((BASE / 'packet.json').read_bytes()), 'nativeExecuted': False,
            'scope': 'Exact accepted inputs, source derivation, archive inventory/modes and products'}


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
    payload = archive_payload(BASE / 'runtime-sources.tar.gz', source['files'], source['archive']['sha256'], 'selected/')
    product_payload = archive_payload(BUILD_ATTEMPT / 'products.tar.gz', products['products'], PRODUCT)
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'verify', 'dispatch'])
    parser.add_argument('--reviewed-packet'); parser.add_argument('--root-selection'); parser.add_argument('--root-selection-sha256')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'verify':
        print(json.dumps(verify(), sort_keys=True))
    else:
        dispatch(args.reviewed_packet, args.root_selection, args.root_selection_sha256)

