"""Retain all original requirements; select only honestly related new methods."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent
producer=json.loads((ROOT/'verification/hosted-browser-relation-catalog/coverage.json').read_text())
attempts=[(p,json.loads(p.read_text())) for p in sorted((BASE/'attempts').glob('*/receipt.json'))]
selected={major:next(p for p,r in reversed(attempts) if r['major']==major and r['success']) for major in [16,17]}
names={major:[c['name'] for c in json.loads((p.parent/'checks.json').read_text())['checks']] for major,p in selected.items()}
selectors={
 'T02':['original deadline'], 'T03':['driver error','thrown diagnostic'],
 'T04':['genuine lifecycle','unchanged admin'],
 'R01':['full-boundary census'],
 'C03':['identity metadata'], 'C05':['inconsistent fast default'],
 'K01':['full-boundary census'], 'K03':['equality vector empty'],
 'K04':['numeric RI and index backlinks'], 'K05':['constraint trigger immediate'],
 'K06':['incoming RI wrong','numeric RI and index backlinks','incoming FK source'],
 'I01':['full-boundary census'], 'I04':['index collation numeric'],
 'G03':['constraint trigger immediate'],
 'G04':['function alias','settings vector 33'],
 'P03':['policy-role vector five'], 'P06':['policy-role vector five'],
 'A03':['explicit empty immutable'], 'A05':['owner raw ACL grant option'],
 'A06':['PUBLIC readonly','lifecycle sequence','tenant column-only'],
 'V01':['genuine lifecycle','full-boundary census'],
 'V03':['unqualified environment: version'],
 'V04':['numeric RI and index backlinks','index collation numeric'],
 'V05':['independent wire','independent scalar','policy-role vector five','settings vector 33'],
 'J04':['driver error','thrown diagnostic']
}
cases=[]
for case in producer['cases']:
    match=selectors.get(case['id'],[])
    direct={str(major):[name for name in methods if any(part in name for part in match)] for major,methods in names.items()}
    cases.append({'id':case['id'],'requirement':case['requirement'],'producer_method_mapping_audited':True,'producer_component_methods':case['component_methods'],'independent_methods':direct,'full_runtime_case_accepted':False,'remaining_limitations':case['limitations'],'review_scope':'Source and producer method mapping audited; listed direct controls are additional selected component evidence only.'})
assert len(cases)==48
(BASE/'coverage-review.json').write_text(json.dumps({'cases':cases,'full_runtime_cases_accepted':0,'scope':'Independent selected component review only. No Store/owner/conjunction/rollback/operational/end-to-end runtime case acceptance.'},indent=2,sort_keys=True)+'\n')
print('mapped 48 requirements; zero full runtime cases accepted')
