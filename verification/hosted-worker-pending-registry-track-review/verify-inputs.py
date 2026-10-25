from pathlib import Path
import hashlib,json,datetime,sys
root=Path(__file__).resolve().parents[2]
packet=root/'verification/hosted-worker-pending-registry-track-recheck'
review=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(name,actual,expected):
 checks.append({'name':name,'actual':actual,'expected':expected,'passed':actual==expected})
check('frozen-receipt',sha(packet/'receipt.json'),'d9bd48d069746b24ed3386e9842a1693e5aba44c33ffd4e095646acaef7cff5c')
check('frozen-patch',sha(packet/'track-recheck.patch'),'a7876fc0786f53ea3e201a1969a3f90a07a0c48c71e2602151f5a4ee7ac64372')
check('prior-review-receipt',sha(packet/'inputs/review-receipt.json'),'c1c53d5437854fb9fb0aa24fabd19cc5cb9053f4c40ca29393801da1abe4ce29')
r=json.loads((packet/'receipt.json').read_text())
for entry in r['artifacts']:
 p=root/entry['path'];check(entry['path'],sha(p),entry['sha256']);check(entry['path']+' bytes',p.stat().st_size,entry['bytes'])
m=json.loads((root/r['run']/'source-manifest.json').read_text())
for e in m['entries']:
 p=packet/'candidate'/e['path'];check('candidate/'+e['path'],sha(p),e['sha256']);check('candidate/'+e['path']+' bytes',p.stat().st_size,e['bytes'])
calculated=hashlib.sha256(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in m['entries']).encode()).hexdigest()
check('sourceDigest',calculated,'f4290d7ab0ece9eb2546d9b6125054d6cbbd4d9ab572d418679fbc41e748b799')
check('changed-production-modules',r['changedProductionModules'],['engine.ts','ledger.ts'])
for e in json.loads((packet/'input-manifest.json').read_text())['entries']:
 p=packet/e['path'];check('input/'+e['path'],sha(p),e['sha256'])
out={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed' if all(x['passed'] for x in checks) else 'failed','checks':checks,'sourceDigest':calculated,'reviewedRevisionProvidedByRoot':'ee390cbf56ba388a21c7d28c884dbed5fd7282fe','revisionCheckedByGit':False}
name=sys.argv[1] if len(sys.argv)>1 else 'input-verification-before.json'
(review/name).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'status':out['status'],'checks':len(checks),'sourceDigest':calculated}))
sys.exit(0 if out['status']=='passed' else 1)
