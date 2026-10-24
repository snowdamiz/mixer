#!/usr/bin/env python3
"""Independent actual identifier-domain counterexample and portable capture."""
import copy,gzip,hashlib,json,os,pathlib,sys,traceback
sys.dont_write_bytecode=True
SOURCE=pathlib.Path(os.environ['MIXER_REVIEW_SOURCE']);sys.path.insert(0,str(SOURCE))
source=(SOURCE/'frozen/tests.py').read_text();exec(compile(source[:source.index('def success(')],str(SOURCE/'frozen/tests.py'),'exec'),globals())
from inspector import inspect,validate,normalize,decode,canonical
from raw_validation import validate_raw
expected=decode(pathlib.Path(os.environ['MIXER_AUTHZ_EXPECTED']).read_bytes());captures=[]
def record(label,raw):
    b=(json.dumps({'label':label,'raw':raw},sort_keys=True,indent=2)+'\n').encode();p=OUT/f'{len(captures)+1:03d}.json.gz';p.write_bytes(gzip.compress(b,mtime=0));entry={'label':label,'path':p.name,'sha256':hashlib.sha256(b).hexdigest()};captures.append(entry);return entry
with DB('mixer_hosted_runtime') as runtime:raw=inspect(ADMIN,runtime)
validate(raw,expected);record('new OID padded baseline',raw)
prior=decode(gzip.decompress((OUT.parents[0]/'inputs/inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz').read_bytes()))['raw']
assert raw['enforcement']['relations'][0]['oid']!=prior['enforcement']['relations'][0]['oid']
assert sorted(t['name'] for t in raw['enforcement']['triggers'] if t['internal'])!=sorted(t['name'] for t in prior['enforcement']['triggers'] if t['internal'])
assert canonical(normalize(raw))==canonical(normalize(prior))
def asterisk_role():
    ADMIN.q('CREATE ROLE "*" NOLOGIN;GRANT "*" TO mixer_hosted_runtime')
    try:
        with DB('mixer_hosted_runtime') as r:before=inspect(ADMIN,r)
        validate_raw(before);record('actual asterisk role without defaults is well-typed',before)
        ADMIN.q('ALTER ROLE "*" IN DATABASE authority_contract SET application_name=review')
        with DB('mixer_hosted_runtime') as r:actual=inspect(ADMIN,r)
        record('actual positive role OID resolving asterisk name',actual)
        row=next(s for s in actual['enforcement']['startup_defaults'] if s['role']=='*');assert row['role_oid']>0
        try:validate_raw(actual)
        except ValueError as exc:error=str(exc)
        else:raise AssertionError('expected observed raw false rejection absent')
        assert 'wildcard association role' in error
        # Even correcting this raw check would leave a selected manifest mismatch.
        hypothetical=copy.deepcopy(actual);hypothetical['enforcement']['startup_defaults']=[]
        try:validate(hypothetical,expected)
        except ValueError as exc:other_mismatch=str(exc)
        else:raise AssertionError('extra reachable role should remain unselected')
        return {'finding':'ACSR01','actual_SQL':'CREATE ROLE "*" NOLOGIN; GRANT "*" TO mixer_hosted_runtime; ALTER ROLE "*" IN DATABASE authority_contract SET application_name=review',
                'actual_raw_row':row,'raw_validator_error':error,'other_selected_mismatch_after_removing_default':other_mismatch,'scope':'false rejection of valid unselected raw shape; no selected-safe admission change or runtime bypass'}
    finally:
        ADMIN.q('ALTER ROLE "*" IN DATABASE authority_contract RESET application_name;REVOKE "*" FROM mixer_hosted_runtime;DROP ROLE "*"')
case('actual quoted asterisk role exposes wildcard raw-domain collision',asterisk_role)
with DB('mixer_hosted_runtime') as r:final=inspect(ADMIN,r)
validate(final,expected);record('safe restoration after independent domain probe',final);ADMIN.close()
summary={'schema':1,'total':len(RESULTS),'passed':sum(r['passed'] for r in RESULTS),'failed':[r['name'] for r in RESULTS if not r['passed']],'captures':captures,'findings':[r['observation'] for r in RESULTS if r['passed']]}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));sys.exit(0 if not summary['failed'] else 1)
