#!/usr/bin/env python3
"""Independent parser, portability and nonlossy raw-boundary controls."""
import argparse,copy,gzip,hashlib,json,pathlib,sys
sys.dont_write_bytecode=True
ap=argparse.ArgumentParser();ap.add_argument('--packet',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();packet=pathlib.Path(a.packet)
sys.path.insert(0,str(packet/'candidate'))
from inspector import decode,validate,normalize,canonical
from raw_validation import validate_raw
raw=decode(gzip.decompress((packet/'inputs/inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz').read_bytes()))['raw']
expected=decode((packet/'inputs/selected-expected.json').read_bytes());results=[]
def attempt(fn):
    try:fn();return True,None
    except (ValueError,UnicodeError) as e:return False,str(e)
def probe(label,mutate,raw_valid,admitted=False):
    x=copy.deepcopy(raw);mutate(x);before=canonical(x);rv,re=attempt(lambda:validate_raw(x));av,ae=attempt(lambda:validate(x,expected))
    unchanged=canonical(x)==before
    results.append(dict(label=label,expected_raw_valid=raw_valid,raw_valid=rv,expected_admission=admitted,admitted=av,raw_error=re,admission_error=ae,input_unchanged=unchanged,passed=rv==raw_valid and av==admitted and unchanged))
# Bounds deliberately chosen by value, rather than imported implementation constants.
for group,rows in raw['enforcement'].items():
    for field in rows[0] if rows else []:
        if field=='oid' or field.endswith('_oid'):
            for value in [True,False,0.0,1.0,-1,4294967296,10**80]:
                probe(f'{group}.{field} rejects {value!r}',lambda x,g=group,f=field,v=value:x['enforcement'][g][0].__setitem__(f,v),False)
            if rows[0][field]>0:
                for value in [1,2147483648,4294967295]:
                    probe(f'{group}.{field} portable {value}',lambda x,g=group,f=field,v=value:x['enforcement'][g][0].__setitem__(f,v),True,True)
# Validate internal text before its intentional discard, with UTF8 byte arithmetic.
for name,valid in [('😀'*15+'abc',True),('😀'*16,False),('a'*62+'é',False),('a'*61+'é',True),('\udfff',False),('\x00x',False),('\uffff',True),('e\u0301'*21,True)]:
    probe('internal identifier byte/encoding '+repr(name),lambda x,n=name:next(t for t in x['enforcement']['triggers'] if t['internal']).__setitem__('name',n),valid,valid)
for name,valid in [('x\x00',False),('\ud800',False),('😀',True),('\uffff',True),('',False)]:
    probe('internal definition encoding '+repr(name),lambda x,n=name:next(t for t in x['enforcement']['triggers'] if t['internal']).__setitem__('definition',n),valid,valid)
for group,rows in raw['enforcement'].items():
    if rows:
        def dup(x,g=group):
            row=copy.deepcopy(x['enforcement'][g][0]);row.update(oid=4294967295) if 'oid' in row else None;x['enforcement'][g].append(row)
        probe('extra semantic row retained '+group,dup,group != 'triggers')
        if 'oid' in rows[0]:probe('duplicate transport oid rejected '+group,lambda x,g=group:x['enforcement'][g].append(copy.deepcopy(x['enforcement'][g][0])),False)
transport=[]
for label,value in [('escaped duplicate','{"name":1,"na\\u006de":2}'),('deep duplicate','{"x":[{"a":{"k":1,"k":2}}]}'),('trailing comma','{"x":1,}'),('leading zero','{"x":01}'),('leading plus','{"x":+1}'),('truncated','{"x":'),('literal control','{"x":"\x01"}')]:
    valid,error=attempt(lambda v=value:decode(v));transport.append(dict(label=label,input=value,accepted=valid,error=error,passed=not valid))
# Large exponent is accepted by json.loads but cannot survive primitive validation.
x=canonical(raw);needle='"oid":'+str(raw['enforcement']['relations'][0]['oid']);assert needle in x
probe_value=decode(x.replace(needle,'"oid":1e400',1));v,e=attempt(lambda:validate_raw(probe_value));transport.append(dict(label='overflow exponent cannot reach normalization',accepted=v,error=e,passed=not v))
result={'schema':1,'scope':'additional model-input boundaries, not actual malformed PostgreSQL catalogs','total':len(results)+len(transport),'passed':all(r['passed'] for r in results+transport),'cases':results,'transport':transport}
pathlib.Path(a.out).write_text(json.dumps(result,indent=2,ensure_ascii=True)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['cases','transport']},indent=2));sys.exit(0 if result['passed'] else 1)
