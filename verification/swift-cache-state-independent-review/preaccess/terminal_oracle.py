"""Reviewer-owned total T00--T15 contract consistency support, not Rust evidence."""
from oracle import MAX, zero_projection, visible_projection

CHILDREN=['InputBinding','InputBudget','InputInvalid','EnvelopePoison',
 'EnvelopeUnavailable','EnvelopeRefused','Limited','Cap','Closed','Unsupported']
TAGS=['Absent','Valid','Poison','Unreadable','Stale','Malformed']
LATCHES=['None','Refusal','Failure','Limit']

def guards(x,q):
 # Reads are deliberately conditional: suppressed snapshots need no Q access,
 # and inactive private storage need not be initialized or readable.
 n,nc,calls=x['N'],x['NC'],x['calls']
 m,seq,work,ins,stage=(q[k] for k in ['M','sequence','work','instructions','stage'])
 nums=[n,nc,calls,m,seq,work,ins,stage,q['residents'],q['bytes'],q['pins'],q['nonce']]
 if any(type(v)!=int or not 0<=v<=MAX for v in nums): return False
 if not 0<=m<=n<=4194304 or n>nc or calls>nc or seq!=m or stage>10: return False
 if not 1<=x['slots']<=64 or not 1<=x['pin_slots']<=64: return False
 if q['residents']>x['slots'] or q['pins']>x['pin_slots'] or q['nonce']==0: return False
 if (q['residents']==0)!=(q['bytes']==0) or (q['pins'] and not q['residents']): return False
 latch=x['L']
 if latch=='None':
  if x['reason']!=0 or x['stop']!=0 or m!=n or calls!=m or not m or (x['C']=='Closed' and stage!=0): return False
 else:
  reasons={'Refusal':range(6,14),'Failure':[14],'Limit':[1]}
  if x['reason'] not in reasons[latch] or x['stop']!=m+1 or m+1>n or calls!=m+1: return False
 if m==0 and [work,ins,stage,q['residents'],q['bytes'],q['pins'],q['nonce']]!=[0,0,0,0,0,0,1]: return False
 if stage:
  if type(q['op'])!=int or not 0<q['op']<=MAX or type(q['function'])!=int or not 0<=q['function']<80000: return False
 if 6<=stage<=10:
  a,b,c=q['selected'],q['taken'],q['committed']
  if any(type(v)!=int or not 0<=v<=MAX for v in [a,b,c]): return False
  if a>>x['slots'] or b&~a or c&~b or type(q['feasible'])!=bool: return False
  if q['feasible'] and (type(q['destination'])!=int or not 0<=q['destination']<x['slots']): return False
  if stage in (7,8) and (not q['feasible'] or type(q['pending'])!=int or not 0<=q['pending']<x['slots'] or not a&(1<<q['pending'])): return False
 return True

def project(x,q):
 if x.get('outer') is not None: return 'T00',None,x['outer']
 # A returned aggregate has both admissions. Three other variants are excluded
 # at contract level; actual private receipt construction remains a future proof.
 if (x.get('SS',1),x.get('SF',1))!=(1,1): raise ValueError('outside returned private paid domain; not a runtime pass')
 c,p,l=x['C'],x['P'],x['L']
 def z(t,b,r): return t,zero_projection(b,r,x['NC']),None
 if c=='InputBinding': return z('T01',0,2)
 if c=='InputBudget': return z('T02',4,1)
 if c=='InputInvalid': return z('T03',0,3)
 if c=='EnvelopePoison' or p=='Poison': return z('T04',5,16)
 header_bad=(p=='Absent' and (x['calls']!=0 or l!='None')) or (p=='Valid' and x['calls']==0) or x.get('bad_header',False)
 if p in ('Unreadable','Stale','Malformed') or header_bad: return z('T05',5,16)
 if c in ('EnvelopeUnavailable','Unsupported'): return z('T06',0,5)
 if c=='EnvelopeRefused': return z('T07',3,4)
 if p=='Absent': return z('T08',0,5)
 if not guards(x,q): return z('T09',5,16)
 if l=='Refusal': t,b,r,stop,failure,tail='T10',3,x['reason'],x['stop'],0,1
 elif l=='Failure': t,b,r,stop,failure,tail='T11',6,14,x['stop'],x['stop'],1
 elif l=='Limit': t,b,r,stop,failure,tail='T12',4,1,x['stop'],0,1
 elif c=='Limited': t,b,r,stop,failure,tail='T13',4,1,x['N']+1,0,1
 elif c=='Cap': t,b,r,stop,failure,tail='T14',2,0,0,0,1
 else: t,b,r,stop,failure,tail='T15',1,0,0,0,0
 # Supply only guarded fields to the projector so no inactive field is read.
 safe={k:q[k] for k in ['M','work','instructions','stage','residents','bytes','pins','nonce']}
 active=q['stage']!=0; planned=6<=q['stage']<=10
 safe.update(op=q['op'] if active else 0,function=q['function'] if active else MAX,
  selected=q['selected'] if planned else 0,taken=q['taken'] if planned else 0,committed=q['committed'] if planned else 0,
  pending=q['pending'] if q['stage'] in (7,8) else MAX,feasible=q['feasible'] if planned else False)
 safe['destination']=q['destination'] if planned and safe['feasible'] else MAX
 return t,visible_projection(safe,x['N'],x['NC'],b,r,stop,failure,tail),None

def sample(stage=0,latch='None',child='Cap'):
 m=4; n=m+int(latch!='None')
 x={'C':child,'P':'Valid','L':latch,'N':n,'NC':n,'calls':n,'slots':3,'pin_slots':3,
  'reason':{'None':0,'Refusal':9,'Failure':14,'Limit':1}[latch],
  'stop':m+1 if latch!='None' else 0,'SS':1,'SF':1}
 q={'M':m,'sequence':m,'work':20,'instructions':30,'stage':stage,'op':2,'function':513,
  'residents':2,'bytes':6,'pins':1,'nonce':4,'selected':2,'taken':2 if stage==8 else 0,
  'committed':0,'feasible':True,'destination':1,'pending':1}
 return x,q
