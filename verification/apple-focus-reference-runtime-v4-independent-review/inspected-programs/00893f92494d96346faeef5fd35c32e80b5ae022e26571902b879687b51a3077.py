import sys,subprocess,socket,json,copy,time
from pathlib import Path
def forbidden(*args,**kwargs):raise AssertionError('Native command/service forbidden in V4 actual-composition host probe')
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
