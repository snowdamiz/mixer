#!/usr/bin/env python3
"""Derive the V8 host utility from accepted V7 bytes; never import runtime code."""
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OLD = ROOT / 'verification/apple-settings-fixed-chunk-runtime-preparation'


def one(raw, before, after):
    if raw.count(before) != 1:
        raise ValueError('Exactly one utility edit required: ' + before[:100])
    return raw.replace(before, after, 1)


raw = (OLD / 'prepare.py').read_text()
start = raw.index('PRIOR = ')
end = raw.index('\ndef require(', start)
raw = raw[:start] + '''PRIOR = ROOT / 'verification/apple-settings-fixed-chunk-runtime-preparation'
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

''' + raw[end:]
start = raw.index('def references():')
end = raw.index('\ndef prior_payload():', start)
raw = raw[:start] + '''def references():
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

''' + raw[end:]
start = raw.index('def derived_payload():')
end = raw.index('\ndef selection_template(', start)
raw = raw[:start] + '''def derived_payload():
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

''' + raw[end:]
raw = raw.replace('Fixed4992 Settings V7 runtime selected source closure', 'Focus-system V8 runtime selected source closure')
raw = raw.replace("fromfile='accepted-v6/'", "fromfile='accepted-v7/'").replace("tofile='fixed4992-v7/'", "tofile='focus-system-v8/'")
raw = one(raw, "('source-delta.patch', patch.encode()), ('runtime-source-manifest.json', stable(archive))]", "('source-delta.patch', patch.encode()), ('runtime-source-manifest.json', stable(archive)),\n                      ('binding-delta.json', stable(binding_delta()))]")
raw = raw.replace("'mixer.apple-settings-fixed-chunk-runtime-packet.1'", "'mixer.apple-focus-system-runtime-packet.1'")
raw = raw.replace("'be472ce6424a691de5673e3438d2768264827d23'", "'9102ad3ee1247187c01ea5f55c42caaac882961b'")
raw = one(raw, "'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.7'", "'outputPrefix': OUTPUT_PREFIX, 'rootSelectionSchema': 'mixer.apple-focus-reference-root-selection.8'")
raw = one(raw, "'simulatorNamePrefix': 'MixerFocusReferenceV7-'", "'simulatorNamePrefix': 'MixerFocusReferenceV8-'")
raw = raw.replace('PASS: fixed4992 V7 Settings runtime packet prepared; no native execution', 'PASS: focus-system V8 runtime packet prepared; no native execution')
raw = one(raw, "expected, adapter = derived_payload()", "expected, adapter = derived_payload()\n    require(json.loads((BASE / 'binding-delta.json').read_bytes()) == binding_delta(), 'Exact literal/mode delta differs')")
raw = one(raw, "'gaAccepted': False, 'physicalPhones': 'disconnected-deferred'}", "'gaAccepted': False, 'physicalPhones': 'disconnected-deferred',\n              'futureRuntimeOriginalsSelected': False, 'futureSupplementalJoinSelected': False}")
(BASE / 'prepare.py').write_text(raw)

raw = (OLD / 'local_first_failure.py').read_text()
if raw.count('native-run-v7-') != 2: raise ValueError('Exactly two safe-metadata path literals required')
(BASE / 'local_first_failure.py').write_text(raw.replace('native-run-v7-', 'native-run-v8-'))

raw = (OLD / 'record_command.py').read_text()
raw = raw.replace('be472ce6424a691de5673e3438d2768264827d23', '9102ad3ee1247187c01ea5f55c42caaac882961b')
raw = raw.replace('0677712483e4f078cbd10120efd5c9f9d4a13fe31b9f455caa1a984772d2bfeb', 'ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d')
raw = one(raw, "{'prepare.py', 'run_controls.py', 'seal.py'}", "{'bootstrap.py', 'prepare.py', 'run_controls.py', 'seal.py'}")
(BASE / 'record_command.py').write_text(raw)

raw = (OLD / 'seal.py').read_text().replace('apple-settings-fixed-chunk-runtime-preparation.md', 'apple-focus-system-runtime-preparation.md')
(BASE / 'seal.py').write_text(raw)

raw = (OLD / 'run_controls.py').read_text()
# Utility fixtures move coherently; the selected 32-file runtime uses the closed derivation above.
for before, after in [('root-selection.7', 'root-selection.8'), ('MixerFocusReferenceV7-', 'MixerFocusReferenceV8-'),
                      ('native-run-v7-', 'native-run-v8-'), ('runtime-import.7', 'runtime-import.8'),
                      ('runtime.7', 'runtime.8')]: raw = raw.replace(before, after)
raw = raw.replace('root-selection.6', 'root-selection.7').replace('MixerFocusReferenceV6-', 'MixerFocusReferenceV7-')
raw = raw.replace('native-run-v6-', 'native-run-v7-').replace('runtime-import.6', 'runtime-import.7').replace('runtime.6', 'runtime.7')
raw = one(raw, "sorted([p.RECEIVER, 'importer.py', 'join_support.py', 'local_first_failure.py'])", "sorted(p.literal_delta())")
raw = one(raw, "p.reviewed_payload()['sources/selected/' + p.RECEIVER]", "p.prior_payload()[p.RECEIVER]")
raw = one(raw, 'for version in [7, 6, 5, 8]:', 'for version in [8, 7, 6, 9]:')
raw = one(raw, 'accepted = version == 7 and not wrong_argv', 'accepted = version == 8 and not wrong_argv')
(BASE / 'run_controls.py').write_text(raw)
print('Derived host utilities; no runtime module imported or native action performed')
