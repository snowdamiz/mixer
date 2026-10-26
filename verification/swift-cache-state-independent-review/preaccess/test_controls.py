"""Only reviewer encoder/oracle consistency controls; zero new Rust tests."""
import hashlib
import itertools
import json
from pathlib import Path
import unittest
from oracle import (MAX,OBS,WORDS,EMPTY_RES,unpack,pack,sorted_prefix,zero_projection,
 evaluate,stream_bytes,input_bytes)
from terminal_oracle import project,sample

HERE=Path(__file__).resolve().parent
F=HERE/'fixtures'
def data(name): return json.loads((F/name).read_text())

class ReadTrap(dict):
 def __getitem__(self,key): raise AssertionError('unexpected Q read '+key)

class Controls(unittest.TestCase):
 checks=0
 def check(self,condition):
  self.__class__.checks+=1
  if not condition: self.fail('consistency check failed')

 def test_01_wire_and_profile_exact_independent_lengths(self):
  cases=data('cases.json'); schema=data('schema.json'); states=data('states.json')
  self.check(len(WORDS)==16 and len(OBS)==32)
  for c in cases:
   raw=(F/c['stream']).read_bytes(); header=unpack(raw[:512]); footer=unpack(raw[-512:])
   self.check(len(raw)==1024+128*len(c['raw_records']))
   self.check(raw[512:-512]==b''.join(pack(w) for w in c['raw_records']))
   self.check(header[:5]==[0x315244524F58494D,1,512,128,512])
   context=unpack((F/c['context']).read_bytes()); profile=(F/c['profile']).read_bytes()
   self.check(len(context)==1024 and len(profile)==2560512)
   self.check(context[4]==header[5] and header[16:24]==context[16:24])
   self.check(unpack(profile[:512])[28:32]==header[20:24])
   self.check(footer[36:44]==header[16:24])
   for f,p in schema['profile_rows'].items():
    off=512+int(f)*32; self.check(unpack(profile[off:off+32])==[1+(p[2]<<32),p[0],p[1],0])
   self.check(c['expected_internal_state_ref'] in states)
   self.check(len(c['expected_words'])==32 and c['expected_words'][26:]==[0]*6)

 def test_02_anchor_built_hit_release(self):
  c=next(x for x in data('cases.json') if x['id']=='built-hit-release-closed')
  self.check(c['expected_words']==[1,0,13,13,0,13,39,26,0,MAX,1,6,1,3,MAX,0,0,0,MAX,MAX,0,100608,1,1,1,0,0,0,0,0,0,0])
  s=data('states.json')[c['expected_internal_state_ref']]
  self.check(s['rows']['resident']['rows']=={'0':[1,1,6,1,33,1,0,0]})
  self.check(s['rows']['pin']['rows']=={'1':[0,2,2,2,33,22]})
  self.check(s['rows']['plan']['rows']=={'1':[1,100,8,0,6]})

 def test_03_sorted_prefix_anchored_destination_and_ties(self):
  witnesses=data('private-victim-witnesses.json')
  self.check(witnesses[0]['expected']['selection_order']==[2])
  self.check(witnesses[0]['expected']['destination']==2)
  self.check(witnesses[1]['expected']['selection_order']==[2,1])
  self.check(witnesses[1]['expected']['emission_order']==[1,2])
  self.check(witnesses[1]['expected']['destination']==1)
  ties=next(x for x in witnesses if x['id']=='private-64-ties')
  self.check(ties['expected']['selection_order']==list(range(32)))
  self.check(ties['expected']['destination']==31)
  pinned=next(x for x in witnesses if x['id']=='private-64-all-pinned')
  self.check(not pinned['expected']['feasible'] and pinned['expected']['destination']==MAX)

 def test_04_sorted_prefix_finite_masks(self):
  # 3**4 occupancy/pin states, four timestamp patterns and requests1..5.
  for flags in itertools.product(range(3),repeat=4):
   for times in ([0,0,0,0],[4,3,2,1],[1,3,2,4],[MAX,0,MAX,0]):
    res=[EMPTY_RES.copy() for _ in range(64)]
    for i,flag in enumerate(flags):
     if flag: res[i]=[1,i,1,int(flag==2),times[i],i+1,0,0]
    for request in range(1,6):
     p=sorted_prefix(res,4,0,4,request)
     eligible=sorted((times[i],i) for i,v in enumerate(flags) if v==1)
     self.check(p['selection_order']==[i for _,i in eligible[:len(p['selection_order'])]])
     self.check(p['emission_order']==sorted(p['selection_order']))
     self.check(not any(flags[i]==2 for i in p['selection_order']))
     if p['feasible']:
      self.check(p['remaining_bytes']+request<=4)
      self.check(p['destination']==(p['selection_order'][-1] if p['selection_order'] else flags.index(0)))

 def test_05_failure_no_rollback_and_no_publication(self):
  cases={x['id']:x for x in data('cases.json')}; states=data('states.json')
  for stage in range(11):
   cap=cases[f'cap-stage-{stage:02}']; fail=cases[f'failure-stage-{stage:02}']
   self.check(fail['expected_terminal']=='T11')
   self.check(fail['expected_internal_state_ref']==cap['expected_internal_state_ref'])
   self.check(fail['expected_words'][3]==cap['expected_words'][3])
   self.check(fail['expected_words'][20]==cap['expected_words'][3]+1)
  before=states[cases['failure-stage-07']['expected_internal_state_ref']]
  after=states[cases['failure-stage-08']['expected_internal_state_ref']]
  self.check('0' in before['rows']['resident']['rows'])
  self.check('0' not in after['rows']['resident']['rows'])
  self.check(cases['failure-then-forbidden-resume']['expected_terminal']=='T07')

 def test_06_complete_word_and_stage_coverage(self):
  rows=data('word-mutations.json')
  forms={tuple(r['form']) for r in rows}
  self.check({f[0] for f in forms}==set(range(1,15)))
  for form in forms:
   self.check({r['word'] for r in rows if tuple(r['form'])==form}==set(range(16)))
  for row in rows:
   self.check(len(row['raw_record'])==16 and len(row['expected_words'])==32)
   self.check(row['expected_words'][26:]==[0]*6)
  self.check({x['stage_before'] for x in data('stage-transitions.json')}==set(range(11)))

 def test_07_terminal_literal_suppression_and_all_rows(self):
  cases=data('terminal-full32.json'); found=set()
  for c in cases:
   row,words,error=project(c['input'],c['Q']); found.add(row)
   self.check(words==c['expected_words'] and error==c['expected_error'])
   if words is not None:
    self.check(words[26:]==[0]*6 and words[1] not in (15,17))
    self.check(words[21]==768+7680*c['input']['NC'])
  self.check(found=={f'T{i:02}' for i in range(16)})
  for child,boundary,reason in [('InputBinding',0,2),('InputBudget',4,1),('InputInvalid',0,3)]:
   x,_=sample(); x['C']=child; x['P']='Poison'
   row,words,error=project(x,ReadTrap())
   self.check(words==[boundary,reason]+[0]*19+[31488,1,1]+[0]*8)

 def test_08_inactive_and_suppressed_read_traps(self):
  for child in ['InputBinding','InputBudget','InputInvalid','EnvelopePoison','EnvelopeUnavailable','EnvelopeRefused','Unsupported']:
   x,_=sample(); x['C']=child; self.check(project(x,ReadTrap())[0]!='T09')
  x,q=sample(0,'None','Closed')
  for key in ['op','function','selected','taken','committed','pending','destination','feasible']: del q[key]
  self.check(project(x,q)[0]=='T15')
  x,q=sample(6); q['feasible']=False
  del q['destination']; del q['pending']
  self.check(project(x,q)[1][19]==MAX)

 def test_09_paid_charge_no_refund_and_outer_error(self):
  self.check(8192-8151==41 and 471+7680==8151)
  self.check(sum([256,2560,2568,768,640,640,248])==7680)
  self.check(512+256+7680==8448)
  x,q=sample(); x.update(C='InputInvalid',N=0,NC=1,calls=0,P='Absent')
  self.check(project(x,ReadTrap())[1]==[0,3]+[0]*19+[8448,1,1]+[0]*8)
  error={'code':6,'stage':8,'offset':17,'record':0,'reserved':0}
  x['outer']=error; self.check(project(x,ReadTrap())==('T00',None,error))
  x.pop('outer')
  for paid in [(0,0),(0,1),(1,0)]:
   x['SS'],x['SF']=paid
   with self.assertRaises(ValueError): project(x,ReadTrap())
   # Model rejection is only a consistency check. It is explicitly not proof
   # that an eventual Rust receipt cannot be constructed in this state.

 def test_10_guard_mutations(self):
  edits=[('M',6),('sequence',3),('stage',11),('nonce',0),('residents',4),('bytes',0),
   ('pins',4),('op',0),('function',80000),('selected',8),('taken',4),('committed',4),('pending',3),('destination',3)]
  for key,value in edits:
   x,q=sample(8); q[key]=value
   self.check(project(x,q)[0]=='T09')
  x,q=sample(); x.update(P='Absent',calls=1); self.check(project(x,ReadTrap())[0]=='T05')

 def test_11_defaults_cover_all_rows_and_source_independence(self):
  states=data('states.json')
  for key,state in states.items():
   canonical=json.dumps(state,sort_keys=True,separators=(',',':')).encode()
   self.check(hashlib.sha256(canonical).hexdigest()==key)
   for region,count,width in [('function',80000,12),('resident',64,8),('pin',64,6),('plan',512,5)]:
    r=state['rows'][region]
    self.check(r['count']==count and len(r['default'])==width)
    self.check(all(0<=int(i)<count and len(row)==width for i,row in r['rows'].items()))

 def test_12_public_file_matrix_recompute_is_consistency_only(self):
  schema=data('schema.json'); profile={int(f):p for f,p in schema['profile_rows'].items()}
  for c in data('cases.json'):
   if c['id'] in ['late-footer-invalid','empty-invalid-footer']: continue
   result=evaluate(c['raw_records'],c['config'],profile,c['cap'])
   self.check(result['words']==c['expected_words'])
   self.check(result['terminal']==c['expected_terminal'])

 def test_13_sequence_and_private_fixture_anchors(self):
  variants=data('sequence-variants.json')
  self.check({x['action'] for x in variants}=={'omit','duplicate','swap-next'})
  for x in variants:
   self.check(len(x['expected_words'])==32 and x['expected_words'][26:]==[0]*6)
  states=data('states.json'); private={x['id']:x for x in data('private-semantic-witnesses.json')}
  self.check(private['nonce-max']['expected_reason']==12)
  endpoint=states[private['nonce-max-minus-one']['expected_after_state_ref']]
  self.check(endpoint['logical_scalars']['nonce']==MAX)
  self.check(endpoint['rows']['pin']['rows']['1'][1]==MAX-1)
  for name,x in private.items():
   if name=='nonce-max-minus-one': continue
   self.check(x['before_state_ref']==x['expected_after_state_ref'])
   self.check(x['expected_reason']==(12 if name=='nonce-max' else 13))

 def test_14_exact_source_data_and_closed_upstream_custody(self):
  root=HERE.parents[2]
  custody=json.loads((HERE/'input-custody.json').read_text())
  self.check(custody['unique_members']==651 and custody['unique_bytes']==4801337)
  for item in custody['verified_members']:
   b=(root/item['path']).read_bytes()
   self.check(len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'])
  for item in custody['selected_snapshots']:
   b=(HERE/item['snapshot']).read_bytes()
   self.check(len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'])
  base=HERE/'inputs'/'verification/swift-semantic-adapter-prerequisite'
  seams=json.loads((base/'source-seams.json').read_text())['seams']
  self.check(len(seams)==14)
  for seam in seams:
   b=(base/seam['snapshot']).read_bytes()
   self.check(hashlib.sha256(b).hexdigest()==seam['source_sha256'])
   excerpt=b''.join(b.splitlines(keepends=True)[seam['first_line']-1:seam['last_line']])
   self.check(excerpt.decode()==seam['excerpt_utf8'])
   self.check(hashlib.sha256(excerpt).hexdigest()==seam['excerpt_sha256'])

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 print(json.dumps({'methods':result.testsRun,'checks':Controls.checks,'failures':len(result.failures),
  'errors':len(result.errors),'Rust_product_tests':0,'scope':'reviewer encoder/oracle consistency only'}))
 raise SystemExit(not result.wasSuccessful())
