#!/usr/bin/env python3
"""Pure offline review; artifact bytes are never executed or deserialized as code."""
import sys
def audit(event,args):
 if event.startswith(('socket.','subprocess.')) or event in {'os.system','os.fork','os.posix_spawn','pty.spawn'}:raise RuntimeError('offline audit denied '+event)
sys.addaudithook(audit)
import ast,datetime,hashlib,io,json,platform,re,signal,stat,tarfile,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
SHA='86a96a4ba6c14e45be41999873f00d5788bbc649'
TREE='0e4df024715e23aefe3aa7635c6829df5d4e85fa'
CAP=256*1024*1024
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('40 second offline review bound')));signal.alarm(40)
def digest(b):return hashlib.sha256(b).hexdigest()
def binding(b):return {'bytes':len(b),'sha256':digest(b)}
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def put(n,v):(ROOT/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def safe_name(n):
 assert isinstance(n,str) and n and not n.startswith('/') and '\\' not in n and ':' not in n and '\x00' not in n
 assert all(p not in ('','.','..') for p in n.split('/')) and str(PurePosixPath(n))==n
def safe_tar(raw,mtime=None):
 result,folded,total={},set(),0
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as t:
  for m in t.getmembers():
   safe_name(m.name);assert m.name not in result and m.name.casefold() not in folded
   assert m.isfile() and not m.linkname and not m.pax_headers and 0<=m.size<=CAP
   if mtime is not None:assert m.mtime==mtime
   total+=m.size;assert total<=CAP
   b=t.extractfile(m).read(CAP+1);assert len(b)==m.size
   result[m.name]=b;folded.add(m.name.casefold())
 return result
raw=(ROOT/'network-artifact.zip').read_bytes()
assert binding(raw)=={'bytes':11899520,'sha256':'117286f93e1df7773ff59bb6586688d810440b0f1a0726ddba9027b791758385'}
members,folded,expanded={},set(),0
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 for x in z.infolist():
  safe_name(x.filename);assert x.filename not in members and x.filename.casefold() not in folded
  assert not x.is_dir() and not x.flag_bits&1 and stat.S_IFMT(x.external_attr>>16) in (0,stat.S_IFREG)
  expanded+=x.file_size;assert 0<=x.file_size<=CAP and expanded<=CAP
  b=z.read(x);assert len(b)==x.file_size and (ROOT/'network'/x.filename).read_bytes()==b
  members[x.filename]=b;folded.add(x.filename.casefold())
assert len(members)==442
def j(n):return json.loads(members[n])
manifest=j('artifact-manifest.json');observed={n:binding(b) for n,b in members.items() if n!='artifact-manifest.json'}
assert manifest['files']==observed and manifest['tree_digest_sha256']==digest(canonical(observed))
controls=safe_tar(members['collector-source.tar']);assert len(controls)==4
assert digest(controls['hosted/scripts/test-identity-network.py'])=='e5c33b3f2ade996b5c43e5574469dc6f43da2e8b3a3bb5a4109e2f53b60b0f20'
assert j('collector-source-bindings.json')=={p:binding(b) for p,b in controls.items()}
c={}
def literals(node):
 if isinstance(node,ast.Name):return c[node.id]
 if isinstance(node,ast.Dict):
  v={}
  for key,value in zip(node.keys,node.values):
   if key is None:v.update(literals(value))
   else:v[ast.literal_eval(key)]=literals(value)
  return v
 return ast.literal_eval(node)
for node in ast.parse(controls['hosted/scripts/test-identity-network.py']).body:
 if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
  try:c[node.targets[0].id]=literals(node.value)
  except (ValueError,TypeError,KeyError):pass
frozen=c['FROZEN_MANIFEST'];predecessor=c['PREDECESSOR_MANIFEST']
assert len(frozen)==178 and j('product-source-manifest.json')==frozen
assert digest(canonical(frozen))==c['SELECTED_SOURCE_DIGEST']=='ab8f8dbec5894ca96dd673db828a01afdc39a54ad008a2a2d4e598c1c62ce2f7'
assert len(predecessor)==177 and digest(canonical(predecessor))==c['FROZEN_PRODUCT_DIGEST']=='023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e'
logs=[j('logs/%04d.json'%n) for n in range(1,136)]
def parse_batch(n,paths):
 b=members['logs/%04d.stdout'%n];cursor=0;result={};request=''.join(SHA+':'+p+'\n' for p in paths).encode()
 assert logs[n-1]['argv']==['git','--no-replace-objects','cat-file','--batch']
 assert logs[n-1]['stdin_bytes']==len(request) and logs[n-1]['stdin_sha256']==digest(request)
 for p in paths:
  end=b.index(b'\n',cursor);oid,kind,size=b[cursor:end].split();assert kind==b'blob' and re.fullmatch(b'[0-9a-f]{40}',oid)
  cursor=end+1;body=b[cursor:cursor+int(size)]
  assert len(body)==int(size) and hashlib.sha1(b'blob '+size+b'\x00'+body).hexdigest().encode()==oid
  result[p]=body;cursor+=int(size);assert b[cursor:cursor+1]==b'\n';cursor+=1
 assert cursor==len(b)
 return result
product=parse_batch(2,sorted(frozen));assert {p:binding(b) for p,b in product.items()}==frozen
control_paths=['hosted/scripts/test-identity-network.py','hosted/scripts/test_identity_network_collector.py','docs/hosted-identity-production-network-ci-contract.md','.github/workflows/identity-network.yml']
assert parse_batch(3,control_paths)==controls
oldbase,imagebase,execbase,fixturebase=[c[k] for k in ['CONTRACT_BASE','AMENDMENT_BASE','EXECUTION_BASE','FIXTURE_BASE']]
packetpaths=[oldbase+'contract.json',oldbase+'packet-manifest.json']
for image in ['elixir','postgres']:packetpaths.extend(oldbase+'inputs/registry/'+image+s for s in ['-index.json','-amd64-manifest.json','-amd64-config.json'])
iseal=parse_batch(4,[imagebase+'packet-manifest.json']);ip=json.loads(iseal[imagebase+'packet-manifest.json'])
assert len(ip['files'])==78 and digest(canonical(ip['files']))==ip['tree_digest_sha256']==c['AMENDMENT_PACKET']
ifiles=parse_batch(5,packetpaths+[imagebase+p for p in ip['files']])
eseal=parse_batch(6,[execbase+'packet-manifest.json']);ep=json.loads(eseal[execbase+'packet-manifest.json'])
assert len(ep['files'])==16 and digest(canonical(ep['files']))==ep['tree_digest_sha256']==c['EXECUTION_PACKET']
assert digest(eseal[execbase+'packet-manifest.json'])==c['EXECUTION_PACKET_SHA256']
efiles=parse_batch(7,[execbase+p for p in ep['files']])
fseal=parse_batch(8,[fixturebase+'packet-manifest.json']);fp=json.loads(fseal[fixturebase+'packet-manifest.json'])
assert len(fp['files'])==18 and digest(canonical(fp['files']))==fp['tree_digest_sha256']==c['FIXTURE_PACKET']
assert digest(fseal[fixturebase+'packet-manifest.json'])==c['FIXTURE_PACKET_SHA256']
ffiles=parse_batch(9,[fixturebase+p for p in fp['files']])
metadata={**iseal,**ifiles,**eseal,**efiles,**fseal,**ffiles};assert len(metadata)==123
assert safe_tar(members['selected-contract-metadata.tar'])==metadata
for base,packet in [(imagebase,ip),(execbase,ep),(fixturebase,fp)]:
 for p,b in packet['files'].items():assert binding(metadata[base+p])==b
op=json.loads(metadata[oldbase+'packet-manifest.json'])
assert digest(metadata[oldbase+'packet-manifest.json'])==c['CONTRACT_PACKET_SHA256']
assert op['tree_digest_sha256']==digest(canonical(op['files']))==c['CONTRACT_PACKET']
assert digest(metadata[oldbase+'contract.json'])==c['CONTRACT_SHA256']
for p in packetpaths:
 if p!=oldbase+'packet-manifest.json':assert op['files'][p[len(oldbase):]]==binding(metadata[p])
amend=json.loads(metadata[imagebase+'image-amendment.json'])
assert digest(metadata[imagebase+'image-amendment.json'])==c['AMENDMENT_SHA256']
assert digest(metadata[execbase+'execution-amendment.json'])==c['EXECUTION_SHA256']
fixture=json.loads(metadata[fixturebase+'source-amendment.json'])
assert digest(metadata[fixturebase+'source-amendment.json'])==c['FIXTURE_SHA256']
assert json.loads(metadata[fixturebase+'predecessor-source-manifest.json'])==predecessor
assert json.loads(metadata[fixturebase+'selected-source-manifest.json'])==frozen
fixturepath='hosted/test/support/identity_tls_fixture.ex';controlpath='hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs'
delta={fixturepath:{'operation':'replace','before':predecessor[fixturepath],'after':frozen[fixturepath]},controlpath:{'operation':'add','before':None,'after':frozen[controlpath]}}
assert fixture['exact_delta']==delta and set(frozen)-set(predecessor)=={controlpath}
assert {p for p in predecessor if predecessor[p]!=frozen[p]}=={fixturepath}
assert frozen[fixturepath]['sha256']=='d3b55796a8baac4f9ebd37cc9ee5e44bde01ca346ce2dd00a0a5dd884711ba55'
assert frozen[controlpath]['sha256']=='417704f8e805196f9546a508a770d23a55d40ce9d6214be5225f131c4bd2c7c6'
rootbindings=json.loads((ROOT.parent/'source-bindings.json').read_bytes())
assert rootbindings['effective_sources_verified']==178 and rootbindings['effective_digest']==c['SELECTED_SOURCE_DIGEST'] and rootbindings['exact_delta']==delta
reviewbase=fixturebase+'independent-review/';reviewpacket=json.loads(metadata[reviewbase+'packet-manifest.json'])
assert digest(metadata[reviewbase+'packet-manifest.json'])==c['FIXTURE_REVIEW_SHA256']
assert digest(canonical(reviewpacket['files']))==reviewpacket['tree_digest_sha256']==c['FIXTURE_REVIEW_PACKET']
for p,row in reviewpacket['files'].items():assert binding(metadata[reviewbase+p])==row
review=json.loads(metadata[reviewbase+'review.json']);assert review['status']=='source-qualified-accept-for-root-promotion-runtime-unrun' and review['source_blockers']==[]
candidate=review['selected_candidate'];assert candidate['source_count']==178 and candidate['source_digest_sha256']==c['SELECTED_SOURCE_DIGEST']
assert candidate['fixture']=={'path':fixturepath,**frozen[fixturepath]} and candidate['control']=={'path':controlpath,**frozen[controlpath]}
assert fixture['integration_patch']['sha256']==candidate['integration_patch_sha256']==digest(metadata[fixturebase+'integration-candidate.patch'])
assert len(fixture['ordinary_phoenix_controls'])==4 and fixture['remote_execution_only'] and fixture['runtime_or_GA_accepted'] is False
assert canonical(fixture['preserved']['expected_methods'])==canonical(c['EXPECTED_METHODS']) and canonical(fixture['preserved']['test_roots'])==canonical(c['TEST_ROOTS'])
assert fixture['preserved']['original_test_files']=={'hosted/'+p:frozen['hosted/'+p] for p in c['TEST_ROOTS']}
assert all(predecessor['hosted/'+p]==frozen['hosted/'+p] for p in c['TEST_ROOTS'])
helpers={'collector-'+name+'.exs':c[key].encode() for name,key in [('prerequisites','PREREQUISITES_EXS'),('bootstrap','BOOTSTRAP_EXS'),('manifest','MANIFEST_EXS'),('netns','NETNS_EXS'),('observer','OBSERVER_EXS'),('mounts','MOUNTS_EXS')]}
bootstrap=c['BOOTSTRAP_EXS']
for k,v in {'HEX_URL':c['BOOTSTRAP']['hex']['url'],'HEX_SHA':c['BOOTSTRAP']['hex']['sha512'],'REBAR_URL':c['BOOTSTRAP']['rebar']['url'],'REBAR_SHA':c['BOOTSTRAP']['rebar']['sha512']}.items():bootstrap=bootstrap.replace(k,v)
helpers['collector-bootstrap.exs']=bootstrap.encode();helpers['frozen-manifest.json']=canonical(frozen)
assert len(helpers)==7 and safe_tar(members['literal-helpers.tar'])==helpers
assert j('literal-helper-bindings.json')==fixture['literal_helpers']=={p:binding(b) for p,b in helpers.items()}
state,host,finalizer=j('state.json'),j('host.json'),j('finalizer.json')
run=json.loads((ROOT/'40775131359-meta-metadata.json').read_bytes());art=json.loads((ROOT/'40775131359-artifacts-metadata.json').read_bytes())['artifacts'][0]
job,=json.loads((ROOT/'40775131359-jobs-metadata.json').read_bytes())['jobs']
assert run['id']==40775131359 and run['head_sha']==SHA and run['head_commit']['tree_id']==TREE and run['event']=='push' and run['run_attempt']==1 and run['conclusion']=='success'
assert art['id']==12853449249 and art['workflow_run']['id']==run['id'] and art['workflow_run']['head_sha']==SHA and art['digest']=='sha256:'+digest(raw)
assert job['id']==123122340950 and job['run_id']==run['id'] and job['conclusion']=='success'
assert state['sha']==SHA and state['run_id']==str(run['id']) and state['attempt']=='1' and state['command_number']==135
assert host['github_run_id']==state['run_id'] and host['attempt']=='1' and host['uname'][0]=='Linux' and host['uname'][-1]=='x86_64'
assert state['source']['delivery_revision']==SHA and state['source']['product_tree_digest_sha256']==c['SELECTED_SOURCE_DIGEST'] and state['source']['product_files']==178
assert state['source']['predecessor_product_tree_digest_sha256']==c['FROZEN_PRODUCT_DIGEST'] and state['source']['predecessor_product_files']==177
for f,k in [('image_amendment_sha256','AMENDMENT_SHA256'),('image_amendment_packet_sha256','AMENDMENT_PACKET'),('image_source_review_packet_sha256','SOURCE_REVIEW_PACKET'),('execution_amendment_sha256','EXECUTION_SHA256'),('execution_amendment_packet_sha256','EXECUTION_PACKET'),('fixture_amendment_sha256','FIXTURE_SHA256'),('fixture_amendment_packet_sha256','FIXTURE_PACKET'),('fixture_review_packet_sha256','FIXTURE_REVIEW_PACKET')]:assert state['source'][f]==c[k]
binary={30:'bootstrap-exports/hex-actual.bin',32:'bootstrap-exports/rebar-actual.bin',40:'prepared-source-dependencies-tools.tar',95:'compiler-generated/telemetry-source.dag',105:'observer-events.jsonl',107:'production-DNS-rebinding.json',109:'startup-production-network.json',111:'loaded-runtime.json'}
rawbytes=0
for n,x in enumerate(logs,1):
 expected=1 if n in [49,126,135] else 2 if n in [77,79,81] else 0
 assert x['exit_code']==expected and x.get('failure') is None and not x['timed_out'] and not x['overflow']
 assert x['elapsed_seconds']<x['timeout_seconds'] and x['stdout_complete'] and x['stderr_complete']
 assert x['cwd']=='/home/runner/work/mixer/mixer'
 assert x['host_environment']=={'DOCKER_CONFIG':'/home/runner/work/mixer/mixer/identity-network-evidence/.scratch/docker','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','HOME':'/home/runner/work/mixer/mixer/identity-network-evidence/.scratch','LANG':'C.UTF-8','PATH':'/usr/local/bin:/usr/bin:/bin'}
 for ext in ['stdout','stderr']:
  name=binary[n] if n in binary and ext=='stdout' else 'logs/%04d.%s'%(n,ext)
  b=members[name];assert x[ext+'_bytes']==len(b)
  if n in binary and ext=='stdout':assert x['stdout_sha256']==digest(b)
  else:rawbytes+=len(b)
assert rawbytes==state['log_bytes']==10646217
assert members['logs/0001.stdout'].decode().strip()==SHA
def tail(n):
 a=logs[n-1]['argv'];i=a.index('/usr/bin/env')+2
 while '=' in a[i]:i+=1
 return a[i:]
def marker(n,name=None):
 b=members['logs/%04d.stdout'%n];assert b.startswith(b'IDENTITY_JSON=') and members['logs/%04d.stderr'%n]==b''
 v=json.loads(b[len(b'IDENTITY_JSON='):].strip())
 if name:assert j(name)==v
 return v
owned={x['role']:x for x in state['containers']};assert set(owned)=={'prepare','test','pg'} and not state['unresolved_creates']
inspects={role:0 for role in owned};snapshots={};cleanup={}
pg_env={'PATH':c['BASE_ENV']['PATH']+':/usr/lib/postgresql/16/bin','GOSU_VERSION':'1.19','LANG':'en_US.utf8','PG_MAJOR':'16','PG_VERSION':'16.15-1.pgdg12+2','PGDATA':'/var/lib/postgresql/data','POSTGRES_USER':'mixer_fixture','POSTGRES_DB':'mixer_startup_test','POSTGRES_HOST_AUTH_METHOD':'trust'}
envs={'prepare':c['BASE_ENV'],'test':c['BASE_ENV'],'pg':pg_env}
for role,row in owned.items():
 cid=row['cid'];assert re.fullmatch('[0-9a-f]{64}',cid) and row['state']=='removed'
 assert row['name']==state['label']+'-'+role and row['label']==state['label'] and row['image_id']==c['IMAGES']['pg' if role=='pg' else 'test']['config']
 for n,x in enumerate(logs,1):
  a=x['argv']
  if a==['docker','container','inspect',cid] and x['exit_code']==0:
   actual,=json.loads(members['logs/%04d.stdout'%n]);snapshots[n]=actual;inspects[role]+=1
   assert actual['Id']==cid and actual['Image']==row['image_id'] and actual['Name']=='/'+row['name']
   assert actual['Config']['Labels']=={'mixer.identity.role':role,'mixer.identity.run':row['label']}
   cfg=actual['HostConfig'];assert cfg['ReadonlyRootfs'] is True and cfg['Privileged'] is False and cfg['Tmpfs']==c['TMPFS'][role] and actual['Mounts']==[]
   assert cfg['NetworkMode']=={'prepare':'bridge','test':'none','pg':'container:'+owned['test']['cid']}[role]
   assert cfg['SecurityOpt']==['no-new-privileges:true'] and cfg['CapDrop']==['ALL']
   assert {v.removeprefix('CAP_') for v in cfg['CapAdd'] or []}==c['CAPS'][role]
   memory,cpus,pids=c['RESOURCES'][role];assert cfg['Memory']==cfg['MemorySwap']==memory and cfg['NanoCpus']==cpus*10**9 and cfg['PidsLimit']==pids
   ev=dict(v.split('=',1) for v in actual['Config']['Env']);assert len(ev)==len(actual['Config']['Env']) and ev==envs[role]
   assert cfg['Ulimits']==[{'Name':'nofile','Hard':4096,'Soft':4096}]
   for k in ['Binds','Devices','DeviceRequests','PortBindings','VolumesFrom','ExtraHosts','Links']:assert not cfg[k]
   for k in ['PidMode','IpcMode','UTSMode','UsernsMode']:assert cfg[k]!='host'
   assert not any((actual['NetworkSettings']['Ports'] or {}).values()) and not actual['State']['OOMKilled']
  if a[:2]==['docker','exec'] and cid in a:
   i=a.index(cid);ev=j('test-authorization.json')['allowed_environment'] if n==103 else envs[role]
   expected=['docker','exec',*(['-i'] if '-i' in a[:i] else []),'--workdir',a[a.index('--workdir')+1],*[v for k,value in sorted(ev.items()) for v in ['--env',k+'='+value]],cid,'/usr/bin/env','-i',*[k+'='+v for k,v in sorted(ev.items())]]
   assert a[:len(expected)]==expected
 create={'prepare':16,'test':50,'pg':67}[role];a=logs[create-1]['argv']
 assert a[:2]==['docker','create'] and a[a.index('--name')+1]==row['name'] and members['logs/%04d.stdout'%create]==(cid+'\n').encode()
 stop,terminal,remove,absence={'prepare':(43,44,48,49),'pg':(120,121,125,126),'test':(129,130,134,135)}[role]
 assert logs[stop-1]['argv']==['docker','stop','--time','2',cid] and logs[remove-1]['argv']==['docker','rm','--volumes',cid]
 terminal_row=j(role+'-terminal.json');assert terminal_row==snapshots[terminal] and not terminal_row['State']['Running'] and terminal_row['State']['Pid']==0 and not terminal_row['State']['OOMKilled']
 assert logs[absence-1]['argv']==['docker','container','inspect',cid] and members['logs/%04d.stdout'%absence]==b'[]\n' and members['logs/%04d.stderr'%absence]==('Error response from daemon: No such container: '+cid+'\n').encode()
 cleanup[role]={'cid':cid,'stop_command':stop,'terminal_command':terminal,'remove_command':remove,'absence_command':absence,'terminal_exit':terminal_row['State']['ExitCode'],'exact_absence_verified':True}
assert 49<50 and len([x for x in logs if x['argv'][:2]==['docker','create']])==3
for role,n in [('prepare',24),('test',58)]:
 m=marker(n,role+'-mount-policy.json');paths=c['MOUNT_POLICY']['roles'][role]
 assert m['source']=='/proc/self/mountinfo' and m['role']==role and 0<m['read_bytes']<=65536
 assert m['path_modes']=={p:c['MOUNT_POLICY']['modes'][p] for p in paths} and len(m['selected_lines'])==len(paths)
 seen=set()
 for line in m['selected_lines']:
  left,right=line.split(' - ');f=left.split();r=right.split();p=f[4];flags=set(f[5].split(','));sup=set(r[2].split(','))
  assert p in paths and p not in seen and r[:2]==['tmpfs','tmpfs'] and {'rw','nosuid','nodev'}<=flags
  assert ('noexec' not in flags|sup) if p=='/workspace/tooling' else ('noexec' in flags)
  seen.add(p)
for role,n in [('prepare',26),('test',62)]:
 p=marker(n,role+'-prerequisites.json');e=amend['prerequisites']
 assert p['elixir']==e['elixir']=='1.20.4' and p['otp_patch']==e['otp_patch']=='29.1.1' and p['tools']==e['tools'] and len(p['tools'])==7
 assert p['ca']['loaded_count']==150 and p['ca']['loaded_der_sha256']==e['ca']['der_sha256'] and p['ca']['sha256']==e['ca']['sha256']
boot=marker(28,'bootstrap-observed.json')
for tool,n,size in [('hex',30,1133941),('rebar',32,823379)]:
 b=members[binary[n]];cap=j('bootstrap-exports/'+tool+'-actual.json')
 assert len(b)==size and hashlib.sha512(b).hexdigest()==c['BOOTSTRAP'][tool]['sha512'] and len(set(b))==256
 assert cap['bytes']==size and cap['sha256']==digest(b) and cap['sha512']==hashlib.sha512(b).hexdigest() and cap['command_number']==n and cap['owned_cid']==owned['prepare']['cid']
 assert boot[tool]['status']==200 and boot[tool]['redirects']==0 and boot[tool]['tls_peer_and_hostname_verified'] and boot[tool]['content_length_and_eof_exact']
prepared=marker(36,'prepared-manifest.json');restored=marker(64)
assert prepared==restored and set(prepared)=={'source','deps','tools','helpers'} and prepared['source']==frozen
archive=safe_tar(members['prepared-source-dependencies-tools.tar'],mtime=1);assert len(archive)==1233;combined={}
for section,rows in prepared.items():
 for p,e in rows.items():
  assert p not in combined and not any(x in {'_build','evidence','downloads','home','cache'} or x.startswith('mixer-key-owner-tls-') for x in PurePosixPath(p).parts)
  combined[p]=e
assert {p:binding(b) for p,b in archive.items()}==combined
assert prepared['helpers']=={p:binding(b) for p,b in helpers.items()}
assert all(archive[p]==b for p,b in {**product,**helpers}.items())
assert hashlib.sha512(archive['tooling/rebar3']).hexdigest()==c['BOOTSTRAP']['rebar']['sha512']
namespace=marker(66);assert namespace['interfaces']==['lo'] and namespace['default_routes']==[] and namespace['routes']==[] and namespace['netns']!=host['netns'] and namespace['setup_socket_closed'] and namespace['open_setup_sockets']==0
assert marker(101,'test-namespace.json')==namespace
database=j('database-before.json');assert json.loads(members['logs/0085.stdout'])==database and database['server_version_num']=='160015'
uids=next(line.split()[1:] for line in members['logs/0087.stdout'].decode().splitlines() if line.startswith('Uid:'));assert uids==j('postgres-process.json')['uid_fields']==['999']*4
assert tail(89)==['/usr/local/bin/mix','deps.compile'] and tail(91)==['/usr/local/bin/mix','compile','--warnings-as-errors']
after=marker(93,'before-tests-manifest.json');assert set(after)=={'source','deps','tools','helpers'}
for section in ['source','tools','helpers']:assert after[section]==prepared[section]
generated_path='hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl/source.dag'
assert generated_path not in prepared['deps'] and set(after['deps'])-set(prepared['deps'])=={generated_path}
assert {p:v for p,v in after['deps'].items() if p!=generated_path}==prepared['deps']
row=after['deps'][generated_path];dag=members['compiler-generated/telemetry-source.dag'];cap=j('compiler-generated/telemetry-source.json')
assert binding(dag)=={'bytes':890,'sha256':'eadc501c6bb1af53b7b94361e9fd888928b6f1f67f37d3c67615488d051d2b13'}
assert row['bytes']==len(dag) and row['sha256']==digest(dag) and row['type']=='regular' and row['mode']==0o644 and row['uid']==row['gid']==0 and row['links']==1
assert set(row['parents'])=={'/workspace','/workspace/hosted','/workspace/hosted/deps','/workspace/hosted/deps/telemetry','/workspace/hosted/deps/telemetry/_build','/workspace/hosted/deps/telemetry/_build/prod','/workspace/hosted/deps/telemetry/_build/prod/lib','/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3','/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl'}
assert all(v=={'gid':0,'uid':0,'mode':0o755,'type':'directory'} for v in row['parents'].values())
assert cap['expected_manifest_row']==row and cap['command_number']==95 and cap['owned_cid']==owned['test']['cid'] and cap['role']=='test' and cap['phase']=='after-offline-compile-before-test-authorization'
assert cap['bytes']==len(dag) and cap['sha256']==digest(dag) and cap['stdout_complete'] and cap['stderr_complete'] and cap['command_exit_code']==0
assert tail(95)==['/usr/local/bin/elixir','/workspace/collector-manifest.exs','export-generated']
validation=j('compiled-input-validation.json');assert validation['prepared_inputs_unchanged'] and validation['remaining_dependency_entries_unchanged'] and validation['generated_output_was_absent_before_compile'] and validation['artifact_contents_interpreted_or_executed'] is False
assert validation['prepared_manifest_sha256']==digest(canonical(prepared)) and validation['compiled_manifest_sha256']==digest(canonical(after))
assert validation['generated_output']['sha256']==digest(dag) and validation['generated_output']['bytes']==len(dag)
beams=marker(97,'compiled-modules-before-tests.json');assert len(beams)==955 and any(p.endswith('/jose_jwk.beam') for p in beams)
expected_erl={PurePosixPath(p).stem for p in archive if p.startswith('hosted/deps/jose/src/') and p.endswith('.erl')}
actual_erl={PurePosixPath(p).stem for p in beams if '/jose/ebin/jose' in p};assert len(expected_erl)==113 and actual_erl==expected_erl
assert b'==> jose\nCompiling 113 files (.erl)\nCompiling 8 files (.ex)\nGenerated jose app' in members['logs/0089.stdout']
auth=j('test-authorization.json');assert auth['source_unchanged'] and auth['assertions_before_flag'] and auth['mount_policy_observed'] and auth['prerequisites_observed'] and auth['owned_test_cid']==owned['test']['cid'] and auth['owned_pg_cid']==owned['pg']['cid']
assert auth['generated_output']==validation['generated_output']
assert tail(103)==['/usr/local/bin/elixir','-r','/workspace/collector-observer.exs','-S','mix','test','--warnings-as-errors','--seed','0','--trace','--no-color','--formatter','ExUnit.CLIFormatter','--formatter','MixerIdentityNetworkCollector.Observer',*c['TEST_ROOTS']]
events=[json.loads(line) for line in members['observer-events.jsonl'].splitlines()]
assert [x['event'] for x in events]==['suite_started','test_started','test_finished','test_started','test_finished','suite_finished']
assert events[-1]=={'invalid':0,'total':2,'failures':0,'skipped':0,'excluded':0,'event':'suite_finished'}
started=[x for x in events if x['event']=='test_started'];finished=[x for x in events if x['event']=='test_finished']
assert all(x['state'] is None for x in finished)
expected_names=[('Elixir.MixerHosted.Identity.KeyOwnerLinuxNetworkTest','test K03 production resolver/classifier pins public peer despite rebinding; private sink remains untouched'),('Elixir.MixerHosted.Identity.StartupLinuxNetworkTest','test IS04 IS05 actual configured startup cold production DNS TLS admission and lifecycle')]
assert [(x['module'],x['name']) for x in started]==expected_names and [(x['module'],x['name']) for x in finished]==expected_names
testout=members['logs/0103.stdout'].decode();assert 'Result: 2/2 passed' in testout and '0 failures' in testout
assert j('production-DNS-rebinding.json')=={'namespace':'disposable network-none Linux lo:1; no product resolver or loopback bypass','initialQueries':2,'authenticatedPeer':'8.8.8.8:443','publicConnections':1,'forbiddenSinkConnections':0,'newPrivateAnswerRejectedBeforeConnect':True}
assert j('startup-production-network.json')=={'resolver':'127.0.0.1:53','destination':'8.8.8.8:443','namespace':'owned Linux network-none NET_ADMIN; 8.8.8.8 on lo:1','actualApplication':True,'endpointLiveness':200,'startupDNSQueries':0,'startupConnections':0,'coldTokenAdmitted':True,'coldDNSQueries':2,'coldConnections':1,'oldLeaseRejectedAfterRestart':True,'restartColdAdmission':True,'shutdownInflightCancelled':True,'allThreeConnectionsClosed':True,'fixtureKeyDirectoryRemoved':True,'publicAdapter':'ConfiguredVerifier.authenticate/2','productionPolicyBypasses':0}
runtime=j('loaded-runtime.json');assert runtime['elixir']=='1.20.4' and runtime['otp_patch']=='29.1.1' and runtime['architecture']=='x86_64-pc-linux-gnu'
assert len(runtime['modules'])==745 and len({x['module'] for x in runtime['modules']})==745
loaded_product=[x for x in runtime['modules'] if x['path'].startswith('/workspace/hosted/_build/test/lib/') and '/ebin/' in x['path']]
assert all(beams[x['path']]==x['sha256'] for x in loaded_product)
jwk,=[x for x in runtime['modules'] if x['module']=='jose_jwk'];assert jwk['sha256']==beams[jwk['path']]
apps={x['application']:x['version'] for x in runtime['applications']};assert len(apps)==len(runtime['applications']) and apps['jose']=='1.11.13' and apps['mixer_hosted']=='0.1.0'
post=marker(113,'after-tests-manifest.json');assert post==after
assert marker(115,'key-directory-cleanup.json')=={'remaining_key_directories':[]}
migrations=j('applied-migrations.json');versions=sorted(int(PurePosixPath(p).name.split('_')[0]) for p in frozen if p.startswith('hosted/priv/repo/migrations/') and p.endswith('.exs'))
assert migrations=={'database':'mixer_startup_test','versions':versions} and len(versions)==10 and json.loads(members['logs/0117.stdout'])==versions
assert state['status']=='two-methods-passed-pending-owned-cleanup-and-independent-acceptance' and state['primary_outcome_frozen'] and not state['cancelled'] and 'primary_failure' not in state
assert state['test_result']=={'methods':2,'no_skips':True,'semantic_receipts':['production-DNS-rebinding.json','startup-production-network.json']}
assert state['cleanup']=={'container_teardown_is_product_lifecycle_proof':False,'errors':[],'status':'verified-exact-created-IDs-absent','unresolved_creates':[]}
assert finalizer=={'cleanup_verified':True,'no_retry_of_identity_lost_or_unknown_create':True,'primary_status':state['status'],'same_original_aggregate_deadline':True,'schema':1}
assert state['host_scratch_cleanup']=='removed owned .scratch; package outputs retained'
assert 'Ran 136 tests in 1.883s' in (ROOT/'network-job.log').read_text()
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'two-network-methods-qualified-ordinary-phoenix-controls-unrun','source_revision':SHA,'source_tree':TREE,'run_id':run['id'],'job_id':job['id'],'run_attempt':1,'artifact_id':art['id'],'zip':binding(raw),'members':len(members),'expanded_bytes':expanded,'artifact_tree_digest_sha256':manifest['tree_digest_sha256'],'control_sources_verified':4,'metadata_files_verified':123,'helpers_verified':7,'historical_product_files_verified':177,'historical_product_digest':c['FROZEN_PRODUCT_DIGEST'],'selected_product_files_verified':178,'selected_product_digest':c['SELECTED_SOURCE_DIGEST'],'exact_delta':delta,'source_amendment':{'sha256':c['FIXTURE_SHA256'],'packet_tree_digest_sha256':c['FIXTURE_PACKET'],'source_review_packet_sha256':c['FIXTURE_REVIEW_PACKET']},'commands_verified':135,'raw_log_bytes':rawbytes,'all_command_streams_retained_and_complete':True,'collector_controls':{'tests':136,'failures':0,'seconds':1.883},'prepared_archive':{'files':len(archive),'mtime_seconds':1,'source_and_input_bytes_unchanged_before_authorization':True},'generated_output':{'accepted':True,'raw_bytes_retained':True,'raw':binding(dag),'file_mode':'0644','parent_modes':'0755','all_input_sections_unchanged':True,'captured_before_authorization':True,'opaque_only':True},'compiled_modules':{'count':len(beams),'jose_erlang_sources':113,'jose_erlang_beams':113,'all_jose_erlang_source_basenames_match_beams':True,'jose_jwk_beam_present':True,'loaded_modules':len(runtime['modules']),'loaded_ebin_hashes_joined':len(loaded_product),'jose_jwk_loaded_and_hash_joined':True,'all_modules_loaded_individually_observed':False},'product_tests':{'invoked':2,'passed':2,'failed':0,'skipped':0,'excluded':0,'exact_named_methods':expected_names,'argv':tail(103),'result_source':'immutable observer events plus complete command103 output'},'K03_semantic_receipt':j('production-DNS-rebinding.json'),'startup_semantic_receipt':j('startup-production-network.json'),'applied_migrations':migrations,'post_test_inputs_unchanged':True,'key_directories_remaining':[],'cleanup':cleanup,'finalizer':finalizer,'remote_host':host,'local_python':platform.python_version(),'local_command':['/usr/bin/python3','-B',str(ROOT/'verify_network.py')],'script_sha256':digest(Path(__file__).read_bytes()),'local_alarm_seconds':40,'offline_audit_denies_network_and_children':True,'local_product_or_runtime_execution':False,'prior_failure_preserved':'verification/github-delivery-positive-timestamp/ci-review/ remains unchanged; prior startup close assertion failure is historical','pending':['four ordinary Phoenix TLS lifecycle controls; failed formatter prevented execution','ordinary Phoenix compile and 701 tests with two network skips remain unproven','all preexisting native/process/custody/provider/customer/release/GA holds'],'limitations':['synthetic remote Linux network-none scope; no provider/customer/GA acceptance','955 beam hashes and 113 JOSE Erlang basename matches do not prove every module was loaded','selected mountinfo lines and whole-read digest retained; full mountinfo bytes absent','container cleanup is not product lifecycle proof','four new ordinary controls were not invoked by the deliberately unchanged two-network-method argv']}
put('network-verification-result.json',result)
print(json.dumps({k:result[k] for k in ['status','source_revision','selected_product_digest','commands_verified','product_tests','cleanup']},indent=2))
