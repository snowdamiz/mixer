"""Seal the independent private-component review without changing producer evidence."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRODUCER = REPO/'verification/stripe-raw-body-capture'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())
def write(p, data): p.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')

def main():
    run = HERE/'run-1'
    summary = load(run/'summary.json')
    integrity = load(run/'integrity.json')
    receipt = load(run/'receipt.json')
    assert receipt['failure'] is None and receipt['cleanup']['scratchRemoved']
    selection = load(REPO/'verification/stripe-raw-body-root-review/selection.json')
    reviewed = {
        'schema': 1, 'observedUTC': datetime.now(timezone.utc).isoformat(),
        'status': 'independent-review-pass-private-component-only-awaiting-root-acceptance',
        'recommendation': 'accept the sealed bounded private component development slice',
        'rootAcceptance': 'pending', 'blockingFindings': [],
        'candidateSHA256': integrity['candidateSHA256'], 'sourceRevisionFromRootSelection': selection['sourceRevision'],
        'acceptedHostedSourceDigest': integrity['sourceDigest'], 'hostedInputs': integrity['hostedInputs'],
        'producerSealSHA256': sha(PRODUCER/'seal.json'), 'producerFiles': integrity['producerFiles'],
        'producerArchiveMemberBindings': integrity['archiveMemberBindings'], 'producerAttemptsRetained': 9,
        'producerCorrelationsExact': True, 'originalMatrixRowsRetained': 13,
        'freshReviewRun': 'run-1', 'freshReviewSummary': summary,
        'independentComponentGroups': 8, 'independentControlledSubcases': 360,
        'actualInvocationObservation': 'VM trace_pattern on real WebhookSignature.verify/4, per-process call trace, separate collector, delivery barrier, argument hash/length/header checks',
        'nonBlockingComponentObservations': [
            {'id': 'O01', 'observation': 'All exact-byte and occurrence checks pass, including identical duplicate signatures rejected on H1 and H2 before body reads.'},
            {'id': 'O02', 'observation': 'Fresh H2 60001-byte explicit-length body returned 49152 bytes against a 32768 target; exact body/HMAC and actual invocation arguments preserved.'},
            {'id': 'O03', 'observation': 'Slow H2 55-byte result returned at 5557ms; read_deadline, halted result, zero actual verifier calls, no 2xx.'},
            {'id': 'O04', 'observation': 'Received synthetic body/signature are exposed in ThousandIsland measurements; Bandit metadata and H2 trailer Logger exposure independently reproduced.'}
        ],
        'cleanup': receipt['cleanup'], 'freshCandidateAndSignatureCompilation': True, 'freshDependencyCompilation': False,
        'productionChanged': False, 'producerEvidenceChanged': False, 'trackerChanged': False, 'nativeStarted': False,
        'publicAdmissionAccepted': False, 'g23Accepted': False,
        'pending': ['root acceptance/integration', 'endpoint transport telemetry/log privacy', 'hard cancellation and stream/connection disposal',
            'header-read deadlines, resource and buffer limits', 'TLS/ALPN/deployed ingress/provider compatibility',
            'real maximum-size H2 body', 'server-owned endpoint/account/mode/generation/secrets',
            'durable deduplicated inbox with atomic Oban enqueue', 'Stripe test-mode reconciliation', 'usage ledger and full G23 workflows'],
        'replayCommand': ['python3', '-B', 'verification/stripe-raw-body-capture-review/run.py'],
        'verificationCommand': ['python3', '-B', 'verification/stripe-raw-body-capture-review/verify.py']
    }
    write(HERE/'review.json', reviewed)
    entries = {str(p.relative_to(REPO)): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(HERE.rglob('*')) if p.is_file() and p != HERE/'seal.json'}
    doc = REPO/'docs/stripe-raw-body-capture-review.md'
    entries[str(doc.relative_to(REPO))] = {'bytes': doc.stat().st_size, 'sha256': sha(doc)}
    write(HERE/'seal.json', entries)
    print(f'SEALED: {len(entries)} independent review files; private component recommendation, root/public/G23 pending')

if __name__ == '__main__': main()
