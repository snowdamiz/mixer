import copy,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
fixture=json.loads((D/'actual-instruction-mutation-fixture.json').read_bytes())
def serialized(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def sha(v):return hashlib.sha256(serialized(v)).hexdigest()
caller=fixture['callers'][0];other=fixture['callers'][1];assert caller!=other
context={'context_id':fixture['context_id'],'identity_review_status':'reviewed-exact-context','boundaries':[{'id':'a','required_states':['clean','fatal'],'caller':caller}]};rows={'rows':[{'boundary_id':'a','state':s,'caller':caller} for s in ('clean','fatal')]};approved={context['context_id']:sha(context)}
def gate(c):
 if sha(c)!=approved.get(c['context_id']):raise ValueError('independent exact context-map hash mismatch')
gate(context);out=[]
for name,change in [('real-neighbor-caller-and-all-rows',lambda c,r:(c['boundaries'][0].update(caller=other),[v.update(caller=other) for v in r['rows']])),('required-state-and-matching-row-removed',lambda c,r:(c['boundaries'][0]['required_states'].remove('fatal'),r.update(rows=[v for v in r['rows'] if v['state']!='fatal']))),('boundary-and-all-rows-removed',lambda c,r:(c['boundaries'].clear(),r['rows'].clear())),('same-context-self-review-claim',lambda c,r:c.update(identity_review_status='self-reviewed'))]:
 c=copy.deepcopy(context);r=copy.deepcopy(rows);change(c,r)
 try:gate(c)
 except ValueError as e:out.append({'name':name,'rejected':True,'reason':str(e)})
 else:raise AssertionError('coherent substitution accepted '+name)
print(json.dumps({'scope':'Synthetic context authority controls using two real compiled tuples; not actual product qualification','positive_approved_context_control':1,'negative_controls':out,'all_rejected':True},indent=2))
