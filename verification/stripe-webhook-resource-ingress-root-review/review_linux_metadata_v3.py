"""Review exact native solver output and signed artifacts before bounded fetch."""
from pathlib import Path, PurePosixPath
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
P = ROOT / 'verification/stripe-resource-linux-compiler-metadata-v3'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P / 'seal.json') == 'a229a85cb950facf79cc1c3c68760100246269ea1100f8c113459bf3418be80b'
sealed = json.loads((P / 'seal.json').read_text())['files']
for name, digest in sealed.items():
    path = ROOT / name
    assert path.is_file() and not path.is_symlink() and sha(path) == digest, name
lock = json.loads((P / 'package-lock.json').read_text())
assert sha(P / 'package-lock.json') == '4db8b41afffdf796acaec18bcc3b5574be593af0c11c4cb860b39da5d64a36b4'
assert lock['basePackageChanges'] == lock['baseRuntimeUpgradeDelta'] == []
assert lock['nativeSummary'] == {'newlyInstalled': 36, 'notUpgraded': 10, 'removed': 0, 'upgraded': 0}
packages = lock['packages']
assert len(packages) == len({x['name'] for x in packages}) == 36
assert sum(x['bytes'] for x in packages) == 50997408
assert sum(x['installedSizeKiB'] * 1024 for x in packages) == 179546112
solver = (ROOT / lock['nativeSolverStdout']['path']).read_text().splitlines()
assert {line for line in solver if line.startswith('Inst ')} == {x['nativeInstRecord'] for x in packages}
assert {line for line in solver if line.startswith('Conf ')} == {x['nativeConfRecord'] for x in packages}
stanza_count = 0
for package in packages:
    assert package['action'] == 'new' and package['baseVersion'] is None
    assert package['architecture'] in ['arm64', 'all']
    filename = package['filename']
    assert filename.startswith('pool/main/') and str(PurePosixPath(filename)) == filename
    assert all(part not in ['', '.', '..'] for part in filename.split('/'))
    assert package['url'] == 'https://ports.ubuntu.com/ubuntu-ports/' + filename
    assert len(package['signedProvenance']) > 0
    for provenance in package['signedProvenance']:
        for field in ['authenticatedExpandedIndex', 'compressedIndex', 'inRelease', 'nativeSignatureStatus', 'nativeVerifiedRelease']:
            artifact = provenance[field]
            path = ROOT / artifact['path']
            assert sha(path) == artifact['sha256'] and path.stat().st_size == artifact['bytes']
        index = (ROOT / provenance['authenticatedExpandedIndex']['path']).read_bytes()
        start, length = provenance['stanzaOffset'], provenance['stanzaBytes']
        raw = index[start:start+length]
        assert hashlib.sha256(raw).hexdigest() == provenance['stanzaSha256']
        fields = dict(line.split(': ', 1) for line in raw.decode().splitlines() if line and not line[0].isspace() and ': ' in line)
        for signed, selected in [('Package','name'),('Version','version'),('Architecture','architecture'),('Filename','filename'),('SHA256','sha256')]:
            assert fields[signed] == package[selected]
        assert int(fields['Size']) == package['bytes'] and int(fields['Installed-Size']) == package['installedSizeKiB']
        status = (ROOT / provenance['nativeSignatureStatus']['path']).read_text().splitlines()
        assert [x.split()[2] for x in status if x.startswith('[GNUPG:] VALIDSIG ')] == ['F6ECB3762474EDA9D21B7022871920D1991BC93C']
        stanza_count += 1
commands = []
for label, script, extra in [('retained-audit','audit_retained.py',[]),('lock-recheck','lock_packages.py',['--check'])]:
    argv = [sys.executable, '-B', str(P / script), *extra]
    run = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    outputs = {}
    for stream in ['stdout','stderr']:
        path = OUT / ('v3-' + label + '.' + stream)
        path.write_bytes(getattr(run, stream))
        outputs[stream] = {'path': str(path.relative_to(ROOT)), 'sha256': sha(path), 'bytes': path.stat().st_size}
    commands.append({'argv': argv, 'exitCode': run.returncode, 'outputs': outputs})
    assert run.returncode == 0, label
review = {'schema': 1, 'accountableReviewer': '/root', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'reviewScriptSHA256': sha(Path(__file__)), 'metadataSealSHA256': sha(P/'seal.json'), 'sealedFilesVerified': len(sealed),
    'exactPackages': 36, 'signedStanzasIndependentlyJoined': stanza_count, 'prospectiveTransferBytes': 50997408,
    'baseRuntimeUpgradeDelta': [], 'commands': commands, 'status': 'exact-metadata-lock-accepted-for-bounded-acquisition',
    'actualPackageExpandedBytesObserved': False, 'compilerExecuted': False, 'LinuxResourceRuntimeAccepted': False, 'gaAccepted': False}
(OUT/'linux-compiler-metadata-v3-review.json').write_text(json.dumps(review,indent=2)+'\n')
proposal = json.loads((ROOT/'verification/stripe-resource-linux-compiler-preparation/proposal.json').read_text())
selection = {'schema': 1, 'accountableReviewer': '/root', 'observedUTC': review['observedUTC'], 'phase': 'C4',
    'status': 'selected-official-locked-deb-acquisition-only', 'rootReviewSHA256': sha(OUT/'linux-compiler-metadata-v3-review.json'),
    'metadataSealSHA256': sha(P/'seal.json'), 'packageLockPath': str((P/'package-lock.json').relative_to(ROOT)), 'packageLockSHA256': sha(P/'package-lock.json'),
    'exactPackageCount': 36, 'exactTransferBytes': 50997408, 'bounds': proposal['proposedBounds'],
    'ownership': ['verification/stripe-resource-linux-compiler-acquisition/**','docs/stripe-resource-linux-compiler-acquisition.md'],
    'selectedActions': ['Acquire only the 36 exact locked official HTTPS URLs, one request at a time, no redirects or retries; verify signed size and SHA256 before use.',
        'Use a new mode0700 owned directory, exclusive regular files and cumulative wall/stream/transfer/storage bounds; retain failed-attempt evidence and remove partial payloads.',
        'Retain full per-request provenance, times, command/tools and source/lock identities; host controls must cover tamper, path, redirect, size, time and cleanup failures.',
        'No package extraction, host/container installation, maintainer scripts, tool image assembly, compiler/helper/NIF/resource execution in C4.',
        'Prepare the finite C5 offline assembly proposal using package metadata and documented existing bounds; do not execute C5.'],
    'packageAcquisitionSelected': True, 'packageInstallationSelected': False, 'compilerExecutionSelected': False,
    'resourceRuntimeSelected': False, 'gaAccepted': False}
destination=OUT/'linux-compiler-acquisition-selection.json'
assert not destination.exists(), 'Acquisition selection already exists'
destination.write_text(json.dumps(selection,indent=2)+'\n')
print(json.dumps({'filesVerified':len(sealed),'stanzas':stanza_count,'selectionSHA256':sha(destination)}))
