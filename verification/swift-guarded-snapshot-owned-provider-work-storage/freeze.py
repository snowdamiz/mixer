#!/usr/bin/env python3
"""Freeze only this lane after successful source/host verification."""
from pathlib import Path
import datetime,hashlib,json,sys
sys.dont_write_bytecode=True
import check_packet
HERE=Path(__file__).resolve().parent
def main():
    assert not (HERE/'seal.json').exists(),'already immutable'
    verification=check_packet.validate(sealed=False)
    rows=check_packet.members();seal={'schema':1,'status':'frozen-producer-candidate-requires-fresh-independent-review','frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_tree_sha256':'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d','member_count':len(rows),'total_bytes':sum(r['bytes'] for r in rows),'member_table_sha256':check_packet.sha(check_packet.canon(rows)),'members':rows,'verification':verification}
    (HERE/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'seal_sha256':hashlib.sha256((HERE/'seal.json').read_bytes()).hexdigest(),'members':len(rows),'bytes':seal['total_bytes'],'status':seal['status']}))
if __name__=='__main__':main()
