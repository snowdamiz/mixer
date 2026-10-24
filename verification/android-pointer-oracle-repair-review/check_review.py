#!/usr/bin/env python3
"""Read-only recursive independent review seal replay, including nested seals."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def files():
    if HERE.is_symlink():raise ValueError('review root symlink')
    own=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_symlink():raise ValueError('review symlink')
        if path.is_file() and path != HERE/'artifact-seal.json':own.append(path)
    doc=ROOT/'docs/android-pointer-oracle-repair-review.md'
    if doc.is_symlink():raise ValueError('review document symlink')
    own.append(doc)
    return {str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(own)}

def check():
    seal=HERE/'artifact-seal.json';expected=json.loads(seal.read_text())
    if files()!=expected['files']:raise ValueError('exact recursive review membership/hash/size drift')
    return {'status':'passed-independent-pointer-oracle-repair-review-seal','files':len(expected['files']),'sealSHA256':sha(seal),'nativeDispatchAuthorized':False}

if __name__=='__main__':print(json.dumps(check(),indent=2,sort_keys=True))
