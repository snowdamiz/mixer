#!/usr/bin/env python3
"""Real local HTTP + Swift crypto + owned VM integration. Never production."""
from pathlib import Path
import base64, hashlib, json, os, socket, subprocess, tempfile, time, urllib.error, urllib.parse, urllib.request

ROOT = Path(__file__).resolve().parents[2]
executables = [ROOT/'cli/.build/debug/mixer', ROOT/'updates/.build/debug/mixer-update', ROOT/'vm/target/release/mixer-vm']
binary_digests = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in executables}

def command(args, cwd=ROOT, expected=0):
    result = subprocess.run([str(x) for x in args], cwd=cwd, text=True, capture_output=True, timeout=180)
    if result.returncode != expected:
        raise AssertionError(f"Command {args[0]} exited {result.returncode}: {result.stdout[-2500:]} {result.stderr[-2500:]}")
    return result.stdout

with tempfile.TemporaryDirectory(prefix='mixer-release-e2e-') as temporary:
    folder = Path(temporary)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    command(['go', 'run', ROOT/'tests/integration/release_fixture.go', folder, f'127.0.0.1:{port}'], cwd=ROOT/'services')
    executable = folder/'mixer-service'
    command(['go','build','-o',executable,'./cmd/mixer-service'],cwd=ROOT/'services')
    env = dict(os.environ, MIXER_SERVICE_CONFIG=str(folder/'service.json'))
    log = open(folder/'server.log','w+')
    server = subprocess.Popen([str(executable)],env=env,stdout=log,stderr=log)
    token = (folder/'admin.token').read_text()
    base = f'http://127.0.0.1:{port}'
    def request(method,path,body=None,key=None,auth=True,expected=200):
        headers={}
        if auth: headers['Authorization']='Bearer '+token
        if body is not None: headers['Content-Type']='application/json'
        if key: headers['Idempotency-Key']=key
        req=urllib.request.Request(base+path,data=body,method=method,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=5) as response: status=response.status;data=response.read()
        except urllib.error.HTTPError as error: status=error.code;data=error.read()
        assert status==expected,(method,path,status,data[:300])
        return json.loads(data) if data else None
    results=[]
    try:
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.1): break
            except OSError:
                if server.poll() is not None: raise AssertionError('Local service exited at startup')
                time.sleep(.05)
        for platform in ('ios','android'):
            digest=(folder/f'{platform}-digest').read_text()
            host=json.loads((folder/f'{platform}-host.json').read_text())
            prefix='/v1/orgs/integration/projects/fieldlog'
            body=(folder/f'{platform}-upload.json').read_bytes()
            first=request('PUT',prefix+'/artifacts/'+digest,body,'upload-'+platform,expected=201)
            assert request('PUT',prefix+'/artifacts/'+digest,body,'upload-'+platform,expected=201)==first
            validated=request('POST',prefix+'/releases/validate',json.dumps({'artifact_sha256':digest}).encode(),'validate-'+platform)
            assert validated['protocol_valid'] and not validated['compiler_eligibility_verified']
            published=request('POST',prefix+'/channels/internal/publish',(folder/f'{platform}-publish.json').read_bytes(),'publish-'+platform)
            assert published['delivery']=='local_only'
            query=urllib.parse.urlencode(dict(host['scope'],runtime=host['runtime'],channel='internal',installation='integration-install'))
            offered=request('GET','/v1/updates?'+query,auth=False)
            artifact=request('GET',offered['artifact_url'],auth=False)
            (folder/'downloaded-manifest.json').write_text(json.dumps(artifact['signed_manifest']))
            (folder/'downloaded-assignment.json').write_text(json.dumps(offered['signed_assignment']))
            (folder/'downloaded.wasm').write_bytes(base64.b64decode(artifact['payload']))
            args=[ROOT/'cli/.build/debug/mixer','update','verify','--manifest',folder/'downloaded-manifest.json','--payload',folder/'downloaded.wasm','--host',folder/f'{platform}-host.json','--roots',folder/f'{platform}-roots.json','--assignment',folder/'downloaded-assignment.json','--channel','internal','--installation','integration-install','--last-sequence','0','--now','1792627300']
            verified=json.loads(command(args));assert verified['status']=='local-candidate-verified'
            replay=list(args); replay[replay.index('--last-sequence')+1]='1'
            replay_result=json.loads(command(replay,expected=1))
            assert replay_result['status']=='protocol-rejected' and replay_result.get('executableVerification') is None,replay_result
            output=json.loads(command([ROOT/'vm/target/release/mixer-vm','invoke',folder/'downloaded.wasm','completion','i32:1','i32:2']))
            assert output['ok'] and output['result']=={'type':'i32','value':5000},output
            empty=json.loads(command([ROOT/'vm/target/release/mixer-vm','invoke',folder/'downloaded.wasm','completion','i32:0','i32:0']))
            assert empty['ok'] and empty['result']=={'type':'i32','value':0},empty
            (folder/'downloaded.wasm').write_bytes(b'unverified replacement')
            tampered=json.loads(command(args,expected=1))
            assert tampered['status']=='protocol-rejected' and tampered.get('executableVerification') is None,tampered
            results.append({'platform':platform,'artifactSHA256':digest,'httpUploadRetry':'same-result','serverPolicyApproved':False,'swiftAndOwnedVMValidation':'passed','replay':'rejected','modelExecution':output})
        assert binary_digests == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in executables}, 'Verification executables changed during the run'
        print(json.dumps({'schema':1,'status':'passed','scope':'local HTTP release -> Swift verifier -> owned integer VM; no full Swift, device OTA or hosted qualification','executables':binary_digests,'platforms':results},indent=2))
    finally:
        server.terminate()
        try:server.wait(timeout=12)
        except subprocess.TimeoutExpired:server.kill();server.wait()
        log.close()
