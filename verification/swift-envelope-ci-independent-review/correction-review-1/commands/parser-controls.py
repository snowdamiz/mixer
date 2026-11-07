#!/usr/bin/env python3
"""Independent selected parser controls; no producer test or model import."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROUND=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
runner=ROUND/'portable-root/scripts/ci/check-analyzer-envelope.py'
if hashlib.sha256(runner.read_bytes()).hexdigest()!='4c56beec330b8118f01be3a6e7460f9857e4b1e8b61f29b4a9bce16fb6c1130c':raise RuntimeError('unadmitted parser')
spec=importlib.util.spec_from_file_location('independent_corrected_parser',runner)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
originals=ROUND/'parser-originals'
targets=json.loads((originals/'span-map.json').read_bytes())
versions=json.loads((originals/'versions.json').read_bytes())
inputs=ROUND/'parser-inputs';inputs.mkdir(exist_ok=True)
results=[]


def save_input(name,raw,suffix):
    path=inputs/(name+suffix)
    if path.exists():
        if path.read_bytes()!=raw:raise RuntimeError('case input changed')
    else:path.write_bytes(raw)
    return {'path':str(path.relative_to(ROUND)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def check(name,kind,expected,raw,action,meta=None):
    row={'name':name,'kind':kind,'expected_accept':expected,'input':save_input(name,raw,'.stderr' if kind=='diagnostic' else '.stdout'),**(meta or {})}
    try:
        value=action();row['accepted']=True
        if kind=='identity':row['observed_identity']=value
        else:row['observed_primary_spans']=[{'start':x['primary_span']['byte_start'],'end':x['primary_span']['byte_end'],'file':x['primary_span']['file_name'],'code':x['code']} for x in value]
    except Exception as error:row.update({'accepted':False,'error_type':type(error).__name__,'error':str(error)})
    row['passed']=row['accepted']==expected;results.append(row)


def identity(name,text,expected):
    check(name,'identity',expected,text.encode(),lambda:r.select_host_target(r.rustc_identity(text),{'host':'aarch64-apple-darwin','rust':'1.99.0'}))


for release,text in versions.items():identity('valid-identity-'+release,text,True)
base=versions['1.99.0']
fields=['binary','release','host','commit-hash','commit-date','LLVM version']
for key in fields:
    line=next(x for x in base.splitlines() if x.startswith(key+': '))
    identity('missing-'+key.replace(' ','-'),base.replace(line+'\n',''),False)
    identity('empty-'+key.replace(' ','-'),base.replace(line,key+': '),False)
    identity('duplicate-identical-'+key.replace(' ','-'),base+line+'\n',False)
    identity('duplicate-conflict-'+key.replace(' ','-'),base+key+': unselected\n',False)
identity('incoherent-release',base.replace('release: 1.99.0','release: 1.98.1'),False)
identity('incoherent-header-commit',base.replace('(b940084d7 ','(000000000 '),False)
identity('incoherent-header-date',base.replace('commit-date: 2026-09-28','commit-date: 2026-09-27'),False)
identity('invalid-calendar-date',base.replace('2026-09-28','2026-02-30'),False)
identity('short-full-commit-hash',base.replace('b940084d7eb6a299eb4bfeb8e34901bc051e7ac4','b940084d7'),False)
identity('nonhex-full-commit-hash',base.replace('b940084d7eb6a299eb4bfeb8e34901bc051e7ac4','g'*40),False)
identity('malformed-LLVM',base.replace('LLVM version: 23.1.1','LLVM version: unknown'),False)
identity('unknown-field',base+'unexpected: field\n',False)
identity('malformed-line',base+'missing separator\n',False)
identity('extra-blank-line',base+'\n',False)
identity('whitespace-value',base.replace('binary: rustc','binary: rustc '),False)
identity('installer-identity','rustup-init 1.99.0\n',False)
identity('unsupported-release',base.replace('1.99.0','1.98.2'),False)
identity('unsupported-host',base.replace('aarch64-apple-darwin','x86_64-apple-darwin'),False)
identity('unsupported-nightly',base.replace('1.99.0','1.99.0-nightly'),False)


def serialize(value):return ('\n'.join(json.dumps(x) for x in value)+'\n').encode()


def edit(original,action):
    value=[json.loads(x) for x in original.splitlines() if x.strip()]
    error=next(d for d in value if d.get('level')=='error' and d.get('code'))
    primary=next(s for s in error['spans'] if s.get('is_primary'))
    action(value,error,primary)
    return serialize(value)


normal_row={'exit':1,'timed_out':False,'child_returned':True,'owned_group_gone':True}
target_dir=ROUND/'absent-api-targets';target_dir.mkdir(exist_ok=True)
for probe in targets['probes']:
    name=probe['name'];source=originals/'api'/(name+'.rs')
    original=(originals/'diagnostics'/('api-negative-'+name+'.stderr')).read_bytes()
    def diagnostic(case,raw,expected=False,row=None,src=source):
        metadata={'probe':name,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'row':row or normal_row}
        check(name+'-'+case,'diagnostic',expected,raw,lambda:r.verify_negative(name,raw.decode(),src,target_dir/(name+'-absent'),row or normal_row),metadata)
    diagnostic('valid-real',original,True)
    diagnostic('wrong-leading-u',edit(original,lambda v,e,s:s.update(byte_start=0,byte_end=1)))
    diagnostic('wrong-file',edit(original,lambda v,e,s:s.update(file_name='api/unrelated.rs')))
    diagnostic('path-alias',edit(original,lambda v,e,s:s.update(file_name='api/./'+name+'.rs')))
    diagnostic('missing-primary',edit(original,lambda v,e,s:[x.update(is_primary=False) for x in e['spans']]))
    diagnostic('mixed-good-and-bad-primary',edit(original,lambda v,e,s:e['spans'].append({**s,'byte_start':0,'byte_end':1})))
    diagnostic('duplicate-primary',edit(original,lambda v,e,s:e['spans'].append(dict(s))))
    diagnostic('wrong-code',edit(original,lambda v,e,s:e.update(code={'code':'E0463'})))
    diagnostic('unrelated-message',edit(original,lambda v,e,s:e.update(message='unrelated compiler refusal')))
    diagnostic('extra-coded-error',edit(original,lambda v,e,s:v.append({**e,'code':{'code':'E0463'},'message':'missing library'})))
    diagnostic('nested-coded-error',edit(original,lambda v,e,s:e.setdefault('children',[]).append({'level':'error','code':{'code':'E0463'},'message':'nested missing library','spans':[]})))
    for label,value in [('bool',True),('float',float(probe['selected_primary_spans'][0]['byte_start'])),('string',str(probe['selected_primary_spans'][0]['byte_start'])),('null',None),('nan',float('nan')),('infinity',float('inf'))]:
        diagnostic('offset-'+label,edit(original,lambda v,e,s,value=value:s.update(byte_start=value)))
    diagnostic('nonbool-primary',edit(original,lambda v,e,s:s.update(is_primary=1)))
    diagnostic('nonstring-file',edit(original,lambda v,e,s:s.update(file_name=None)))
    diagnostic('reversed-span',edit(original,lambda v,e,s:s.update(byte_start=s['byte_end']+1)))
    diagnostic('empty-span',edit(original,lambda v,e,s:s.update(byte_end=s['byte_start'])))
    diagnostic('beyond-source',edit(original,lambda v,e,s:s.update(byte_end=len(source.read_bytes())+1)))
    diagnostic('children-object',edit(original,lambda v,e,s:e.update(children={})))
    diagnostic('spans-object',edit(original,lambda v,e,s:e.update(spans={})))
    diagnostic('boolean-message',edit(original,lambda v,e,s:e.update(message=True)))
    text=serialize([json.loads(x) for x in original.splitlines() if x.strip()]).decode()
    diagnostic('duplicate-top-key',text.replace('"level":','"level": "error", "level":',1).encode())
    diagnostic('duplicate-nested-key',text.replace('"byte_start":','"byte_start": 0, "byte_start":',1).encode())
    diagnostic('malformed-json',original[:len(original)//2])
    diagnostic('top-array',b'[]\n')
    diagnostic('top-null',b'null\n')
    for label,change in [('exit-zero',{'exit':0}),('signal',{'exit':-9}),('crash',{'exit':101}),('timeout',{'timed_out':True}),('unreturned-child',{'child_returned':False}),('live-group',{'owned_group_gone':False}),('outliving-descendant',{'descendants_outlived_direct_child':True})]:
        diagnostic('abnormal-'+label,original,row={**normal_row,**change})
    mutant=ROUND/'mutated-parser-sources'/name/'api'/(name+'.rs');mutant.parent.mkdir(parents=True,exist_ok=True)
    if not mutant.exists():mutant.write_bytes(source.read_bytes()+b'\n')
    diagnostic('mutated-source',original,src=mutant)
    if name=='no-observation-constructor':diagnostic('missing-one-selected-field',edit(original,lambda v,e,s:e['spans'].remove(s)))

summary={'schema':1,'label':a.label,'python_version':sys.version,'python_optimization':sys.flags.optimize,'admitted_parser_sha256':hashlib.sha256(runner.read_bytes()).hexdigest(),'scope':'Independent parser inputs from preserved real diagnostics/source/version bytes; no producer test/model/collector import; helper cases do not replace black-box or host execution.','case_count':len(results),'passed':sum(x['passed'] for x in results),'failed':[x['name'] for x in results if not x['passed']],'cases':results}
with (ROUND/('parser-'+a.label+'.json')).open('x') as stream:json.dump(summary,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({k:v for k,v in summary.items() if k!='cases'},sort_keys=True))
sys.exit(0 if not summary['failed'] else 1)
