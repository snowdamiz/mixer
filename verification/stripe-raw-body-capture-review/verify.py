"""Read-only, content-based review seal, provenance, invocation and cleanup checks."""
import difflib, hashlib, json, tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from run import audit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRODUCER = REPO/'verification/stripe-raw-body-capture'
EXPECTED = '7797a09d3a99f5dabafb681bf2e5bda4bb1f01bc3974beb94176965f9f30546e'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())
def archive(path):
    content = {}
    with tarfile.open(path) as tar:
        for entry in tar:
            p = PurePosixPath(entry.name)
            assert entry.isfile() and not p.is_absolute() and '..' not in p.parts and entry.name not in content
            content[entry.name] = tar.extractfile(entry).read()
    return content

def main():
    seal = load(HERE/'seal.json')
    expected = {str(p.relative_to(REPO)) for p in HERE.rglob('*') if p.is_file() and p != HERE/'seal.json'} | {'docs/stripe-raw-body-capture-review.md'}
    assert set(seal) == expected
    for path, pin in seal.items():
        p = REPO/path
        assert p.stat().st_size == pin['bytes'] and sha(p) == pin['sha256'], path
    review = load(HERE/'review.json')
    assert review['candidateSHA256'] == EXPECTED
    assert review['blockingFindings'] == [] and review['rootAcceptance'] == 'pending'
    assert review['publicAdmissionAccepted'] is False and review['g23Accepted'] is False
    assert sha(PRODUCER/'seal.json') == review['producerSealSHA256']
    assert audit() == load(HERE/'run-1/integrity.json'), 'producer archive/current pin audit changed'
    for path, pin in load(PRODUCER/'seal.json').items():
        p = REPO/path
        assert p.stat().st_size == pin['bytes'] and sha(p) == pin['sha256'], path
    for run in sorted(HERE.glob('run-*')):
        nested = load(run/'seal.json')
        assert set(nested) == {str(p.relative_to(run)) for p in run.rglob('*') if p.is_file() and p.name != 'seal.json'}
        for path, pin in nested.items():
            p = run/path
            assert p.stat().st_size == pin['bytes'] and sha(p) == pin['sha256']
        source = archive(run/'review-source-closure.tar.gz')
        assert {p: hashlib.sha256(b).hexdigest() for p, b in source.items()} == load(run/'source-inputs.json')
        assert hashlib.sha256(source['candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex']).hexdigest() == EXPECTED
        original = archive(PRODUCER/'run-9/candidate-source-closure.tar.gz')
        for path, content in original.items():
            if path != 'tests/wire.exs': assert source[path] == content, path
        assert source['tests/independent.exs'] == (HERE/'independent.exs').read_bytes()
        diff = ''.join(difflib.unified_diff(original['tests/wire.exs'].decode().splitlines(True), source['tests/wire.exs'].decode().splitlines(True), fromfile='sealed-producer/tests/wire.exs', tofile='review-derived/tests/wire.exs'))
        assert (run/'wire-instrumentation.diff').read_text() == diff
        receipt = load(run/'receipt.json')
        assert receipt['failure'] is None and receipt['cleanup']['scratchRemoved'] is True
        assert receipt['cleanup']['identityMatched'] and receipt['cleanup']['ownedProcessGroupsEmpty']
        assert receipt['cleanup']['lsofExit'] == 1 and receipt['cleanup']['openHolders'] is False
        assert all(x['connectionRefused'] for x in receipt['cleanup']['ports'])
        assert load(run/'owned-process-groups.json')['remaining'] == []
        for command in receipt['commands']:
            assert command['exitCode'] == 0 and command['timedOut'] is False
            assert sha(run/command['output']) == command['outputSHA256']
        for phase in ['component', 'independent', 'wire']:
            policy = load(run/phase/'production-policy.json')
            assert policy['testClockAtomPresent'] is False and policy['productionClockSpoofIgnored'] is True
            assert sha(run/phase/'production-beam/Elixir.MixerHosted.Billing.RawWebhookCapture.beam') == policy['sha256']
        events = load(run/'wire/events.json')
        clients = load(run/'wire/clients.json')
        by_id = {x['id']: x for x in events}
        assert len(events) == len(by_id) == 100 and len(clients) == 110
        assert len({x['id'] for x in clients}) == 110
        for event in events:
            assert event['tracedVerifierCalls'] == event['verifierCalls'] == (1 if event['outcome'] == 'captured' else 0)
            if event['outcome'] == 'captured':
                [actual] = event['tracedVerifierInputs']
                assert actual['bodySHA256'] == event['bodySHA256'] and actual['bodyBytes'] == event['bodyBytes']
                assert actual['signatureValues'] == event['signatureValues'] == event['exposedSignatureValues']
                assert actual['secretCount'] == 1 and actual['utc'] == 1700000000
            else: assert event['tracedVerifierInputs'] == []
        assert all(not any(200 <= status <= 299 for status in c['statuses']) for c in clients)
        assert all(c['serverEnd'] != 'harness_deadline' for c in clients)
        correlations = [{'id': c['id'], 'statuses': c['statuses'], 'transport': c['transport'], 'classification': by_id.get(c['id'], {}).get('outcome', 'framework-pre-Plug'), 'event': by_id.get(c['id'])} for c in clients]
        assert load(run/'correlations.json') == correlations
        summary = load(run/'summary.json')
        assert summary['actualTracedVerifierCalls'] == sum(x['tracedVerifierCalls'] for x in events) == 31
        assert summary['outcomes'] == dict(Counter(x['classification'] for x in correlations))
        assert summary['transports'] == dict(Counter(x['transport'] for x in clients))
        for phase, name, count in [('component', 'component-summary.json', 14), ('independent', 'independent-summary.json', 8), ('wire', 'wire-summary.json', 16)]:
            assert load(run/phase/name) == {'excluded': 0, 'failures': 0, 'skipped': 0, 'total': count}
        late = by_id['h2-late-success']
        assert late['elapsedMs'] >= 5000 and late['reason'] == 'read_deadline' and late['tracedVerifierCalls'] == 0
        telemetry = load(run/'wire/telemetry.json')
        logs = load(run/'wire/logs.json')
        assert any(x['event'] == ['thousand_island', 'connection', 'recv'] and x['measurementBodySeen'] for x in telemetry)
        assert any(x['event'] == ['thousand_island', 'connection', 'recv'] and x['measurementSignatureSeen'] for x in telemetry)
        assert any(x['event'][0] == 'bandit' and (x['metadataBodySeen'] or x['metadataSignatureSeen']) for x in telemetry)
        assert any(x['trailerSeen'] for x in logs)
        listener = load(run/'wire/listener-cleanup.json')
        assert all(listener[x] for x in ['listenerStopped', 'connectRefused', 'telemetryDetached', 'loggerHandlerRemoved'])
        assert len(load(run/'wire/socketCleanup.json')) == len(clients)
        assert all(x['closed'] for x in load(run/'wire/socketCleanup.json'))
    print(f'PASS: {len(seal)} sealed review files; exact producer seal/source/archive/diff; 38 test groups, 110 clients, 31 actual verifier calls; cleanup; public/G23 remain pending')

if __name__ == '__main__': main()
