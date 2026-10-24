#!/usr/bin/env python3
"""Seal exact isolated implementation packet, including nested failures/receipts/seals."""
import json,os,sys
from pathlib import Path
import build as common
HERE=common.HERE;ROOT=common.ROOT

def files():
    excluded=HERE/'packet-seal.json';paths=[]
    if HERE.is_symlink():raise ValueError('proof root symlink refused')
    for p in sorted(HERE.rglob('*')):
        if p.is_symlink():raise ValueError('symlink refused')
        if p.is_dir() and p.name in ('.build','__pycache__'):raise ValueError('owned scratch remains')
        if p.is_file() and p!=excluded:paths.append(p)
    paths.append(ROOT/'docs/android-authored-toggle-input-implementation.md')
    return {str(p.relative_to(ROOT)):common.bind(p) for p in sorted(paths)}

def main():
    final=HERE/'finalization';final.mkdir()
    receipt={'schema':1,'startedUTC':common.now(),'commands':[],'nativeRuntime':'NOT RUN','nativeDispatchAuthorized':False,'nativeAccepted':False,'gaAccepted':False,'GitCommandsExecuted':0,'physicalTargetsQueried':False,'nativeInstancesStarted':0}
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    def command(name,argv):
        start=common.now();argv=list(map(str,argv));r=common.owned.execute(argv,cwd=ROOT,env=env,timeout=180);p=final/(name+'.log');p.write_bytes(r.stdout)
        receipt['commands'].append({'name':name,'argv':argv,'cwd':str(ROOT),'startedUTC':start,'finishedUTC':common.now(),'exitCode':r.returncode,'output':str(p.relative_to(ROOT)),**common.bind(p),'ownedCommandGroupCleanup':r.groupCleanup})
        if r.returncode:raise RuntimeError(name+' failed')
    selected=json.loads((ROOT/'verification/android-authored-toggle-root-review/selection.json').read_text())
    for n,v in selected['bindings'].items():
        if common.bind(ROOT/n)!=v:raise ValueError('root selection drift '+n)
    receipt['rootSelection']={'path':'verification/android-authored-toggle-root-review/selection.json',**common.bind(ROOT/'verification/android-authored-toggle-root-review/selection.json'),'bindingsVerified':len(selected['bindings'])}
    for n in ['candidate-1','candidate-2','candidate-3','supplement-1','supplement-2','supplement-3','upstream-controls','upstream-controls-2']:
        folder=HERE/n
        if common.seal(folder)!=json.loads((folder/'artifact-seal.json').read_text()):raise ValueError('attempt seal drift '+n)
        r=json.loads((folder/'receipt.json').read_text())
        if not r['cleanup']['absent'] or (folder/'.build').exists() or any(c['ownedCommandGroupCleanup']['after'] for c in r['commands']):raise ValueError('owned cleanup not complete '+n)
    for n in ['NativeAppearanceViewsV2.java','NativeRenderer.java']:
        relative='native/android/app/src/dev/mixer/android/'+n
        if (ROOT/relative).read_bytes()!=(HERE/'inputs'/relative).read_bytes():raise ValueError('live production changed by this lane '+n)
    for n in common.FAMILIES:
        frozen=HERE/'candidate-3/inputs'/common.NATIVE/(n+'.java')
        if common.bind(frozen)!=common.bind(HERE/'candidate-source/dev/mixer/android'/(n+'.java')):raise ValueError('candidate source not frozen '+n)
    command('read-only-final-candidate-replay',[sys.executable,'-B',HERE/'check_packet.py','--candidate','candidate-3','--supplement','supplement-3'])
    command('python-version',[sys.executable,'--version'])
    producer=json.loads((HERE/'candidate-3/receipt.json').read_text());supplement=json.loads((HERE/'supplement-3/receipt.json').read_text())
    receipt.update({'status':'sealed-isolated-authored-toggle-host-build-packet-native-NOT-RUN','finishedUTC':common.now(),'candidate':'candidate-3','productionSourceClosureSHA256':producer['sourceClosureSHA256'],'baselineFixtureAPK':producer['apk'],'productionPolicyTests':33,'upstreamSyntheticGuardTests':55,'supplement':'supplement-3','supplementAPK':supplement['apk'],'supplementSourceClosureSHA256':supplement['sourceClosureSHA256'],'retainedSupplementExecutable':supplement['retainedExecutable'],'baselineFixtureBytesUnchanged':True,'unchangedNativeSwiftLibraries':18,'unmodifiedLiveSourceConfirmedBeforeRootIntegration':True,'ownedAttemptSealsVerified':8,'nativeRunner':'root owns separate derived baseline wrapper under verification/android-authored-toggle-input-runner; no native entrypoint executed by this lane','limitations':['native baseline and component execution unobserved','component fixture binding acknowledgements are not authoritative engine commits','raw native checked callbacks and component authoritative commits remain null','renderer authority lifecycle cases beyond baseline pending','TalkBack service and disabled native keys pending','physical phones disconnected deferred; Apple parity/public signed transport/separate repository FieldLog/store/operational/accountable GA pending']})
    common.save(HERE/'receipt.json',receipt)
    common.save(HERE/'packet.json',{'schema':1,'status':receipt['status'],'selectedCandidate':'candidate-3','selectedSupplement':'supplement-3','nativeDispatchAuthorized':False,'sourceRevisionAuthority':'copied source closures; root context 8c634c49 only, no lane Git commands','productionPolicyTests':33,'upstreamSyntheticGuardTests':55,'fixtureActionsUnchanged':20,'nativeRuntime':'NOT RUN','nativeAccepted':False,'gaAccepted':False,'runnerScope':'separately root-reviewed derived wrapper required; immutable candidate5 timing runner remains pinned','attempts':{n:common.bind(HERE/n/'receipt.json') for n in ['candidate-1','candidate-2','candidate-3','supplement-1','supplement-2','supplement-3','upstream-controls','upstream-controls-2']}})
    mapping=files();common.save(HERE/'packet-seal.json',{'schema':1,'excludedExactPath':'verification/android-authored-toggle-input/packet-seal.json','files':mapping})
    print(json.dumps({'status':receipt['status'],'sealedFiles':len(mapping),'packetSeal':common.bind(HERE/'packet-seal.json'),'nativeRuntime':'NOT RUN'},sort_keys=True,indent=2))
if __name__=='__main__':main()
