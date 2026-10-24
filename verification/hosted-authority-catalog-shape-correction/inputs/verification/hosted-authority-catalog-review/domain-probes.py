#!/usr/bin/env python3
"""Frozen raw-input boundary probes; no database or producer file is changed."""
import copy,datetime,gzip,hashlib,json,pathlib,subprocess,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ATTEMPT=HERE/'attempt-2'
sys.path.insert(0,str(ATTEMPT/'source'))
from inspector import validate,decode
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    source=ATTEMPT/'independent/observations/001.json.gz';raw=decode(gzip.decompress(source.read_bytes()))['raw']
    expected_path=ATTEMPT/'inputs/verification/hosted-authority-catalog-correction/selected-expected.json';expected=decode(expected_path.read_bytes())
    cases=[]
    def probe(label,group,key,value,domain_valid,row_predicate=lambda r:True):
        changed=copy.deepcopy(raw);row=next(r for r in changed['enforcement'][group] if row_predicate(r));row[key]=value
        try:validate(changed,expected);admitted=True;error=None
        except ValueError as exc:admitted=False;error=str(exc)
        cases.append({'label':label,'group':group,'field':key,'value':value,'domain_valid':domain_valid,'admitted':admitted,'contract_gap':admitted and not domain_valid,'rejection':error})
    for group in ['relations','constraints','indexes','triggers']:
        for value,valid in [(-1,False),(0,False),(1,True),(4294967295,True),(4294967296,False),(True,False),(1.0,False),('1',False),(None,False),({},False)]:
            probe('row OID '+group,group,'oid',value,valid)
    for field in ['relation_oid','function_oid','constraint_oid','referenced_relation_oid','constraint_index_oid']:
        for value,valid in [(-1,False),(0,False),(1,True),(4294967295,True),(4294967296,False),(True,False),(1.0,False),('1',False),(None,False),({},False)]:
            probe('nonzero trigger association OID','triggers',field,value,valid,lambda r:r['internal'] and bool(r[field]))
    for field in ['name','definition']:
        for value in [None,{},[],False,0,'']:
            probe('required nonempty internal text','triggers',field,value,False,lambda r:r['internal'])
    for group,rows in raw['enforcement'].items():
        if not rows:continue
        row=rows[0]
        for field,value in row.items():
            if type(value) is bool:probe('retained boolean must not equal integer',group,field,int(value),False)
    receipt={'schema':1,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'cwd':str(ROOT),'observed_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'python':sys.version,'source_path':str(source.relative_to(ROOT)),'source_sha256':sha(source.read_bytes()),'expected_sha256':sha(expected_path.read_bytes()),'inspector_sha256':sha((ATTEMPT/'source/inspector.py').read_bytes()),'script_sha256':sha(pathlib.Path(__file__).read_bytes()),'scope':'raw comparator model inputs only; no runtime bypass claim','total':len(cases),'admitted_malformed':sum(c['contract_gap'] for c in cases),'valid_uint32_OID_portability_controls':sum(c['domain_valid'] and c['admitted'] for c in cases),'rejected':sum(not c['admitted'] for c in cases),'cases':cases}
    (ATTEMPT/'domain-probes.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='cases'},indent=2))
if __name__=='__main__':main()
