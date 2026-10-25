#!/usr/bin/env python3
"""Compile/link the exact selected app and runner; no native execution."""
import collections
import datetime
import json
import os
import platform
import plistlib
import shutil
import signal
import subprocess
import sys
import time
import traceback
from common import *

COMMANDS = []
DEADLINE = time.monotonic() + 780

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def group_members(pgid):
    r = subprocess.run(['/bin/ps', '-axo', 'pid=,pgid='], capture_output=True, timeout=10, check=True)
    assert not r.stderr
    return [int(line.split()[0]) for line in r.stdout.decode().splitlines() if int(line.split()[1]) == pgid]

def command(recipe):
    env = os.environ.copy()
    env.update(recipe['explicitEnvironment'])
    started, stamp = utc(), time.monotonic()
    p = subprocess.Popen(recipe['argv'], cwd=recipe['cwd'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    sent, timedout = [], False
    actual_timeout = max(0.1, min(recipe['timeoutSeconds'], DEADLINE - time.monotonic()))
    try: out, err = p.communicate(timeout=actual_timeout)
    except subprocess.TimeoutExpired:
        timedout = True
        if group_members(p.pid): os.killpg(p.pid, signal.SIGTERM); sent.append('SIGTERM')
        try: out, err = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if group_members(p.pid): os.killpg(p.pid, signal.SIGKILL); sent.append('SIGKILL')
            out, err = p.communicate(timeout=5)
    name = recipe['name']
    (OUT / (name + '.stdout')).write_bytes(out)
    (OUT / (name + '.stderr')).write_bytes(err)
    COMMANDS.append({**recipe, 'startedUTC': started, 'finishedUTC': utc(), 'elapsedSeconds': time.monotonic() - stamp,
                     'actualTimeoutSeconds': actual_timeout, 'overallBuildDeadlineSeconds': 780, 'exitCode': p.returncode, 'timedOut': timedout, 'signalsSent': sent, 'ownedPID': p.pid, 'ownedPGID': p.pid,
                     'processGroupAbsent': not group_members(p.pid), 'stdoutEOF': True, 'stderrEOF': True,
                     'stdout': binding(OUT / (name + '.stdout')), 'stderr': binding(OUT / (name + '.stderr'))})
    save('commands.json', COMMANDS)
    assert COMMANDS[-1]['processGroupAbsent'], 'Owned child survives; preserve scratch'
    print(f'{name}: exit {p.returncode}', flush=True)
    return p.returncode

def cleanup():
    assert SCRATCH.is_dir() and not SCRATCH.is_symlink()
    before = SCRATCH.lstat()
    inode = {'device': before.st_dev, 'inode': before.st_ino, 'mode': before.st_mode}
    assert before.st_nlink >= 2
    assert all(not group_members(c['ownedPGID']) for c in COMMANDS)
    r = subprocess.run(['/usr/sbin/lsof', '-nP', '+D', str(SCRATCH)], capture_output=True, timeout=30)
    (OUT / 'holders.stdout').write_bytes(r.stdout)
    (OUT / 'holders.stderr').write_bytes(r.stderr)
    save('holder-check.json', {'argv': ['/usr/sbin/lsof', '-nP', '+D', str(SCRATCH)], 'exitCode': r.returncode,
                              'stdoutEOF': True, 'stderrEOF': True, 'stdout': binding(OUT / 'holders.stdout'),
                              'stderr': binding(OUT / 'holders.stderr')})
    assert r.returncode == 1 and not r.stdout and not r.stderr, 'Scratch has holders; preserve it'
    inventory = tree(SCRATCH)
    assert all((SCRATCH / n).lstat().st_nlink == 1 for n in inventory)
    after = SCRATCH.lstat()
    assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
    assert all(not group_members(c['ownedPGID']) for c in COMMANDS)
    verified_archives = {}
    for name in ['sources.tar.gz', 'products.tar.gz', 'failed-partial-products.tar.gz']:
        p = OUT / name
        if p.exists():
            verified_archives[name] = {'binding': binding(p), 'regularMembers': len(payload(p.read_bytes()))}
    shutil.rmtree(SCRATCH)
    save('cleanup.json', {'ownedScratchPath': str(SCRATCH), 'ownedScratchInodeBeforeAndImmediatelyBeforeRemoval': inode,
                         'inodeStable': True, 'regularFilesSingleLink': True, 'archivesVerifiedBeforeRemoval': verified_archives,
                         'removedFileBytes': sum(r['bytes'] for r in inventory.values()), 'removedRegularFiles': len(inventory),
                         'processGroupsAbsent': True, 'stdoutStderrEOF': True, 'holdersAbsent': True,
                         'ownedScratchRemoved': not SCRATCH.exists(), 'nativeInstancesTouched': 0, 'otherProjectsTouched': False})

def main():
    finite = json.loads((BASE / 'finite/receipt.json').read_bytes())
    assert finite['passed'] and finite['differentialSemanticOutputsEqual']
    assert finite['correctedSourceArchive'] == binding(ROOT / SOURCE)
    assert not OUT.exists(), 'Preserve every earlier attempt'
    OUT.mkdir()
    inputs = verify_inputs()
    save('input-bindings-before.json', inputs)
    source = payload((ROOT / SOURCE).read_bytes())
    SCRATCH.mkdir()
    (SCRATCH / 'tmp').mkdir()
    # Archive names already begin accepted/, matching the original recipe layout.
    for name, (raw, mode) in source.items():
        p = SCRATCH / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw); p.chmod(mode)
    source_rows = archive_tree(OUT / 'sources.tar.gz', SCRATCH / 'accepted')
    expected = {n.removeprefix('accepted/'): r for n, r in rows(source).items()}
    assert source_rows == expected
    save('source-manifest.json', {'schema': 1, 'sources': source_rows, 'sourceTreeSHA256': sha(canonical(source_rows)),
                                 'selectedArchiveMembers': rows(source), 'selectedSourceTreeSHA256': sha(canonical(rows(source))),
                                 'archive': binding(OUT / 'sources.tar.gz'), 'selectedArchive': binding(ROOT / SOURCE),
                                 'changedFromPriorCompileClosure': CHANGED, 'producerOnlyChangedMembers': ['accepted/source/Prototype/PassiveLifecycleObserver.swift'], 'producerByteIdenticalMembers': 41, 'unchangedCompileClosureFiles': 39, 'addedSourceMembers': ADDED, 'prototypeSwiftFiles': PROTOTYPE_NAMES, 'overallSwiftFiles': 37, 'harnessSwiftFiles': HARNESS_NAMES,
                                 'sourceRevisionReportedByRoot': REVISION, 'gitQueried': False})
    original_tools = json.loads((ROOT / ORIGINAL / 'tool-bindings.json').read_bytes())['tools']
    tool_paths = list(original_tools)
    tools_before = {p: binding(Path(p).resolve()) for p in tool_paths}
    assert tools_before == original_tools, 'Original recipe tools changed'
    save('tools.json', {'schema': 1, 'bindings': tools_before, 'resolvedPaths': {p: str(Path(p).resolve()) for p in tool_paths},
                        'sdkRequested': str(SDK), 'sdkResolved': str(SDK.resolve()), 'python': sys.version, 'platform': platform.platform(),
                        'sourceRevisionReportedByRoot': REVISION, 'originalToolsMatch': True})
    recipes = recipe_commands()
    save('recipe-comparison.json', {'source': binding(ROOT / GENERIC / 'attempt-1/commands.json'), 'originalScratchPrefix': str(ROOT / GENERIC / 'attempt-1/owned-build'),
                                  'ownedScratchPrefix': str(SCRATCH), 'scratchSubstitutionOnlyFromVerifiedGenericRecipe': True, 'additionalAppSources': ADDED, 'commands': recipes,
                                  'originalBuildScript': binding(ROOT / 'verification/apple-focus-reference-diagnostic-v1/build.py'),
                                  'qualificationReviewHandoff': binding(ROOT / 'verification/apple-focus-reference-diagnostic-v1-independent-review/handoff.json')})
    codes = {}
    (SCRATCH / 'products/MixerToggleDiagnostics.app/Frameworks').mkdir(parents=True)
    (SCRATCH / 'modules').mkdir()
    for r in recipes:
        name = r['name']
        if name in ['mixer-ui', 'app']:
            predecessor = 'mixer-core' if name == 'mixer-ui' else 'mixer-ui'
            if codes[predecessor] != 0: codes[name] = None; continue
        if name == 'runner': assert not (SCRATCH / 'runner-build').exists()
        if name == 'app': assert not (SCRATCH / 'products/MixerToggleDiagnostics.app/MixerToggleDiagnostics').exists()
        codes[name] = command(r)
        if codes[name] != 0:
            break
    assert (OUT / 'xcode-version.stdout').read_bytes() == b'Xcode 26.6\nBuild version 17F113\n'
    assert b'Apple Swift version 6.3.3' in (OUT / 'swift-version.stdout').read_bytes()
    assert (OUT / 'sdk-version.stdout').read_bytes() == b'26.5\n'
    assert tree(SCRATCH / 'accepted') == source_rows
    assert {p: binding(Path(p).resolve()) for p in tool_paths} == tools_before
    app = SCRATCH / 'products/MixerToggleDiagnostics.app'
    if codes.get('app') == 0:
        source_info = source['accepted/source/Prototype/Info.plist'][0]
        info = plistlib.loads(source_info)
        before = info['MinimumOSVersion']; assert before == '17.0'
        info['MinimumOSVersion'] = '26.0'
        (app / 'Info.plist').write_bytes(plistlib.dumps(info))
        save('packaging-derivation.json', {'source': row(source_info, source['accepted/source/Prototype/Info.plist'][1]),
                                         'product': binding(app / 'Info.plist'), 'changedProperty': 'MinimumOSVersion',
                                         'before': before, 'after': '26.0', 'sourceUnchanged': True, 'signing': 'unsigned',
                                         'sameDerivationAsOriginal': True})
    warning_result = {}
    for name in ['mixer-core', 'mixer-ui', 'app', 'runner']:
        current = {s: warning_messages((OUT / (name + '.' + s)).read_bytes()) if (OUT / (name + '.' + s)).exists() else [] for s in ['stdout', 'stderr']}
        original = {s: warning_messages((ROOT / ORIGINAL / 'commands' / (name + '.' + s)).read_bytes()) for s in ['stdout', 'stderr']}
        warning_result[name] = {'current': current, 'originalQualification': original,
                                'sameMessageMultisets': all(collections.Counter(current[s]) == collections.Counter(original[s]) for s in current)}
    save('warning-comparison.json', {'commandWarnings': warning_result,
                                     'warningLineOccurrences': sum(len(v) for r in warning_result.values() for v in r['current'].values()),
                                     'originalQualificationFullAppAndRunnerBaseline': True})
    export = SCRATCH / 'export'; export.mkdir()
    shutil.copytree(app, export / app.name)
    if (SCRATCH / 'runner-build/Build/Products').is_dir():
        shutil.copytree(SCRATCH / 'runner-build/Build/Products', export / 'runner-products')
    passed = len(codes) == 8 and all(v == 0 for v in codes.values())
    archive = OUT / ('products.tar.gz' if passed else 'failed-partial-products.tar.gz')
    product_rows = archive_tree(archive, export)
    product_values = payload(archive.read_bytes())
    save('product-manifest.json', {'schema': 1, 'products': product_rows, 'archive': binding(archive),
                                  'productTreeSHA256': sha(canonical(product_rows)), 'sourceTreeSHA256': sha(canonical(source_rows)),
                                  'appProductsFresh': all(codes.get(k) == 0 for k in ['app','mixer-ui','mixer-core']),
                                  'runnerProductsFresh': codes.get('runner') == 0, 'oldAppProductFilesCopied': 0,
                                  'appProductFiles': sum(n.startswith(app.name + '/') for n in product_rows),
                                  'runnerProductFiles': sum(n.startswith('runner-products/') for n in product_rows),
                                  'target': 'arm64-apple-ios26.0-simulator', 'destination': 'generic/platform=iOS Simulator', 'nativeExecuted': False})
    inspection = product_inspection(product_values)
    compiled = ['MixerToggleDiagnostics.app/Frameworks/libMixerCore.dylib', 'MixerToggleDiagnostics.app/Frameworks/libMixerUI.dylib',
                'MixerToggleDiagnostics.app/MixerToggleDiagnostics',
                'runner-products/Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests']
    for n in compiled:
        if passed:
            m = inspection['machO'][n]
            assert m['cpuType'] == 0x100000c
            assert m['buildVersions'] == [{'platform': 7, 'minimumOS': '26.0.0', 'sdk': '26.5.0', 'toolCount': 1}], n
    inspection['freshCompiledLinkedTargets'] = compiled
    inspection['appleRunnerLauncherAndFrameworksArePlatformProvided'] = True
    save('product-inspection.json', inspection)
    assert verify_inputs() == inputs
    save('input-bindings-after.json', inputs)
    assert rows(payload((OUT / 'sources.tar.gz').read_bytes())) == source_rows
    assert rows(payload(archive.read_bytes())) == product_rows
    cleanup()
    save('receipt.json', {'schema': 1, 'observedUTC': utc(), 'status': 'compiled-linked-fresh-app-and-runner-build-only' if passed else 'build-failed-preserved',
                         'passed': passed, 'sourceRevisionReportedByRoot': REVISION, 'gitQueried': False, 'exitCodes': codes,
                         'sourceFiles': 42, 'overallSwiftFiles': 37, 'prototypeSwiftFiles': 12, 'harnessSwiftFiles': 4, 'sourceTreeSHA256': sha(canonical(source_rows)), 'selectedSourceTreeSHA256': sha(canonical(rows(source))),
                         'productFiles': len(product_rows), 'productTreeSHA256': sha(canonical(product_rows)),
                         'sourceArchive': binding(OUT / 'sources.tar.gz'), 'productArchive': binding(archive),
                         'appProductFilesFresh': sum(n.startswith(app.name + '/') for n in product_rows),
                         'runnerProductFilesFresh': sum(n.startswith('runner-products/') for n in product_rows),
                         'oldAppProductFilesCopied': 0, 'recipeOnlyChangesScratchPrefixFromVerifiedGenericBuild': True,
                         'allWarningMessageMultisetsMatchFullOriginalQualification': all(r['sameMessageMultisets'] for r in warning_result.values()),
                         'warningLineOccurrences': sum(len(v) for r in warning_result.values() for v in r['current'].values()),
                         'allCommandsZeroExitEOFNoSignalsNoTimeoutGroupsAbsent': all(c['exitCode'] == 0 and c['stdoutEOF'] and c['stderrEOF'] and not c['signalsSent'] and not c['timedOut'] and c['processGroupAbsent'] for c in COMMANDS),
                         'inputsAndToolsUnchangedAfterBuild': True, 'ownedScratchRemoved': not SCRATCH.exists(),
                         'runtimeSelected': False, 'nativeExecuted': False, 'nativeAccepted': False, 'futureRuntimeIngestionAccepted': False,
                         'originalOraclePassed': False, 'gaAccepted': False, 'simulatorOrDeviceCommands': 0, 'uiOrCapture': False,
                         'listenersOrExplicitNetwork': False, 'physicalPhones': 'disconnected-deferred', 'liveSourceEdits': False, 'copiedObserverCorrection': True,
                         'limitations': ['Generic simulator build only; no runtime packet selected or assembled.',
                                         'Generic compilation does not authorize future original ingestion or a native attempt.',
                                         'Historical V8 Settings Passed and first Tab Failed remain unchanged; fresh native behavior is untested.',
                                         'Physical-phone, full UI, FieldLog published-consumer, signing, store, operational and GA qualification remain pending.']})
    print(json.dumps({'passed': passed, 'exitCodes': codes, 'productFiles': len(product_rows), 'ownedScratchRemoved': not SCRATCH.exists()}), flush=True)
    return 0 if passed else 1

if __name__ == '__main__':
    try: sys.exit(main())
    except Exception:
        if OUT.exists():
            (OUT / 'failure.txt').write_text(traceback.format_exc())
            if SCRATCH.exists():
                try: cleanup()
                except Exception: (OUT / 'cleanup-failure.txt').write_text(traceback.format_exc())
        raise
