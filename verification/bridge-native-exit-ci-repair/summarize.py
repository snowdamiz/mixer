#!/usr/bin/env python3
"""Seal observed diagnostic facts without changing product or tracker files."""
from pathlib import Path
import datetime, hashlib, json, re, shutil, subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())

original = OUT/'hosted-original'; original.mkdir(exist_ok=True)
for name in ['swift-job.log', 'jobs.json']:
    shutil.copyfile(ROOT/'verification/github-ci-26943ac'/name, original/name)
shutil.copyfile(ROOT/'verification/github-ci-7855754/jobs.json', original/'previous-green-jobs.json')
diff = subprocess.check_output(['git','diff','7855754','26943ac','--','experimental-capability-runtime',
    'sdk/Sources/MixerCapabilities','sdk/Sources/MixerGuest','.github/workflows/verify.yml'],cwd=ROOT)
(original/'relevant-revision-diff.patch').write_bytes(diff)
paths = ['experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Session.swift',
         'experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests/HTTPTests.swift']
patch = subprocess.check_output(['git','diff','26943ac','--',*paths],cwd=ROOT)
(OUT/'candidate.patch').write_bytes(patch)
probe = OUT/'PublicationProbe.swift'
variants = {}
for name in ['baseline','preflight','baseline-full','candidate','candidate-stress','candidate-stress-v2','baseline-stress']:
    manifest_path = OUT/name/'source-manifest.json'
    receipt_path = OUT/name/'receipt.json'
    receipt = read(receipt_path)
    manifest = read(manifest_path)
    source = OUT/name/'source'
    logs = []
    for log in sorted((OUT/name).glob('*-filtered.log')):
        text = log.read_text()
        logs.append({'path':str(log.relative_to(OUT)), 'sha256':sha(log),
            'passedSummaries': re.findall(r'Test run with .+ passed after .+ seconds\.', text),
            'failedSummaries': re.findall(r'Test run with .+ failed after .+ seconds.+', text),
            'tsanWarnings':text.count('WARNING: ThreadSanitizer'),
            'probeLines': [line for line in text.splitlines() if line.startswith(('PREFLIGHT_OBSERVATION','PUBLICATION'))]})
    variants[name] = {'receiptSHA256':sha(receipt_path), 'manifestSHA256':sha(manifest_path),
        'frozenSourceVerified':all(sha(source/relative)==digest for relative,digest in manifest.items()), 'logs':logs,
        'productBindings':{path:manifest[path] for path in paths},
        'scope':'negative deterministic precondition reproduction' if name=='preflight' else
                'discarded incorrect extra probe, retained failure' if name=='candidate-stress' else
                'local host check; not pinned hosted toolchain qualification'}
native = read(OUT/'native-26943ac/receipt.json')
result = {'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'local-repair-qualified-pinned-hosted-replay-pending',
    'baseRevision':'26943ac8a6d17f59cb8a8323609d9e90a0268542',
    'baseTree':'d3ab8e729bca9e1a5eb76ff196ba469c77c9a8d0',
    'productFiles':{path:sha(ROOT/path) for path in paths},
    'candidatePatchSHA256':sha(OUT/'candidate.patch'), 'probeSHA256':sha(probe),
    'hostedLogSHA256':sha(original/'swift-job.log'), 'jobsSHA256':sha(original/'jobs.json'),
    'previousGreenJobsSHA256':sha(original/'previous-green-jobs.json'),
    'relevantSourcesIdenticalAcrossPreviousGreenAndFailure':diff==b'',
    'observed':[
        'Hosted run40037022177 Swift job120698923707 fails only bridge step; VM/services pass',
        'Hosted target records StorageTests.swift11 generic predicate failure after22.179s; actual predicate location/state is absent',
        'Hosted TSan reports Session.swift189 read vs138 init and Ownership.swift132 read vs117 start; process also reports signal6',
        'Deterministic original fixture plus transport clock seam reaches guest completion gate=false active=0 exits=0, then original invalidation predicate fails',
        'Unmodified baseline full48 and both stress probes pass locally under newer Swift6.3.3/Xcode26.6 without TSan diagnostics',
        'Candidate full48 pass Debug Release TSan;64 source/timer/native-drain plus32 GuestUI startup/deinit/retirement iterations pass under TSan',
        'Candidate-stress first generic probe incorrectly required retained exit after already acknowledged policy denial; that failed diagnostic is excluded from qualification'],
    'hypothesesNotProven':[
        '50ms request may expire before URLSession adoption on hosted TSan, matching deterministic reproduction; hosted log does not establish this exact route',
        'Original gate has5s escape and awaited conjunction can also be missed if observation is delayed; hosted state/timing not retained',
        'Two publication race reports are addressed by explicit queue-to-task lock publication; local newer toolchain does not reproduce them, so CI6.2.4 confirmation remains required'],
    'ownershipAssessment':[
        'handoff lock exists before dispatch, receives started owner/session before success resume, and is taken/cleared under same lock after await',
        'success continuation resumes once; cancelled/error branches never put a public session into the slot and retain original owner.stop/permit cleanup',
        'constructorReturned remains in original queued tail after continuation resolution; nil public owner/retirement probes detect retained extra handoff session',
        'HTTP test now awaits URLProtocol start plus real lease/native exit, triggers close/drop, waits actual invalidation, keeps15-held/16th-rejected and final reclamation checks',
        'HTTP test retains original800x5ms polling bound and5s gate escape, and explicitly checks gate did not time out'],
    'nativeReceiptSHA256':sha(OUT/'native-26943ac/receipt.json'), 'nativeLibrary':native['library'],
    'variants':variants,
    'limitations':[
        'Hosted pin Swift6.2.4 Xcode26.3 unavailable locally; local toolchain Swift6.3.3 Xcode26.6',
        'Static native Rust archive and system frameworks not Swift TSan instrumented',
        'No physical devices, cross-platform execution, release/signing/store/customer/GA evidence',
        'No commit/push/tracker edits or production publication by this investigation lane']}
(OUT/'findings.json').write_text(json.dumps(result,indent=2)+'\n')
files = {str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()
    and '.build' not in p.relative_to(OUT).parts and p.name!='evidence-manifest.json'
    and not {'cargo-home','tmp'}.intersection(p.relative_to(OUT).parts)}
(OUT/'evidence-manifest.json').write_text(json.dumps(files,indent=2)+'\n')
print(json.dumps({'status':result['status'],'variants':len(variants),'files':len(files)},indent=2))
