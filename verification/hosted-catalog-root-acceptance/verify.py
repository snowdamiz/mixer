#!/usr/bin/env python3
"""Read-only verification of the selected catalog prerequisite."""
import hashlib,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 for name,digest in json.loads((HERE/'seal.json').read_text())['bindings'].items():assert sha(ROOT/name)==digest,name
 r=json.loads((HERE/'acceptance.json').read_text())
 for group in [r['bindings'],json.loads((HERE/'accepted-input-bindings.json').read_text())]:
  for name,digest in group.items():assert sha(ROOT/name)==digest,name
 for c in json.loads((HERE/'commands.json').read_text()):assert c['exitCode']==0 and sha(HERE/c['log'])==c['sha256']
 review=json.loads((ROOT/'verification/hosted-catalog-wildcard-review/receipt.json').read_text())
 assert review['independent_review_passed']and not review['findings']
 assert review['candidate_source_digest']==r['candidateSourceDigest']and r['rootAccepted']
 assert not r['liveIntegrated']and not r['gaAccepted']
 print(json.dumps({'verified':True,'upstreamBindings':r['upstreamBindings'],'rootBindings':len(r['bindings']),'resolved':['ACSR01','ACSR02'],'liveIntegrated':False,'gaAccepted':False}))
if __name__=='__main__':main()
