#!/usr/bin/env python3
"""Read-only sealed independent review audit. No subprocess, network or writes."""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda data: hashlib.sha256(data).hexdigest()
stable = lambda value: (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
binding = lambda path: {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
checks = []

def check(name, value):
    assert value, name
    checks.append(name)

def read(name):
    return json.loads((HERE / name).read_bytes())

sealed = read('handoff.json')
check('handoff digest', (HERE / 'handoff.sha256').read_text().strip() == sha((HERE / 'handoff.json').read_bytes()))
for name, expected in sealed['members'].items():
    check('sealed member ' + name, binding(ROOT / name) == expected)
actual = {str(path.relative_to(ROOT)) for path in HERE.rglob('*') if path.is_file() and path.name not in ['handoff.json', 'handoff.sha256']} | {'docs/apple-passive-lifecycle-review.md'}
check('exact owned file closure', actual == set(sealed['members']))
for name, expected in read('input-bindings.json').items():
    check('immutable review input ' + name, binding(ROOT / name) == expected)
check('original producer handoff exact', sealed['candidateHandoffSHA256'] == '9e30a9aeef107094d70b17fc83fc632f0278af9d0384a58564cd7b0456efbd75')
producer = json.loads((ROOT / 'verification/apple-passive-lifecycle-observer/handoff.json').read_bytes())
for name, expected in producer['members'].items():
    check('unchanged producer member ' + name, binding(ROOT / name) == expected)
receipt = read('host-receipt.json')
check('finite host acceptance bound', receipt['passed'] and receipt['candidateHandoffSHA256'] == sealed['candidateHandoffSHA256'] and receipt['sourceArchiveSHA256'] == sealed['sourceArchiveSHA256'])
check('83 independent archive controls', receipt['structuralChecks'] == 83 and len(read('structural-checks.json')['checks']) == 83)
check('116 exact producer host controls', receipt['producerHost']['checks'] == 116 and receipt['producerHost']['passed'])
check('371 independent host controls', receipt['independentHost']['checks'] == 371 and receipt['independentHost']['passed'] and receipt['independentHost']['notificationWorkloads'] == 84)
check('exact full field bound reached', receipt['independentHost']['largestEncodedFieldBytes'] == 16_384)
check('46 to 59 independent notification retention', receipt['independentHost']['minimumRetainedNotificationRows'] == 46 and receipt['independentHost']['maximumRetainedNotificationRows'] == 59)
check('exact independent test source', binding(HERE / 'HostReview.swift') == receipt['testedSources']['independent-HostReview.swift'])
check('actual compiled source member bound', receipt['exactCompiledFoundationMember'] == read('source-manifest.json')['members']['accepted/source/Prototype/PassiveLifecycleData.swift'])
check('source member tree digest', receipt['sourceMemberTreeSHA256'] == sha(stable(read('source-manifest.json')['members'])))
commands = read('commands.json')
check('only bounded allowed host commands', [command['name'] for command in commands] == ['python-version', 'producer-read-only-audit', 'swift-version', 'compile-exact-producer-host', 'execute-exact-producer-host', 'compile-independent-host', 'execute-independent-host'])
for command in commands:
    check('terminal success ' + command['name'], command['exitCode'] == 0 and not command['timedOut'] and command['timeoutSeconds'] <= 55)
    for stream in ['stdout', 'stderr']:
        check('output binding ' + command['name'] + ' ' + stream, sha((HERE / (command['name'] + '.' + stream)).read_bytes()) == command[stream + 'SHA256'])
    check('command source binding ' + command['name'], command['sourceArchiveSHA256'] == sealed['sourceArchiveSHA256'])
check('142 producer audit methods', json.loads((HERE / 'producer-read-only-audit.stdout').read_bytes())['checks'] == 142)
check('host execution output summaries bound', json.loads((HERE / 'execute-exact-producer-host.stdout').read_text().splitlines()[-1]) == receipt['producerHost'] and json.loads((HERE / 'execute-independent-host.stdout').read_text().splitlines()[-1]) == receipt['independentHost'])
cleanup = read('cleanup.json')
check('owned scratch and executables removed', receipt['ownedHostScratchRemoved'] and cleanup['ownedHostScratchRemoved'] and not (HERE / '.host-work').exists())
check('reviewer assumption failure retained', not read('history/reviewer-assumption-1/host-receipt.json')['passed'] and 'Foundation options reproduce exact historical original packet bytes' in (HERE / 'history/reviewer-assumption-1/execute-independent-host.stderr').read_text())
check('failed review scratch was also cleaned', read('history/reviewer-assumption-1/host-receipt.json')['ownedHostScratchRemoved'])
check('no UIKit native network or GA claim', not receipt['uikitCompiled'] and receipt['genericSimulatorBuilds'] == receipt['nativeExecutions'] == receipt['nativeQueries'] == receipt['networkCalls'] == 0 and not receipt['gaAccepted'] and receipt['physicalPhones'] == 'disconnected-deferred')
result = json.loads((ROOT / 'verification/apple-focus-system-native-result/result.json').read_bytes())
check('historical V8 verdict preserved', result['officialMethods'] == {'test000PublicSettingsFullKeyboardAccess': 'Passed', 'test010ReferenceFirstTab': 'Failed'} and not result['nativePassed'])
check('review source host scope accepted only', sealed['status'] == 'accepted-source-and-finite-foundation-host-prerequisite' and not sealed['uikitCompiled'] and not sealed['nativeExecution'] and not sealed['gaAccepted'])
print(json.dumps({'passed': True, 'checks': len(checks), 'sourceArchiveSHA256': sealed['sourceArchiveSHA256'], 'candidateHandoffSHA256': sealed['candidateHandoffSHA256'], 'producerHostChecks': 116, 'independentHostChecks': 371, 'uikitCompiled': False, 'nativeExecution': False, 'gaAccepted': False, 'scope': 'Sealed independent source and finite Foundation host prerequisite only'}, sort_keys=True))
