#!/usr/bin/env python3
"""Bounded offline evidence join; never executes product, collector or archive code."""
import ast, datetime, hashlib, io, json, platform, re, signal, stat, subprocess, tarfile, zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SHA = '56ff14c925168284761c5aca4f0bd4129cf3c995'
TREE = '75989099938ed5256c4144cbc9e62979ee323183'
CAP = 256 * 1024 * 1024
CONTROL_PATHS = ['hosted/scripts/test-identity-network.py', 'hosted/scripts/test_identity_network_collector.py', 'docs/hosted-identity-production-network-ci-contract.md', '.github/workflows/identity-network.yml']
EXPECTED_CONTROL_SHA = ['ee9c047ae628b18df2cd8c7b963910bc573b998358cf76eb27abec81598cb05e', '0a0cca3001af5c01a35b59b7d18bdd090f220aa52218d56f2c9676273f9d1615', '9f7ac0bc7a3e625ae353bc3c3354c1cd0e1efdc1ac06eccc52d8162fcce1ded0', '4b5fa14bfa80601354bd063f3e93f728fa1175e52de3d5c6bcc62a99b044eb19']

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
assert len(data)==11377187 and len(data)<=64*1024*1024 and digest(data)=='2f0e7761685d64924bc743c3b8ad73d944ed726ecc0e4b14228010a840552be9'
members,folded,expanded={},set(),0
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    for item in archive.infolist():
        safe_name(item.filename)
        assert item.filename not in members and item.filename.casefold() not in folded
        assert not item.is_dir() and not item.flag_bits&1 and stat.S_IFMT(item.external_attr>>16) in (0,stat.S_IFREG)
        expanded+=item.file_size; assert 0<=item.file_size<=CAP and expanded<=CAP
        body=archive.read(item); assert len(body)==item.file_size
        members[item.filename]=body; folded.add(item.filename.casefold())
assert len(members)==350 and expanded==34757799
manifest=json.loads(members['artifact-manifest.json'])
observed={n:binding(b) for n,b in members.items() if n!='artifact-manifest.json'}
assert manifest['files']==observed and manifest['tree_digest_sha256']==digest(canonical(observed))
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
job,=json.loads((ROOT/'job-metadata.json').read_text())['jobs']
assert run['id']==40753111388 and run['head_sha']==SHA and run['head_commit']['tree_id']==TREE and run['conclusion']=='failure' and run['run_attempt']==1 and run['event']=='push'
assert artifact_meta['id']==12845285898 and artifact_meta['workflow_run']['id']==run['id'] and artifact_meta['workflow_run']['head_sha']==SHA and artifact_meta['digest']=='sha256:'+digest(data)
assert job['id']==123044764614 and job['run_id']==run['id'] and job['conclusion']=='failure'
assert state['sha']==SHA and state['run_id']==str(run['id']) and state['attempt']=='1' and state['command_number']==107
assert host['github_run_id']==state['run_id'] and host['attempt']=='1' and host['uname'][0]=='Linux' and host['uname'][-1]=='x86_64'
assert state['source']['delivery_revision']==SHA and state['source']['product_tree_digest_sha256']==constants['FROZEN_PRODUCT_DIGEST']
for field,key in [('image_amendment_sha256','AMENDMENT_SHA256'),('image_amendment_packet_sha256','AMENDMENT_PACKET'),('image_source_review_packet_sha256','SOURCE_REVIEW_PACKET'),('execution_amendment_sha256','EXECUTION_SHA256'),('execution_amendment_packet_sha256','EXECUTION_PACKET')]: assert state['source'][field]==constants[key]
logs=[json.loads(members[f'logs/{n:04d}.json']) for n in range(1,108)]
raw_bytes=0
binary_names={28:'bootstrap-exports/hex-actual.bin',30:'bootstrap-exports/rebar-actual.bin',38:'prepared-source-dependencies-tools.tar'}
for n,entry in enumerate(logs,1):
    assert entry['exit_code']==(1 if n in [47,98,107] else 2 if n in [75,77] else 0) and 'failure' not in entry
    assert not entry['timed_out'] and not entry['overflow'] and entry['elapsed_seconds']<entry['timeout_seconds']
    assert entry['stdout_complete'] and entry['stderr_complete']
    assert entry['cwd']=='/home/runner/work/mixer/mixer'
    assert entry['host_environment']=={'DOCKER_CONFIG':'/home/runner/work/mixer/mixer/identity-network-evidence/.scratch/docker','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','HOME':'/home/runner/work/mixer/mixer/identity-network-evidence/.scratch','LANG':'C.UTF-8','PATH':'/usr/local/bin:/usr/bin:/bin'}
    for ext in ['stdout','stderr']:
        name=binary_names[n] if n in binary_names and ext=='stdout' else f'logs/{n:04d}.{ext}'
        body=members[name]; assert entry[ext+'_bytes']==len(body)
        if n in binary_names and ext=='stdout': assert entry['stdout_sha256']==digest(body)
        else: raw_bytes+=len(body)
assert raw_bytes==state['log_bytes']==9967989
assert members['logs/0001.stdout'].decode().strip()==SHA
for n,request,output in [(2,request2,output2),(3,request3,output3),(4,request4,output4),(5,request5,output5),(6,request6,output6),(7,request7,output7)]:
    assert logs[n-1]['argv']==['git','--no-replace-objects','cat-file','--batch'] and logs[n-1]['stdin_bytes']==len(request) and logs[n-1]['stdin_sha256']==digest(request) and members[f'logs/{n:04d}.stdout']==output
for pull,inspect,role in [(10,11,'test'),(12,13,'pg')]:
    selected=constants['IMAGES'][role]; assert logs[pull-1]['argv']==['docker','pull','--platform','linux/amd64',selected['ref']] and logs[inspect-1]['argv']==['docker','image','inspect',selected['ref']]
    actual=json.loads(members[role+'-image.json']); assert json.loads(members[f'logs/{inspect:04d}.stdout'])==[actual]
    assert actual['Id']==selected['config'] and actual['Os']=='linux' and actual['Architecture']=='amd64' and actual['RepoDigests']==[selected['ref'].removeprefix('library/')]
assert len(state['containers'])==3 and not state['unresolved_creates']
owned={r['role']:r for r in state['containers']}; assert set(owned)=={'prepare','test','pg'}
snapshots={}; inspect_counts={role:0 for role in owned}; cleanup={}
pg_env={'PATH':constants['BASE_ENV']['PATH']+':/usr/lib/postgresql/16/bin','GOSU_VERSION':'1.19','LANG':'en_US.utf8','PG_MAJOR':'16','PG_VERSION':'16.15-1.pgdg12+2','PGDATA':'/var/lib/postgresql/data','POSTGRES_USER':'mixer_fixture','POSTGRES_DB':'mixer_startup_test','POSTGRES_HOST_AUTH_METHOD':'trust'}
envs={'prepare':constants['BASE_ENV'],'test':constants['BASE_ENV'],'pg':pg_env}
for role,row in owned.items():
    cid=row['cid']; assert re.fullmatch('[0-9a-f]{64}',cid) and row['state']=='removed' and row['label']==state['label'] and row['name']==state['label']+'-'+role
    assert row['image_id']==constants['IMAGES']['pg' if role=='pg' else 'test']['config']
    for n,entry in enumerate(logs,1):
        if entry['argv']!=['docker','container','inspect',cid] or entry['exit_code']!=0: continue
        actual,=json.loads(members[f'logs/{n:04d}.stdout']); snapshots[n]=actual; inspect_counts[role]+=1
        assert actual['Id']==cid and actual['Image']==row['image_id'] and actual['Name']=='/'+row['name']
        assert actual['Config']['Labels']=={'mixer.identity.role':role,'mixer.identity.run':row['label']}
        cfg=actual['HostConfig']; assert cfg['ReadonlyRootfs'] is True and cfg['Privileged'] is False and cfg['Tmpfs']==constants['TMPFS'][role] and actual['Mounts']==[]
        assert cfg['NetworkMode']==({'prepare':'bridge','test':'none','pg':'container:'+owned['test']['cid']}[role])
        assert cfg['SecurityOpt']==['no-new-privileges:true'] and cfg['CapDrop']==['ALL'] and {v.removeprefix('CAP_') for v in (cfg['CapAdd'] or [])}==constants['CAPS'][role]
        memory,cpus,pids=constants['RESOURCES'][role]; assert cfg['Memory']==cfg['MemorySwap']==memory and cfg['NanoCpus']==cpus*10**9 and cfg['PidsLimit']==pids
        env=dict(v.split('=',1) for v in actual['Config']['Env']); assert len(env)==len(actual['Config']['Env']) and env==envs[role]
        assert cfg['Ulimits']==[{'Name':'nofile','Hard':4096,'Soft':4096}]
        for key in ['Binds','Devices','DeviceRequests','PortBindings','VolumesFrom','ExtraHosts','Links']: assert not cfg[key]
        for key in ['PidMode','IpcMode','UTSMode','UsernsMode']: assert cfg[key]!='host'
        assert not any((actual['NetworkSettings']['Ports'] or {}).values()) and not actual['State']['OOMKilled']
    create_n={'prepare':14,'test':48,'pg':65}[role]; create=logs[create_n-1]['argv']
    assert create[:2]==['docker','create'] and create[create.index('--name')+1]==row['name'] and row['image_id'] in create and members[f'logs/{create_n:04d}.stdout']==(cid+'\n').encode()
    for n,entry in enumerate(logs,1):
        a=entry['argv']
        if a[:2]==['docker','exec'] and cid in a:
            idx=a.index(cid); e=envs[role]
            expected=['docker','exec',*(['-i'] if '-i' in a[:idx] else []),'--workdir',a[a.index('--workdir')+1],*[v for k,value in sorted(e.items()) for v in ['--env',k+'='+value]],cid,'/usr/bin/env','-i',*[k+'='+v for k,v in sorted(e.items())]]
            assert a[:len(expected)]==expected
    stop_n,terminal_n,remove_n,absence_n={'prepare':(41,42,46,47),'pg':(92,93,97,98),'test':(101,102,106,107)}[role]
    assert logs[stop_n-1]['argv']==['docker','stop','--time','2',cid] and logs[remove_n-1]['argv']==['docker','rm','--volumes',cid]
    terminal=json.loads(members[role+'-terminal.json']); assert terminal==snapshots[terminal_n] and not terminal['State']['Running'] and terminal['State']['Pid']==0 and not terminal['State']['OOMKilled']
    assert logs[absence_n-1]['argv']==['docker','container','inspect',cid] and members[f'logs/{absence_n:04d}.stdout']==b'[]\n' and members[f'logs/{absence_n:04d}.stderr']==('Error response from daemon: No such container: '+cid+'\n').encode()
    cleanup[role]={'cid':cid,'stop_command':stop_n,'terminal_command':terminal_n,'terminal_exit':terminal['State']['ExitCode'],'remove_command':remove_n,'absence_command':absence_n,'exact_absence_verified':True}
assert 47<48 and len([r for r in logs if r['argv'][:2]==['docker','create']])==3
def exec_tail(n):
    a=logs[n-1]['argv']; idx=a.index('/usr/bin/env')+2
    while '=' in a[idx]: idx+=1
    return a[idx:]
def marker(n,name=None):
    raw=members[f'logs/{n:04d}.stdout']; assert raw.startswith(b'IDENTITY_JSON=') and members[f'logs/{n:04d}.stderr']==b''
    value=json.loads(raw.removeprefix(b'IDENTITY_JSON=').strip())
    if name: assert json.loads(members[name])==value
    return value
for role,n in [('prepare',22),('test',56)]:
    mounts=marker(n,role+'-mount-policy.json'); assert exec_tail(n)==['/usr/local/bin/elixir','/workspace/collector-mounts.exs',role]
    paths=constants['MOUNT_POLICY']['roles'][role]; assert mounts['source']=='/proc/self/mountinfo' and mounts['role']==role and 0<mounts['read_bytes']<=65536 and re.fullmatch('[0-9a-f]{64}',mounts['read_sha256'])
    assert mounts['path_modes']=={p:constants['MOUNT_POLICY']['modes'][p] for p in paths} and len(mounts['selected_lines'])==len(paths)
    entries={}
    for line in mounts['selected_lines']:
        left,right=line.split(' - '); f=left.split(); fs=right.split(); path=f[4]; flags=set(f[5].split(',')); supers=set(fs[2].split(','))
        assert path in paths and path not in entries and fs[:2]==['tmpfs','tmpfs'] and {'rw','nosuid','nodev'}<=flags
        assert ('noexec' not in flags|supers) if path=='/workspace/tooling' else ('noexec' in flags)
        sizes=[v[5:] for v in supers if v.startswith('size=')]; assert len(sizes)==1 and sizes[0].endswith('k')
        selected_size=int(next(v[5:] for v in constants['TMPFS'][role][path].split(',') if v.startswith('size=')))
        assert int(sizes[0][:-1])*1024==selected_size; entries[path]=(f[0],f[1])
    assert entries['/workspace/tooling'][1]==entries['/workspace'][0]
for role,n in [('prepare',24),('test',60)]:
    prereq=marker(n,role+'-prerequisites.json'); expected=amendment['prerequisites']
    assert exec_tail(n)==['/usr/local/bin/elixir','/workspace/collector-prerequisites.exs']
    assert prereq['elixir']==expected['elixir']=='1.20.4' and prereq['otp_patch']==expected['otp_patch']=='29.1.1' and prereq['tools']==expected['tools'] and len(prereq['tools'])==7
    assert prereq['openssl'].startswith('OpenSSL 3.0.22 ') and 'Mix 1.20.4' in prereq['mix'] and prereq['crypto_libraries']==[{'name':'OpenSSL','number':805306720,'version':'OpenSSL 3.0.22 25 Aug 2026'}]
    ca=prereq['ca']; assert {k:ca[k] for k in ['path','bytes','sha256']}=={k:expected['ca'][k] for k in ['path','bytes','sha256']} and ca['load']=='explicit-selected-bundle' and ca['loaded_count']==150 and ca['loaded_der_sha256']==expected['ca']['der_sha256']
boot=marker(26,'bootstrap-observed.json'); assert exec_tail(26)==['/usr/local/bin/elixir','/workspace/collector-bootstrap.exs']
export_bindings={}
for tool,size,n,path,accepted in [('hex',1133941,28,'/workspace/downloads/hex.ez','bootstrap-hex-2.5.1.ez'),('rebar',823379,30,'/workspace/tooling/rebar3','bootstrap-rebar-3.28.0')]:
    assert boot[tool]=={**{k:constants['BOOTSTRAP'][tool][k] for k in ['url','sha512']},'bytes':size,'status':200,'redirects':0,'tls_peer_and_hostname_verified':True,'content_length_and_eof_exact':True}
    b=members[binary_names[n]]; capture=json.loads(members['bootstrap-exports/'+tool+'-actual.json']); sha512=hashlib.sha512(b).hexdigest()
    assert len(b)==size and sha512==constants['BOOTSTRAP'][tool]['sha512'] and b==members[accepted] and len(set(b))==256
    assert capture=={'schema':1,'tool':tool,'container_path':path,'owned_cid':owned['prepare']['cid'],'role':'prepare','command_number':n,'maximum_bytes':16777216,'bytes':size,'sha256':digest(b),'sha512':sha512,'expected_sha512':sha512,'stdout_complete':True,'stderr_complete':True,'command_exit_code':0,'qualification':'bounded-public-command-stdout-only-before-host-size-and-digest-validation'}
    literal='path = '+json.dumps(path)+'; true = File.stat!(path).size <= 16777216; :ok = :io.setopts(:standard_io, encoding: :latin1); :ok = IO.binwrite(File.read!(path))'
    assert exec_tail(n)==['/usr/local/bin/elixir','-e',literal] and logs[n-1]['stdout_artifact']==binary_names[n]
    export_bindings[tool]={**binding(b),'sha512':sha512,'command':n,'all256_byte_values':True}
assert boot['hex_version']=='2.5.1' and boot['rebar_version']=='rebar 3.28.0 on Erlang/OTP 29 Erts 17.1\n' and boot['exact_rebar_path']=='/workspace/tooling/rebar3'
assert boot['rebar_transfer']=={'source':'/workspace/downloads/rebar3','destination':'/workspace/tooling/rebar3','download_bytes':823379,'copied_bytes':823379,'target_bytes':823379,'sha512':constants['BOOTSTRAP']['rebar']['sha512'],'exclusive_create':True,'closed_before_hash':True,'owned_download_removed':True}
assert exec_tail(32)==['/usr/local/bin/mix','deps.get','--check-locked']
prepared_manifest=marker(34,'prepared-manifest.json'); restored=marker(62); after=marker(89)
assert prepared_manifest==restored and set(prepared_manifest)=={'source','deps','tools','helpers'} and prepared_manifest['source']==frozen
prepared=safe_tar(members['prepared-source-dependencies-tools.tar']); combined={}
for section,rows in prepared_manifest.items():
    for p,e in rows.items():
        assert p not in combined and not any(part in {'_build','evidence','downloads','home','cache'} or part.startswith('mixer-key-owner-tls-') for part in PurePosixPath(p).parts)
        combined[p]=e
assert {p:binding(b) for p,b in prepared.items()}==combined and prepared_manifest['helpers']=={p:binding(b) for p,b in helpers.items()}
assert all(prepared[p]==b for p,b in product.items()) and all(prepared[p]==b for p,b in helpers.items())
assert hashlib.sha512(prepared['tooling/rebar3']).hexdigest()==constants['BOOTSTRAP']['rebar']['sha512']
out=io.BytesIO()
with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as archive:
    for p,b in sorted({**product,**helpers}.items()):
        m=tarfile.TarInfo(p); m.size,m.mode,m.mtime=len(b),0o644,0; archive.addfile(m,io.BytesIO(b))
for n,body in [(20,out.getvalue()),(54,members['prepared-source-dependencies-tools.tar'])]:
    assert exec_tail(n)==['/usr/bin/tar','--extract','--file','-','--directory','/workspace','--no-same-owner','--no-same-permissions'] and logs[n-1]['stdin_bytes']==len(body) and logs[n-1]['stdin_sha256']==digest(body)
namespace=marker(64,'test-namespace.json'); assert namespace['interfaces']==['lo'] and namespace['default_routes']==[] and namespace['routes']==[] and namespace['netns']!=host['netns'] and namespace['public_address']=='8.8.8.8' and namespace['setup_socket_closed'] and namespace['open_setup_sockets']==0
assert all(namespace[k]=='0000000000001400' for k in ['cap_eff','cap_prm','cap_bnd'])
database=json.loads(members['database-before.json']); assert json.loads(members['logs/0081.stdout'])==database=={'server_version_num':'160015','timezone':'UTC','database':'mixer_startup_test','databases':['mixer_startup_test','postgres','template0','template1']}
pg=json.loads(members['postgres-process.json']); assert pg['namespace']==namespace['netns']==members['logs/0071.stdout'].decode().strip() and pg['version']==members['logs/0073.stdout'].decode() and '16.15' in pg['version']
uids=next(line.split()[1:] for line in members['logs/0083.stdout'].decode().splitlines() if line.startswith('Uid:')); assert uids==pg['uid_fields']==['999']*4
assert exec_tail(85)==['/usr/local/bin/mix','deps.compile'] and exec_tail(87)==['/usr/local/bin/mix','compile','--warnings-as-errors'] and exec_tail(89)==['/usr/local/bin/elixir','/workspace/collector-manifest.exs']
diff=[]
for section in sorted(set(prepared_manifest)|set(after)):
    for p in sorted(set(prepared_manifest[section])|set(after[section])):
        if prepared_manifest[section].get(p)!=after[section].get(p): diff.append({'section':section,'path':p,'before':prepared_manifest[section].get(p),'after':after[section].get(p)})
assert diff==[{'section':'deps','path':'hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl/source.dag','before':None,'after':{'bytes':895,'sha256':'71360df95b056715d6215b91ba581e4dd91d850f4894c13720f142075a53d685'}}]
assert all('MIXER_ISOLATED_NETNS=1' not in r['argv'] for r in logs)
assert not any(n in members for n in ['before-tests-manifest.json','test-authorization.json','observer-events.jsonl','loaded-runtime.json','applied-migrations.json'])
assert state['status']=='FAILED-or-partial' and state['primary_outcome_frozen'] and not state['cancelled'] and state['primary_failure']=={'message':'source/dependency/tool mutation','type':'CollectorError'}
assert state['cleanup']=={'container_teardown_is_product_lifecycle_proof':False,'errors':[],'status':'verified-exact-created-IDs-absent','unresolved_creates':[]}
assert state['host_scratch_cleanup']=='removed owned .scratch; package outputs retained' and finalizer=={'cleanup_verified':True,'no_retry_of_identity_lost_or_unknown_create':True,'primary_status':'FAILED-or-partial','same_original_aggregate_deadline':True,'schema':1}
assert 'Ran 111 tests in 1.021s' in (ROOT/'job.log').read_text()
docker=json.loads(members['logs/0009.stdout']); assert docker['Client']['Version']==docker['Server']['Version']=='28.0.4'
for name in set(members)-{f'logs/{n:04d}.stdout' for n in range(2,8)}: retained('artifact/'+name,members[name])
for label,files in [('collector-source',controls),('literal-helpers',helpers),('selected-contract-metadata',metadata)]:
    for name,body in files.items(): retained(label+'/'+name,body)
for p in ['hosted/deps/telemetry/rebar.config','hosted/deps/telemetry/src/telemetry.app.src']:
    if p in prepared: retained('prepared-selected/'+p,prepared[p])
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':{'model':'gpt-6-astra','reasoning_effort':'xhigh','python':platform.python_version()},'source_revision':SHA,'source_tree':TREE,'run_id':run['id'],'run_attempt':1,'artifact_id':artifact_meta['id'],'zip':binding(data),'members':len(members),'expanded_bytes':expanded,'artifact_manifest_files':len(observed),'artifact_tree_digest_sha256':manifest['tree_digest_sha256'],'source_files_verified':4,'metadata_files_verified':104,'helpers_verified':7,'product_files_verified':177,'product_digest':constants['FROZEN_PRODUCT_DIGEST'],'commands_verified':107,'raw_log_bytes':raw_bytes,'all_command_streams_retained_and_complete':True,'remote_host':host,'remote_docker':docker,'remote_controls':{'tests':111,'seconds':1.021,'failures':0},'bootstrap_exports':export_bindings,'prepared_archive':{**binding(members['prepared-source-dependencies-tools.tar']),'files':len(prepared),'section_counts':{s:len(r) for s,r in prepared_manifest.items()}},'container_inspections':inspect_counts,'actual_mount_policy':['prepare','test'],'offline_dependencies_and_compile_exit_zero':True,'first_failure':{'after_command':89,'message':state['primary_failure']['message'],'manifest_diff':diff,'classification':'strict precompile dependency manifest includes newly generated Rebar source.dag; source unchanged is not established by comparing entire deps trees across compilation'},'cleanup':cleanup,'finalizer':finalizer,'product_methods_run':0,'not_run':['compiled module identity collection','test authorization','two production-DNS/TLS methods','semantic receipts','current-ten migration check','post-test source/key cleanup checks'],'limitations':['new source.dag content not retained; its observed hash and length are retained','full mountinfo bytes absent; source-bound selected lines and whole-read hash retained','dependency compiler warnings retained despite exit zero','container stop/absence is not product lifecycle proof','all native/process/custody/provider/customer/release/GA holds remain'],'local_runtime_or_ci_actions':False,'command':'python3 -B verification/github-delivery-binary-export-and-ui/network-review/verify_artifact.py','alarm_seconds':50,'git_timeout_seconds':20,'script_sha256':digest(Path(__file__).read_bytes())}
put('manifest-diff.json',diff); put('verification-result.json',result)
print(json.dumps({'status':'failed-run-evidence-verified','artifact_tree':manifest['tree_digest_sha256'],'binary_export':'exact pinned Hex and Rebar passed','new_failure':'one generated telemetry/Rebar source.dag added after compile','cleanup':'three exact owned CIDs absent','product_methods_run':0},indent=2))
