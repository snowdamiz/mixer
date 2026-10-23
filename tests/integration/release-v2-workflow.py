#!/usr/bin/env python3
"""Real loopback HTTP v1/v2 -> public Swift verifier; small TEST fixtures only."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'compiler'))
from qualification_support import CommandRecorder, clean_environment, strict_json
LEGACY = '6cb27591319a2066e1eb8b3025400137373cb2d6'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def source():
    paths = list((ROOT/'services').rglob('*.go')) + list((ROOT/'services/release/migrations').glob('*.sql'))
    paths += list((ROOT/'updates/Sources').rglob('*')) + list((ROOT/'tests/integration/http-v2-consumer/Sources').rglob('*.swift'))
    paths += [ROOT/name for name in ['services/go.mod', 'services/go.sum', 'updates/Package.swift', 'updates/Package.resolved',
        'tests/integration/http-v2-consumer/Package.swift', 'tests/integration/http-v2-consumer/Package.resolved',
        'tests/integration/release-v2-workflow.py', 'compiler/qualification_support.py', 'contracts/release-v1.json', 'contracts/release-v2.json',
        'services/README.md', 'services/protocol/README.md', 'services/release/POSTGRES.md', 'tests/integration/README.md',
        'services/protocol/testdata/signed-release-v1.json', 'services/protocol/testdata/signed-release-v2.json']]
    rows = [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in sorted(set(paths)) if p.is_file()]
    return {'algorithm': 'SHA256 of compact sorted JSON path/hash array', 'files': rows,
            'sha256': hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--swift', required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve(); output.mkdir(parents=True, exist_ok=False)
    environment = dict(clean_environment(), GOTOOLCHAIN='go1.26.4', TOOLCHAINS='com.apple.dt.toolchain.XcodeDefault')
    if os.environ.get('DEVELOPER_DIR'):
        environment['DEVELOPER_DIR'] = os.environ['DEVELOPER_DIR']
    environment['PATH'] = str(args.swift.resolve().parent) + os.pathsep + environment['PATH']
    receipt = {'schema': 1, 'status': 'running', 'scope': __doc__, 'commands': [], 'requests': [],
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'testedSource': source(), 'limitations': ['Local checkout dependencies, not immutable published consumer adoption.',
            'Public TEST roots/non-executable payloads only; no production credential, native capability execution, activation or device/OTA qualification.',
            'Swift HTTP test consumer accepts small fixtures up to 96KiB and uses the metadata string bound; this is not a production large-payload downloader.',
            'This HTTP harness uses the local snapshot store; real PostgreSQL is exercised by the separate isolated-cluster runner.',
            'No new CLI publication command, hosted deployment, outbox dispatch or production readiness.']}
    server = None
    server_stream = None

    def run(name, command, cwd=ROOT, expected=0, env=None, timeout=180):
        command = [str(p) for p in command]
        if not Path(command[0]).is_absolute(): command[0] = shutil.which(command[0]) or command[0]
        recorder = CommandRecorder(output, receipt['commands'], cwd, log_limit=8_388_608, result_limit=2_097_152)
        try:
            return recorder.run(name, command, env=environment if env is None else env, expected=(expected,), timeout=timeout)
        finally:
            row = receipt['commands'][-1]
            row['workingDirectory'], row['expectedExitCode'] = str(cwd), expected
            print(json.dumps(row), flush=True)

    def start():
        nonlocal server, server_stream
        server_stream = (output/('server-'+str(len(receipt.get('serverRuns', [])))+'.log')).open('wb')
        server_env = dict(environment, MIXER_SERVICE_CONFIG=str(output/'service.json'))
        server = subprocess.Popen([str(executable)], cwd=ROOT, env=server_env, stdout=server_stream, stderr=subprocess.STDOUT)
        receipt.setdefault('serverRuns', []).append({'binarySHA256': sha(executable), 'configPath': str(output/'service.json'),
            'credentialStorage': 'only scoped token hashes in config; ephemeral bearer values never logged', 'pid': server.pid})
        for _ in range(120):
            check(server.poll() is None, 'Local service exited before readiness')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.1): return
            except OSError: time.sleep(.05)
        raise RuntimeError('Local loopback service did not become ready')

    def stop():
        nonlocal server, server_stream
        if server is not None:
            server.terminate()
            try: code = server.wait(timeout=12)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait(); raise RuntimeError('Service failed graceful shutdown')
            receipt['serverRuns'][-1]['exitCode'] = code
            server_stream.close(); server_stream = None; server = None
            check(code == 0, 'Service lifecycle failed')

    try:
        receipt['swiftVersion'] = run('swift-version', [args.swift, '--version'])
        receipt['goVersion'] = run('go-version', ['go', 'version'], ROOT/'services')
        receipt['xcodeVersion'] = run('xcode-version', ['/usr/bin/xcodebuild', '-version'])
        executable = output/'mixer-service'
        run('build-service', ['go', 'build', '-trimpath', '-o', executable, './cmd/mixer-service'], ROOT/'services')
        package = ROOT/'tests/integration/http-v2-consumer'; scratch = output/'swift-build'
        run('build-swift-consumer', [args.swift, 'build', '--package-path', package, '--scratch-path', scratch], timeout=600)
        binary_folder = Path(run('swift-bin-path', [args.swift, 'build', '--package-path', package, '--scratch-path', scratch, '--show-bin-path']).strip())
        consumer = binary_folder/'http-release-check'
        receipt['builtBinaries'] = {'serviceSHA256': sha(executable), 'swiftConsumerSHA256': sha(consumer)}
        archive = output/'legacy-source.tar'
        run('legacy-source-archive', ['git', 'archive', '--format=tar', '--output', archive, LEGACY, 'services'])
        legacy_source = output/'legacy-source'; legacy_source.mkdir()
        with tarfile.open(archive) as source_archive: source_archive.extractall(legacy_source, filter='data')
        legacy_binary = output/'mixer-service-v1-only'
        run('build-v1-only-service', ['go', 'build', '-trimpath', '-o', legacy_binary, './cmd/mixer-service'], legacy_source/'services')
        receipt['legacyBinary'] = {'sourceCommit': LEGACY, 'sha256': sha(legacy_binary)}
        vectors = {v: json.loads((ROOT/f'services/protocol/testdata/signed-release-v{v}.json').read_text()) for v in (1, 2)}
        check(all(v['test_only'] for v in vectors.values()), 'Only public TEST fixtures are supported')
        token = secrets.token_urlsafe(32)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        config = {'developer_mode': True, 'listen': f'127.0.0.1:{port}', 'data_directory': str(output/'state'),
            'hosts': [vectors[v]['host'] for v in (1, 2)], 'roots': vectors[1]['roots']+vectors[2]['roots'],
            'tokens': [{'sha256': hashlib.sha256(token.encode()).hexdigest(), 'role': 'publisher', 'organization': 'org-a', 'project': 'project-a', 'actor': 'TEST-http-integration'}]}
        config_path = output/'service.json'; config_path.write_text(json.dumps(config)); config_path.chmod(0o600)
        opener = urllib.request.build_opener(NoRedirect())

        def request(method, path, value=None, key='', auth=True, expected=200):
            check(server is not None and server.poll() is None, 'Owned local service exited')
            check(path.startswith(('/v1/', '/v2/')), 'Unexpected delivery version or external URL')
            body = None if value is None else json.dumps(value, separators=(',', ':')).encode()
            headers = {'Content-Type': 'application/json'}
            if auth: headers['Authorization'] = 'Bearer '+token
            if key: headers['Idempotency-Key'] = key
            req = urllib.request.Request(base+path, data=body, headers=headers, method=method)
            try:
                with opener.open(req, timeout=5) as response: status, data = response.status, response.read(24*1_048_576+1)
            except urllib.error.HTTPError as error: status, data = error.code, error.read(24*1_048_576+1)
            check(status == expected and len(data) <= 24*1_048_576, str((method, path, status, expected, data[:300])))
            receipt['requests'].append({'method': method, 'path': path, 'status': status, 'bodySHA256': hashlib.sha256(body or b'').hexdigest(), 'responseSHA256': hashlib.sha256(data).hexdigest()})
            return data

        start()
        scope = '/orgs/org-a/projects/project-a'
        legacy_wire = None
        for version in (1, 2):
            vector = vectors[version]; prefix = f'/v{version}'+scope; digest = vector['artifact_sha256']
            upload = {'signed_manifest': vector['signed_manifest'], 'payload': vector['payload']}
            if version == 2:
                snapshot = (output/'state/release.json').read_bytes()
                check(strict_json(snapshot)['schema'] == 1, 'Legacy operation upgraded schema')
                request('PUT', prefix+'/artifacts/'+digest, upload, 'unauth-v2', auth=False, expected=401)
                request('PUT', '/v1'+scope+'/artifacts/'+digest, upload, 'wrong-version-v2', expected=400)
                request('PUT', prefix+'/artifacts/'+digest, upload, 'upload-v1', expected=409)
                check((output/'state/release.json').read_bytes() == snapshot, 'Failed v2 request mutated/upgraded state')
            first = request('PUT', prefix+'/artifacts/'+digest, upload, f'upload-v{version}', expected=201)
            check(request('PUT', prefix+'/artifacts/'+digest, upload, f'upload-v{version}', expected=201) == first, 'Idempotent retry changed response')
            request('POST', prefix+'/releases/validate', {'artifact_sha256': digest}, f'validate-v{version}')
            request('POST', prefix+'/channels/beta/publish', {'signed_assignment': vector['signed_assignment']}, f'publish-v{version}')
            command = [consumer, base, ROOT/f'services/protocol/testdata/signed-release-v{version}.json', str(version), '0']
            result = strict_json(run(f'swift-http-v{version}', command).strip().splitlines()[-1])
            check(result['status'] == 'passed' and result['protocol'] == version and result['artifactSHA256'] == digest, 'Swift did not verify selected content')
            check(len(result['verifiedGrants']) == (2 if version == 2 else 0), 'Typed grants absent or v1 gained authority')
            receipt.setdefault('swiftHTTP', []).append(result)
            replay = command[:-1]+[str(vector['signed_assignment']['assignment']['sequence'])]
            rejected = strict_json(run(f'swift-replay-v{version}', replay, expected=1).strip().splitlines()[-1])
            check(rejected['status'] == 'rejected' and ('sequence' in rejected['error'].lower() or 'replay' in rejected['error'].lower()), 'Replay rejection reason differs')
            wire = request('GET', f'/v{version}/artifacts/'+digest+'?organization=org-a&project=project-a', auth=False)
            if version == 1: legacy_wire = wire
        check(strict_json((output/'state/release.json').read_text())['schema'] == 2, 'Successful v2 commit did not upgrade schema')
        request('GET', '/v1/artifacts/'+vectors[2]['artifact_sha256']+'?organization=org-a&project=project-a', auth=False, expected=404)
        q = dict(vectors[2]['host']['scope'], runtime=vectors[2]['host']['runtime'], channel='beta', installation=vectors[2]['installation'])
        request('GET', '/v1/updates?'+urllib.parse.urlencode(q), auth=False, expected=204)
        mismatch = [consumer, base, ROOT/'services/protocol/testdata/signed-release-v2.json', '1', '0']
        rejected = strict_json(run('swift-explicit-version-mismatch', mismatch, expected=1).strip().splitlines()[-1])
        check(rejected['status'] == 'rejected' and 'refusing version probing' in rejected['error'], 'Explicit version mismatch not rejected')
        stop()
        state_hash = sha(output/'state/release.json')
        old_config = dict(config, hosts=[vectors[1]['host']]); old_path = output/'legacy-config.json'
        old_path.write_text(json.dumps(old_config)); old_path.chmod(0o600)
        run('old-service-refuses-schema2', [legacy_binary], expected=1,
            env=dict(environment, MIXER_SERVICE_CONFIG=str(old_path)), timeout=10)
        failure = (output/'old-service-refuses-schema2.stderr').read_text()
        check('corrupt durable store' in failure or 'unknown durable store schema' in failure, 'Old service failed for unrelated reason')
        check(sha(output/'state/release.json') == state_hash, 'Old service mutated upgraded state')
        receipt['oldBinaryRefusesUpgradedSnapshotWithoutMutation'] = True
        start()
        check(request('GET', '/v1/artifacts/'+vectors[1]['artifact_sha256']+'?organization=org-a&project=project-a', auth=False) == legacy_wire, 'Restart changed legacy bytes')
        report = strict_json(run('swift-v2-after-restart', [consumer, base, ROOT/'services/protocol/testdata/signed-release-v2.json', '2', '0']).strip().splitlines()[-1])
        check(report['artifactSHA256'] == vectors[2]['artifact_sha256'], 'Restart lost v2 verified content')
        receipt['restartPreservesV1BytesAndV2VerifiedGrants'] = True
        stop()
        check(source() == receipt['testedSource'], 'Source changed during integration; freeze and rerun')
        check(sha(executable) == receipt['builtBinaries']['serviceSHA256'] and sha(consumer) == receipt['builtBinaries']['swiftConsumerSHA256'], 'Frozen executable changed')
        receipt['status'] = 'passed-local-http-v1-v2-public-swift-verification'
    except Exception as error:
        receipt['status'], receipt['failure'] = 'failed', str(error)
        raise
    finally:
        if server is not None:
            try: stop()
            except Exception as error:
                receipt['cleanupFailure'], receipt['status'] = str(error), 'failed'
        (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    if receipt['status'] != 'passed-local-http-v1-v2-public-swift-verification':
        raise RuntimeError('Qualification or cleanup failed; see receipt')


if __name__ == '__main__':
    main()
