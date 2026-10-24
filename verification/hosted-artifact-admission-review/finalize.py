#!/usr/bin/env python3
"""Archive exact retained review inputs and historical helper revisions."""
import hashlib,json,pathlib,shutil,tarfile
OUT=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
current=(OUT/'adversarial.exs').read_text()
old=current
start=old.index('    # Independently mutate every closed container\'s fields;')
end=old.index('    # Valid max uint64 values and exact JSON/CBOR integers beyond double precision.',start)
old=old[:start]+old[end:]
start=old.index('  def trace_calls(out,name,bytes,fun) do\n')
end=old.index('  def main(fpath,out) do\n',start)
old=old[:start]+old[end:]
start=old.index('    traced=[trace_calls(')
end=old.index('    File.write!(Path.join(out,"independent-observations.json"),',start)
old=old[:start]+old[end:]
for name,adversarial in [('run-1',old),('run-2',current)]:
 run=OUT/name;r=json.loads((run/'receipt.json').read_text());helpers=run/'helpers';helpers.mkdir(exist_ok=True)
 for rel,want in r['reviewHelpers'].items():
  dest=helpers/pathlib.Path(rel).name
  data=adversarial.encode() if dest.name=='adversarial.exs' else (OUT/dest.name).read_bytes()
  assert sha(data)==want,(name,dest.name)
  if dest.exists():assert dest.read_bytes()==data
  else:dest.write_bytes(data)
 inputs=run/'inputs';archive=run/'inputs.tar.gz';index=run/'input-archive.json'
 if not archive.exists():
  files={str(p.relative_to(run)):sha(p.read_bytes()) for p in sorted(inputs.rglob('*')) if p.is_file()}
  with tarfile.open(archive,'w:gz') as tar:
   for path in files:tar.add(run/path,arcname=path,recursive=False)
  with tarfile.open(archive,'r:gz') as tar:
   assert len(tar.getmembers())==len(files)
   for m in tar.getmembers():assert m.isfile() and sha(tar.extractfile(m).read())==files[m.name]
  index.write_text(json.dumps({'schema':1,'archiveSHA256':sha(archive.read_bytes()),'files':files,'cleanup':{'looseOriginalInputsRemovedAfterVerifiedLosslessArchival':True},'scope':'Original case payload, JSON, trusted-object ETF and observations remain byte-exact inside inputs.tar.gz; only public key material/signatures, never generated private keys.'},indent=2)+'\n')
  shutil.rmtree(inputs)
print('Archived lossless originals; matched both historical helper hashes; owned loose inputs removed.')
