"""Independent finite fixture oracle; no candidate or historical model imports.

This is test-support logic, never executed Rust or release authority. Victims
are a sorted eligible prefix, with no merge sort or producer selection loop.
"""
from copy import deepcopy
import struct

MAX = (1 << 64) - 1
WORDS = ['sequence','kind','phase','operation','work','instructions','function',
 'offset','length','type','slot','pin_slot','nonce','a','b','c']
OBS = ['boundary','reason','observed_records','cache_state_records','stop_record',
 'last_sequence','last_work','last_instructions','active_operation','requested_function',
 'resident_count','resident_bytes','held_pins','next_nonce','active_plan_cell',
 'selected_mask','taken_mask','committed_mask','pending_victim','destination',
 'failure_coordinate','semantic_debit','semantic_setup_paid','semantic_finish_paid',
 'fixture_state_observed','tail_unknown','stored_prefix_validated','full_replay_accepted',
 'semantic_metrics_valid','real_binding_verified','reserved0','reserved1']
EMPTY_RES = [0,MAX,0,0,0,0,0,0]
EMPTY_PIN = [MAX,0,0,0,0,0]
EMPTY_PLAN = [MAX,0,0,0,0]
DEFAULT_FUNCTION = [MAX,0,(1<<32)-1,0,0,(1<<32)-1,0,0,0,0,0,0]

def pack(w): return struct.pack('<'+'Q'*len(w),*w)
def unpack(b): return list(struct.unpack('<'+'Q'*(len(b)//8),b))
def row_record(kind, f=1, op=1, phase=0, **payload):
 w=[0,kind,phase,op,0,0,f,MAX,MAX,MAX,MAX,MAX,0,0,0,0]
 for key,value in payload.items(): w[WORDS.index(key)]=value
 return w

def sorted_prefix(residents, slots, base, capacity, request):
 """A declarative sorted-prefix oracle, deliberately unlike repeated source scans."""
 live=[(i,r) for i,r in enumerate(residents[:slots]) if r[0]]
 total=sum(r[2] for _,r in live)
 if total>MAX or base+total>MAX: return {'overflow':True,'feasible':False}
 empty=next((i for i in range(slots) if not residents[i][0]),MAX)
 ordered=sorted((r[4],i,r[2]) for i,r in live if r[3]==0)
 # Enumerate all prefixes, select the first feasible one. No producer merge code.
 sums=[sum(v[2] for v in ordered[:n]) for n in range(len(ordered)+1)]
 choices=[n for n,removed in enumerate(sums)
   if (empty!=MAX or n>0) and base+total-removed+request<=capacity]
 n=choices[0] if choices else len(ordered)
 selected=[v[1] for v in ordered[:n]]
 feasible=bool(choices)
 return {'overflow':False,'feasible':feasible,'selection_order':selected,
  'emission_order':sorted(selected),'selected_mask':sum(1<<i for i in selected),
  'destination':(selected[-1] if selected else empty) if feasible else MAX,
  'initial_bytes':total,'remaining_bytes':total-sums[n],'first_empty':empty}

def field_valid(w,c,profile):
 if len(w)!=16 or any(type(x)!=int or not 0<=x<=MAX for x in w): return False
 seq,k,phase,op,work,ins,f,off,length,ty,slot,pin,nonce,a,b,d=w
 if seq==0 or not 1<=k<=14 or phase>5: return False
 body=(f in profile and profile[f]==[off,length,ty] and ty<c['types'] and off+length<=c['extent'])
 release=(f in profile and profile[f][0]==off and profile[f][2]==ty and length==MAX)
 absent=(off==length==ty==MAX); no_slots=(slot==pin==MAX and nonce==0)
 if k==1: return op>0 and f<80000 and absent and no_slots and [a,b,d]==[0,0,0]
 if k==12: return op==0 and release and slot<c['slots'] and pin<c['pins'] and nonce>0 and a>0 and b==0 and d<c['pins']
 if k==13: return op==0 and f==MAX and absent and no_slots and [a,b,d]==[phase,0,0]
 if k==14: return absent and (f==MAX or f<80000) and no_slots and 1<=a<=21 and 1<=b<=24 and 1<=d<=6
 if not op>0 or not body: return False
 if k==2: return pin==MAX and nonce==0 and b==d==0 and ((a==0 and slot==MAX) or (a==1 and slot<c['slots']))
 if k==3: return no_slots and a==b==0 and d==f&511
 if k==4: return no_slots and a<=2 and ((a==1 and b<80000 and b!=f) or (a!=1 and b==MAX)) and d==f&511
 if k==5: return no_slots and 0<a<=c['entry'] and b==c['base'] and d==c['capacity'] and b+a<=d and b+a<=MAX
 if k in (6,7,8): return slot<c['slots'] and pin==MAX and nonce==0 and a>0 and b==d==0
 if k in (9,10): return no_slots and 0<a<=c['entry'] and b==d==0
 if k==11: return slot<c['slots'] and pin<c['pins'] and nonce>0 and a<=1 and b>0 and 1<=d<=c['pins']
 return False

class Refusal(Exception):
 def __init__(self, layer, reason): self.layer,self.reason=layer,reason

class State:
 def __init__(self,c,profile):
  self.c,self.profile=c,profile
  self.res=[EMPTY_RES.copy() for _ in range(64)]
  self.pins=[EMPTY_PIN.copy() for _ in range(64)]
  self.plans=[EMPTY_PLAN.copy() for _ in range(512)]
  self.nonce=1; self.stage=0; self.op=0; self.function=MAX
  self.phase=0; self.mask=1; self.last_op=0; self.m=0; self.work=0; self.ins=0
  self.first_pin=MAX; self.lookup_slot=MAX; self.request=0
  self.selected=self.taken=self.committed=0; self.pending=MAX
  self.destination=MAX; self.feasible=False; self.selection=[]; self.emission=[]
  self.scan=False; self.build=False; self.ready=False

 def rows(self):
  # The defaults apply to every unlisted row, including unused native slots.
  defined={str(f):[p[0],p[1],p[2]+(1<<32),0,0,(1<<32)-1,0,0,0,0,0,0]
    for f,p in self.profile.items()}
  return {'function':{'count':80000,'stride':96,'default':DEFAULT_FUNCTION,'rows':defined},
   'resident':{'count':64,'stride':64,'default':EMPTY_RES,'rows':{str(i):r for i,r in enumerate(self.res) if r!=EMPTY_RES}},
   'pin':{'count':64,'stride':48,'default':EMPTY_PIN,'rows':{str(i):r for i,r in enumerate(self.pins) if r!=EMPTY_PIN}},
   'plan':{'count':512,'stride':40,'default':EMPTY_PLAN,'rows':{str(i):r for i,r in enumerate(self.plans) if r!=EMPTY_PLAN}}}

 def snapshot(self):
  return {'M':self.m,'sequence':self.m,'work':self.work,'instructions':self.ins,
   'stage':self.stage,'op':self.op,'function':self.function,
   'residents':sum(r[0] for r in self.res),'bytes':sum(r[2] for r in self.res),
   'pins':sum(p[1]!=0 for p in self.pins),'nonce':self.nonce,
   'selected':self.selected,'taken':self.taken,'committed':self.committed,
   'pending':self.pending,'destination':self.destination,'feasible':self.feasible}

 def logical_scalars(self):
  return {**self.snapshot(),'phase':self.phase,'mask':self.mask,'last_operation':self.last_op,
   'first_free_pin':self.first_pin,'lookup_slot':self.lookup_slot,'requested_bytes':self.request,
   'scan_open':self.scan,'build_open':self.build,'build_ready':self.ready,
   'selection_order':self.selection,'emission_order':self.emission,
   'inactive_storage':'private stale words unspecified by contract; projection must not read them'}

 def check(self):
  live=[r for r in self.res if r[0]]
  if len({r[1] for r in live})!=len(live): raise Refusal('semantic',13)
  nonces=[p[1] for p in self.pins if p[1]]
  if len(nonces)!=len(set(nonces)): raise Refusal('semantic',13)
  if any(r[1] not in self.profile or r[2]==0 or r[6:]!=[0,0] for r in live): raise Refusal('semantic',13)
  for i,r in enumerate(self.res):
   count=sum(p[1]!=0 and p[0]==i for p in self.pins)
   if count!=r[3] or (not r[0] and r!=EMPTY_RES): raise Refusal('semantic',13)
  if sum(r[2] for r in live)>MAX: raise Refusal('semantic',13)

 def advance(self,w):
  # Called only for a syntactically/profile checked record. Stage is a compact
  # independent relation table, not imported envelope or producer code.
  k,op,f=w[1],w[3],w[6]
  if w[2] != self.phase and k!=13: raise Refusal('envelope',5)
  if self.phase==5: raise Refusal('envelope',4)
  after=self.stage
  if k==13:
   if self.stage!=0 or w[2]<=self.phase or self.mask&(1<<w[2]): raise Refusal('envelope',5)
  elif k==12:
   if self.stage: raise Refusal('envelope',6)
  elif k==14:
   if (op==0 and self.stage!=0) or (op and (not self.stage or op!=self.op)): raise Refusal('envelope',8)
   raise Refusal('failure',14)
  elif k==1:
   if self.stage or self.phase>=4 or op!=self.last_op+1: raise Refusal('envelope',10)
   after=1
  else:
   if op!=self.op or f!=self.function: raise Refusal('envelope',11)
   transitions={2:(1,2 if w[13] else 3),3:(3,4),4:(4,5),5:(5,6),6:(6,7),7:(7,8),8:(8,6),9:(6,9),10:(9,10)}
   if k==11:
    if not ((self.stage==2 and w[13]==0) or (self.stage==10 and w[13]==1)): raise Refusal('envelope',13)
    after=0
   elif k not in transitions or self.stage!=transitions[k][0]: raise Refusal('envelope',12)
   else: after=transitions[k][1]
  # Stage gates above have no mutation. The caller evaluates a deep copy, so
  # every semantic refusal retains exact original scalar/row bytes.
  self.check()
  if k==1:
   self.op=self.last_op=op; self.function=f
   self.first_pin=self.lookup_slot=MAX; self.request=0
   self.selected=self.taken=self.committed=0; self.pending=MAX
   self.destination=MAX; self.feasible=False; self.selection=[]; self.emission=[]
   self.scan=self.build=self.ready=False
  elif k==2:
   if f not in self.profile: raise Refusal('semantic',6)
   if self.nonce==MAX: raise Refusal('semantic',12)
   free=[i for i,p in enumerate(self.pins[:self.c['pins']]) if p[1]==0]
   if not free: raise Refusal('semantic',11)
   matches=[i for i,r in enumerate(self.res[:self.c['slots']]) if r[0] and r[1]==f]
   if (w[13]==0 and matches) or (w[13]==1 and matches!=[w[10]]): raise Refusal('semantic',7)
   self.first_pin=free[0]; self.lookup_slot=w[10]
  elif k==3: self.scan=True
  elif k==4:
   p=self.plans[f&511]; identity=[f,*self.profile[f]]
   expected=0 if p[0]==MAX else 2 if p[:4]==identity else 1
   if p[0]==f and p[:4]!=identity: raise Refusal('semantic',8)
   if w[13]!=expected or w[14]!=(p[0] if expected==1 else MAX): raise Refusal('semantic',8)
   if expected!=2: self.plans[f&511]=identity+[0]
   self.scan=False
  elif k==5:
   p=self.plans[f&511]
   if p[:4]!=[f,*self.profile[f]]: raise Refusal('semantic',8)
   if p[4] and p[4]!=w[13]: raise Refusal('semantic',10)
   plan=sorted_prefix(self.res,self.c['slots'],self.c['base'],self.c['capacity'],w[13])
   if plan['overflow']: raise Refusal('semantic',13)
   p[4]=w[13]; self.request=w[13]; self.selected=plan['selected_mask']
   self.feasible=plan['feasible']; self.destination=plan['destination']
   self.selection=plan['selection_order']; self.emission=plan['emission_order']
  elif k in (6,7,8):
   slot=w[10]; bit=1<<slot
   if not self.feasible: raise Refusal('semantic',9)
   next_emit=next((i for i in self.emission if not self.committed&(1<<i)),MAX)
   if slot!=next_emit or not self.selected&bit: raise Refusal('semantic',9)
   if k==6:
    r=self.res[slot]
    if not r[0] or r[3]!=0 or r[2]!=w[13]: raise Refusal('semantic',9)
    self.pending=slot
   elif k==7:
    if self.pending!=slot or self.taken&bit: raise Refusal('semantic',9)
    r=self.res[slot]
    if not r[0] or r[3]!=0 or r[2]!=w[13]: raise Refusal('semantic',9)
    self.res[slot]=EMPTY_RES.copy(); self.taken|=bit
   else:
    if self.pending!=slot or not self.taken&bit or self.res[slot][0]: raise Refusal('semantic',9)
    # The victim bytes survive in the pre-Take logical obligation; recover from
    # caller history rather than infer a refund from an unseen ledger.
    if getattr(self,'pending_bytes',None)!=w[13]: raise Refusal('semantic',9)
    self.committed|=bit; self.pending=MAX
   if k==6: self.pending_bytes=w[13]
  elif k in (9,10):
   if w[13]!=self.request: raise Refusal('semantic',10)
   if not self.feasible or self.selected!=self.committed: raise Refusal('semantic',9)
   if k==9: self.build=True
   else: self.build=False; self.ready=True
  elif k==11:
   slot=w[10]; r=self.res[slot]
   if w[11]!=self.first_pin or self.pins[w[11]][1]!=0: raise Refusal('semantic',11)
   if w[12]!=self.nonce: raise Refusal('semantic',12)
   if w[13]==1:
    if slot!=self.destination or r[0] or not self.ready: raise Refusal('semantic',7)
    if w[14]!=self.request: raise Refusal('semantic',10)
    if w[15]!=1: raise Refusal('semantic',11)
    self.res[slot]=[1,f,self.request,0,0,self.op,0,0]; r=self.res[slot]
   elif slot!=self.lookup_slot or not r[0] or r[1]!=f: raise Refusal('semantic',7)
   if w[14]!=r[2] or w[15]!=r[3]+1: raise Refusal('semantic',11)
   r[3]+=1; r[4]=w[4]
   self.pins[w[11]]=[slot,self.nonce,self.op,self.op,w[4],w[5]]
   self.nonce+=1
  elif k==12:
   p=self.pins[w[11]]; r=self.res[w[10]]
   if p[1]!=w[12] or p[0]!=w[10] or not p[1] or not r[0] or r[1]!=f or r[3]==0: raise Refusal('semantic',11)
   if w[13]!=r[2] or w[15]!=r[3]-1: raise Refusal('semantic',11)
   r[3]-=1; self.pins[w[11]]=EMPTY_PIN.copy()
  elif k==13: self.phase=w[2]; self.mask|=1<<w[2]
  self.stage=after; self.m+=1; self.work=w[4]; self.ins=w[5]
  self.check()

def zero_projection(boundary,reason,nc,ss=1,sf=1):
 w=[0]*32; w[0:2]=[boundary,reason]; w[21:24]=[512*ss+256*sf+7680*nc,ss,sf]
 return w

def visible_projection(q,n,nc,boundary,reason,stop=0,failure=0,tail=0):
 stage=q['stage']; active=stage!=0; planned=6<=stage<=10
 return [boundary,reason,n,q['M'],stop,q['M'],q['work'],q['instructions'],
  q['op'] if active else 0,q['function'] if active else MAX,
  q['residents'],q['bytes'],q['pins'],q['nonce'],q['function']&511 if 3<=stage<=10 else MAX,
  q['selected'] if planned else 0,q['taken'] if planned else 0,q['committed'] if planned else 0,
  q['pending'] if stage in (7,8) else MAX,q['destination'] if planned and q['feasible'] else MAX,
  failure,512+256+7680*nc,1,1,1,tail,0,0,0,0,0,0]

class Envelope:
 """Own small closed relation, independent of the semantic snapshot."""
 def __init__(self):
  self.stage=0; self.phase=0; self.mask=1; self.op=0; self.function=MAX
  self.pin_failed=False; self.terminal_failed=False
 def step(self,w):
  k,op,f=w[1],w[3],w[6]
  if self.phase==5: raise Refusal('envelope',4)
  if k==13:
   if self.stage or w[2]<=self.phase or self.mask&(1<<w[2]): raise Refusal('envelope',5)
   self.phase=w[2]; self.mask|=1<<w[2]; return
  if w[2]!=self.phase: raise Refusal('envelope',5)
  if k==12:
   if self.stage: raise Refusal('envelope',6)
   return
  if k==14:
   if op==0:
    if self.stage or self.terminal_failed: raise Refusal('envelope',7)
    self.terminal_failed=True
   else:
    if not self.stage or self.pin_failed or self.terminal_failed or op!=self.op: raise Refusal('envelope',8)
    self.stage=0; self.pin_failed=True
   return
  if self.pin_failed or self.terminal_failed: raise Refusal('envelope',9)
  if k==1:
   if self.stage or self.phase>=4 or op!=self.op+1: raise Refusal('envelope',10)
   self.stage=1; self.op=op; self.function=f; return
  if op!=self.op or f!=self.function: raise Refusal('envelope',11)
  if k==11:
   if (self.stage,w[13]) not in ((2,0),(10,1)): raise Refusal('envelope',13)
   self.stage=0; return
  relation={2:(1,2 if w[13] else 3),3:(3,4),4:(4,5),5:(5,6),6:(6,7),7:(7,8),8:(8,6),9:(6,9),10:(9,10)}
  if k not in relation or self.stage!=relation[k][0]: raise Refusal('envelope',12)
  self.stage=relation[k][1]

def evaluate(records,c,profile,cap=True):
 s=State(c,profile); latch=None; layer=None; refusal=None; history=[]
 envelope=Envelope(); envelope_error=None
 last_work=last_ins=last_op=phase=0; mask=1; framed=0
 for w in records:
  if not field_valid(w,c,profile):
   return {'terminal':'T03','layer':'framing-fields','words':zero_projection(0,3,framed+1),
    'state':s.logical_scalars(),'rows':s.rows(),'history':history,'failed_record':framed+1}
  coordinate=(w[0]==framed+1 and w[4]>=last_work and w[5]>=last_ins)
  if w[1]==13:
   coordinate &= w[2]>phase and not mask&(1<<w[2]); phase=w[2]; mask|=1<<w[2]
  else: coordinate &= w[2]==phase
  if w[1]==1:
   coordinate &= w[3]==last_op+1; last_op=w[3]
  elif w[1] not in (12,13,14): coordinate &= w[3]==last_op
  elif w[1]==14: coordinate &= w[3] in (0,last_op)
  if not coordinate:
   return {'terminal':'T03','layer':'framing-coordinate','words':zero_projection(0,3,framed+1),
    'state':s.logical_scalars(),'rows':s.rows(),'history':history,'failed_record':framed+1}
  framed+=1; last_work,last_ins=w[4:6]
  if not envelope_error:
   try: envelope.step(w)
   except Refusal as problem: envelope_error=problem.reason
  if envelope_error: continue
  if latch: continue
  candidate=deepcopy(s)
  try: candidate.advance(w)
  except Refusal as e:
   layer,refusal=e.layer,e.reason
   if layer=='envelope': raise ValueError('independent envelope/state relation disagreement')
   latch='Failure' if layer=='failure' else 'Refusal'
  else:
   s=candidate
   history.append({'sequence':w[0],'logical_scalars':s.logical_scalars(),'rows':s.rows()})
 if envelope_error:
  terminal='T07'; layer='envelope'; words=zero_projection(3,4,len(records))
 elif latch:
  terminal='T11' if latch=='Failure' else 'T10'; b=6 if latch=='Failure' else 3
  words=visible_projection(s.snapshot(),framed,len(records),b,refusal,s.m+1,s.m+1 if b==6 else 0,1)
 else:
  terminal='T14' if cap and s.m else ('T15' if s.m and envelope.stage==0 and envelope.phase==5 else 'T08')
  words=visible_projection(s.snapshot(),framed,len(records),2 if cap else 1,0,tail=int(cap)) if s.m else zero_projection(0,5,len(records))
 return {'terminal':terminal,'layer':layer,'words':words,'state':s.logical_scalars(),'rows':s.rows(),'history':history}

def stream_bytes(records,c,cap):
 n=len(records); limit=max(n,1) if cap else max(n+1,1)
 h=[0]*64; h[:10]=[0x315244524F58494D,1,512,128,512,limit,80000,64,512,33]
 h[16:32]=list(range(101,117))
 foot=[0]*64; foot[:10]=[0x31444E454F58494D,1,n,n+int(cap),int(cap),n,
   records[-1][4] if n else 0,records[-1][5] if n else 0,
   max((w[3] for w in records if w[1]==1),default=0),int(cap)]
 foot[10:12]=foot[6:8]; foot[14]=MAX; foot[15]=33; foot[33]=5
 foot[35]=limit; foot[36:44]=h[16:24]
 return pack(h)+b''.join(pack(w) for w in records)+pack(foot),limit

def input_bytes(c,profile,cap):
 context=[0]*1024; context[:16]=[int.from_bytes(b'MIXFIX01','little'),1,8192,1,cap,33,
  c['extent'],c['types'],c['slots'],c['pins'],1,c['base'],c['capacity'],c['entry'],0,0]
 context[16:24]=list(range(101,109)); context[40:48]=list(range(109,117))
 header=[0]*64; header[:16]=[int.from_bytes(b'MIXPRF01','little'),1,512,32,80000,
  c['extent'],c['types'],c['slots'],c['pins'],1,c['base'],c['capacity'],c['entry'],0,0,0]
 header[16:24]=context[40:48]; header[28:32]=context[20:24]
 rows=[]
 for f in range(80000):
  if f in profile:
   offset,length,ty=profile[f]; rows.extend([1+(ty<<32),offset,length,0])
  else: rows.extend([((1<<32)-1)<<32,MAX,0,0])
 return pack(context),pack(header)+pack(rows)
