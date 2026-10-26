import copy,json
from structured_rows import validate
C={'class':'dev/mixer/android/Subject','class_sha256':'a'*64,'source_sha256':'b'*64,'method':'call','descriptor':'()V','bci':1,'opcode':'invokevirtual','callee':{'owner':'android/view/View','name':'invalidate','descriptor':'()V'}}
P={'mandatory_subjects':['direct-editor'],'boundaries':[{'id':'a','required_states':['clean','fatal'],'subjects':['direct-editor']},{'id':'b','required_states':['clean'],'subjects':['field-preservation']}]}
X={'boundaries':[{'id':b['id'],'required_states':b['required_states'],'caller':C} for b in P['boundaries']]}
V={'original_result':{'kind':'boolean','value':True},'gate_state':{'terminal':False,'draw_allowed':True,'input_allowed':True},'retirement_state':{'attempt_revoked':False,'target_disposition':'active'},'count_state':{'busy':0,'field_preservations':0,'native_calls':1},'cleanup_state':{'target_close_calls':1,'busy':False,'pending':False},'fatal_state':{'class':None,'identity':None,'escaped_exact':False}}
R={'status':'passed','rows':[{'boundary_id':b['id'],'state':s,'status':'passed','evidence_kind':'executed-host','hit':1,'caller':C,'original_authority':{'mode':'LIVE_PRESENTATION','fence_identity':'f1','token_identity':'t1','record_identity':'r1','view_identity':'v1','editable_identity':'e1','binding_identity':'b1','attempt_identity':'a1','target_identity':'target1'},'receiver_identity':'view1','production_frames':[{k:C[k] for k in ('class','method','descriptor','bci')}],'native_event_jni_sequence':[{'method':'View.invalidate','phase':'entry','frame_index':0,'receiver_identity':'view1'}],'cleanup_fatal_disposition':{'cleanup_attempted':True,'busy_balanced':True,'first_fatal_identity':None,'pending_reason':None},'expected':V,'observed':V,'unsupported_successor_authority':False} for b in P['boundaries'] for s in b['required_states']]}
assert validate(P,X,R)=={'boundaries':2,'states':3};controls=[]
def negative(name,fn):
 x=copy.deepcopy(X);r=copy.deepcopy(R);fn(x,r)
 try:validate(P,x,r)
 except (ValueError,TypeError) as e:controls.append({'name':name,'rejected':True,'reason':str(e)});return
 raise AssertionError('accepted mutation '+name)
negative('absent-expected-and-observed',lambda x,r:(r['rows'][0].pop('expected'),r['rows'][0].pop('observed')))
negative('boolean-hit',lambda x,r:r['rows'][0].update(hit=True))
negative('nonempty-string-authority',lambda x,r:r['rows'][0].update(original_authority='wrong'))
negative('nonempty-string-frames',lambda x,r:r['rows'][0].update(production_frames='wrong'))
negative('nonempty-string-sequence',lambda x,r:r['rows'][0].update(native_event_jni_sequence='wrong'))
negative('nonempty-string-cleanup',lambda x,r:r['rows'][0].update(cleanup_fatal_disposition='wrong'))
negative('deleted-boundary-and-all-rows',lambda x,r:(x['boundaries'].pop(),r.update(rows=[v for v in r['rows'] if v['boundary_id']!='b'])))
negative('deleted-state-and-row',lambda x,r:(x['boundaries'][0]['required_states'].remove('fatal'),r.update(rows=[v for v in r['rows'] if v['state']!='fatal'])))
negative('wrong-neighbor-caller',lambda x,r:r['rows'][0]['caller'].update(bci=4))
negative('empty-expected-observed',lambda x,r:r['rows'][0].update(expected={},observed={}))
negative('bool-native-count',lambda x,r:r['rows'][0]['observed']['count_state'].update(native_calls=True))
negative('duplicate-row',lambda x,r:r['rows'].append(copy.deepcopy(r['rows'][0])))
negative('zero-hit',lambda x,r:r['rows'][0].update(hit=0))
negative('missing-active-row',lambda x,r:r['rows'].pop())
negative('source-only-overclaim',lambda x,r:r['rows'][0].update(evidence_kind='source-only'))
negative('caller-absent-from-frames',lambda x,r:r['rows'][0]['production_frames'][0].update(method='foreign'))
print(json.dumps({'scope':'Synthetic integrity fixture only; no source inventory, execution or product acceptance','positive_shape_controls':1,'negative_controls':controls,'all_rejected':True},indent=2))
