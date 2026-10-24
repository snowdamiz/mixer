#!/usr/bin/env python3
"""Read-only verification of the sealed repair evidence; no guest execution."""
import gzip
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def verify():
    seal = read('seal.json')
    for name, pin in seal['files'].items():
        assert sha((HERE / name).read_bytes()) == pin, ('packet seal', name)
    members = {str(p.relative_to(HERE)) for p in HERE.rglob('*')
               if p.is_file() and p != HERE / 'seal.json'}
    assert members == set(seal['files'])
    for name, pin in seal['externalFiles'].items():
        assert sha((ROOT / name).read_bytes()) == pin, ('external seal', name)
    source = read('source.json')
    baseline = read('baseline-manifest.json')
    candidate = read('candidate-manifest.json')
    assert len(baseline) == len(candidate) == 132
    assert sha(encoded(baseline)) == source['acceptedCandidateClosure'] == \
        '64a3d9c52ade75ec16de10191f14257fb75ff358c366666cf47809e2b9a7f0de'
    assert sha(encoded(candidate)) == source['candidateClosure']
    changed = sorted(name for name in candidate if candidate[name] != baseline[name])
    assert changed == source['changedFiles'] == [
        'src/experimental_swift_reactor/control.rs',
        'src/experimental_swift_reactor/lifecycle_tests.rs']
    for name, pin in candidate.items():
        assert sha((HERE / 'candidate' / name).read_bytes()) == pin
        assert sha((ROOT / 'vm' / name).read_bytes()) == pin, ('live source drift', name)
    control = changed[0]
    helper = (HERE / 'test-only-helper.txt').read_text()
    old = (HERE / 'baseline' / control).read_text()
    new = (HERE / 'candidate' / control).read_text()
    assert sha(old.encode()) == baseline[control]
    assert new.count(helper) == 1 and new.replace(helper, '') == old
    assert new.index('#[cfg(test)]\nimpl RuntimeControl {') < new.index(helper) < \
        new.index('/// The actual proof moves with both adopted tickets.')
    assert (HERE / 'helper-format.rs').read_text() == \
        '#[cfg(test)]\nimpl RuntimeControl {\n' + helper + '}\n'
    for name in changed:
        assert sha((HERE / 'baseline' / name).read_bytes()) == baseline[name]
    log = source['githubFailure']
    assert sha((ROOT / log['rawLog']).read_bytes()) == log['rawLogSHA256']
    configs = read('configuration-results.json')
    identities = read('test-identities.json')
    assert len(identities) == len(set(identities)) == 49
    assert {item['configuration'] for item in configs} == \
        {'swift-debug', 'all-debug', 'swift-release', 'all-release'}
    for config in configs:
        assert sorted(x.rsplit('::', 1)[-1] for x in config['listed']) == identities
        assert config['passed'] == config['listed'] and not config['ignored']
        assert config['defaultTestParallelism']
        archive = (HERE / config['archive']).read_bytes()
        assert sha(archive) == config['archiveSHA256']
        assert sha(gzip.decompress(archive)) == config['executableSHA256']
        for label in config['commands']:
            command = read('commands/' + label + '.json')
            assert command['exitCode'] == 0 and command['candidateClosure'] == source['candidateClosure']
        execute = read('commands/' + config['configuration'] + '-execute.json')
        assert execute['argv'][1:] == ['swift_lifecycle_']
        assert 'RUST_TEST_THREADS' not in execute['environment']
        output = (HERE / 'commands' / (config['configuration'] + '-execute.stdout')).read_text()
        assert sorted(re.findall(r'^test (\S+) \.\.\. ok$', output, re.M)) == config['passed']
        assert 'test result: ok. 49 passed; 0 failed; 0 ignored;' in output
    commands = list((HERE / 'commands').glob('*.json'))
    spent = 0
    for file in commands:
        command = json.loads(file.read_text())
        spent += command['durationSeconds']
        assert command['sourceUnchanged'] and not command['timedOut']
        assert not command['remainingProcessGroup'] and command['timeoutSeconds'] <= 180
        assert command['tools'] == command['postTools']
        assert command['candidateClosure'] == source['candidateClosure']
        for suffix in ['stdout', 'stderr']:
            assert sha(file.with_suffix('.' + suffix).read_bytes()) == command[suffix + 'SHA256']
        assert command['exitCode'] == (1 if file.stem == 'rustfmt-check' else 0)
    assert spent < 900
    assert read('commands/rustfmt-changed-scope-check.json')['exitCode'] == 0
    cleanup = read('cleanup.json')
    assert cleanup['targetAbsent'] and not cleanup['liveHolders']
    assert not (HERE / 'owned-target').exists()
    receipt = read('receipt.json')
    assert receipt['qualifiedIdentityExecutions'] == 196 and receipt['qualifiedFailures'] == 0
    assert receipt['candidateClosure'] == source['candidateClosure']
    assert not receipt['newProductionAccountingCredit'] and not receipt['GAcredit']
    print(json.dumps({'verified': True, 'sourceFiles': 132,
                      'changedSourceFiles': changed, 'qualifiedIdentityExecutions': 196,
                      'productionChecks': 4, 'ownedTargetRemoved': True,
                      'candidateClosure': source['candidateClosure']}, sort_keys=True))


if __name__ == '__main__':
    verify()
