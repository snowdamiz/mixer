#!/usr/bin/env python3
"""Validate final independent review against compact producer artifacts only."""
from pathlib import Path
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 d=json.loads((HERE/'review.json').read_text())
 assert d['status']=='reviewed-amended-frozen-contract-proposal-no-blocking-findings'
 p=ROOT/d['independentReceipt'];assert sha(p)==d['independentReceiptSHA256']
 r=json.loads(p.read_text());folder=p.parent
 assert r['status']=='independently-verified-declaration-compiler-layout-only'
 assert r['compilerFreshConfigurations']==2 and r['metadataReplays']==16 and len(r['commands'])==24
 for c in r['commands']:
  assert c['exitCode']==0
  for stream in ['stdout','stderr']:assert sha(folder/c[stream])==c[stream+'SHA256']
  if c['sourceBefore'] is not None:
   assert c['sourceBefore']==c['sourceAfter']
   encoded=(json.dumps(c['sourceBefore'],sort_keys=True,indent=2)+'\n').encode()
   assert hashlib.sha256(encoded).hexdigest()==c['sourceTreeSHA256']==d['candidateDeclarationTreeSHA256']
 packet=ROOT/r['producerPacket'];pr=json.loads((packet/'receipt.json').read_text())
 assert sha(packet/'receipt.json')==d['producerReceiptSHA256']
 portable=json.loads((packet/'qualifying-artifacts.json').read_text());assert sha(packet/portable['archive'])==portable['archiveSHA256']==d['portableArchiveSHA256']
 with tarfile.open(packet/portable['archive']) as tar:
  data={m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
 assert len(data)==len(portable['artifacts'])==24
 artifacts={a['id']:a for a in portable['artifacts']}
 for a in artifacts.values():
  assert hashlib.sha256(data[a['archiveMember']]).hexdigest()==a['sha256'] and len(data[a['archiveMember']])==a['bytes']
 for b in r['binaries']:
  assert b['sha256']==artifacts[b['label']]['sha256']
  command=next(c for c in r['commands'] if c['name']=='replay-'+b['label'])
  records=[line[line.index('AF_'):] for line in (folder/command['stdout']).read_text().splitlines() if 'AF_' in line]
  assert records==b['records']==next(x['records'] for x in pr['layouts'] if x['label']==b['label'])
 for key in ['frameExecutionAccepted','accountingCompletenessAccepted','nativeRuntimeAccepted','physicalRuntimeAccepted','gaAccepted']:assert d[key] is False
 seal=json.loads((HERE/'review-seal.json').read_text())
 for path,value in seal['bindings'].items():assert sha(ROOT/path)==value,path
 print(json.dumps({'status':'verified-independent-contract-proposal-only','commands':24,'freshCargoChecks':2,'metadataReplays':16,'portableArtifacts':24,'fields':1061,'frameRuntimeAcceptance':False},sort_keys=True))
if __name__=='__main__':main()
