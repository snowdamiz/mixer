#!/usr/bin/env python3
"""Replay immutable producer seal bindings. Reads producer files; writes own receipt."""
from pathlib import Path
import argparse,datetime,hashlib,json,sys
from review import BASE,PACKET,require,sha,read,logical_bytes
def file_hash(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--seal',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();r={'schema':1,'status':'in-progress','command':sys.argv,'cwd':str(Path.cwd()),'tool':sys.version,'verifierSHA256':sha(Path(__file__).read_bytes()),'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accountingAccepted':False,'qualifiedRuntimeExecuted':False}
 try:
  data=a.seal.read_bytes();seal=json.loads(data);require(seal['version']==5,'unsupported seal version');require(isinstance(seal['bindings'],dict)and seal['bindings'],'empty seal');bindings=seal['bindings']
  require(sha(data)=='7d5a043e7c982a84d5fe1a85444a6a492a40ebddf87a36e95ebdedde02593b15','producer-confirmed immutable seal digest changed')
  require((PACKET/'review-seal.sha256').read_text().strip()==sha(data)+'  review-seal.json','seal sidecar mismatch')
  total=0
  for rel,record in bindings.items():
   p=PACKET/rel;require(not Path(rel).is_absolute()and'..'not in Path(rel).parts,'seal path escape');require(file_hash(p)==record['sha256']and p.stat().st_size==record['bytes'],'sealed file drift '+rel);total+=record['bytes']
  documents={}
  for rel in bindings:
   if rel.startswith('review-inputs/docs/'):
    target=BASE/'docs'/Path(rel).name;require(file_hash(target)==bindings[rel]['sha256'],'sealed document differs from reviewed current document '+rel);documents[str(target.relative_to(BASE))]=bindings[rel]['sha256']
   if rel.startswith('review-inputs/authority/'):
    target=BASE/'verification/swift-calls-dispatch-root-review'/Path(rel).name;require(file_hash(target)==bindings[rel]['sha256'],'sealed authority differs from reviewed current authority '+rel)
  required=['candidate-final-source.json','candidate-final-source.tar.gz','candidate-final-manifest.json','inventory-v5.json','finite-numeric-positions-v5.json','compiler-headers-v5.json','compiler-partitions-v5.json','compiler-function-items-v5.json','temporal-position-mapping-v5.json','finite-exception-reconciliation-v5.json','final-query-bindings.json','final-accounting-report.json','final-typed-field-layouts.json.gz','final-contextual-type-mappings.json.gz','final-contextual-definition-bridges.json.gz','final-contextual-field-bindings.json.gz','final-identity-bridge-controls.json','layout_driver.rs','identity_bridge.py','collect.py']
  missing=set(required)-set(bindings);transported={}
  for name in ['historical-json-transports.json','json-transports.json']:
   if name in bindings:transported.update(read(PACKET/name))
  if 'final-inventory-transport.json'in bindings:
   t=read(PACKET/'final-inventory-transport.json');transported[t['logicalPath']]={'transport':t['transportPath']}
  for rel in missing:
   require(rel in transported and transported[rel]['transport']in bindings,'required final proof artifact absent from seal '+rel);logical_bytes(PACKET/rel)
  source=read(PACKET/'candidate-final-source.json');require(source['sourceClosure']=='ba9231499244692bbed61f0566ec72864a979df9e3fc71511560ec66a2e00c70','unexpected final product source');require(source['archiveSHA256']==file_hash(PACKET/'candidate-final-source.tar.gz'),'final source archive pointer drift')
  require(sha((PACKET/'candidate-final-manifest.json').read_bytes())==source['sourceClosure'],'final source manifest closure drift')
  require(seal['allOwnedCompilerGroupsAndScratchCleaned']is True and seal['runtimeQualified']is False and seal['independentAccountingAccepted']is False and seal['rootSelectionPending']is True,'producer scope/cleanup flags changed')
  require(seal['candidateSourceClosure']==source['sourceClosure'],'seal candidate source mismatch')
  r.update(status='sealed-producer-bindings-passed',producerSealSHA256=sha(data),files=len(bindings),bytes=total,documents=documents,capturedAttempts=seal['capturedAttempts'],requiredLogicalArtifactsTransported=sorted(missing),sourceClosure=source['sourceClosure'],archiveSHA256=source['archiveSHA256'])
 except BaseException as e:r.update(status='rejected',error=repr(e))
 a.output.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n');print(json.dumps(r,sort_keys=True,indent=2));return r['status']=='rejected'
if __name__=='__main__':raise SystemExit(main())
