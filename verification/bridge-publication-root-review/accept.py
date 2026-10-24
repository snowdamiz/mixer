from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/bridge-native-exit-ci-repair'
REVIEW = ROOT / 'verification/bridge-publication-independent-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
bindings = {}
local_checks = {}
for directory in [PRODUCER, REVIEW]:
    manifest = read(directory / 'evidence-manifest.json')
    for rel, digest in manifest.items():
        assert sha(directory / rel) == digest, str(directory / rel)
    local_checks[str(directory.relative_to(ROOT))] = len(manifest)
findings = read(REVIEW / 'findings.json')
assert not findings['remainingBlockingFindings']
for rel, digest in findings['reviewedFilesSHA256'].items():
    assert sha(ROOT / rel) == digest, rel
    bindings[rel] = digest
receipt = read(REVIEW / 'candidate-v4/receipt.json')
assert receipt['snapshotUnchanged'] and receipt['rootCandidateFilesUnchanged']
for item in findings['qualification']:
    log = REVIEW / item['log']
    assert sha(log) == item['outputSHA256']
    data = log.read_text()
    assert item['exitCode'] == 0 and item['tests'] == 51
    assert re.search(r'Test run with 51 tests in 1 suite passed', data)
    assert 'WARNING: ThreadSanitizer' not in data
    bindings[str(log.relative_to(ROOT))] = sha(log)
paths = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--',
    str(PRODUCER.relative_to(ROOT)),str(REVIEW.relative_to(ROOT)),str(HERE.relative_to(ROOT))],
    cwd=ROOT,text=True).splitlines()
for rel in paths:
    if rel == str((HERE / 'acceptance.json').relative_to(ROOT)):
        continue
    assert '/.build/' not in rel and not rel.endswith('.a'), rel
    bindings[rel] = sha(ROOT / rel)
out = dict(schema=1,status='accepted-local-bridge-publication-repair-hosted-replay-pending',
           reviewer='root',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           sourceRevision=findings['sourceRevision'],
           changes=['Lock-protected single-take publication of fully started native owner and public session.',
                    'HTTP fixture waits for actual request/native exit before close, rejects gate expiry and explicitly keeps 15 construction permits alive.'],
           testsPerMode=51,modes=['Debug','Release','Swift TSan'],
           scope='Exact final two-file patch, all48 existing bridge tests plus3 independent controlled cancellation/publication/failure schedules. Native archive remains separately source-bound to26943ac.',
           sourceReview='Success publishes after owner.start and takes/clears once. Failure/cancel branches preserve cleanup, single continuation and original constructor tail. Controlled held resumption preserves cancellation-after-finished semantics and proves public deinit with construction retained.',
           retainedLocalManifestChecks=local_checks,
           originalHostedCause='Two publication data race reports and a native-exit observation timeout are retained. Pre-session expiry and optimized held-array lifetime hazards are demonstrated separately; neither is claimed as exact hosted timeout cause.',
           pending=['Pinned hosted Swift6.2.4/Xcode26.3 replay to close the observed CI failure.',
                    'No complete interleaving proof; native Rust/system frameworks are outside Swift TSan.',
                    'No device, native parity, immutable published consumer, signing/store/customer/operational or GA qualification.'],
           bindings=dict(sorted(bindings.items())))
(HERE / 'acceptance.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':out['status'],'bindings':len(bindings),'localManifestChecks':local_checks}))
