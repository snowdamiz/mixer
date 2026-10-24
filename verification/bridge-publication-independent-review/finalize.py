#!/usr/bin/env python3
from pathlib import Path
import hashlib, json

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
def sha(raw): return hashlib.sha256(raw).hexdigest()
receipt = json.loads((OUT/'candidate-v4/receipt.json').read_text())
assert receipt['snapshotUnchanged'] and receipt['rootCandidateFilesUnchanged']
assert receipt['fullExistingSuiteAndScheduleProbes']
checks = []
for record in receipt['commands']:
    raw = (OUT/'candidate-v4'/record['output']).read_bytes()
    assert sha(raw) == record['outputSHA256'] and record['exitCode'] == 0
    text = raw.decode()
    assert 'Test run with 51 tests in 1 suite passed' in text
    assert 'WARNING: ThreadSanitizer' not in text
    for marker in ['queuedCancellation completion=1 retirement=1 cleanup=1 tail=true permits=16',
                   'finishedCancellation completion=1 publicDeinit=true retirement=1 cleanup=1 tail=true permits=16',
                   'failedCreation completion=1 error=1 retirement=1 cleanup=1 tail=true permits=16']:
        assert marker in text
    checks.append({'log': 'candidate-v4/'+record['output'], 'exitCode':record['exitCode'],
                   'tests':51,'outputSHA256':record['outputSHA256']})
assert len(checks) == 3
for name, digest in receipt['candidateFilesSHA256'].items(): assert sha((ROOT/name).read_bytes()) == digest
for attempt in ['draft-compile','candidate-v1','candidate-v2','candidate-v3','candidate-v4']:
    source = OUT/attempt/'source/experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests/ScheduleProbe.swift'
    if source.exists(): (OUT/attempt/'ScheduleProbe.swift').write_bytes(source.read_bytes())
findings = {
    'status':'scoped-independent-review-complete',
    'recommendation':'No remaining blocking finding in the two reviewed files; commit the scoped patch and require the pinned hosted Swift 6.2.4 CI replay before treating the hosted failure as closed.',
    'reviewedFilesSHA256':receipt['candidateFilesSHA256'],
    'sourceRevision':receipt['sourceRevision'],'sourceTree':receipt['sourceTree'],
    'remainingBlockingFindings':[],
    'resolvedReviewFinding':{
        'file':'experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests/HTTPTests.swift',
        'issue':'The fifteen reserved constructions were only used through a later removeAll; the capacity proof needs an explicit lifetime through the awaited reclamation.',
        'evidence':'candidate-v1 Release failed the analogous two capacity assertions for its map-built held array; candidate-v3 Release passed after adding only an explicit end-of-scope held-array lifetime pin. Debug and TSan v1 passed. The append-built HTTP fixture itself did not fail locally; neither its early release nor any other array lifetime is claimed. This is an optimized probe lifetime hazard, not evidence of the unknown original hosted timeout route.',
        'repair':'Root approved one line withExtendedLifetime(held) {} after the final gate timeout assertion, before cancellation/removal; final candidate-v4 includes it.'},
    'sourceReview':[
        'The handoff lock is created before construction queue submission. owner.start and public session initialization precede the locked store. The resumed task locks the same slot, takes the session, and clears the slot exactly once.',
        'The success branch has one Void continuation resume after publication. Failed and cancelled outcomes never populate the handoff slot; each has one throwing resume. Constructor-tail observation remains after the outcome switch.',
        'Cancellation after finished does not revoke an accepted session. Earlier cancellation takes the cleanup path. A held task executor tests cancellation after constructor completion/publication and before the handoff take without product instrumentation.',
        'The HTTP fixture observes actual URLProtocol start, an active transport lease and a retained native exit before close/drop. Its five-second invalidation gate and existing polling bounds are unchanged; a 30-second HTTP operation budget establishes pending work rather than the test trigger. Gate expiry is explicitly rejected.',
        'The final lifetime pin keeps the fifteen reserved constructions alive through the capacity rejection and awaited reclamation. It does not change any public runtime behavior.'
    ],
    'controlledSchedules':[
        'Queued cancellation before real constructor execution: no premature cleanup/retirement; one CancellationError result, constructor tail, cleanup and retirement; construction consumed thereafter; all sixteen permits reusable.',
        'Cancellation after real constructor tail/publication while resumed task is held: returned session remains open and executes actual startup; result slot cleared; public weak reference becomes nil with construction kept alive; one cleanup/tail/retirement; all sixteen permits reusable.',
        'Real malformed-module construction failure: one typed construction error and terminal observation, no public session, one cleanup/tail/retirement, no repeat create or repeated cancel effects; all sixteen permits reusable.'
    ],
    'qualification':checks,
    'excludedDiagnostics':{
        'draft-compile':'Probe-only consuming-parameter capture failed compilation in all modes; no test execution/qualification.',
        'candidate-v1':'Debug/TSan four selected tests passed; Release two capacity assertions failed before the explicit held-array lifetime pin. Preserved, excluded from final qualification.',
        'candidate-v2':'Probe-only inferred #expect return value triggered unused-result warnings-as-errors; no test execution/qualification.',
        'candidate-v3':'Corrected lifetime probe passed four selected tests in each mode against the earlier HTTP fixture; diagnostic comparison only, superseded by exact final candidate-v4.'},
    'limits':[
        'Local Apple Swift 6.3.3 / Xcode 26.6 differs from hosted Apple Swift 6.2.4 / Xcode 26.3. The hosted race was not reproduced locally; a pinned hosted replay remains mandatory.',
        'The native capability VM archive and headers are reused from the producer frozen 26943ac receipt with independently rechecked hashes. This is not a build or qualification of current whole-VM changes.',
        'Rust archive/system frameworks are not Swift TSan instrumented; the bounded schedules do not prove every possible interleaving.',
        'No observer/gate timeout increase, polling-bound increase or sanitizer suppression was used as qualification. The fixture operation budget is distinct from its unchanged observation/gate bounds.',
        'No physical device, cross-platform, published-package dogfood, signing, store, customer, release or GA gate evidence; no commit, push or tracker edit from this reviewer.'
    ]}
(OUT/'findings.json').write_text(json.dumps(findings,indent=2)+'\n')
manifest = {str(p.relative_to(OUT)):sha(p.read_bytes()) for p in sorted(OUT.rglob('*'))
            if p.is_file() and not {'source','.build','__pycache__'}.intersection(p.relative_to(OUT).parts)
            and p.name != 'evidence-manifest.json' and p.suffix not in {'.pem','.key'}}
(OUT/'evidence-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'testsPerMode':51,'modes':len(checks),'reviewedFilesSHA256':receipt['candidateFilesSHA256'],
                  'receiptSHA256':sha((OUT/'candidate-v4/receipt.json').read_bytes())},indent=2))
