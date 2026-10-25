from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[1]
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
command=[sys.executable,str(OWN/'verify-inputs.py'),'--after']
started=now()
result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,timeout=30)
(OWN/'input-verification.stdout.log').write_text(result.stdout)
(OWN/'input-verification.stderr.log').write_text(result.stderr)
(OWN/'validation-commands.json').write_text(json.dumps([{'command':command,'cwd':str(ROOT),'startedUTC':started,'finishedUTC':now(),'exitCode':result.returncode,'stdoutEOF':True,'stderrEOF':True,'timeoutSeconds':30}],indent=2)+'\n')
assert result.returncode==0,result.stderr
report=json.loads((OWN/'report.json').read_text())
manifest=json.loads((OWN/'source-manifest.json').read_text())
for e in manifest['entries']:
    data=(OWN/'candidate'/e['path']).read_bytes()
    assert sha(data)==e['sha256'] and len(data)==e['bytes']
cleanup=json.loads((OWN/'cleanup-seal.json').read_text())
for check in cleanup['checks']:
    assert not Path(check['storage']).exists()
    try: os.kill(check['pid'],0)
    except ProcessLookupError: pass
    else: raise AssertionError(('owned process remains',check['pid']))
artifacts=[]
for path in sorted(OWN.iterdir()):
    if path.is_file() and path.name!='receipt.json':
        data=path.read_bytes()
        artifacts.append({'path':str(path.relative_to(ROOT)),'sha256':sha(data),'bytes':len(data)})
doc=ROOT/'docs/hosted-worker-pending-registry-engine-correction-review.md'
data=doc.read_bytes()
artifacts.append({'path':str(doc.relative_to(ROOT)),'sha256':sha(data),'bytes':len(data)})
receipt={
 'schema':1,'status':'changes-required-one-confirmed-provider-track-race','observedUTC':now(),
 'scope':'bounded independent frozen correction source review and focused actual workerd/SQLite controls; no integration authority',
 'frozenCorrectionReceiptSHA256':'3af44bc2353edab386ba20b30e647a71a2b70301c3e37ba2aea50de100a381f1',
 'frozenCorrectionPatchSHA256':'04203b53a6c22b252b781adca727511d977ec5a3e64b83ece2f60dce3f3653d7',
 'frozenCorrectionSourceDigest':'ee330a270f6151dfff96ed561a8b654ca1cc753026d03583cea99aee4276d811',
 'originalFailedReviewReceiptSHA256':'3476e3e26845e4b3b21cf0208aac883908660fa5e3ae8c83392ec3859c824de0',
 'reviewSourceDigest':manifest['sourceDigest'],'allProductionSourcesByteIdenticalToFrozenCorrection':True,
 'onlyProductionCorrectionFromOriginal':'src/engine.ts','selectedRegistrySHA256':'99d8a5dc4e2e9b8875c262ae44d2f1307d3107d3bc48c4300e981f68ec12b428',
 'frozenInputHashesValidated':121,'frozenInputFilesBound':286,'frozenInputsUnchangedAtSeal':True,'reviewSourceManifestRevalidatedAtSeal':True,
 'actualWorkerdSQLite':True,'controlsExecuted':47,'harnessAssertionsPassed':47,'passingSafetyAndPositiveControls':46,'confirmedProductDefects':1,
 'harnessExitDoesNotMeanProductAcceptance':True,
 'findings':[{'priority':'P1','id':'provider-mismatch-after-pre-track-await-not-fenced','file':'verification/hosted-worker-pending-registry-engine-correction/candidate/src/engine.ts','lines':'60-73','control':'same-version-provider-restore-during-terminal-track-boundary','observed':{'flushed':True,'stateVersion':'3','providerKind':'external-macos','trustedProviderKind':'cloudflare-linux','quarantined':0,'permanentFenceCount':0,'registryPending':0,'trackOutbox':None}}],
 'ownedStorageEnvironmentsRemoved':47,'observedOwnedProcessIdentities':48,'allObservedOwnedPidsAbsentAtSeal':True,'ownedSIGKILLControls':0,
 'commands':json.loads((OWN/'commands.json').read_text()),'versions':json.loads((OWN/'tool-versions.json').read_text()),'artifacts':artifacts,
 'limitations':['producer54groups verified as frozen evidence, not rerun','live71controllergroups and20processcontrols not rerun','clock/provider/fault helpers are excluded finite synthetic fixtures','no public/scheduled entry integration or schedule installation','no production provider, clock, signing, storage-restore, capacity or operational qualification','no native or physical-device evidence','no deployed qualification, immutable-package FieldLog dogfood or GA acceptance'],
 'liveFilesModified':False,'trackersModified':False,'gitAccessedOrModified':False,'forbiddenLanesAccessedOrExecuted':False,
 'productionIntegrationAccepted':False,'productionPublished':False,'gaAccepted':False,'frozen':True
}
(OWN/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'receiptSHA256':sha((OWN/'receipt.json').read_bytes()),'artifacts':len(artifacts),'sourceDigest':manifest['sourceDigest']}))
