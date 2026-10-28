#!/usr/bin/env python3
"""Materialize the closed tooling-tmpfs amendment; source evidence only."""
from pathlib import Path
import ast,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'verification/identity-network-image-amendment-v2/metadata'
REVIEW=ROOT/'verification/github-delivery-blocker-campaign/network-review';V1=ROOT/'verification/identity-network-image-amendment-v1/metadata'
def row(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def canon(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(name,v):p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
assert not OUT.exists()
proof={}
def retain(name,source):
 b=source.read_bytes();p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);proof[name]=row(b)
for name in ['image-amendment.json','packet-manifest.json']:retain('proof/prior-v1/'+name,V1/name)
review_files=['decision.json','verification-result.json','retention-receipt.json','job-metadata.json','selected/artifact/artifact-manifest.json','selected/artifact/prepare-prerequisites.json','selected/artifact/logs/0022.json','selected/artifact/logs/0022.stderr','selected/artifact/collector-state.json','selected/artifact/bootstrap-plan.json']
for name in review_files:
 if not (REVIEW/name).is_file():
  assert name=='selected/artifact/collector-state.json'
  continue
 retain('proof/runtime/'+name,REVIEW/name)
urls={
 'moby-v28.0.4-oci_linux.go':'https://raw.githubusercontent.com/moby/moby/v28.0.4/daemon/oci_linux.go',
 'moby-v28.0.4-mount-flags_unix.go':'https://raw.githubusercontent.com/moby/moby/v28.0.4/vendor/github.com/moby/sys/mount/flags_unix.go',
 'elixir-v1.20.4-rebar.ex':'https://raw.githubusercontent.com/elixir-lang/elixir/v1.20.4/lib/mix/lib/mix/rebar.ex',
}
requests=[]
for name,url in urls.items():
 with urllib.request.urlopen(url,timeout=25) as response:
  assert response.status==200;b=response.read(262145);assert len(b)<=262144
 p=OUT/'inputs/official'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);proof['inputs/official/'+name]=row(b)
 requests.append({'url':url,**row(b),'timeout_seconds':25,'max_bytes':262144,'scope':'official platform/tool source only; not execution'})
write('inputs/official/requests.json',requests);proof['inputs/official/requests.json']=row((OUT/'inputs/official/requests.json').read_bytes())
parsed=ast.parse((ROOT/'hosted/scripts/test-identity-network.py').read_text());constants={n.targets[0].id:ast.literal_eval(n.value) for n in parsed.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {'TMPFS','RESOURCES','CAPS'}}
old=constants['TMPFS'];new=json.loads(json.dumps(old))
for role in ['prepare','test']:
 new[role]['/workspace']='rw,nosuid,nodev,noexec,size=1006632960,mode=0755'
 new[role]['/workspace/tooling']='rw,nosuid,nodev,exec,size=67108864,mode=0755'
 new[role]['/tmp']='rw,nosuid,nodev,noexec,size=67108864,mode=1777'
v1=json.loads((V1/'image-amendment.json').read_bytes())
partition={'total_bytes':1073741824,'workspace_bytes':1006632960,'tooling_bytes':67108864,'roles':['prepare','test'],'tooling_path':'/workspace/tooling'}
policy={'source':'/proc/self/mountinfo','max_bytes':65536,'max_selected_line_bytes':4096,'roles':{'prepare':['/workspace','/workspace/tooling','/tmp'],'test':['/workspace','/workspace/tooling','/tmp','/run']},'required':'tmpfs-rw-nosuid-nodev-exact-size-noexec-except-tooling','descendants':'only-exact-selected-tooling-child-mount-is-permitted','tooling_mount_parent':'workspace-mount-id','modes':{'/workspace':493,'/workspace/tooling':493,'/tmp':1023,'/run':493}}
contract={'schema':1,'operation':'carve-bounded-executable-tooling-tmpfs','base_contract':v1['predecessor'],'prior_amendment':{'path':'verification/identity-network-image-amendment-v1/metadata/','amendment_sha256':row((V1/'image-amendment.json').read_bytes())['sha256'],'packet_tree_digest_sha256':'9ddc12c8277b120dcd8ef7577dd9da03d245b8502802db85399a6f1104bcbdc8'},'old_tmpfs':old,'new_tmpfs':new,'workspace_partition':partition,'preserved':{'test_image':v1['test_image'],'prerequisites':v1['prerequisites'],'product_pg_bootstrap_contract':v1['preserved'],'resources':{k:list(v) for k,v in constants['RESOURCES'].items()},'capabilities':{k:sorted(v) for k,v in constants['CAPS'].items()}},'mount_observation':policy,'runtime_basis':{'run_id':40740023326,'artifact_id':12837649788,'delivery_revision':'cc350d3303ca71c5d57e87846f6a61304b658fa7','artifact_tree_digest_sha256':'616274ea3bccd45a7b506a0b71de1016b004cbe55e9ca5f3da9fb2cfb9d394bf','artifact_zip_sha256':'932f877ed0fc8cf8ad9457e0ba1b4888ff7bd5a58762b86975f6e887f9673231','failed_command':22,'prerequisite_receipt_reference':{'original_path':'verification/github-delivery-blocker-campaign/network-review/selected/artifact/prepare-prerequisites.json','packet_path':'proof/runtime/selected/artifact/prepare-prerequisites.json',**proof['proof/runtime/selected/artifact/prepare-prerequisites.json']},'source_supported_noexec_inference':True,'actual_prior_mountinfo':False},'proof_files':proof}
write('execution-amendment.json',contract)
files={str(p.relative_to(OUT)):row(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file()}
write('packet-manifest.json',{'schema':1,'files':files,'tree_digest_sha256':canon(files)})
print(json.dumps({'amendment_sha256':row((OUT/'execution-amendment.json').read_bytes())['sha256'],'packet_root':canon(files),'file_count':len(files)}))
