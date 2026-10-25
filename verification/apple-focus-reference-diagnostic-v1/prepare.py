#!/usr/bin/env python3
"""Fresh source-only reference diagnostic; no runtime module or native tool import."""
import argparse
import difflib
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OLD = ROOT / 'verification/apple-focus-diagnostic-runtime-v1'
BUILD = ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1-build'
PACKET_SHA = 'd7c4c0f146434eeb7323036809acb5b4a80d41ff10f596eed8c25bdaa314e783'
SOURCE_ARCHIVE_SHA = '5b7f6b663e71b0ce56bb016bb0c42e5e30b622d20469e0a47b89cab352625e32'
RUNTIME_ARCHIVE_SHA = 'a2dc43359e23b0c4fec0f7bc7f8224ed9a5ba678f32d2e7fc571b98093e24715'
OBSERVER_SHA = 'c712724207fb5d327da0f6367e7a7f598494b3bb43f8b25fdfefcf94d3aefa88'
APP = 'source/Prototype/main.swift'
RUNNER = 'harness/UITests/ToggleUITests.swift'
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010ReferenceFirstTab']
ORACLES = [
    'apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py',
    'apple-toggle-keyboard-focus/keyboard_oracle.py',
    'apple-toggle-keyboard-focus/cases.json',
    'apple-toggle-pan-commit-harness-v2/commit_oracle.py',
    'apple-toggle-pan-commit-harness-v2/cases.json',
    'apple-toggle-native-interruption/interruption_oracle.py',
    'apple-toggle-native-interruption/cases.json',
    'apple-toggle-pan-origin-correction/oracle.py',
    'apple-toggle-semantic-activation/semantic_oracle.py',
]


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def row(path):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            'Canonical regular input required: ' + str(path))
    data = path.read_bytes()
    return {'kind': 'file', 'bytes': len(data), 'mode': stat.S_IMODE(info.st_mode), 'sha256': sha(data)}


def read(path, expected=None):
    bound = row(path)
    require(expected is None or bound['sha256'] == expected, 'Input hash changed: ' + str(path))
    return path.read_bytes()


def archive(path, manifest, prefix, expected_sha):
    read(path, expected_sha)
    values, seen = {}, set()
    files = {prefix + name: item for name, item in manifest.items()}
    directories = {str(parent) for name in files for parent in PurePosixPath(name).parents if str(parent) != '.'}
    with tarfile.open(path, 'r:gz') as source:
        members = source.getmembers()
        require(len(members) <= 256, 'Source archive entry bound exceeded')
        for member in members:
            name = PurePosixPath(member.name)
            require(member.name and not name.is_absolute() and '..' not in name.parts and str(name) == member.name,
                    'Unsafe source archive name')
            require(member.name not in seen, 'Duplicate source archive member')
            seen.add(member.name)
            if member.isdir():
                require(member.name in directories and member.size == 0 and member.mode == 0o755,
                        'Unexpected source archive directory')
                continue
            require(member.name in files, 'Unmanifested source archive member')
            expected = files[member.name]
            require(expected['kind'] == 'file' and member.isfile() and member.mode == expected['mode']
                    and member.size == expected['bytes'] and member.size <= 2_000_000,
                    'Source archive type/mode/size changed')
            data = source.extractfile(member).read(member.size + 1)
            require(sha(data) == expected['sha256'] and len(data) == expected['bytes'], 'Source member changed')
            values[member.name.removeprefix(prefix)] = data
    require(seen == set(files) | directories, 'Source archive membership incomplete')
    return values


def inputs():
    packet_bytes = read(OLD / 'packet.json', PACKET_SHA)
    packet = json.loads(packet_bytes)
    outputs = json.loads(read(OLD / 'output-manifest.json', packet['outputManifestSHA256']))
    sources = json.loads(read(BUILD / 'source-manifest.json'))
    require(sources['materializedSources'] == outputs['acceptedSources'], 'Accepted source manifests disagree')
    runtime_manifest = json.loads(read(OLD / 'selected-runtime-source-manifest.json', packet['selectedSourceArchiveManifestSHA256']))
    require(runtime_manifest['files'] == outputs['selectedRuntime'], 'Selected runtime manifests disagree')
    accepted = archive(BUILD / 'accepted-sources.tar.gz', sources['materializedSources'], 'accepted/', SOURCE_ARCHIVE_SHA)
    selected = archive(OLD / 'selected-runtime-sources.tar.gz', runtime_manifest['files'], 'selected/', RUNTIME_ARCHIVE_SHA)
    require(len(accepted) == 39 and len(selected) == 29, 'Exact inherited source membership required')
    require(sha(selected['command_observer.py']) == OBSERVER_SHA, 'Accepted command observer V2 changed')
    paths = [OLD / 'packet.json', OLD / 'output-manifest.json', OLD / 'selected-runtime-source-manifest.json',
             OLD / 'selected-runtime-sources.tar.gz', BUILD / 'source-manifest.json', BUILD / 'accepted-sources.tar.gz',
             OLD / 'runtime/captures/0001-before-1.json', OLD / 'runtime/captures/0001-after-1.json',
             OLD / 'runtime/captures/0001-keyboard-witness-1.json',
             ROOT / 'docs/apple-focus-diagnostic-runtime-v1-checkpoint.md', ROOT / 'docs/apple-focus-diagnostic-v1-analysis.md',
             ROOT / 'AGENTS.md']
    bindings = {str(path.relative_to(ROOT)): row(path) for path in paths}
    return accepted, selected, sources, bindings


def once(text, old, new):
    require(text.count(old) == 1, 'Missing or ambiguous derivative anchor: ' + old[:90])
    return text.replace(old, new, 1)


def render(accepted):
    changed = dict(accepted)
    changed[APP] = once(accepted[APP].decode(),
        '    override var preferredFocusEnvironments: [UIFocusEnvironment] { [toggle] }',
        '    override var preferredFocusEnvironments: [UIFocusEnvironment] { [referenceButton] }').encode()
    runner = once(accepted[RUNNER].decode(),
        'expectedSelection: Bool? = nil) throws -> [String: Any] {',
        'expectedSelection: Bool? = nil, requiredFocusBefore: String? = nil) throws -> [String: Any] {')
    runner = once(runner, '        let before = try ax("before")\n',
        '        let before = try ax("before")\n'
        '        if let requiredFocusBefore {\n'
        '            let observedFocus = try focus(before)\n'
        '            let premisePassed = observedFocus == requiredFocusBefore\n'
        '            try jsonAttachment("Reference first-Tab precondition", ["schema": "mixer.apple-focus-reference-precondition.1",\n'
        '                "case": caseName, "phase": phase, "generation": baseline["generation"]!, "actionIndex": baseline["actionIndex"]!,\n'
        '                "requiredFocus": requiredFocusBefore, "observedFocus": observedFocus as Any? ?? NSNull(),\n'
        '                "passed": premisePassed, "actionInjectionCount": 0, "before": before])\n'
        '            guard premisePassed else { throw Failure.focus("Reference first-Tab precondition failed before key injection") }\n'
        '        }\n')
    runner = once(runner, '    func test010EnabledFromOff() throws { try enabled(false) }\n',
        '    func test010ReferenceFirstTab() throws {\n'
        '        _ = try launchCase("keyboard-enabled-off", initial: false)\n'
        '        try key("acquire", "tab", requiredFocusBefore: "plain-uibutton-reference")\n'
        '    }\n'
        '    func test010EnabledFromOff() throws { try enabled(false) }\n')
    changed[RUNNER] = runner.encode()
    require({name for name in accepted if changed[name] != accepted[name]} == {APP, RUNNER}, 'Unexpected derivative membership')
    return changed


def manifest(values, original_modes):
    return {name: {'kind': 'file', 'bytes': len(data), 'mode': original_modes[name]['mode'], 'sha256': sha(data)}
            for name, data in sorted(values.items())}


def generated():
    accepted, selected, inherited, bindings = inputs()
    changed = render(accepted)
    source_rows = manifest(changed, inherited['materializedSources'])
    diff = ''.join(''.join(difflib.unified_diff(accepted[name].decode().splitlines(True), changed[name].decode().splitlines(True),
        fromfile='a/' + name, tofile='b/' + name)) for name in sorted(accepted) if accepted[name] != changed[name]).encode()
    oracle_rows = {name: row for name, row in json.loads((OLD / 'selected-runtime-source-manifest.json').read_bytes())['files'].items()
                   if name.startswith('inputs/runtime/verification/') and name.removeprefix('inputs/runtime/verification/') in ORACLES}
    require(len(oracle_rows) == 9, 'Exact pure oracle closure required')
    contract = {'schema': 'mixer.apple-focus-reference-diagnostic.1', 'status': 'source-prepared-runtime-unselected',
        'inheritedPacketSHA256': PACKET_SHA, 'sourceRevisionLabel': inherited['sourceRevisionLabel'],
        'sourceRevisionMeaning': 'Inherited frozen compilation label; no Git command in this lane.',
        'methods': METHODS, 'originalOracleCase': 'keyboard-enabled-off', 'phase': 'acquire',
        'requiredFocusBefore': 'plain-uibutton-reference', 'maximumApplicationKeyInjections': 1,
        'publicKeyAPI': 'XCUIElement.typeKey(_:modifierFlags:)', 'fixedIDs': ['authored-toggle', 'plain-uibutton-reference', 'next-focus'],
        'environment': {'developerDirectory': '/Applications/Xcode_26.6.app/Contents/Developer', 'Xcode': '26.6', 'XcodeBuild': '17F113',
            'simulatorRuntime': 'iOS 26.5', 'simulatorRuntimeBuild': '23F77', 'deviceType': 'iPhone 17 Pro'},
        'unchangedBounds': {'commandSeconds': 600, 'witnessSeconds': 12, 'focusOnlyFollowUpSeconds': 0.250,
            'defaultTestAllowanceSeconds': 30, 'maximumTestAllowanceSeconds': 45},
        'diagnosticOutcomeContract': ['failed-reference-precondition-zero-injections', 'one-original-strict-oracle-result',
            'incomplete-after-passing-precondition-injection-status-unknown'],
        'originalFailurePreserved': True, 'originalTestMethodUnchanged': True, 'oracleSourcesUnchanged': True,
        'observerV2SHA256': sha(selected['command_observer.py']), 'pureOracleClosure': oracle_rows,
        'derivativeSources': source_rows, 'derivativeSourceTreeSHA256': sha(stable(source_rows)),
        'changedSources': {name: {'beforeSHA256': sha(accepted[name]), 'afterSHA256': sha(changed[name])} for name in [APP, RUNNER]},
        'inputs': bindings, 'inputTreeSHA256': sha(stable(bindings)), 'patchSHA256': sha(diff),
        'runtimeSelected': False, 'nativeExecuted': False, 'completeCaseSet': False, 'runPassed': False,
        'fullSixCaseQualification': False, 'nativeKeyboardQualification': False, 'carrierAccepted': False,
        'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
    return changed, source_rows, diff, contract


def write_archive(path, values, rows):
    require(not path.exists(), 'Preserve prior derivative archive')
    directories = {str(parent) for name in rows for parent in PurePosixPath('accepted/' + name).parents if str(parent) != '.'}
    with path.open('xb') as output, gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as zipped, tarfile.open(fileobj=zipped, mode='w') as target:
        for name in sorted(directories):
            info = tarfile.TarInfo(name); info.type = tarfile.DIRTYPE; info.mode = 0o755; target.addfile(info)
        for name, data in sorted(values.items()):
            info = tarfile.TarInfo('accepted/' + name); info.mode = rows[name]['mode']; info.size = len(data)
            target.addfile(info, io.BytesIO(data))
    require(archive(path, rows, 'accepted/', row(path)['sha256']) == values, 'Derivative archive round trip differs')


def prepare():
    require(not (BASE / 'prepared.json').exists(), 'Preserve previous preparation')
    values, rows, patch, contract = generated()
    (BASE / 'source.patch').write_bytes(patch)
    write_archive(BASE / 'accepted-sources.tar.gz', values, rows)
    contract['archive'] = row(BASE / 'accepted-sources.tar.gz')
    (BASE / 'prepared.json').write_bytes(stable(contract))
    print('PASS: two-source reference derivative archived; runtime unselected')


def verify():
    values, rows, patch, contract = generated()
    require((BASE / 'source.patch').read_bytes() == patch, 'Derivative source diff changed')
    contract['archive'] = row(BASE / 'accepted-sources.tar.gz')
    require((BASE / 'prepared.json').read_bytes() == stable(contract), 'Prepared contract changed')
    require(archive(BASE / 'accepted-sources.tar.gz', rows, 'accepted/', contract['archive']['sha256']) == values,
            'Derivative source archive changed')
    return {'preparedSHA256': sha(stable(contract)), 'sourceTreeSHA256': contract['derivativeSourceTreeSHA256'],
            'nativeExecuted': False, 'runtimeSelected': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'verify'])
    args = parser.parse_args()
    if args.action == 'prepare': prepare()
    else: print(json.dumps(verify(), sort_keys=True))
