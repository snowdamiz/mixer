from pathlib import Path
import argparse,copy,gzip,hashlib,json,platform,signal,sys
from audit_selected_replay_v2 import Audit,loads,same

def main():
 signal.alarm(60);parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--recovery',type=Path,required=True);args=parser.parse_args();assert not args.output.exists();base=args.run.resolve();path=base/'boundary-027.rows.jsonl.gz';raw=loads(next(gzip.open(path,'rt')));small=loads(Path(str(path)+'.compact.jsonl').open().readline());audit=Audit(base,args.recovery.resolve());audit.row(raw,small,{'file':path.name,'row':1});controls=[]
 def refusal(name,action):
  try:action()
  except(KeyError,TypeError,ValueError,IndexError)as result:controls.append({'name':name,'refused':True,'reason':str(result)});return
  raise AssertionError('unrefused hostile metadata '+name)
 def mutate(name,change):
  a=copy.deepcopy(raw);b=copy.deepcopy(small);change(a,b);refusal(name,lambda:audit.row(a,b,{'file':path.name,'row':1}))
 mutate('bool-caller-bci',lambda a,b:a['selected']['caller'].__setitem__('bci',True))
 mutate('float-caller-bci',lambda a,b:a['selected']['caller'].__setitem__('bci',float(a['selected']['caller']['bci'])))
 mutate('BCI-zero-substitution',lambda a,b:a['selected']['caller'].__setitem__('bci',0))
 mutate('foreign-caller-source-hash',lambda a,b:a['selected']['caller'].__setitem__('source_sha256','0'*64))
 mutate('wrong-caller-descriptor',lambda a,b:a['selected']['caller'].__setitem__('descriptor','()V'))
 mutate('nonempty-malformed-selected-structure',lambda a,b:a.__setitem__('selected','nonempty'))
 mutate('missing-clean-latch',lambda a,b:a.pop('outcome_probe_clean'))
 mutate('missing-selected-hook-and-points-together',lambda a,b:(a.pop('selected_hook_fired'),a.__setitem__('selected',{}),b.__setitem__('selected_immutable_event_points',[])))
 mutate('bool-event-index',lambda a,b:b['selected_immutable_event_points'][0].__setitem__('sequence_index',True))
 mutate('float-real-frame-BCI',lambda a,b:b['selected_immutable_event_points'][0]['production_frames'][0].__setitem__('bci',float(b['selected_immutable_event_points'][0]['production_frames'][0]['bci'])))
 refusal('duplicate-JSON-object-key',lambda:loads('{"bci":1,"bci":2}'))
 refusal('nonstandard-JSON-NaN',lambda:loads('{"value":NaN}'))
 refusal('nonstandard-JSON-Infinity',lambda:loads('{"value":Infinity}'))
 for name,left,right in [('bool-int',True,1),('int-float',381,381.0),('nested-bool-int',{'count':[True]},{'count':[1]}),('nested-float-int',{'bci':381.0},{'bci':381})]:
  assert not same(left,right),name;controls.append({'name':name,'refused':True,'reason':'strict recursive types differ'})
 def bool_value(a,b):
  completion=next(item for item in a['actual_native_outcomes']if item['value']['kind']=='boolean');completion['value']['value']=1
 def snapshot_order(a,b):
  completion=next(item for item in a['actual_native_outcomes']if item['value']['kind']=='typed-snapshot'and len(item['value']['fields'])>1);completion['value']['fields'].reverse()
 mutate('coherent-raw-native-Boolean-as-integer',bool_value)
 mutate('coherent-raw-typed-snapshot-field-order',snapshot_order)
 mutate('floating-same-invocation-return-index',lambda a,b:b['selected_actual_call_pairs'][0].__setitem__('same_invocation_before_return_sequence_index',float(b['selected_actual_call_pairs'][0]['same_invocation_before_return_sequence_index'])))
 mutate('missing-actual-receiver-map',lambda a,b:(a.pop('native_receiver_bindings'),b.pop('native_receiver_bindings')))
 mutate('duplicate-actual-receiver-binding',lambda a,b:(a['native_receiver_bindings'].append(copy.deepcopy(a['native_receiver_bindings'][0])),b['native_receiver_bindings'].append(copy.deepcopy(b['native_receiver_bindings'][0]))))
 mutate('coherent-original-field-drift-in-compact',lambda a,b:b.__setitem__('scenario','candidate-other-scenario'))
 mutate('missing-explicit-native-validation-outcome',lambda a,b:(a.pop('validation_failure'),b.pop('validation_failure')))
 mutate('void-scenario-result-replaced-by-null',lambda a,b:(a.__setitem__('enclosing_actual_outcome',{'kind':'null'}),b.__setitem__('enclosing_actual_outcome',{'kind':'null'})))
 refusal('failed-parent-without-explicit-recovery',lambda:Audit(base))
 empty=Audit(base,args.recovery.resolve());refusal('missing-full189-state-roster',empty.require_historical_states)
 for historical in empty.historical:empty.history[historical]=[{'state':state}for state in('clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback')]
 empty.require_historical_states();deleted=next(iter(empty.historical));saved=empty.history.pop(deleted);refusal('deleted-whole-boundary-and-all-state-rows',empty.require_historical_states);empty.history[deleted]=saved;empty.history[deleted].append({'state':'clean'});refusal('duplicate-required-state',empty.require_historical_states)
 args.output.write_text(json.dumps({'schema':2,'source_provenance':{name:{'bytes':len((Path(__file__).resolve().parent/name).read_bytes()),'sha256':hashlib.sha256((Path(__file__).resolve().parent/name).read_bytes()).hexdigest()}for name in('test_observation_auditor_v2.py','audit_selected_replay_v2.py')},'python':sys.version,'python_executable':sys.executable,'platform':platform.platform(),'argv':sys.argv,'positive_actual_row':str(base/'boundary-027.rows.jsonl.gz')+':1','controls':controls,'scope':'Read-only actual source/class/raw/compact reconciliation controls; synthetic roster completeness controls grant no execution evidence. Output remains unqualified.'},indent=2)+'\n');signal.alarm(0);print(json.dumps({'actual_positive_rows':1,'refusal_controls':len(controls),'all_refused':all(item['refused']for item in controls)}))
if __name__=='__main__':main()
