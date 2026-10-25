#!/usr/bin/env python3
"""Finalize and seal the source/host adapter packet; no native execution."""
import pathlib
import sys
import adapter as a


def main():
    b = a.build_helper()
    b.require(not (a.BASE/'packet-seal.json').exists(), 'Adapter already sealed')
    result = a.verify(unsealed_host_check=True)
    current = b.revalidate()
    b.require(current == b.read(a.BASE/'accepted-inputs-before.json'), 'Accepted inputs changed during host controls')
    b.save(a.BASE/'accepted-inputs-after.json', current)
    a.records(b, b.read(a.BASE/'selected-inputs.json')['files'])
    b.save(a.BASE/'preseal-preflight.json', result)
    b.require(not any(a.BASE.glob('adapter-host-*')), 'Owned host scratch remains')
    stderr = (a.BASE/'host-controls.stderr').read_text()
    b.require('Ran 13 tests in 6.862s' in stderr and stderr.rstrip().endswith('OK'), 'Final focused host controls incomplete')
    sources = {str(path.relative_to(a.ROOT)):b.sha(path) for path in sorted(a.BASE.glob('*.py'))}
    b.save(a.BASE/'host-controls.json', dict(schema=1, observedUTC=b.utc(), passed=True, methodsPassed=13,
           argv=['/opt/homebrew/opt/python@3.14/bin/python3.14','-B','verification/apple-toggle-keyboard-full-case-v3-adapter/test_adapter.py'],
           cwd=str(a.ROOT), pythonVersion=sys.version, pythonExecutable=str(pathlib.Path(sys.executable).resolve()),
           pythonBinarySHA256=b.sha(pathlib.Path(sys.executable).resolve()),
           environmentObservation='Inherited shell environment; -B; audit rejects subprocess/system/posix_spawn',
           elapsedSecondsFromUnittest=6.862, exitCode=0,
           stdoutSHA256=b.sha(a.BASE/'host-controls.stdout'), stderrSHA256=b.sha(a.BASE/'host-controls.stderr'),
           sourceFiles=sources, sourceTreeSHA256=b.digest(sources), nativeProcessCreated=False,
           acceptedInputsUnchanged=True, syntheticScratchAbsent=True))
    b.save(a.BASE/'attempt-notes.json', dict(schema=1, attempts=2, finalPassed=True,
           firstAttempt='host-attempt-1/receipt.json; 13 methods; one failure and three errors; all raw evidence retained',
           correction='Add accepted packet directory for local helper imports; restrict stale-product mock to product path',
           acceptedInputsMutated=False, nativeExecuted=False))
    b.save(a.BASE/'cleanup.json', dict(schema=1, observedUTC=b.utc(), ownedHostScratchAbsent=True,
           sourceBeforeAfterEqual=True, buildSourceReviewSealsUnchanged=True,
           simulatorInstancesCreated=0, simulatorCleanupRequired=False, otherProjectProcessesOrDataAddressed=False,
           originalCompilerFailureEvidenceUnchanged=True, postBuildNativeRunSelected=False,
           physicalPhones='disconnected-deferred', nativeAcceptancePending=True, carrierAccepted=False, gaAccepted=False))
    files = {str(path.relative_to(a.ROOT)):b.file_record(path) for path in sorted(a.BASE.rglob('*')) if path.is_file() or path.is_symlink()}
    doc = a.ROOT/'docs/apple-toggle-keyboard-full-case-v3-adapter.md'
    files[str(doc.relative_to(a.ROOT))] = b.file_record(doc)
    seal = dict(schema='mixer.apple-toggle.keyboard-full-case-v3-adapter.1', observedUTC=b.utc(), files=files,
           status='source-host-prepared-for-independent-review-native-unselected',
           producerSealSHA256=b.PINS['producer'], independentSourceReviewSealSHA256=b.PINS['review'],
           buildSealSHA256=a.BUILD_SEAL, buildAcceptanceSHA256=a.BUILD_ACCEPTANCE_HASH,
           productTreeSHA256=a.RUNNER_TREE, productArchiveSHA256=a.RUNNER_ARCHIVE,
           runtimeSelectionSHA256=a.RUNTIME_SELECTION_HASH, runtimeSources=22, runtimeCaseDataFiles=3,
           sourceRevision=b.read(a.BUILD_ACCEPTANCE)['sourceRevision'], sourceRevisionObservation='Root acceptance metadata; no Git query',
           hostMethodsPassed=13, applicationCasesExecuted=0, nativeExecutionSelected=False, nativeInstancesQueried=False,
           compilerInvoked=False, physicalPhones='disconnected-deferred', nativeAcceptancePending=True, carrierAccepted=False, gaAccepted=False)
    b.save(a.BASE/'packet-seal.json', seal)
    print(b.sha(a.BASE/'packet-seal.json'))


if __name__ == '__main__':
    main()
