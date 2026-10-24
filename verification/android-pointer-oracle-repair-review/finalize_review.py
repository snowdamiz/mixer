#!/usr/bin/env python3
"""Seal this independent host review only; no producer mutation or native tools."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/android-pointer-oracle-repair'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def bind(path):return {'bytes':path.stat().st_size,'sha256':sha(path)}

save(HERE/'official-platform-contracts.json',{
    'observedUTC':'2026-10-24','access':'web search/open official Android Developers references',
    'Instrumentation':{'url':'https://developer.android.com/reference/android/app/Instrumentation#sendPointerSync(android.view.MotionEvent)',
        'quote':'This method blocks until the recipient has finished handling the event.',
        'inference':'The frozen observer callbacks must occur during the corresponding synchronous injection call; inclusive uptime comparisons preserve equal millisecond observations.'},
    'MotionEvent':{'url':'https://developer.android.com/reference/android/view/MotionEvent#getHistorySize()',
        'quote':'This only applies to ACTION_MOVE events -- all other actions will have a size of 0.',
        'inference':'The passive MotionEvent observer cannot legitimately report nonempty history on UP, CANCEL or DOWN.'}})

names=['oracle.py','run.py','common.py','check_packet.py','CoordinatorJoinActivity.java','CoordinatorJoinInstrumentation.java','test_host.py','runner-contract-4.json','runner-source-4/transformed_runner.py']
save(HERE/'source-review.json',{
    'producerSourceBindings':{str((PRODUCER/n).relative_to(ROOT)):bind(PRODUCER/n) for n in names},
    'passiveObservation':{'Activity':'29-47','motionSerialization':'Instrumentation166-170','entryExitUptime':'Instrumentation173-183','workerInjection':'Instrumentation263-270','singleSuperclassDispatch':True,'gestureDirectCallbackOrPerformClick':False},
    'oracleFindings':{'F06':'worker109-112 and Activity117-123 do not join matching event workerBefore/workerAfter interval','F07':'history125-133 permits non-MOVE container'},
    'minimumF06Repair':{'joinKey':'sealed current eventTime after point validation','inclusiveRule':'workerBefore <= entryUptime <= exitUptime <= workerAfter; eventTime <= entryUptime','historyException':'historical MOVE samples retain sealed time/path/pressure order checks and may belong to earlier worker sends'},
    'minimumF07Repair':'empty history on every non-MOVE; real MOVE history remains permitted; frozen worker requests contain no history',
    'wrapperReview':{'exactConcreteDerivationLoaded':True,'predispatchChecks':'source105/nativeSDK88, archive, extracted APK, local packaging, official alignment and exact signer before first adb/emulator call','preinstallChecks':'repeat source105/nativeSDK88, APK, packaging, official alignment and exact signer immediately before install','runtimeOutput':'fresh runtime-N under exact designated runtime subtree; reused paths/escapes/symlinks rejected','runtimeSeal':'only own exact root artifact-seal.json omitted; nested receipts included'},
    'nativeDispatch':False,'nativeCommandExecution':False,'productionMutation':False})

results=json.loads((HERE/'host-review-2/adversarial-results.json').read_text())
failures=[r for r in results if not r['expectationMet']]
assert len(results)==19 and len(failures)==5
findings=[
    {'id':'F06','severity':'blocking evidence acceptance','title':'Activity delivery timing is not correlated with matching synchronous worker injection','source':'verification/android-pointer-oracle-repair/oracle.py','line':119,'falseAcceptanceCases':[r['case'] for r in failures if r['finding']=='F06'],'observedAndroidFailure':False,'syntheticParserFinding':True},
    {'id':'F07','severity':'blocking evidence acceptance','title':'Non-MOVE history can stand in for every Activity MOVE','source':'verification/android-pointer-oracle-repair/oracle.py','line':125,'falseAcceptanceCases':[r['case'] for r in failures if r['finding']=='F07'],'observedAndroidFailure':False,'syntheticParserFinding':True}]
save(HERE/'findings.json',findings)

for attempt in ('host-review-1','host-review-2'):
    directory=HERE/attempt
    receipt=json.loads((directory/'receipt.json').read_text())
    used=directory/'review-source-used.py'
    if not used.exists():used.write_bytes((HERE/'review.py').read_bytes())
    assert bind(used)==receipt['reviewerSource']
    scratch=Path(receipt['scratch']['path'])
    assert receipt['scratch']['removed'] and receipt['scratch']['openHoldersEmpty'] and not scratch.exists()
    for p in directory.rglob('*'):
        assert not p.is_symlink()
    seal={str(p.relative_to(directory)):bind(p) for p in sorted(directory.rglob('*')) if p.is_file() and p!=directory/'artifact-seal.json'}
    save(directory/'artifact-seal.json',{'files':seal,'scope':'all attempt files including complete failing synthetic fixtures; only own exact root seal omitted'})

packet_check=subprocess.run([sys.executable,'-B',str(PRODUCER/'check_packet.py')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
(HERE/'producer-packet-final.log').write_bytes(packet_check.stdout)
packet=json.loads(packet_check.stdout)
assert packet['hostFiles']==284 and packet['packetSealSHA256']=='275e733bbc31262c12bf65402fc12e110a43c9f5d14cb41ad157be7a5d755fd5'
receipt={
    'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'review-complete-native-held-two-oracle-findings','findings':['F06','F07'],
    'producerHostTests':42,'independentProbes':19,'unexpectedSyntheticAcceptances':5,
    'artifactAndRunnerReview':'passed-exact-candidate5-source-archive-APK-signature-packaging-and-wrapper-controls',
    'nativeDispatchAuthorized':False,'nativeCommandsExecuted':0,'physicalTargetsQueried':False,
    'producerMutation':False,'trackerMutation':False,'GitMutation':False,'scratchCleanup':'both attempts absent after identity and empty-holder checks',
    'reviewAttempts':{n:bind(HERE/n/'artifact-seal.json') for n in ('host-review-1','host-review-2')},
    'producerPacket':packet,'reviewDoc':bind(ROOT/'docs/android-pointer-oracle-repair-review.md'),
    'finalizationCommand':[sys.executable,'-B',str(HERE/'finalize_review.py')],
    'finalizer':bind(Path(__file__)),
    'producerFinalCheckCommand':{'argv':[sys.executable,'-B',str(PRODUCER/'check_packet.py')],'cwd':str(ROOT),'exitCode':packet_check.returncode,'output':'producer-packet-final.log',**bind(HERE/'producer-packet-final.log')},
    'limitations':['synthetic parser findings are not observed Android delivery failures','fresh producer Javac/DEX replay bound by packet; historical compilations not repeated','root must review separate corrected oracle/runner packet before bounded native run','physical phones disconnected and deferred; no release, customer, operational or GA acceptance']}
save(HERE/'receipt.json',receipt)
checker=__import__('importlib.util').util.spec_from_file_location('review_seal',HERE/'check_review.py')
mod=__import__('importlib.util').util.module_from_spec(checker);checker.loader.exec_module(mod)
save(HERE/'artifact-seal.json',{'schema':1,'files':mod.files(),'scope':'complete recursive independent host review plus document; only this exact root seal excluded'})
print(json.dumps(mod.check(),indent=2,sort_keys=True))
