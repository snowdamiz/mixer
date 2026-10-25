"""Closed supplemental schema and exact host join. No runtime/transport imports."""
import copy, hashlib, json
from dataclasses import dataclass
from decimal import Decimal

SCHEMA='mixer.apple-toggle.focus-system.1'
SLOTS=('authored-toggle','plain-uibutton-reference','next-focus')
LIMIT=2_147_483_647
STATUSES={'complete','incomplete-counter','incomplete-count','incomplete-metadata','incomplete-time','incomplete-entry-size','incomplete-total-size'}
class Incomplete(ValueError):pass

def require(ok,reason):
 if not ok:raise Incomplete(reason)
def keys(v,want):require(type(v) is dict and set(v)==set(want.split()),'closed-keys')
def integer(v,lo=0,hi=LIMIT):return type(v) is int and lo<=v<=hi
def number(v):return (type(v) in (int,Decimal) and (type(v) is int or v.is_finite()) and v>=0)
def token(v):return type(v) is str and 0<len(v.encode())<=128 and all(33<=ord(c)<=126 for c in v)
def optional_token(v):return v is None or token(v)
def canonical(v):
 """No binary float round trip; Decimal spellings retain exact timestamp values."""
 if v is None:return 'null'
 if type(v) is bool:return 'true' if v else 'false'
 if type(v) is int:return str(v)
 if type(v) is Decimal:
  require(v.is_finite(),'nonfinite');return str(v)
 if type(v) is str:return json.dumps(v,ensure_ascii=False,separators=(',',':'))
 if type(v) is list:return '['+','.join(canonical(x) for x in v)+']'
 if type(v) is dict:
  require(all(type(k) is str for k in v),'non-string-key')
  return '{'+','.join(canonical(k)+':'+canonical(v[k]) for k in sorted(v))+'}'
 raise Incomplete('unsupported-json-type')
def encoded(v):return canonical(v).encode()
def loads(raw):
 def reject(v):raise Incomplete('nonfinite-json')
 def pairs(items):
  out={}
  for k,v in items:
   require(k not in out,'duplicate-json-key');out[k]=v
  return out
 return json.loads(raw,parse_float=Decimal,parse_constant=reject,object_pairs_hook=pairs)

def endpoint(system,controls):
 keys(system,'state identity item');item=system['item'];keys(item,'state identity fixedMatches')
 matches=item['fixedMatches'];require(type(matches) is list and len(matches)==3 and all(type(v) is bool for v in matches),'fixed-matches')
 if system['state']=='unavailable':
  require(system['identity'] is None and item['state']=='unavailable' and item['identity'] is None and not any(matches),'unavailable-item');return
 require(system['state']=='present' and token(system['identity']),'system-presence')
 if item['state']=='null':require(item['identity'] is None and not any(matches),'null-item');return
 require(item['state'] in ('fixed','other') and token(item['identity']),'item-state')
 expected=[item['identity']==r['identity'] for r in controls]
 require(matches==expected and item['state']==('fixed' if any(expected) else 'other'),'pointer-identity-map')

def validate(value,contexts):
 keys(value,'schema authoritative atomic entries dropped revision captureStatus')
 require(value['schema']==SCHEMA and value['authoritative'] is False and value['atomic'] is False,'supplemental-only')
 require(value['captureStatus'] in STATUSES and integer(value['dropped']) and integer(value['revision']),'bounded-envelope')
 require(type(value['entries']) is list and len(value['entries'])<=128,'entry-count')
 require(len(encoded(value))<=65536,'total-size')
 require(type(contexts) is list and len(contexts)<=128,'original-context-count')
 context_by_seq={}
 for context in contexts:
  require(type(context) is dict and integer(context.get('sequence'),1) and context['sequence'] not in context_by_seq,'original-context-sequence')
  context_by_seq[context['sequence']]=context
 require(list(context_by_seq)==list(range(1,len(contexts)+1)),'original-context-order')
 callback_refs=[]
 known_identities=None
 prior=Decimal(0)
 for index,row in enumerate(value['entries'],1):
  keys(row,'sequence startedUptime finishedUptime site contextSequence stage environment system controls scene')
  require(len(encoded(row))<=4096,'entry-size')
  require(integer(row['sequence'],1) and row['sequence']==index,'entry-sequence')
  require(number(row['startedUptime']) and number(row['finishedUptime']) and prior<=row['startedUptime']<=row['finishedUptime'],'entry-time')
  prior=row['finishedUptime']
  require(row['site'] in ('snapshot','controller-callback','carrier-callback') and token(row['stage']),'entry-site-stage')
  if row['site']=='snapshot':require(row['contextSequence'] is None,'snapshot-context')
  else:
   seq=row['contextSequence'];require(integer(seq,1) and seq in context_by_seq,'callback-context')
   require(seq not in callback_refs,'duplicate-callback-context');callback_refs.append(seq)
   context=context_by_seq[seq]
   require(context.get('source')==row['site'][:-9] and number(context.get('uptime')) and context['uptime']<=row['startedUptime'],'callback-source-time')
  env=row['environment'];keys(env,'selection identity windowIdentity')
  require(token(env['identity']) and optional_token(env['windowIdentity']),'environment-identity')
  require((env['selection']=='window' and env['identity']==env['windowIdentity']) or (env['selection']=='controller' and env['windowIdentity'] is None),'environment-selection')
  controls=row['controls'];require(type(controls) is list and len(controls)==3,'fixed-three-controls')
  identities=[]
  for slot,control in zip(SLOTS,controls):
   keys(control,'slot identity isFocused attachedToWindow windowIdentity canBecomeFocused focusGroupIdentifier focusGroupPriority')
   require(control['slot']==slot and token(control['identity']) and control['identity'] not in identities,'control-identity-order');identities.append(control['identity'])
   require(all(type(control[k]) is bool for k in ('isFocused','attachedToWindow','canBecomeFocused')),'control-booleans')
   require(optional_token(control['windowIdentity']) and control['attachedToWindow']==(control['windowIdentity'] is not None),'control-attachment')
   group=control['focusGroupIdentifier'];require(group is None or (type(group) is str and len(group.encode())<=128),'group-identifier')
   require(integer(control['focusGroupPriority'],-(2**63),2**63-1),'group-priority')
  if known_identities is None:known_identities=identities
  require(identities==known_identities,'known-control-identity-changed')
  endpoint(row['system'],controls)
  scene=row['scene'];keys(scene,'state identity systemIdentity itemIdentity')
  require(all(optional_token(scene[k]) for k in ('identity','systemIdentity','itemIdentity')),'scene-identities')
  if scene['state']=='absent':require(all(scene[k] is None for k in ('identity','systemIdentity','itemIdentity')),'scene-absent')
  elif scene['state']=='unavailable':require(token(scene['identity']) and scene['systemIdentity'] is None and scene['itemIdentity'] is None,'scene-unavailable')
  else:require(scene['state']=='present' and token(scene['identity']) and token(scene['systemIdentity']),'scene-present')
 if value['captureStatus']=='complete':
  require(value['dropped']==0 and value['revision']==len(value['entries']),'complete-accounting')
  require(callback_refs==list(context_by_seq),'complete-context-order')
 else:
  require(value['dropped']>0 and value['revision']>=len(value['entries']),'incomplete-accounting')
  raise Incomplete(value['captureStatus'])
 return value

SELECTED_ACTION='v7-first-tab'
RAW_INPUTS={
 'before':(16451,'82581f55bd299fb623d85a39fa726ee072bb54fb065164da6618fec63c2c9c3d'),
 'after':(21153,'160f124cb50b74006b7f6791c0aab6a683dab65a9ad9c193604569efcf2a7a9b'),
 'witness':(1816,'388655651136e672499be043e1188733ca6dd549af67f755185332a77b90d70e'),
}
@dataclass(frozen=True)
class OriginalActionAnchor:
 """Frozen V7 replay inputs, never authority to ingest a future runtime action."""
 selection:str
 before_packet_raw:bytes
 after_packet_raw:bytes
 witness_packet_raw:bytes

def _original_action(anchor):
 require(type(anchor) is OriginalActionAnchor and anchor.selection==SELECTED_ACTION,'original-action-selection')
 packets={}
 for role,(size,digest) in RAW_INPUTS.items():
  raw=getattr(anchor,role+'_packet_raw')
  require(type(raw) is bytes and len(raw)==size and hashlib.sha256(raw).hexdigest()==digest,'original-action-raw-'+role)
  packets[role]=loads(raw)
 action=packets['witness']['binding']
 require(type(action['case']) is str and action['case']=='keyboard-enabled-off' and type(action['generation']) is int and action['generation']==1 and type(action['actionIndex']) is int and action['actionIndex']==1,'selected-action-identity')
 return packets

def select_original_action(selection,before_packet_raw,after_packet_raw,witness_packet_raw):
 """Verify the closed, independently pinned raw packet digests before joining.

 No candidate observation or candidate-supplied expected fingerprint participates
 in selection. A later native packet needs a separately reviewed selection.
 Invalid selection raises Incomplete and cannot produce a complete join receipt.
 """
 anchor=OriginalActionAnchor(selection,before_packet_raw,after_packet_raw,witness_packet_raw)
 _original_action(anchor)
 return anchor

def same_json(left,right):
 """Exact JSON values, nested types and Decimal spellings; no float coercion."""
 if type(left) is not type(right):return False
 if type(right) is dict:
  return left.keys()==right.keys() and all(same_json(left[k],right[k]) for k in right)
 if type(right) is list:
  return len(left)==len(right) and all(same_json(a,b) for a,b in zip(left,right))
 if type(right) is Decimal:return left.is_finite() and right.is_finite() and left.as_tuple()==right.as_tuple()
 return type(right) in (str,int,bool,type(None)) and left==right

def without_diagnostic(value):
 require(type(value) is dict,'original-observation-type')
 return {k:v for k,v in value.items() if k!='focusSystemDiagnostic'}

def join(before,after,witness,binding,anchor,original_verdict):
 """Frozen V7 supplemental replay only; preserve the original verdict identity."""
 receipt={'schema':'mixer.apple-toggle.focus-system-join.1','scope':'frozen-v7-replay-only','authoritative':False,'atomic':False,'nativePass':False,'captureStatus':'incomplete-invalid','binding':None}
 original_bytes=None
 try:
  original_bytes=encoded(original_verdict)
  packets=_original_action(anchor)
  original_witness=packets['witness']['witness'];original_binding=packets['witness']['binding']
  expected={k:original_binding[k] for k in ('case','generation','actionIndex')}
  receipt['binding']=copy.deepcopy(expected)
  require(same_json(without_diagnostic(before),packets['before']['observation']),'original-before-observation')
  require(same_json(without_diagnostic(after),packets['after']['observation']),'original-after-observation')
  require(same_json(witness,original_witness),'original-witness')
  require(same_json(binding,original_binding),'original-binding')
  require(same_json(original_verdict['keyboardWitness'],witness),'verdict-witness-consistency')
  require(same_json(original_verdict['keyboardBinding'],binding),'verdict-binding-consistency')
  require(same_json(original_verdict,packets['after']['verdict']),'original-verdict')
  keys(binding,'case generation actionIndex baselineUptime evaluatedUptime')
  keys(expected,'case generation actionIndex')
  require(token(binding['case']) and integer(binding['generation'],1) and integer(binding['actionIndex'],1),'binding-types')
  require(all(type(binding[k]) is type(expected[k]) and binding[k]==expected[k] for k in expected),'binding-mismatch')
  require(number(binding['baselineUptime']) and number(binding['evaluatedUptime']),'binding-time')
  keys(witness,'case generation actionIndex phase key publicAPI returned before startedUptime finishedUptime after')
  require(all(type(witness[k]) is type(binding[k]) and witness[k]==binding[k] for k in expected),'witness-binding')
  require(witness['publicAPI']=='XCUIElement.typeKey(_:modifierFlags:)' and witness['returned'] is True,'original-key-api')
  phase_keys={'acquire':'tab','space-first':'space','space-reverse':'space','tab-reference':'tab','tab-next':'tab','reverse-reference':'shift-tab','reverse-toggle':'shift-tab','stale-space':'space','resumed-space':'space','disabled-held-space':'space','disabled-navigation':'tab','disabled-space':'space','disabled-reverse':'shift-tab'}
  require(witness['phase'] in phase_keys and witness['key']==phase_keys[witness['phase']],'original-key-phase')
  times=[binding['baselineUptime'],witness['before']['uptime'],witness['startedUptime'],witness['finishedUptime'],witness['after']['uptime'],binding['evaluatedUptime']]
  require(all(number(v) for v in times) and times[0]<=times[1]<=times[2]<times[3]<=times[4]<=times[5] and times[4]-times[1]<=12,'original-witness-time')
  # Every original endpoint and full witness/binding now matches pinned packets.
  left=validate(before['focusSystemDiagnostic'],before['focusContexts'])
  right=validate(after['focusSystemDiagnostic'],after['focusContexts'])
  require(all(type(x['focusContextDropped']) is int and x['focusContextDropped']==0 and type(x['focusContextRevision']) is int and x['focusContextRevision']==len(x['focusContexts']) for x in [before,after]),'original-context-overflow')
  require(after['focusContexts'][:len(before['focusContexts'])]==before['focusContexts'],'original-context-prefix')
  require(right['entries'][:len(left['entries'])]==left['entries'],'entry-prefix')
  require(not left['entries'] or left['entries'][-1]['finishedUptime']<=times[1],'before-boundary-time')
  require(not right['entries'] or right['entries'][-1]['finishedUptime']<=times[5],'after-boundary-time')
  delta=right['entries'][len(left['entries']):]
  receipt.update(captureStatus='complete',selectedOriginalAction=anchor.selection,selectedPacketSHA256={role:digest for role,(_,digest) in RAW_INPUTS.items()},beforeEntryCount=len(left['entries']),afterEntryCount=len(right['entries']),newSequences=[r['sequence'] for r in delta],witnessSHA256=hashlib.sha256(encoded(witness)).hexdigest(),bindingSHA256=hashlib.sha256(encoded(binding)).hexdigest(),beforeObservationSHA256=hashlib.sha256(encoded(without_diagnostic(before))).hexdigest(),afterObservationSHA256=hashlib.sha256(encoded(without_diagnostic(after))).hexdigest(),beforeDiagnosticSHA256=hashlib.sha256(encoded(left)).hexdigest(),afterDiagnosticSHA256=hashlib.sha256(encoded(right)).hexdigest(),originalVerdictSHA256=hashlib.sha256(original_bytes).hexdigest())
 except (Incomplete,KeyError,TypeError,ValueError,OverflowError,UnicodeError) as e:
  reason=str(e)
  receipt['captureStatus']='incomplete-'+(reason if token(reason) else 'malformed')
 if original_bytes is not None:require(encoded(original_verdict)==original_bytes,'original-verdict-mutated')
 return {'supplemental':receipt,'originalVerdict':original_verdict}

class Buffer:
 """Host model of Swift's bounded retention; no UIKit or native claims."""
 def __init__(self):self.entries=[];self.dropped=0;self.revision=0;self.status='complete'
 def value(self):return dict(schema=SCHEMA,authoritative=False,atomic=False,entries=copy.deepcopy(self.entries),dropped=self.dropped,revision=self.revision,captureStatus=self.status)
 def fail(self,status):
  if self.status=='complete':self.status=status
  if self.dropped<LIMIT:self.dropped+=1
  else:self.status='incomplete-counter'
 def append(self,row):
  if self.revision>=LIMIT:self.fail('incomplete-counter');return
  self.revision+=1
  if self.status!='complete':self.fail(self.status);return
  if len(self.entries)>=128:self.fail('incomplete-count');return
  candidate=copy.deepcopy(row);candidate['sequence']=self.revision
  try:
   if len(encoded(candidate))>4096:self.fail('incomplete-entry-size');return
   proposed=self.value();proposed['entries'].append(candidate);proposed.update(dropped=LIMIT,revision=LIMIT,captureStatus='incomplete-entry-size')
   if len(encoded(proposed))>65536:self.fail('incomplete-total-size');return
  except Incomplete:self.fail('incomplete-metadata');return
  self.entries.append(candidate)
