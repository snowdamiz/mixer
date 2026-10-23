#!/usr/bin/env python3
"""Audit frozen source, logs and actual retained artifacts; no runtime execution."""
import hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def main():
 p=HERE/'2026-10-23-candidate-2/receipt.json';raw=p.read_bytes();r=json.loads(raw)
 need(sha(raw)=='5aa8a0f4e533c7d42bd5e81fce5abaa84b3c1fe2f68f7ec9308f593e68d36c36','frozen receipt')
 for path,digest in r['source_files'].items():need(sha((Path(r['export'])/path).read_bytes())==digest,'source export '+path)
 for path,digest in r['owned_files'].items():need(sha((ROOT/path).read_bytes())==digest,'owned production/test '+path)
 for path,digest in r['baseline_files'].items():need(sha(subprocess.check_output(['git','show',r['dependency_revision']+':'+path],cwd=ROOT))==digest,'Git baseline '+path)
 for path,digest in r['native_files'].items():need(sha((Path(r['native_copy'])/path).read_bytes())==digest,'native artifact '+path)
 for c in r['commands']:
  data=(ROOT/c['log']).read_bytes();need(sha(data)==c['sha256'],'command log '+c['name']);need(c['exit_code']==c['expected_exit'],'command result '+c['name'])
  if 'expected_tests' in c:need(c['observed_tests']==[c['expected_tests']],'test count '+c['name'])
  if 'required_fragment' in c:need(c['required_fragment'].encode() in data,'compile rejection '+c['name'])
 retained=0
 for mode,group in r['retained_products'].items():
  for path,digest in group['files'].items():need(sha((Path(group['directory'])/path).read_bytes())==digest,'retained '+mode+'/'+path);retained+=1
 for target,outputs in r['artifacts'].items():
  for a in outputs:need(sha(Path(a['path']).read_bytes())==a['sha256'],'actual '+target+' output')
 reviewpath=ROOT/'verification/capability-durable-store-review/final-receipt.json'
 reviewraw=reviewpath.read_bytes();review=json.loads(reviewraw)
 need(sha(reviewraw)=='a3642344f8c3dde11ab33c4040e863b6632a2c5b0001ab4b495ce5cf84d1047b','exact independent review')
 need(review['ownerReceipt']['sha256']==sha(raw) and review['sourceManifestSHA256']==r['source_manifest_sha256'],'review source binding')
 need(review['probeExecutions']==24 and not review['openActionableFindings'],'independent scope/result')
 for path,digest in review['reviewedProduction'].items():need(r['owned_files'][path]==digest,'review production pin')
 rows={str(p.relative_to(HERE)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['final-receipt.json','evidence-manifest.sha256'] and '__pycache__' not in p.parts}
 manifest=''.join(d+'  '+p+'\n' for p,d in sorted(rows.items())).encode();(HERE/'evidence-manifest.sha256').write_bytes(manifest)
 final={'status':'scoped owner qualification and independent review passed; root integration pending','source_manifest_sha256':r['source_manifest_sha256'],'qualification_receipt_sha256':sha(raw),'owned_files':r['owned_files'],'source_export_files':len(r['source_files']),'immutable_dependency_files':len(r['baseline_files']),'command_logs':len(r['commands']),'retained_host_files':retained,'evidence_files':len(rows),'evidence_manifest_sha256':sha(manifest),'independent_review':{'path':str(reviewpath.relative_to(ROOT)),'sha256':sha(reviewraw),'probe_executions':24,'open_actionable_findings':[]},'scope':r['scope'],'limitations':r['limitations']}
 (HERE/'final-receipt.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(final,indent=2));print('final-sha256 '+sha((HERE/'final-receipt.json').read_bytes()))
if __name__=='__main__':main()
