from pathlib import Path
import argparse,json,hashlib,subprocess,os
p=argparse.ArgumentParser()
for key in ('execution-manifest','execution-root','classes','java','output'):p.add_argument('--'+key,required=True,type=Path)
p.add_argument('--case');p.add_argument('--assemble',type=Path)
a=p.parse_args();root=a.execution_root
# Synthetic certificate values are parser/integrity fixtures, not product behavioral evidence.
m=json.loads((root/'matrix.json').read_bytes());m['execution_manifest_sha256']=hashlib.sha256(a.execution_manifest.read_bytes()).hexdigest();m['external_python_admission_sha256']=json.loads(a.execution_manifest.read_bytes())['external_python_admission_sha256']

a.output.write_text(json.dumps(m))
print('synthetic selected producer executed')
