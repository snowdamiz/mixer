#!/usr/bin/env python3
"""Independent host-only review. Never dispatches a native or discovery command."""
import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import traceback
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/android-pointer-oracle-repair'
OUT = HERE / 'host-review-1'
SDK = Path('/opt/homebrew/share/android-commandlinetools')
EXPECTED = {
    'packet-seal.json': '275e733bbc31262c12bf65402fc12e110a43c9f5d14cb41ad157be7a5d755fd5',
    'packet.json': 'd9511187a6466b9d3253ccfdfa971aa95fb10cdcfdd73d058c1e2e28bf22c98b',
    'run.py': '3aa02d1b8469ca3f14c355738f16ed774a2c0431007df9f03474b87c99a188d5',
    'oracle.py': '969dc86860e5b1bbce4941645eef68694401fc9839debf7b137c4dcaf9181dcf',
    'runner-contract-4.json': 'a757865ecd435422d3cc1da98d4a0669d34ab7a5b0d14c3ed6ed97265541b63f',
    'runner-source-4/transformed_runner.py': 'bd7cd16883a831aac29fa13d162eabf6fae78c88c6b523919e4d9b38c0103b31',
    'candidate-5/built-artifacts.tar.gz': '847de52459dbe90b8fd5abbe186aaf2f936cce38981cbc28ce86b36bcdc9249b',
}

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, value): Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def bind(path): return {'bytes': Path(path).stat().st_size, 'sha256': sha(path)}

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

def probes(work):
    sys.path.insert(0, str(PRODUCER))
    import common
    import oracle
    import test_host
    results = []

    def probe(name, mutate=None, *, should_accept=False, finding=None):
        directory = work / name
        native, metadata = test_host.synthetic_oracle_fixture(directory)
        rows = [json.loads(line) for line in (directory / 'pointer-observations.jsonl').read_text().splitlines()]
        original = copy.deepcopy(rows)
        if mutate: mutate(native, rows, directory)
        test_host.rewrite_rows(directory, native, rows)
        error = None
        result = None
        try:
            result = oracle.validate(native, directory, metadata)
            accepted = True
        except (ValueError, KeyError, TypeError) as failure:
            accepted = False
            error = repr(failure)
        item = {'case': name, 'shouldAccept': should_accept, 'observedAccepted': accepted,
                'expectationMet': accepted == should_accept, 'exception': error, 'oracleResult': result,
                'finding': finding, 'syntheticOnly': True, 'nativeEvidence': False,
                'mutatedObservationRows': [r for r in rows if r not in original],
                'removedObservationRows': [r for r in original if r not in rows]}
        if finding:
            kept = OUT / 'reproductions' / name
            kept.parent.mkdir(exist_ok=True)
            shutil.copytree(directory, kept)
            save(kept / 'native.json', native)
            save(kept / 'metadata.json', metadata)
            item['retainedFixture'] = str(kept.relative_to(ROOT))
        save(OUT / (name + '.json'), item)
        results.append(item)
        print(json.dumps({k: item[k] for k in ('case', 'shouldAccept', 'observedAccepted', 'expectationMet', 'exception', 'finding')}, sort_keys=True), flush=True)

    def delivered(rows, action='P03-1'):
        return [r for r in rows if r['kind'] in ('activity-entry', 'activity-exit') and r.get('actionId') == action]

    probe('baseline', should_accept=True)
    probe('coalesced-valid-move', lambda n,r,d: test_host.coalesce(n,r), should_accept=True)
    def dropped(n,r,d):
        r[:] = [x for x in r if not (x['kind'] in ('activity-entry','activity-exit') and x.get('actionId')=='P03-1' and x['event']['action']==2 and x['event']['eventTime'] != x['event']['downTime']+640)]
        n['summaries'][2]['nativeDeliveryCount'] = 3
    probe('dropped-intermediate-valid', dropped, should_accept=True)
    def exact_boundary(n,r,d):
        for x in r:
            if x['kind']=='activity-entry': x['workerIndependentUptime'] = x['event']['eventTime']+1
            elif x['kind']=='activity-exit': x['uptime'] = x['event']['eventTime']+2
    probe('worker-delivery-equal-ms-boundary', exact_boundary, should_accept=True)
    for flag in (1,2,3):
        def obscured(n,r,d,flag=flag):
            for x in delivered(r): x['event']['flags']=flag
        probe('old-F01-obscured-'+str(flag), obscured)
    def bad_pressure(n,r,d):
        for x in delivered(r):
            if x['event']['action']==2: x['event']['pointers'][0]['pressure']=0
    probe('old-F02-pressure', bad_pressure)
    def bad_history(n,r,d):
        test_host.coalesce(n,r)
        for x in delivered(r):
            if x['event']['history']: x['event']['history'][0]['eventTime']=x['event']['downTime']+17
    probe('old-F03-history-offpath', bad_history)
    def no_moves(n,r,d):
        r[:] = [x for x in r if not (x['kind'] in ('activity-entry','activity-exit') and x.get('actionId')=='P03-1' and x['event']['action']==2)]
        n['summaries'][2]['nativeDeliveryCount']=2
    probe('old-F04-no-moves', no_moves)
    def late(n,r,d):
        x=next(x for x in r if x['kind']=='worker-send' and x.get('actionId')=='P01-1')
        x['workerAfter']=n['summaries'][0]['actionEndUptime']+1
    probe('old-F05-worker-outside-action', late)
    def before_worker(n,r,d):
        # 1 ms before workerBefore; still >= eventTime and within the action.
        for x in delivered(r, 'P01-1'):
            if x['kind']=='activity-entry': x['workerIndependentUptime']=x['event']['eventTime']
            else: x['uptime']=x['event']['eventTime']
    probe('new-F06-delivery-before-worker', before_worker, finding='F06')
    def future_event(n,r,d):
        # Both callbacks happen 1 ms before the timestamp of their event.
        for x in delivered(r,'P01-1'):
            if x['kind']=='activity-entry': x['workerIndependentUptime']=x['event']['eventTime']-1
            else: x['uptime']=x['event']['eventTime']-1
    probe('new-F06-delivery-before-eventtime', future_event, finding='F06')
    def after_worker(n,r,d):
        for x in delivered(r,'P01-1'):
            if x['kind']=='activity-entry': x['workerIndependentUptime']=x['event']['eventTime']+3
            else: x['uptime']=x['event']['eventTime']+4
    probe('new-F06-delivery-after-sync-return', after_worker, finding='F06')
    def terminal_history(n,r,d,action='P03-1'):
        moves=[x for x in r if x['kind']=='activity-entry' and x.get('actionId')==action and x['event']['action']==2]
        history=[{'eventTime':x['event']['eventTime'],'pointers':[{'id':0,'x':x['event']['pointers'][0]['x'],'y':x['event']['pointers'][0]['y'],'pressure':1}]} for x in moves]
        r[:]=[x for x in r if not(x['kind'] in ('activity-entry','activity-exit') and x.get('actionId')==action and x['event']['action']==2)]
        for x in delivered(r,action):
            if x['event']['action'] in (1,3): x['event']['history']=copy.deepcopy(history)
        n['summaries'][2 if action=='P03-1' else 4]['nativeDeliveryCount']=2
    probe('new-F07-all-moves-only-UP-history', terminal_history, finding='F07')
    probe('new-F07-all-moves-only-CANCEL-history', lambda n,r,d:terminal_history(n,r,d,'P05-1'), finding='F07')
    def history_wrong_offset(n,r,d):
        test_host.coalesce(n,r)
        for x in delivered(r):
            if x['event']['history']:x['event']['history'][0]['pointers'][0]['x']+=10
    probe('history-offset-negative', history_wrong_offset)
    def duplicate(n,r,d):
        test_host.coalesce(n,r)
        for x in delivered(r):
            if x['event']['history']:x['event']['history'][1]['eventTime']=x['event']['history'][0]['eventTime']
    probe('history-duplicate-negative', duplicate)
    def cross_dispatch(n,r,d):
        x=[x for x in delivered(r,'P01-1') if x['kind']=='activity-exit'][0]
        x['uptime']=x['event']['eventTime']+90
    probe('activity-overlap-negative', cross_dispatch)
    policy=[]
    for attempt in ('../runtime-1','runtime/runtime-1','runtime-0','runtime-01','/tmp/runtime-1'):
        try: common.runtime_directory(attempt); accepted=True
        except ValueError: accepted=False
        policy.append({'attempt':attempt,'accepted':accepted})
    base=work/'policy';here=base/'verification/android-pointer-oracle-repair';here.mkdir(parents=True)
    (base/'docs').mkdir();(base/'docs/android-pointer-oracle-repair.md').write_text('review fixture')
    runtime=here/'runtime';runtime.mkdir();(runtime/'runtime-1').mkdir()
    with patch.object(common,'HERE',here),patch.object(common,'RUNTIME',runtime),patch.object(common,'ROOT',base):
        try:common.runtime_directory('runtime-1');reused=True
        except ValueError:reused=False
        (runtime/'runtime-1/receipt.json').write_text('{}')
        import check_packet
        (here/'nested').mkdir();(here/'nested/artifact-seal.json').write_text('{}')
        bindings=check_packet.files()
        (runtime/'runtime-1/receipt.json').write_text('{"changed":true}')
        unchanged=check_packet.files()==bindings
        link=runtime/'escaped';link.symlink_to(base/'docs/android-pointer-oracle-repair.md')
        try:check_packet.files();symlink_accepted=True
        except ValueError:symlink_accepted=False
        finally:link.unlink()
        policy.extend([{'reusedAttemptAccepted':reused},{'onlyDesignatedRuntimeExcluded':unchanged},
                       {'nestedReceiptBound':'verification/android-pointer-oracle-repair/nested/artifact-seal.json' in bindings},
                       {'excludedRuntimeSymlinkAccepted':symlink_accepted}])
    save(OUT/'runtime-policy.json',policy)
    save(OUT/'adversarial-results.json',results)
    failures=[r for r in results if not r['expectationMet']]
    print(json.dumps({'probes':len(results),'unexpectedAcceptances':len(failures),'syntheticOnly':True,'nativeDispatch':False},sort_keys=True))
    return 0

def main():
    OUT.mkdir()
    receipt={'startedUTC':now(),'scope':'independent host source/artifact/parser review only','nativeCommands':0,'physicalDiscovery':False,'producerMutation':False,'commands':[],'reviewerSource':bind(__file__)}
    scratch=Path(tempfile.mkdtemp(prefix='mixer-pointer-oracle-independent-',dir='/private/tmp'))
    identity=scratch.stat();receipt['scratch']={'path':str(scratch),'device':identity.st_dev,'inode':identity.st_ino}
    def command(name, argv, *, allowed=(0,), env=None):
        started=now()
        result=subprocess.run([str(x) for x in argv],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120,env=env,start_new_session=True)
        path=OUT/(name+'.log');path.write_bytes(result.stdout)
        receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'cwd':str(ROOT),'startedUTC':started,'finishedUTC':now(),'exitCode':result.returncode,'output':str(path.relative_to(ROOT)),**bind(path)})
        save(OUT/'receipt.json',receipt)
        if result.returncode not in allowed:raise RuntimeError(name+' failed '+str(result.returncode))
        return result.stdout
    try:
        command('python-version',[sys.executable,'--version'])
        command('source-revision',['git','rev-parse','HEAD'])
        command('source-tree',['git','rev-parse','HEAD^{tree}'])
        command('source-status',['git','status','--short'])
        receipt['toolBindings']={str(p):bind(p) for p in (Path(sys.executable).resolve(),Path('/usr/sbin/lsof'),SDK/'build-tools/37.0.0/zipalign',SDK/'build-tools/37.0.0/apksigner',SDK/'build-tools/37.0.0/lib/apksigner.jar')}
        bindings={name:bind(PRODUCER/name) for name in EXPECTED}
        if any(bindings[n]['sha256']!=h for n,h in EXPECTED.items()):raise ValueError('designated candidate binding drift')
        receipt['producerBindings']=bindings
        command('packet-check-before',[sys.executable,'-B',PRODUCER/'check_packet.py'])
        hostwork=scratch/'producer-host';hostwork.mkdir()
        command('producer-host-tests',[sys.executable,'-B',PRODUCER/'test_host.py','--work',hostwork])
        probework=scratch/'independent-probes';probework.mkdir()
        command('independent-probes',[sys.executable,'-B',__file__,'--probes',probework])
        sys.path.insert(0,str(PRODUCER))
        import common
        import run
        guard=module('review_apk_guard',ROOT/'verification/android-coordinator-apk-packaging/apk_packaging.py')
        candidate=common.candidate(PRODUCER/'candidate-5',guard)
        runner,source,_=run.load_runner()
        if hashlib.sha256(source.encode()).hexdigest()!=EXPECTED['runner-source-4/transformed_runner.py']:raise ValueError('concrete runner mismatch')
        apk=Path(json.loads((PRODUCER/'packet.json').read_text())['retainedSignedAPK']['path'])
        if sha(apk)!='57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714':raise ValueError('retained APK drift')
        layout=guard.validate(apk);save(OUT/'independent-apk-packaging.json',layout)
        command('zipalign-version',[SDK/'build-tools/37.0.0/zipalign','-h'],allowed=(0,2))
        command('apksigner-version',[SDK/'build-tools/37.0.0/apksigner','version'])
        command('official-zipalign',[SDK/'build-tools/37.0.0/zipalign','-c','-P','16','-v','4',apk])
        signature=command('official-apksigner',[SDK/'build-tools/37.0.0/apksigner','verify','--verbose','--print-certs',apk])
        if re.findall(rb'certificate SHA-256 digest: ([0-9a-f]{64})',signature)!=[candidate['debugCertificateSHA256'].encode()]:raise ValueError('debug signing certificate mismatch')
        old=ROOT/'verification/android-pointer-fixture/candidate-4'
        lock4=json.loads((old/'source-lock.json').read_text())['files'];lock5=json.loads((PRODUCER/'candidate-5/source-lock.json').read_text())['files']
        artifacts4=json.loads((old/'built-artifacts.json').read_text());artifacts5=json.loads((PRODUCER/'candidate-5/built-artifacts.json').read_text())
        closure=hashlib.sha256(json.dumps(lock5,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        delta={'sourceClosureSHA256':closure,'sourceInputs':len(lock5),'changedSources':sorted(k for k in set(lock4)|set(lock5) if lock4.get(k)!=lock5.get(k)),
               'changedArtifacts':sorted(k for k in set(artifacts4)|set(artifacts5) if artifacts4.get(k)!=artifacts5.get(k)),
               'productionClassesUnchanged':sum(k.startswith('production-classes/') and artifacts4.get(k)==v for k,v in artifacts5.items()),
               'nativeLibrariesUnchanged':sum(k.startswith('apk/lib/') and artifacts4.get(k)==v for k,v in artifacts5.items()),
               'nativeSDKInputsUnchangedAndRechecked':sum(k.startswith(('native/','sdk/')) and lock4.get(k)==v and sha(ROOT/k)==v for k,v in lock5.items()),
               'freshJavacDEXReplay':'producer build-replay-1 is recursively bound by packet check; no redundant historical rebuild performed',
               'APK':bind(apk),'archive':bind(PRODUCER/'candidate-5/built-artifacts.tar.gz')}
        assert closure=='9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce'
        assert delta['changedSources']==['verification/android-coordinator-join/CoordinatorJoinInstrumentation.java']
        assert delta['changedArtifacts']==['coordinator-join.apk','dex/classes.dex','test-classes/dev/mixer/android/CoordinatorJoinInstrumentation.class']
        assert (delta['productionClassesUnchanged'],delta['nativeLibrariesUnchanged'],delta['nativeSDKInputsUnchangedAndRechecked'])==(155,18,88)
        save(OUT/'independent-artifact-review.json',delta)
        command('packet-check-after',[sys.executable,'-B',PRODUCER/'check_packet.py'])
        receipt['status']='completed-host-review-with-two-reproducible-oracle-findings'
    except BaseException as failure:
        receipt['failure']=repr(failure);receipt['status']='failed-host-review-execution';(OUT/'failure.log').write_text(traceback.format_exc())
        raise
    finally:
        receipt['scratch']['filesBeforeCleanup']=sum(p.is_file() for p in scratch.rglob('*'))
        receipt['scratch']['bytesBeforeCleanup']=sum(p.stat().st_size for p in scratch.rglob('*') if p.is_file())
        if scratch.is_symlink() or (scratch.stat().st_dev,scratch.stat().st_ino)!=(identity.st_dev,identity.st_ino):raise ValueError('owned scratch identity changed')
        holders=command('scratch-open-holders',['/usr/sbin/lsof','-nP','+D',scratch],allowed=(0,1))
        if holders:raise ValueError('owned scratch has open holders')
        if scratch.is_symlink() or (scratch.stat().st_dev,scratch.stat().st_ino)!=(identity.st_dev,identity.st_ino):raise ValueError('owned scratch changed after holder check')
        shutil.rmtree(scratch);receipt['scratch']['removed']=not scratch.exists();receipt['scratch']['openHoldersEmpty']=True
        receipt['finishedUTC']=now();save(OUT/'receipt.json',receipt)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--probes',type=Path);args=parser.parse_args()
    if args.probes:raise SystemExit(probes(args.probes))
    main()
