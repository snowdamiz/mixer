#!/usr/bin/env python3
"""Real local HTTP + linked Swift crypto + trusted owned-VM executable integration.

This uses fresh synthetic fixtures and immutable local tool snapshots. It does
not attest a hostile local executable or qualify physical/mobile/hosted OTA.
"""
from pathlib import Path
import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'compiler'))
from qualification_support import CommandRecorder, clean_environment, strict_json


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(65536), b''):
            sha.update(chunk)
    return sha.hexdigest()


def command(args, cwd=ROOT, expected=0, env=None):
    args = [str(x) for x in args]
    if not Path(args[0]).is_absolute():
        args[0] = shutil.which(args[0]) or args[0]
    return CommandRecorder(log_folder, commands, cwd).run(
        'command-'+str(len(commands)+1), args, expected=(expected,),
        timeout=180, env=env if env is not None else clean_environment())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


with tempfile.TemporaryDirectory(prefix='mixer-release-e2e-') as temporary:
    folder = Path(temporary)
    tool_folder = folder/'tools'
    tool_folder.mkdir(mode=0o700)
    log_folder = folder/'logs'
    log_folder.mkdir(mode=0o700)
    commands = []
    tools, identities = {}, {}
    for name, relative in [('cli', 'cli/.build/debug/mixer'),
                           ('verifier', 'updates/.build/debug/mixer-update'),
                           ('vm', 'vm/target/release/mixer-vm')]:
        source = ROOT/relative
        target = tool_folder/name
        shutil.copyfile(source, target)
        target.chmod(0o500)
        sha = digest(target)
        check(sha == digest(source), 'Verification executable changed while snapshotting')
        tools[name] = target
        identities[name] = {'sourcePath': relative, 'sha256': sha}
    # Ambient overrides must not make a receipt name binaries it did not run.
    env = dict(clean_environment(), MIXER_UPDATE_TOOL=str(tools['verifier']), MIXER_VM=str(tools['vm']))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    command(['go', 'run', ROOT/'tests/integration/release_fixture.go', folder,
             f'127.0.0.1:{port}'], cwd=ROOT/'services')
    executable = folder/'mixer-service'
    command(['go', 'build', '-o', executable, './cmd/mixer-service'], cwd=ROOT/'services')
    identities['service'] = {'sourcePath': 'services/cmd/mixer-service', 'sha256': digest(executable)}
    server_env = dict(env, MIXER_SERVICE_CONFIG=str(folder/'service.json'))
    log = open(folder/'server.log', 'w+')
    server = subprocess.Popen([str(executable)], env=server_env, stdout=log, stderr=log)
    token = (folder/'admin.token').read_text()
    base = f'http://127.0.0.1:{port}'

    def request(method, path, body=None, key=None, auth=True, expected=200):
        check(server.poll() is None, 'Owned local service exited')
        check(path.startswith('/v1/'), 'Unexpected non-versioned or external delivery URL')
        headers = {}
        if auth:
            headers['Authorization'] = 'Bearer '+token
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if key:
            headers['Idempotency-Key'] = key
        req = urllib.request.Request(base+path, data=body, method=method, headers=headers)
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=5) as response:
                status = response.status
                data = response.read(24*1024*1024+1)
        except urllib.error.HTTPError as error:
            status = error.code
            data = error.read(24*1024*1024+1)
        check(len(data) <= 24*1024*1024, 'HTTP response exceeds integration limit')
        check(status == expected, (method, path, status, data[:300]))
        return strict_json(data) if data else None

    results = []
    try:
        ready = False
        for _ in range(100):
            check(server.poll() is None, 'Local service exited at startup')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.1):
                    ready = True
                    break
            except OSError:
                time.sleep(.05)
        check(ready, 'Local service did not listen within startup deadline')
        prefix = '/v1/orgs/integration/projects/fieldlog'
        request('GET', prefix+'/audit', auth=False, expected=401)
        request('GET', '/v1/orgs/other/projects/fieldlog/audit', expected=403)
        for platform in ('ios', 'android'):
            artifact_digest = (folder/f'{platform}-digest').read_text()
            host = strict_json((folder/f'{platform}-host.json').read_text())
            body = (folder/f'{platform}-upload.json').read_bytes()
            first = request('PUT', prefix+'/artifacts/'+artifact_digest, body,
                            'upload-'+platform, expected=201)
            check(request('PUT', prefix+'/artifacts/'+artifact_digest, body,
                          'upload-'+platform, expected=201) == first, 'Retry response changed')
            request('PUT', prefix+'/artifacts/'+artifact_digest, body+b' ',
                    'upload-'+platform, expected=409)
            validated = request('POST', prefix+'/releases/validate',
                                json.dumps({'artifact_sha256': artifact_digest}).encode(), 'validate-'+platform)
            check(validated['protocol_valid'] is True and validated['compiler_eligibility_verified'] is False,
                  'Server overstated protocol/compiler qualification')
            published = request('POST', prefix+'/channels/internal/publish',
                                (folder/f'{platform}-publish.json').read_bytes(), 'publish-'+platform)
            check(published['delivery'] == 'local_only', 'Unexpected nonlocal publication')
            query = urllib.parse.urlencode(dict(host['scope'], runtime=host['runtime'],
                                               channel='internal', installation='integration-install'))
            offered = request('GET', '/v1/updates?'+query, auth=False)
            artifact = request('GET', offered['artifact_url'], auth=False)
            (folder/'downloaded-manifest.json').write_text(json.dumps(artifact['signed_manifest']))
            (folder/'downloaded-assignment.json').write_text(json.dumps(offered['signed_assignment']))
            payload = base64.b64decode(artifact['payload'], validate=True)
            check(payload == (folder/'payload.wasm').read_bytes(), 'Public payload differs from uploaded fixture')
            (folder/'downloaded.wasm').write_bytes(payload)
            args = [tools['cli'], 'update', 'verify', '--manifest', folder/'downloaded-manifest.json',
                    '--payload', folder/'downloaded.wasm', '--host', folder/f'{platform}-host.json',
                    '--roots', folder/f'{platform}-roots.json', '--assignment', folder/'downloaded-assignment.json',
                    '--channel', 'internal', '--installation', 'integration-install', '--last-sequence', '0',
                    '--now', '1792627300']
            verified = strict_json(command(args, env=env))
            check(verified['status'] == 'local-candidate-verified' and verified['policyApproved'] is False
                  and verified['published'] is False, 'Invalid candidate qualification boundary')
            check(verified['linkedProtocolVerification']['artifactSHA256'] == artifact_digest,
                  'CLI did not bind the actual immutable artifact')
            check(verified['protocolTool']['sha256'] == identities['verifier']['sha256']
                  and verified['executableTool']['sha256'] == identities['vm']['sha256'], 'CLI tool provenance mismatch')
            replay = list(args)
            replay[replay.index('--last-sequence')+1] = '1'
            rejected = strict_json(command(replay, expected=1, env=env))
            check(rejected['status'] == 'protocol-rejected' and rejected.get('executableVerification') is None,
                  'Replay reached executable validation')
            # Signed payload that fits the VM default but exceeds signed memory.
            budget = list(args)
            for flag, name in [('--manifest', f'{platform}-budget-manifest.json'),
                               ('--payload', f'{platform}-budget.wasm'),
                               ('--assignment', f'{platform}-budget-assignment.json')]:
                budget[budget.index(flag)+1] = folder/name
            budget_report = strict_json(command(budget, expected=2, env=env))
            check(budget_report['status'] == 'executable-rejected'
                  and budget_report['linkedProtocolVerification'] is not None, 'Signed memory ceiling was ignored')
            output = strict_json(command([tools['vm'], 'invoke', folder/'downloaded.wasm',
                                         'completion', 'i32:1', 'i32:2'], env=env))
            check(output['ok'] is True and output['result'] == {'type': 'i32', 'value': 5000}, output)
            empty = strict_json(command([tools['vm'], 'invoke', folder/'downloaded.wasm',
                                        'completion', 'i32:0', 'i32:0'], env=env))
            check(empty['ok'] is True and empty['result'] == {'type': 'i32', 'value': 0}, empty)
            (folder/'downloaded.wasm').write_bytes(b'unverified replacement')
            tampered = strict_json(command(args, expected=1, env=env))
            check(tampered['status'] == 'protocol-rejected' and tampered.get('executableVerification') is None,
                  'Tampered payload reached executable validation')
            results.append({'platform': platform, 'artifactSHA256': artifact_digest,
                            'httpUploadRetry': 'same-result', 'changedIdempotencyBody': 'rejected',
                            'serverPolicyApproved': False, 'linkedSwiftAndOwnedVMValidation': 'passed',
                            'replay': 'rejected', 'signedMemoryBudget': 'enforced', 'modelExecution': output})
        for name, path in tools.items():
            check(digest(path) == identities[name]['sha256'], 'Frozen executable changed during run')
        check(server.poll() is None, 'Owned local service exited before receipt completion')
        print(json.dumps({'schema': 2, 'status': 'passed',
                          'scope': 'local HTTP release -> linked Swift verifier -> trusted local owned integer VM; no full Swift, device OTA or hosted qualification',
                          'executables': identities, 'sourceBuildCorrespondence': 'Existing CLI/Swift/VM executables were snapshotted; this script does not attest their source-build correspondence or sandbox malicious local tools.',
                          'commands': commands,
                          'harnessSHA256': {str(path.relative_to(ROOT)): digest(path) for path in [Path(__file__), ROOT/'tests/integration/release_fixture.go', ROOT/'compiler/qualification_support.py']},
                          'ambientToolOverrides': 'ignored; explicit private executable snapshots are forced',
                          'authorization': 'unauthenticated admin and cross-tenant reads rejected', 'platforms': results}, indent=2))
    finally:
        server.terminate()
        try:
            server.wait(timeout=12)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
        log.close()
