"""Exact84-query canonical serialization gate composed with frozen v3 rows.

This predicate does not establish native receiver identity when no event exists.
The independently frozen v3 input manifest pins actual raw/compact bytes.
"""
from pathlib import Path
import gzip,hashlib,importlib,json,sys,itertools
BASE=Path(__file__).resolve().parents[1]
STATE=BASE.parent
REPO=BASE.parents[3]
V3=STATE/'offline-reconciler-v3'
OUTPUT3=STATE/'offline-reconciler-run3'
RUN=STATE/'full-candidate-v1/run-33'
RECOVERY=STATE/'run33-single-state-recovery'
V3_SOURCE_SHA='969fb9ce4b3dbe806debb2b5124b6c0d9b176e89b55955b3c0fd72eda78d0c1f'
V3_OUTPUT_SHA='58ae832a2c8f42ca84c2646f7068a9c21a6841abb914dfda95f6614a7671597d'
LEDGER_SHA='e14e2fbeed50a822584f0c1a6e2418a300712c31df431789548e31ce84f4e85e'
FAMILIES=frozenset(('getCursorCapsMode','getSelectedText','getTextBeforeCursor','getTextAfterCursor','getExtractedText','getSurroundingText','takeSnapshot'))
STATES=frozenset(('current','successor','terminal','dirty','stale','changing','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'))

def need(condition,message):
 if not condition:raise ValueError(message)
def ident(p):
 d=p.read_bytes();return {'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()}
def selected_seal(path,expected):
 need(ident(path/'seal.json')['sha256']==expected,'exact external frozen dependency seal')
 seal=json.loads((path/'seal.json').read_bytes());need({str(p.relative_to(path))for p in path.rglob('*')if p.is_file()}=={'seal.json'}|{m['path']for m in seal['members']},'closed frozen dependency')
 for m in seal['members']:need(ident(path/m['path'])=={k:m[k]for k in('bytes','sha256')},'exact dependency member '+m['path'])

def load_audit():
 selected_seal(V3,V3_SOURCE_SHA);selected_seal(OUTPUT3,V3_OUTPUT_SHA)
 need(ident(OUTPUT3/'complete-proved-unresolved-ledger.json')['sha256']==LEDGER_SHA,'exact completed v3 ledger')
 sys.path.insert(0,str(V3/'code'));module=importlib.import_module('audit_selected_replay_v2');need(Path(module.__file__).resolve()==V3/'code/audit_selected_replay_v2.py','exact frozen v3 module path');return module

def canonical_query_gate(row,filename):
 need(type(row)is dict and type(filename)is str,'structured query row/file')
 family=row['family'];need(type(family)is str and family in FAMILIES and filename=='query-'+family+'.rows.jsonl.gz','only exact seven query file/family schemas')
 need(not row.get('historical_id')and 'original_attempt_close'not in row,'no historical/close schema fallback')
 authority=row['original_authority'];need(type(authority)is dict,'original query authority object');receiver=authority['receiver'];attempt=authority['attempt'];need(type(attempt)is dict and type(attempt.get('target'))is str and type(receiver)is str and receiver==attempt['target'],'original receiver equals actual attempt target as strings')
 prefix,separator,ordinal=receiver.partition('@');need(prefix=='android.view.inputmethod.BaseInputConnection'and separator=='@'and bool(ordinal)and ordinal[0]in'123456789'and all(c in'0123456789'for c in ordinal),'exact BaseInputConnection class and canonical positive decimal global identity')
 if 'original_target'in row:need(type(row['original_target'])is str and row['original_target']==receiver,'explicit query target cannot contradict original authority')
 return {'receiver':receiver,'attempt_target':attempt['target'],'canonical_serialization':True,'scope':'Canonical original authority serialization only; no native receiver credit without a selected actual event.'}

def actual_query_rows(module):
 for family in sorted(FAMILIES):
  path=RUN/('query-'+family+'.rows.jsonl.gz');compact=Path(str(path)+'.compact.jsonl')
  with gzip.open(path,'rt')as raw,compact.open()as small:
   for index,pair in enumerate(itertools.zip_longest(raw,small),1):
    need(all(x is not None for x in pair),'exact raw/compact query line count');yield path,index,module.loads(pair[0]),module.loads(pair[1]),pair

def run_gate():
 module=load_audit();audit=module.Audit(RUN,RECOVERY);ledger=module.loads((OUTPUT3/'complete-proved-unresolved-ledger.json').read_bytes());files={x['file']:x for x in ledger['files']if x['file'].startswith('query-')};need(set(files)=={'query-'+family+'.rows.jsonl.gz'for family in FAMILIES},'exact seven completed-v3 query files');seen=set();rows=[]
 for family in FAMILIES:
  name='query-'+family+'.rows.jsonl.gz';path=RUN/name;need(ident(path)=={k:files[name][k]for k in('bytes','sha256')}and module.same(ident(Path(str(path)+'.compact.jsonl')),files[name]['compact']),'same immutable query files as v3 ledger')
 for path,index,raw,compact,lines in actual_query_rows(module):
  key=(raw['family'],raw['state']);need(key not in seen and key[1]in STATES,'unique exact query state');seen.add(key);canonical=canonical_query_gate(raw,path.name);report=audit.row(raw,compact,{'file':path.name,'row':index});need(module.same(report,files[path.name]['rows'][index-1]),'same full v3 raw/compact row report, no evidence rewriting');rows.append({'file':path.name,'row':index,'family':raw['family'],'state':raw['state'],'canonical_identity_gate':canonical,'selected_events':report['selected_events'],'raw_line_sha256':hashlib.sha256(lines[0].encode()).hexdigest(),'compact_line_sha256':hashlib.sha256(lines[1].encode()).hexdigest(),'v3_report_unchanged':True})
 need(seen=={(family,state)for family in FAMILIES for state in STATES}and len(rows)==84,'all exact84 query rows')
 return {'schema':1,'status':'passed-focused84-canonical-query-plus-v3-raw-consistency; not-qualified','v3_source_seal_sha256':V3_SOURCE_SHA,'v3_output_seal_sha256':V3_OUTPUT_SHA,'v3_ledger_sha256':LEDGER_SHA,'rows':rows,'actual_query_rows':84,'selected_event_rows':sum(x['selected_events']>0 for x in rows),'zero_selected_event_rows':sum(x['selected_events']==0 for x in rows),'scope':'Mandatory addendum composition for this exact v3 output. It does not change raw/compact files or prove native receiver identity in zero-selected rows. Generic descriptor/outcome and semantic/runtime qualification remain pending.','qualified':False}
