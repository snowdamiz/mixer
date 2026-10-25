#!/usr/bin/env python3
"""Frozen, isolated host review. Native/process/network boundaries fail closed."""
import argparse
import ast
from contextlib import redirect_stdout, redirect_stderr
import copy
import datetime
from decimal import Decimal
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import bindings

BASE=bindings.BASE; ROOT=bindings.ROOT; stable=bindings.stable; sha=bindings.sha
SPAWNS=[]

def audit(event,args):
    if event=='subprocess.Popen':
        executable,argv=args[:2]
        permitted=(str(Path(executable).resolve())==str(Path(sys.executable).resolve()) and len(argv)==5
                   and argv[1:3]==['-B','-c'] and all(marker in argv[3] for marker in
                   ['subprocess.Popen=forbidden','socket.socket.bind=forbidden','socket.socket.connect=forbidden'])
                   and Path(argv[4]).resolve().is_relative_to(BASE))
        if not permitted: raise AssertionError('Independent host boundary rejected subprocess: '+repr(argv))
        SPAWNS.append({'argv':argv,'programSHA256':sha(argv[3].encode()),'scope':'Inspected native-disabled copied Python composition only'})
    if event in ('os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex'):
        raise AssertionError('Independent host boundary rejected '+event)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

INDEPENDENT_PROGRAM=r'''import sys,subprocess,socket,json,copy,os,uuid
from pathlib import Path
def forbidden(*args,**kwargs):raise AssertionError('Native/process/network action forbidden in independent host probe')
subprocess.Popen=forbidden
socket.socket.bind=forbidden
socket.socket.connect=forbidden
def audit(event,args):
    if event in ('subprocess.Popen','os.system','os.exec','os.posix_spawn','socket.bind','socket.connect','socket.connect_ex'):forbidden()
sys.addaudithook(audit)
sys.path.insert(0,sys.argv[1])
import composition as c
base=Path(c.selection['outputBase']);request=json.loads((base/'independent-request.json').read_bytes())
runtime=base/'runtime';runtime.mkdir();documents=base/'synthetic-documents';documents.mkdir()
bridge=c.h.Bridge({'diagnostic':documents},runtime/'captures','a'*64,c.selection['trustedRootSelection']['ownedSimulatorIdentity'],allowed_cases={'keyboard-enabled-off'})
folder=runtime/'captures';rows=[]
def inventory(stage):
    try:
        captures,aux=c.auxiliary_inventory.validate(folder,c.selection['trustedRootSelection']['ownedSimulatorIdentity'])
        rows.append({'stage':stage,'accepted':True,'roles':sorted(captures),'profile':aux})
    except Exception as error:rows.append({'stage':stage,'accepted':False,'failure':type(error).__name__+': '+str(error)})
inventory('bridge-only')
old=c.ROOT/'verification/apple-focus-diagnostic-runtime-v1/runtime/captures'
journals=sorted(old.glob('0000-settings-*.json'));first=json.loads(journals[0].read_bytes());clock=[first['receivedUptime']]
bridge.settings.now=lambda:clock[0];bridge.settings.deadline=first['sessionDeadlineUptime']
for index,path in enumerate(journals):
    saved=json.loads(path.read_bytes());clock[0]=saved['receivedUptime'];record=copy.deepcopy(saved['record'])
    if 'generation' in record:record['generation']=bridge.settings.token
    bridge.request('evaluate',{'settingsDiagnostic':record})
    if index==0:inventory('valid-start')
    if request['stage']=='start':break
    if request['stage']=='payload' and any(item['complete'] and item['format']=='png' for item in bridge.settings.uploads.values()):break
inventory('valid-session')
mutation=request['mutation'];attempts=sorted((folder/'.settings-attempts').iterdir());journal=folder/'0000-settings-0000.json'
def rewrite(path,fn):
    value=json.loads(path.read_bytes());fn(value);path.write_text(json.dumps(value,sort_keys=True)+'\n')
outcome=attempts[0]/'outcome.json'
if mutation=='same-bytes-journal-replacement':
    raw=journal.read_bytes();journal.unlink();journal.write_bytes(raw)
elif mutation=='same-bytes-payload-replacement':
    path=next(folder.glob('settings-*-png.png'));raw=path.read_bytes();path.unlink();path.write_bytes(raw)
elif mutation=='external-journal-hardlink':os.link(journal,base/'unaccounted-journal.json')
elif mutation=='external-payload-hardlink':os.link(next(folder.glob('settings-*-ax.txt')),base/'unaccounted-ax.txt')
elif mutation=='orphan-payload':(folder/'settings-9999-png.png').write_bytes(b'orphan')
elif mutation=='orphan-ancillary-failure':(folder/('ancillary-'+str(uuid.uuid4())+'.json')).write_text('{"failure":"historical postcommit error"}\n')
elif mutation=='historical-ancillary-failure':rewrite(outcome,lambda v:v.update(ancillary=[{'operation':'postcommit-error','protocolOutcomeUnchanged':True}]))
elif mutation=='historical-unresolved-retirement':rewrite(outcome,lambda v:v['retirement'].update(state='unresolved'))
elif mutation=='journal-receipt-boolean':rewrite(journal,lambda v:v.update(receivedUptime=True))
elif mutation=='journal-wrong-generation':rewrite(journal,lambda v:v.update(generation=str(uuid.uuid4())))
elif mutation=='journal-duplicate-key':journal.write_text(journal.read_text().rstrip()[:-1]+',"record":{}}\n')
elif mutation=='attempt-directory-symlink':
    target=base/'retained-attempt';attempts[0].rename(target);attempts[0].symlink_to(target,target_is_directory=True)
elif mutation=='attempt-outcome-symlink':
    target=base/'retained-outcome.json';outcome.rename(target);outcome.symlink_to(target)
elif mutation=='duplicate-outcome-owner':
    other=attempts[1]/'outcome.json';owner=json.loads(outcome.read_bytes())['journal'];rewrite(other,lambda v:v.update(journal=owner))
elif mutation=='swapped-staged-journals':
    one=next(p for p in attempts[0].iterdir() if p.name.startswith('0000-settings-'));two=next(p for p in attempts[1].iterdir() if p.name.startswith('0000-settings-'))
    intermediate=base/'stage-swap';one.rename(intermediate);two.rename(one);intermediate.rename(two)
elif mutation=='guard-after-later-commit':(folder/'.settings-transaction-guard.json').write_text('{}\n')
elif mutation=='summary-extra-key':rewrite(folder/'bridge-summary.json',lambda v:v.update(authoritativeObservation={'injected':True}))
elif mutation=='summary-only-verdict':rewrite(folder/'bridge-summary.json',lambda v:v.update(verdicts=[{'passed':True}]))
elif mutation=='summary-generation-boolean':rewrite(folder/'bridge-summary.json',lambda v:v.update(generation=False))
elif mutation=='summary-observation-claim':rewrite(folder/'bridge-summary.json',lambda v:v.update(lastValidObservationAvailable=True))
elif mutation=='unknown-app-command':(folder/'0001-command-3.json').write_text('{}\n')
elif mutation=='missing-first-journal':journal.unlink()
elif mutation=='missing-middle-journal':(folder/'0000-settings-0001.json').unlink()
elif mutation=='payload-mislabeled-role':
    path=next(folder.glob('settings-*-png.png'));path.rename(folder/'0001-keyboard-witness-2.json')
elif mutation=='none':pass
else:raise AssertionError('Unknown independent mutation '+mutation)
inventory('after-mutation')
print(json.dumps({'syntheticOnly':True,'nativeExecuted':False,'keyMethodsCalled':0,'mutation':mutation,'stage':request['stage'],'rows':rows,'inventory':[str(p.relative_to(folder)) for p in sorted(folder.rglob('*'))]},sort_keys=True))
'''

def main(number):
    attempt=BASE/f'attempt-{number}';assert attempt.is_dir() and not (attempt/'receipt.json').exists()
    before=bindings.verify();assert before==json.loads((attempt/'frozen-inputs-before.json').read_bytes())
    copies=attempt/'producer-copy';snapshot=attempt/'source-inspection'
    for name,row in json.loads((attempt/'source-inspection-manifest.json').read_bytes()).items():assert sha((snapshot/name).read_bytes())==row['sha256']
    for path in copies.iterdir():assert bindings.row(path)==bindings.row(bindings.PRODUCER/path.name)
    static={}
    for path in snapshot.rglob('*.py'):
        source=path.read_text();static[str(path.relative_to(snapshot))]=[{'line':node.lineno,'kind':type(node).__name__,'source':node.name if isinstance(node,(ast.FunctionDef,ast.ClassDef)) else ast.get_source_segment(source,node)} for node in ast.parse(source).body]
    (attempt/'static-entrypoints.json').write_bytes(stable(static))
    (attempt/'reviewer-source.py').write_bytes(Path(__file__).read_bytes())
    sys.dont_write_bytecode=True;sys.addaudithook(audit);sys.path.insert(0,str(copies))
    prepare=load('prepare',copies/'prepare.py');prepare.ROOT=ROOT;prepare.BASE=copies
    prepare.OLD=ROOT/'verification/apple-focus-diagnostic-runtime-v1';prepare.V1=ROOT/'verification/apple-focus-reference-diagnostic-v1'
    prepare.V2=ROOT/'verification/apple-focus-reference-diagnostic-v2';prepare.REVIEW=ROOT/'verification/apple-focus-reference-diagnostic-v2-independent-review'
    tests=load('test_importer',copies/'test_importer.py');i=tests.i
    started=time.monotonic();outcomes={};details=[]
    def run_suite(label,suite):
        with (attempt/(label+'.stdout.log')).open('w') as out,(attempt/(label+'.stderr.log')).open('w') as err,redirect_stdout(out),redirect_stderr(err):
            result=unittest.TextTestRunner(stream=err,verbosity=2).run(suite)
        outcomes[label]={'testsRun':result.testsRun,'failures':[{'name':str(case),'traceback':tb} for case,tb in result.failures],'errors':[{'name':str(case),'traceback':tb} for case,tb in result.errors],'skipped':result.skipped,'passed':result.wasSuccessful()}
        return result
    run_suite('producer',unittest.defaultTestLoader.loadTestsFromModule(tests))
    replay=load('replay_review',copies/'replay_review.py').run(attempt)
    repair=load('test_repair',copies/'test_repair.py')
    run_suite('repair',unittest.defaultTestLoader.loadTestsFromTestCase(repair.FocusRepairControls))
    (attempt/'repair-composition-outcomes.json').write_bytes(stable(repair.FocusRepairControls.records))

    class IndependentControls(tests.RuntimeControls):
        def raw_execute(self,fixture,manifest=None,summary=None):
            raw={key:i.stable(fixture[key]) for key in ['summary','tests','manifest']}
            if manifest is not None:raw['manifest']=manifest
            if summary is not None:raw['summary']=summary
            capsule=self.host_capsule(fixture['root'],fixture['session'],fixture['observer']['exitCode'],raw,{role+'.json':i.stable(value) for role,value in fixture['values'].items()},{role:i.stable(value) for role,value in fixture['captures'].items()})
            return self.execute(fixture,capsule)

        def timestamp_case(self,token,offset=0,role='before',expected='one-strict-original-verdict-passed'):
            f=self.fixture();raw=i.stable(f['manifest'])
            old=b'1792893615.0' if role=='before' else b'1792893620.0'
            assert raw.count(old)==1;raw=raw.replace(old,token.encode())
            # Independent exact arithmetic: original decimal tuple, no ambient Decimal multiplication.
            d=Decimal(token);t=d.as_tuple();coefficient=int(''.join(map(str,t.digits)));power=t.exponent+9
            floor_ns=coefficient*10**power if power>=0 else coefficient//10**(-power)
            f['captures'][role]['signature'][1]=floor_ns+offset
            if role=='before':f['captures']['after']['signature'][1]=floor_ns+offset
            result=self.raw_execute(f,manifest=raw)
            details.append({'control':'raw-'+role+'-endpoint','token':token,'offsetNS':offset,'expected':expected,'result':result})
            self.assertEqual(result['diagnosticOutcome'],expected,result)
            if expected=='invalid-or-incomplete-evidence':self.assertIsNone(result['keyInjectionCount'])

        def test_independent_raw_nine_digit_premise_endpoint(self):self.timestamp_case('1792893615.123456789')
        def test_independent_raw_nine_digit_premise_plus_one_ns(self):self.timestamp_case('1792893615.123456789',1,expected='invalid-or-incomplete-evidence')
        def test_independent_raw_changed_after_witness_endpoint(self):self.timestamp_case('1792893620.987654321',role='after')
        def test_independent_raw_changed_after_witness_plus_one_ns(self):self.timestamp_case('1792893620.987654321',1,'after','invalid-or-incomplete-evidence')
        def test_independent_raw_tenth_digit_rejected(self):self.timestamp_case('1792893615.1234567891',expected='invalid-or-incomplete-evidence')
        def test_independent_raw_deep_fractional_tail_rejected(self):self.timestamp_case('1792893615.123456789000000000000000001',expected='invalid-or-incomplete-evidence')
        def test_independent_raw_deep_fractional_tail_below_integer_rejected(self):self.timestamp_case('1792893615.999999999999999999999999999',1,expected='invalid-or-incomplete-evidence')
        def test_independent_raw_deep_fractional_witness_tail_rejected(self):self.timestamp_case('1792893620.123456789000000000000000001',role='after',expected='invalid-or-incomplete-evidence')
        def test_independent_signature_all_fields_cross_samples(self):
            invalid={0:[False,0,-1,1.0],1:[False,-1,1.0],2:[False,0,-1,1.0,16000001],3:['G'*64,'A'*64,'0'*63,'0'*65,False]}
            for role in ['before','after']:
                for field,values in invalid.items():
                    for value in values:
                        with self.subTest(role=role,field=field,value=value):
                            f=self.fixture();f['captures'][role]['signature'][field]=value;self.reject(f)
        def test_independent_summary_cannot_fill_missing_native_key_evidence(self):
            f=self.fixture(missing=True);result=self.execute(f)
            details.append({'control':'missing-return-remains-unknown','result':result});self.assertEqual(result['diagnosticOutcome'],'unknown');self.assertIsNone(result['keyInjectionCount'])
        def test_independent_unbound_public_dict_cannot_authorize(self):
            f=self.fixture();result=self.execute(f,copy.deepcopy(f['summary']));self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence');self.assertIsNone(result['keyInjectionCount'])
        def test_independent_unchanged_files_allowed(self):
            f=self.fixture();self.assertEqual(f['captures']['before']['signature'],f['captures']['after']['signature']);self.assertEqual(self.execute(f)['diagnosticOutcome'],'one-strict-original-verdict-passed')
        def composition_probe(self,stage,mutation):
            h=prepare.helpers();rows=prepare.manifest(self.derived)
            with tempfile.TemporaryDirectory(prefix='independent-composition-',dir=prepare.BASE) as tmp:
                base=Path(tmp);h.materialize(base/'selected',rows,self.derived)
                selection=copy.deepcopy(self.template);selection.update(repositoryRoot=str(ROOT),outputBase=str(base),productsRoot=str(base/'products'),productArchive=str(prepare.V1/'compile-attempt-1/products.tar.gz'),productManifest=self.products,trustedRootSelection=self.fixture()['root'],files={name:row['sha256'] for name,row in rows.items()})
                (base/'selected/runtime-selection.json').write_bytes(stable(selection));(base/'independent-request.json').write_bytes(stable({'stage':stage,'mutation':mutation}))
                completed=subprocess.run([sys.executable,'-B','-c',INDEPENDENT_PROGRAM,str(base/'selected')],capture_output=True,text=True,timeout=45)
                label='composition-'+stage+'-'+mutation
                (attempt/(label+'.stdout.log')).write_text(completed.stdout);(attempt/(label+'.stderr.log')).write_text(completed.stderr)
                self.assertEqual(completed.returncode,0,completed.stderr);record=json.loads(completed.stdout);details.append({'control':label,'record':record})
                self.assertTrue(all(row['accepted'] for row in record['rows'][:-1]),record)
                self.assertEqual(record['rows'][-1]['accepted'],mutation=='none',record)
                if mutation=='none':
                    self.assertEqual(record['rows'][-1]['roles'],[]);self.assertIs(record['rows'][-1]['profile']['authoritativeApplicationEvidenceCreated'],False)

    mutations={
        'same-bytes-journal-replacement':'start','same-bytes-payload-replacement':'payload',
        'external-journal-hardlink':'start','external-payload-hardlink':'payload','orphan-payload':'payload',
        'orphan-ancillary-failure':'payload','historical-ancillary-failure':'payload','historical-unresolved-retirement':'payload',
        'journal-receipt-boolean':'start','journal-wrong-generation':'payload','journal-duplicate-key':'start',
        'attempt-directory-symlink':'start','attempt-outcome-symlink':'start','duplicate-outcome-owner':'payload',
        'swapped-staged-journals':'payload','guard-after-later-commit':'payload','summary-extra-key':'start',
        'summary-only-verdict':'payload','summary-generation-boolean':'start','summary-observation-claim':'payload',
        'unknown-app-command':'start','missing-first-journal':'start','missing-middle-journal':'payload',
        'payload-mislabeled-role':'payload','none':'payload'}
    for mutation,stage in mutations.items():
        def control(self,stage=stage,mutation=mutation):self.composition_probe(stage,mutation)
        setattr(IndependentControls,'test_independent_composition_'+mutation.replace('-','_'),control)
    loader=unittest.TestLoader();suite=unittest.TestSuite(IndependentControls(name) for name in loader.getTestCaseNames(IndependentControls) if name.startswith('test_independent_'))
    independent=run_suite('independent',suite)
    (attempt/'control-results.json').write_bytes(stable(details))
    (attempt/'suite-results.json').write_bytes(stable(outcomes))
    (attempt/'independent-composition-program.py').write_text(INDEPENDENT_PROGRAM)
    after=bindings.verify();(attempt/'frozen-inputs-after.json').write_bytes(stable(after));assert before==after
    temporary=[str(p) for p in copies.iterdir() if p.is_dir() and not p.name.startswith('host-attempt-')]
    output_rows={str(p.relative_to(attempt)):bindings.row(p) for p in sorted(attempt.rglob('*')) if p.is_file()}
    receipt={'schema':'mixer.apple-focus-reference-runtime-independent-review.3','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve()),'--attempt',str(number)],'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'hostUname':dict(zip(('sysname','nodename','release','version','machine'),os.uname())),'elapsedSeconds':time.monotonic()-started,'reviewerModel':'gpt-6.1-sol','reasoningEffort':'xhigh','sourceRevisionLabel':'ba9ad4372f94463ba4d363cdfd76dd565c96413f','sourceRevisionMeaning':'Inherited compile label; exact tree hashes define this review; no Git query','handoffSHA256':bindings.EXPECTED_HANDOFF,'packetSHA256':bindings.EXPECTED_PACKET,'frozenInputCount':len(before['bindings']),'bindingTreeSHA256':before['bindingTreeSHA256'],'suiteResults':outcomes,'historicalReview':{k:replay[k] for k in ['testsRun','controlsPassed','errors','skipped','failures','expectedReplayOutcome','originalReviewerSourceSHA256']},'independentPassed':independent.wasSuccessful(),'nativeExecuted':False,'runtimeSelected':False,'runPassed':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred','hostSpawns':SPAWNS,'cleanup':{'allFrozenInputsUnchanged':before==after,'ownedTemporaryDirectoriesAbsent':not temporary,'remainingOwnedScratch':temporary,'sourceSnapshotsPreserved':True,'otherProjectsTouched':False,'nativeCommandsInvoked':0,'nativeInstancesCreatedOrQueried':0,'servicesStarted':0},'outputs':output_rows,'outputTreeSHA256':sha(stable(output_rows))}
    (attempt/'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({'producer':{k:v for k,v in outcomes['producer'].items() if k not in ['failures','errors']},'repair':{k:v for k,v in outcomes['repair'].items() if k not in ['failures','errors']},'historical':{'testsRun':replay['testsRun'],'controlsPassed':replay['controlsPassed'],'failures':len(replay['failures'])},'independent':{'testsRun':independent.testsRun,'failed':len(independent.failures),'errors':len(independent.errors)},'receiptSHA256':sha((attempt/'receipt.json').read_bytes()),'cleanup':receipt['cleanup']},sort_keys=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,required=True);main(p.parse_args().attempt)
