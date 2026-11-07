from pathlib import Path
import copy,json,sys,signal
from canonical_query import load_audit,canonical_query_gate,actual_query_rows,RUN,RECOVERY

def main():
 signal.alarm(60);output=Path(sys.argv[1]);assert not output.exists();module=load_audit();path,index,raw,small,lines=next(x for x in actual_query_rows(module)if x[2]['family']=='getTextBeforeCursor'and x[2]['state']=='terminal');audit=module.Audit(RUN,RECOVERY);audit.row(raw,small,{'file':path.name,'row':index});canonical_query_gate(raw,path.name);controls=[]
 def refuse(name,change,old_accepts=False):
  a=copy.deepcopy(raw);b=copy.deepcopy(small);change(a,b)
  if old_accepts:audit.row(a,b,{'file':path.name,'row':index})
  try:canonical_query_gate(a,path.name)
  except(ValueError,KeyError,TypeError,IndexError)as failure:controls.append({'name':name,'refused':True,'v3_row_accepts_coherent_witness':old_accepts,'reason':str(failure)});return
  raise AssertionError('unrefused query canonical mutation '+name)
 def identity(value):
  def change(a,b):
   for row in(a,b):row['original_authority']['receiver']=value;row['original_authority']['attempt']['target']=value
  return change
 refuse('coherent-not-an-object-identity',identity('not-an-object-identity'),True)
 refuse('coherent-wrong-receiver-class',identity('java.lang.Object@1'),True)
 refuse('coherent-leading-zero-global-ordinal',identity('android.view.inputmethod.BaseInputConnection@01'),True)
 refuse('coherent-zero-global-ordinal',identity('android.view.inputmethod.BaseInputConnection@0'))
 refuse('coherent-signed-global-ordinal',identity('android.view.inputmethod.BaseInputConnection@+1'))
 refuse('coherent-bool-receiver-target',identity(True))
 refuse('coherent-null-receiver-target',identity(None))
 refuse('missing-original-receiver',lambda a,b:(a['original_authority'].pop('receiver'),b['original_authority'].pop('receiver')))
 refuse('missing-actual-attempt-target',lambda a,b:(a['original_authority']['attempt'].pop('target'),b['original_authority']['attempt'].pop('target')))
 refuse('contradictory-explicit-target',lambda a,b:(a.__setitem__('original_target','android.view.inputmethod.BaseInputConnection@999999'),b.__setitem__('original_target','android.view.inputmethod.BaseInputConnection@999999')))
 output.write_text(json.dumps({'schema':1,'actual_positive_terminal_row':{'file':path.name,'row':index,'zero_selected_events':True},'refusal_controls':controls,'scope':'Focused actual-row predicates only; unchanged v3 retained40 controls executed separately.','qualified':False},indent=2)+'\n');signal.alarm(0);print(json.dumps({'refusals':len(controls),'three_coherent_v3_witnesses_preserved':True}),flush=True)
if __name__=='__main__':main()
