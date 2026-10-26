"""Seal independently encoded raw input and expectations before candidate access."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from oracle import (MAX, OBS, WORDS, State, row_record, evaluate, stream_bytes,
 input_bytes, sorted_prefix, pack, EMPTY_RES, EMPTY_PIN)
from terminal_oracle import sample, project, CHILDREN, TAGS, LATCHES

HERE=Path(__file__).resolve().parent
OUT=HERE/'fixtures'
CONFIG={'extent':4096,'types':2,'slots':3,'pins':3,'base':0,'capacity':10,'entry':10}
PROFILE={1:[100,8,0],2:[200,9,0],3:[300,10,1],513:[400,11,0]}
STATES={}; CASES={}

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def put(name,v):
 p=OUT/name; p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')

def state_ref(e):
 state={'logical_scalars':e['state'],'rows':e['rows']}
 key=sha(canonical(state)); STATES[key]=state; return key

def body(kind,f=1,op=1,**kw):
 p=PROFILE[f]
 return row_record(kind,f,op,offset=p[0],length=p[1],type=p[2],**kw)

def numbered(rows):
 result=[]
 for i,r in enumerate(rows,1):
  r=r.copy(); r[0]=i; r[4]=i*3; r[5]=i*2; result.append(r)
 return result

def build(f=1,op=1,nonce=1,slot=0,pin=0,request=6,prior=MAX,outcome=0,victims=()):
 rows=[row_record(1,f,op),body(2,f,op),body(3,f,op,c=f&511),
  body(4,f,op,a=outcome,b=prior,c=f&511),body(5,f,op,a=request,b=0,c=10)]
 for victim,amount in victims:
  rows += [body(k,f,op,slot=victim,a=amount) for k in (6,7,8)]
 rows += [body(9,f,op,a=request),body(10,f,op,a=request),
  body(11,f,op,slot=slot,pin_slot=pin,nonce=nonce,a=1,b=request,c=1)]
 return rows

def release(f=1,slot=0,pin=0,nonce=1,amount=6,post=0):
 return row_record(12,f,0,offset=PROFILE[f][0],type=PROFILE[f][2],slot=slot,
  pin_slot=pin,nonce=nonce,a=amount,c=post)

def hit(f=1,op=2,nonce=2,slot=0,pin=1,amount=6,post=2):
 return [row_record(1,f,op),body(2,f,op,slot=slot,a=1),
  body(11,f,op,slot=slot,pin_slot=pin,nonce=nonce,b=amount,c=post)]

def phase(p=5): return row_record(13,MAX,0,phase=p,a=p)
def failure(op=1,f=MAX): return row_record(14,f,op,a=4,b=3,c=2)

def save_case(name,rows,c=CONFIG,cap=True,override=None):
 records=numbered(rows); e=evaluate(records,c,PROFILE,cap)
 if override:
  e['terminal'],e['words']=override
 stream,limit=stream_bytes(records,c,cap)
 context,profile=input_bytes(c,PROFILE,limit)
 config_id=sha(canonical(c))[:12]
 p=OUT/'profiles'/f'{config_id}.bin'; p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists(): p.write_bytes(profile)
 ctx=OUT/'contexts'/f'{config_id}-{limit}.bin'; ctx.parent.mkdir(parents=True,exist_ok=True); ctx.write_bytes(context)
 dest=OUT/'streams'/f'{name}.bin'; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(stream)
 history=[{'sequence':h['sequence'],'state_ref':state_ref({'state':h['logical_scalars'],'rows':h['rows']})} for h in e['history']]
 item={'id':name,'layer':'public actual-File from empty; execution pending',
  'config':c,'profile':f'profiles/{config_id}.bin','context':f'contexts/{config_id}-{limit}.bin',
  'stream':f'streams/{name}.bin','cap':cap,'raw_records':records,'expected_terminal':e['terminal'],
  'expected_words':e['words'],'expected_internal_state_ref':state_ref(e),'checked_history':history,
  'scope':'expected private rows require separately admitted test-only snapshot instrumentation; public API exposes typed observation only'}
 CASES[name]=item; return records,e

def main():
 OUT.mkdir(exist_ok=True)
 b=build(); r=release(); h=hit()
 mainrows=b+h+[release(post=1),phase()]
 save_case('built-hit-release-closed',mainrows,cap=False)
 save_case('duplicate-release',b+h+[release(post=1),release(post=1)])
 save_case('first-free-reuse',b+[r]+hit(op=2,nonce=2,pin=0,post=1)+[phase()],cap=False)
 evict=b+[r]+build(2,op=2,nonce=2,request=8,victims=[(0,6)])
 save_case('empty-present-last-victim-destination',evict+[phase()],cap=False)
 conflict=b+[r]+build(513,op=2,nonce=2,request=6,prior=1,outcome=1,victims=[(0,6)])
 save_case('plan-collision-replacement',conflict+[phase()],cap=False)
 match=evict+[release(2,nonce=2,amount=8)]+build(1,op=3,nonce=3,request=6,outcome=2,victims=[(0,8)])
 save_case('plan-match-known-bytes',match+[phase()],cap=False)
 save_case('phase-only-closed',[phase()],cap=False)
 save_case('undefined-acquire-cap',[row_record(1,79999,1)])
 save_case('undefined-acquire-failure',[row_record(1,79999,1),failure(1,MAX),phase()],cap=False)
 save_case('first-record-terminal-failure',[failure(0,513),phase()],cap=False)
 save_case('empty-invalid-footer',[],cap=False,override=('T03',[0,3]+[0]*19+[768,1,1]+[0]*8))
 late,_=save_case('late-footer-invalid',mainrows,cap=False,
  override=('T03',[0,3]+[0]*19+[768+7680*len(mainrows),1,1]+[0]*8))
 invalid=OUT/'streams'/'late-footer-invalid.bin'
 raw=bytearray(invalid.read_bytes()); raw[-512+44*8]=1; invalid.write_bytes(raw)
 # All eleven stages are reached through actual profile/record bytes, including
 # stages7/8 through a real prior publication/release/eviction from empty state.
 prefixes={}
 all_paths=[b,b+h,evict,conflict,match]
 for rows in all_paths:
  for n in range(1,len(rows)+1):
   rs=numbered(rows[:n]); e=evaluate(rs,CONFIG,PROFILE)
   if e['terminal']=='T14': prefixes.setdefault(e['state']['stage'],rows[:n])
 if set(prefixes)!=set(range(11)): raise ValueError('stage coverage')
 for stage,rows in sorted(prefixes.items()):
  save_case(f'cap-stage-{stage:02}',rows)
  last_op=max((w[3] for w in rows if w[1]==1),default=0)
  save_case(f'failure-stage-{stage:02}',rows+[failure(last_op if stage else 0,513),phase()],cap=False)
 # Failure latches remain first across legal phase/release tails and CAP.
 save_case('failure-with-live-pin-release-tail',b+hit()[:1]+[failure(2),r,phase()],cap=False)
 save_case('failure-then-forbidden-resume',b+hit()[:1]+[failure(2),body(2,1,2,slot=0,a=1)])
 one={**CONFIG,'slots':1,'pins':1}
 save_case('one-slot-eviction',evict+[phase()],one,cap=False)
 many={**CONFIG,'slots':64,'pins':64}
 sixtyfour=build()
 for i in range(2,65): sixtyfour+=hit(op=i,nonce=i,pin=i-1,post=i)
 save_case('64-live-pins',sixtyfour+[phase()],many,cap=False)
 save_case('full-pin-table-lookup-refused',sixtyfour+[row_record(1,1,65),body(2,1,65,slot=0,a=1)],many)

 # Closed independently encoded mutation map. Each mutant replaces only its
 # final record in a sealed prefix and has a genuine CAP footer at that cut.
 # Materialize its stream with stream_bytes; reuse the listed immutable profile.
 exemplars=[]
 for rows in all_paths:
  for index,w in enumerate(rows):
   form=(w[1],w[13] if w[1] in (2,4,11) else 0)
   if form not in [x[0] for x in exemplars]: exemplars.append((form,rows[:index],w))
 exemplars += [((12,0),b,release()),((13,0),b,phase()),((14,0),[],failure(0)),((14,1),b[:1],failure(1,513))]
 mutants=[]; seen=set()
 values=[0,1,MAX,MAX-1,63,64,65,79999,80000,(1<<32)-1,1<<32]
 for form,prefix,w in exemplars:
  canonical_rows=numbered(prefix+[w]); original=canonical_rows[-1]
  for word in range(16):
   for value in sorted(set(values+[max(0,original[word]-1),min(MAX,original[word]+1)])):
    if value==original[word]: continue
    key=(tuple(tuple(r) for r in canonical_rows[:-1]),tuple(original),word,value)
    if key in seen: continue
    seen.add(key); changed=original.copy(); changed[word]=value
    rows=canonical_rows[:-1]+[changed]; e=evaluate(rows,CONFIG,PROFILE)
    mutants.append({'id':f'W{len(mutants):05}','form':list(form),'word':word,'name':WORDS[word],
     'value':value,'prefix_records':canonical_rows[:-1],'raw_record':changed,
     'expected_terminal':e['terminal'],'expected_words':e['words'],
     'expected_layer':e['layer'],'expected_state_ref':state_ref(e),
     'refusal_policy':'single defect exact named reason; overlaps admit any violated named predicate with absorbing nonmutation'})
 put('word-mutations.json',mutants)

 transitions=[]
 for stage,prefix in sorted(prefixes.items()):
  for form,_,event in exemplars:
   raw=event.copy(); prior_op=max((w[3] for w in prefix if w[1]==1),default=0)
   if raw[1] not in (12,13,14): raw[3]=prior_op+1 if raw[1]==1 else prior_op
   if raw[1]==14: raw[3]=prior_op if stage else 0
   rows=numbered(prefix+[raw]); e=evaluate(rows,CONFIG,PROFILE)
   transitions.append({'id':f'S{stage:02}-K{form[0]:02}-F{form[1]}','stage_before':stage,'form':list(form),
    'prefix_records':rows[:-1],'raw_record':rows[-1],'expected_terminal':e['terminal'],
    'expected_words':e['words'],'expected_state_ref':state_ref(e)})
 put('stage-transitions.json',transitions)

 sequence_variants=[]
 for path_id,rows in enumerate([mainrows,evict,conflict,match]):
  for i in range(len(rows)):
   variants=[('omit',rows[:i]+rows[i+1:]),('duplicate',rows[:i]+[rows[i]]+rows[i:])]
   if i+1<len(rows): variants.append(('swap-next',rows[:i]+[rows[i+1],rows[i]]+rows[i+2:]))
   for action,variant in variants:
    records=numbered(variant); e=evaluate(records,CONFIG,PROFILE)
    sequence_variants.append({'id':f'path{path_id}-{action}-{i:02}','action':action,
     'raw_records':records,'expected_terminal':e['terminal'],'expected_words':e['words'],
     'expected_state_ref':state_ref(e),'note':'coordinates independently renumbered so lifecycle defects are not hidden behind sequence/work drift'})
 put('sequence-variants.json',sequence_variants)

 # Minimal sorted-prefix witnesses plus an exhaustive finite mask domain. These
 # are oracle consistency controls; they do not run or qualify a Rust planner.
 private=[]
 for amount in (6,8):
  res=[EMPTY_RES.copy() for _ in range(64)]
  res[1]=[1,1,3,0,9,1,0,0]; res[2]=[1,2,3,0,1,2,0,0]
  private.append({'id':f'private-empty-last-victim-{amount}','layer':'private seeded state; no public construction claim',
    'resident_rows':res,'config':CONFIG,'request':amount,
    'expected':sorted_prefix(res,3,0,10,amount)})
 for order in ('ties','reverse','increasing','pinned','all-pinned'):
  res=[[1,i,1,int(order=='all-pinned' or (order=='pinned' and i%2==0)),
    7 if order=='ties' else 64-i if order=='reverse' else i,i+1,0,0] for i in range(64)]
  private.append({'id':'private-64-'+order,'layer':'private seeded state; no public construction claim',
   'resident_rows':res,'config':{**many,'capacity':64},'request':32,
   'expected':sorted_prefix(res,64,0,64,32)})
 put('private-victim-witnesses.json',private)

 private_semantic=[]
 for name in ['nonce-max-minus-one','nonce-max','duplicate-resident','duplicate-live-nonce',
   'wrong-token-entry','resident-byte-overflow','resident-generation','resident-reserved']:
  state=State(CONFIG,PROFILE)
  for w in numbered(b): state.advance(w)
  if name=='nonce-max-minus-one': state.nonce=MAX-1
  elif name=='nonce-max': state.nonce=MAX
  elif name=='duplicate-resident': state.res[1]=[1,1,1,0,0,1,0,0]
  elif name=='duplicate-live-nonce':
   state.pins[1]=state.pins[0].copy(); state.res[0][3]=2
  elif name=='wrong-token-entry': state.pins[0][0]=1
  elif name=='resident-byte-overflow': state.res[1]=[1,2,MAX,0,0,1,0,0]
  elif name=='resident-generation': state.res[0][6]=1
  elif name=='resident-reserved': state.res[0][7]=1
  # AcquireBegin has no new resident/token admission. To reach a deliberately
  # corrupted pre-Lookup private fixture, seed its stage1 in the test domain.
  state.stage=1; state.op=state.last_op=2; state.function=1
  before={'state':state.logical_scalars(),'rows':state.rows()}
  event=body(2,1,2,slot=0,a=1); event[0]=state.m+1; event[4]=27; event[5]=18
  after=deepcopy(state); layer=reason=None
  try: after.advance(event)
  except Exception as problem:
   from oracle import Refusal
   if not isinstance(problem,Refusal): raise
   layer,reason=problem.layer,problem.reason; after=state
  raw_events=[event]
  if name=='nonce-max-minus-one':
   publication=body(11,1,2,slot=0,pin_slot=1,nonce=MAX-1,b=6,c=2)
   publication[0]=after.m+1; publication[4]=30; publication[5]=20; after.advance(publication); raw_events.append(publication)
  private_semantic.append({'id':name,'layer':'private corrupted/seeded state only; execution pending',
   'before_state_ref':state_ref(before),'raw_records':raw_events,'expected_refusal_layer':layer,
   'expected_reason':reason,'expected_after_state_ref':state_ref({'state':after.logical_scalars(),'rows':after.rows()}),
   'note':'MAX-1 case includes subsequent exact publication and increments nonce to MAX; never claim this seeded reachability as public File execution'})
 put('private-semantic-witnesses.json',private_semantic)

 terminal=[]
 # One explicit witness per T row, with all32 expected words frozen as data.
 for t in range(16):
  x,q=sample(0,'None','Closed')
  if t==0: x['outer']={'code':16,'stage':8,'offset':0,'record':0,'reserved':0}
  elif t in (1,2,3): x['C']={1:'InputBinding',2:'InputBudget',3:'InputInvalid'}[t]; x['P']='Poison'
  elif t==4: x['C']='EnvelopePoison'
  elif t==5: x['P']='Stale'
  elif t==6: x['C']='EnvelopeUnavailable'
  elif t==7: x['C']='EnvelopeRefused'
  elif t==8: x.update(P='Absent',calls=0); q={}
  elif t==9: q['nonce']=0
  elif t in (10,11,12): x,q=sample(8,{10:'Refusal',11:'Failure',12:'Limit'}[t],'Closed')
  elif t==13: x['C']='Limited'
  elif t==14: x['C']='Cap'
  row,w,error=project(x,q)
  if row!=f'T{t:02}': raise ValueError((t,row))
  terminal.append({'id':row,'input':x,'Q':q,'expected_words':w,'expected_error':error})
 for stage in range(11):
  x,q=sample(stage); row,w,error=project(x,q)
  terminal.append({'id':f'stage-word-{stage:02}','input':x,'Q':q,'expected_row':row,'expected_words':w,'expected_error':error})
 for latch in ['Refusal','Failure','Limit']:
  x,q=sample(0,latch,'Closed'); x.update(N=1,NC=1,calls=1,stop=1)
  q.update(M=0,sequence=0,work=0,instructions=0,residents=0,bytes=0,pins=0,nonce=1)
  row,w,error=project(x,q)
  terminal.append({'id':'first-call-'+latch,'input':x,'Q':q,'expected_row':row,'expected_words':w,'expected_error':error})
 for child in CHILDREN:
  for tag in TAGS:
   for latch in LATCHES:
    for stage in range(11):
     x,q=sample(stage,latch,child); x['P']=tag
     if tag=='Absent' and latch=='None': x['calls']=0
     row,w,error=project(x,q)
     terminal.append({'id':f'{child}/{tag}/{latch}/{stage}','input':x,'Q':q,
      'expected_row':row,'expected_words':w,'expected_error':error})
 put('terminal-full32.json',terminal)
 put('returned-paid-domain-exclusions.json',{'runtime_passes':0,'contract_exclusions_only':[
  {'SS':0,'SF':0},{'SS':0,'SF':1},{'SS':1,'SF':0}],
  'required_actual_proof':'No public or private constructor or return path can create Ok aggregate with either admission unpaid. Outer Err has no aggregate. Prove all constructors, caller moves and error paths after source admission.'})

 # Public syntax/provenance are deliberately separate. Fixture digest echoes
 # never authorize copied/live source identity or a real profile/custody adapter.
 put('cases.json',list(CASES.values()))
 put('states.json',STATES)
 put('schema.json',{'record_words':WORDS,'observation_words':OBS,'profile_rows':PROFILE,
  'config':CONFIG,'expected_state_encoding':'Defaults cover every row; sparse overrides are complete row replacements. Logical scalars are complete observable contract state, not invented values for unspecified inactive private cells.',
  'private_snapshot_gate':'Future test-only private snapshot instrument must be admitted and source-bound separately from public actual-File execution.',
  'mutant_stream_recipe':'prefix_records + raw_record, stream_bytes(...,cap=True); matching context cap=max(record_count,1); profile for CONFIG. All raw words are sealed here.',
  'all_new_Rust_product_tests':0})
 print(json.dumps({'public_cases':len(CASES),'word_mutations':len(mutants),'stage_transitions':len(transitions),
  'terminal_cases':len(terminal),'deduplicated_full_states':len(STATES),'private_victim_cases':len(private),
  'new_Rust_product_tests':0}))

if __name__=='__main__': main()
