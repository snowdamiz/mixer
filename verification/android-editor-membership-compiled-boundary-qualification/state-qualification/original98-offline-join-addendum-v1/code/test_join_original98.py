from pathlib import Path
import copy,json
from join_original98 import load_inputs,validate

def controls():
 data=load_inputs();positive=validate(data);refusals=[]
 def refuse(name,change):
  candidate=copy.deepcopy(data);change(candidate)
  try:validate(candidate)
  except(ValueError,KeyError,TypeError,IndexError)as failure:refusals.append({'name':name,'refused':True,'reason':str(failure)});return
  raise AssertionError('unrefused original98 corruption '+name)
 def command_change(d,key,value):
  for collection in(d['commands'],d['receipt']['commands']):
   next(c for c in collection if c['label'].startswith('original-'))[key]=value
 refuse('missing-original-case',lambda d:d['roster']['cases'].pop())
 refuse('duplicate-original-case-id',lambda d:d['roster']['cases'][1].__setitem__('case_id',d['roster']['cases'][0]['case_id']))
 refuse('missing-historical-alias',lambda d:d['roster']['cases'][0]['historical_aliases'].clear())
 refuse('duplicate-historical-alias',lambda d:d['roster']['cases'][1].__setitem__('historical_aliases',copy.deepcopy(d['roster']['cases'][0]['historical_aliases'])))
 refuse('foreign-selected-review-seal',lambda d:d['roster']['selected_review_seal'].__setitem__('sha256','0'*64))
 refuse('foreign-historical-roster-hash',lambda d:d['roster']['cases'][0]['historical_aliases'][0].__setitem__('sha256','0'*64))
 refuse('foreign-original-source-hash',lambda d:d['roster']['cases'][0]['source'].__setitem__('sha256','0'*64))
 refuse('coherent-bool-current-exit',lambda d:command_change(d,'exit',False))
 refuse('coherent-current-timeout',lambda d:command_change(d,'timeout',True))
 refuse('coherent-current-unreaped-child',lambda d:command_change(d,'reaped',False))
 refuse('coherent-current-unbounded-child',lambda d:command_change(d,'timeout_seconds',61))
 def wrong_argument(d):
  for collection in(d['commands'],d['receipt']['commands']):
   c=next(c for c in collection if c['label']=='original-001-prepared-admission-order');c['argv'][-2]='positive-values'
 refuse('coherent-wrong-original-scenario',wrong_argument)
 def bool_old(d):
  alias=d['roster']['cases'][0]['historical_aliases'][0];next(c for c in d['documents'][alias['command_roster']]if c['name']==alias['name'])['exit']=False
 refuse('bool-historical-exit',bool_old)
 refuse('missing-source-from-compile-freeze',lambda d:d['source_freeze']['sources'].pop())
 refuse('missing-actual-emitted-class',lambda d:d['class_map'].pop(next(iter(d['class_map']))))
 return {'schema':1,'actual_positive_commands':positive['unique_actual_commands'],'actual_positive_aliases':positive['historical_passed_aliases'],'refusal_controls':refusals,'qualified':False}
