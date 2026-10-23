import hashlib,io,json,pathlib,subprocess,tarfile
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[1]
revision='3d4b88dd2eea3e26ce7ea87b3f78cb11631b410a'
source=OUT/'.local/source';source.mkdir(parents=True)
command=['git','archive','--format=tar',revision,'sdk','capabilities']
archive=subprocess.check_output(command,cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as stream:stream.extractall(source,filter='data')
manifest={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.rglob('*')) if p.is_file()}
text=''.join(value+'  '+name+'\n' for name,value in manifest.items())
(OUT/'source.sha256').write_text(text)
(OUT/'freeze.json').write_text(json.dumps({'revision':revision,'git_tree':subprocess.check_output(['git','rev-parse',revision+'^{tree}'],cwd=ROOT,text=True).strip(),'command':command,'archive_sha256':hashlib.sha256(archive).hexdigest(),'manifest_sha256':hashlib.sha256(text.encode()).hexdigest(),'files':len(manifest)},indent=2)+'\n')
print('Frozen',len(manifest),'files at',revision)
