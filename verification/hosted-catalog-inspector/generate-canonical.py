#!/usr/bin/env python3
import gzip,json,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'inputs/oracle'))
import inspector
values=['a','*','\\','"','/','\b','\f','\n','\r','\t','\x1f','\x7f','é','\uffff','😀','\u2028','𐀀','\u0080']
raw=json.loads(gzip.decompress((HERE/'inputs/baseline.json.gz').read_bytes()))
raw['enforcement']['parameter_acl']=[{'oid':i+1,'parameter':v,'acl':None,'entries':[{'grantor':g,'grantee':'*','privilege':'SET','grantable':False} for g in values]} for i,v in enumerate(values)]
result={'scalars':[{'value':v,'canonical':inspector.canonical(v)} for v in values+[{'é':'😀','a':'\\','*':'\n'}]],'raw':raw,'normalized_canonical':inspector.canonical(inspector.normalize(raw))}
(HERE/'inputs/canonical-vectors.json').write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n')
print(json.dumps({'scalar_vectors':len(result['scalars']),'normalized_vectors':1}))
