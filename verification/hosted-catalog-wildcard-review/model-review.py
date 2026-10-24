#!/usr/bin/env python3
"""Reexecute frozen oracles and independently probe the two changed domains."""
import argparse,contextlib,copy,gzip,hashlib,importlib.util,io,json,os,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
PACKET=HERE/'frozen/verification/hosted-catalog-wildcard-correction'
ROOT=HERE.parents[1]
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def js(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def outcome(fn):
    try:fn();return True,None
    except ValueError as e:return False,str(e)
def execute():
    os.environ['MIXER_SHAPE_PACKET']=str(PACKET);sys.path.insert(0,str(PACKET/'candidate'))
    from inspector import decode,validate,normalize
    from raw_validation import validate_raw
    boundary=load('review_frozen_boundary',PACKET/'replay-boundaries.py').execute()
    recorded=js(PACKET/'attempt-1/models/receipt.json')
    assert all(canonical(v)==canonical(recorded[k]) for k,v in boundary.items())
    p=PACKET/'replay-extra-probes.py';code=p.read_text();footer="pathlib.Path(a.out).write_text(json.dumps(result,indent=2,ensure_ascii=True)+'\\n');print(json.dumps({k:v for k,v in result.items() if k not in ['cases','transport']},indent=2));sys.exit(0 if result['passed'] else 1)\n"
    assert code.endswith(footer);saved=sys.argv
    try:
        sys.argv=[str(p),'--packet',str(PACKET),'--out','unused-read-only'];ns={'__file__':str(p),'__name__':'review_extra_replay'};exec(compile(code[:-len(footer)],str(p),'exec'),ns)
    finally:sys.argv=saved
    extra=ns['result'];assert canonical(extra)==canonical(js(PACKET/'attempt-1/extra-models.json'))
    focused=load('review_frozen_focused',PACKET/'model-tests.py').execute();assert canonical(focused)==canonical(js(PACKET/'attempt-1/focused-models.json'))
    unique=load('review_frozen_unique',PACKET/'replay-name-uniqueness.py').execute();assert canonical(unique)==canonical(js(PACKET/'name-uniqueness-results.json'))
    raw=decode(gzip.decompress((PACKET/'inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz').read_bytes()))['raw'];expected=decode((PACKET/'selected-expected.json').read_bytes());validate(raw,expected)
    independent=[]
    def probe(label,x,raw_ok,selected_ok):
        before=canonical(x);rv,re=outcome(lambda:validate_raw(x));sv,se=outcome(lambda:validate(x,expected));unchanged=canonical(x)==before
        independent.append({'label':label,'expected_raw_valid':raw_ok,'expected_selected_admitted':selected_ok,'raw_valid':rv,'selected_admitted':sv,'raw_error':re,'selected_error':se,'input_unchanged':unchanged,'passed':rv==raw_ok and sv==selected_ok and unchanged})
    # Existing resolved-text domain deliberately has no new identifier length rule.
    names=[('*',True),('actual',True),('x'*64,True),('é'*64,True),('名'*256,True),(' ',True),('',False),(None,False),('\x00',False),('a\x00b',False),('\ud800',False),([],False),({},False),(False,False),(1,False)]
    for field in ['database','role']:
        for oid in [0,1,4294967295]:
            for name,valid in names:
                x=copy.deepcopy(raw);row={'database_oid':0,'database':'*','role_oid':0,'role':'*','config':['application_name=review']};row.update({field+'_oid':oid,field:name});x['enforcement']['startup_defaults']=[row]
                probe('association '+field+' '+repr((oid,name)),x,valid and (oid>0 or name=='*'),False)
        for oid in [False,True,-1,4294967296,1.0,None,'1']:
            x=copy.deepcopy(raw);row={'database_oid':0,'database':'*','role_oid':0,'role':'*','config':['application_name=review']};row.update({field+'_oid':oid,field:'*'});x['enforcement']['startup_defaults']=[row];probe('association OID type '+field+' '+repr(oid),x,False,False)
    for db_oid in [0,1,4294967295]:
        for role_oid in [0,1,4294967295]:
            x=copy.deepcopy(raw);x['enforcement']['startup_defaults']=[{'database_oid':db_oid,'database':'*','role_oid':role_oid,'role':'*','config':['application_name=review']}];probe('both star names '+repr((db_oid,role_oid)),x,True,False)
    ts=raw['enforcement']['triggers'];internal=next(i for i,t in enumerate(ts) if t['internal']);same_internal=next(i for i,t in enumerate(ts) if t['internal'] and i!=internal and t['relation_oid']==ts[internal]['relation_oid']);same_external=next(i for i,t in enumerate(ts) if not t['internal'] and t['relation_oid']==ts[internal]['relation_oid']);other=next(i for i,t in enumerate(ts) if t['relation_oid']!=ts[internal]['relation_oid'])
    for label,i,j in [('internal/internal',internal,same_internal),('internal/external',internal,same_external),('external/internal',same_external,internal)]:
        for reverse in [False,True]:
            x=copy.deepcopy(raw);x['enforcement']['triggers'][i]['name']=ts[j]['name']
            if reverse:x['enforcement']['triggers'].reverse()
            probe('same-pair '+label+' reverse='+str(reverse),x,False,False)
    # A second external row with a fresh OID still collides on the catalog key.
    for reverse in [False,True]:
        x=copy.deepcopy(raw);row=copy.deepcopy(ts[same_external]);row['oid']=4294967295;assert all(t['oid']!=row['oid'] for t in ts);x['enforcement']['triggers'].append(row)
        if reverse:x['enforcement']['triggers'].reverse()
        probe('same-pair external/external reverse='+str(reverse),x,False,False)
    for label,name in [('same name different relation',ts[other]['name']),('different name same relation','review_unique_internal')]:
        for reverse in [False,True]:
            x=copy.deepcopy(raw);x['enforcement']['triggers'][internal]['name']=name
            if reverse:x['enforcement']['triggers'].reverse()
            probe(label+' reverse='+str(reverse),x,True,True)
    for malformed in [[],{},None,False,'','\x00','x'*64,'\ud800']:
        x=copy.deepcopy(raw);x['enforcement']['triggers'][internal]['name']=malformed;probe('trigger name domain before pair '+repr(malformed),x,False,False)
    # Independently retain the old failing behavior as negative controls.
    old=load('review_old_raw',HERE/'frozen/verification/hosted-authority-catalog-shape-correction/candidate/raw_validation.py')
    controls=[]
    for field in ['database','role']:
        x=copy.deepcopy(raw);row={'database_oid':0,'database':'*','role_oid':0,'role':'*','config':['application_name=review']};row[field+'_oid']=1;x['enforcement']['startup_defaults']=[row]
        was,error=outcome(lambda:old.validate_raw(x));now,_=outcome(lambda:validate_raw(x));assert not was and now
        controls.append({'label':'ACSR01 old rejects positive literal star '+field,'predecessor_raw_valid':was,'corrected_raw_valid':now,'predecessor_error':error,'passed':True})
    for label,j in [('internal/internal',same_internal),('internal/external',same_external)]:
        x=copy.deepcopy(raw);x['enforcement']['triggers'][internal]['name']=ts[j]['name'];was,error=outcome(lambda:old.validate_raw(x));now,_=outcome(lambda:validate_raw(x));assert was and not now
        controls.append({'label':'ACSR02 old admits impossible pair '+label,'predecessor_raw_valid':was,'corrected_raw_valid':now,'predecessor_error':error,'passed':True})
    assert all(r['passed'] for r in independent) and all([boundary['passed'],extra['passed'],focused['passed']])
    return {'schema':1,'scope':'raw models, never claims actual impossible SQL catalogs or an authorization bypass','frozen_oracles':{'original_126':boundary['original_126'],'added_whole_shape':boundary['added_whole_shape'],'strict_transport':boundary['strict_transport'],'selected_portability':boundary['selected_portability'],'independent_extra_total':extra['total'],'focused_total':focused['total'],'uniqueness':unique},'independent_total':len(independent),'independent_cases':independent,'predecessor_negative_controls':controls,'all_passed':True}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();r=execute();pathlib.Path(a.out).write_text(json.dumps(r,indent=2,ensure_ascii=True)+'\n');print(json.dumps({'all_passed':r['all_passed'],'independent_total':r['independent_total'],'negative_controls':len(r['predecessor_negative_controls']),'original_model_counts':[126,1083,8,3,136,24,3]},indent=2))
