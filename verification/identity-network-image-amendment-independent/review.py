#!/usr/bin/env python3
"""Independent bounded source joins and pure decisions; no image execution."""
import ast
import base64
import copy
import difflib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import signal
import subprocess
import sys
import time
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/identity-network-image-amendment-v1'
META = PACKET / 'metadata'
REVIEW = META / 'source-review'
OLD = ROOT / 'verification/identity-production-network-contract'
PATHS = ['hosted/scripts/test-identity-network.py', 'hosted/scripts/test_identity_network_collector.py', '.github/workflows/identity-network.yml', 'docs/hosted-identity-production-network-ci-contract.md', 'THIRD_PARTY.yml']
def row(body): return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
def digest(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def put(name, value): (OUT/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def packet(base, count, tree, outside_seal=()):
    raw = (base/'packet-manifest.json').read_bytes()
    seal = json.loads(raw)
    assert len(seal['files']) == count and seal['tree_digest_sha256'] == tree and digest(seal['files']) == tree
    actual = {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()}
    assert actual == set(seal['files']) | {'packet-manifest.json'} | set(outside_seal)
    for path, expected in seal['files'].items():
        assert not (base/path).is_symlink() and row((base/path).read_bytes()) == expected, path
    return {'files': count, 'tree_digest_sha256': tree, 'manifest': row(raw), 'outside_seal_not_admitted': list(outside_seal)}
def literal(source, name):
    return next(ast.literal_eval(n.value) for n in ast.parse(source).body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
def methods(source):
    return {c.name+'.'+f.name: ast.get_source_segment(source, f) for c in ast.parse(source).body if isinstance(c, ast.ClassDef) for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith('test_')}

started = time.monotonic()
source = (ROOT/PATHS[0]).read_text()
before = (PACKET/'implementation/before'/PATHS[0]).read_text()
pins = {p: row((ROOT/p).read_bytes()) for p in PATHS}
assert pins == json.loads((PACKET/'implementation/source-bindings.json').read_bytes())
assert pins[PATHS[0]]['sha256'] == '7ea70a4802f8053e448566da41f3f72a8a0dad4f3152c13471ec2b8e498a6a7d'
assert pins[PATHS[1]]['sha256'] == 'a5f3ebfd7dea80e5892e448a1a85c28affe6b3e695f6a579b96ecdd65f625727'
assert digest(pins) == 'bb21492941740aed5ed9202f8aa744461ed1c90be582da5b4b03ea7cabafc773'
for p in PATHS: assert (ROOT/p).read_bytes() == (PACKET/'implementation/after'/p).read_bytes()
seals = {
    'producer': packet(PACKET, 110, 'c6116eb09de8bdd75ac3f3036c469efed7e11f6beef4210e9577ff9b72cd392c'),
    'metadata': packet(META, 78, '9ddc12c8277b120dcd8ef7577dd9da03d245b8502802db85399a6f1104bcbdc8'),
    'source_review': packet(REVIEW, 71, '261023b77cb55255f666959f367330783a354174252ed23b71145566f87ba597'),
    'predecessor': packet(OLD, 46, 'a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d', ('offline-audit.json',)),
}
original_review = ROOT/'verification/identity-network-image-prerequisite-review'
for p in REVIEW.rglob('*'):
    if p.is_file(): assert p.read_bytes() == (original_review/p.relative_to(REVIEW)).read_bytes()
amendment = json.loads((META/'image-amendment.json').read_bytes())
assert row((META/'image-amendment.json').read_bytes())['sha256'] == '6a2ec88721d89a28e40961f834b856598ba0f6f14d88708906cf3931e0e33afa'

# Independently bind all three OCI index -> AMD64 child -> config relationships.
oci = []
for base, name, identity in [(OLD, 'elixir', amendment['old_test_image']), (OLD, 'postgres', amendment['preserved']['postgres']), (META, 'elixir', amendment['test_image'])]:
    data = [(base/'inputs/registry'/f'{name}{suffix}.json').read_bytes() for suffix in ['-index', '-amd64-manifest', '-amd64-config']]
    for body, pin in zip(data, [identity['index'], identity['ref'].split('@')[1], identity['config']]): assert 'sha256:'+row(body)['sha256'] == pin
    index, child, config = map(json.loads, data)
    matches = [m for m in index['manifests'] if m.get('platform') == {'architecture':'amd64', 'os':'linux'}]
    assert len(matches) == 1 and matches[0]['digest'] == identity['ref'].split('@')[1]
    assert matches[0]['size'] == len(data[1]) and child['config']['digest'] == identity['config'] and child['config']['size'] == len(data[2])
    assert (config['os'], config['architecture']) == ('linux', 'amd64')
    oci.append(identity)

# Join retained layer observations to immutable manifest and config, then replay
# the inventory overlay in memory. Blob SHA calculations are prior evidence;
# no deleted blob is redownloaded or represented as freshly hashed here.
inspection = json.loads((REVIEW/'layer-inspection.json').read_bytes())
child = json.loads((META/'inputs/registry/elixir-amd64-manifest.json').read_bytes())
config = json.loads((META/'inputs/registry/elixir-amd64-config.json').read_bytes())
layers = [r for r in inspection['layers'] if r['label'].startswith('bookworm-')]
assert len(layers) == len(child['layers']) == len(config['rootfs']['diff_ids']) == 4
merged = {}
for observed, expected, diff in zip(layers, child['layers'], config['rootfs']['diff_ids']):
    assert 'sha256:'+observed['compressed_sha256'] == expected['digest'] and observed['compressed_bytes'] == expected['size'] and observed['uncompressed_diff_id'] == diff
    raw = (REVIEW/observed['inventory']).read_bytes()
    assert row(raw) == {'bytes': observed['inventory_bytes'], 'sha256': observed['inventory_sha256']}
    rows = list(map(json.loads, raw.splitlines())); assert len(rows) == observed['members']
    for item in observed['selected_text']: assert row((REVIEW/item['retained']).read_bytes()) == {k:item[k] for k in ['bytes','sha256']}
    for entry in rows:
        path = entry['path']; leaf = PurePosixPath(path).name
        if leaf == '.wh..wh..opq':
            prefix = str(PurePosixPath(path).parent).rstrip('/')+'/'
            merged = {p:v for p,v in merged.items() if not p.startswith(prefix)}
        elif leaf.startswith('.wh.'):
            deleted = str(PurePosixPath(path).with_name(leaf[4:]))
            merged = {p:v for p,v in merged.items() if p != deleted and not p.startswith(deleted+'/')}
        else:
            if entry['type'] != '5': merged = {p:v for p,v in merged.items() if not p.startswith(path+'/')}
            merged[path] = dict(entry, layer=observed['label'])
retained = {r['path']:r for r in map(json.loads, (REVIEW/'inputs/layers/bookworm-merged-inventory.jsonl').read_bytes().splitlines())}
assert merged == retained

def resolve(requested):
    path = posixpath.normpath('/'+requested.lstrip('/'))
    for _ in range(64):
        parts = path.lstrip('/').split('/')
        for i in range(1,len(parts)+1):
            prefix='/'.join(parts[:i]); entry=merged.get(prefix)
            if entry and entry['type']=='2':
                target=entry['linkname'] if entry['linkname'].startswith('/') else posixpath.join('/',posixpath.dirname(prefix),entry['linkname'])
                path=posixpath.normpath(posixpath.join(target,*parts[i:])); break
        else:
            entry=merged[path.lstrip('/')]
            if entry['type']=='1': path='/'+entry['linkname'].lstrip('/'); continue
            return path,entry
    raise AssertionError('link-depth')
caps = json.loads((REVIEW/'analysis/capabilities.json').read_bytes())
for expected in caps['required_objects']:
    path,entry=resolve(expected['requested']); assert path == expected['resolved'] and entry == expected['object']
for path, expected in amendment['prerequisites']['tools'].items():
    _,entry=resolve(path); assert entry['type']=='0' and int(entry['mode'],8)&0o111 and {k:entry[k] for k in ['bytes','sha256']}==expected
static=caps['static_elf_dependency_objects']; assert len(static)==20
for path,expected in static.items():
    _,entry=resolve(path); assert entry['sha256']==expected['sha256'] and entry['elf']==expected['elf'] and entry['elf']['machine']==62
    for dep in expected['dependencies']:
        _,target=resolve(dep['resolved']); assert target['sha256']==dep['sha256'] and dep['resolved'] in static
ca_path='inputs/layers/selected-text/bookworm-runtime-packages/etc__ssl__certs__ca-certificates.crt'
ca=(REVIEW/ca_path).read_bytes(); expected_ca=amendment['prerequisites']['ca']
assert row(ca)=={k:expected_ca[k] for k in ['bytes','sha256']}
der=[]
for pem in ca.split(b'-----BEGIN CERTIFICATE-----')[1:]:
    encoded, tail=pem.split(b'-----END CERTIFICATE-----',1)
    der.append(hashlib.sha256(base64.b64decode(b''.join(encoded.split()), validate=True)).hexdigest())
assert len(der)==len(set(der))==150 and sorted(der)==expected_ca['der_sha256']==sorted(r['der_sha256'] for r in caps['ca_bundle']['certificates'])
status=(REVIEW/'inputs/layers/selected-text/bookworm-runtime-packages/var__lib__dpkg__status').read_text()
packages={}
for stanza in status.split('\n\n'):
    fields=dict(line.split(': ',1) for line in stanza.splitlines() if ': ' in line and not line.startswith(' '))
    if fields.get('Package'): packages[fields['Package']]=fields
for entry in caps['package_source_inventory']: assert all(packages[entry['Package']][k]==v for k,v in entry.items())

# The old tests and all isolation mechanisms stay identical; only named
# collector admission, image and prerequisite sections change.
oldmethods=methods((PACKET/'implementation/before'/PATHS[1]).read_text()); newmethods=methods((ROOT/PATHS[1]).read_text())
assert len(oldmethods)==68 and len(newmethods)==84 and all(newmethods[k]==v for k,v in oldmethods.items())
oldtree=ast.parse(before); newtree=ast.parse(source)
olddefs={n.name:ast.get_source_segment(before,n) for n in oldtree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
newdefs={n.name:ast.get_source_segment(source,n) for n in newtree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
changeddefs=[k for k,v in olddefs.items() if newdefs[k]!=v]; assert changeddefs==['Collector']
oldc=next(n for n in oldtree.body if isinstance(n,ast.ClassDef) and n.name=='Collector'); newc=next(n for n in newtree.body if isinstance(n,ast.ClassDef) and n.name=='Collector')
newcm={n.name:ast.get_source_segment(source,n) for n in newc.body if isinstance(n,ast.FunctionDef)}
changedcm=[n.name for n in oldc.body if isinstance(n,ast.FunctionDef) and ast.get_source_segment(before,n)!=newcm[n.name]]; assert changedcm==['collect']
for name in ['FROZEN_MANIFEST','FROZEN_LOCK_SHA256','FROZEN_PRODUCT_DIGEST','PRODUCT_COMMIT','BOOTSTRAP','TEST_ROOTS','BASE_ENV','MANIFEST_EXS','NETNS_EXS','OBSERVER_EXS']: assert literal(before,name)==literal(source,name),name
workflow=(ROOT/PATHS[2]).read_text(); oldworkflow=(PACKET/'implementation/before'/PATHS[2]).read_text()
assert workflow.replace("      - 'verification/identity-network-image-amendment-v1/**'\n",'').replace('            /verification/identity-network-image-amendment-v1/metadata/**\n','')==oldworkflow
assert workflow.count("      - 'verification/identity-network-image-amendment-v1/**'")==2
assert workflow.count('            /verification/identity-network-image-amendment-v1/metadata/**')==1
oldinv=(PACKET/'implementation/before/THIRD_PARTY.yml').read_text(); newinv=(ROOT/'THIRD_PARTY.yml').read_text()
prefix,suffix=oldinv.split('# Selected by',1); assert newinv.startswith(prefix) and newinv.endswith('# Selected by'+suffix)
assert newinv[len(prefix):-len('# Selected by'+suffix)].count('  - name:')==6
for entry in caps['package_source_inventory']: assert entry['Version'] in newinv

# Read committed product blobs without index mutation; working store is separate.
head=subprocess.run(['git','--no-replace-objects','rev-parse','HEAD','HEAD^{tree}'],cwd=ROOT,check=True,capture_output=True,timeout=5).stdout.decode().splitlines()
manifest=literal(source,'FROZEN_MANIFEST'); assert len(manifest)==177
raw=subprocess.run(['git','--no-replace-objects','cat-file','--batch'],cwd=ROOT,input=''.join(head[0]+':'+p+'\n' for p in sorted(manifest)).encode(),check=True,capture_output=True,timeout=10).stdout
offset=0; observed={}
for p in sorted(manifest):
    end=raw.index(b'\n',offset); header=raw[offset:end].split(); assert len(header)==3 and header[1]==b'blob'; count=int(header[2]); body=raw[end+1:end+1+count]; assert raw[end+1+count:end+2+count]==b'\n'; offset=end+2+count; observed[p]=row(body)
assert offset==len(raw) and observed==manifest and digest(observed)=='023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
protected={p:row((ROOT/p).read_bytes()) for p in ['.github/workflows/hosted.yml','hosted/lib/mixer_hosted/browser_auth/store.ex']}
assert protected['.github/workflows/hosted.yml']['sha256']=='fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57'
assert protected['hosted/lib/mixer_hosted/browser_auth/store.ex']['sha256']=='8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'
put('source-checks.json',{'status':'pass','HEAD':head[0],'git_tree':head[1],'python':sys.version,'seals':seals,'canonical':pins,'canonical_digest':digest(pins),'frozen_product_files':177,'frozen_product_digest':digest(observed),'original_test_bodies_unchanged':68,'total_test_methods':84,'retained_layer_joins':4,'merged_members':len(merged),'exact_tool_objects':7,'static_ELF_objects':20,'ca_der_hashes':150,'preserved_methods_except':['Collector.collect'],'inventory_added_entries':6,'protected_live':protected,'elapsed_seconds':time.monotonic()-started})

# One fresh complete guarded control-suite execution, with the suite's own
# 50-second alarm and an independent 55-second parent timeout.
start=time.monotonic()
result=subprocess.run([sys.executable,'-B',str(ROOT/PATHS[1])],cwd=ROOT,capture_output=True,timeout=55)
(OUT/'controls.stdout').write_bytes(result.stdout); (OUT/'controls.stderr').write_bytes(result.stderr)
put('controls-result.json',{'argv':[sys.executable,'-B',PATHS[1]],'timeout_seconds':55,'inner_alarm_seconds':50,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-start,'python':sys.version,'stdout':row(result.stdout),'stderr':row(result.stderr)})
assert result.returncode==0 and b'Ran 84 tests' in result.stderr and result.stderr.rstrip().endswith(b'OK')

# Focused independent mutations cover JSON type confusion and old-namespace
# re-sealing, beyond the producer suite. No subprocess/socket is available.
signal.alarm(15)
spec=importlib.util.spec_from_file_location('independent_controls',ROOT/PATHS[1]); module=importlib.util.module_from_spec(spec)
guards=[mock.patch(t,side_effect=AssertionError('external operation forbidden')) for t in ['subprocess.Popen','os.system','socket.socket','socket.create_connection']]
for g in guards:g.start()
try:
    spec.loader.exec_module(module); c=module.collector
    metadata=module.exact_metadata(); c.validate_selected_metadata(metadata)
    base,expected=module.exact_prerequisites(); c.validate_prerequisites(base,expected)
    cases=[]
    for name,path,value in [('crypto-bool',['crypto_libraries',0,'number'],False),('crypto-float',['crypto_libraries',0,'number'],805306720.0),('ca-float-bytes',['ca','bytes'],224449.0),('ca-float-count',['ca','loaded_count'],150.0),('ca-null-roots',['ca','loaded_der_sha256'],None),('ca-duplicate-root',['ca','loaded_der_sha256'],[expected['ca']['der_sha256'][0]]*150),('tools-null',['tools'],None),('tool-float-bytes',['tools','/usr/bin/env','bytes'],48536.0),('tool-extra',['tools','/unselected/tool'],{'bytes':1,'sha256':'0'*64}),('versions-null',['versions'],None),('extra-result',['unexpected'],True)]:
        valuecopy=copy.deepcopy(base); cursor=valuecopy
        for k in path[:-1]: cursor=cursor[k]
        cursor[path[-1]]=value
        try:c.validate_prerequisites(valuecopy,expected)
        except c.CollectorError:cases.append(name)
        else:raise AssertionError('accepted '+name)
    for name in ['old-packet-reseal','new-index-swap','extra-old-namespace']:
        values=dict(metadata)
        if name=='old-packet-reseal':
            p=c.CONTRACT_BASE+'packet-manifest.json'; seal=json.loads(values[p]); seal['files']['contract.json']['sha256']='0'*64; seal['tree_digest_sha256']=digest(seal['files']); values[p]=json.dumps(seal).encode()
        elif name=='new-index-swap': values[c.AMENDMENT_BASE+'inputs/registry/elixir-index.json']=values[c.CONTRACT_BASE+'inputs/registry/elixir-index.json']
        else:values[c.CONTRACT_BASE+'override.json']=b'{}'
        try:c.validate_selected_metadata(values)
        except c.CollectorError:cases.append(name)
        else:raise AssertionError('accepted '+name)
    put('focused-decisions.json',{'status':'pass','positive_cases':2,'negative_cases':cases,'negative_count':len(cases),'guards':['subprocess.Popen','os.system','socket.socket','socket.create_connection'],'alarm_seconds':15,'scope':'pure Python decisions, not runtime observations'})
finally:
    for g in reversed(guards):g.stop()
    signal.alarm(0)
assert pins=={p:row((ROOT/p).read_bytes()) for p in PATHS}
assert protected=={p:row((ROOT/p).read_bytes()) for p in protected}
print(json.dumps({'status':'pass','seals':seals,'controls':84,'focused_negative_decisions':len(cases),'protected_unchanged':True,'scope':'source and pure Python only'},indent=2))
