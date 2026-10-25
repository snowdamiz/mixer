#!/usr/bin/env python3
"""Record the already accepted source/build inputs and unselected run proposal."""
import pathlib
import sys
import adapter as a


def main():
    b = a.build_helper()
    b.require(not (a.BASE/'packet-seal.json').exists(), 'Adapter already sealed')
    source = b.revalidate()
    b.require(source == b.read(a.BUILD/'source-before.json'), 'Accepted source changed')
    b.save(a.BASE/'accepted-inputs-before.json', source)
    files = [a.BUILD_ACCEPTANCE, a.BUILD/'packet-seal.json', a.BUILD/'supplement/build-products-manifest.json',
             a.ARCHIVE, a.BUILD/'supplement/tools-verified.json', a.PREP/'runtime-selection.json',
             a.PREP/'private-contract.json', a.PREP/'run-proposal.json',
             a.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/source-lock.json',
             a.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/built-app-manifest.json',
             a.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/built-app.tar.gz',
             a.ROOT/'verification/apple-toggle-native-failure-analysis/sdk26-comparator/built-app-manifest.json',
             a.ROOT/'verification/apple-toggle-native-failure-analysis/sdk26-comparator/built-app.tar.gz']
    selected = {str(path.relative_to(a.ROOT)):b.file_record(path) for path in files}
    b.save(a.BASE/'selected-inputs.json', dict(schema=1, files=selected,
           sourceSealSHA256=b.PINS['producer'], reviewSealSHA256=b.PINS['review'],
           buildSealSHA256=a.BUILD_SEAL, buildAcceptanceSHA256=a.BUILD_ACCEPTANCE_HASH,
           V9AppSourceClosureSHA256='f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46',
           runnerSourceTreeSHA256='946ab559edadd5352912d5747629256a6287d9ca892d5aad0fbd0a7ce4d81e2c'))
    b.save(a.BASE/'adapter-runtime-selection.json', dict(schema=1,
           files={'adapter.py':a.sha(a.BASE/'adapter.py')},
           selectedClosedRuntime=str(a.PREP.relative_to(a.ROOT)), runtimeSelectionSHA256=a.RUNTIME_SELECTION_HASH,
           acceptedBuildHelper=str((a.BUILD/'build_runner.py').relative_to(a.ROOT)),
           acceptedBuildSealSHA256=a.BUILD_SEAL,
           nativeExecutionSelected=False))
    contract = b.read(a.PREP/'private-contract.json')
    b.save(a.BASE/'private-contract.json', dict(schema=1, sourceOnly=True,
           replacement='Only historical h.verify and runner archive binding; accepted V3 composition and orchestration source unchanged',
           preflightFailure='First BaseException object latched in each prepared harness; no native command or runtime output after preflight failure',
           methods=a.METHODS, unchangedBudgets=contract['unchangedBudgets'],
           unchangedCleanup='All five independently attempted resources and positive workspace absence proof, including incomplete-allocation narrow cleanup',
           unchangedStrictEvidence=contract['requiredQualificationEvidence'],
           runtimeImports='Exact accepted closed 22-source/three-case-data V3 selection; accepted composition guard unchanged',
           fixedRuntimePath=str(a.PREP/'runtime'), postBuildAdapterOnly=True, nativeExecutionSelected=False,
           applicationCasesExecuted=0, physicalPhones='disconnected-deferred', nativeAcceptancePending=True, carrierAccepted=False, gaAccepted=False))
    b.save(a.BASE/'run-proposal.json', dict(schema=1, status='proposed-not-selected', executed=False,
           prerequisites=['Exact sealed adapter independent review', 'Exact root adapter acceptance', 'Separate explicit root execution selection binding adapter seal and accepted build seal',
                          'Fresh absent fixed V3 runtime path', 'Installed exact iOS26.5(23F77) runtime and iPhone17Pro type verified only after native selection'],
           proposedPrivateInvocation='adapter.compose().run(exact_root_reviewed_adapter_packet_seal_sha256, "interaction")',
           CLI='Verification only; no native run action is exposed',
           runtimePath=str(a.PREP/'runtime'), deviceType='com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro',
           runtime='com.apple.CoreSimulator.SimRuntime.iOS-26-5', runtimeBuild='23F77', maximumOwnedInstances=1,
           frontend='Preserve observed baseline frontend identities; do not launch or signal frontend',
           testCommand='Existing V3 test-without-building sequence only; seven exact -only-testing methods; concurrency one; 600-second outer timeout; 30/45-second default/maximum method allowance',
           methods=a.METHODS, selectedAppArchives={key:value for key,value in [('diagnostic','b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393'),('comparator','1c55dab124608b019ab4a1b6e0a9a2355e5f72287602b890a0a3f78aa6b30fa9')]},
           productTreeSHA256=a.RUNNER_TREE, runnerArchiveSHA256=a.RUNNER_ARCHIVE,
           compilerRetryPermitted=False, applicationRebuildPermitted=False,
           strictPass='Seven exact official passed methods plus actual setup-enabled JSON attachment, six strict completed native keyboard cursors, xcodebuild0, no bridge/session/reporting failures and all five cleanup passes',
           cleanup='Always attempt owned server shutdown/close, thread join, capability workspace removal, and owned-simulator deletion/baseline reconciliation; preserve uncertain or foreign entries',
           physicalPhones='disconnected-deferred', nativeAccepted=False, carrierAccepted=False, gaAccepted=False))
    b.save(a.BASE/'provenance.json', dict(schema=1, observedUTC=b.utc(),
           argv=[sys.executable,'-B',str(pathlib.Path(__file__).resolve())], cwd=str(a.ROOT),
           pythonVersion=sys.version, pythonExecutable=str(pathlib.Path(sys.executable).resolve()),
           pythonBinarySHA256=b.sha(pathlib.Path(sys.executable).resolve()),
           sourceRevision=b.read(a.BUILD_ACCEPTANCE)['sourceRevision'], revisionObservation='Root acceptance metadata; no Git query',
           acceptedProducerFiles=len(source['producer']), acceptedReviewFiles=len(source['review']), inputBindings=len(source['inputBindings']),
           sourceSnapshotSHA256=b.sha(a.BASE/'accepted-inputs-before.json'), runtimeSelectedSources=22, runtimeCaseTables=3,
           compilerInvoked=False, nativeInstancesQueried=False, nativeRun=False, computerUse=False,
           physicalPhones='disconnected-deferred', nativeAcceptancePending=True, gaAccepted=False))
    print('accepted source/build inputs recorded; native run proposal remains unselected')


if __name__ == '__main__':
    main()
