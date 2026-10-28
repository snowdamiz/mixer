"""Retrospective strict saved-stream policy; no subprocess or product execution.

Scoped implementation from independently frozen source/query bindings. It never
opens saved actual stderr: the separately released adapter supplies raw bytes.
"""
from pathlib import Path
import json
import re
import time

D = Path(__file__).resolve().parent
P = D.parent / 'swift-root-bound-work-storage-layout-preaccess'

class Refusal(ValueError): pass
def need(value, why):
    if not value: raise Refusal(why)
def unique(pairs):
    obj = {}
    for key, value in pairs:
        need(key not in obj, 'duplicate-JSON-key')
        obj[key] = value
    return obj
def constant(value): raise Refusal('nonfinite-JSON-constant')
def decode(raw):
    try: return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)
    except (UnicodeError,json.JSONDecodeError) as error: raise Refusal('malformed-JSON') from error
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()

BINDINGS = decode((P/'diagnostic-bindings-corrected.json').read_bytes())
POLICY = decode((D/'policy.json').read_bytes())
COORDS = ('byte_start','byte_end','line_start','line_end','column_start','column_end')

def same_range(span, expected):
    return all(type(span.get(k)) is int and span[k] == expected[k] for k in COORDS)

def validate_span(span):
    need(isinstance(span,dict),'span-not-object')
    name=span.get('file_name'); need(name in BINDINGS['staged_two_sources'],'span-source-not-frozen')
    text=BINDINGS['staged_two_sources'][name]; raw=text.encode()
    start,end=span.get('byte_start'),span.get('byte_end')
    need(type(start) is int and type(end) is int and 0<=start<end<=len(raw),'span-byte-range')
    try: before,selected=raw[:start].decode(),raw[start:end].decode()
    except UnicodeError as error: raise Refusal('span-character-boundary') from error
    sl=before.count('\n')+1;el=sl+selected.count('\n')
    sc=len(before.rsplit('\n',1)[-1])+1;ec=len((before+selected).rsplit('\n',1)[-1])+1
    for key,value in zip(COORDS,(start,end,sl,el,sc,ec)):
        need(type(span.get(key)) is int and span[key]==value,'span-coordinate-'+key)
    snippets=span.get('text');lines=text.splitlines()
    need(isinstance(snippets,list) and len(snippets)==el-sl+1,'span-excerpt-cardinality')
    for i,item in enumerate(snippets):
        need(isinstance(item,dict) and item.get('text')==lines[sl+i-1],'span-source-excerpt')
        first,last=item.get('highlight_start'),item.get('highlight_end')
        need(type(first) is int and type(last) is int and 1<=first<=last<=len(lines[sl+i-1])+1,'span-highlight-range')
        if i==0:need(first==sc,'span-highlight-start')
        if i==len(snippets)-1:need(last==ec,'span-highlight-end')
    return selected

def all_spans(value):
    if isinstance(value,list):
        for item in value:yield from all_spans(item)
    elif isinstance(value,dict):
        if 'file_name' in value and all(k in value for k in COORDS):yield value
        for item in value.values():yield from all_spans(item)

def primary(obj):
    spans=obj.get('spans');need(isinstance(spans,list),'missing-spans')
    need(all(isinstance(s,dict) for s in spans),'nonobject-span')
    found=[s for s in spans if s.get('is_primary') is True]
    need(len(found)==1,'primary-cardinality');return found[0]

def closure_spelling():
    row=BINDINGS['actual_closure']
    return '{closure@'+BINDINGS['closure_file']+':'+str(row['line_start'])+':'+str(row['column_start'])+': '+str(row['identity_end_line'])+':'+str(row['identity_end_column'])+'}'

def symbol_bindings():
    """Derive symbols from frozen full expressions, never from observed errors."""
    raw=BINDINGS['staged_two_sources'][BINDINGS['closure_file']].encode();rows=[]
    for query in BINDINGS['closure_queries']:
        expression=query['expression'];start=expression['byte_start'];end=start+19
        need(raw[start:expression['byte_end']].decode()==expression['text'],'frozen-full-expression-text')
        need(raw[start:end]==b'std::mem::transmute' and raw[end:end+1]==b'(','frozen-symbol-at-expression-start')
        before=raw[:start].decode();selected=raw[start:end].decode()
        sl=before.count('\n')+1;sc=len(before.rsplit('\n',1)[-1])+1
        symbol=dict(zip(COORDS,(start,end,sl,sl,sc,sc+len(selected))))
        rows.append({'operation':query['operation'],'expression':expression,'symbol':symbol,'symbol_text':selected})
    need(len(rows)==2 and {r['operation'] for r in rows}=={'size','alignment'},'frozen-symbol-roster')
    return rows

def named_value(obj):
    need(obj.get('message')=='mismatched types','E0308-message')
    span=primary(obj);exp=span.get('expansion')
    need(isinstance(exp,dict) and exp.get('macro_decl_name')=='pair!','exact-pair-expansion')
    invocation=exp.get('span');need(isinstance(invocation,dict),'pair-invocation')
    need(invocation.get('expansion') is None,'nested-pair-expansion')
    matches=[r for r in BINDINGS['named_queries'] if r['file']==span['file_name']==invocation['file_name'] and same_range(span,r['query_rhs']) and same_range(invocation,r['invocation'])]
    need(len(matches)==1,'exact-named-operation-expansion-binding');row=matches[0]
    definition=exp.get('def_site_span')
    if definition is not None:
        d=row['macro_definition']
        need(definition['file_name']==row['file'] and definition['line_start']==d['line_start'] and definition['byte_start']<=d['byte_start'] and definition['byte_end']>=d['byte_end'],'macro-definition-binding')
    match=re.fullmatch(r'expected an array with a size of 0, found one with a size of ([0-9]+)',span.get('label') or '')
    need(match is not None,'concrete-named-value');value=int(match[1]);need(0<value<2**64,'target-usize-named-value')
    for child in obj.get('children',[]):
        need(isinstance(child,dict) and child.get('code') is None and child.get('level')=='help' and child.get('message')=='consider specifying the actual array length' and child.get('children')==[],'unexpected-named-child')
    return row['id'],value

def closure_value(obj,symbols):
    need(obj.get('message')=='cannot transmute between types of different sizes, or dependently-sized types','E0512-message')
    span=primary(obj);need(span.get('expansion') is None,'closure-expansion')
    matches=[r for r in symbols if span['file_name']==BINDINGS['closure_file'] and same_range(span,r['symbol'])]
    need(len(matches)==1,'exact-anchored-19-byte-transmute-symbol');row=matches[0]
    need(validate_span(span)=='std::mem::transmute','transmute-symbol-text')
    children=obj.get('children');need(isinstance(children,list) and len(children)==2,'closure-note-cardinality')
    for child in children:
        need(isinstance(child,dict) and child.get('level')=='note' and child.get('code') is None and child.get('spans')==[] and child.get('children')==[],'closure-note-shape')
    notes=[c.get('message') for c in children]
    source=[n for n in notes if isinstance(n,str) and n.startswith('source type:')]
    target=[n for n in notes if n=='target type: `[u8; 0]` (0 bits)']
    need(len(source)==len(target)==1,'closure-source-target-cardinality')
    match=re.fullmatch(r'source type: `([^`]+)` \(([0-9]+) bits\)',source[0]);need(match is not None,'concrete-closure-bits')
    spell=closure_spelling();maybe=[p+spell+'>' for p in ['MaybeUninit<','std::mem::MaybeUninit<','core::mem::MaybeUninit<']]
    expected=maybe if row['operation']=='size' else ['ClosureAlignmentProbeV1<'+m+'>' for m in maybe]
    need(match[1] in expected,'actual-closure-wrapper-identity');bits=int(match[2]);need(bits>0 and bits%8==0,'positive-byte-closure-bits')
    return row['operation'],bits

def alignment(source,wrapper):
    need(type(source) is int and type(wrapper) is int and source>0 and wrapper>0,'positive-integer-bits')
    need(source%8==wrapper%8==0,'byte-bits');size=source//8;align=(wrapper-source)//8
    need(align>0 and align&(align-1)==0 and size%align==0,'concrete-closure-alignment')
    need(size<2**64 and align<2**64,'target-usize-closure-overflow')
    return {'size':size,'align':align,'source_bits':source,'wrapper_bits':wrapper}

def parse_diagnostics(stderr,stdout=b'',exit_code=1,deadline=None):
    def bounded():need(deadline is None or time.monotonic()<deadline,'parser-deadline')
    bounded();need(exit_code==1,'compiler-exit');need(stdout==b'','compiler-stdout')
    need(type(stderr) is bytes and 0<len(stderr)<=2097152,'stderr-bound')
    try:lines=stderr.decode('utf-8').splitlines()
    except UnicodeError as error:raise Refusal('malformed-UTF8') from error
    need(len(lines)==64 and all(lines),'complete-64-record-stream')
    warnings={};named={};closure={};summaries=set();symbols=symbol_bindings();span_count=0
    expected_warnings=[canonical(row['record']) for row in POLICY['warning_records']]
    need(len(expected_warnings)==len(set(expected_warnings))==3,'exact-three-warning-policy')
    for record_index,line in enumerate(lines):
        bounded();obj=decode(line);need(isinstance(obj,dict) and obj.get('$message_type')=='diagnostic','diagnostic-object')
        need(isinstance(obj.get('spans'),list) and isinstance(obj.get('children'),list),'diagnostic-spans-children-lists')
        for span in all_spans(obj):bounded();validate_span(span);span_count+=1
        level=obj.get('level');code=obj.get('code');code_name=code.get('code') if isinstance(code,dict) else None
        if level=='warning':
            key=canonical(obj);need(key in expected_warnings,'exact-source-bound-warning-object')
            index=expected_warnings.index(key);need(index not in warnings,'duplicate-warning-object');warnings[index]=True
            need(record_index==POLICY['warning_records'][index]['record_index'],'exact-warning-record-position')
        elif level=='error' and code_name=='E0308':
            key,value=named_value(obj);need(key not in named,'duplicate-named-operation');named[key]=value
        elif level=='error' and code_name=='E0512':
            key,value=closure_value(obj,symbols);need(key not in closure,'duplicate-closure-operation');closure[key]=value
        else:
            match=[i for i,row in enumerate(POLICY['summaries']) if canonical(obj)==canonical(row['record']) and record_index==row['record_index']]
            need(len(match)==1,'exact-summary-message-counts-and-shape');need(match[0] not in summaries,'duplicate-summary');summaries.add(match[0])
    need(set(warnings)=={0,1,2},'warning-cardinality')
    need(set(named)=={r['id'] for r in BINDINGS['named_queries']} and len(named)==56,'named-cardinality')
    need(set(closure)=={'size','alignment'} and len(summaries)==3,'closure-summary-cardinality')
    layouts=[]
    for index in range(0,56,2):
        row=BINDINGS['named_queries'][index];size,align=named[index],named[index+1]
        need(align>0 and align&(align-1)==0 and size%align==0,'named-layout-pair')
        layouts.append({'type':row['type'],'size':size,'align':align})
    actual=alignment(closure['size'],closure['alignment']);bounded()
    # All output candidates are constructed/returned only after the complete
    # stream, warnings, summaries, bindings and concrete arithmetic passed.
    return {'schema':1,'status':'RETROSPECTIVE_SAVED_RAW_LAYOUT_CANDIDATES_PENDING_INDEPENDENT_ROOT_REVIEW',
        'named_layout_candidates':layouts,'actual_closure_candidate':actual,'primary_E0308':56,'primary_E0512':2,
        'exact_source_bound_warnings':3,'summaries':3,'source_spans_verified':span_count,
        'original_contract_accepted':False,'retrospective_policy_applied':True,
        'layouts_accepted':False,'prices_backing_peak_funding_full_ownership_native_FieldLog_OTA_GA_accepted':False}
