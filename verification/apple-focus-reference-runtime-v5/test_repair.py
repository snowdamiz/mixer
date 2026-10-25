"""V5 production-composition and exact-metadata controls. All observations are host fixtures."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
import prepare
import test_importer as legacy

PRODUCTION_PROGRAM = r'''import sys,subprocess,socket,json,copy,time
from pathlib import Path
def forbidden(*args,**kwargs):raise AssertionError('Native command/service forbidden in V5 actual-composition host probe')
subprocess.Popen=forbidden
socket.socket.bind=forbidden
socket.socket.connect=forbidden
sys.path.insert(0,sys.argv[1])
import composition as c
base=Path(c.selection['outputBase']);request=json.loads((base/'probe-request.json').read_bytes())
runtime=base/'runtime';runtime.mkdir();documents=base/'synthetic-documents';documents.mkdir()
bridge=c.h.Bridge({'diagnostic':documents},runtime/'captures','a'*64,c.selection['trustedRootSelection']['ownedSimulatorIdentity'],allowed_cases={'keyboard-enabled-off'})
folder=runtime/'captures';rows=[]
def observe(stage):
    try:
        captures=c.join_support.application_captures(base)
        _,profile=c.auxiliary_inventory.validate(folder,c.selection['trustedRootSelection']['ownedSimulatorIdentity'])
        result={'accepted':True,'roles':sorted(captures),'journalCount':profile['settingsJournalCount'],'payloadCount':profile['settingsPayloadCount'],'attemptCount':profile['settingsAttemptCount'],'auxiliaryCreatesAppEvidence':profile['authoritativeApplicationEvidenceCreated']}
    except Exception as error:result={'accepted':False,'failure':type(error).__name__+': '+str(error)}
    result.update(stage=stage,files=[p.name for p in sorted(folder.iterdir())]);rows.append(result)
observe('actual-composed-bridge-construction')
old=c.ROOT/'verification/apple-focus-diagnostic-runtime-v1/runtime/captures'
journals=sorted(old.glob('0000-settings-*.json'));first=json.loads(journals[0].read_bytes());clock=[first['receivedUptime']]
bridge.settings.now=lambda:clock[0];bridge.settings.deadline=first['sessionDeadlineUptime']
if request['mutation']=='retirement-uncertain':
    original_sync=bridge.persistence.io.sync
    def fail_retirement(path,role):
        if role=='postcommit-guard-directory':raise OSError('Synthetic postcommit retirement failure')
        return original_sync(path,role)
    bridge.persistence.io.sync=fail_retirement
if request['mutation']=='outcome-write-failure':
    original_write=bridge.persistence.io.write
    def fail_outcome(path,payload,role):
        if role=='attempt-outcome':raise OSError('Synthetic attempt outcome write failure')
        return original_write(path,payload,role)
    bridge.persistence.io.write=fail_outcome
payload_stage=False
for index,path in enumerate(journals):
    saved=json.loads(path.read_bytes());clock[0]=saved['receivedUptime'];record=copy.deepcopy(saved['record'])
    if 'generation' in record:record['generation']=bridge.settings.token
    bridge.request('evaluate',{'settingsDiagnostic':record})
    if index==0:observe('actual-session-start-transaction-commit')
    if any(item['complete'] is True and item['format']=='png' for item in bridge.settings.uploads.values()) and not payload_stage:
        observe('actual-session-linked-ax-and-png-publication');payload_stage=True
    if request['stage']=='start':break
    if request['stage']=='payload' and payload_stage:break
if request['stage'] in ['complete','baseline']:
    observe('actual-complete-settings-transaction-journals')
if request['stage']=='baseline':
    bridge.request('begin',{'candidate':'diagnostic','case':'keyboard-enabled-off'})
    state=json.loads((old/'0001-before-1.json').read_bytes())['observation'];state['state']['focused']=False;state['stage']='host-synthetic-launch'
    native=documents/'observations.json';native.write_text(json.dumps(state,sort_keys=True,separators=(',',':'))+'\n')
    bridge.request('ready',{})
    actual_write=bridge.write_command
    def fake_app_ack(command):
        actual_write(command)
        value=json.loads(native.read_bytes());value['stage']=command
        event=copy.deepcopy(value['events'][-1]);event.update(sequence=len(value['events']),stage=command,reason='host-synthetic-ack');value['events'].append(event)
        native.write_text(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n')
    bridge.write_command=fake_app_ack
    for command in ['resume','reset']:bridge.request('command',{'command':command})
    geometry=json.loads((old/'0001-before-1.json').read_bytes())['geometry']
    baseline=bridge.request('baseline',{'action':'native-keyboard','geometry':geometry})
    observe('actual-before-premise-zero-injection-baseline-with-settings')
    before=json.loads((folder/'0001-before-1.json').read_bytes())
    witness=json.loads((old/'0001-keyboard-witness-1.json').read_bytes())['witness']
    for row in witness['before']['elements'].values():row['hasFocus']=False
    p={'schema':c.reference_contract.SCHEMA,'case':'keyboard-enabled-off','phase':'acquire','generation':baseline['generation'],'actionIndex':baseline['actionIndex'],'requiredFocus':'plain-uibutton-reference','observedFocus':None,'passed':False,'actionInjectionCount':0,'before':witness['before']}
    classification=c.reference_contract.result([p],[],c.oracle)
    rows[-1]['syntheticFalsePremiseClassification']=classification['status'];rows[-1]['syntheticInjectionCount']=classification['keyInjectionCount']
mutation=request['mutation']
if mutation=='guard':(folder/'.settings-transaction-guard.json').write_bytes(b'{}')
elif mutation=='bridge-failure':bridge.record_failure('host-test',ValueError('Synthetic bridge failure'))
elif mutation=='foreign-action':(folder/'0001-before-2.json').write_bytes(b'{}')
elif mutation=='foreign-generation':(folder/'0002-begin.json').write_bytes(b'{}')
elif mutation=='unknown-settings-prefix':(folder/'0000-settings-anything.json').write_bytes(b'{}')
elif mutation=='invalid-lower-level-journal':bridge.persistence.commit(('settings-0001',{'record':'host-only-independent-synthetic-payload-publication'}),[])
elif mutation=='payload-corrupt':
    payload=next(folder.glob('settings-*-ax.txt'));payload.write_bytes(payload.read_bytes()+b'corrupt')
elif mutation in ['outcome-extra','outcome-boolean','missing-outcome','attempt-foreign-file','attempt-foreign-name','payload-symlink','journal-identity']:
    attempt=next((folder/'.settings-attempts').iterdir())
    if mutation=='missing-outcome':(attempt/'outcome.json').unlink()
    elif mutation=='attempt-foreign-file':(attempt/'foreign.dat').write_bytes(b'foreign')
    elif mutation=='attempt-foreign-name':attempt.rename(attempt.parent/'foreign')
    elif mutation=='payload-symlink':
        path=next(folder.glob('settings-*-ax.txt'));path.rename(folder/'retained-ax.txt');path.symlink_to(folder/'retained-ax.txt')
    elif mutation=='journal-identity':
        path=folder/'0000-settings-0000.json';value=json.loads(path.read_bytes());value['ownedSimulatorIdentity']['udid']='foreign';path.write_text(json.dumps(value)+'\n')
    else:
        path=attempt/'outcome.json';value=json.loads(path.read_bytes())
        if mutation=='outcome-extra':value['unrecognized']='foreign'
        else:value['retirement']['guardAbsenceEstablished']=1
        path.write_text(json.dumps(value)+'\n')
if mutation!='none':observe('after-adversarial-mutation')
print(json.dumps({'syntheticOnly':True,'nativeExecuted':False,'keyInjectionCalls':0,'rows':rows,'guardPresent':bridge.persistence.guard.exists(),'persistenceUncertain':bridge.persistence.uncertain,'retirementPending':bridge.persistence.retirement_pending},sort_keys=True))
'''


class FocusRepairControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        legacy.RuntimeControls.setUpClass();cls.ref=legacy.RuntimeControls('test_001_one_complete_strict_original_pass_is_diagnostic_only');cls.records=[]
    @classmethod
    def tearDownClass(cls):legacy.RuntimeControls.tearDownClass()

    def probe(self,stage='start',mutation='none'):
        ref=self.ref;h=prepare.helpers();rows=prepare.manifest(ref.derived)
        with tempfile.TemporaryDirectory(prefix='actual-composition-',dir=prepare.BASE) as temp:
            base=Path(temp);h.materialize(base/'selected',rows,ref.derived)
            selection=copy.deepcopy(ref.template);selection.update(repositoryRoot=str(prepare.ROOT),outputBase=str(base),productsRoot=str(base/'products'),productArchive=str(prepare.V1/'compile-attempt-1/products.tar.gz'),productManifest=ref.products,trustedRootSelection=ref.fixture()['root'],files={name:row['sha256'] for name,row in rows.items()})
            (base/'selected/runtime-selection.json').write_bytes(prepare.stable(selection));(base/'probe-request.json').write_bytes(prepare.stable({'stage':stage,'mutation':mutation}))
            completed=subprocess.run([sys.executable,'-B','-c',PRODUCTION_PROGRAM,str(base/'selected')],capture_output=True,text=True,timeout=45)
            self.assertEqual(completed.returncode,0,completed.stderr)
            value=json.loads(completed.stdout);value.update(mode=stage,mutation=mutation,probeProgramSHA256=prepare.sha(PRODUCTION_PROGRAM.encode()))
            self.records.append(value)
            for row in value['rows'][:-1] if mutation!='none' else value['rows']:
                if mutation in ['retirement-uncertain','outcome-write-failure'] and row['stage']!='actual-composed-bridge-construction':
                    self.assertFalse(row['accepted'],row)
                else:
                    self.assertTrue(row['accepted'],row)
                    self.assertIs(row['auxiliaryCreatesAppEvidence'],False)
            self.assertIs(value['nativeExecuted'],False);self.assertEqual(value['keyInjectionCalls'],0)
            return value

    def test_actual_bridge_and_valid_session_ax_png_publication(self):
        value=self.probe('payload');row=value['rows'][-1];self.assertTrue(row['accepted']);self.assertGreater(row['payloadCount'],1);self.assertEqual(row['roles'],[]);self.assertEqual(row['attemptCount'],row['journalCount'])

    def test_actual_complete_settings_then_before_premise_zero_input_inventory(self):
        value=self.probe('baseline');row=value['rows'][-1];self.assertTrue(row['accepted']);self.assertEqual(row['roles'],['before','begin']);self.assertGreater(row['payloadCount'],1);self.assertEqual(row['syntheticFalsePremiseClassification'],'failed-reference-precondition');self.assertEqual(row['syntheticInjectionCount'],0)

    def test_invalid_transactionstore_record_is_not_session_journal(self):
        value=self.probe('start','invalid-lower-level-journal');self.assertFalse(value['rows'][-1]['accepted']);self.assertIn('Session journal',value['rows'][-1]['failure'])

    def reject_metadata(self,mutate):
        fixture=self.ref.fixture();mutate(fixture);self.ref.reject(fixture)

    def test_signature_closed_schema_all_four_fields(self):
        for role,index,values in [('before',0,[False,-1,1.0,0]),('after',0,[True,-1,1.0]),('before',1,[True,-1,1.5]),('after',2,[False,0,-1,1.5,16_000_001]),('before',3,['g'*64,'A'*64,'f'*63,'not-a-sha256',1])]:
            for value in values:
                with self.subTest(role=role,index=index,value=value):self.reject_metadata(lambda f,r=role,n=index,v=value:f['captures'][r]['signature'].__setitem__(n,v))

    def test_command_generation_exact_integer(self):
        for value in [True,False,2.0,'2',None]:
            with self.subTest(value=value):self.reject_metadata(lambda f,v=value:f['captures']['before'].update(commandGeneration=v))

    def execute_signature_boundary(self,role,offset):
        f=self.ref.fixture();timestamp=f['manifest'][1]['attachments'][0 if role=='before' else 2]['timestamp'];endpoint=legacy.i.decimal_timestamp_ns(Decimal(str(timestamp)))
        f['captures'][role]['signature'][1]=endpoint+offset
        if role=='before':f['captures']['after']['signature'][1]=endpoint+offset
        return self.ref.execute(f)

    def test_before_premise_exact_decimal_endpoint_and_one_nanosecond(self):
        self.assertEqual(self.execute_signature_boundary('before',0)['diagnosticOutcome'],'one-strict-original-verdict-passed')
        result=self.execute_signature_boundary('before',1);self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence');self.assertIsNone(result['keyInjectionCount'])

    def test_changed_after_uses_witness_endpoint_and_one_nanosecond(self):
        self.assertEqual(self.execute_signature_boundary('after',0)['diagnosticOutcome'],'one-strict-original-verdict-passed')
        result=self.execute_signature_boundary('after',1);self.assertEqual(result['diagnosticOutcome'],'invalid-or-incomplete-evidence');self.assertIsNone(result['keyInjectionCount'])

    def test_unchanged_signature_does_not_require_post_key_file_write(self):
        f=self.ref.fixture();self.assertEqual(f['captures']['before']['signature'],f['captures']['after']['signature']);self.assertEqual(self.ref.execute(f)['diagnosticOutcome'],'one-strict-original-verdict-passed')

    def test_exact_decimal_nanoseconds_avoid_epoch_float_rounding(self):
        self.assertEqual(legacy.i.decimal_timestamp_ns(Decimal('1792893615.123456789')),1792893615123456789)
        self.assertEqual(legacy.i.decimal_timestamp_ns(Decimal('1792893615.123')),1792893615123000000)
        with self.assertRaises(ValueError):legacy.i.decimal_timestamp_ns(Decimal('1792893615.1234567891'))
        self.assertEqual(legacy.i.datetime_ns('2026-10-25T02:00:00.123456+00:00'),1792893600123456000)

    def test_original_raw_decimal_tokens_are_used_for_import(self):
        f=self.ref.fixture();raw={key:legacy.i.stable(f[key]) for key in ['summary','tests','manifest']}
        raw['manifest']=raw['manifest'].replace(b'1792893615.0',b'1792893615.123456789')
        endpoint=1792893615123456789;f['captures']['before']['signature'][1]=endpoint;f['captures']['after']['signature'][1]=endpoint
        def capsule():return self.ref.host_capsule(f['root'],f['session'],0,raw,{role+'.json':legacy.i.stable(value) for role,value in f['values'].items()},{role:legacy.i.stable(value) for role,value in f['captures'].items()})
        self.assertEqual(self.ref.execute(f,capsule())['diagnosticOutcome'],'one-strict-original-verdict-passed')
        f['captures']['before']['signature'][1]+=1;f['captures']['after']['signature'][1]+=1
        self.assertEqual(self.ref.execute(f,capsule())['diagnosticOutcome'],'invalid-or-incomplete-evidence')


MUTATIONS={
 'unresolved_guard':('start','guard'),
 'actual_bridge_failure':('start','bridge-failure'),
 'actual_retirement_uncertainty':('start','retirement-uncertain'),
 'actual_attempt_reporting_failure':('start','outcome-write-failure'),
 'foreign_action':('start','foreign-action'),
 'foreign_generation':('start','foreign-generation'),
 'unknown_settings_name':('start','unknown-settings-prefix'),
 'journal_linked_payload_corruption':('payload','payload-corrupt'),
 'unexpected_attempt_outcome_member':('start','outcome-extra'),
 'incorrect_outcome_boolean_type':('start','outcome-boolean'),
 'missing_attempt_outcome':('start','missing-outcome'),
 'unreferenced_staged_file':('start','attempt-foreign-file'),
 'foreign_attempt_name':('start','attempt-foreign-name'),
 'journal_linked_payload_symlink':('payload','payload-symlink'),
 'foreign_journal_device':('start','journal-identity'),
}
for name,(stage,mutation) in MUTATIONS.items():
    def control(self,stage=stage,mutation=mutation):
        value=self.probe(stage,mutation);self.assertFalse(value['rows'][-1]['accepted'],value)
    setattr(FocusRepairControls,'test_auxiliary_rejects_'+name,control)
