from pathlib import Path
import hashlib,json,difflib
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(name,d):(packet/name).write_text(json.dumps(d,indent=2)+'\n')
producer=root/'verification/hosted-worker-pending-migration-history';review=root/'verification/hosted-worker-pending-migration-history-review'
expected={producer:'5bce543f307a07666aa5bc70b4f9e5da6f59ac82edc5956c26d859a8f64d288e',review:'43992550d3fff245b10e0d019c484f904f24f6de1b4de6bb2645635e0cc3aa06'}
checks={};receipts={}
def bind(p,expected=None):
 b=p.read_bytes();digest=sha(b)
 if expected is not None:assert digest==expected,(str(p),digest)
 rel=str(p.relative_to(root));checks[rel]={'path':rel,'sha256':digest,'bytes':len(b)}
 return b
for base,digest in expected.items():
 b=bind(base/'receipt.json',digest);receipt=json.loads(b);receipts[base.name]=receipt
 assert len(receipt['artifacts'])==({producer:213,review:136}[base])
 for entry in receipt['artifacts']:
  p=root/entry['path'];assert not any(word in entry['path'].lower() for word in ['catalog-inspector','authority-driver','transportv2','transport-v2','outbound-worker'])
  assert len(bind(p,entry['sha256']))==entry['bytes']
 bind(base/'seal.sha256')
for entry in json.loads((review/'source-closure.json').read_text())['externalFixtureAndToolBindings']:
 assert len(bind(root/entry['path'],entry['sha256']))==entry['bytes']
decision=root/'verification/hosted-worker-pending-migration-history-root-review/independent-decision.json';d=json.loads(bind(decision));assert d['selectedCorrection']=='Add exact track_outbox_json null requirement to shared unenrolledMigrationShape, preserve registered enrollment and terminalProjection behavior.'
old=b"r.registration_json===null&&r.registry_ack_version==='0'";new=b"r.registration_json===null&&r.track_outbox_json===null&&r.registry_ack_version==='0'"
for base,dst in [(producer,'candidate'),(review,'independent-candidate'),(review,'boundary-candidate')]:
 manifest=json.loads((base/'source-manifest.json').read_text())
 for entry in manifest['entries']:
  b=(base/'candidate'/entry['path']).read_bytes();assert sha(b)==entry['sha256'] and len(b)==entry['bytes']
  target=packet/dst/entry['path'];assert not target.exists(),str(target);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 p=packet/dst/'src/engine.ts';b=p.read_bytes();assert b.count(old)==1;p.write_bytes(b.replace(old,new))
 if dst=='candidate':
  (packet/'migration-outbox.patch').write_text(''.join(difflib.unified_diff(b.decode().splitlines(True),p.read_text().splitlines(True),fromfile='frozen/src/engine.ts',tofile='candidate/src/engine.ts')))
(packet/'request.json').write_bytes((review/'request.json').read_bytes())
p=packet/'boundary-candidate/test/worker.ts';s=p.read_text();anchor="   case 'reviewDowngradeOnly':{";assert s.count(anchor)==1
extra="""   case 'outboxBoundaryBytes':{
    const values:Record<string,string|null>={missing:null,empty:'',malformed:'{'};
    if(typeof arg.form!=='string'||!Object.prototype.hasOwnProperty.call(values,arg.form))throw new Error('finite_outbox_boundary');
    this.ctx.storage.sql.exec('UPDATE operation SET track_outbox_json=?',values[arg.form]);await this.ledger.sync();return {row:this.ledger.read()};
   }
"""
p.write_text(s.replace(anchor,extra+anchor));(packet/'boundary-fixture.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),p.read_text().splitlines(True),fromfile='frozen-review/test/worker.ts',tofile='boundary-candidate/test/worker.ts')))
write('input-manifest.json',{'schema':1,'frozenProducerReceiptSHA256':expected[producer],'frozenProducerSourceDigest':'361c391b035a7a4cdbfaa9d6013cb4944431eb97ad14c65731caac292f947483','frozenReviewReceiptSHA256':expected[review],'frozenArtifactsVerified':349,'selectedCorrection':d,'checks':list(checks.values())})
write('preparation.json',{'copiedProducerSourceEntries':len(json.loads((producer/'source-manifest.json').read_text())['entries']),'copiedReviewSourceEntriesPerClosure':len(json.loads((review/'source-manifest.json').read_text())['entries']),'inputFilesBound':len(checks),'productionConditionAdded':'r.track_outbox_json===null','productionOtherBytesChanged':False,'driverBytesChanged':False,'boundaryFixtureAddedOnly':True,'gitConsultedOrChanged':False})
print(json.dumps({'frozenArtifacts':349,'boundInputs':len(checks),'copiedClosures':3,'exactOneConditionEngineCorrection':True}))
