from pathlib import Path
import hashlib,json,shutil,datetime

root=Path(__file__).resolve().parents[2]
packet=Path(__file__).resolve().parent
producer=root/'verification/hosted-worker-pending-terminal-consistency'
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def checks():
 receipt=producer/'receipt.json'
 assert sha(receipt.read_bytes())=='e4afac5866c26ffd96c460bbdd54e3cf0098bc1d378601ba7e542d6f819e677b'
 r=json.loads(receipt.read_text())
 assert r['patchSHA256']=='ca15d306c91dbdbccc3ae858fb09c0236258f5e51c2fa9dbc38b914ae73284d5'
 assert r['sourceDigest']=='b46bac2e4377663e2df078743c655c062f42cc92893a3d53b702476b05b6966f'
 groups={}
 for group,entries in [('producerArtifacts',r['artifacts']),('priorBindings',json.loads((producer/'input-manifest.json').read_text())['checks'])]:
  for e in entries:
   b=(root/e['path']).read_bytes()
   assert len(b)==e['bytes'] and sha(b)==e['sha256'],e['path']
  groups[group]=len(entries)
 manifest=json.loads((producer/'source-manifest.json').read_text())
 assert sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in manifest['entries']).encode())==manifest['sourceDigest']
 for e in manifest['entries']:
  b=(producer/'candidate'/e['path']).read_bytes()
  assert sha(b)==e['sha256'] and len(b)==e['bytes']
 groups['candidateSourceEntries']=len(manifest['entries'])
 return {'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'allUnchanged':True,**groups,'receiptSHA256':sha(receipt.read_bytes()),'sourceDigest':manifest['sourceDigest']}

if __name__=='__main__':
 before=checks();write(packet/'frozen-before.json',before)
 for e in json.loads((producer/'source-manifest.json').read_text())['entries']:
  dest=packet/'candidate'/e['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(producer/'candidate'/e['path'],dest)
 p=packet/'candidate/test/harness.mjs'
 p.write_text(p.read_text().replace('mixer-pending-terminal-consistency-owned-','mixer-pending-terminal-review-owned-'))
 print(json.dumps(before))
