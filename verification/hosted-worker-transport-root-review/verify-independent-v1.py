#!/usr/bin/env python3
"""Verify retained review data; passing defect reproductions are not acceptance."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REVIEW = ROOT / 'verification/hosted-worker-transport-independent-review'
PRODUCER = ROOT / 'verification/hosted-worker-transport'
RECEIPT = '5c4e1605be31b6ba1de6feff18794c071d1dbc2dc9fee72102cf86145f46f7c7'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    output = BASE / 'independent-v1-decision.json'
    require(not output.exists(), 'Preserve previous decision')
    raw = (REVIEW / 'receipt.json').read_bytes()
    require(sha(raw) == RECEIPT, 'Review receipt changed')
    receipt = json.loads(raw)
    for row in receipt['artifacts']:
        path = REVIEW / row['path']
        require(path.resolve() == path and path.is_file() and path.stat().st_nlink == 1,
                'Noncanonical review artifact')
        data = path.read_bytes()
        require(len(data) == row['size'] and sha(data) == row['sha256'], 'Review artifact changed')
    document = receipt['review_document']
    require(sha((ROOT / document['path']).read_bytes()) == document['sha256'], 'Review document changed')
    binding = json.loads((REVIEW / 'input-binding.json').read_bytes())
    producer = json.loads((PRODUCER / 'receipt.json').read_bytes())
    require(binding['sources'] == json.loads((PRODUCER / 'source-map.json').read_bytes())['sources'],
            'Reviewer used different producer input')
    require(binding['source_digest'] == receipt['source_digest'] == producer['source_digest'], 'Source digest mismatch')
    archive = PRODUCER / 'candidate-inputs.tar.gz'
    require(sha(archive.read_bytes()) == receipt['archive_sha256'] == producer['archive_sha256'], 'Archive changed')
    expected = {row['path']: row for row in binding['sources']}
    require(len(expected) == binding['input_count'] == 86, 'Input count mismatch')
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        require(len(members) == len(expected) and {m.name for m in members} == set(expected), 'Archive inventory mismatch')
        for member in members:
            require(member.isfile() and not member.islnk() and not member.issym(), 'Nonregular archived input')
            row = expected[member.name]
            data = tar.extractfile(member).read()
            require(len(data) == row['size'] and sha(data) == row['sha256'], 'Archived input changed')
            path = ROOT / member.name
            require(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == row['sha256'], 'Current input changed')
    commands = json.loads((REVIEW / 'commands.json').read_bytes())['commands']
    for command in commands:
        require(command['exit_code'] == 0 and command['outer_timeout'] is False, 'Final review command failed')
        for stream in ['stdout', 'stderr']:
            require(sha((REVIEW / (command['name'] + '.' + stream)).read_bytes()) == command[stream + '_sha256'], 'Command output changed')
    counts = {}
    for key, expected_count in [('producer_replay', 25), ('independent_controls', 13)]:
        row = receipt['test_results'][key]
        require((row['tests'], row['failures'], row['skipped'], row['excluded']) == (expected_count, 0, 0, 0), 'Review execution result changed')
        require(row['frozen_modules_loaded'] == [], 'Unexpected module loaded')
        counts[key] = expected_count
    reproduction = json.loads((REVIEW / 'guard-loss-reproduction.json').read_bytes())
    require(reproduction['replacement_role_accepted'] is True and reproduction['live_server_tls_handlers'] == 17
            and reproduction['expected_global_limit'] == 16 and reproduction['old_raw_open'] is True
            and reproduction['old_ssl_handler_alive'] is True, 'Defect reproduction changed')
    header_evidence = {}
    for command in ['query', 'ensure_started', 'stop']:
        data = (REVIEW / ('authenticated-request-' + command + '.http')).read_bytes()
        head, body = data.split(b'\r\n\r\n', 1)
        lines = head.split(b'\r\n')
        require(lines[0] == b'POST /internal/mixer-build-worker/v1 HTTP/1.1', 'Request line changed')
        headers = [line.split(b':', 1) for line in lines[1:]]
        fields = {key.lower(): value.strip() for key, value in headers}
        require(len(headers) == len(fields) == 8 and fields[b'user-agent'] == b'mint/1.11.0', 'Original header mismatch changed')
        require(int(fields[b'content-length']) == len(body), 'Body length differs')
        require(json.loads(body)['command'] == command, 'Command identity differs')
        header_evidence[command] = {'headerCount': len(headers), 'userAgent': fields[b'user-agent'].decode(),
                                    'syntheticCredentialOnly': True, 'sha256': sha(data)}
    require(not (REVIEW / 'inputs').exists() and not (REVIEW / 'build').exists(), 'Owned extraction/build remains')
    result = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'command': [sys.executable, str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
              'verifierSHA256': sha(Path(__file__).read_bytes()), 'reviewReceiptSHA256': RECEIPT,
              'status': 'v1-integration-rejected-repair-required', 'currentAndArchivedInputsVerified': len(expected),
              'reviewArtifactsVerified': len(receipt['artifacts']), 'reviewCommandOutputsVerified': len(commands),
              'testExecutions': counts, 'interpretation': 'Independent passing controls include successful defect reproductions.',
              'blockingReproduction': reproduction, 'actualHeaderEvidence': header_evidence,
              'nextCandidateHeaderContract': 'docs/hosted-worker-transport-amendment-v2.md',
              'reviewCleanup': receipt['cleanup'], 'rootImportedOrExecutedCandidateCode': False,
              'productionIntegrationAccepted': False, 'nativeOrProviderAccepted': False, 'gaAccepted': False}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ['status', 'currentAndArchivedInputsVerified', 'reviewArtifactsVerified', 'reviewCommandOutputsVerified']}))


if __name__ == '__main__':
    main()
