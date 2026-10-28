"""Synthetic whole streams only. Actual saved error diagnostics are never read."""
import copy
import json
import time
import io
from pathlib import Path
import parser as P
from input_bytes import read_pinned_bytes
from check import sha

D=Path(__file__).resolve().parent

def span(file,loc,label=None,expansion=None):
    lines=P.BINDINGS['staged_two_sources'][file].splitlines();snippets=[]
    for n in range(loc['line_start'],loc['line_end']+1):
        snippets.append({'text':lines[n-1],'highlight_start':loc['column_start'] if n==loc['line_start'] else 1,
            'highlight_end':loc['column_end'] if n==loc['line_end'] else len(lines[n-1])+1})
    return {'file_name':file,**{k:loc[k] for k in P.COORDS},'is_primary':True,'text':snippets,'label':label,'expansion':expansion}
def diagnostic(code,message,spans=None,children=None):
    return {'$message_type':'diagnostic','level':'error','code':{'code':code,'explanation':None},'message':message,'spans':spans or [],'children':children or [],'rendered':None}
def synthetic():
    rows=[]
    for row in P.BINDINGS['named_queries']:
        value=((row['id']//2)+1)*8 if row['operation']=='size' else 8
        expansion={'macro_decl_name':'pair!','span':span(row['file'],row['invocation']), 'def_site_span':span(row['file'],row['macro_definition'])}
        primary=span(row['file'],row['query_rhs'],'expected an array with a size of 0, found one with a size of '+str(value),expansion)
        # Three additional finite source geometries per named error exercise
        # secondary spans. No actual error record or numerical layout is read.
        secondary=[span(row['file'],row[key]) for key in ['query_rhs','invocation','macro_definition']]
        for item in secondary:item['is_primary']=False
        rows.append(diagnostic('E0308','mismatched types',[primary]+secondary))
    for row in P.symbol_bindings():
        shape='MaybeUninit<'+P.closure_spelling()+'>';bits=192
        if row['operation']=='alignment':shape='ClosureAlignmentProbeV1<'+shape+'>';bits=256
        children=[{'level':'note','code':None,'message':'source type: `'+shape+'` ('+str(bits)+' bits)','spans':[],'children':[]},
            {'level':'note','code':None,'message':'target type: `[u8; 0]` (0 bits)','spans':[],'children':[]}]
        rows.append(diagnostic('E0512','cannot transmute between types of different sizes, or dependently-sized types',[span(P.BINDINGS['closure_file'],row['symbol'])],children))
    for warning in P.POLICY['warning_records']:rows.insert(warning['record_index'],copy.deepcopy(warning['record']))
    rows.extend(copy.deepcopy(row['record']) for row in P.POLICY['summaries'])
    assert len(rows)==64
    return rows
def encode(rows):return ('\n'.join(json.dumps(row,sort_keys=True) for row in rows)+'\n').encode()
def named(rows,n=0):return [r for r in rows if (r.get('code') or {}).get('code')=='E0308'][n]
def closure(rows,n=0):return [r for r in rows if (r.get('code') or {}).get('code')=='E0512'][n]

def memory_controls(controls):
    expected={'bytes':292318,'sha256':'05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635'}
    # The separately observed pathname is deliberately always exact: the test
    # varies only the bytes returned by the fake reader. No actual raw is read.
    path_observation=dict(expected)
    for label,payload in [('wrong',b'x'*expected['bytes']),('short',b'x'*(expected['bytes']-1)),('overlong',b'x'*(expected['bytes']+8))]:
        reads=[];calls=0
        class Reader(io.BytesIO):
            def read(self,limit):reads.append(limit);return super().read(limit)
        def opener(mode):assert mode=='rb';return Reader(payload)
        assert path_observation==expected
        try:
            loaded=read_pinned_bytes(D/'never-read-actual',expected,time.monotonic()+1,opener=opener)
            calls+=1
            raise AssertionError('wrong memory would reach parser')
        except P.Refusal as error:
            assert calls==0 and reads==[expected['bytes']+1]
            controls.append({'name':'synthetic-'+label+'-memory-rejected-despite-correct-path-hash-zero-parser-calls','rejected':True,'reason':str(error),'parser_calls':0,'read_limit':reads[0]})
    payload=b'arbitrary synthetic memory fixture';expected={'bytes':len(payload),'sha256':sha(payload)};reads=[]
    class Reader(io.BytesIO):
        def read(self,limit):reads.append(limit);return super().read(limit)
    loaded=read_pinned_bytes(D/'never-read-actual',expected,time.monotonic()+1,opener=lambda mode:Reader(payload))
    assert loaded==payload and sha(loaded)==expected['sha256'] and reads==[len(payload)+1]
    controls.append({'name':'synthetic-exact-memory-returned-with-finite-read','passed':True})
    loaded=read_pinned_bytes(D/'never-read-actual',{'bytes':0,'sha256':sha(b'')},time.monotonic()+1,opener=lambda mode:io.BytesIO(b''))
    assert loaded==b''
    controls.append({'name':'synthetic-empty-stdout-memory-pinned','passed':True})
    try:read_pinned_bytes(D/'never-read-actual',expected,time.monotonic()-1,opener=lambda mode:(_ for _ in ()).throw(AssertionError('expired read must not open')))
    except P.Refusal:controls.append({'name':'synthetic-expired-memory-read-refuses-before-open','rejected':True})
    else:raise AssertionError('expired memory read accepted')

def main():
    start=time.monotonic();rows=synthetic();raw=encode(rows);controls=[]
    result=P.parse_diagnostics(raw,deadline=start+15)
    assert len(result['named_layout_candidates'])==28 and result['actual_closure_candidate']=={'size':24,'align':8,'source_bits':192,'wrapper_bits':256}
    assert result['source_spans_verified']==346
    assert result['layouts_accepted'] is False and result['original_contract_accepted'] is False
    def reject(name,mutate=None,**overrides):
        test=copy.deepcopy(rows)
        if mutate:mutate(test)
        try:P.parse_diagnostics(overrides.pop('stderr',encode(test)),**overrides)
        except P.Refusal as error:controls.append({'name':name,'rejected':True,'reason':str(error)})
        else:raise AssertionError('adverse stream accepted: '+name)
    for i,index in enumerate([0,1,14]):
        suffix='-W0'+str(i+1)
        reject('warning-missing'+suffix,lambda r,j=index:r.pop(j))
        reject('warning-duplicate-extra'+suffix,lambda r,j=index:r.append(copy.deepcopy(r[j])))
        reject('warning-duplicate-replaces-distinct'+suffix,lambda r,j=index:r.__setitem__(j,copy.deepcopy(r[[0,1,14][(i+1)%3]])))
        reject('warning-wrong-message'+suffix,lambda r,j=index:r[j].update(message='different warning'))
        reject('warning-wrong-code'+suffix,lambda r,j=index:r[j]['code'].update(code='unused_variables'))
        reject('warning-wrong-level'+suffix,lambda r,j=index:r[j].update(level='note'))
        reject('warning-wrong-source'+suffix,lambda r,j=index:r[j]['spans'][0].update(file_name='/proxy.rs'))
        reject('warning-wrong-byte'+suffix,lambda r,j=index:r[j]['spans'][0].update(byte_start=r[j]['spans'][0]['byte_start']+1))
        reject('warning-wrong-excerpt'+suffix,lambda r,j=index:r[j]['spans'][0]['text'][0].update(text='proxy source'))
        reject('warning-wrong-rendering'+suffix,lambda r,j=index:r[j].update(rendered='omitted rendering'))
        reject('warning-wrong-child'+suffix,lambda r,j=index:r[j]['children'][0].update(message='different child'))
        reject('warning-extra-field'+suffix,lambda r,j=index:r[j].update(extra='unexpected'))
        def suggestion(r,j=index):
            help=next(c for c in r[j]['children'] if c['level']=='help');help['spans'][0]['suggested_replacement']='proxy'
        reject('warning-wrong-suggestion'+suffix,suggestion)
    reject('unknown-fourth-warning',lambda r:r.append({'$message_type':'diagnostic','level':'warning','code':{'code':'unused_variables'},'message':'unknown','spans':[],'children':[]}))
    def swap_warning(r):r[0],r[2]=r[2],r[0]
    reject('warning-right-object-wrong-position',swap_warning)
    for n in range(2):
        suffix='-operation-'+str(n)
        reject('closure-symbol-shortened'+suffix,lambda r,j=n:closure(r,j)['spans'][0].update(byte_end=closure(r,j)['spans'][0]['byte_end']-1))
        reject('closure-symbol-shifted'+suffix,lambda r,j=n:closure(r,j)['spans'][0].update(byte_start=closure(r,j)['spans'][0]['byte_start']+1))
        def substitute(r,j=n,full=False):
            binding=P.symbol_bindings()[j];loc=binding['expression'] if full else dict(binding['symbol'],byte_start=binding['symbol']['byte_start']+5,column_start=binding['symbol']['column_start']+5)
            closure(r,j)['spans']=[span(P.BINDINGS['closure_file'],loc)]
        reject('closure-symbol-valid-geometry-substring'+suffix,substitute)
        reject('closure-symbol-full-expression-disallowed'+suffix,lambda r,j=n:substitute(r,j,True))
        reject('closure-wrong-operation-location'+suffix,lambda r,j=n:closure(r,j).update(spans=copy.deepcopy(closure(r,1-j)['spans'])))
        reject('closure-symbol-wrong-source'+suffix,lambda r,j=n:closure(r,j)['spans'][0].update(file_name='/proxy.rs'))
    for index in [61,62,63]:
        reject('summary-missing-'+str(index),lambda r,j=index:r.pop(j))
        reject('summary-duplicate-'+str(index),lambda r,j=index:r.append(copy.deepcopy(r[j])))
        reject('summary-wrong-message-'+str(index),lambda r,j=index:r[j].update(message='wrong summary'))
        reject('summary-nonempty-child-'+str(index),lambda r,j=index:r[j]['children'].append({'level':'note','message':'extra','spans':[],'children':[]}))
        reject('summary-wrong-code-'+str(index),lambda r,j=index:r[j].update(code={'code':'E0000'}))
    reject('summary-wrong-error-count',lambda r:r[61].update(message='aborting due to 57 previous errors; 3 warnings emitted'))
    reject('summary-wrong-warning-count',lambda r:r[61].update(message='aborting due to 58 previous errors; 2 warnings emitted'))
    reject('summary-warning-free-original-spelling',lambda r:r[61].update(message='aborting due to 58 previous errors'))
    reject('missing-named-error',lambda r:r.remove(named(r)))
    reject('duplicate-named-error',lambda r:r.append(copy.deepcopy(named(r))))
    reject('duplicate-named-replaces-other',lambda r:r.__setitem__(3,copy.deepcopy(named(r))))
    reject('missing-closure-error',lambda r:r.remove(closure(r)))
    reject('duplicate-closure-error',lambda r:r.append(copy.deepcopy(closure(r))))
    reject('unexpected-error-code',lambda r:named(r)['code'].update(code='E0000'))
    reject('ambiguous-primary',lambda r:named(r)['spans'].append(copy.deepcopy(named(r)['spans'][0])))
    reject('wrong-query-source',lambda r:named(r)['spans'][0].update(file_name='/different.rs'))
    reject('wrong-query-byte',lambda r:named(r)['spans'][0].update(byte_start=named(r)['spans'][0]['byte_start']+1))
    reject('wrong-query-highlight',lambda r:named(r)['spans'][0]['text'][0].update(highlight_start=1))
    reject('wrong-query-excerpt',lambda r:named(r)['spans'][0]['text'][0].update(text='proxy source'))
    reject('missing-pair-expansion',lambda r:named(r)['spans'][0].update(expansion=None))
    reject('wrong-pair-name',lambda r:named(r)['spans'][0]['expansion'].update(macro_decl_name='proxy!'))
    reject('wrong-pair-invocation',lambda r:named(r)['spans'][0]['expansion'].update(span=copy.deepcopy(named(r,2)['spans'][0]['expansion']['span'])))
    reject('wrong-macro-definition',lambda r:named(r)['spans'][0]['expansion'].update(def_site_span=copy.deepcopy(named(r,2)['spans'][0]['expansion']['span'])))
    for value in ['N','0',str(2**64)]:reject('nonconcrete-zero-overflow-named-'+value,lambda r,v=value:named(r)['spans'][0].update(label='expected an array with a size of 0, found one with a size of '+v))
    reject('nonpower-two-named-align',lambda r:named(r,1)['spans'][0].update(label='expected an array with a size of 0, found one with a size of 3'))
    reject('unexpected-named-child',lambda r:named(r)['children'].append({'level':'note','code':None,'message':'proxy','spans':[],'children':[]}))
    reject('closure-proxy-type',lambda r:closure(r)['children'][0].update(message='source type: `MaybeUninit<CaptureProxyV1>` (192 bits)'))
    reject('closure-wrong-physical-identity',lambda r:closure(r)['children'][0].update(message=closure(r)['children'][0]['message'].replace(P.closure_spelling(),'{closure@/different:1:1: 1:3}')))
    reject('closure-wrapper-wrong-physical-identity',lambda r:closure(r,1)['children'][0].update(message=closure(r,1)['children'][0]['message'].replace(P.closure_spelling(),'{closure@/different:1:1: 1:3}')))
    reject('closure-wrong-wrapper',lambda r:closure(r,1)['children'][0].update(message=closure(r,1)['children'][0]['message'].replace('ClosureAlignmentProbeV1','CaptureSum')))
    reject('closure-dependent-size',lambda r:closure(r)['children'][0].update(message=closure(r)['children'][0]['message'].replace('192 bits','size can vary')))
    reject('closure-nonbyte-size',lambda r:closure(r)['children'][0].update(message=closure(r)['children'][0]['message'].replace('192 bits','191 bits')))
    reject('closure-nonzero-target',lambda r:closure(r)['children'][1].update(message='target type: `[u8; 1]` (8 bits)'))
    reject('closure-ambiguous-source-note',lambda r:closure(r)['children'].append(copy.deepcopy(closure(r)['children'][0])))
    reject('closure-unexpected-note-span',lambda r:closure(r)['children'][0]['spans'].append(copy.deepcopy(closure(r)['spans'][0])))
    reject('malformed-json',stderr=b'not-json\n'*64)
    reject('invalid-utf8',stderr=b'\xff\n'*64)
    reject('duplicate-top-level-key',stderr=raw.replace(b'"level": "warning"',b'"level": "error", "level": "warning"',1))
    reject('duplicate-nested-code-key',stderr=raw.replace(b'"code": "unused_imports"',b'"code": "wrong", "code": "unused_imports"',1))
    reject('duplicate-nested-span-key',stderr=raw.replace(b'"file_name":',b'"file_name": "/proxy", "file_name":',1))
    reject('nonfinite-json',stderr=raw.replace(b'"explanation": null',b'"explanation": NaN',1))
    reject('nonempty-stdout',stdout=b'unexpected')
    reject('wrong-exit',exit_code=0)
    reject('expired-parser-deadline',deadline=time.monotonic()-1)
    reject('missing-valid-secondary-span-345-refused',lambda r:named(r)['spans'].pop())
    reject('extra-valid-secondary-span-347-refused',lambda r:named(r)['spans'].append(copy.deepcopy(named(r)['spans'][1])))
    reject('secondary-span-wrong-source',lambda r:named(r)['spans'][1].update(file_name='/proxy.rs'))
    reject('secondary-span-wrong-byte',lambda r:named(r)['spans'][1].update(byte_start=named(r)['spans'][1]['byte_start']+1))
    reject('secondary-span-wrong-highlight',lambda r:named(r)['spans'][1]['text'][0].update(highlight_start=1))
    reject('secondary-span-wrong-excerpt',lambda r:named(r)['spans'][1]['text'][0].update(text='proxy source'))
    for source,wrapper in [(0,8),(192,192),(192,184),(192,216),(192,193),(200,264),(2**70,2**70+64)]:
        try:P.alignment(source,wrapper)
        except P.Refusal as error:controls.append({'name':'invalid-concrete-arithmetic-'+str(source)+'-'+str(wrapper),'rejected':True,'reason':str(error)})
        else:raise AssertionError('adverse arithmetic accepted')
    memory_controls(controls)
    report={'schema':2,'status':'V2_SYNTHETIC_CONTROLS_ONLY_PASSED','positive_synthetic_streams':1,'positive_synthetic_span_count':346,'adverse_controls':[item for item in controls if item.get('rejected') is True],'positive_memory_controls':[item for item in controls if item.get('passed') is True],'adverse_controls_passed':sum(item.get('rejected') is True for item in controls),'total_controls':len(controls),
        'actual_saved_raw_parser_calls':0,'synthetic_sizes_are_not_product_observations':True,'layouts_accepted':False,'compiler_invocations':0,'child_workloads':0,'elapsed_seconds':time.monotonic()-start}
    with (D/'controls-result.json').open('x') as handle:json.dump(report,handle,indent=2,sort_keys=True);handle.write('\n')
    print(json.dumps({'status':report['status'],'adverse_controls':report['adverse_controls_passed'],'total_controls':report['total_controls'],'actual_saved_raw_parser_calls':0}))
    return report
if __name__=='__main__':main()
