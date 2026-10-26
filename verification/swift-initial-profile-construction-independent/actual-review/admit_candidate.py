#!/usr/bin/env python3
"""Independent exact custody and owned source replay preparation."""
from pathlib import Path
import datetime,hashlib,json,shutil,sys
OUT=Path(__file__).resolve().parent
PRE=OUT.parent
ROOT=PRE.parents[1]
CANDIDATE=ROOT/'verification/swift-initial-profile-construction-implementation'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,d):(OUT/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def check(base,name,digest):
 b=(base/name).read_bytes();assert sha(b)==digest
 d=json.loads(b)
 for m in d['members']:
  p=base/m['path'];assert p.is_file() and not p.is_symlink();v=p.read_bytes()
  assert len(v)==m['bytes'] and sha(v)==m['sha256'],str(p)
 assert len(d['members'])==d['member_count'] and sum(m['bytes'] for m in d['members'])==d['total_bytes']
 return {'path':str((base/name).relative_to(ROOT)),'sha256':digest,'members':d['member_count'],'bytes':d['total_bytes']}
def main():
 custody={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Root explicitly released frozen candidate; independent actual review, no root acceptance','python':sys.version}
 custody['preaccess']=check(PRE,'preaccess-seal.json','b9048e6edd9941ca3293badd322d89fbfb16a25c1cb02502896d38c589b4295a')
 custody['candidate']=check(CANDIDATE,'seal.json','50d1c32174ee4cbcade6095039261ea0ff8eed05680322bfb59b5de0dd4cd8b1')
 d=json.loads((CANDIDATE/'seal.json').read_text());payload={m['path'] for m in d['members']}
 actual={str(p.relative_to(CANDIDATE)) for p in CANDIDATE.rglob('*') if p.is_file()}
 assert actual==payload|{'seal.json','seal.sha256'}
 sidecar=(CANDIDATE/'seal.sha256').read_bytes();assert sidecar.decode().split()[0]=='50d1c32174ee4cbcade6095039261ea0ff8eed05680322bfb59b5de0dd4cd8b1'
 custody['envelope_sidecar']={'path':'seal.sha256','sha256':sha(sidecar),'payload_member':False}
 root_custody=ROOT/'verification/swift-semantic-adapter-root-review/initial-profile-candidate-custody.json'
 assert sha(root_custody.read_bytes())=='3f8d3612233541bda3888a1018dcf7287d6129250b4d00f9c07c2f8153dbcfd3'
 (OUT/'root-candidate-custody.json').write_bytes(root_custody.read_bytes())
 stage=OUT/'staging';dest=stage/'verification/component';assert not dest.exists()
 source=json.loads((CANDIDATE/'source-manifest-attempt-11.json').read_text());assert source['member_count']==140 and source['tree_sha256']=='71a00fde8a43aef5a7e6104932d3f0ca10a5989fb686c99828937b05aa363c7c'
 for m in source['members']:
  p=CANDIDATE/'source/vm'/m['path'];b=p.read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256'];q=dest/'source/vm'/m['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
 host=json.loads((CANDIDATE/'host-support-manifest.json').read_text());assert host['member_count']==11
 for m in host['members']:
  b=(CANDIDATE/m['retained_path']).read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256'];q=dest/m['retained_path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
 copies=['verification/swift-initial-profile-construction-protocol/test-budget-records.json','verification/swift-initial-profile-construction-protocol/local-structure-proposal.json','verification/swift-semantic-adapter-root-review/initial-profile-unit-test-local-structure.json','verification/swift-semantic-adapter-root-review/initial-profile-compile-placement-amendment.md','verification/swift-semantic-adapter-root-review/initial-profile-build-configuration-amendment.md','verification/swift-cache-state-profile-adapter/required-tests.json']
 custody['staged_root_inputs']=[]
 for name in copies:
  b=(ROOT/name).read_bytes();q=stage/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);custody['staged_root_inputs'].append({'path':name,'bytes':len(b),'sha256':sha(b)})
 custody.update({'distribution_source_sha256':source['tree_sha256'],'source_paths':140,'host_support_paths':11,'staged_candidate':str(dest),'preaccess_immutable':True,'native_or_capture_or_process_inventory':False})
 write('source-manifest.json',source);write('host-support-manifest.json',host);write('input-custody.json',custody)
 for n in ['decision.json','ACCOUNTING.md','accounting.json','actual-layout-comparison-attempt-11.json','command-receipts-attempt-11.json','command-receipts-attempt-12.json','environment-attempt-11.json','environment-attempt-12.json','source-closure-review.json']:
  p=OUT/'candidate-evidence'/n;p.parent.mkdir(exist_ok=True);p.write_bytes((CANDIDATE/n).read_bytes())
 print('PASS custody: preaccess254 immutable; candidate3830 complete payload + separately verified seal sidecar; 140+11 exact staged sources; no mutations outside actual-review.')
if __name__=='__main__':main()
