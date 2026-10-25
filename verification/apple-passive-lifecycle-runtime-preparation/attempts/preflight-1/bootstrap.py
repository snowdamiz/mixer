#!/usr/bin/env python3
"""Derive V9 host utilities from sealed V8 bytes without importing runtime code."""
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OLD = ROOT / 'verification/apple-focus-system-runtime-preparation'


def one(raw, before, after):
    if raw.count(before) != 1:
        raise ValueError('Exactly one utility edit required: ' + before[:100])
    return raw.replace(before, after, 1)


raw = (OLD / 'prepare.py').read_text()
start = raw.index('PRIOR = ')
end = raw.index('\ndef require(', start)
raw = raw[:start] + '''PRIOR = ROOT / 'verification/apple-focus-system-runtime-preparation'
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

''' + raw[end:]
start = raw.index('def references():')
end = raw.index('\ndef prior_payload():', start)
raw = raw[:start] + '''def reference_paths():
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
            actual_member = check(ROOT / member)
            require(set(expected) <= {'kind', 'mode', 'bytes', 'sha256'} and
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

''' + raw[end:]
raw = raw.replace('Exact accepted V7 composition required', 'Exact accepted V8 composition required')
raw = raw.replace('Accepted V7 adapter suffix differs', 'Accepted V8 adapter suffix differs').replace('V8 adapter suffix differs', 'V9 adapter suffix differs')
raw = raw.replace('Focus-system V8 runtime selected source closure', 'Passive-lifecycle V9 runtime selected source closure')
raw = raw.replace("fromfile='accepted-v7/'", "fromfile='accepted-v8/'").replace("tofile='focus-system-v8/'", "tofile='passive-lifecycle-v9/'")
raw = raw.replace("'mixer.apple-focus-system-runtime-packet.1'", "'mixer.apple-passive-lifecycle-runtime-packet.1'")
raw = raw.replace('9102ad3ee1247187c01ea5f55c42caaac882961b', '7b6048642b42e4900cccff4e14aa0fe8949ab35e')
raw = raw.replace('Inherited fresh-build receipt label; no Git query; exact hashes authoritative', 'Root-reported correction context; inherited build revision is historical; no Git query; exact archives authoritative')
raw = raw.replace('SHA256 of stable 40-member fresh source manifest sources', 'SHA256 of stable 42-member corrected compile source manifest sources')
raw = one(raw, "'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.8'", "'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.9'")
raw = one(raw, "'simulatorNamePrefix': 'MixerFocusReferenceV8-'", "'simulatorNamePrefix': 'MixerFocusReferenceV9-'")
raw = raw.replace('PASS: focus-system V8 runtime packet prepared; no native execution', 'PASS: passive-lifecycle V9 runtime packet prepared; no native execution')
raw = one(raw, "'referencesVerified': len(bound),", "'referencesVerified': len(bound), 'immediateSealMemberChecks': sum(item[2] for item in INPUT_SEALS),\n               'immediateSeals': len(INPUT_SEALS), 'recursiveHistoricalReferencesCopied': False,")
(BASE / 'prepare.py').write_text(raw)

raw = (OLD / 'local_first_failure.py').read_text()
if raw.count('native-run-v8-') != 2: raise ValueError('Exactly two safe-metadata path literals required')
(BASE / 'local_first_failure.py').write_text(raw.replace('native-run-v8-', 'native-run-v9-'))
raw = (OLD / 'record_command.py').read_text().replace('9102ad3ee1247187c01ea5f55c42caaac882961b', '7b6048642b42e4900cccff4e14aa0fe8949ab35e')
raw = raw.replace('ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d', 'f402eba7b6fa8abf2671e3a95441351dace37f291a9d55024232c9112b2720fb')
(BASE / 'record_command.py').write_text(raw)
raw = (OLD / 'seal.py').read_text().replace('apple-focus-system-runtime-preparation.md', 'apple-passive-lifecycle-runtime-preparation.md')
(BASE / 'seal.py').write_text(raw)

raw = (OLD / 'run_controls.py').read_text()
changes = [('root-selection.8', 'root-selection.9'), ('MixerFocusReferenceV8-', 'MixerFocusReferenceV9-'),
           ('native-run-v8-', 'native-run-v9-'), ('runtime-import.8', 'runtime-import.9'), ('runtime.8', 'runtime.9'),
           ('root-selection.7', 'root-selection.8'), ('MixerFocusReferenceV7-', 'MixerFocusReferenceV8-'),
           ('native-run-v7-', 'native-run-v8-'), ('runtime-import.7', 'runtime-import.8'), ('runtime.7', 'runtime.8')]
for i, (before, after) in enumerate(changes): raw = raw.replace(before, '__V9_LITERAL_' + str(i) + '__')
for i, (before, after) in enumerate(changes): raw = raw.replace('__V9_LITERAL_' + str(i) + '__', after)
raw = one(raw, 'for version in [8, 7, 6, 9]:', 'for version in [9, 8, 7, 10]:')
raw = one(raw, 'accepted = version == 8 and not wrong_argv', 'accepted = version == 9 and not wrong_argv')
raw = one(raw, "REFERENCE_PATHS = {p.ROOT / name for name in json.loads(packet_before)['references']}", 'REFERENCE_PATHS = p.reference_paths()')
(BASE / 'run_controls.py').write_text(raw)
print('Derived host utilities from sealed V8; no runtime module imported or native action performed')
