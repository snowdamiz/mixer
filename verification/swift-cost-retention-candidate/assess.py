#!/usr/bin/env python3
"""Derive finite results from retained output; no engine execution."""
import hashlib,json,pathlib,re
OUT=pathlib.Path(__file__).resolve().parent
def write(name,value): (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def records(label,tag):
 text=(OUT/'commands'/label/'stdout').read_text()
 return [json.loads(s) for s in re.findall(re.escape(tag)+r' (\{[^\n]+\})',text)]
base={r['case']:r for r in records('baseline-final-swift','COST_TRACE')}
candidate={r['case']:r for r in records('candidate-expanded-2','COST_TRACE')}
assert base.keys()==candidate.keys() and len(base)==6
traces=[]
for name in base:
 a,b=base[name],candidate[name]
 traces.append({'case':name,'baseline':a,'candidate':b,'workRatio':b['traceWork']/a['traceWork'],'workChangePercent':100*(b['traceWork']-a['traceWork'])/a['traceWork'],'savedDecodes':a['decodes']-b['decodes']})
assert all(t['workRatio']>1 for t in traces)
commands=[]
for d in sorted((OUT/'commands').iterdir()):
 r=json.loads((d/'result.json').read_text());out=(d/'stdout').read_text()
 commands.append({'label':d.name,'result':r,'testResults':re.findall(r'test result: (?:ok|FAILED)\.[^\n]+',out),'sourceManifestSHA256':hashlib.sha256((d/'source-manifest.json').read_bytes()).hexdigest()})
parity=[]
for suffix in ['generic-unit','generic-integration']:
 a=(OUT/'commands'/('baseline-'+suffix)/'stdout').read_text();b=(OUT/'commands'/('candidate-'+suffix)/'stdout').read_text()
 norm=lambda s:re.sub(r'finished in [0-9.]+s','finished in <elapsed>s',s)
 assert norm(a)==norm(b)
 parity.append({'scope':suffix,'stdoutIdenticalAfterElapsedSecondsOnly':True,'normalizedSHA256':hashlib.sha256(norm(a).encode()).hexdigest()})
text=(OUT/'commands/candidate-expanded-2/stdout').read_text()
fields=[{'name':n,'offset':int(o),'bytes':int(b)} for n,o,b in re.findall(r'COST_FIELD name=(\w+) offset=(\d+) bytes=(\d+)',text)]
inventory=re.search(r'COST_INVENTORY bytes=(\d+) disjoint_copies=3 operation=(\d+)',text)
assert inventory and len(fields)==len(json.loads((OUT/'inventory-fields.json').read_text())['fields'])
assert all(f['offset']+f['bytes']<=int(inventory[1]) for f in fields)
write('result-summary.json',{'schema':1,'decision':'reject-this-candidate-for-live-integration-and-do-not-select-full-target','reason':'Every fixed finite trace uses more CacheWork, including a severe phase-shift regression; no policy was retuned.','independentReview':'not claimed or performed by producer','traces':traces,'baselineShape':records('baseline-final-swift','COST_SHAPE')[0],'candidateShape':records('candidate-expanded-2','COST_SHAPE')[0],'commands':commands,'genericParity':parity,'namedInventory':{'bytes':int(inventory[1]),'copies':3,'operationBytes':int(inventory[2]),'fieldCount':len(fields),'declaredFieldPayloadBytes':sum(f['bytes'] for f in fields),'fields':fields},'scope':'Finite Release host cache verification only; guest instruction counters remain zero. No full target/native/network/GA qualification.','limitsUnchanged':True})
print(json.dumps({'decision':'reject','traces':len(traces),'genericParity':True,'inventoryBytes':int(inventory[1]),'fieldCount':len(fields)}))
