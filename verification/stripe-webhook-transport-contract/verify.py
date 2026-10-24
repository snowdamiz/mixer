"""Verify retained closures and scoped API observations, without live baseline assumptions."""
import base64, hashlib, json, tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify_run(run):
    seal = json.loads((run / 'seal.json').read_text())
    actual = {str(p.relative_to(run)) for p in run.rglob('*') if p.is_file() and p != run / 'seal.json'}
    assert set(seal) == actual, (run.name, 'seal inventory mismatch')
    for name, value in seal.items():
        data = (run / name).read_bytes()
        assert sha(data) == value['sha256'] and len(data) == value['bytes'], (run.name, name)
    with tarfile.open(run / 'source-closure.tar.gz') as archive:
        manifest = json.loads((run / 'source-inputs.json').read_text())
        assert {member.name for member in archive.getmembers()} == set(manifest)
        for name, digest in manifest.items():
            assert sha(archive.extractfile(name).read()) == digest, (run.name, name)
        acceptance = json.loads(archive.extractfile('verification/stripe-raw-body-integration/acceptance.json').read())
        for name, digest in acceptance['sourceInputs'].items():
            assert manifest[name] == digest, (run.name, 'accepted source', name)
        pins = json.loads(archive.extractfile('verification/stripe-raw-body-capture/pinned-dependency-identity.json').read())
        assert pins['source'] == json.loads((run / 'dependency-source-inputs.json').read_text())
        assert pins['beams'] == json.loads((run / 'dependency-beam-inputs.json').read_text())
    with tarfile.open(run / 'dependency-source-closure.tar.gz') as archive:
        manifest = json.loads((run / 'dependency-source-inputs.json').read_text())
        assert {member.name for member in archive.getmembers()} == set(manifest)
        for name, digest in manifest.items():
            assert sha(archive.extractfile(name).read()) == digest, (run.name, 'dependency source', name)
    receipt = json.loads((run / 'receipt.json').read_text())
    cleanup = receipt['cleanup']
    assert cleanup['scratchRemoved'] and cleanup['ownedProcessGroupsEmpty'] and not cleanup['openHolders']
    assert all(value['connectionRefused'] for value in cleanup['ports'])
    for command in receipt['commands']:
        assert sha((run / command['output']).read_bytes()) == command['outputSHA256']
    return receipt

def main():
    attempts = json.loads((HERE / 'attempts.json').read_text())
    for attempt in attempts['attempts']:
        receipt = verify_run(HERE / attempt['run'])
        assert (receipt['failure'] is None) == (attempt['status'] == 'pass')
    final = HERE / attempts['authoritativeRun']
    result = json.loads((final / 'probe.json').read_text())
    assert all(result['cleanup'][key] for key in ['listener_down', 'connection_and_stream_owners_down', 'watchdogs_down', 'port_refused', 'telemetry_detached', 'owned_logger_handlers_removed'])
    assert len(result['cleanup']['sockets']) == 8 and all(value['closed'] for value in result['cleanup']['sockets'])
    kills = [value for value in result['results'] if value['kind'] == 'watchdog_kill']
    assert len(kills) == 4 and all(value['reason'] == ':killed' and 500 <= value['elapsed_ms'] <= 600 for value in kills)
    stalled = {'h1-body-stall', 'h2-body-drip', 'h2-stream-only'}
    assert not any(value['kind'] == 'capture_return' and value['case'] in stalled for value in result['results'])
    clients = [value for value in result['results'] if value['kind'] == 'client']
    assert len(clients) == 8
    for name in ['h1-cl-success', 'h1-chunked-success']:
        client = next(value for value in clients if value['case'] == name)
        assert base64.b64decode(client['result']['response_base64']).startswith(b'HTTP/1.1 418 ')
    trailer_client = next(value for value in clients if value['case'] == 'h2-trailer-sink')
    assert any(value['type'] == 'status' and value['status'] == 418 for value in trailer_client['responses'])
    stream_only = next(value for value in clients if value['case'] == 'h2-stream-only')
    assert stream_only['responses'] == [] and stream_only['connection_usable_after_stream_kill']
    assert any(value['bits']['trailer'] for value in result['unfiltered_logs'])
    assert len(result['filtered_logs']) == 3 and all(value['safe'] for value in result['filtered_logs'])
    assert not any(any(value['bits'].values()) for value in result['filtered_logs'])
    telemetry = result['telemetry']
    assert any(value['event'][-1] == 'recv' and value['measurements']['body'] for value in telemetry)
    assert any(value['event'][-1] == 'async_recv' and value['measurements']['signature'] for value in telemetry)
    assert any(value['event'] == ['bandit', 'request', 'start'] and value['metadata']['signature'] for value in telemetry)
    for item in json.loads((HERE / 'api-map.json').read_text())['findings']:
        source = (HERE / item['retainedSource']).read_bytes()
        assert sha(source) == item['sourceSHA256']
        assert 0 < item['lines'][0] <= item['lines'][1] <= len(source.splitlines())
    for source in json.loads((HERE / 'sources.json').read_text())['sources']:
        if 'retained' in source:
            assert sha((HERE / source['retained']).read_bytes()) == source['sha256']
    receipt = json.loads((HERE / 'receipt.json').read_text())
    assert sha((REPO / receipt['contract']).read_bytes()) == receipt['contractSHA256']
    assert receipt['rootContractSelection'] == 'pending' and not receipt['publicAdmissionAccepted'] and not receipt['g23Accepted']
    for value in json.loads((HERE / 'upstream-receipts/manifest.json').read_text())['sources'].values():
        assert sha((HERE / value['retained']).read_bytes()) == value['sha256']
    seal_path = HERE / 'seal.json'
    if seal_path.exists():
        seal = json.loads(seal_path.read_text())
        inventory = {str(p.relative_to(REPO)) for p in HERE.rglob('*') if p.is_file() and p != seal_path}
        inventory.add('docs/stripe-webhook-transport-contract.md')
        assert inventory == set(seal['files']), 'top-level inventory drift'
        for name, value in seal['files'].items():
            data = (REPO / name).read_bytes()
            assert sha(data) == value['sha256'] and len(data) == value['bytes'], name
    print(json.dumps({'status': 'pass', 'attempts': len(attempts['attempts']), 'authoritativeRun': final.name, 'clients': len(clients), 'watchdogKills': len(kills), 'fullPrivacyQualified': False, 'rootSelection': 'pending', 'publicAdmission': False}, sort_keys=True))

if __name__ == '__main__':
    main()
