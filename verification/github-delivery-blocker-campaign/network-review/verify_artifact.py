#!/usr/bin/env python3
"""Bounded offline evidence review. No product/collector imports or runtime calls."""
import ast, datetime, hashlib, importlib.util, io, json, platform, re, signal, stat, subprocess, tarfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
SHA='cc350d3303ca71c5d57e87846f6a61304b658fa7'
ZIP_SHA='932f877ed0fc8cf8ad9457e0ba1b4888ff7bd5a58762b86975f6e887f9673231'
UTILITY=REPO/'verification/github-delivery-identity-network/network-review/verify_failed_artifact.py'
assert hashlib.sha256(UTILITY.read_bytes()).hexdigest()=='371e6c453a57eb90377acf669c0622c5d71925c2497e10782db296573073ccb6'
spec=importlib.util.spec_from_file_location('data_only_archive_readers',UTILITY)
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
reader.ROOT,reader.REPO,reader.CAP=ROOT,REPO,256*1024*1024
binding,canonical,digest=reader.binding,reader.canonical,reader.digest
safe_name,safe_tar,git_blobs=reader.safe_name,reader.safe_tar,reader.git_blobs
def put(name,value): (ROOT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def deadline(*_):raise TimeoutError('offline review50second bound')
signal.signal(signal.SIGALRM,deadline);signal.alarm(50)
data=(ROOT/'artifact.zip').read_bytes()
assert len(data)==2778386 and len(data)<=64*1024*1024 and digest(data)==ZIP_SHA
members={};folded=set();expanded=0
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    for item in archive.infolist():
        safe_name(item.filename)
        assert item.filename not in members and item.filename.casefold() not in folded
        assert not item.is_dir() and not item.flag_bits&1 and stat.S_IFMT(item.external_attr>>16) in (0,stat.S_IFREG)
        expanded+=item.file_size;assert 0<=item.file_size<=reader.CAP and expanded<=reader.CAP
        body=archive.read(item);assert len(body)==item.file_size
        members[item.filename]=body;folded.add(item.filename.casefold())
names=set(reader.META_NAMES)|{'bootstrap-plan.json','prepare-prerequisites.json'}
names.update(f'logs/{n:04d}.{ext}' for n in range(1,32) for ext in ['json','stdout','stderr'])
assert set(members)==names and len(members)==108
manifest=json.loads(members['artifact-manifest.json'])
observed={name:binding(body) for name,body in members.items() if name!='artifact-manifest.json'}
assert manifest['files']==observed and manifest['tree_digest_sha256']==digest(canonical(observed))
controls,request3,output3=git_blobs(SHA,reader.CONTROL_PATHS)
assert safe_tar(members['collector-source.tar'],controls)==controls
assert json.loads(members['collector-source-bindings.json'])=={p:binding(b) for p,b in controls.items()}
constants={}
for node in ast.parse(controls[reader.CONTROL_PATHS[0]]).body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        try:constants[node.targets[0].id]=ast.literal_eval(node.value)
        except (ValueError,TypeError):pass
frozen=constants['FROZEN_MANIFEST'];assert len(frozen)==177
assert json.loads(members['product-source-manifest.json'])==frozen and digest(canonical(frozen))==constants['FROZEN_PRODUCT_DIGEST']
product,request2,output2=git_blobs(SHA,sorted(frozen));original,_,_=git_blobs(constants['PRODUCT_COMMIT'],sorted(frozen))
assert product==original and {p:binding(b) for p,b in product.items()}==frozen
newbase=constants['AMENDMENT_BASE'];oldbase=constants['CONTRACT_BASE']
newseal,request4,output4=git_blobs(SHA,[newbase+'packet-manifest.json'])
newpacket=json.loads(newseal[newbase+'packet-manifest.json'])
assert len(newpacket['files'])==78 and newpacket['tree_digest_sha256']==digest(canonical(newpacket['files']))==constants['AMENDMENT_PACKET']
remaining,request5,output5=git_blobs(SHA,reader.PACKET_PATHS+[newbase+p for p in newpacket['files']])
metadata={**newseal,**remaining};assert len(metadata)==87 and safe_tar(members['selected-contract-metadata.tar'],metadata)==metadata
for p,e in newpacket['files'].items():assert binding(metadata[newbase+p])==e
oldpacket=json.loads(metadata[oldbase+'packet-manifest.json'])
assert digest(metadata[oldbase+'packet-manifest.json'])==constants['CONTRACT_PACKET_SHA256']
assert oldpacket['tree_digest_sha256']==digest(canonical(oldpacket['files']))==constants['CONTRACT_PACKET']
assert digest(metadata[oldbase+'contract.json'])==constants['CONTRACT_SHA256']
for p in reader.PACKET_PATHS:
    if p!=oldbase+'packet-manifest.json':assert oldpacket['files'][p.removeprefix(oldbase)]==binding(metadata[p])
amendment=json.loads(metadata[newbase+'image-amendment.json']);assert digest(metadata[newbase+'image-amendment.json'])==constants['AMENDMENT_SHA256']
helpers={'collector-'+name+'.exs':constants[key].encode() for name,key in [('prerequisites','PREREQUISITES_EXS'),('bootstrap','BOOTSTRAP_EXS'),('manifest','MANIFEST_EXS'),('netns','NETNS_EXS'),('observer','OBSERVER_EXS')]}
bootstrap=constants['BOOTSTRAP_EXS']
for placeholder,value in {'HEX_URL':constants['BOOTSTRAP']['hex']['url'],'HEX_SHA':constants['BOOTSTRAP']['hex']['sha512'],'REBAR_URL':constants['BOOTSTRAP']['rebar']['url'],'REBAR_SHA':constants['BOOTSTRAP']['rebar']['sha512']}.items():bootstrap=bootstrap.replace(placeholder,value)
helpers['collector-bootstrap.exs']=bootstrap.encode();helpers['frozen-manifest.json']=canonical(frozen)
assert safe_tar(members['literal-helpers.tar'],helpers)==helpers and json.loads(members['literal-helper-bindings.json'])=={p:binding(b) for p,b in helpers.items()}
state,finalizer,host=[json.loads(members[p]) for p in ['state.json','finalizer.json','host.json']]
assert state['sha']==SHA and state['run_id']=='40740023326' and state['attempt']=='1'
assert host['github_run_id']==state['run_id'] and host['attempt']=='1' and host['uname'][0]=='Linux' and host['uname'][-1]=='x86_64'
assert state['source']['delivery_revision']==SHA and state['source']['product_tree_digest_sha256']==constants['FROZEN_PRODUCT_DIGEST']
for field,key in [('image_amendment_sha256','AMENDMENT_SHA256'),('image_amendment_packet_sha256','AMENDMENT_PACKET'),('image_source_review_packet_sha256','SOURCE_REVIEW_PACKET')]:assert state['source'][field]==constants[key]
logs=[json.loads(members[f'logs/{n:04d}.json']) for n in range(1,32)]
raw_bytes=0
for n,entry in enumerate(logs,1):
    assert entry['exit_code']==(1 if n in [22,31] else 0)
    assert not entry['timed_out'] and not entry['overflow'] and entry['elapsed_seconds']<entry['timeout_seconds']
    assert entry['stdout_complete']==(n!=22) and entry['stderr_complete']==(n!=22)
    assert entry['cwd']=='/home/runner/work/mixer/mixer'
    assert entry['host_environment']=={'DOCKER_CONFIG':'/home/runner/work/mixer/mixer/identity-network-evidence/.scratch/docker','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','HOME':'/home/runner/work/mixer/mixer/identity-network-evidence/.scratch','LANG':'C.UTF-8','PATH':'/usr/local/bin:/usr/bin:/bin'}
    for ext in ['stdout','stderr']:
        assert entry[ext+'_bytes']==len(members[f'logs/{n:04d}.{ext}']);raw_bytes+=entry[ext+'_bytes']
assert raw_bytes==state['log_bytes'] and state['command_number']==31
assert members['logs/0001.stdout'].decode().strip()==SHA
for n,request,output in [(2,request2,output2),(3,request3,output3),(4,request4,output4),(5,request5,output5)]:
    assert logs[n-1]['argv']==['git','--no-replace-objects','cat-file','--batch']
    assert logs[n-1]['stdin_bytes']==len(request) and logs[n-1]['stdin_sha256']==digest(request) and members[f'logs/{n:04d}.stdout']==output
for pull,inspect,role in [(8,9,'test'),(10,11,'pg')]:
    expected=constants['IMAGES'][role];assert logs[pull-1]['argv']==['docker','pull','--platform','linux/amd64',expected['ref']]
    assert logs[inspect-1]['argv']==['docker','image','inspect',expected['ref']]
    actual=json.loads(members[role+'-image.json']);assert json.loads(members[f'logs/{inspect:04d}.stdout'])==[actual]
    assert actual['Id']==expected['config'] and actual['Os']=='linux' and actual['Architecture']=='amd64'
    assert actual['RepoDigests']==[expected['ref'].removeprefix('library/')]
assert len(state['containers'])==1 and not state['unresolved_creates']
owned=state['containers'][0];cid=owned['cid'];assert re.fullmatch('[0-9a-f]{64}',cid)
assert owned['role']=='prepare' and owned['state']=='removed' and owned['image_id']==constants['IMAGES']['test']['config']
assert owned['label']==state['label'] and owned['name']==state['label']+'-prepare'
assert members['logs/0012.stdout']==(cid+'\n').encode()
create=logs[11]['argv'];assert create[:2]==['docker','create'] and create[create.index('--network')+1]=='bridge' and create[-3:]==[owned['image_id'],'-e','Process.sleep(:infinity)']
snapshots={}
for n in [13,14,15,17,19,21,23,24,26,27,29]:
    assert logs[n-1]['argv']==['docker','container','inspect',cid]
    actual,=json.loads(members[f'logs/{n:04d}.stdout']);assert actual['Id']==cid and actual['Image']==owned['image_id'] and actual['Name']=='/'+owned['name']
    assert actual['Config']['Labels']['mixer.identity.run']==owned['label'] and actual['Config']['Labels']['mixer.identity.role']=='prepare'
    cfg=actual['HostConfig'];assert cfg['ReadonlyRootfs'] is True and cfg['Privileged'] is False and cfg['NetworkMode']=='bridge'
    assert cfg['Tmpfs']==constants['TMPFS']['prepare'] and actual['Mounts']==[]
    assert cfg['SecurityOpt']==['no-new-privileges:true'] and cfg['CapDrop']==['ALL'] and not cfg['CapAdd']
    memory,cpus,pids=constants['RESOURCES']['prepare'];assert cfg['Memory']==cfg['MemorySwap']==memory and cfg['NanoCpus']==cpus*10**9 and cfg['PidsLimit']==pids
    env=dict(item.split('=',1) for item in actual['Config']['Env']);assert len(env)==len(actual['Config']['Env']) and env==constants['BASE_ENV']
    for key in ['Binds','Devices','DeviceRequests','PortBindings','VolumesFrom','ExtraHosts','Links']:assert not cfg[key]
    assert not actual['State']['OOMKilled']
    if n<16:assert actual['State']['Status']=='created' and not actual['State']['Running'] and actual['State']['Pid']==0
    elif n<25:assert actual['State']['Status']=='running' and actual['State']['Running'] and actual['State']['Pid']>0
    else:assert actual['State']['Status']=='exited' and not actual['State']['Running'] and actual['State']['Pid']==0 and actual['State']['ExitCode']==0
    snapshots[n]=actual
assert logs[15]['argv']==['docker','start',cid] and members['logs/0016.stdout']==(cid+'\n').encode()
def exec_argv(command,workdir,interactive=False):
    env=constants['BASE_ENV'];args=['docker','exec',*(['-i'] if interactive else []),'--workdir',workdir]
    args += [part for k,v in sorted(env.items()) for part in ['--env',k+'='+v]]
    return args+[cid,'/usr/bin/env','-i',*[k+'='+v for k,v in sorted(env.items())],*command]
out=io.BytesIO()
with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as archive:
    for p,b in sorted({**product,**helpers}.items()):
        m=tarfile.TarInfo(p);m.size,m.mode,m.mtime=len(b),0o644,0;archive.addfile(m,io.BytesIO(b))
transfer=out.getvalue();assert logs[17]['argv']==exec_argv(['/usr/bin/tar','--extract','--file','-','--directory','/workspace','--no-same-owner','--no-same-permissions'],'/workspace',True)
assert logs[17]['stdin_bytes']==len(transfer) and logs[17]['stdin_sha256']==digest(transfer)
assert logs[19]['argv']==exec_argv(['/usr/local/bin/elixir','/workspace/collector-prerequisites.exs'],'/workspace/hosted')
prereq=json.loads(members['prepare-prerequisites.json']);assert members['logs/0020.stdout'].startswith(b'IDENTITY_JSON=')
assert json.loads(members['logs/0020.stdout'].removeprefix(b'IDENTITY_JSON=').strip())==prereq and members['logs/0020.stderr']==b''
expected=amendment['prerequisites'];assert prereq['elixir']==expected['elixir'] and prereq['otp_patch']==expected['otp_patch'] and prereq['tools']==expected['tools']
assert prereq['openssl'].startswith('OpenSSL 3.0.22 ') and 'Mix 1.20.4' in prereq['mix']
assert prereq['crypto_libraries']==[{'name':'OpenSSL','number':805306720,'version':'OpenSSL 3.0.22 25 Aug 2026'}]
ca=prereq['ca'];assert {k:ca[k] for k in ['path','bytes','sha256']}=={k:expected['ca'][k] for k in ['path','bytes','sha256']}
assert ca['load']=='explicit-selected-bundle' and ca['loaded_count']==150 and ca['loaded_der_sha256']==expected['ca']['der_sha256']
assert logs[21]['argv']==exec_argv(['/usr/local/bin/elixir','/workspace/collector-bootstrap.exs'],'/workspace/hosted')
failure=members['logs/0022.stderr'].decode();assert ':erlang.open_port({:spawn_executable, ~c"/workspace/tooling/rebar3"}' in failure and ':eacces' in failure and 'collector-bootstrap.exs:86:' in failure
assert bootstrap.splitlines()[85].strip()=='{rebar_version, 0} = System.cmd("/workspace/tooling/rebar3", ["--version"], stderr_to_stdout: true)'
assert logs[21]['failure']=='nonzero/timeout command' and logs[21]['timeout_seconds']==60 and members['logs/0022.stdout']==b''
assert len([r for r in logs if r['argv'][:2]==['docker','exec']])==3
assert logs[24]['argv']==['docker','stop','--time','2',cid]
assert json.loads(members['prepare-terminal.json'])==snapshots[26]
assert logs[27]['argv']==['docker','logs',cid]
assert logs[29]['argv']==['docker','rm','--volumes',cid] and members['logs/0030.stdout']==(cid+'\n').encode()
assert logs[30]['argv']==['docker','container','inspect',cid] and members['logs/0031.stdout']==b'[]\n'
assert members['logs/0031.stderr']==('Error response from daemon: No such container: '+cid+'\n').encode()
assert state['status']=='FAILED-or-partial' and state['primary_outcome_frozen'] and not state['cancelled']
assert state['primary_failure']=={'message':'nonzero/timeout command','type':'CollectorError'}
assert state['cleanup']=={'container_teardown_is_product_lifecycle_proof':False,'errors':[],'status':'verified-exact-created-IDs-absent','unresolved_creates':[]}
assert finalizer=={'cleanup_verified':True,'no_retry_of_identity_lost_or_unknown_create':True,'primary_status':'FAILED-or-partial','same_original_aggregate_deadline':True,'schema':1}
assert 'Ran 84 tests in 0.568s' in (ROOT/'job.log').read_text()
docker=json.loads(members['logs/0007.stdout']);assert docker['Client']['Version']==docker['Server']['Version']=='28.0.4'
# Retain all small logs and exact data-only nested archives, avoiding duplicate
# large git batch outputs. Their complete bytes remain CRC/hash bound in ZIP.
for name in names-{'logs/0002.stdout','logs/0003.stdout','logs/0004.stdout','logs/0005.stdout'}:reader.write_regular('artifact/'+name,members[name])
for label,files in [('collector-source',controls),('literal-helpers',helpers),('selected-contract-metadata',metadata)]:
    for name,body in files.items():reader.write_regular(label+'/'+name,body)
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':'gpt-6-astra','reasoning_effort':'xhigh','reviewer_python':platform.python_version(),'delivery_revision':SHA,'delivery_tree':'07f2b0e23e58dd445e2731930fc66b00ed49ec2e','run_id':40740023326,'artifact_id':12837649788,'zip':binding(data),'members':len(members),'expanded_bytes':expanded,'artifact_manifest_files':len(observed),'artifact_tree_digest_sha256':manifest['tree_digest_sha256'],'source_files_verified':4,'metadata_files_verified':87,'helpers_verified':6,'product_files_verified':177,'product_digest':constants['FROZEN_PRODUCT_DIGEST'],'commands_verified':31,'raw_log_bytes':raw_bytes,'remote_host':host,'remote_docker':docker,'remote_controls':{'tests':84,'seconds':0.568,'failures':0},'preparation_prerequisites':'actual exact-seven-tool-and-CA150-crypto-VM-result-accepted','primary_failure':{'command':22,'exit_code':1,'elapsed_seconds':logs[21]['elapsed_seconds'],'stderr':failure,'producer_stream_complete_flags':False,'claim':'retained434-byte failure evidence bound; no complete-stream success claimed'},'bootstrap_scope':'fixed helper reached direct Rebar exec after earlier TLS/hash/Hex assertions; no structured bootstrap-observed receipt or bootstrap artifact bytes retained; no complete bootstrap pass','cleanup':{'exact_prepare_cid':cid,'stop_exit':0,'terminal_exit':0,'remove_exit':0,'exact_absence_verified':True,'host_scratch':state['host_scratch_cleanup'],'finalizer':finalizer},'not_run':['test/PG container creation','dependency resolution','offline compile','two network test methods'],'actual_mountinfo_retained':False,'local_runtime_or_CI_actions':False,'command':'python3 -B verification/github-delivery-blocker-campaign/network-review/verify_artifact.py','command_deadline_seconds':50,'reviewer_script_sha256':digest(Path(__file__).read_bytes()),'reader_utility_sha256':digest(UTILITY.read_bytes())}
put('verification-result.json',result)
print(json.dumps({'status':'failed-run-evidence-verified','manifest_files':len(observed),'manifest_tree':manifest['tree_digest_sha256'],'first_failure_command':22,'first_failure':'EACCES spawning exact /workspace/tooling/rebar3 --version','prerequisites':'pass','cleanup':'exact owned CID absent','methods_run':0},indent=2))
