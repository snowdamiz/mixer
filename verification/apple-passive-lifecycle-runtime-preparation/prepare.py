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
PRIOR = ROOT / 'verification/apple-focus-system-runtime-preparation'
BUILD = ROOT / 'verification/apple-passive-lifecycle-sendable-correction'
BUILD_ATTEMPT = BUILD / 'build-attempt-1'
BUILD_HANDOFF = '207821bc258c351b1767932ad7b2e85dd7f621f3ad7e56054bcb3cfdcf87ed88'
PRIOR_PACKET = '70dcc748cf67ce6573215b3815736aca4689707cc081d34c8069f9b5f13c3a82'
PRODUCT = '495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904'
SOURCE = 'f402eba7b6fa8abf2671e3a95441351dace37f291a9d55024232c9112b2720fb'
OLD_SOURCE = 'ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d'
OLD_PRODUCT = '681059d32edbd63128c8f4552af2ed161d6dce05847397ffa6ce57b5402364d9'
OUTPUT_PREFIX = 'native-run-v9-'
SOURCES = ['prepare.py', 'run_controls.py', 'record_command.py', 'seal.py', 'local_first_failure.py', 'bootstrap.py']
RECEIVER = 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
COMPILE_ARCHIVE = '42fce2c1e14ef5672677430ab730008d3349bf80cb064a794d38c500ef1dc6eb'
SELECTED_ARCHIVE = 'bf31888a14490e83e2424f458eac0cf8f56258d581ff2fc4034840b0d1783663'
PRODUCT_TREE = '1132e5c80d5fc426b7d0562a5a674ee2302be701f835852da05a4d53c4f1f5fc'
ARTIFACTS = ['adapter.py', 'importer.py', 'selection-template.json', 'source-delta.patch',
             'runtime-source-manifest.json', 'runtime-sources.tar.gz', 'binding-delta.json']
INPUT_SEALS = [
    ('verification/apple-focus-system-runtime-preparation/handoff.json',
     '20dd17885f3c9b923465299da1cff9044ae178cb448b026c531552be87f332c5', 59),
    ('verification/apple-focus-system-runtime-review/handoff.json',
     '874ce792b4353f5b8ae21a5e08ea655c7909ba5111a104a28708caed600c8d89', 26),
    ('verification/apple-focus-system-native-result/handoff.json',
     '0d4ff885c95e54386cd06e53794077defa7acac5cf63525583a8053f053c90de', 10),
    ('verification/apple-passive-lifecycle-sendable-correction/handoff.json', BUILD_HANDOFF, 81),
    ('verification/apple-passive-sendable-review/handoff.json',
     '859892145e06424104de36370c5811fb47dedacf34a6a0546e8f796b9fb3e2e1', 29),
]
DIRECT_PINS = {
    'verification/current-diagnostic-corrections-root-review/apple-acceptance.json':
        'f86d268cb38cbbcce4578bfec10175be95900c9bb2281b95564b1e4a52d3df66',
    'verification/apple-focus-system-native-build/attempt-1/source-manifest.json':
        '9d9049d33c9ecacc49c1d44f445885fc9018f64dc5fed94a61efff7ac6e744f7',
    'verification/apple-focus-system-native-build/attempt-1/sources.tar.gz':
        '3cfd2e83369b566a48cc50f263ff879bc7da2c7b49cb0a836980da7c5b39cdc1',
}


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
    result = {'schema': 1, 'scope': 'Passive-lifecycle V9 runtime selected source closure',
              'files': rows, 'treeSHA256': sha(stable(rows)), 'archive': row(path),
              'directories': sorted(directories), 'directoryMode': 0o755}
    require(archive_payload(path, rows, result['archive']['sha256'], 'selected/')
            == {name: (source / name).read_bytes() for name in rows}, 'Archive round-trip differs')
    return result


def reference_paths():
    """Immediate pinned member read closure only; no recursive historical copies."""
    paths = {ROOT / name for name in DIRECT_PINS}
    for name, digest, count in INPUT_SEALS:
        path = ROOT / name
        require(row(path)['sha256'] == digest, 'Immediate seal differs')
        value = json.loads(path.read_bytes())
        require(len(value['members']) == count, 'Immediate seal member count differs')
        paths.add(path)
        for member in value['members']:
            safe_name(member)
            paths.add(ROOT / member)
    return paths


def references():
    """Verify each immediate sealed original once and bind only its seal identity."""
    bindings, checked, seals = {}, {}, {}
    def check(path):
        name = str(path.relative_to(ROOT))
        safe_name(name)
        require(not any(word in name.lower() for word in ('catalog-inspector', 'authority-driver', 'worker-transport')),
                'Excluded handoff lane refused')
        if name not in checked:
            checked[name] = row(path)
        return checked[name]
    for name, digest, count in INPUT_SEALS:
        path = ROOT / name
        actual = check(path)
        require(actual['sha256'] == digest, 'Accepted immediate seal differs: ' + name)
        bindings[name] = actual
        value = json.loads(path.read_bytes())
        require(len(value['members']) == count, 'Exact immediate member count required')
        require(sha(stable(value['members'])) == value['memberTreeSHA256'], 'Immediate member tree differs')
        for member, expected in value['members'].items():
            actual_member = {**check(ROOT / member), 'linkCount': 1}
            require(set(expected) <= {'kind', 'mode', 'bytes', 'sha256', 'linkCount'} and
                    all(actual_member[key] == item for key, item in expected.items()), 'Sealed member changed: ' + member)
        seals[name] = value
    for name, digest in DIRECT_PINS.items():
        actual = check(ROOT / name)
        require(actual['sha256'] == digest, 'Accepted direct input differs: ' + name)
        bindings[name] = actual
    root_accept = json.loads((ROOT / 'verification/current-diagnostic-corrections-root-review/apple-acceptance.json').read_bytes())
    require(root_accept['sourceAndGenericBuildAccepted'] is True
            and root_accept['hostRuntimePreparationSelected'] is True and root_accept['nativeRunSelected'] is False
            and root_accept['bindings']['producer']['sha256'] == BUILD_HANDOFF
            and root_accept['bindings']['review']['sha256'] == INPUT_SEALS[-1][1]
            and root_accept['candidateArchiveSHA256'] == SELECTED_ARCHIVE
            and root_accept['productArchiveSHA256'] == PRODUCT, 'Root source/build acceptance differs')
    prior = json.loads((PRIOR / 'packet.json').read_bytes())
    require(row(PRIOR / 'packet.json')['sha256'] == PRIOR_PACKET and prior['selectedFiles'] == 32
            and prior['runtimeSourceTreeSHA256'] == '4ed156befa6fd0d74c57a72b7be5a2181f763dab4c30851578a50d8a49a13a9b'
            and prior['sourceTreeSHA256'] == OLD_SOURCE and prior['nativeExecuted'] is False,
            'Exact accepted V8 preparation required')
    review = seals['verification/apple-focus-system-runtime-review/handoff.json']
    require(review['status'] == 'source-and-host-runtime-preparation-accepted'
            and review['blockingFindings'] == [] and review['packetSHA256'] == PRIOR_PACKET
            and review['nativeSelected'] is False, 'Accepted V8 independent runtime review differs')
    history_seal = seals['verification/apple-focus-system-native-result/handoff.json']
    history = json.loads((ROOT / 'verification/apple-focus-system-native-result/result.json').read_bytes())
    require(history_seal['auditPassed'] is True and history_seal['nativePassed'] is False
            and history['auditPassed'] is True and history['packetSHA256'] == PRIOR_PACKET
            and history['runID'] == 'd9a1ae2b-ef02-4db2-b2ff-4979213c8236'
            and history['officialMethods'] == {'test000PublicSettingsFullKeyboardAccess': 'Passed',
                                               'test010ReferenceFirstTab': 'Failed'}
            and history['failedOriginalPredicates'] == ['actualNativeFocusTraversal']
            and history['otherOriginalPredicatesPassed'] == 19 and history['xcodebuildExitCode'] == 65
            and history['sourceAndProductScratchAbsent'] is True
            and history['ownedDeviceAbsentInRecordedFinalInventory'] is True
            and history['nativePassed'] is False and history['gaAccepted'] is False,
            'Audited V8 original verdict must remain exact')
    build = seals['verification/apple-passive-lifecycle-sendable-correction/handoff.json']
    corrected_review = seals['verification/apple-passive-sendable-review/handoff.json']['audit']
    require(build['audit']['passed'] is True and build['audit']['sourceMembers'] == 42
            and build['audit']['candidateArchiveSHA256'] == SELECTED_ARCHIVE
            and build['audit']['productArchiveSHA256'] == PRODUCT and build['nativeExecuted'] is False
            and build['runtimeSelected'] is False, 'Accepted corrected build scope differs')
    require(corrected_review['passed'] is True and corrected_review['blockingFindings'] == []
            and corrected_review['status'] == 'accepted-minimal-copied-observer-correction-and-generic-build-evidence'
            and corrected_review['producerHandoffSHA256'] == BUILD_HANDOFF
            and corrected_review['candidateArchiveSHA256'] == SELECTED_ARCHIVE
            and corrected_review['productArchiveSHA256'] == PRODUCT
            and corrected_review['producerByteIdenticalMembers'] == 41
            and corrected_review['producerChangedMembers'] == 1
            and corrected_review['baselineByteIdenticalMembers'] == 39
            and corrected_review['futureRuntimeIngestionAccepted'] is False
            and corrected_review['runtimeSelected'] is False and corrected_review['nativeExecuted'] is False,
            'Final accepted correction review differs')
    source = json.loads((BUILD_ATTEMPT / 'source-manifest.json').read_bytes())
    require(len(source['sources']) == len(source['selectedArchiveMembers']) == 42
            and sha(stable(source['sources'])) == source['sourceTreeSHA256'] == SOURCE
            and source['archive']['sha256'] == COMPILE_ARCHIVE
            and source['selectedArchive']['sha256'] == SELECTED_ARCHIVE
            and source['overallSwiftFiles'] == 37 and len(source['prototypeSwiftFiles']) == 12,
            'Exact forty-two-source compile closure differs')
    compiled = archive_payload(BUILD_ATTEMPT / 'sources.tar.gz', source['sources'], COMPILE_ARCHIVE, explicit_directories=False)
    selected = archive_payload(BUILD / 'review-source-package.tar.gz', source['selectedArchiveMembers'], SELECTED_ARCHIVE,
                               explicit_directories=False)
    require(compiled == {name.removeprefix('accepted/'): data for name, data in selected.items()},
            'Recipe-relative archive differs from exact corrected source bytes')
    require(all(item['mode'] == 0o444 for item in source['sources'].values()), 'Selected source mode must remain 0444')
    old_path = ROOT / 'verification/apple-focus-system-native-build/attempt-1'
    old_source = json.loads((old_path / 'source-manifest.json').read_bytes())
    old = archive_payload(old_path / 'sources.tar.gz', old_source['sources'], DIRECT_PINS[str((old_path / 'sources.tar.gz').relative_to(ROOT))], explicit_directories=False)
    require(len(old) == 40 and sha(stable(old_source['sources'])) == OLD_SOURCE, 'Exact forty-source baseline required')
    require(sorted(set(compiled) - set(old)) == ['source/Prototype/PassiveLifecycleData.swift', 'source/Prototype/PassiveLifecycleObserver.swift']
            and not (set(old) - set(compiled))
            and [name for name in sorted(old) if old[name] != compiled[name]] == ['source/Prototype/main.swift']
            and sum(old[name] == compiled[name] for name in old) == 39, 'Only accepted passive source additions/main integration allowed')
    product = json.loads((BUILD_ATTEMPT / 'product-manifest.json').read_bytes())
    require(len(product['products']) == 55 and product['archive']['sha256'] == PRODUCT
            and sha(stable(product['products'])) == product['productTreeSHA256'] == PRODUCT_TREE
            and product['sourceTreeSHA256'] == SOURCE and product['appProductsFresh'] is True
            and product['runnerProductsFresh'] is True and product['appProductFiles'] == 13
            and product['runnerProductFiles'] == 42 and product['oldAppProductFilesCopied'] == 0,
            'Exact fresh app/runner products required')
    archive_payload(BUILD_ATTEMPT / 'products.tar.gz', product['products'], PRODUCT, explicit_directories=False)
    receipt = json.loads((BUILD_ATTEMPT / 'receipt.json').read_bytes())
    require(receipt['passed'] is True and receipt['sourceTreeSHA256'] == SOURCE
            and receipt['productTreeSHA256'] == PRODUCT_TREE and receipt['sourceFiles'] == 42
            and receipt['warningLineOccurrences'] == 21 and receipt['ownedScratchRemoved'] is True
            and receipt['nativeExecuted'] is False and receipt['runtimeSelected'] is False,
            'Corrected fresh build receipt differs')
    return bindings


def literal_delta():
    return {
        'importer.py': [(OLD_SOURCE, SOURCE, 1), (OLD_PRODUCT, PRODUCT, 1),
                        ('mixer.apple-focus-reference-root-selection.8', 'mixer.apple-focus-reference-root-selection.9', 1),
                        ('MixerFocusReferenceV8-', 'MixerFocusReferenceV9-', 1),
                        ('mixer.apple-focus-reference-runtime-import.8', 'mixer.apple-focus-reference-runtime-import.9', 1)],
        'join_support.py': [('native-run-v8-', 'native-run-v9-', 1),
                            ('mixer.apple-focus-reference-runtime.8', 'mixer.apple-focus-reference-runtime.9', 1)],
        'local_first_failure.py': [('native-run-v8-', 'native-run-v9-', 2)],
    }


def binding_delta():
    return {'schema': 1, 'baselinePacketSHA256': PRIOR_PACKET,
            'changedRuntimeFiles': {name: [{'before': before, 'after': after, 'occurrences': count}
                                         for before, after, count in changes]
                                   for name, changes in literal_delta().items()},
            'unchangedRuntimeFiles': sorted(set(prior_payload()) - set(literal_delta())),
            'compileSourceFiles': {'before': 40, 'after': 42, 'unchangedBytes': 39,
                                   'added': ['source/Prototype/PassiveLifecycleData.swift', 'source/Prototype/PassiveLifecycleObserver.swift'],
                                   'changed': ['source/Prototype/main.swift'], 'mode': 0o444},
            'correctedObserverComparedToPassiveProducer': {'unchangedMembers': 41, 'changedMembers': 1,
                                    'changedPath': 'accepted/source/Prototype/PassiveLifecycleObserver.swift',
                                    'scope': 'Notification string identity mapping; exact correction accepted by independent review'},
            'futureSupplementalJoinSelected': False, 'futureRuntimeOriginalsSelected': False,
            'frozenV7JoinAnchorAuthority': 'replay-only',
            'originalsPolicy': 'Retain raw before/after/witness and original oracle independently through unchanged capture paths. Root selects immutable originals after collection before any separately reviewed supplemental offline join.'}


def prior_payload():
    source = json.loads((PRIOR / 'runtime-source-manifest.json').read_bytes())
    return archive_payload(PRIOR / 'runtime-sources.tar.gz', source['files'], source['archive']['sha256'], 'selected/')


def replace_once(raw, before, after):
    require(raw.count(before) == 1, 'Exactly one bound source replacement required')
    return raw.replace(before, after, 1)


def derived_payload():
    original = prior_payload()
    require(len(original) == 32, 'Exact accepted V8 composition required')
    selected = dict(original)
    for name, changes in literal_delta().items():
        for before, after, count in changes:
            require(selected[name].count(before.encode()) == count, 'Exact changed-literal inventory required')
            selected[name] = selected[name].replace(before.encode(), after.encode())
        restored = selected[name]
        for before, after, count in reversed(changes):
            require(restored.count(after.encode()) == count, 'Exact reverse-literal inventory required')
            restored = restored.replace(after.encode(), before.encode())
        require(restored == original[name], 'No semantic runtime change allowed: ' + name)
    adapter = (PRIOR / 'adapter.py').read_bytes()
    require(original['join_support.py'].endswith(adapter), 'Accepted V9 adapter suffix differs')
    for before, after, count in literal_delta()['join_support.py']:
        require(adapter.count(before.encode()) == count, 'Exact adapter literal required')
        adapter = adapter.replace(before.encode(), after.encode())
    require(selected['join_support.py'].endswith(adapter), 'V9 adapter suffix differs')
    require((BASE / 'local_first_failure.py').read_bytes() == selected['local_first_failure.py'],
            'Local safe metadata module differs from selected bytes')
    require(sorted(name for name in selected if selected[name] != original[name]) == sorted(literal_delta()),
            'Only three identity/namespace derivatives may change')
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
                              selected[name].decode().splitlines(True), fromfile='accepted-v8/' + name,
                              tofile='passive-lifecycle-v9/' + name))
    for name, raw in [('adapter.py', adapter), ('importer.py', selected['importer.py']),
                      ('selection-template.json', stable(selection_template(selected))),
                      ('source-delta.patch', patch.encode()), ('runtime-source-manifest.json', stable(archive)),
                      ('binding-delta.json', stable(binding_delta()))]:
        with (BASE / name).open('xb') as stream:
            stream.write(raw)
    changed = sorted(name for name in selected if selected[name] != original.get(name))
    packet = {'schema': 'mixer.apple-passive-lifecycle-runtime-packet.1',
              'scope': 'Host preparation only; separate source review and fresh root selection required',
              'references': bound, 'sourceRevisionContext': '7b6048642b42e4900cccff4e14aa0fe8949ab35e',
              'sourceRevisionMeaning': 'Root-reported correction context; inherited build revision is historical; no Git query; exact archives authoritative',
              'sourceTreeSHA256': SOURCE, 'sourceTreeMeaning': 'SHA256 of stable 42-member corrected compile source manifest sources',
              'nativeProductArchiveSHA256': PRODUCT, 'runtimeSourceTreeSHA256': archive['treeSHA256'],
              'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.9',
              'simulatorNamePrefix': 'MixerFocusReferenceV9-', 'changedSelectedFiles': changed,
              'unchangedSelectedFiles': len(original) - len([n for n in original if selected[n] != original[n]]),
              'selectedFiles': len(selected), 'files': {name: row(BASE / name) for name in SOURCES + ARTIFACTS},
              'nativeExecuted': False, 'runtimeSelected': False, 'compileRerun': False,
              'gaAccepted': False, 'physicalPhones': 'disconnected-deferred',
              'futureRuntimeOriginalsSelected': False, 'futureSupplementalJoinSelected': False}
    with (BASE / 'packet.json').open('xb') as stream:
        stream.write(stable(packet))
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'packetSHA256': sha(stable(packet)), 'referencesVerified': len(bound), 'immediateSealMemberChecks': sum(item[2] for item in INPUT_SEALS),
               'immediateSeals': len(INPUT_SEALS), 'recursiveHistoricalReferencesCopied': False,
               'sourceTreeSHA256': SOURCE, 'runtimeSourceTreeSHA256': archive['treeSHA256'],
               'selectedFiles': len(selected), 'changedSelectedFiles': changed,
               'ownedPreparationScratchAbsent': not scratch.exists(), 'nativeInstancesCreatedOrQueried': 0,
               'nativeExecuted': False, 'compilerExecuted': False, 'listenerStarted': False,
               'output': 'PASS: passive-lifecycle V9 runtime packet prepared; no native execution'}
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
    require(json.loads((BASE / 'binding-delta.json').read_bytes()) == binding_delta(), 'Exact literal/mode delta differs')
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

