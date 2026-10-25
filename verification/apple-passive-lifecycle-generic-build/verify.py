#!/usr/bin/env python3
"""Read-only evidence audit; no extraction, writes, compilation or native commands."""
import collections
import json
import plistlib
import sys
from common import *

REPORT = ROOT / 'docs/apple-passive-lifecycle-generic-build.md'

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
    passed = receipt['passed']
    assert receipt['status'] == ('compiled-linked-fresh-app-and-runner-build-only' if passed else 'build-failed-preserved')
    assert receipt['sourceRevisionReportedByRoot'] == REVISION
    for k in ['gitQueried','nativeExecuted','runtimeSelected','nativeAccepted','futureRuntimeIngestionAccepted','originalOraclePassed','gaAccepted','listenersOrExplicitNetwork','uiOrCapture','sourceEdits']:
        assert receipt[k] is False, k
    assert receipt['simulatorOrDeviceCommands'] == 0 and receipt['physicalPhones'] == 'disconnected-deferred'
    assert receipt['oldAppProductFilesCopied'] == 0 and receipt['recipeOnlyChangesScratchPrefixAndTwoAppSources']
    assert receipt['inputsAndToolsUnchangedAfterBuild'] and receipt['ownedScratchRemoved']
    source = payload((ROOT / SOURCE).read_bytes())
    selected_rows = rows(source)
    source_values = payload((OUT / 'sources.tar.gz').read_bytes())
    source_rows = rows(source_values)
    assert source_values == {n.removeprefix('accepted/'): v for n, v in source.items()}
    manifest = load('source-manifest.json')
    assert manifest['sources'] == source_rows and manifest['selectedArchiveMembers'] == selected_rows
    assert manifest['archive'] == receipt['sourceArchive'] == binding(OUT / 'sources.tar.gz')
    assert manifest['selectedArchive'] == binding(ROOT / SOURCE)
    assert manifest['changedFromPriorCompileClosure'] == CHANGED and manifest['unchangedCompileClosureFiles'] == 39
    assert manifest['addedSourceMembers'] == ADDED
    assert manifest['prototypeSwiftFiles'] == PROTOTYPE_NAMES and manifest['harnessSwiftFiles'] == HARNESS_NAMES
    assert manifest['overallSwiftFiles'] == receipt['overallSwiftFiles'] == 37
    assert receipt['prototypeSwiftFiles'] == 12 and receipt['harnessSwiftFiles'] == 4
    assert manifest['sourceTreeSHA256'] == receipt['sourceTreeSHA256'] == sha(canonical(source_rows))
    assert manifest['selectedSourceTreeSHA256'] == receipt['selectedSourceTreeSHA256'] == sha(canonical(selected_rows))
    assert len(source_rows) == receipt['sourceFiles'] == 42 and all(r['mode'] == 0o444 for r in source_rows.values())
    recipes = recipe_commands()
    commands = load('commands.json')
    comparison = load('recipe-comparison.json')
    assert comparison['commands'] == recipes and comparison['scratchSubstitutionAndTwoAdditionalAppSourcesOnly']
    assert comparison['additionalAppSources'] == ADDED
    assert comparison['source'] == binding(ROOT / RECIPE)
    assert comparison['originalScratchPrefix'] == OLD_SCRATCH and comparison['ownedScratchPrefix'] == str(SCRATCH)
    assert comparison['originalBuildScript'] == binding(ROOT / 'verification/apple-focus-reference-diagnostic-v1/build.py')
    assert comparison['qualificationReviewHandoff'] == binding(ROOT / 'verification/apple-focus-reference-diagnostic-v1-independent-review/handoff.json')
    assert len(commands) == 8 and receipt['exitCodes'] == {c['name']: c['exitCode'] for c in commands}
    all_clean = all(c['exitCode'] == 0 and c['stdoutEOF'] and c['stderrEOF'] and not c['signalsSent'] and not c['timedOut'] and c['processGroupAbsent'] for c in commands)
    assert all_clean == receipt['allCommandsZeroExitEOFNoSignalsNoTimeoutGroupsAbsent']
    assert passed == all(c['exitCode'] == 0 for c in commands)
    for c, expected in zip(commands, recipes):
        for k, v in expected.items(): assert c[k] == v, (c['name'], k)
        assert c['stdoutEOF'] and c['stderrEOF'] and c['processGroupAbsent']
        assert 0 < c['actualTimeoutSeconds'] <= c['timeoutSeconds'] and c['overallBuildDeadlineSeconds'] == 780
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
        matches = []
        for stream in ['stdout', 'stderr']:
            now = warning_messages((OUT / (name + '.' + stream)).read_bytes())
            old = warning_messages((ROOT / ORIGINAL / 'commands' / (name + '.' + stream)).read_bytes())
            assert now == r['current'][stream] and old == r['originalQualification'][stream]
            matches.append(collections.Counter(now) == collections.Counter(old))
            count += len(now)
        assert r['sameMessageMultisets'] == all(matches)
    assert count == warnings['warningLineOccurrences'] == receipt['warningLineOccurrences']
    assert receipt['allWarningMessageMultisetsMatchFullOriginalQualification'] == all(r['sameMessageMultisets'] for r in warnings['commandWarnings'].values())
    product_name = 'products.tar.gz' if passed else 'failed-partial-products.tar.gz'
    products = payload((OUT / product_name).read_bytes())
    product_rows = rows(products)
    pm = load('product-manifest.json')
    assert product_rows == pm['products'] and len(product_rows) == receipt['productFiles']
    assert pm['archive'] == receipt['productArchive'] == binding(OUT / product_name)
    assert pm['productTreeSHA256'] == receipt['productTreeSHA256'] == sha(canonical(product_rows))
    assert pm['sourceTreeSHA256'] == receipt['sourceTreeSHA256']
    assert pm['oldAppProductFilesCopied'] == 0 and not pm['nativeExecuted']
    app_count = sum(n.startswith('MixerToggleDiagnostics.app/') for n in product_rows)
    runner_count = sum(n.startswith('runner-products/') for n in product_rows)
    assert pm['appProductFiles'] == receipt['appProductFilesFresh'] == app_count
    assert pm['runnerProductFiles'] == receipt['runnerProductFilesFresh'] == runner_count
    inspection = product_inspection(products)
    actual = load('product-inspection.json')
    assert actual['machO'] == inspection['machO'] and actual['plists'] == inspection['plists']
    expected_compiled = ['MixerToggleDiagnostics.app/Frameworks/libMixerCore.dylib','MixerToggleDiagnostics.app/Frameworks/libMixerUI.dylib','MixerToggleDiagnostics.app/MixerToggleDiagnostics','runner-products/Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests']
    assert actual['freshCompiledLinkedTargets'] == expected_compiled
    assert actual['appleRunnerLauncherAndFrameworksArePlatformProvided']
    if passed:
        assert app_count == 13 and runner_count == 42 and len(product_rows) == 55
        assert pm['appProductsFresh'] and pm['runnerProductsFresh']
    for n, expected_type in zip(expected_compiled, [6,6,2,8]):
        if n not in inspection['machO']:
            assert not passed
            continue
        m = inspection['machO'][n]
        assert m['cpuType'] == 0x100000c and m['fileType'] == expected_type
        assert m['buildVersions'] == [{'platform':7,'minimumOS':'26.0.0','sdk':'26.5.0','toolCount':1}]
    if receipt['exitCodes']['app'] == 0:
        app_macho = inspection['machO'][expected_compiled[2]]
        assert '@executable_path/Frameworks' in app_macho['rpaths']
        assert {'@rpath/libMixerCore.dylib','@rpath/libMixerUI.dylib'} <= {d['name'] for d in app_macho['dylibs']}
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
    test_info = products['runner-products/Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/Info.plist'][0]
    assert plistlib.loads(test_info)['MinimumOSVersion'] == '26.0'
    runner_info = products['runner-products/Debug-iphonesimulator/MixerToggleUITests-Runner.app/Info.plist'][0]
    assert plistlib.loads(runner_info)['MinimumOSVersion'] == '13.0'
    if not passed:
        unavailable = load('packaging-not-applied.json')
        assert not unavailable['applied'] and unavailable['sourceMinimumOSVersion'] == '17.0' and unavailable['plannedProductMinimumOSVersion'] == '26.0'
        assert unavailable['reason'] == 'App compilation failed before app executable and app Info.plist packaging.'
        assert unavailable['source'] == selected_rows['accepted/source/Prototype/Info.plist']
        assert 'MixerToggleDiagnostics.app/MixerToggleDiagnostics' not in products
        assert 'MixerToggleDiagnostics.app/Info.plist' not in products
        failure = load('compile-failure.json')
        assert failure['sourceMember'] == 'accepted/source/Prototype/PassiveLifecycleObserver.swift'
        assert failure['line'] == 25 and failure['column'] == 50 and failure['commandExitCode'] == 1
        assert failure['stderr'] == binding(OUT/'app.stderr')
        assert failure['source'] == selected_rows[failure['sourceMember']]
        assert failure['diagnostic'] in (OUT/'app.stderr').read_text()
        assert not failure['sourceChanged'] and not failure['retrySelected']
    observed = load('observed-product-scope.json')
    assert observed['originalInspection'] == binding(OUT/'product-inspection.json')
    assert not observed['buildPassed'] and not observed['appExecutablePresent'] and not observed['appInfoPlistPresent']
    assert observed['actuallyCompiledLinkedTargets'] == [n for n in expected_compiled if n in inspection['machO']]
    assert observed['missingCompiledLinkedTargets'] == [expected_compiled[2]]
    assert observed['partialAppFiles'] == app_count and observed['freshRunnerFiles'] == runner_count
    proposal = json.loads((BASE/'correction-proposal.json').read_bytes())
    assert proposal['acceptedSource'] == selected_rows['accepted/source/Prototype/PassiveLifecycleObserver.swift']
    assert proposal['proposedPatch'] == binding(BASE/'correction-proposal.patch')
    assert proposal['status'] == 'proposal-only-uncompiled-unaccepted' and proposal['compilerInvocationsForProposal'] == 0
    for k in ['rootHasSelectedCorrection','changesApplied','nativeExecuted','gaAccepted']: assert proposal[k] is False
    assert failure['proposalOnly'] == binding(BASE/'correction-proposal.json')
    cleanup = load('cleanup.json')
    assert cleanup['ownedScratchPath'] == str(SCRATCH) and not SCRATCH.exists()
    for k in ['inodeStable','regularFilesSingleLink','processGroupsAbsent','stdoutStderrEOF','holdersAbsent','ownedScratchRemoved']: assert cleanup[k], k
    assert cleanup['nativeInstancesTouched'] == 0 and not cleanup['otherProjectsTouched']
    assert cleanup['removedFileBytes'] > 0 and cleanup['removedRegularFiles'] > 0
    assert cleanup['archivesVerifiedBeforeRemoval'] == {'sources.tar.gz':{'binding':binding(OUT / 'sources.tar.gz'),'regularMembers':42},product_name:{'binding':binding(OUT / product_name),'regularMembers':len(product_rows)}}
    holders = load('holder-check.json')
    assert holders['argv'] == ['/usr/sbin/lsof','-nP','+D',str(SCRATCH)]
    assert holders['exitCode'] == 1 and holders['stdoutEOF'] and holders['stderrEOF']
    for s in ['stdout','stderr']: assert holders[s] == binding(OUT / ('holders.'+s)) and holders[s]['bytes'] == 0
    driver = json.loads((BASE / 'driver-receipt.json').read_bytes())
    for k in ['stdoutEOF','stderrEOF','processGroupAbsent']: assert driver[k]
    assert driver['exitCode'] == (0 if passed else 1) and not driver['timedOut'] and not driver['signalsSent']
    assert driver['script'] == binding(BASE / 'build.py') and driver['common'] == binding(BASE / 'common.py')
    initial = json.loads((BASE / 'driver-command.json').read_bytes())
    assert all(driver[k] == v for k,v in initial.items())
    for s in ['stdout','stderr']: assert driver[s] == binding(BASE / ('driver.'+s))
    assert driver['stderr']['bytes'] == 0
    return {'evidenceAuditPassed':True,'buildPassed':passed,'upstreamHandoffMembersVerified':sum(inputs['handoffMembersVerified'].values()),'sourceFiles':42,'overallSwiftFiles':37,'prototypeSwiftFiles':12,'harnessSwiftFiles':4,'sourceByteChanges':1,'sourceAdditions':2,'unchangedSourceBytes':39,'selectedSourceMode':'0444','freshAppProductFiles':app_count,'freshRunnerProductFiles':runner_count,'oldProductFilesCopied':0,'productArchiveSHA256':binding(OUT / product_name)['sha256'],'productTreeSHA256':receipt['productTreeSHA256'],'warningLineOccurrences':count,'ownedScratchAbsent':True,'nativeExecuted':False,'runtimeSelected':False,'nativeAccepted':False,'gaAccepted':False}

def main():
    h = json.loads((BASE / 'handoff.json').read_bytes())
    actual = inventory()
    assert h['members'] == actual and h['memberTreeSHA256'] == sha(canonical(actual))
    digest = sha((BASE / 'handoff.json').read_bytes())
    assert (BASE / 'handoff.sha256').read_text() == digest+'  handoff.json\n'
    assert h['rootSelectionSHA256'] == binding(ROOT / SELECTION)['sha256']
    result = audit()
    assert h['audit'] == result
    print(json.dumps({'handoffSHA256':digest,'sealedMembers':len(actual),**result},indent=2,sort_keys=True))
    return 0

if __name__ == '__main__': sys.exit(main())
