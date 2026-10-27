from pathlib import Path
import argparse,copy,gzip,hashlib,json,signal
from delegated_association import validate_row,INNER,OUTER
def identity(path):
 data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def main():
 signal.alarm(60);parser=argparse.ArgumentParser();parser.add_argument('--raw',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();assert not args.output.exists();rows=[json.loads(line)for line in gzip.open(args.raw,'rt')];positive=[{'state':row['state'],**validate_row(row)}for row in rows];base=next(row for row in rows if row['state']=='current');own=[index for index,item in enumerate(base['actual_native_outcomes'])if item['method']=='BaseInputConnection.setComposingRegion'and item['receiver_identity']==base['original_target']and item['completion']=='return'];assert len(own)==2;first,second=own
 def change(name,mutation):
  row=copy.deepcopy(base);mutation(row)
  try:validate_row(row)
  except(KeyError,TypeError,ValueError)as refusal:return {'name':name,'refused':True,'reason':str(refusal)}
  raise AssertionError('accepted wrong actual association: '+name)
 def item(row,index):return row['actual_native_outcomes'][index]
 def remove(row,indices):row['actual_native_outcomes']=[value for index,value in enumerate(row['actual_native_outcomes'])if index not in indices]
 def swap(row):row['actual_native_outcomes'][first],row['actual_native_outcomes'][second]=row['actual_native_outcomes'][second],row['actual_native_outcomes'][first]
 def wrong_caller(row):
  # Another actually observed product invocation frame chain from the same exact compiled run.
  neighbor=next(value['production_frames']for value in row['actual_native_outcomes']if value['production_frames']and value['production_frames']!=item(row,first)['production_frames'])
  item(row,first)['production_frames']=copy.deepcopy(neighbor);item(row,second)['production_frames']=copy.deepcopy(neighbor)
 negatives=[change('wrong-descriptor',lambda row:item(row,second).__setitem__('descriptor','(I)Z')),change('wrong-order',swap),change('wrong-value',lambda row:item(row,second)['value'].__setitem__('value',False)),change('boolean-as-integer',lambda row:item(row,second)['value'].__setitem__('value',1)),change('wrong-receiver',lambda row:item(row,second).__setitem__('receiver_identity','foreign-actual-receiver')),change('wrong-frame',lambda row:item(row,second).__setitem__('production_frames',[])),change('coherent-other-actual-caller',wrong_caller),change('wrong-event',lambda row:item(row,second).__setitem__('native_event_sequence_index',item(row,second)['native_event_sequence_index']+1)),change('boolean-event-index',lambda row:item(row,second).__setitem__('native_event_sequence_index',True)),change('wrong-phase',lambda row:item(row,second).__setitem__('native_event_phase','entry')),change('missing-outer-completion',lambda row:remove(row,{second})),change('missing-inner-completion',lambda row:remove(row,{first})),change('missing-both-completions',lambda row:remove(row,{first,second})),change('doubled-completion',lambda row:row['actual_native_outcomes'].append(copy.deepcopy(item(row,second)))),change('missing-explicit-delegation-marker',lambda row:item(row,second).pop('native_outcome_association')),change('extra-native-entry',lambda row:row.__setitem__('native_target_entries',2))]
 result={'schema':1,'raw':str(args.raw),'raw_identity':identity(args.raw),'positive_rows':positive,'negative_controls':negatives,'scope':'Actual retained JVM observations reconciled, with hostile data substitutions refused. Ordinary host utility only; no execution-closure, whole matrix, native, OTA or GA admission.'};args.output.write_text(json.dumps(result,indent=2)+'\n');signal.alarm(0);print(json.dumps({'positive_rows':len(positive),'negative_controls':len(negatives),'all_refused':all(row['refused']for row in negatives)}))
if __name__=='__main__':main()
