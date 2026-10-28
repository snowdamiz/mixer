#!/usr/bin/env python3
"""One-time closed image amendment materializer; no runtime or release authority."""
from pathlib import Path
import hashlib,json,shutil,urllib.request
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'verification/identity-network-image-amendment-v1/metadata'
REVIEW=ROOT/'verification/identity-network-image-prerequisite-review'
def digest(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return digest(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def write(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
review_manifest=json.loads((REVIEW/'packet-manifest.json').read_bytes())
assert review_manifest['tree_digest_sha256']==canonical(review_manifest['files'])=='261023b77cb55255f666959f367330783a354174252ed23b71145566f87ba597'
assert not OUT.exists()
for name,row in review_manifest['files'].items():
 b=(REVIEW/name).read_bytes(); assert row=={'bytes':len(b),'sha256':digest(b)}
 p=OUT/'source-review'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
shutil.copyfile(REVIEW/'packet-manifest.json',OUT/'source-review/packet-manifest.json')
for suffix in ['index','amd64-manifest','amd64-config']:
 p=OUT/'inputs/registry'/('elixir-'+suffix+'.json');p.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(REVIEW/'inputs/official'/('bookworm-candidate-'+suffix+'.json'),p)
url='https://raw.githubusercontent.com/erlang/otp/OTP-29.1.1/lib/public_key/src/public_key.erl'
with urllib.request.urlopen(url,timeout=25) as response:
 assert response.status==200
 b=response.read(262145);assert len(b)<=262144
p=OUT/'inputs/official/otp-29.1.1-public_key.erl';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
write(OUT/'inputs/official/public-key-request.json',{'url':url,'bytes':len(b),'sha256':digest(b),'scope':'official API source only; no execution','timeout_seconds':25,'max_bytes':262144})
candidate=json.loads((REVIEW/'analysis/amendment-candidate.json').read_bytes())
capabilities=json.loads((REVIEW/'analysis/capabilities.json').read_bytes())
def image(row): return {'ref':row['runtime_ref'],'index':row['index_digest'],'config':row['config_digest'],'platform':'linux/amd64'}
old=candidate['old_contract'];new=candidate['proposed_test_image'];preserved=candidate['unchanged'];product=preserved['product_source_identity']
tools={row['requested']:{k:row['object'][k] for k in ['bytes','sha256']} for row in capabilities['required_objects'] if row['requested'] in preserved['tool_paths']}
ca={k:capabilities['ca_bundle'][k] for k in ['path','bytes','sha256']}
ca['der_sha256']=sorted(row['der_sha256'] for row in capabilities['ca_bundle']['certificates'])
bootstrap={row['tool']:{k:row[k] for k in ['url','sha512','version']} for row in preserved['bootstrap']['selection']}
amendment={'schema':1,'operation':'replace-test-image-only','predecessor':{k:old[k] for k in ['packet_manifest_sha256','packet_tree_digest_sha256']},'old_test_image':image(old['old_image']),'test_image':{**image(new),'tag':new['tag']},'preserved':{'product_commit':product['product_commit'],'product_files':177,'product_digest':product['product_tree_digest_sha256'],'lock_sha256':product['lock_sha256'],'postgres':image(preserved['database_image']),'bootstrap':bootstrap,'test_roots':preserved['frozen_methods'],'contract_boundaries':'all-other-predecessor-contract-fields-unchanged'},'prerequisites':{'tools':tools,'ca':ca,'elixir':'1.20.4','otp_patch':'29.1.1','openssl_version_prefix':'OpenSSL 3.0.22 ','crypto_library':{'name':'OpenSSL','positive_numeric_identity':True,'version_prefix':'OpenSSL 3.0.22 '},'loaded_os_roots':'explicit-selected-bundle-load-nonempty-and-source-hashes-exact'},'source_review':{'relative_namespace':'source-review/','packet_manifest_sha256':digest((REVIEW/'packet-manifest.json').read_bytes()),'packet_tree_digest_sha256':review_manifest['tree_digest_sha256']}}
amendment['predecessor']['contract_sha256']=old['sha256']
write(OUT/'image-amendment.json',amendment)
files={str(p.relative_to(OUT)):{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(OUT.rglob('*')) if p.is_file()}
write(OUT/'packet-manifest.json',{'schema':1,'files':files,'tree_digest_sha256':canonical(files)})
print(json.dumps({'amendment_sha256':digest((OUT/'image-amendment.json').read_bytes()),'packet_root':canonical(files),'file_count':len(files),'source_review_manifest_sha256':amendment['source_review']['packet_manifest_sha256']},sort_keys=True))
