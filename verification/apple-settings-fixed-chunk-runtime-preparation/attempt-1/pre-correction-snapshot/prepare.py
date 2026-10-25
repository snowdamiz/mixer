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
PRIOR = ROOT / 'verification/apple-settings-instrumented-runtime-preparation'
BUILD = ROOT / 'verification/apple-settings-fixed-chunk-native-build'
BUILD_ATTEMPT = BUILD / 'attempt-1'
BUILD_HANDOFF = '3e6dc04dd9d2f314f3ccf5a9dc363e88c327936f2e9719b9365000f81859cc21'
PRIOR_PACKET = 'f7ef1ed54b65a71e666646d1e4b54cef1cea5b7afdfee804810ffaf2c65eaeb6'
ACCEPTANCE = 'ddeda29f57c16a6e71a809ce43a90e7a89d1a110b6a2094580d0badc57c9f76c'
PRODUCT = 'cca8472579ed6ce7c3c00babadb44d37ba34dc1a400ec00fc7802536342d7a2c'
SOURCE = '0677712483e4f078cbd10120efd5c9f9d4a13fe31b9f455caa1a984772d2bfeb'
OLD_SOURCE = '2b44b02dbd702becefa8b609435928890ad7c1a5f7cb11b3cc0fd1f5000ca101'
OLD_PRODUCT = 'c3e696b102d0a5daefa928e2941437739c5c418eb876dc31a65f0acef8e6e924'
OUTPUT_PREFIX = 'native-run-v7-'
SOURCES = ['prepare.py', 'run_controls.py', 'record_command.py', 'seal.py', 'local_first_failure.py', 'bootstrap.py']
ENDPOINT = ROOT / 'verification/apple-settings-fixed-chunk-implementation'
RECEIVER = 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
REVIEW_ARCHIVE = '585f44532cb67ca626ae7c2c95bfa7030408bf2b4dc57f5bac0fdbd84cea66af'
COMPILE_ARCHIVE = '96cf2e6d4356035e004564a2a4d4e01122fb570835e4089c6c83788ab53465f8'
PRODUCT_TREE = '58835bb84bfdf801a395a237c6ea6dfdd746ca005c9533736ec2ee5cf80fa4b8'
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
    result = {'schema': 1, 'scope': 'Fixed4992 Settings V7 runtime selected source closure',
              'files': rows, 'treeSHA256': sha(stable(rows)), 'archive': row(path),
              'directories': sorted(directories), 'directoryMode': 0o755}
    require(archive_payload(path, rows, result['archive']['sha256'], 'selected/')
            == {name: (source / name).read_bytes() for name in rows}, 'Archive round-trip differs')
    return result


def references():
    """Bind accepted V6 composition, reviewed receiver and exact fresh build only."""
    bindings = {}
    def bind(path, expected=None):
        actual = row(path)
        require(expected is None or actual['sha256'] == expected, 'Accepted input identity differs: ' + str(path))
        bindings[str(path.relative_to(ROOT))] = actual
        return actual
    def sealed(path, digest, required_count=None):
        bind(path, digest)
        value = json.loads(path.read_bytes())
        if required_count is not None:
            require(len(value['members']) == required_count, 'Accepted sealed inventory differs')
        for name, expected in value['members'].items():
            safe_name(name)
            # Do not traverse a named but unselected lane through a handoff.
            require(not any(word in name.lower() for word in ('catalog-inspector', 'authority-driver', 'worker-transport')),
                    'Excluded handoff lane refused')
            actual = row(ROOT / name)
            require(set(expected) <= {'kind', 'mode', 'bytes', 'sha256'}
                    and all(actual[key] == item for key, item in expected.items()), 'Accepted sealed member changed: ' + name)
            bindings[name] = actual
        return value
    prior_seal = sealed(PRIOR / 'handoff.json', 'ca361bde1632c4ad4bbaf517817b9d8a5a9426a25d462738a9e03eeeb1786a3c', 61)
    require(prior_seal['packetSHA256'] == PRIOR_PACKET and prior_seal['nativeExecuted'] is False,
            'Accepted V6 preparation scope differs')
    bind(PRIOR / 'packet.json', PRIOR_PACKET)
    prior = json.loads((PRIOR / 'packet.json').read_bytes())
    require(prior['selectedFiles'] == 32, 'Accepted V6 runtime file count differs')
    for name in ['runtime-source-manifest.json', 'runtime-sources.tar.gz', 'adapter.py', 'importer.py', 'selection-template.json']:
        require(row(PRIOR / name) == prior['files'][name], 'Accepted V6 artifact differs: ' + name)
    review_root = ROOT / 'verification/apple-settings-instrumented-runtime-review'
    bind(review_root / 'handoff.json', 'dbfcd7c074acbe63b27bd26a94d77f72c494fa4fdc8b0f9b6792aa2d83da049f')
    accepted_review = json.loads((review_root / 'handoff.json').read_bytes())
    for name in ['verification/apple-settings-instrumented-runtime-review/review.json',
                 'docs/apple-settings-instrumented-runtime-review.md']:
        expected = accepted_review['members'][name]
        require(row(ROOT / name) == expected, 'Accepted V6 independent review differs')
        bindings[name] = expected
    decision = json.loads((review_root / 'review.json').read_bytes())
    require(decision['status'] == 'source-and-host-packaging-accepted' and decision['blockingFindings'] == []
            and decision['packetSHA256'] == PRIOR_PACKET and decision['nativeSelected'] is False,
            'Accepted V6 independent decision differs')
    bind(BUILD / 'handoff.json', BUILD_HANDOFF)
    build = sealed(BUILD / 'handoff.json', BUILD_HANDOFF, 42)
    require(build['nativeExecuted'] is False and build['nativeExecutionSelected'] is False
            and build['sourceFiles'] == 40 and build['products'] == 55
            and build['runnerProductFilesFresh'] == 42 and build['originalApplicationFilesUnchanged'] == 13
            and build['sourceTreeSHA256'] == SOURCE and build['productTreeSHA256'] == PRODUCT_TREE
            and build['sourceArchiveSHA256'] == COMPILE_ARCHIVE and build['productArchiveSHA256'] == PRODUCT
            and build['warningLines'] == 15 and build['allWarningMessagesMatchOriginalAndPrior'] is True,
            'Accepted fresh build scope differs')
    accept_path = ROOT / 'verification/apple-settings-fixed-chunk-build-root-review/acceptance.json'
    bind(accept_path, ACCEPTANCE)
    acceptance = json.loads(accept_path.read_bytes())
    require(acceptance['buildAccepted'] is True and acceptance['hostRuntimePreparationSelected'] is True
            and acceptance['nativeExecutionSelected'] is False and acceptance['handoffSHA256'] == BUILD_HANDOFF
            and acceptance['sourceRevision'] == 'be472ce6424a691de5673e3438d2768264827d23', 'Root build acceptance differs')
    bind(ENDPOINT / 'handoff.json', '2d01866f3fa0f88b283ba8f2774f03092eb93d9616daeaa7d5d2875618cf6748')
    endpoint_seal = json.loads((ENDPOINT / 'handoff.json').read_bytes())
    for name in ['source-package-manifest.json', 'source-bindings.json', 'review-source-package.tar.gz']:
        path = ENDPOINT / name
        expected = endpoint_seal['members'][str(path.relative_to(ROOT))]
        actual = bind(path)
        require(all(actual[key] == item for key, item in expected.items()), 'Reviewed source artifact differs')
    require(bind(ENDPOINT / 'review-source-package.tar.gz')['sha256'] == REVIEW_ARCHIVE, 'Reviewed endpoint archive differs')
    endpoint_review = ROOT / 'verification/apple-settings-fixed-chunk-review'
    bind(endpoint_review / 'handoff.json', '43f2ee87e461d28a8d05d113adf7a9581ea34c6d16e0dfe5caee26773febc092')
    endpoint_review_seal = json.loads((endpoint_review / 'handoff.json').read_bytes())
    for name in ['verification/apple-settings-fixed-chunk-review/review.json', 'docs/apple-settings-fixed-chunk-review.md']:
        actual = bind(ROOT / name)
        require(all(actual[key] == item for key, item in endpoint_review_seal['members'][name].items()),
                'Accepted fixed4992 independent review differs')
    endpoint_decision = json.loads((endpoint_review / 'review.json').read_bytes())
    require(endpoint_decision['status'] == 'ACCEPTED_SCOPED' and endpoint_decision['findings'] == []
            and endpoint_decision['producerSourceArchiveSHA256'] == REVIEW_ARCHIVE, 'Receiver review decision differs')
    source = json.loads((BUILD_ATTEMPT / 'source-manifest.json').read_bytes())
    require(len(source['sources']) == 40 and sha(stable(source['sources'])) == SOURCE
            and source['archive']['sha256'] == COMPILE_ARCHIVE, 'Exact fresh compile closure differs')
    accepted = archive_payload(BUILD_ATTEMPT / 'accepted-sources.tar.gz', source['sources'], COMPILE_ARCHIVE, explicit_directories=False)
    reviewed = reviewed_payload()
    for name, raw in accepted.items():
        require(raw == reviewed['sources/' + name], 'Fresh compile source differs from reviewed endpoint package: ' + name)
    products = json.loads((BUILD_ATTEMPT / 'product-manifest.json').read_bytes())
    require(len(products['products']) == 55 and products['archive']['sha256'] == PRODUCT
            and products['originalApplicationFilesUnchanged'] == 13 and products['runnerProductsFresh'] is True
            and products['runnerProductFiles'] == 42 and products['sourceTreeSHA256'] == SOURCE,
            'Exact fresh product closure differs')
    require(sha(stable(products['products'])) == products['productTreeSHA256'] == PRODUCT_TREE,
            'Fresh product tree identity differs')
    archive_payload(BUILD_ATTEMPT / 'products.tar.gz', products['products'], PRODUCT, explicit_directories=False)
    return bindings


def reviewed_payload():
    rows = json.loads((ENDPOINT / 'source-package-manifest.json').read_bytes())
    require(len(rows) == 97 and row(ENDPOINT / 'review-source-package.tar.gz')['sha256'] == REVIEW_ARCHIVE,
            'Exact reviewed package required')
    payload = {}
    with tarfile.open(ENDPOINT / 'review-source-package.tar.gz', 'r:gz') as archive:
        for member in archive.getmembers():
            safe_name(member.name)
            require(member.isfile() and member.name.startswith('package/'), 'Reviewed package regular file required')
            name = member.name[len('package/'):]
            require(name in rows and name not in payload, 'Unlisted/duplicate reviewed member')
            raw = archive.extractfile(member).read()
            require({'kind': 'file', 'mode': member.mode, 'bytes': len(raw), 'sha256': sha(raw)} == rows[name],
                    'Reviewed package member differs: ' + name)
            payload[name] = raw
    require(set(payload) == set(rows), 'Reviewed package inventory differs')
    return payload


def prior_payload():
    source = json.loads((PRIOR / 'runtime-source-manifest.json').read_bytes())
    return archive_payload(PRIOR / 'runtime-sources.tar.gz', source['files'], source['archive']['sha256'], 'selected/')


def replace_once(raw, before, after):
    require(raw.count(before) == 1, 'Exactly one bound source replacement required')
    return raw.replace(before, after, 1)


def derived_payload():
    original = prior_payload()
    require(len(original) == 32, 'Exact approved V6 composition required')
    selected = dict(original)
    reviewed = reviewed_payload()
    # Prove the reviewed endpoint package preserved the other 31 V6 runtime files.
    for name, raw in original.items():
        require(name == RECEIVER or reviewed['sources/selected/' + name] == raw,
                'Unexpected reviewed runtime change: ' + name)
    selected[RECEIVER] = reviewed['sources/selected/' + RECEIVER]
    require(selected[RECEIVER] != original[RECEIVER], 'Fresh reviewed fixed4992 receiver required')
    substitutions = [(OLD_SOURCE, SOURCE), (OLD_PRODUCT, PRODUCT),
                     ('mixer.apple-focus-reference-root-selection.6', 'mixer.apple-focus-reference-root-selection.7'),
                     ('MixerFocusReferenceV6-', 'MixerFocusReferenceV7-'),
                     ('mixer.apple-focus-reference-runtime-import.6', 'mixer.apple-focus-reference-runtime-import.7')]
    for before, after in substitutions:
        selected['importer.py'] = replace_once(selected['importer.py'], before.encode(), after.encode())
    restored = selected['importer.py']
    for before, after in reversed(substitutions):
        restored = replace_once(restored, after.encode(), before.encode())
    require(restored == original['importer.py'], 'Importer changes beyond exact identity/namespace substitutions')
    adapter = (PRIOR / 'adapter.py').read_bytes()
    adapter = replace_once(adapter, b"'native-run-v6-'", b"'native-run-v7-'")
    adapter = replace_once(adapter, b"'mixer.apple-focus-reference-runtime.6'", b"'mixer.apple-focus-reference-runtime.7'")
    require(original['join_support.py'].endswith((PRIOR / 'adapter.py').read_bytes()), 'Approved V6 adapter suffix differs')
    selected['join_support.py'] = original['join_support.py'][:-len((PRIOR / 'adapter.py').read_bytes())] + adapter
    require(sorted(name for name in selected if selected[name] != original[name]) == sorted([RECEIVER, 'importer.py', 'join_support.py']),
            'Only reviewed receiver, importer identities and adapter namespace may change')
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
                              selected[name].decode().splitlines(True), fromfile='accepted-v6/' + name,
                              tofile='fixed4992-v7/' + name))
    for name, raw in [('adapter.py', adapter), ('importer.py', selected['importer.py']),
                      ('selection-template.json', stable(selection_template(selected))),
                      ('source-delta.patch', patch.encode()), ('runtime-source-manifest.json', stable(archive))]:
        with (BASE / name).open('xb') as stream:
            stream.write(raw)
    changed = sorted(name for name in selected if selected[name] != original.get(name))
    packet = {'schema': 'mixer.apple-settings-fixed-chunk-runtime-packet.1',
              'scope': 'Host preparation only; separate source review and fresh root selection required',
              'references': bound, 'sourceRevisionContext': 'be472ce6424a691de5673e3438d2768264827d23',
              'sourceRevisionMeaning': 'Inherited fresh-build receipt label; no Git query; exact hashes authoritative',
              'sourceTreeSHA256': SOURCE, 'sourceTreeMeaning': 'SHA256 of stable 40-member fresh source manifest sources',
              'nativeProductArchiveSHA256': PRODUCT, 'runtimeSourceTreeSHA256': archive['treeSHA256'],
              'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.7',
              'simulatorNamePrefix': 'MixerFocusReferenceV7-', 'changedSelectedFiles': changed,
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
               'output': 'PASS: fixed4992 V7 Settings runtime packet prepared; no native execution'}
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

