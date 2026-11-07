"""Independent finite oracle for actual UIKit semantic callback observations."""
import copy

def cases():
 result=[]
 for initial in [False,True]:
  for ax in [False,True]:
   for mode,enabled,input_ in [('admitted',True,True),('blocked',False,True),('blocked',True,False),('blocked',False,False)]:result.append((mode,initial,ax,enabled,input_))
 for initial in [False,True]:
  for mode in ['reentrant-primary','reentrant-accessibility']:result.append((mode,initial,False,True,True))
 for mode in ['rebind-selection','rebind-cancel','close-selection','close-cancel']:
  for initial in [False,True]:
   for ax in [False,True]:result.append((mode,initial,ax,True,True))
 return result

def verify(rows):
 assert type(rows) is list and len(rows)==36
 identities=set();checks=0
 for i,(row,spec) in enumerate(zip(rows,cases())):
  mode,initial,ax,enabled,input_=spec
  assert set(row)=={'index','mode','initial','accessibility','enabled','input','hookFired','returned','nestedReturn','before','after'}
  assert type(row['index']) is int and row['index']==i and row['mode']==mode
  for k,v in [('initial',initial),('accessibility',ax),('enabled',enabled),('input',input_)]:assert type(row[k]) is bool and row[k] is v
  assert row['hookFired'] is (mode not in ['admitted','blocked'])
  before,after=row['before'],row['after']
  for x in [before,after]:
   assert set(x)=={'selected','retained','primary','accepted','events','lastValue','identity','enabled','allowed','selectedTrait','disabledTrait','buttonTrait','toggleTrait','nativeAutomaticSelection','label','hint'}
   for k in ['selected','retained','enabled','allowed','selectedTrait','disabledTrait','buttonTrait','toggleTrait','nativeAutomaticSelection']:assert type(x[k]) is bool
   for k in ['primary','accepted','events']:assert type(x[k]) is int and x[k]>=0
   assert type(x['identity']) is str and x['identity']
   assert x['selected']==x['retained']==x['selectedTrait'] and x['disabledTrait'] is (not x['enabled'])
   assert x['buttonTrait'] and x['toggleTrait'] and not x['nativeAutomaticSelection']
   assert x['label']=='Sync entries' and x['hint']=='Updates the sync preference'
  assert before['identity']==after['identity'];identities.add(before['identity'])
  assert before['selected'] is initial and before['enabled'] is enabled and before['allowed'] is input_
  accepted=mode in ['admitted','reentrant-primary','reentrant-accessibility']
  value=not initial if accepted or mode=='rebind-cancel' else initial
  assert after['selected'] is value and after['enabled'] is enabled
  assert after['allowed'] is (False if mode.startswith('close-') else input_)
  assert after['events']-before['events']==int(accepted) and after['accepted']-before['accepted']==int(accepted)
  assert after['lastValue']==(not initial if accepted else before['lastValue'])
  expected_primary=0 if ax and mode=='blocked' else 2 if mode=='reentrant-primary' else 1
  assert after['primary']-before['primary']==expected_primary
  assert row['returned'] is (accepted if ax else None)
  assert row['nestedReturn'] is (False if mode=='reentrant-accessibility' else None)
  checks+=1
 assert len(identities)==1
 return {'cases':checks,'status':'passed-semantic-callback-components-only','heldPanAccessibility':'pending-real-input-case','physicalVoiceOver':'pending-final-matrix'}

def host_fixture():
 rows=[]
 for i,(mode,initial,ax,enabled,input_) in enumerate(cases()):
  accepted=mode in ['admitted','reentrant-primary','reentrant-accessibility'];value=not initial if accepted or mode=='rebind-cancel' else initial
  before=dict(selected=initial,retained=initial,primary=11,accepted=5,events=7,lastValue=False,identity='host-oracle-fixture-only',enabled=enabled,allowed=input_,selectedTrait=initial,disabledTrait=not enabled,buttonTrait=True,toggleTrait=True,nativeAutomaticSelection=False,label='Sync entries',hint='Updates the sync preference')
  after=copy.deepcopy(before);after.update(selected=value,retained=value,selectedTrait=value,allowed=False if mode.startswith('close-') else input_,events=7+int(accepted),accepted=5+int(accepted),lastValue=not initial if accepted else before['lastValue'],primary=11+(0 if ax and mode=='blocked' else 2 if mode=='reentrant-primary' else 1))
  rows.append(dict(index=i,mode=mode,initial=initial,accessibility=ax,enabled=enabled,input=input_,hookFired=mode not in ['admitted','blocked'],returned=accepted if ax else None,nestedReturn=False if mode=='reentrant-accessibility' else None,before=before,after=after))
 return rows
