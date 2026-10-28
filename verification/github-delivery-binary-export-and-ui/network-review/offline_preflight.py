#!/usr/bin/env python3
"""Offline readset binding only; never execute collector or product code."""
import ast, datetime, hashlib, json, platform, signal, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SHA = '56ff14c925168284761c5aca4f0bd4129cf3c995'
TREE = '75989099938ed5256c4144cbc9e62979ee323183'
def timeout(*_): raise TimeoutError('offline preflight exceeded 40 seconds')
signal.signal(signal.SIGALRM, timeout)
signal.alarm(40)
def binding(data): return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def git(*args):
    return subprocess.run(['git','--no-replace-objects',*args],cwd=REPO,capture_output=True,check=True,timeout=15).stdout
assert git('rev-parse',SHA+'^{tree}').decode().strip()==TREE
selection=json.loads((REPO/'verification/console-session-and-checkout-root-review/identity-network-binary-selection.json').read_bytes())
selected={row['path']:{k:row[k] for k in ('bytes','sha256')} for row in selection['canonical_sources']}
controls={}
for path,expected in selected.items():
    body=git('show',SHA+':'+path)
    assert binding(body)==expected and (REPO/path).read_bytes()==body
    controls[path]=body
constants={}
for node in ast.parse(controls['hosted/scripts/test-identity-network.py']).body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        try: constants[node.targets[0].id]=ast.literal_eval(node.value)
        except (ValueError,TypeError): pass
frozen=constants['FROZEN_MANIFEST']
assert len(frozen)==177
canonical=json.dumps(frozen,sort_keys=True,separators=(',',':')).encode()
assert hashlib.sha256(canonical).hexdigest()==constants['FROZEN_PRODUCT_DIGEST']=='023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
for path,expected in frozen.items():
    current=git('show',SHA+':'+path)
    assert binding(current)==expected and current==git('show',constants['PRODUCT_COMMIT']+':'+path)
protected={'.github/workflows/hosted.yml':'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57','hosted/lib/mixer_hosted/browser_auth/store.ex':'8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
for path,expected in protected.items(): assert binding((REPO/path).read_bytes())['sha256']==expected
prior=REPO/'verification/github-delivery-runtime-followup/network-review/packet-manifest.json'
assert binding(prior.read_bytes())['sha256']=='4ccc5ebe10600086473c96afd9aabf68ed63c46068419f5e599ac747f0d1800c'
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'offline-readset-ready-awaiting-root-run-id','source_revision':SHA,'source_tree':TREE,'controls':selected,'product_files':len(frozen),'product_digest':constants['FROZEN_PRODUCT_DIGEST'],'product_original_commit':constants['PRODUCT_COMMIT'],'protected_live_sources':protected,'prior_packet_manifest':binding(prior.read_bytes()),'python':platform.python_version(),'git':git('--version').decode().strip(),'reviewer':{'model':'gpt-6-astra','reasoning_effort':'xhigh'},'github_api_calls':0,'actual_runtime_acceptance':False,'command':'python3 -B verification/github-delivery-binary-export-and-ui/network-review/offline_preflight.py','alarm_seconds':40,'git_call_timeout_seconds':15,'script':binding(Path(__file__).read_bytes()),'constraints':['only owned network-review writes','no local compiler, Docker, PG, native, UI or capture','no held process or private FieldLog probes','no dispatch, rerun, canonical edits, commit or push']}
with (HERE/'offline-preflight.json').open('x') as f: f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':result['status'],'product_files':len(frozen),'selected_sources':len(selected),'protected_sources_unchanged':True}))
