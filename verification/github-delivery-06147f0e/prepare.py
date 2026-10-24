from pathlib import Path
import hashlib,json,subprocess
root=Path('/Users/andreyyurlov/Documents/dev/mixer');base=Path('/tmp/mixer-evidence-delivery');selected=set();seals=[]
for name,filename in [('apple-toggle-keyboard-focus-v4-runtime-analysis','analysis-seal.json'),('apple-toggle-keyboard-focus-v5-preparation','packet-seal.json'),('apple-toggle-keyboard-focus-v5-independent-review','review-seal.json'),('stripe-resource-linux-tool-payload-v3','seal.json'),('stripe-resource-linux-compiler-preparation','seal.json'),('stripe-resource-linux-compiler-metadata','seal.json')]:
 seal=root/'verification'/name/filename;d=json.loads(seal.read_text());selected.add(str(seal.relative_to(root)))
 for n,h in d['files'].items():
  p=root/n;assert p.is_file() and not p.is_symlink(),n;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,n;selected.add(n)
 seals.append({'path':str(seal.relative_to(root)),'sha256':hashlib.sha256(seal.read_bytes()).hexdigest(),'files':len(d['files'])})
for name in ['github-ci-2335207a-engine','github-ci-fdf59652-engine','github-delivery-fdf59652','apple-toggle-keyboard-focus-v5-root-review','ci-native-linux-checkpoint','stripe-webhook-resource-ingress-root-review/linux-tool-payload-v3-review']:
 for p in (root/'verification'/name).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:selected.add(str(p.relative_to(root)))
for n in ['PLAN.md','STATUS.md','THIRD_PARTY.yml','gates/ga.json','work-graph.json','verification/apple-toggle-keyboard-focus-v4-root-review/v5-preparation-selection.json','verification/apple-toggle-keyboard-focus-v4-root-review/runtime-analysis-check.stdout','verification/apple-toggle-keyboard-focus-v4-root-review/runtime-analysis-check.stderr']:
 selected.add(n)
for n in ['linux-compiler-metadata-selection.json','linux-compiler-metadata-review.json','linux-compiler-metadata-review.stdout','linux-compiler-metadata-review.stderr','review_linux_metadata.py','linux-compiler-metadata-v2-selection.json','linux-compiler-metadata-v2-export-addendum.json']:
 selected.add('verification/stripe-webhook-resource-ingress-root-review/'+n)
tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().strip('\0').split('\0'));dirty=set(subprocess.check_output(['git','diff','--name-only','-z'],cwd=root).decode().strip('\0').split('\0'))
selected={n for n in selected if n not in tracked or n in dirty};files={}
for n in sorted(selected):
 p=root/n;assert p.is_file() and not p.is_symlink(),n;b=p.read_bytes();assert len(b)<99_000_000,(n,len(b));files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'mode':'100755' if p.stat().st_mode&0o111 else '100644'}
m={'parent':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),'files':files,'validatedSeals':seals}
Path(str(base)+'-manifest.json').write_text(json.dumps(m,indent=2)+'\n');Path(str(base)+'-paths').write_bytes(b'\0'.join(n.encode() for n in files)+b'\0');print(json.dumps({'paths':len(files),'bytes':sum(v['bytes'] for v in files.values()),'seals':seals},indent=2))
