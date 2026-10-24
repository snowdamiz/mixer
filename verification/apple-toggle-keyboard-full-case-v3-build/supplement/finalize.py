#!/usr/bin/env python3
"""Root-selected empty-directory restoration and existing product archival only."""
import json
import os
import pathlib
import plistlib
import stat
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import build_runner as b

HERE = pathlib.Path(__file__).resolve().parent
PREFIX = 'MixerToggleUITests.xcodeproj/project.xcworkspace'
DIRECTORIES = [PREFIX, PREFIX+'/xcshareddata', PREFIX+'/xcshareddata/swiftpm', PREFIX+'/xcshareddata/swiftpm/configuration']


def identity(path):
    info = path.lstat()
    b.require(stat.S_ISDIR(info.st_mode) and not path.is_symlink() and path.resolve() == path, 'Exact real directory required: '+str(path))
    return {'device':info.st_dev, 'inode':info.st_ino, 'mode':stat.S_IMODE(info.st_mode), 'children':sorted(os.listdir(path))}


def main():
    originals = ['build_runner.py','test_recorder.py','attempt-started.json','command.json','compiler.stdout','compiler.stderr',
                 'recorder.stdout','recorder.stderr','source-before.json','source-after.json','tools-before.json','tools-after.json',
                 'host-controls.stdout','host-controls.stderr']
    original_hashes = {name:b.sha(b.BASE/name) for name in originals}
    before = b.read(b.BASE/'source-before.json')
    failed_after = b.read(b.BASE/'source-after.json')
    current = b.revalidate()
    b.require(current == failed_after, 'Stopped-attempt tree changed before supplement')
    expected_changes = {name:{'kind':'directory','mode':0o777} for name in DIRECTORIES}
    b.require({k:v for k,v in failed_after['runner'].items() if k not in before['runner']} == expected_changes, 'Exact four added directories required')
    b.require(all(failed_after['runner'][name] == row for name,row in before['runner'].items()), 'Original runner entry changed')
    b.require(all(before[key] == failed_after[key] for key in before if key != 'runner'), 'Other source group changed')
    tools_before = b.tool_metadata()
    b.require(tools_before == b.read(b.BASE/'tools-before.json') == b.read(b.BASE/'tools-after.json'), 'Tools changed since compiler')
    products_before = b.tree(b.PRODUCTS)
    identities = {name:identity(b.PREP/'harness'/name) for name in DIRECTORIES}
    b.save(HERE/'selection-and-identities.json', dict(schema=1, observedUTC=b.utc(), selectedBy='/root',
           selection='Explicit parent follow-on after independent source-before/source-after comparison',
           allowed='Only four observed Xcode-created empty directories; no-follow identity checks and deepest-first rmdir; no recursion or unlink; no compiler retry',
           originalEvidence=original_hashes, addedDirectories=expected_changes, identities=identities))
    removals = []
    for name in reversed(DIRECTORIES):
        path = b.PREP/'harness'/name
        row = identity(path)
        b.require(all(row[key] == identities[name][key] for key in ['device','inode','mode']), 'Directory identity changed before rmdir')
        b.require(row['children'] == [], 'Directory is not empty; preserve it')
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            b.require(stat.S_ISDIR(info.st_mode) and (info.st_dev,info.st_ino,stat.S_IMODE(info.st_mode)) == (row['device'],row['inode'],row['mode']), 'No-follow directory identity changed')
            os.rmdir(path.name, dir_fd=parent_fd)
            try:
                os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                absence = True
            else:
                absence = False
            b.require(absence, 'Positive directory absence proof required')
            removals.append({'name':name,'identity':row,'operation':'rmdir by parent dir_fd and exact basename','absenceVerified':True})
        finally:
            os.close(parent_fd)
    b.save(HERE/'directory-removals.json', dict(schema=1, observedUTC=b.utc(), removals=removals, recursiveDeletion=False, unlinkPerformed=False))
    restored = b.revalidate()
    b.require(restored == before, 'Full source tree not restored to pre-compile observation')
    b.save(HERE/'source-restored.json', restored)
    archive = HERE/'test-runner-products.tar.gz'
    b.archive_tree(b.PRODUCTS, products_before, archive)
    products_after = b.tree(b.PRODUCTS)
    b.require(products_after == products_before, 'Products changed during supplement')
    tools_after = b.tool_metadata()
    b.require(tools_before == tools_after, 'Tools changed during supplement')
    b.save(HERE/'tools-verified.json', tools_after)
    final_source = b.revalidate()
    b.require(final_source == before, 'Source changed during product archival')
    b.require(original_hashes == {name:b.sha(b.BASE/name) for name in originals}, 'Original evidence changed')
    configurations = [name for name,row in products_after.items() if row['kind']=='file' and name.endswith('.xctestrun')]
    b.require(len(configurations)==1, 'One exact compiled xctestrun required')
    configuration = plistlib.loads((b.PRODUCTS/configurations[0]).read_bytes())
    b.require('MixerToggleUITests' in configuration, 'Runner target absent')
    manifest = dict(schema='mixer.apple-toggle.keyboard-full-case-v3-build-products.1', observedUTC=b.utc(),
          status='compiler succeeded; initial recorder failed on generated empty directories; source restoration and product archival supplement verified',
          compilerExitCode=b.read(b.BASE/'command.json')['exitCode'], compilerAttempts=1, recorderExitCode=1,
          originalEvidence=original_hashes, sourceRevision=b.read(b.SELECT/'acceptance.json')['sourceRevision'],
          sourceRevisionObservation='Root acceptance metadata; no Git query',
          sourceFullTreeRestored=True, sealedInputFileBytesAndModesUnchanged=True, toolFilesStable=True, productFilesStable=True,
          productsPath=str(b.PRODUCTS), products=products_after, productTreeSHA256=b.digest(products_after),
          productArchiveSHA256=b.sha(archive), archiveManifestVerified=True,
          archiveVerification='Every file payload, hash, byte count, mode, directory mode, symlink target and member checked without extraction',
          sourceRestoredSHA256=b.sha(HERE/'source-restored.json'), toolReceiptSHA256=b.sha(HERE/'tools-verified.json'),
          xctestrun=configurations[0], xctestrunConfiguration=configuration,
          genericRunnerCompiled=True, buildAcceptance='Pending independent and root review of this supplement', postBuildAdapterPrepared=False,
          nativeInstancesQueried=False, nativeRuntimeExecuted=False, applicationCasesExecuted=0, nativeAcceptancePending=True,
          physicalPhones='disconnected-deferred', carrierAccepted=False, gaAccepted=False)
    b.save(HERE/'build-products-manifest.json', manifest)
    b.save(HERE/'cleanup.json', dict(schema=1, observedUTC=b.utc(), generatedFourDirectoriesAbsent=True,
          sourceFullTreeRestored=True, syntheticHostScratchAbsent=not any(b.BASE.glob('host-control-*')),
          simulatorInstancesCreated=0, simulatorCleanupRequired=False, otherProjectDataOrProcessesAddressed=False,
          retainedOwnedBuild=str(b.BUILD), retainedOwnedCompilerTemporary=str(b.BASE/'compiler-tmp'),
          retainedReason='Preserve original failed recorder and successful compiler observation for review; no automatic deletion of compiler state',
          archiveByteModeVerified=True, physicalPhones='disconnected-deferred'))
    print(json.dumps({'status':manifest['status'],'productEntries':len(products_after),
          'productFiles':sum(row['kind']=='file' for row in products_after.values()),
          'productTreeSHA256':manifest['productTreeSHA256'],'productArchiveSHA256':manifest['productArchiveSHA256']}))


if __name__ == '__main__':
    main()
