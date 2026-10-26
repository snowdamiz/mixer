#!/usr/bin/env python3
"""Freeze/verify only the new packet with packet-relative member paths."""
import argparse,hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args()
def digest(b):return hashlib.sha256(b).hexdigest()
def members():return [dict(path=str(p.relative_to(HERE)),bytes=p.stat().st_size,sha256=digest(p.read_bytes()))for p in sorted(HERE.rglob('*'))if p.is_file()and p.name!='seal.json']
actual=members()
if args.verify:
 d=json.loads((HERE/'seal.json').read_text())
 if d['members']!=actual:raise ValueError('frozen packet differs')
else:
 d=dict(schema=1,member_base='packet-relative',members=actual,total_bytes=sum(r['bytes']for r in actual),source_sha256=digest((HERE/'source/cache_state.rs.txt').read_bytes()),implementation_selected=False,independent_review_pending=True)
 (HERE/'seal.json').write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(members=len(actual),bytes=sum(r['bytes']for r in actual),seal_sha256=digest((HERE/'seal.json').read_bytes()),verified=True)))
