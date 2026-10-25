#!/usr/bin/env python3
"""Read-only sealed audit: no extraction, builds, runtime or output-file writes."""
import collections
import json
import plistlib
import sys
from common import *

REPORT = ROOT / 'docs/apple-focus-system-native-build.md'

def load(name): return json.loads((OUT / name).read_bytes())

def inventory():
    result = {}
    for p in sorted(BASE.rglob('*')):
        if p.is_dir(): continue
        if p in [BASE / 'handoff.json', BASE / 'handoff.sha256']: continue
        result[str(p.relative_to(ROOT))] = binding(p, True)
    result[str(REPORT.relative_to(ROOT))] = binding(REPORT, True)
    return dict(sorted(result.items()))

def audit():
    inputs = verify_inputs()
    assert load('input-bindings-before.json') == load('input-bindings-after.json') == inputs
    receipt = load('receipt.json')
    assert receipt['passed'] and receipt['status'] == 'compiled-linked-fresh-app-and-runner-build-only'
    assert receipt['sourceRevisionReportedByRoot'] == REVISION
    assert receipt['allCommandsZeroExitEOFNoSignalsNoTimeoutGroupsAbsent']
    assert receipt['appProductFilesFresh'] == 13 and receipt['runnerProductFilesFresh'] == 42
    assert receipt['oldAppProductFilesCopied'] == 0
    assert not receipt['gitQueried'] and not receipt['nativeExecuted'] and not receipt['runtimeSelected']
    assert not receipt['nativeAccepted'] and not receipt['futureRuntimeIngestionAccepted']
    assert not receipt['originalOraclePassed'] and not receipt['gaAccepted']
    assert receipt['simulatorOrDeviceCommands'] == 0 and receipt['physicalPhones'] == 'disconnected-deferred'
    assert not receipt['listenersOrExplicitNetwork'] and not receipt['uiOrCapture'] and not receipt['sourceEdits']
    source = payload((ROOT / SOURCE).read_bytes())
    selected_rows = rows(source)
    source_values = payload((OUT / 'sources.tar.gz').read_bytes())
    source_rows = rows(source_values)
    assert source_values == {n.removeprefix('accepted/'): v for n, v in source.items()}
    manifest = load('source-manifest.json')
    assert manifest['sources'] == source_rows and manifest['selectedArchiveMembers'] == selected_rows
    assert manifest['archive'] == receipt['sourceArchive'] == binding(OUT / 'sources.tar.gz')
    assert manifest['selectedArchive'] == binding(ROOT / SOURCE)
    assert manifest['changedFromPriorCompileClosure'] == CHANGED and manifest['unchangedCompileClosureFiles'] == 38
    assert manifest['sourceTreeSHA256'] == receipt['sourceTreeSHA256'] == sha(canonical(source_rows))
    assert manifest['selectedSourceTreeSHA256'] == receipt['selectedSourceTreeSHA256'] == sha(canonical(selected_rows))
    assert len(source_rows) == receipt['sourceFiles'] == 40 and all(r['mode'] == 0o444 for r in source_rows.values())
    recipes = recipe_commands()
    commands = load('commands.json')
    comparison = load('recipe-comparison.json')
    assert comparison['commands'] == recipes and comparison['substitutionOnly']
    assert comparison['source'] == binding(ROOT / RECIPE)
    assert comparison['originalScratchPrefix'] == OLD_SCRATCH and comparison['ownedScratchPrefix'] == str(SCRATCH)
    assert comparison['originalBuildScript'] == binding(ROOT / 'verification/apple-focus-reference-diagnostic-v1/build.py')
    assert comparison['qualificationReviewHandoff'] == binding(ROOT / 'verification/apple-focus-reference-diagnostic-v1-independent-review/handoff.json')
    assert len(commands) == 8 and receipt['exitCodes'] == {c['name']: c['exitCode'] for c in commands}
    for c, expected in zip(commands, recipes):
        for k, v in expected.items(): assert c[k] == v, (c['name'], k)
        assert c['exitCode'] == 0 and not c['timedOut'] and not c['signalsSent']
        assert c['stdoutEOF'] and c['stderrEOF'] and c['processGroupAbsent']
        for stream in ['stdout', 'stderr']:
            assert c[stream] == binding(OUT / (c['name'] + '.' + stream))
    assert (OUT / 'xcode-version.stdout').read_bytes() == b'Xcode 26.6\nBuild version 17F113\n'
    assert b'Apple Swift version 6.3.3' in (OUT / 'swift-version.stdout').read_bytes()
    assert (OUT / 'sdk-version.stdout').read_bytes() == b'26.5\n'
    tools = load('tools.json')
    originals = json.loads((ROOT / ORIGINAL / 'tool-bindings.json').read_bytes())['tools']
    assert tools['bindings'] == originals == {p: binding(Path(p).resolve()) for p in originals}
    assert tools['resolvedPaths'] == {p: str(Path(p).resolve()) for p in originals}
    assert tools['sdkRequested'] == str(SDK) and tools['sdkResolved'] == str(SDK.resolve())
    warnings = load('warning-comparison.json')
    assert warnings['originalQualificationFullAppAndRunnerBaseline']
    count = 0
    for name in ['mixer-core', 'mixer-ui', 'app', 'runner']:
        r = warnings['commandWarnings'][name]
        assert r['sameMessageMultisets']
        for stream in ['stdout', 'stderr']:
            now = warning_messages((OUT / (name + '.' + stream)).read_bytes())
            old = warning_messages((ROOT / ORIGINAL / 'commands' / (name + '.' + stream)).read_bytes())
            assert now == r['current'][stream] and old == r['originalQualification'][stream]
            assert collections.Counter(now) == collections.Counter(old)
            count += len(now)
    assert count == warnings['warningLineOccurrences'] == receipt['warningLineOccurrences'] == 21
    products = payload((OUT / 'products.tar.gz').read_bytes())
    product_rows = rows(products)
    pm = load('product-manifest.json')
    assert product_rows == pm['products'] and len(product_rows) == receipt['productFiles'] == 55
    assert pm['archive'] == receipt['productArchive'] == binding(OUT / 'products.tar.gz')
    assert pm['productTreeSHA256'] == receipt['productTreeSHA256'] == sha(canonical(product_rows))
    assert pm['sourceTreeSHA256'] == receipt['sourceTreeSHA256']
    assert pm['appProductsFresh'] and pm['runnerProductsFresh'] and pm['oldAppProductFilesCopied'] == 0
    assert pm['appProductFiles'] == 13 and pm['runnerProductFiles'] == 42 and not pm['nativeExecuted']
    inspection = product_inspection(products)
    actual_inspection = load('product-inspection.json')
    assert actual_inspection['machO'] == inspection['machO'] and actual_inspection['plists'] == inspection['plists']
    expected_compiled = ['MixerToggleDiagnostics.app/Frameworks/libMixerCore.dylib', 'MixerToggleDiagnostics.app/Frameworks/libMixerUI.dylib',
                         'MixerToggleDiagnostics.app/MixerToggleDiagnostics',
                         'runner-products/Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests']
    assert actual_inspection['freshCompiledLinkedTargets'] == expected_compiled
    assert actual_inspection['appleRunnerLauncherAndFrameworksArePlatformProvided']
    for n, expected_type in zip(expected_compiled, [6, 6, 2, 8]):
        m = inspection['machO'][n]
        assert m['cpuType'] == 0x100000c and m['fileType'] == expected_type
        assert m['buildVersions'] == [{'platform': 7, 'minimumOS': '26.0.0', 'sdk': '26.5.0', 'toolCount': 1}]
    app_macho = inspection['machO'][expected_compiled[2]]
    assert '@executable_path/Frameworks' in app_macho['rpaths']
    assert {'@rpath/libMixerCore.dylib', '@rpath/libMixerUI.dylib'} <= {d['name'] for d in app_macho['dylibs']}
    source_plist = source['accepted/source/Prototype/Info.plist'][0]
    info = plistlib.loads(source_plist)
    assert info['MinimumOSVersion'] == '17.0'
    info['MinimumOSVersion'] = '26.0'
    app_info = products['MixerToggleDiagnostics.app/Info.plist']
    assert app_info[0] == plistlib.dumps(info)
    packaging = load('packaging-derivation.json')
    assert packaging['source'] == selected_rows['accepted/source/Prototype/Info.plist']
    assert packaging['product'] == row(*app_info)
    assert packaging['changedProperty'] == 'MinimumOSVersion' and packaging['before'] == '17.0' and packaging['after'] == '26.0'
    assert packaging['sourceUnchanged'] and packaging['sameDerivationAsOriginal'] and packaging['signing'] == 'unsigned'
    cleanup = load('cleanup.json')
    assert cleanup['ownedScratchPath'] == str(SCRATCH) and not SCRATCH.exists()
    for k in ['inodeStable', 'regularFilesSingleLink', 'processGroupsAbsent', 'stdoutStderrEOF', 'holdersAbsent', 'ownedScratchRemoved']: assert cleanup[k], k
    assert cleanup['nativeInstancesTouched'] == 0 and not cleanup['otherProjectsTouched']
    assert cleanup['removedFileBytes'] == 165203605 and cleanup['removedRegularFiles'] == 455
    assert cleanup['archivesVerifiedBeforeRemoval'] == {
        'sources.tar.gz': {'binding': binding(OUT / 'sources.tar.gz'), 'regularMembers': 40},
        'products.tar.gz': {'binding': binding(OUT / 'products.tar.gz'), 'regularMembers': 55}}
    holders = load('holder-check.json')
    assert holders['argv'] == ['/usr/sbin/lsof', '-nP', '+D', str(SCRATCH)]
    assert holders['exitCode'] == 1 and holders['stdoutEOF'] and holders['stderrEOF']
    for s in ['stdout', 'stderr']:
        assert holders[s] == binding(OUT / ('holders.' + s)) and holders[s]['bytes'] == 0
    driver = json.loads((BASE / 'driver-receipt.json').read_bytes())
    for k in ['stdoutEOF', 'stderrEOF', 'processGroupAbsent']: assert driver[k]
    assert driver['exitCode'] == 0 and not driver['timedOut'] and not driver['signalsSent']
    assert driver['script'] == binding(BASE / 'build.py') and driver['common'] == binding(BASE / 'common.py')
    initial = json.loads((BASE / 'driver-command.json').read_bytes())
    assert all(driver[k] == v for k, v in initial.items())
    for s in ['stdout', 'stderr']: assert driver[s] == binding(BASE / ('driver.' + s))
    assert driver['stderr']['bytes'] == 0
    # The retained preflight failed before creating scratch or invoking a compiler.
    old = BASE / 'attempts/preflight-1'
    prior = json.loads((old / 'driver-receipt.json').read_bytes())
    assert prior['exitCode'] == 1 and prior['processGroupAbsent'] and prior['stdoutEOF'] and prior['stderrEOF']
    assert prior['script'] == binding(old / 'build.py') and prior['common'] == binding(old / 'common.py')
    for s in ['stdout', 'stderr']: assert prior[s] == binding(old / ('driver.' + s))
    assert not (old / 'attempt-1/owned-build').exists() and not (old / 'attempt-1/commands.json').exists()
    assert 'AssertionError' in (old / 'attempt-1/failure.txt').read_text()
    explanation = json.loads((old / 'explanation.json').read_bytes())
    assert explanation['compilerInvocations'] == 0 and not explanation['ownedScratchCreated']
    return {'passed': True, 'upstreamHandoffMembersVerified': sum(inputs['handoffMembersVerified'].values()),
            'sourceFiles': 40, 'sourceByteChanges': 2, 'selectedSourceMode': '0444', 'historicalSourceMode': '0644',
            'freshAppProductFiles': 13, 'freshRunnerProductFiles': 42, 'oldAppProductFilesCopied': 0,
            'productArchiveSHA256': binding(OUT / 'products.tar.gz')['sha256'], 'productTreeSHA256': receipt['productTreeSHA256'],
            'warningLineOccurrences': count, 'ownedScratchAbsent': True, 'nativeExecuted': False,
            'runtimeSelected': False, 'futureRuntimeIngestionAccepted': False, 'nativeAccepted': False, 'gaAccepted': False}

def main():
    handoff = json.loads((BASE / 'handoff.json').read_bytes())
    actual = inventory()
    assert handoff['members'] == actual
    assert handoff['memberTreeSHA256'] == sha(canonical(actual))
    digest = sha((BASE / 'handoff.json').read_bytes())
    assert (BASE / 'handoff.sha256').read_text() == digest + '  handoff.json\n'
    assert handoff['rootSelectionSHA256'] == PINS[SELECTION]
    result = audit()
    assert handoff['audit'] == result
    print(json.dumps({'handoffSHA256': digest, 'sealedMembers': len(actual), **result}, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__': sys.exit(main())
