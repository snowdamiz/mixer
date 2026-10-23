#!/usr/bin/env python3
import hashlib,io,json,pathlib,subprocess,tarfile
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
REVISION='3d4b88dd2eea3e26ce7ea87b3f78cb11631b410a'
SOURCE=OUT/'.local/source'
SOURCE.mkdir(parents=True)
args=['git','archive','--format=tar',REVISION,'sdk','capabilities','docs/capability-exit-observation-proposal.md']
data=subprocess.check_output(args,cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(data)) as stream:stream.extractall(SOURCE,filter='data')
manifest={p.relative_to(SOURCE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SOURCE.rglob('*')) if p.is_file()}
text=''.join(digest+'  '+name+'\n' for name,digest in manifest.items())
(OUT/'frozen-source.sha256').write_text(text)
(OUT/'freeze.json').write_text(json.dumps({'revision':REVISION,'git_tree':subprocess.check_output(['git','rev-parse',REVISION+'^{tree}'],cwd=ROOT,text=True).strip(),'command':args,'archive_sha256':hashlib.sha256(data).hexdigest(),'manifest_sha256':hashlib.sha256(text.encode()).hexdigest(),'files':len(manifest)},indent=2)+'\n')
print('Frozen',len(manifest),'committed files at',REVISION)
