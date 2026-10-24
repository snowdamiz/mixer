"""Audit failed offline APT simulation and select its one-option retry."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
P = ROOT / 'verification/stripe-resource-linux-compiler-metadata-v2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P / 'seal.json') == '605e64b6841bbbdfaf9ed0072b80c4bf3a49fad531358d1418ee685bdc856809'
sealed = json.loads((P / 'seal.json').read_text())['files']
for path, digest in sealed.items():
    assert (ROOT / path).is_file() and not (ROOT / path).is_symlink()
    assert sha(ROOT / path) == digest, path
r = json.loads((P / 'attempt/receipt.json').read_text())
commands = {row['label']: row for row in r['commands']}
for row in commands.values():
    for output in row['outputs'].values():
        assert sha(ROOT / output['path']) == output['sha256']
        assert (ROOT / output['path']).stat().st_size == output['bytes']
addendum = json.loads((OUT / 'linux-compiler-metadata-v2-export-addendum.json').read_text())
assert set(r['metadataArtifacts']) == set(addendum['allowedExports'])
for name, artifact in r['metadataArtifacts'].items():
    assert artifact['available'] and sha(ROOT / artifact['path']) == artifact['sha256']
    bound = addendum['allowedExports'][name]
    if 'sha256' in bound:
        assert artifact['sha256'] == bound['sha256'] and artifact['bytes'] == bound['bytes']
    else:
        assert artifact['bytes'] <= bound['maximumBytes']
assert sum(a['bytes'] for a in r['metadataArtifacts'].values()) == 605365
assert all(n <= 524288 for n in r['ordinaryStreamRetainedBytes'].values())
policy = json.loads((ROOT / commands['policy-before']['outputs']['stdout']['path']).read_text())[0]
h, c = policy['HostConfig'], policy['Config']
assert c['Image'] == r['image'] and policy['Image'] == r['image'].split('@')[1]
assert policy['ImageManifestDescriptor']['digest'] == r['requiredPlatformDescriptorDigest']
assert policy['ImageManifestDescriptor']['platform'] == {'os': 'linux', 'architecture': 'arm64'}
assert c['User'] == '65534:65534' and h['ReadonlyRootfs'] and h['NetworkMode'] == 'none'
assert h['CapDrop'] == ['ALL'] and h['SecurityOpt'] == ['no-new-privileges']
assert (h['PidsLimit'], h['Memory'], h['NanoCpus']) == (128, 1073741824, 2000000000)
assert h['Ulimits'] == [{'Name': 'core', 'Hard': 0, 'Soft': 0}]
assert h['Tmpfs'] == {'/tmp': 'rw,noexec,nosuid,nodev,size=134217728,mode=1777'}
assert len(h['Mounts']) == 1 and h['Mounts'][0]['ReadOnly'] and h['Mounts'][0]['Target'] == '/inputs'
assert not Path(h['Mounts'][0]['Source']).exists() and all(r['cleanup'].values())
assert commands['cleanup-remove']['exitCode'] == 0 and commands['cleanup-absence']['exitCode'] == 1
assert r['containerId'] in (ROOT / commands['cleanup-absence']['outputs']['stderr']['path']).read_text()
assert r['phases']['prepare']['exitCode'] == r['phases']['authenticate']['exitCode'] == 0
assert 'MIXER_SOLVER_EXIT=100' in r['phases']['resolve']['markers']
assert 'MIXER_TAMPERED_INDEX_REJECTED=1' in r['phases']['resolve']['markers']
assert 'MIXER_TAMPERED_SIGNATURE_REJECTED=1' in r['phases']['resolve']['markers']
proposal = json.loads((P / 'offline-retry-proposal.json').read_text())
proposed = (ROOT / proposal['proposedSource']['path']).read_text()
original = (P / 'inputs/resolve.sh').read_text()
assert original.replace('--simulate --no-download ', '--simulate ', 1) == proposed
review = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'accountableReviewer': '/root', 'sealSHA256': sha(P / 'seal.json'), 'sealedFilesVerified': len(sealed), 'fixedExportsVerified': 15, 'fixedExportBytes': 605365, 'cleanupVerified': True, 'APTExitCode': 100, 'exactPackageLock': None, 'causalStatus': 'The cached-archive restriction is the proposed cause, supported by APT documentation; exact retry has not executed.', 'status': 'failed-attempt-preserved-and-one-option-retry-selected', 'gaAccepted': False}
(OUT / 'linux-compiler-metadata-v2-review.json').write_text(json.dumps(review, indent=2) + '\n')
selection = json.loads((OUT / 'linux-compiler-metadata-v2-selection.json').read_text())
selection.update(observedUTC=review['observedUTC'], status='selected-one-simulate-only-offline-metadata-attempt', previousSelectionSHA256=sha(OUT / 'linux-compiler-metadata-v2-selection.json'), rootReviewSHA256=sha(OUT / 'linux-compiler-metadata-v2-review.json'), metadataSealSHA256=sha(P / 'seal.json'), proposalSHA256=sha(P / 'offline-retry-proposal.json'), ownership=['verification/stripe-resource-linux-compiler-metadata-v3/**', 'docs/stripe-resource-linux-compiler-metadata-v3.md'])
selection['selectedChanges'] = ['Remove only --no-download from selected APT command; require --simulate, --no-install-recommends, no suggested packages and --no-remove. Never use ignore-missing/fix-missing/unauthenticated.', 'Preserve network-none, readonly, nonroot and all existing native/stream/time/storage limits; one container only.', 'Reuse exact authenticated metadata and base status/keyring hashes; same early and all-outcome evidence exports.', 'Derive exact dependency/version lock only on successful native simulation with full signed index provenance; report any base runtime upgrades.', 'Preserve all previous failures and exact owned cleanup.']
selection['fixedExportAddendumSHA256'] = sha(OUT / 'linux-compiler-metadata-v2-export-addendum.json')
selection['fixedExportAddendumPath'] = str((OUT / 'linux-compiler-metadata-v2-export-addendum.json').relative_to(ROOT))
selection['officialSemanticsSource'] = 'https://manpages.ubuntu.com/manpages/noble/man8/apt-get.8.html'
selection['officialSemanticsObserved'] = 'APT2.8.3 documentation: simulation changes no system state; no-download restricts available archives to already downloaded packages. Exact failure cause remains a hypothesis before retry.'
(OUT / 'linux-compiler-metadata-v3-selection.json').write_text(json.dumps(selection, indent=2) + '\n')
print(json.dumps({'sealedFiles': len(sealed), 'selectionSHA256': sha(OUT / 'linux-compiler-metadata-v3-selection.json')}))
