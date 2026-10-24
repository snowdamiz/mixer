#!/usr/bin/env python3
"""Join immutable final-source results, with explicit execution and reuse origins.

This writes evidence only. It never builds or executes product code, changes a
historical receipt, or promotes an older candidate into final qualification.
"""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
MAIN = HERE / 'results/20261024T050444826239Z/receipt.json'
META = HERE / 'metadata/20261024T050606606361Z/receipt.json'
FREEZE = HERE / 'source-freeze/20261024T045840237261Z'
FINAL_TREE = '4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
BASE_TREE = '4df46815f8a9b30db00dda35ed97603da229ac3be957d3f27df38ed2ac56a7c9'


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def read(path):
    return json.loads(path.read_text())


def reference(path):
    return dict(path=str(path.relative_to(HERE)), sha256=sha(path))


def origin(receipt_path, command_name):
    chain = []
    while True:
        receipt = read(receipt_path)
        command = next(item for item in receipt['commands'] if item['name'] == command_name)
        for stream in ['stdout', 'stderr']:
            assert sha(receipt_path.parent / command[stream]) == command[stream + 'SHA256']
        chain.append(dict(receipt=reference(receipt_path), command=command_name,
                          sourceTreeSHA256=command['sourceTreeSHA256']))
        if not command.get('reusedFromReceipt'):
            return command, chain
        previous = Path(command['reusedFromReceipt'])
        previous.relative_to(HERE)
        old = next(item for item in read(previous)['commands'] if item['name'] == command_name)
        # Paths may point at copied artifacts, but actual invocations and all
        # recorded outputs must be those of the original execution.
        for key in ['argv', 'startedUTC', 'completedUTC', 'exitCode',
                    'sourceTreeSHA256', 'stdoutSHA256', 'stderrSHA256']:
            assert command[key] == old[key], (command_name, key)
        receipt_path = previous


def main():
    receipt, metadata, freeze = read(MAIN), read(META), read(FREEZE / 'freeze.json')
    assert receipt['status'].startswith('passed-') and metadata['status'].startswith('passed-')
    assert freeze['sourceTreeSHA256'] == FINAL_TREE
    assert receipt['sourceFreeze'] == metadata['sourceFreeze'] == freeze
    commands = []
    for item in receipt['commands']:
        executed, chain = origin(MAIN, item['name'])
        assert executed['sourceTreeSHA256'] == item['sourceTreeSHA256']
        variant = item['name'].split('-')[0]
        if variant in ['baseline', 'candidate']:
            assert item['sourceTreeSHA256'] == (BASE_TREE if variant == 'baseline' else FINAL_TREE)
        commands.append(dict(name=item['name'], reused=len(chain) > 1,
                             sourceTreeSHA256=item['sourceTreeSHA256'],
                             executionOrigin=chain[-1], importChain=chain,
                             startedUTC=executed.get('startedUTC'),
                             completedUTC=executed.get('completedUTC'),
                             exitCode=executed['exitCode'],
                             stdout=reference(MAIN.parent / item['stdout']),
                             stderr=reference(MAIN.parent / item['stderr'])))
    by_name = {item['name']: item for item in commands}
    artifact_index = read(MAIN.parent / 'qualifying-artifacts.json')
    artifacts = []
    for item in receipt['binaries']:
        variant = item['label'].split('-')[0]
        tree = BASE_TREE if variant == 'baseline' else FINAL_TREE
        member = next(row for row in artifact_index['members']
                      if row['label'] == item['label'] and row['sha256'] == item['sha256'])
        assert member['sourceTreeSHA256'] == tree
        related = [item['label'] + '-build', item['listCommand'], item['runCommand']]
        assert all(by_name[name]['sourceTreeSHA256'] == tree for name in related)
        artifacts.append(dict(label=item['label'], target=item['target'],
                              sha256=item['sha256'], archiveMember=member['member'],
                              sourceTreeSHA256=tree, buildCommand=related[0],
                              listCommand=related[1], runCommand=related[2],
                              executionOrigin=by_name[related[2]]['executionOrigin']))
    configurations = []
    observations = []
    for comparison in receipt['comparisons']:
        for variant, tree in [('baseline', BASE_TREE), ('candidate', FINAL_TREE)]:
            label = variant + '-' + comparison['config'] + '-' + comparison['profile']
            selected = [item for item in artifacts if item['label'] == label]
            assert selected
            if variant == 'candidate':
                # Every final candidate run was actually executed on the final
                # hook/accounting tree in this one earlier collector attempt.
                assert all(item['executionOrigin']['receipt']['path'] ==
                           'results/20261024T050048420640Z/receipt.json' for item in selected)
            counts = comparison[variant + 'Counts']
            configurations.append(dict(label=label, sourceTreeSHA256=tree,
                                       actualExecutionReceipts=sorted(set(
                                           item['executionOrigin']['receipt']['path'] for item in selected)),
                                       targets=[item['target'] for item in selected],
                                       passed=sum(item['passed'] for item in counts),
                                       ignored=sum(item['ignored'] for item in counts),
                                       counts=counts))
        command = next(item for item in receipt['commands'] if item['name'] ==
                       'candidate-' + comparison['config'] + '-' + comparison['profile'] + '-mixer_vm-run')
        for line in (MAIN.parent / command['stdout']).read_text().splitlines():
            for prefix in ['AF01_DEFAULT ', 'AF22_NARROW ', 'AF_LAYOUT ', 'AF21 cold decode ']:
                if prefix in line:
                    observations.append(dict(config=comparison['config'], profile=comparison['profile'],
                                             command=command['name'], text=line[line.index(prefix):]))
    layouts = []
    for item in metadata['layouts']:
        bounds = next(line for line in item['records'] if line.startswith('AF_BOUNDS|'))
        names = ['frozenPermanent', 'frozenActive', 'permanent', 'active', 'frame',
                 'originalValue', 'executionHeader', 'construction', 'state']
        layouts.append(dict(label=item['label'], fieldCount=item['fieldCount'],
                            bytes=dict(zip(names, map(int, bounds.split('|')[1:])))))
    supplement = read(HERE / 'implementation-inventory-schema.json')
    outcome = dict(
        schema=1, observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='producer-and-independent-review-complete-root-acceptance-pending-at-user-pause',
        finalSource=dict(freeze=reference(FREEZE / 'freeze.json'),
                         manifest=reference(FREEZE / 'candidate-manifest.json'),
                         archive=reference(FREEZE / 'candidate-source.tar.gz'),
                         sourceTreeSHA256=FINAL_TREE, sourceFiles=freeze['sourceFiles']),
        baselineSource=dict(sourceTreeSHA256=BASE_TREE,
                            manifest=reference(MAIN.parent / 'baseline-manifest.json'),
                            archive=reference(MAIN.parent / 'baseline-source.tar.gz')),
        hostReceipt=reference(MAIN), metadataReceipt=reference(META),
        artifactIndex=reference(MAIN.parent / 'qualifying-artifacts.json'),
        artifactArchive=reference(MAIN.parent / 'qualifying-artifacts.tar.gz'),
        metadataArtifactIndex=reference(META.parent / 'qualifying-artifacts.json'),
        metadataArtifactArchive=reference(META.parent / 'qualifying-artifacts.tar.gz'),
        implementationDocument=reference(HERE / 'inputs/implementation.md'),
        caseResults=reference(HERE / 'matrix-results.json'),
        retainedAttempts=reference(HERE / 'attempts.json'),
        processCleanup=reference(HERE / 'process-cleanup/receipt.json'),
        independentReview=dict(decision=reference(HERE / 'inputs/independent-decision.json'),
                               seal=reference(HERE / 'inputs/independent-review-seal.json'),
                               source='verification/swift-active-frames-implementation-review/',
                               remainingBlockingFindings=[], rootAcceptance=False),
        reuse=dict(meaning='Copied exact recorded executions; no command is claimed newly run by importing it.',
                   newlyExecutedCommands=sum(not item['reused'] for item in commands),
                   importedCommands=sum(item['reused'] for item in commands),
                   candidateOrigin='results/20261024T050048420640Z/receipt.json',
                   baselineOrigin='results/20261024T045149763486Z/receipt.json',
                   historicalCandidateExcluded='f10e1fef4a86baf8a0406e925622d7ac48a36aca276f3baa4a6e858d806b257b'),
        commands=commands, runtimeConfigurations=configurations, runtimeArtifacts=artifacts,
        comparisons=receipt['comparisons'], defaultBudgetAndAllocationObservations=observations,
        accounting=dict(frozenFields=1061, supplementalFields=len(supplement),
                        supplementalConfigs=dict(collections.Counter(item['config'] for item in supplement)),
                        layouts=layouts, typedMIR=metadata['typedMIR'],
                        constructionProvenanceSupplement='New cleanup-independent actual construction-ticket validation; positive permanent source and typed positions; frozen contract packet unchanged.'),
        beforeAfterBytes=dict(
            historicalValueOnly=dict(productionHeader=289536, unitHeader=290496,
                                     productionConstruction=1062312, unitConstruction=1065072,
                                     source='verification/swift-executor-operations/results/20261024T013344529137Z/verified-summary.json'),
            propagatedStateOwnerHeaderDelta=2352, propagatedConstructionDelta=6832,
            productionHeaderDelta=1089000, unitHeaderDelta=1948008,
            frozenDeclaredFrameEnvelope=360352,
            productionFrameEnvelopeDelta=689096, unitFrameEnvelopeDelta=1264520,
            originalValueEnvelopeUnchanged=119576,
            publicDefaultStateCeilingUnchanged=134217728,
            publicDefaultCombinedCeilingUnchanged=268435456),
        scope=dict(computerUse=False, nativeRuntime=False, physical=False, publicInvoke=False,
                   dispatcher=False, initializeReady=False, publishedFieldLog=False, gaGatePassed=False),
    )
    (HERE / 'final-receipt.json').write_bytes(encoded(outcome))
    print('final-receipt.json', sha(HERE / 'final-receipt.json'))


if __name__ == '__main__':
    main()
