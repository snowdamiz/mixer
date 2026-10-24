#!/usr/bin/env python3
"""Focused deterministic ACSR01/ACSR02 models; no PostgreSQL or writes on import."""
import copy, gzip, hashlib, json, pathlib, sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'candidate'))
from inspector import decode,validate,canonical
from raw_validation import validate_raw
def execute():
    source=HERE/'inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'
    raw=decode(gzip.decompress(source.read_bytes()))['raw'];expected=decode((HERE/'selected-expected.json').read_bytes());results=[]
    def attempt(fn):
        try:fn();return True,None
        except ValueError as exc:return False,str(exc)
    def probe(label,value,raw_valid,admitted,mutation):
        before=canonical(value);rv,re=attempt(lambda:validate_raw(value));av,ae=attempt(lambda:validate(value,expected));unchanged=canonical(value)==before
        results.append(dict(label=label,mutation=mutation,expected_raw_valid=raw_valid,expected_admitted=admitted,raw_valid=rv,admitted=av,raw_error=re,admission_error=ae,input_unchanged=unchanged,passed=rv==raw_valid and av==admitted and unchanged))
    # These are valid or invalid *unselected* defaults. A successful primitive
    # domain check never substitutes for exact selected comparison.
    for field in ['database','role']:
        for oid,name,valid in [(0,'*',True),(0,'named',False),(0,None,False),(1,'*',True),(4294967295,'*',True),(1,'named',True),(1,None,False),(1,'',False),(1,'\x00',False),(1,'\ud800',False)]:
            x=copy.deepcopy(raw);row={'database_oid':0,'database':'*','role_oid':0,'role':'*','config':['application_name=model']};row.update({field+'_oid':oid,field:name});x['enforcement']['startup_defaults']=[row]
            probe('startup '+field+' '+repr((oid,name)),x,valid,False,{'group':'startup_defaults','row':row})
    frozen=decode((HERE/'inputs/review/name-uniqueness-observations.json').read_bytes())
    for item in frozen['observations']:
        x=copy.deepcopy(raw);row=next(t for t in x['enforcement']['triggers'] if t['oid']==item['mutated_oid']);peer=next(t for t in x['enforcement']['triggers'] if t['oid']==item['peer_oid'])
        assert row['name']==item['old_name'] and peer['name']==item['new_name'];row['name']=peer['name'];valid=not item['violates_retained_pg_trigger_unique_key']
        probe('frozen ACSR02 '+item['mode'],x,valid,valid,{'group':'triggers','oid':row['oid'],'name':row['name'],'peer_oid':peer['oid']})
    x=copy.deepcopy(raw);row=next(t for t in x['enforcement']['triggers'] if t['internal']);assert all(t['name']!='wc_model_distinct' for t in x['enforcement']['triggers']);row['name']='wc_model_distinct'
    probe('different names on the same relation remain portable',x,True,True,{'group':'triggers','oid':row['oid'],'name':row['name']})
    validate(raw,expected)
    return {'schema':1,'scope':'raw copied-input models only; no impossible actual SQL catalog or runtime bypass claim','total':len(results),'passed':all(r['passed'] for r in results),'baseline_admitted':True,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':results}
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();result=execute();pathlib.Path(args.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2));sys.exit(0 if result['passed'] else 1)
