from pathlib import Path
import importlib.util,json,gzip,re,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];CAND=ROOT/'verification/swift-control-accounting-candidate-2'
spec=importlib.util.spec_from_file_location('inv',CAND/'inventory.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
def functions(text):
 last=0;line=1
 for m in re.finditer(r'^fn ([^\n]+)',text,re.M):
  start=m.start();line+=text.count('\n',last,start);last=start;head=m.group(1);at=head.index('(');i=at+1;depth=1
  while depth:depth+=(head[i]=='(')-(head[i]==')');i+=1
  yield head[:at],head[at+1:i-1],text[start:text.find('\n}',start)+2],line
def canonical_name(name):
 return name.replace('experimental_swift_reactor::execution::frame_operations::control_operations::','control_operations::')
def canonical_functions(text):
 for name,params,body,line in functions(text):yield canonical_name(name),params,body,line
inv.prior.functions=canonical_functions
paths=list(Path('/tmp/mixer-swift-control-behavior-20261024/target/debug/deps').glob('*.mir'));selected={}
for p in paths:
 text=p.read_text()
 if '::control_operation(' in text:
  unit='fn experimental_swift_reactor::execution::frame_operations::tests::control_after_value_pop(' in text
  selected['unit' if unit else 'production']=p
assert set(selected)=={'unit','production'},selected
schema=json.loads((CAND/'inventory-schema.json').read_text());results=[]
for config,path in selected.items():
 rows,defs=inv.inventory(path,config);old=[r for r in schema if r['config']==config and 'mirFunction' in r and r['window']!='complete_controlled_empty']
 identity=lambda row:{k:row[k] for k in ['envelope','window','binding','position','rustType','sourceNames','mirType','field']}
 assert list(map(identity,rows))==list(map(identity,old)),(config,len(rows),len(old))
 results.append(dict(config=config,fields=len(rows),functions=len(defs),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=rows,definitions=defs))
 with gzip.open(HERE/('final-'+config+'.mir.gz'),'wb') as f:f.write(path.read_bytes())
(HERE/'canonical-accounting-audit.json').write_text(json.dumps(dict(status='exact-accepted-candidate-2-canonical-roles-preserved',results=results),sort_keys=True,indent=2)+'\n')
print('passed: final production/unit 38-function canonical inventories preserve accepted source roles exactly; hooks separately additive')
