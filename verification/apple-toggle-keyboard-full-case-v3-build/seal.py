#!/usr/bin/env python3
"""Seal the bounded build observation and root-selected supplement."""
import pathlib
import sys
import build_runner as b


def main():
    b.require(not (b.BASE/'packet-seal.json').exists(), 'Build packet already sealed')
    b.require(b.revalidate() == b.read(b.BASE/'source-before.json'), 'Source restoration changed')
    manifest = b.read(b.BASE/'supplement/build-products-manifest.json')
    b.require(b.tree(b.PRODUCTS) == manifest['products'], 'Products changed before seal')
    b.require(b.tool_metadata() == b.read(b.BASE/'supplement/tools-verified.json'), 'Tools changed before seal')
    archive = b.BASE/'supplement/test-runner-products.tar.gz'
    b.require(b.sha(archive) == manifest['productArchiveSHA256'], 'Archive changed before seal')
    b.verify_archive(archive, manifest['products'])
    b.save(b.BASE/'host-controls.json', dict(schema=1, observedUTC=b.utc(),
           argv=['/opt/homebrew/opt/python@3.14/bin/python3.14','-B','verification/apple-toggle-keyboard-full-case-v3-build/test_recorder.py'],
           cwd=str(b.ROOT), environmentObservation='Inherited shell environment; -B prevents Python bytecode writes. Full environment captured separately for the native compiler command.',
           pythonVersion=sys.version, pythonExecutable=str(pathlib.Path(sys.executable).resolve()),
           pythonBinarySHA256=b.sha(pathlib.Path(sys.executable).resolve()), exitCode=0, methodsPassed=12,
           elapsedSecondsFromUnittest=0.850, stdoutSHA256=b.sha(b.BASE/'host-controls.stdout'), stderrSHA256=b.sha(b.BASE/'host-controls.stderr'),
           sourceFiles={name:b.sha(b.BASE/name) for name in ['build_runner.py','test_recorder.py']},
           syntheticScratchAbsent=not any(b.BASE.glob('host-control-*')), nativeProcessStarted=False))
    b.save(b.BASE/'supplement/command.json', dict(schema=1, observedUTC=b.utc(),
           argv=['/opt/homebrew/opt/python@3.14/bin/python3.14','-B','verification/apple-toggle-keyboard-full-case-v3-build/supplement/finalize.py'],
           cwd=str(b.ROOT), pythonVersion=sys.version, pythonExecutable=str(pathlib.Path(sys.executable).resolve()),
           pythonBinarySHA256=b.sha(pathlib.Path(sys.executable).resolve()), sourceSHA256=b.sha(b.BASE/'supplement/finalize.py'),
           environmentObservation='Inherited shell environment; Python -B; no process/native command created by supplement',
           exitCode=0, stdoutSHA256=b.sha(b.BASE/'supplement/finalize.stdout'), stderrSHA256=b.sha(b.BASE/'supplement/finalize.stderr'),
           originalNativeCommandSHA256=b.sha(b.BASE/'command.json'), originalFailedRecorderStderrSHA256=b.sha(b.BASE/'recorder.stderr')))
    files = {str(path.relative_to(b.ROOT)):b.file_record(path) for path in sorted(b.BASE.rglob('*')) if path.is_file() or path.is_symlink()}
    doc = b.ROOT/'docs/apple-toggle-keyboard-full-case-v3-build.md'
    files[str(doc.relative_to(b.ROOT))] = b.file_record(doc)
    b.save(b.BASE/'packet-seal.json', dict(schema='mixer.apple-toggle.keyboard-full-case-v3-build.1', observedUTC=b.utc(),
           files=files, producerSealSHA256=b.PINS['producer'], reviewSealSHA256=b.PINS['review'],
           sourceAcceptanceSHA256=b.PINS['acceptance'], compileSelectionSHA256=b.PINS['selection'],
           sourceRevision=b.read(b.SELECT/'acceptance.json')['sourceRevision'], sourceRevisionObservation='Root acceptance metadata; no Git query',
           status=manifest['status'], compilerAttempts=1, compilerExitCode=0, initialRecorderExitCode=1,
           sourceRestorationAndProductArchiveSupplementVerified=True, productManifestSHA256=b.sha(b.BASE/'supplement/build-products-manifest.json'),
           productTreeSHA256=manifest['productTreeSHA256'], productArchiveSHA256=manifest['productArchiveSHA256'],
           hostMethodsPassed=12, buildAcceptance='Pending independent/root review', postBuildAdapterPrepared=False,
           nativeRuntimeExecuted=False, nativeInstancesQueried=False, applicationCasesExecuted=0,
           physicalPhones='disconnected-deferred', nativeAcceptancePending=True, carrierAccepted=False, gaAccepted=False))
    print(b.sha(b.BASE/'packet-seal.json'))


if __name__ == '__main__':
    main()
