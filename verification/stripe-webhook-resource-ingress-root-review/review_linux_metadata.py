"""Review retained metadata attempts and select one offline dependency retry."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/stripe-resource-linux-compiler-metadata'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


seal = PACKET / 'seal.json'
assert sha(seal) == '7e3f66f09d7b7515f941dbb2a8f98301b1f7504761b82c1083e64ac535653745'
files = json.loads(seal.read_text())['files']
for name, digest in files.items():
    assert (ROOT / name).is_file() and not (ROOT / name).is_symlink()
    assert sha(ROOT / name) == digest, name
prior = json.loads((OUT / 'linux-compiler-metadata-selection.json').read_text())
for phase in ['C1', 'C2']:
    receipt = json.loads((PACKET / phase / 'receipt.json').read_text())
    commands = {row['label']: row for row in receipt['commands']}
    for command in commands.values():
        for output in command['outputs'].values():
            path = ROOT / output['path']
            assert sha(path) == output['sha256'] and path.stat().st_size == output['bytes']
    policy = json.loads((ROOT / commands['policy-before']['outputs']['stdout']['path']).read_text())[0]
    host, config = policy['HostConfig'], policy['Config']
    assert config['Image'] == prior['nativeProbePolicy']['image']
    assert policy['Image'] == config['Image'].split('@')[1]
    assert policy['ImageManifestDescriptor']['digest'] == prior['nativeProbePolicy']['childDigest']
    assert policy['ImageManifestDescriptor']['platform'] == {'os': 'linux', 'architecture': 'arm64'}
    assert config['User'] == '65534:65534' and host['ReadonlyRootfs']
    assert host['NetworkMode'] == 'none' and host['CapDrop'] == ['ALL']
    assert host['SecurityOpt'] == ['no-new-privileges']
    assert (host['PidsLimit'], host['Memory'], host['NanoCpus']) == (128, 1073741824, 2000000000)
    assert host['Ulimits'] == [{'Name': 'core', 'Hard': 0, 'Soft': 0}]
    assert host['Tmpfs'] == {'/tmp': 'rw,noexec,nosuid,nodev,size=134217728,mode=1777'}
    mounts = host['Mounts']
    assert len(mounts) == 1 and mounts[0]['Type'] == 'bind' and mounts[0]['Target'] == '/inputs' and mounts[0]['ReadOnly']
    assert not Path(mounts[0]['Source']).exists()
    assert all(receipt['cleanup'].values()) and commands['cleanup-remove']['exitCode'] == 0
    absent = commands['cleanup-absence']
    assert absent['exitCode'] == 1 and receipt['containerId'] in (ROOT / absent['outputs']['stderr']['path']).read_text()
manifest = json.loads((PACKET / 'metadata-authenticated-manifest.json').read_text())
native_stdout = (PACKET / 'C2/06-probe.stdout').read_text()
for suite, index in manifest['indexes'].items():
    assert sha(ROOT / index['expandedPath']) == index['expandedSha256'] == index['expandedDigest']
    assert (ROOT / index['expandedPath']).stat().st_size == index['expandedBytes']
    assert sha(ROOT / index['releasePath']) == index['nativeVerifiedCleartextSha256']
    assert f"MIXER_SIGNER_VERIFIED={suite}:{index['signerFingerprint']}" in native_stdout
    assert f"MIXER_INDEX_VERIFIED={suite}:{index['indexAlgorithm']}:{index['indexDigest']}:{index['compressedBytes']}" in native_stdout
assert sum(row['expandedBytes'] for row in manifest['indexes'].values()) == 21792217
original = (PACKET / 'verify-c2-authored.sh').read_text()
repaired = (PACKET / 'verify-fixture-repair-proposed.sh').read_text()
assert repaired.replace('chmod 600 "$out/tampered.Packages.xz"\n', '', 1) == original
review = {
    'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'accountableReviewer': '/root', 'sealedFilesVerified': len(files), 'sealSHA256': sha(seal),
    'status': 'partial-metadata-evidence-verified-offline-retry-selected',
    'bothFailedAttemptsAndCleanupVerified': True, 'authenticatedExpandedBytes': 21792217,
    'C1BaseStatusAndKeyringBytesRetained': False, 'C3APTResolutionExecuted': False,
    'repairScope': 'Only chmod of the owned tampered index copy; original failure preserved.',
    'nativeResourceExecutionSelected': False, 'gaAccepted': False,
}
(OUT / 'linux-compiler-metadata-review.json').write_text(json.dumps(review, indent=2) + '\n')
selection = {
    'schema': 1, 'observedUTC': review['observedUTC'], 'accountableReviewer': '/root',
    'status': 'selected-one-additional-offline-metadata-attempt',
    'previousSelectionSHA256': sha(OUT / 'linux-compiler-metadata-selection.json'),
    'rootReviewSHA256': sha(OUT / 'linux-compiler-metadata-review.json'),
    'metadataSealSHA256': sha(seal), 'proposalSHA256': sha(PACKET / 'offline-retry-proposal.json'),
    'ownership': ['verification/stripe-resource-linux-compiler-metadata-v2/**', 'docs/stripe-resource-linux-compiler-metadata-v2.md'],
    'containerAttempts': 1, 'perContainerWallSeconds': 120, 'concurrentContainers': 1,
    'policy': prior['nativeProbePolicy'], 'bounds': prior['bounds'],
    'selectedChanges': [
        'One new immutable attempt with fixed owned tampered-index permissions',
        'Export exact base status/keyring before later controls and require observed C1 hashes',
        'Reverify retained signed metadata offline; export signature status and verified cleartext before later controls',
        'Run corrected negative controls and private no-download no-install-recommends APT simulation against exact captured status and authenticated indexes',
        'Retain solver stdout/stderr on all outcomes; derive exact package lock with full signed index/release provenance and report any base runtime upgrades',
        'All-outcome exact owned container/process/temp cleanup, preserve immutable prior attempts',
    ],
    'hostHTTPSRequests': 0, 'packageTransferSelected': False, 'packageInstallSelected': False,
    'compilerOrHelperOrNifExecutionSelected': False, 'resourceRuntimeSelected': False,
    'notSelected': prior['notSelected'], 'gaAccepted': False,
}
selection['policy']['containerAttempts'] = 1
(OUT / 'linux-compiler-metadata-v2-selection.json').write_text(json.dumps(selection, indent=2) + '\n')
print(json.dumps({'verifiedFiles': len(files), 'selectionSHA256': sha(OUT / 'linux-compiler-metadata-v2-selection.json')}))
