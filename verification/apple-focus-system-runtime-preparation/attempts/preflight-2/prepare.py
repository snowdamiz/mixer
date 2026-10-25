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
PRIOR = ROOT / 'verification/apple-settings-fixed-chunk-runtime-preparation'
BUILD = ROOT / 'verification/apple-focus-system-native-build'
BUILD_ATTEMPT = BUILD / 'attempt-1'
BUILD_HANDOFF = 'a51cc040f4093661789317f2f508bd61888579dd059cc1cef6c2f73920e5aa57'
PRIOR_PACKET = '2a1804ce1a6ece3b7b2125f4aa677e40c54f31846d94f3fec13e1f74d786eed7'
ACCEPTANCE = 'e535eee17b3908aa21a5c1c90c658fac6e393ea5fb34e81edbedccbb1642bce9'
PRODUCT = '681059d32edbd63128c8f4552af2ed161d6dce05847397ffa6ce57b5402364d9'
SOURCE = 'ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d'
OLD_SOURCE = '0677712483e4f078cbd10120efd5c9f9d4a13fe31b9f455caa1a984772d2bfeb'
OLD_PRODUCT = 'cca8472579ed6ce7c3c00babadb44d37ba34dc1a400ec00fc7802536342d7a2c'
OUTPUT_PREFIX = 'native-run-v8-'
SOURCES = ['prepare.py', 'run_controls.py', 'record_command.py', 'seal.py', 'local_first_failure.py', 'bootstrap.py']
RECEIVER = 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
COMPILE_ARCHIVE = '3cfd2e83369b566a48cc50f263ff879bc7da2c7b49cb0a836980da7c5b39cdc1'
SELECTED_ARCHIVE = 'd1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda'
PRODUCT_TREE = '6966d9d0e83fb4552a9b5b6611cea897a9402bb048dc1bdb45562cbd5bedf3f1'
ARTIFACTS = ['adapter.py', 'importer.py', 'selection-template.json', 'source-delta.patch',
             'runtime-source-manifest.json', 'runtime-sources.tar.gz', 'binding-delta.json']
HISTORY = 'verification/apple-settings-fixed-chunk-runtime-preparation/native-run-v7-ddd94f80-4cb3-4a29-8fdd-c6868a343df4/'
HISTORY_PINS = {
    HISTORY + 'root-selection.json': 'abc1d883af3ad8b62e537ee10c7f1d7a925bfc0e6f0422ccfa5819da6d907b27',
    HISTORY + 'runtime/runtime-verdict.json': '7a86b1c28425719e1eee662f9d5ed85dbe84508d221f7d5f9d0af5780f35c211',
    HISTORY + 'runtime/lifecycle.json': '16b2e80bbc578223a72a8660f3b5469b73d96f0a5158a5346f51401105d855ee',
    HISTORY + 'scratch-cleanup.json': 'cafc3de1dacdc63bc20bf28375047203cdf3d48a196a50272f6355aeb9cf6280',
    'docs/apple-settings-fixed-chunk-native-result.md': 'd23d67e1e4e6073fd92d116a88dace6101ed6087bbe7e00c865db82648b76131',
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
    result = {'schema': 1, 'scope': 'Focus-system V8 runtime selected source closure',
              'files': rows, 'treeSHA256': sha(stable(rows)), 'archive': row(path),
              'directories': sorted(directories), 'directoryMode': 0o755}
    require(archive_payload(path, rows, result['archive']['sha256'], 'selected/')
            == {name: (source / name).read_bytes() for name in rows}, 'Archive round-trip differs')
    return result


def references():
    """File-only verification of exact accepted V7 and fresh build handoffs."""
    bindings = {}
    def bind(path, expected=None):
        name = str(path.relative_to(ROOT))
        safe_name(name)
        require(not any(word in name.lower() for word in ('catalog-inspector', 'authority-driver', 'worker-transport')),
                'Excluded handoff lane refused')
        actual = row(path)
        require(expected is None or actual['sha256'] == expected, 'Accepted identity differs: ' + name)
        bindings[name] = actual
        return actual
    def sealed(path, digest, count):
        bind(path, digest)
        value = json.loads(path.read_bytes())
        require(len(value['members']) == count, 'Exact accepted member count required')
        for name, expected in value['members'].items():
            actual = bind(ROOT / name)
            require(set(expected) <= {'kind', 'mode', 'bytes', 'sha256'}
                    and all(actual[key] == item for key, item in expected.items()), 'Sealed member changed: ' + name)
        if 'memberTreeSHA256' in value:
            require(sha(stable(value['members'])) == value['memberTreeSHA256'], 'Accepted member tree differs')
        return value
    prior_seal = sealed(PRIOR / 'handoff.json', 'bcb2b7135eaa594b6a6ac0a84866cf0877ec1a3cb0264b1a51fcc33afd0860b2', 66)
    require(prior_seal['packetSHA256'] == PRIOR_PACKET and prior_seal['nativeExecuted'] is False,
            'Accepted V7 preparation scope differs')
    bind(PRIOR / 'packet.json', PRIOR_PACKET)
    prior = json.loads((PRIOR / 'packet.json').read_bytes())
    require(prior['selectedFiles'] == 32 and prior['runtimeSourceTreeSHA256'] ==
            '914a446192ea6207abcec314f919c45c9bacf53dd5220d1b2724cbede5175426', 'Exact accepted V7 closure required')
    for name, expected in prior['references'].items():
        require(bind(ROOT / name) == expected, 'Prior accepted reference changed: ' + name)
    review = ROOT / 'verification/apple-settings-fixed-chunk-runtime-review'
    sealed(review / 'handoff.json', 'e1c8b2345056742eacbc2b2faa415e760f75ba351b639adb410124322e3f4035', 26)
    decision = json.loads((review / 'review.json').read_bytes())
    require(decision['status'] == 'source-and-host-packaging-accepted' and decision['blockingFindings'] == []
            and decision['packetSHA256'] == PRIOR_PACKET and decision['nativeSelected'] is False,
            'Accepted V7 independent review differs')
    build = sealed(BUILD / 'handoff.json', BUILD_HANDOFF, 53)
    require(build['sourceRevisionReportedByRoot'] == '9102ad3ee1247187c01ea5f55c42caaac882961b'
            and build['selectedSourceArchiveSHA256'] == SELECTED_ARCHIVE and build['nativeExecuted'] is False
            and build['runtimeSelected'] is False and build['futureRuntimeIngestionAccepted'] is False,
            'Accepted fresh build scope differs')
    upstream = json.loads((BUILD_ATTEMPT / 'input-bindings-before.json').read_bytes())
    require(upstream == json.loads((BUILD_ATTEMPT / 'input-bindings-after.json').read_bytes()),
            'Build before/after upstream bindings differ')
    require(sum(upstream['handoffMembersVerified'].values()) == 425, '425 upstream build checks required')
    for name, digest in upstream['pins'].items():
        bind(ROOT / name, digest)
    for name, count in upstream['handoffMembersVerified'].items():
        sealed(ROOT / name, upstream['pins'][name], count)
    accept = ROOT / 'verification/apple-focus-system-observation-root-review/build-acceptance.json'
    bind(accept, ACCEPTANCE)
    accepted = json.loads(accept.read_bytes())
    require(accepted['genericBuildAccepted'] is True and accepted['runtimeSelected'] is False
            and accepted['futureRuntimeIngestionAccepted'] is False and accepted['handoffSHA256'] == BUILD_HANDOFF
            and accepted['freshAppFiles'] == 13 and accepted['freshRunnerFiles'] == 42
            and accepted['oldAppProductsReused'] == 0, 'Root fresh build acceptance differs')
    source = json.loads((BUILD_ATTEMPT / 'source-manifest.json').read_bytes())
    require(len(source['sources']) == 40 and sha(stable(source['sources'])) == SOURCE
            and source['archive']['sha256'] == COMPILE_ARCHIVE
            and source['selectedArchive']['sha256'] == SELECTED_ARCHIVE, 'Fresh compile closure differs')
    compile_payload = archive_payload(BUILD_ATTEMPT / 'sources.tar.gz', source['sources'], COMPILE_ARCHIVE,
                                      explicit_directories=False)
    selected_path = ROOT / 'verification/apple-focus-system-observation/review-source-package.tar.gz'
    selected = archive_payload(selected_path, source['selectedArchiveMembers'], SELECTED_ARCHIVE,
                               explicit_directories=False)
    require(compile_payload == {name.removeprefix('accepted/'): raw for name, raw in selected.items()},
            'Recipe-relative archive differs from exact selected source bytes')
    require(all(item['mode'] == 0o444 for item in source['sources'].values()), 'Selected source mode must remain 0444')
    old_source = json.loads((ROOT / 'verification/apple-settings-fixed-chunk-native-build/attempt-1/source-manifest.json').read_bytes())
    old = archive_payload(ROOT / 'verification/apple-settings-fixed-chunk-native-build/attempt-1/accepted-sources.tar.gz',
                          old_source['sources'], old_source['archive']['sha256'], explicit_directories=False)
    old = {name.removeprefix('accepted/'): raw for name, raw in old.items()}
    require(set(old) == set(compile_payload) and all(item['mode'] == 0o644 for item in old_source['sources'].values()),
            'Historical source closure/mode differs')
    changed = [name for name in sorted(old) if old[name] != compile_payload[name]]
    require(changed == ['source/Prototype/DiagnosticTrace.swift', 'source/Prototype/main.swift'],
            'Only the two accepted supplemental app files may change bytes')
    product = json.loads((BUILD_ATTEMPT / 'product-manifest.json').read_bytes())
    require(len(product['products']) == 55 and product['archive']['sha256'] == PRODUCT
            and sha(stable(product['products'])) == product['productTreeSHA256'] == PRODUCT_TREE
            and product['sourceTreeSHA256'] == SOURCE and product['appProductsFresh'] is True
            and product['runnerProductsFresh'] is True and product['appProductFiles'] == 13
            and product['runnerProductFiles'] == 42 and product['oldAppProductFilesCopied'] == 0,
            'Exact fresh app/runner products required')
    archive_payload(BUILD_ATTEMPT / 'products.tar.gz', product['products'], PRODUCT, explicit_directories=False)
    for name, digest in HISTORY_PINS.items(): bind(ROOT / name, digest)
    history_root = json.loads((ROOT / (HISTORY + 'root-selection.json')).read_bytes())
    history = json.loads((ROOT / (HISTORY + 'runtime/runtime-verdict.json')).read_bytes())
    lifecycle = json.loads((ROOT / (HISTORY + 'runtime/lifecycle.json')).read_bytes())
    require(history_root['runID'] == 'ddd94f80-4cb3-4a29-8fdd-c6868a343df4'
            and history_root['schema'] == 'mixer.apple-focus-reference-root-selection.7'
            and history['settingsPreconditionPassed'] is True and history['singleTabDiagnosticEvidencePassed'] is False
            and history['diagnosticOutcome'] == 'one-strict-original-verdict-failed' and history['runPassed'] is False
            and lifecycle['cleanedUp'] is True and len(lifecycle['cleanupResults']) == 5
            and all(item['passed'] is True for item in lifecycle['cleanupResults']), 'Historical V7 verdict must remain exact')
    return bindings


def literal_delta():
    return {
        'importer.py': [(OLD_SOURCE, SOURCE, 1), (OLD_PRODUCT, PRODUCT, 1),
                        ('mixer.apple-focus-reference-root-selection.7', 'mixer.apple-focus-reference-root-selection.8', 1),
                        ('MixerFocusReferenceV7-', 'MixerFocusReferenceV8-', 1),
                        ('mixer.apple-focus-reference-runtime-import.7', 'mixer.apple-focus-reference-runtime-import.8', 1)],
        'join_support.py': [('native-run-v7-', 'native-run-v8-', 1),
                            ('mixer.apple-focus-reference-runtime.7', 'mixer.apple-focus-reference-runtime.8', 1)],
        'local_first_failure.py': [('native-run-v7-', 'native-run-v8-', 2)],
    }


def binding_delta():
    return {'schema': 1, 'baselinePacketSHA256': PRIOR_PACKET,
            'changedRuntimeFiles': {name: [{'before': before, 'after': after, 'occurrences': count}
                                         for before, after, count in changes]
                                   for name, changes in literal_delta().items()},
            'unchangedRuntimeFiles': sorted(set(prior_payload()) - set(literal_delta())),
            'compileSourceByteChanges': ['source/Prototype/DiagnosticTrace.swift', 'source/Prototype/main.swift'],
            'compileSourceModeChanges': {'members': 40, 'before': 0o644, 'after': 0o444,
                                         'meaning': 'Selected archive mode metadata; not forty source byte changes'},
            'futureSupplementalJoinSelected': False, 'frozenV7JoinAnchorAuthority': 'replay-only',
            'originalsPolicy': 'Retain raw before/after/witness and original oracle independently through unchanged capture paths. Root selects immutable originals after collection before any separately reviewed supplemental offline join.'}


def prior_payload():
    source = json.loads((PRIOR / 'runtime-source-manifest.json').read_bytes())
    return archive_payload(PRIOR / 'runtime-sources.tar.gz', source['files'], source['archive']['sha256'], 'selected/')


def replace_once(raw, before, after):
    require(raw.count(before) == 1, 'Exactly one bound source replacement required')
    return raw.replace(before, after, 1)


def derived_payload():
    original = prior_payload()
    require(len(original) == 32, 'Exact accepted V7 composition required')
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
    require(original['join_support.py'].endswith(adapter), 'Accepted V7 adapter suffix differs')
    for before, after, count in literal_delta()['join_support.py']:
        require(adapter.count(before.encode()) == count, 'Exact adapter literal required')
        adapter = adapter.replace(before.encode(), after.encode())
    require(selected['join_support.py'].endswith(adapter), 'V8 adapter suffix differs')
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
                              selected[name].decode().splitlines(True), fromfile='accepted-v7/' + name,
                              tofile='focus-system-v8/' + name))
    for name, raw in [('adapter.py', adapter), ('importer.py', selected['importer.py']),
                      ('selection-template.json', stable(selection_template(selected))),
                      ('source-delta.patch', patch.encode()), ('runtime-source-manifest.json', stable(archive)),
                      ('binding-delta.json', stable(binding_delta()))]:
        with (BASE / name).open('xb') as stream:
            stream.write(raw)
    changed = sorted(name for name in selected if selected[name] != original.get(name))
    packet = {'schema': 'mixer.apple-focus-system-runtime-packet.1',
              'scope': 'Host preparation only; separate source review and fresh root selection required',
              'references': bound, 'sourceRevisionContext': '9102ad3ee1247187c01ea5f55c42caaac882961b',
              'sourceRevisionMeaning': 'Inherited fresh-build receipt label; no Git query; exact hashes authoritative',
              'sourceTreeSHA256': SOURCE, 'sourceTreeMeaning': 'SHA256 of stable 40-member fresh source manifest sources',
              'nativeProductArchiveSHA256': PRODUCT, 'runtimeSourceTreeSHA256': archive['treeSHA256'],
              'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.8',
              'simulatorNamePrefix': 'MixerFocusReferenceV8-', 'changedSelectedFiles': changed,
              'unchangedSelectedFiles': len(original) - len([n for n in original if selected[n] != original[n]]),
              'selectedFiles': len(selected), 'files': {name: row(BASE / name) for name in SOURCES + ARTIFACTS},
              'nativeExecuted': False, 'runtimeSelected': False, 'compileRerun': False,
              'gaAccepted': False, 'physicalPhones': 'disconnected-deferred',
              'futureRuntimeOriginalsSelected': False, 'futureSupplementalJoinSelected': False}
    with (BASE / 'packet.json').open('xb') as stream:
        stream.write(stable(packet))
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'packetSHA256': sha(stable(packet)), 'referencesVerified': len(bound),
               'sourceTreeSHA256': SOURCE, 'runtimeSourceTreeSHA256': archive['treeSHA256'],
               'selectedFiles': len(selected), 'changedSelectedFiles': changed,
               'ownedPreparationScratchAbsent': not scratch.exists(), 'nativeInstancesCreatedOrQueried': 0,
               'nativeExecuted': False, 'compilerExecuted': False, 'listenerStarted': False,
               'output': 'PASS: focus-system V8 runtime packet prepared; no native execution'}
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

