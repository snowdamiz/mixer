from pathlib import Path
import json,hashlib,tarfile,difflib,shutil,sys
P=Path(__file__).resolve().parent;S=P/'.scratch';manifest=json.loads((P/'baseline-source-manifest.json').read_text())
if len(sys.argv)>1:
 d=P/'history'/sys.argv[1];d.mkdir(parents=True,exist_ok=False)
 for n in ['candidate-source.tar.gz','candidate-manifest.json','candidate.patch','writer.rs','observer.rs','prepare.py']:
  shutil.copyfile(P/n,d/n)
f=S/'candidate/src/experimental_swift_reactor/cache_tests.rs';original=(S/'baseline/src/experimental_swift_reactor/cache_tests.rs').read_text();f.write_text(original+'\nmod ordered_wire {\n'+(P/'writer.rs').read_text()+'\n}\n'+(P/'observer.rs').read_text())
files={n:hashlib.sha256((S/'candidate'/n).read_bytes()).hexdigest() for n in manifest}
(P/'candidate-manifest.json').write_text(json.dumps(files,sort_keys=True,indent=2)+'\n')
with tarfile.open(P/'candidate-source.tar.gz','w:gz')as t:
 for n in manifest:t.add(S/'candidate'/n,arcname=n,recursive=False)
patches=[]
for n in manifest:
 a=(S/'baseline'/n).read_bytes();b=(S/'candidate'/n).read_bytes()
 if a!=b:patches.extend(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(P/'candidate.patch').write_text(''.join(patches))
print('candidate refreshed; complete132 archive/manifest/patch')
