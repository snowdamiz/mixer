#!/usr/bin/env python3
"""Seal only this independent source146 review; no tool/product execution."""
from pathlib import Path
import hashlib,json,platform,sys
HERE=Path(__file__).resolve().parent

def snapshot():
    ms=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p!=HERE/'seal.json':
            b=p.read_bytes();ms.append({'path':p.relative_to(HERE).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    r=json.loads((HERE/'review.json').read_bytes())
    return {'schema':1,'status':'frozen-'+r['status'],'member_count':len(ms),'member_bytes':sum(m['bytes'] for m in ms),'members':ms,'source_tree_sha256':r['source_tree_sha256'],'source_members':146,'host_members':11,'producer_seal_sha256':'1aacaaff5795625739811b2502476c22567c2b5a3bcc9fb096e61fa5c147c976','own_preaccess_seal_sha256':'f135ff01574b7597fcb467a571e8f912f6661d0740ba5974a453f13efe6010b7','independent_checks':r['checks'],'own_preaccess_checks':87,'full_definitions':219,'unchanged_full_definitions':218,'literal_only_count_change':1,'settled_actual_dereferences_composed':1456,'settled_actual_stores_composed':37,'baseline':r['baseline'],'whole_host_quote_or_operational_grant':False,'native_OTA_FieldLog_customer_GA':False,'new_compiler_or_runtime_execution':False,'python':platform.python_version(),'seal_command':[sys.executable,str(HERE/'freeze.py')]}

def main():
    b=(json.dumps(snapshot(),sort_keys=True,indent=2)+'\n').encode()
    if '--check-only' in sys.argv:
        if (HERE/'seal.json').read_bytes()!=b:raise AssertionError('independent packet changed')
    else:
        if (HERE/'seal.json').exists():raise AssertionError('refuse seal replacement')
        (HERE/'seal.json').write_bytes(b)
    s=json.loads(b);print(json.dumps({'passed':True,'seal_sha256':hashlib.sha256(b).hexdigest(),'member_count':s['member_count'],'member_bytes':s['member_bytes'],'mode':'check-only' if '--check-only' in sys.argv else 'freeze'}))
if __name__=='__main__':main()
