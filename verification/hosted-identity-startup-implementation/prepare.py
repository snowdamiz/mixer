#!/usr/bin/env python3
import hashlib,json,subprocess,tempfile,shutil
from pathlib import Path
O=Path(__file__).resolve().parent; R=O.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
scratch=Path(tempfile.mkdtemp(prefix='mixer-identity-startup-',dir='/private/tmp')).resolve()
shutil.copytree(R/'hosted',scratch/'hosted',ignore=shutil.ignore_patterns('_build','erl_crash.dump'))
shutil.copytree(R/'services/protocol/testdata',scratch/'services/protocol/testdata')
files={str(p.relative_to(R)):sha(p) for p in sorted((R/'hosted').rglob('*')) if p.is_file() and not {'deps','_build','__pycache__'}.intersection(p.relative_to(R).parts) and p.name!='erl_crash.dump'}
deps={str(p.relative_to(R)):sha(p) for p in sorted((R/'hosted/deps').rglob('*')) if p.is_file() and '_build' not in p.relative_to(R).parts}
def save(n,v):(O/n).write_text(json.dumps(v,indent=2)+'\n')
save('source-inputs.json',{'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'source':files,'dependencies':deps,'sourceDigest':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'dependencyDigest':hashlib.sha256(json.dumps(deps,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'dirtyDiff':subprocess.check_output(['git','diff','--','hosted'],cwd=R,text=True)})
save('state.json',{'scratch':str(scratch),'commands':[]})
print(scratch)
