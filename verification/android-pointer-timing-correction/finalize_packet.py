#!/usr/bin/env python3
"""Freeze complete host evidence; no native or Git dispatch."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import support

def main():
    out = support.HERE / 'finalization'
    if out.exists(): raise ValueError('fresh finalization required')
    out.mkdir()
    support.save(out / 'command.json', {'argv': [sys.executable, '-B', str(Path(__file__).resolve())], 'cwd': str(support.ROOT),
                                       'python': support.bind(Path(sys.executable).resolve()), 'source': support.bind(__file__)})
    # Host-1 predates the loader-isolation fix. Reconstruct each original JSON
    # contract from its retained exact source snapshot, accepting only its known
    # wrapper-embedded SHA. No failed result or original receipt is overwritten.
    snapshots = []
    for name in ('host-1', 'host-2'):
        attempt = support.HERE / name
        receipt = json.loads((attempt / 'receipt.json').read_text())
        used = attempt / 'source-used'
        for filename, binding in receipt['sourceFiles'].items():
            if support.bind(used / filename) != binding: raise ValueError('retained source snapshot differs')
        contract = json.loads((support.HERE / 'runner-contract.json').read_text())
        contract['implementationBindings'] = {p.name: support.sha(p) for p in sorted(used.glob('*.py')) if p.name != 'run.py'}
        data = (json.dumps(contract, indent=2, sort_keys=True) + '\n').encode()
        digest = hashlib.sha256(data).hexdigest()
        expected = re.search(r"CONTRACT_SHA256 = '([0-9a-f]{64})'", (used / 'run.py').read_text()).group(1)
        if digest != expected: raise ValueError('original contract reconstruction differs from retained wrapper SHA')
        (used / 'runner-contract.json').write_bytes(data)
        snapshots.append({'attempt': name, 'contractSHA256': digest, 'method': 'exact reconstruction checked against immutable source-used wrapper embedded SHA'})
        support.save(attempt / 'artifact-seal.json', {str(p.relative_to(attempt)): support.bind(p) for p in sorted(attempt.rglob('*')) if p.is_file() and p != attempt / 'artifact-seal.json'})
        if receipt['scratch']['existsAfter'] or Path(receipt['scratch']['path']).exists(): raise ValueError('attempt scratch remains')
        if any(c['ownedCommandGroupCleanup']['after'] for c in receipt['commands']): raise ValueError('owned command group remains')
    support.save(out / 'attempt-contract-retention.json', snapshots)
    upstream = support.upstream()
    helper = support.load('timing_finalize_groups', support.ROOT / 'verification/android-coordinator-runner-cleanup/owned_process.py')
    commands = []
    for name, script in [('producer-final-replay', support.PRIOR / 'check_packet.py'), ('review-final-replay', support.REVIEW / 'check_review.py')]:
        argv = [sys.executable, '-B', str(script)]
        result = helper.execute(argv, cwd=support.ROOT, timeout=120)
        path = out / (name + '.log'); path.write_bytes(result.stdout)
        commands.append({'argv': argv, 'cwd': str(support.ROOT), 'exitCode': result.returncode, 'output': str(path.relative_to(support.ROOT)),
                         'ownedCommandGroupCleanup': result.groupCleanup, **support.bind(path)})
        if result.returncode or result.groupCleanup['after']: raise ValueError('final predecessor replay failed')
    results = json.loads((support.HERE / 'host-2/test-results.json').read_text())
    if results['status'] != 'passed' or results['executed'] != 55 or len(results['exactFiveControls']) != 5: raise ValueError('host controls not qualified')
    old_packet = json.loads((support.PRIOR / 'packet.json').read_text())
    packet = {'schema': 1, 'status': 'sealed-host-only-F06-F07-correction-root-independent-review-pending',
              'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'nativeRuntime': 'NOT RUN', 'nativeAcceptance': False, 'nativeDispatchAuthorizedByThisPacket': False,
              'nativeCommandsExecuted': 0, 'physicalTargetsQueried': False, 'gaAcceptance': False,
              'sourceRevision': old_packet['sourceRevision'], 'sourceTree': old_packet['sourceTree'],
              'sourceClosureSHA256': support.CLOSURE, 'sourceInputs': 105, 'liveNativeSDKInputsRechecked': 88,
              'repositoryContext': {'revision': json.loads(support.SELECTION.read_text())['sourceRevision'],
                                    'authority': 'immutable root correction selection; no Git command made by this correction'},
              'candidate': 'candidate-5', 'apkSHA256': support.APK, 'builtArchiveSHA256': support.ARCHIVE,
              'retainedSignedAPK': old_packet['retainedSignedAPK'], 'archiveReference': str((support.PRIOR / 'candidate-5/built-artifacts.tar.gz').relative_to(support.ROOT)),
              'archiveCopied': False, 'rebuilds': 0, 'unchangedConcreteRunnerSHA256': support.CONCRETE,
              'runnerWrapperSHA256': support.sha(support.HERE / 'run.py'), 'oracleSHA256': support.sha(support.HERE / 'oracle.py'),
              'runnerContractSHA256': support.sha(support.HERE / 'runner-contract.json'),
              'runtimeOutputPolicy': support.RUNTIME_POLICY, 'runtimeSubtreeExcluded': 'verification/android-pointer-timing-correction/runtime',
              'rootSelectedCorrection': support.bind(support.SELECTION), 'upstream': upstream,
              'hostTestCount': 55, 'priorHostTests': 42, 'newHostTests': 13, 'exactRetainedNegativeControlsRejected': 5,
              'hostAttempts': {'host-1': 'retained harness isolation failure; scratch removed', 'host-2': 'passed; scratch removed'},
              'allOwnedScratchRemoved': True, 'nativeInstancesStarted': 0, 'directNativeCallbackCount': None,
              'nextRootCommand': ['python3', '-B', 'verification/android-pointer-timing-correction/run.py', '--build', 'candidate-5', '--attempt', 'runtime-1', '--execute-native'],
              'limitations': ['root must independently accept corrected oracle/runner/host packet before native dispatch',
                             'finite synthetic host proof is not Android runtime evidence',
                             'physical phones disconnected and deferred; broader native/public/signed OTA/FieldLog/store/customer/operations/GA gates pending']}
    support.save(support.HERE / 'packet.json', packet)
    support.save(support.HERE / 'receipt.json', {'schema': 1, 'status': packet['status'], 'packetSHA256': support.sha(support.HERE / 'packet.json'),
                 'nativeRuntime': 'NOT RUN', 'nativeCommandsExecuted': 0, 'GitCommandsExecuted': 0,
                 'physicalTargetsQueried': False, 'hostTests': results, 'finalReplayCommands': commands,
                 'upstream': upstream, 'toolVersions': 'host-2/*-version.log', 'sourceIdentity': {k: packet[k] for k in ('sourceRevision','sourceTree','sourceClosureSHA256')},
                 'failedAttempt': 'host-1 retained with exact sources/logs and hash-verified reconstructed original contract',
                 'exploratoryReadFailure': {'exitCode': 1, 'scope': 'read-only summary of findings.json incorrectly treated its list as an object; repeated with correct list handling before implementation',
                                            'error': 'TypeError: list indices must be integers or slices, not dict', 'nativeCommands': 0},
                 'cleanup': 'both attempts removed scratch after empty lsof, unchanged device/inode, and no symlinks; every owned command group ended empty'})
    support.save(support.HERE / 'packet-seal.json', {'schema': 1, 'runtimeSubtreeExcluded': packet['runtimeSubtreeExcluded'], 'files': support.files()})
    check = support.load('timing_final_check', support.HERE / 'check_packet.py').check()
    print(json.dumps(check, indent=2, sort_keys=True))

if __name__ == '__main__': main()
