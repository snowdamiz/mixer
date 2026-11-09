#!/usr/bin/env python3
"""Read-only guards for root's exact prospective application."""
from pathlib import Path
import argparse
import hashlib
import json
HERE=Path(__file__).resolve().parent
def need(ok,msg):
    if not ok: raise RuntimeError(msg)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def guard(root, installed=False):
    mapping=json.loads((HERE/'application-map.json').read_text())
    for row in mapping['full_mapping']:
        target=root/row['destination']
        if row['operation']=='retain-new-reviewed-file' and not installed:
            continue
        pin=row['sha256'] if installed else row['before_sha256']
        if pin is None: need(not target.exists(), 'Expected absent: '+row['destination'])
        else: need(target.is_file() and not target.is_symlink() and digest(target)==pin, 'Application hash differs: '+row['destination'])
    for row in json.loads((HERE/'metadata-map.json').read_text())['mapping']:
        before=(root/row['path']).read_text() if not installed else None
        staged=(HERE/'metadata'/row['path']).read_text()
        if before is not None:
            for change in row['replacements']:
                need(before.count(change['from'])==change['count']==1, 'Metadata replacement count differs')
                before=before.replace(change['from'],change['to'])
            need(before==staged, 'Metadata semantics differ')
        need(hashlib.sha256(staged.encode()).hexdigest()==row['sha256'], 'Staged metadata differs')
    return {'installed':installed,'checked_mapping_rows':len(mapping['full_mapping'])}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--installed',action='store_true')
    a=p.parse_args();print(json.dumps(guard(a.root,a.installed),sort_keys=True))
