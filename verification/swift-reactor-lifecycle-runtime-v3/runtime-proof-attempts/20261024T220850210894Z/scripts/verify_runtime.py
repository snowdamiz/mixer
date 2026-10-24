#!/usr/bin/env python3
"""Read-only replay of selected runtime observations and retained executables."""
from pathlib import Path
import collections, gzip, json
import collect as c
import run_runtime as runner
import verify_pre_runtime

SELECTION_SHA = '79d043510c877a5b07f8add919799cfb18e0829682c3cc1f213f1544e5d95cb6'

def verify():
    source = verify_pre_runtime.verify()
    selected = c.HERE / 'finite-representation-selection.json'
    assert c.sha(selected.read_bytes()) == SELECTION_SHA
    selection = c.read_json(selected)
    assert selection['candidateClosure'] == source['candidateClosure']
    assert selection['preRuntimeFreezeSHA256'] == c.sha((c.HERE / 'pre-runtime-freeze.json').read_bytes())
    assert selection['preRuntimeSealSHA256'] == c.sha((c.HERE / 'seal.json').read_bytes())
    assert selection['finiteRepresentationAccepted'] is True
    for name, digest in c.read_json(c.HERE / 'runtime-driver-bindings.json').items():
        assert c.sha((c.HERE / name).read_bytes()) == digest
        assert (c.HERE / 'runtime-executed-scripts' / name).read_bytes() == (c.HERE / name).read_bytes()
    plan = c.read_json(c.HERE / 'runtime-plan.json')
    assert plan == runner.plan() and len(plan) == 30
    results = c.read_json(c.HERE / 'runtime-results.json')
    assert [row['id'] for row in results] == [row['id'] for row in plan[:len(results)]]
    inventories = c.read_json(runner.s.ACCOUNTING / 'test-inventories.json')
    baseline_query = c.read_json(runner.s.ACCOUNTING / 'exact-query-swift-debug-production.json')
    baseline = c.read_json(runner.s.ACCOUNTING / baseline_query['attempt'] / 'tools.json')
    node = c.read_json(c.ROOT / 'verification/swift-calls-dispatch-node-oracle-qualification/node-provenance.json')
    totals = collections.Counter()
    observed = []
    for result, item in zip(results, plan):
        folder = c.HERE / 'runtime-attempts' / item['id']
        assert result['sourceClosure'] == source['candidateClosure']
        assert result['rootRepresentationSelectionSHA256'] == SELECTION_SHA
        artifacts = c.read_json(folder / 'artifacts.json')
        artifact_bytes = {}
        for artifact in artifacts:
            raw = gzip.decompress((folder / artifact['path']).read_bytes())
            assert len(raw) == artifact['bytes'] and c.sha(raw) == artifact['sha256']
            artifact_bytes[artifact['sha256']] = raw
        cleanup = c.read_json(folder / 'cleanup.json')
        assert cleanup['removed'] and cleanup['holderCheckEmpty'] and cleanup['nativeInstancesCreated'] == 0
        assert not Path(cleanup['scratch']).exists()
        totals['targetsCleaned'] += 1
        totals['logicalBytesCleaned'] += cleanup['logicalBytesRemoved']
        commands = []
        for name in ['build', 'list', 'execute', 'check']:
            path = folder / (name + '.json')
            if not path.exists():
                continue
            command = c.read_json(path)
            tools = c.read_json(folder / (name + '-tools.json'))
            assert tools['compiler'] == baseline
            assert tools['node'] == {k: node[k] for k in ['actualPath','executableSHA256','version','systemVersion']}
            assert tools['explicitPATH'] == runner.s.EXPLICIT_PATH
            assert command['sourceClosure'] == source['candidateClosure']
            assert command['sourceUnchanged'] and not command['remainingGroup']
            assert command['launched'] and 'exitCode' in command
            assert command['selectionSHA256'] == runner.s.SELECTION_SHA
            assert command['PATH'] == runner.s.EXPLICIT_PATH
            for stream in ['stdout', 'stderr']:
                raw = gzip.decompress((folder / (name + '-' + stream + '.gz')).read_bytes())
                assert c.sha(raw) == command[stream + 'SHA256']
            if name in ['list', 'execute']:
                assert command['executableSHA256'] in artifact_bytes
                assert len(artifact_bytes[command['executableSHA256']]) == command['executableBytes']
                assert Path(command['argv'][0]).is_relative_to(Path(cleanup['scratch']) / 'target')
            commands.append((name, command))
        assert len(commands) == (1 if item['family'] == 'check' else 3)
        if item['family'] == 'check':
            name, command = commands[0]
            assert name == 'check'
            assert command['argv'] == ['cargo','check','--lib','--locked','--offline',*runner.flags(item)]
            assert result['passed'] == (command['exitCode'] == 0)
            totals['cargoCheckRows'] += 1
        else:
            by_name = dict(commands)
            targetflags = ['--lib'] if item['target'] == 'mixer_vm' else ['--test',item['target']]
            assert by_name['build']['argv'] == ['cargo','test',*targetflags,'--no-run','--locked','--offline',*runner.flags(item),'--message-format=json-render-diagnostics']
            artifact = c.read_json(folder / 'cargo-artifact.json')
            assert artifact['target']['name'] == item['target'] and artifact['profile']['test'] and not artifact['fresh']
            executable = artifact['executable']
            prefix = [item['filter']] if item['filter'] else []
            assert by_name['list']['argv'] == [executable,*prefix,'--list']
            assert by_name['execute']['argv'] == [executable,*prefix,'--nocapture','--test-threads=1']
            listed = gzip.decompress((folder / 'list-stdout.gz').read_bytes()).decode()
            names = [line[:-6] for line in listed.splitlines() if line.endswith(': test')]
            assert names == c.read_json(folder / 'exact-tests.json') and len(names) == len(set(names))
            if item['family'] == 'focused':
                assert names == next(x['lifecycleTests'] for x in inventories if x['context'] == item['feature'] + '-' + item['profile'])
                assert len(names) == 23
            executed = gzip.decompress((folder / 'execute-stdout.gz').read_bytes())
            actual = runner.observations(executed, names)
            assert actual == c.read_json(folder / 'observed-identities.json')
            assert result['tests'] == len(names)
            assert result['identitiesPassed'] == sum(x['status'] == 'passed' for x in actual)
            all_passed = by_name['execute']['exitCode'] == 0 and all(x['status'] == 'passed' for x in actual) and f'{len(names)} passed; 0 failed; 0 ignored;' in executed.decode(errors='replace')
            assert result['passed'] == all_passed
            assert result['executableSHA256'] == by_name['execute']['executableSHA256']
            if item['target'] == 'span_execution_oracle':
                qualified = c.read_json(folder / 'qualified-node-check.json')
                assert qualified['fullLoaderAndCacheFileSetMatched'] and qualified['injectionEnvironmentEmpty']
                assert qualified['provenanceSHA256'] == c.sha((c.ROOT / 'verification/swift-calls-dispatch-node-oracle-qualification/node-provenance.json').read_bytes())
                assert qualified['nodeSHA256'] == node['executableSHA256'] and qualified['systemCacheBytes'] == node['systemCacheBytes']
                totals['qualifiedNodeOracleRows'] += 1
            totals['testRows'] += 1
            totals['testIdentityExecutions'] += len(names)
            totals['passedIdentityExecutions'] += sum(x['status'] == 'passed' for x in actual)
            totals[item['family'] + 'TestRows'] += 1
        if not result['passed']:
            assert result is results[-1], 'matrix continued after failure'
        observed.append({'id': item['id'], 'family': item['family'], 'feature': item['feature'], 'profile': item['profile'], 'passed': result['passed'], 'tests': result.get('tests'), 'identitiesPassed': result.get('identitiesPassed'), 'exitCode': result.get('exitCode'), 'cleanupComplete': True})
    complete = len(results) == len(plan) and all(x['passed'] for x in results)
    if complete:
        terminal = c.read_json(c.HERE / 'runtime-complete.json')
        assert terminal['commands'] == 30 and terminal['focusedContexts'] == 4 and terminal['exactLifecycleTestsPerContext'] == 23
    if (c.HERE / 'runtime-final-seal.json').exists():
        seal = c.read_json(c.HERE / 'runtime-final-seal.json')
        for name, digest in seal['files'].items():
            assert c.sha((c.HERE / name).read_bytes()) == digest, name
        assert c.sha(c.enc(seal['files'])) == seal['closureSHA256']
    return {'schema': 'mixer.swift-lifecycle.runtime-v3-read-only-replay.1', 'verified': True, 'candidateClosure': source['candidateClosure'], 'rootRuntimeSelectionSHA256': SELECTION_SHA, 'selectedMatrixComplete': complete, 'completedRows': len(results), 'plannedRows': len(plan), 'allObservedRowsPassed': all(x['passed'] for x in results), 'totals': dict(totals), 'observedRows': observed, 'fullPlannedSLRowsComplete': False, 'runtimeOrCompilerRerun': False}

if __name__ == '__main__':
    print(c.enc(verify()).decode())
