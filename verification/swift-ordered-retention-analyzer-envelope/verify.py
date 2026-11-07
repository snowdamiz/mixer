#!/usr/bin/env python3
"""Read-only producer seal check; does not execute a frozen runner/product."""
import hashlib
import json
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()
def main():
    seal=BASE/'seal.json';h=digest(seal);assert h==(BASE/'seal.sha256').read_text().strip()
    value=json.loads(seal.read_text())
    for m in value['members']:
        p=ROOT/m['path'];assert p.stat().st_size==m['bytes'] and digest(p)==m['sha256'],m['path']
    print(json.dumps(dict(sha256=h,members=len(value['members']),bytes=sum(m['bytes'] for m in value['members']),status='all-frozen-members-match-no-product-execution')))
if __name__=='__main__':main()
