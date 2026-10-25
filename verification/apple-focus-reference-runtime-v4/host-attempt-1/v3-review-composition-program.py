import sys,subprocess,socket,json,copy,os,uuid
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
