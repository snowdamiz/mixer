#!/usr/bin/env python3
"""Snapshot the immutable correction packet before independent execution."""
import hashlib,json,pathlib,shutil
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/hosted-catalog-wildcard-correction'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
assert sha((PRODUCER/'receipt.json').read_bytes())=='cc82538ba0709c831cf2b0579109a93cd419a972318fb84576e8ec03071d295f'
files=json.loads((PRODUCER/'artifact-manifest.json').read_bytes())['files']
assert len(files)==96
extras=['verification/hosted-catalog-wildcard-correction/artifact-manifest.json','docs/hosted-catalog-wildcard-direction.md','docs/hosted-authority-catalog-shape-review.md','AGENTS.md','verification/hosted-authority-catalog-shape-correction/candidate/raw_validation.py']
entries=[]
for rel in [e['path'] for e in files]+extras:
    src=ROOT/rel; b=src.read_bytes(); dst=HERE/'frozen'/rel;dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists();dst.write_bytes(b)
    entries.append({'path':rel,'copy':str(dst.relative_to(HERE)),'bytes':len(b),'sha256':sha(b)})
save(HERE/'input-manifest.json',entries)
print(json.dumps({'snapshot_files':len(entries),'producer_bindings':len(files),'receipt_sha256':sha((PRODUCER/'receipt.json').read_bytes()),'candidate_source_digest':json.loads((PRODUCER/'receipt.json').read_bytes())['candidate_source_digest']},indent=2))
