#!/usr/bin/env python3
"""Bounded offline evidence join; never executes product, collector or archive code."""
import ast, datetime, hashlib, io, json, platform, re, signal, stat, subprocess, tarfile, zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SHA = 'fb7c7f20f8a308424ef4b7092d19d3d4de2c7627'
TREE = '509093e0fcc9f4c83583f8d0ecd61b8b3c9d83d4'
CAP = 256 * 1024 * 1024
CONTROL_PATHS = ['hosted/scripts/test-identity-network.py', 'hosted/scripts/test_identity_network_collector.py', 'docs/hosted-identity-production-network-ci-contract.md', '.github/workflows/identity-network.yml']
EXPECTED_CONTROL_SHA = ['c3defc87beeda3ccd1f6fbfbdf190c8eb6ca2715823ccdbddc36c877813fcc7f', 'aafc29738f3b25f1c04c58f15a4fadd8ee920fb8c2b06c2c59ef91cd55128222', '0b8890b678750f95cf9eaaaad71dae9096d741eb8e41db081c649bca39a730f5', '4b5fa14bfa80601354bd063f3e93f728fa1175e52de3d5c6bcc62a99b044eb19']

def deadline(*_): raise TimeoutError('offline review 50 second bound')
signal.signal(signal.SIGALRM, deadline)
signal.alarm(50)
def digest(b): return hashlib.sha256(b).hexdigest()
def binding(b): return {'bytes':len(b), 'sha256':digest(b)}
def canonical(v): return json.dumps(v, sort_keys=True, separators=(',', ':')).encode()
def put(name, value):
    with (ROOT/name).open('x') as f: f.write(json.dumps(value, indent=2, sort_keys=True)+'\n')
def safe_name(name):
    assert isinstance(name,str) and name and not name.startswith('/') and '\\' not in name and ':' not in name and '\x00' not in name
    assert all(p not in ('','.','..') for p in name.split('/')) and str(PurePosixPath(name)) == name
def safe_tar(raw):
    result, folded, total = {}, set(), 0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
        for member in archive.getmembers():
            safe_name(member.name)
            assert member.name not in result and member.name.casefold() not in folded
            assert member.isfile() and not member.linkname and not member.pax_headers and 0 <= member.size <= CAP
            total += member.size; assert total <= CAP
            body=archive.extractfile(member).read(CAP+1); assert len(body)==member.size
            result[member.name]=body; folded.add(member.name.casefold())
    return result
def git_blobs(rev, paths):
    request=''.join(rev+':'+p+'\n' for p in paths).encode()
    run=subprocess.run(['git','--no-replace-objects','cat-file','--batch'],input=request,cwd=REPO,capture_output=True,timeout=20,check=True)
    assert not run.stderr and len(run.stdout)<=CAP
    cursor,result=0,{}
    for path in paths:
        end=run.stdout.index(b'\n',cursor); oid,kind,size=run.stdout[cursor:end].split()
        assert kind==b'blob' and re.fullmatch(b'[0-9a-f]{40}',oid)
        cursor=end+1; body=run.stdout[cursor:cursor+int(size)]
        assert len(body)==int(size) and hashlib.sha1(b'blob '+size+b'\x00'+body).hexdigest().encode()==oid
        result[path]=body; cursor+=int(size); assert run.stdout[cursor:cursor+1]==b'\n'; cursor+=1
    assert cursor==len(run.stdout)
    return result,request,run.stdout
def retained(name, body):
    safe_name(name); path=ROOT/'selected'/name; path.parent.mkdir(parents=True,exist_ok=True)
    assert not path.exists() and not path.is_symlink()
    with path.open('xb') as f: f.write(body)

data=(ROOT/'artifact.zip').read_bytes()
assert len(data)==2913212 and len(data)<=64*1024*1024 and digest(data)=='f417f539debbe00a5a07933761ec6fac5653f794039cfff73328c4d4413f7c42'
members,folded,expanded={},set(),0
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    for item in archive.infolist():
        safe_name(item.filename)
        assert item.filename not in members and item.filename.casefold() not in folded
        assert not item.is_dir() and not item.flag_bits&1 and stat.S_IFMT(item.external_attr>>16) in (0,stat.S_IFREG)
        expanded+=item.file_size; assert 0<=item.file_size<=CAP and expanded<=CAP
        body=archive.read(item); assert len(body)==item.file_size
        members[item.filename]=body; folded.add(item.filename.casefold())
meta_names=['artifact-manifest.json','bootstrap-observed.json','bootstrap-plan.json','collector-source-bindings.json','collector-source.tar','finalizer.json','host.json','literal-helper-bindings.json','literal-helpers.tar','pg-image.json','prepare-mount-policy.json','prepare-prerequisites.json','prepare-terminal.json','product-source-manifest.json','selected-contract-metadata.tar','state.json','test-image.json']
expected=set(meta_names)|{f'logs/{n:04d}.{e}' for n in range(1,38) for e in ['json','stdout','stderr']}
expected.remove('logs/0028.stdout')
assert set(members)==expected and len(members)==127 and expanded==14297082
manifest=json.loads(members['artifact-manifest.json'])
observed={n:binding(b) for n,b in members.items() if n!='artifact-manifest.json'}
assert manifest['files']==observed and manifest['tree_digest_sha256']==digest(canonical(observed))=='055c62040b51a5e3c0243b64edc0e74980beab236bd7723bcf9de5c132d0f5fa'
controls,request3,output3=git_blobs(SHA,CONTROL_PATHS)
assert [digest(controls[p]) for p in CONTROL_PATHS]==EXPECTED_CONTROL_SHA
assert safe_tar(members['collector-source.tar'])==controls
assert json.loads(members['collector-source-bindings.json'])=={p:binding(b) for p,b in controls.items()}
constants={}
for node in ast.parse(controls[CONTROL_PATHS[0]]).body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        try: constants[node.targets[0].id]=ast.literal_eval(node.value)
        except (ValueError,TypeError): pass
frozen=constants['FROZEN_MANIFEST']; assert len(frozen)==177
assert json.loads(members['product-source-manifest.json'])==frozen and digest(canonical(frozen))==constants['FROZEN_PRODUCT_DIGEST']=='023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
product,request2,output2=git_blobs(SHA,sorted(frozen)); original,_,_=git_blobs(constants['PRODUCT_COMMIT'],sorted(frozen))
assert product==original and {p:binding(b) for p,b in product.items()}==frozen
oldbase=constants['CONTRACT_BASE']; imagebase=constants['AMENDMENT_BASE']; execbase=constants['EXECUTION_BASE']
packetpaths=[oldbase+'contract.json',oldbase+'packet-manifest.json']
for image in ['elixir','postgres']:
    packetpaths.extend(oldbase+'inputs/registry/'+image+s for s in ['-index.json','-amd64-manifest.json','-amd64-config.json'])
image_seal,request4,output4=git_blobs(SHA,[imagebase+'packet-manifest.json']); image_packet=json.loads(image_seal[imagebase+'packet-manifest.json'])
assert len(image_packet['files'])==78 and image_packet['tree_digest_sha256']==digest(canonical(image_packet['files']))==constants['AMENDMENT_PACKET']
image_files,request5,output5=git_blobs(SHA,packetpaths+[imagebase+p for p in image_packet['files']])
exec_seal,request6,output6=git_blobs(SHA,[execbase+'packet-manifest.json']); exec_packet=json.loads(exec_seal[execbase+'packet-manifest.json'])
assert digest(exec_seal[execbase+'packet-manifest.json'])==constants['EXECUTION_PACKET_SHA256']
assert len(exec_packet['files'])==16 and exec_packet['tree_digest_sha256']==digest(canonical(exec_packet['files']))==constants['EXECUTION_PACKET']
exec_files,request7,output7=git_blobs(SHA,[execbase+p for p in exec_packet['files']])
metadata={**image_seal,**image_files,**exec_seal,**exec_files}
assert len(metadata)==104 and safe_tar(members['selected-contract-metadata.tar'])==metadata
for base,packet in [(imagebase,image_packet),(execbase,exec_packet)]:
    for p,e in packet['files'].items(): assert binding(metadata[base+p])==e
oldpacket=json.loads(metadata[oldbase+'packet-manifest.json'])
assert digest(metadata[oldbase+'packet-manifest.json'])==constants['CONTRACT_PACKET_SHA256']
assert oldpacket['tree_digest_sha256']==digest(canonical(oldpacket['files']))==constants['CONTRACT_PACKET']
assert digest(metadata[oldbase+'contract.json'])==constants['CONTRACT_SHA256']
for p in packetpaths:
    if p!=oldbase+'packet-manifest.json': assert oldpacket['files'][p.removeprefix(oldbase)]==binding(metadata[p])
amendment=json.loads(metadata[imagebase+'image-amendment.json'])
assert digest(metadata[imagebase+'image-amendment.json'])==constants['AMENDMENT_SHA256']
assert digest(metadata[execbase+'execution-amendment.json'])==constants['EXECUTION_SHA256']
helpers={'collector-'+name+'.exs':constants[key].encode() for name,key in [('prerequisites','PREREQUISITES_EXS'),('bootstrap','BOOTSTRAP_EXS'),('manifest','MANIFEST_EXS'),('netns','NETNS_EXS'),('observer','OBSERVER_EXS'),('mounts','MOUNTS_EXS')]}
bootstrap=constants['BOOTSTRAP_EXS']
for placeholder,value in {'HEX_URL':constants['BOOTSTRAP']['hex']['url'],'HEX_SHA':constants['BOOTSTRAP']['hex']['sha512'],'REBAR_URL':constants['BOOTSTRAP']['rebar']['url'],'REBAR_SHA':constants['BOOTSTRAP']['rebar']['sha512']}.items(): bootstrap=bootstrap.replace(placeholder,value)
helpers['collector-bootstrap.exs']=bootstrap.encode(); helpers['frozen-manifest.json']=canonical(frozen)
assert safe_tar(members['literal-helpers.tar'])==helpers and json.loads(members['literal-helper-bindings.json'])=={p:binding(b) for p,b in helpers.items()}
state,finalizer,host=[json.loads(members[p]) for p in ['state.json','finalizer.json','host.json']]
run=json.loads((ROOT/'run-metadata.json').read_text()); artifact_meta=json.loads((ROOT/'artifact-metadata.json').read_text())['artifacts'][0]
assert run['id']==40746908101 and run['head_sha']==SHA and run['head_commit']['tree_id']==TREE and run['conclusion']=='failure' and run['run_attempt']==1
assert artifact_meta['id']==12842685657 and artifact_meta['workflow_run']['id']==run['id'] and artifact_meta['workflow_run']['head_sha']==SHA and artifact_meta['digest']=='sha256:'+digest(data)
assert state['sha']==SHA and state['run_id']=='40746908101' and state['attempt']=='1'
assert host['github_run_id']==state['run_id'] and host['attempt']=='1' and host['uname'][0]=='Linux' and host['uname'][-1]=='x86_64'
assert state['source']['delivery_revision']==SHA and state['source']['product_tree_digest_sha256']==constants['FROZEN_PRODUCT_DIGEST']
for field,key in [('image_amendment_sha256','AMENDMENT_SHA256'),('image_amendment_packet_sha256','AMENDMENT_PACKET'),('image_source_review_packet_sha256','SOURCE_REVIEW_PACKET'),('execution_amendment_sha256','EXECUTION_SHA256'),('execution_amendment_packet_sha256','EXECUTION_PACKET')]: assert state['source'][field]==constants[key]
logs=[json.loads(members[f'logs/{n:04d}.json']) for n in range(1,38)]
raw_bytes=0
for n,entry in enumerate(logs,1):
    assert entry['exit_code']==(1 if n==37 else 0) and 'failure' not in entry
    assert not entry['timed_out'] and not entry['overflow'] and entry['elapsed_seconds']<entry['timeout_seconds']
    assert entry['stdout_complete'] and entry['stderr_complete']
    assert entry['cwd']=='/home/runner/work/mixer/mixer'
    assert entry['host_environment']=={'DOCKER_CONFIG':'/home/runner/work/mixer/mixer/identity-network-evidence/.scratch/docker','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','HOME':'/home/runner/work/mixer/mixer/identity-network-evidence/.scratch','LANG':'C.UTF-8','PATH':'/usr/local/bin:/usr/bin:/bin'}
    for ext in ['stdout','stderr']:
        if n==28 and ext=='stdout': continue
        body=members[f'logs/{n:04d}.{ext}']; assert entry[ext+'_bytes']==len(body); raw_bytes+=len(body)
assert raw_bytes==state['log_bytes']==8997151 and state['command_number']==37
assert members['logs/0001.stdout'].decode().strip()==SHA
for n,request,output in [(2,request2,output2),(3,request3,output3),(4,request4,output4),(5,request5,output5),(6,request6,output6),(7,request7,output7)]:
    assert logs[n-1]['argv']==['git','--no-replace-objects','cat-file','--batch'] and logs[n-1]['stdin_bytes']==len(request) and logs[n-1]['stdin_sha256']==digest(request) and members[f'logs/{n:04d}.stdout']==output
for pull,inspect,role in [(10,11,'test'),(12,13,'pg')]:
    image=constants['IMAGES'][role]; assert logs[pull-1]['argv']==['docker','pull','--platform','linux/amd64',image['ref']] and logs[inspect-1]['argv']==['docker','image','inspect',image['ref']]
    actual=json.loads(members[role+'-image.json']); assert json.loads(members[f'logs/{inspect:04d}.stdout'])==[actual]
    assert actual['Id']==image['config'] and actual['Os']=='linux' and actual['Architecture']=='amd64' and actual['RepoDigests']==[image['ref'].removeprefix('library/')]
assert len(state['containers'])==1 and not state['unresolved_creates']
owned=state['containers'][0]; cid=owned['cid']; assert re.fullmatch('[0-9a-f]{64}',cid)
assert owned['role']=='prepare' and owned['state']=='removed' and owned['image_id']==constants['IMAGES']['test']['config'] and owned['label']==state['label'] and owned['name']==state['label']+'-prepare'
assert members['logs/0014.stdout']==(cid+'\n').encode()
create=logs[13]['argv']; assert create[:2]==['docker','create'] and create[create.index('--network')+1]=='bridge' and create[-3:]==[owned['image_id'],'-e','Process.sleep(:infinity)']
snapshots={}
for n in [15,16,17,19,21,23,25,27,29,30,32,33,35]:
    assert logs[n-1]['argv']==['docker','container','inspect',cid]
    actual,=json.loads(members[f'logs/{n:04d}.stdout']); assert actual['Id']==cid and actual['Image']==owned['image_id'] and actual['Name']=='/'+owned['name']
    assert actual['Config']['Labels']['mixer.identity.run']==owned['label'] and actual['Config']['Labels']['mixer.identity.role']=='prepare'
    cfg=actual['HostConfig']; assert cfg['ReadonlyRootfs'] is True and cfg['Privileged'] is False and cfg['NetworkMode']=='bridge' and cfg['Tmpfs']==constants['TMPFS']['prepare'] and actual['Mounts']==[]
    assert cfg['SecurityOpt']==['no-new-privileges:true'] and cfg['CapDrop']==['ALL'] and not cfg['CapAdd']
    memory,cpus,pids=constants['RESOURCES']['prepare']; assert cfg['Memory']==cfg['MemorySwap']==memory and cfg['NanoCpus']==cpus*10**9 and cfg['PidsLimit']==pids
    env=dict(item.split('=',1) for item in actual['Config']['Env']); assert len(env)==len(actual['Config']['Env']) and env==constants['BASE_ENV']
    for key in ['Binds','Devices','DeviceRequests','PortBindings','VolumesFrom','ExtraHosts','Links']: assert not cfg[key]
    assert not actual['State']['OOMKilled']
    if n<18: assert actual['State']['Status']=='created' and not actual['State']['Running'] and actual['State']['Pid']==0
    elif n<31: assert actual['State']['Status']=='running' and actual['State']['Running'] and actual['State']['Pid']>0
    else: assert actual['State']['Status']=='exited' and not actual['State']['Running'] and actual['State']['Pid']==0 and actual['State']['ExitCode']==0
    snapshots[n]=actual
assert logs[17]['argv']==['docker','start',cid] and members['logs/0018.stdout']==(cid+'\n').encode()
def exec_argv(command,workdir='/workspace/hosted',interactive=False):
    env=constants['BASE_ENV']; args=['docker','exec',*(['-i'] if interactive else []),'--workdir',workdir]
    args += [part for k,v in sorted(env.items()) for part in ['--env',k+'='+v]]
    return args+[cid,'/usr/bin/env','-i',*[k+'='+v for k,v in sorted(env.items())],*command]
out=io.BytesIO()
with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as archive:
    for p,b in sorted({**product,**helpers}.items()):
        m=tarfile.TarInfo(p); m.size,m.mode,m.mtime=len(b),0o644,0; archive.addfile(m,io.BytesIO(b))
transfer=out.getvalue(); assert logs[19]['argv']==exec_argv(['/usr/bin/tar','--extract','--file','-','--directory','/workspace','--no-same-owner','--no-same-permissions'],'/workspace',True) and logs[19]['stdin_bytes']==len(transfer) and logs[19]['stdin_sha256']==digest(transfer)
def marker(n,name):
    raw=members[f'logs/{n:04d}.stdout']; assert raw.startswith(b'IDENTITY_JSON=') and members[f'logs/{n:04d}.stderr']==b''
    value=json.loads(raw.removeprefix(b'IDENTITY_JSON=').strip()); assert json.loads(members[name])==value
    return value
mounts=marker(22,'prepare-mount-policy.json'); assert logs[21]['argv']==exec_argv(['/usr/local/bin/elixir','/workspace/collector-mounts.exs','prepare'])
assert mounts['source']=='/proc/self/mountinfo' and mounts['role']=='prepare' and mounts['read_bytes']==3260 and len(mounts['selected_lines'])==3
assert mounts['path_modes']=={'/tmp':0o1777,'/workspace':0o755,'/workspace/tooling':0o755}
entries={}
for line in mounts['selected_lines']:
    left,right=line.split(' - '); f=left.split(); fs=right.split(); path=f[4]; flags=set(f[5].split(',')); supers=set(fs[2].split(','))
    assert path in mounts['path_modes'] and path not in entries and fs[:2]==['tmpfs','tmpfs'] and {'rw','nosuid','nodev'}<=flags
    assert ('noexec' not in flags|supers) if path=='/workspace/tooling' else ('noexec' in flags)
    sizes=[v[5:] for v in supers if v.startswith('size=')]; assert len(sizes)==1 and sizes[0].endswith('k')
    expected_bytes=int(next(v[5:] for v in constants['TMPFS']['prepare'][path].split(',') if v.startswith('size=')))
    assert int(sizes[0][:-1])*1024==expected_bytes; entries[path]=(f[0],f[1])
assert entries['/workspace/tooling'][1]==entries['/workspace'][0]
prereq=marker(24,'prepare-prerequisites.json'); assert logs[23]['argv']==exec_argv(['/usr/local/bin/elixir','/workspace/collector-prerequisites.exs'])
expected=amendment['prerequisites']; assert prereq['elixir']==expected['elixir']=='1.20.4' and prereq['otp_patch']==expected['otp_patch']=='29.1.1' and prereq['tools']==expected['tools'] and len(prereq['tools'])==7
assert prereq['openssl'].startswith('OpenSSL 3.0.22 ') and 'Mix 1.20.4' in prereq['mix'] and prereq['crypto_libraries']==[{'name':'OpenSSL','number':805306720,'version':'OpenSSL 3.0.22 25 Aug 2026'}]
ca=prereq['ca']; assert {k:ca[k] for k in ['path','bytes','sha256']}=={k:expected['ca'][k] for k in ['path','bytes','sha256']} and ca['load']=='explicit-selected-bundle' and ca['loaded_count']==150 and ca['loaded_der_sha256']==expected['ca']['der_sha256']
boot=marker(26,'bootstrap-observed.json'); assert logs[25]['argv']==exec_argv(['/usr/local/bin/elixir','/workspace/collector-bootstrap.exs']) and logs[25]['timeout_seconds']==60
for tool,size in [('hex',1133941),('rebar',823379)]:
    assert boot[tool]=={**{k:constants['BOOTSTRAP'][tool][k] for k in ['url','sha512']},'bytes':size,'status':200,'redirects':0,'tls_peer_and_hostname_verified':True,'content_length_and_eof_exact':True}
assert boot['exact_rebar_path']=='/workspace/tooling/rebar3' and boot['hex_version']=='2.5.1' and boot['rebar_version']=='rebar 3.28.0 on Erlang/OTP 29 Erts 17.1\n'
assert boot['rebar_transfer']=={'source':'/workspace/downloads/rebar3','destination':'/workspace/tooling/rebar3','download_bytes':823379,'copied_bytes':823379,'target_bytes':823379,'sha512':constants['BOOTSTRAP']['rebar']['sha512'],'exclusive_create':True,'closed_before_hash':True,'owned_download_removed':True}
literal='path = "/workspace/downloads/hex.ez"; true = File.stat!(path).size <= 16777216; IO.binwrite(File.read!(path))'
assert logs[27]['argv']==exec_argv(['/usr/local/bin/elixir','-e',literal]) and logs[27]['stdout_artifact']=='.scratch/copy.bin' and logs[27]['timeout_seconds']==30 and members['logs/0028.stderr']==b''
hex_bytes=(ROOT/'official/pinned-hex-2.5.1.ez').read_bytes(); assert len(hex_bytes)==boot['hex']['bytes'] and hashlib.sha512(hex_bytes).hexdigest()==boot['hex']['sha512']
transcoded=hex_bytes.decode('latin1').encode('utf8'); assert len(transcoded)==logs[27]['stdout_bytes']==1693010 and digest(transcoded)==logs[27]['stdout_sha256']=='9ec3f63426780b4b34d6486a64785e6e499fec9167ac7c81eaad6de7f0c195f6'
assert len([r for r in logs if r['argv'][:2]==['docker','exec']])==5
assert logs[30]['argv']==['docker','stop','--time','2',cid] and json.loads(members['prepare-terminal.json'])==snapshots[32]
assert logs[33]['argv']==['docker','logs',cid] and logs[35]['argv']==['docker','rm','--volumes',cid] and members['logs/0036.stdout']==(cid+'\n').encode()
assert logs[36]['argv']==['docker','container','inspect',cid] and members['logs/0037.stdout']==b'[]\n' and members['logs/0037.stderr']==('Error response from daemon: No such container: '+cid+'\n').encode()
assert state['status']=='FAILED-or-partial' and state['primary_outcome_frozen'] and not state['cancelled'] and state['primary_failure']=={'message':'observed bootstrap artifact digest mismatch','type':'CollectorError'}
assert state['cleanup']=={'container_teardown_is_product_lifecycle_proof':False,'errors':[],'status':'verified-exact-created-IDs-absent','unresolved_creates':[]}
assert state['host_scratch_cleanup']=='removed owned .scratch; package outputs retained'
assert finalizer=={'cleanup_verified':True,'no_retry_of_identity_lost_or_unknown_create':True,'primary_status':'FAILED-or-partial','same_original_aggregate_deadline':True,'schema':1}
assert 'Ran 103 tests in 1.022s' in (ROOT/'job.log').read_text()
docker=json.loads(members['logs/0009.stdout']); assert docker['Client']['Version']==docker['Server']['Version']=='28.0.4'
assert 'do **not** use this function on IO devices in' in (ROOT/'official/elixir-v1.20.4-io.ex').read_text()
# Retain selected small observations plus all archive contents unchanged in ZIP.
for name in expected-{f'logs/{n:04d}.stdout' for n in range(2,8)}: retained('artifact/'+name,members[name])
for label,files in [('collector-source',controls),('literal-helpers',helpers),('selected-contract-metadata',metadata)]:
    for name,body in files.items(): retained(label+'/'+name,body)
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':{'model':'gpt-6-astra','reasoning_effort':'xhigh','python':platform.python_version()},'source_revision':SHA,'source_tree':TREE,'run_id':40746908101,'artifact_id':12842685657,'zip':binding(data),'members':len(members),'expanded_bytes':expanded,'artifact_manifest_files':len(observed),'artifact_tree_digest_sha256':manifest['tree_digest_sha256'],'source_files_verified':4,'metadata_files_verified':104,'helpers_verified':7,'product_files_verified':177,'product_digest':constants['FROZEN_PRODUCT_DIGEST'],'commands_verified':37,'raw_log_bytes':raw_bytes,'remote_host':host,'remote_docker':docker,'remote_controls':{'tests':103,'seconds':1.022,'failures':0},'actual_mount_policy':'prepare tmpfs sizes flags modes and child hierarchy accepted','actual_bootstrap_scope':'verified helper completion, pinned TLS downloads, exclusive cross-mount Rebar copy and direct Rebar execution; host export validation failed','first_failure':{'after_command':28,'message':state['primary_failure']['message'],'command_exit':0,'streams_complete':True,'output_retained':False,'recorded_output_bytes':len(transcoded),'recorded_output_sha256':digest(transcoded),'explanation':'Latin-1 to UTF-8 transcoding produces exact recorded export size and SHA-256 from exact pinned Hex bytes'},'cleanup':{'prepare_cid':cid,'stop_exit':0,'terminal_exit':0,'remove_exit':0,'exact_absence_verified':True,'host_scratch':state['host_scratch_cleanup'],'finalizer':finalizer},'product_methods_run':0,'not_run':['Rebar host binary export','locked dependency resolution','prepared archive export/restore','test/PG container creation','offline compile','two production-DNS/TLS methods'],'limitations':['command 28 raw failed export bytes absent; its receipt SHA and count remain','full mountinfo bytes absent; source-bound selected lines and whole-read hash retained','no corrected Elixir runtime test executed','cleanup is not product lifecycle proof'],'local_runtime_or_ci_actions':False,'command':'python3 -B verification/github-delivery-runtime-followup/network-review/verify_artifact.py','alarm_seconds':50,'git_timeout_seconds':20,'script_sha256':digest(Path(__file__).read_bytes())}
put('verification-result.json',result)
print(json.dumps({'status':'failed-run-evidence-verified','artifact_tree':manifest['tree_digest_sha256'],'new_failure':'Unicode stdio binary export corruption','actual_rebar_direct_exec':'passed','byte_transform_hash_match':True,'cleanup':'exact owned prepare CID absent','product_methods_run':0},indent=2))
