"""Typed row closure against an independently pinned semantic policy, not candidate-declared scope."""
def need(v,msg):
 if not v:raise ValueError(msg)
def integer(v):return type(v) is int
def obj(v,name):need(type(v) is dict,name+' must be object');return v
def text(v,name):need(type(v) is str and bool(v),name+' must be nonempty string');return v
def fields(v,names,name):obj(v,name);need(set(v)==set(names),name+' exact fields mismatch')
def ids(v,name):need(type(v) is list and all(type(x) is str and x for x in v) and len(v)==len(set(v)),name+' must be unique string array')
def result(v):
 fields(v,('original_result','gate_state','retirement_state','count_state','cleanup_state','fatal_state'),'expected/observed')
 fields(v['original_result'],('kind','value'),'original_result');kind=v['original_result']['kind'];value=v['original_result']['value'];need(kind in ('boolean','integer','text','null','snapshot','void'),'invalid result kind')
 need((kind=='boolean' and type(value) is bool) or (kind=='integer' and integer(value)) or (kind=='text' and type(value) is str) or (kind in ('null','void') and value is None) or (kind=='snapshot' and type(value) is dict),'result value type mismatch')
 fields(v['gate_state'],('terminal','draw_allowed','input_allowed'),'gate_state');need(all(type(x) is bool for x in v['gate_state'].values()),'gate booleans required')
 fields(v['retirement_state'],('attempt_revoked','target_disposition'),'retirement_state');need(type(v['retirement_state']['attempt_revoked']) is bool,'revoked boolean required');text(v['retirement_state']['target_disposition'],'target_disposition')
 fields(v['count_state'],('busy','field_preservations','native_calls'),'count_state');need(all(integer(x) and x>=0 for x in v['count_state'].values()),'exact nonnegative integer counts required')
 fields(v['cleanup_state'],('target_close_calls','busy','pending'),'cleanup_state');need(integer(v['cleanup_state']['target_close_calls']) and v['cleanup_state']['target_close_calls']>=0,'close integer required');need(type(v['cleanup_state']['busy']) is bool and type(v['cleanup_state']['pending']) is bool,'cleanup booleans required')
 fields(v['fatal_state'],('class','identity','escaped_exact'),'fatal_state');need(type(v['fatal_state']['escaped_exact']) is bool,'fatal boolean required');need(all(x is None or type(x) is str and x for x in (v['fatal_state']['class'],v['fatal_state']['identity'])),'fatal identity/class type')
def caller(v):
 fields(v,('class','class_sha256','source_sha256','method','descriptor','bci','opcode','callee'),'caller');need(integer(v['bci']) and v['bci']>=0,'BCI exact integer required')
 for k in ('class','class_sha256','source_sha256','method','descriptor','opcode'):text(v[k],'caller '+k)
 fields(v['callee'],('owner','name','descriptor'),'callee')
 for x in v['callee'].values():text(x,'callee field')
def authority(v):
 fields(v,('mode','fence_identity','token_identity','record_identity','view_identity','editable_identity','binding_identity','attempt_identity','target_identity'),'original_authority');need(v['mode'] in ('TRANSACTION','LIVE_PRESENTATION','CLEANUP','LEGACY_V1','REFUSAL_NO_SCOPE'),'authority mode')
 for k,x in v.items():need(type(x) is str and x or x is None,'authority identity must be string or null')
 need(v['mode'] in ('LEGACY_V1','REFUSAL_NO_SCOPE') or type(v['fence_identity']) is str and bool(v['fence_identity']),'authority fence identity required')
 if v['mode'] in ('TRANSACTION','LIVE_PRESENTATION'):text(v['token_identity'],'original token')
def validate(policy,context,matrix):
 obj(policy,'independent semantic policy');obj(context,'context map');obj(matrix,'fresh certificate');obligations=policy.get('boundaries');need(type(obligations) is list and obligations,'policy needs reviewed active obligations');expected={};tags=set()
 for b in obligations:
  obj(b,'policy boundary');bid=text(b.get('id'),'policy boundary id');need(bid not in expected,'duplicate immutable policy boundary');ids(b.get('required_states'),'policy states');need(b['required_states'],'empty policy state set');expected[bid]=set(b['required_states']);ids(b.get('subjects'),'policy subjects');tags.update(b['subjects'])
 need(set(policy['mandatory_subjects'])<=tags,'independent mandatory subject omitted')
 bindings=context.get('boundaries');need(type(bindings) is list,'context boundaries array required');byid={}
 for b in bindings:
  obj(b,'context boundary');bid=text(b.get('id'),'context boundary id');need(bid not in byid,'duplicate context boundary');caller(b.get('caller'));byid[bid]=b
 need(set(byid)==set(expected),'candidate deleted/added immutable active boundary')
 for bid,b in byid.items():ids(b.get('required_states'),'context states');need(set(b['required_states'])==expected[bid],'candidate deleted/added immutable required state')
 need(matrix.get('status')=='passed','fresh certificate did not pass');rows=matrix.get('rows');need(type(rows) is list,'matrix rows array required');seen=set()
 for row in rows:
  obj(row,'matrix row');key=(row.get('boundary_id'),row.get('state'));need(key[0] in expected and key[1] in expected[key[0]],'unknown row');need(key not in seen,'duplicate state row');seen.add(key);need(row.get('status')=='passed' and row.get('evidence_kind')=='executed-host','unqualified/source-only row');need(integer(row.get('hit')) and row['hit']>0,'hit must be exact positive integer');caller(row.get('caller'));need(row['caller']==byid[key[0]]['caller'],'wrong exact caller/neighbor hook');authority(row.get('original_authority'));text(row.get('receiver_identity'),'actual receiver')
  frames=row.get('production_frames');need(type(frames) is list and frames,'production_frames nonempty array required')
  for frame in frames:
   fields(frame,('class','method','descriptor','bci'),'production frame');need(integer(frame['bci']) and frame['bci']>=0,'frame BCI integer');[text(frame[k],'frame '+k) for k in ('class','method','descriptor')]
  need(any(all(f[k]==row['caller'][k] for k in ('class','method','descriptor','bci')) for f in frames),'selected caller absent from full production frames')
  sequence=row.get('native_event_jni_sequence');need(type(sequence) is list and sequence,'native sequence nonempty array required')
  for event in sequence:
   fields(event,('method','phase','frame_index','receiver_identity'),'sequence event');text(event['method'],'event method');need(event['phase'] in ('entry','beforeReturn','feature-event','JNI'),'event phase');need(integer(event['frame_index']) and 0<=event['frame_index']<len(frames),'event frame index');need(event['receiver_identity'] is None or type(event['receiver_identity']) is str and event['receiver_identity'],'event receiver identity')
  fields(row.get('cleanup_fatal_disposition'),('cleanup_attempted','busy_balanced','first_fatal_identity','pending_reason'),'cleanup/fatal disposition');d=row['cleanup_fatal_disposition'];need(type(d['cleanup_attempted']) is bool and type(d['busy_balanced']) is bool,'cleanup disposition booleans');need(all(v is None or type(v) is str and v for v in (d['first_fatal_identity'],d['pending_reason'])),'cleanup disposition identity/reason')
  need('expected' in row and 'observed' in row,'expected and observed are mandatory');result(row['expected']);result(row['observed']);need(row['expected']==row['observed'],'expected/observed mismatch');need(row.get('unsupported_successor_authority') is False,'unsupported successor claim or missing explicit denial')
 need(seen=={(bid,s) for bid,states in expected.items() for s in states},'incomplete immutable state coverage')
 return {'boundaries':len(expected),'states':len(seen)}
