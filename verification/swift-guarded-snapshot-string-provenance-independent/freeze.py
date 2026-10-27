#!/usr/bin/env python3
"""Seal only the independent review directory; root selects nothing here."""
import datetime,hashlib,json,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
def main():
    assert not (D/'seal.json').exists()
    review=json.loads((D/'review.json').read_text());assert review['status']=='return-frozen-candidate-for-correction'
    assert not list(D.rglob('__pycache__'))
    cleanup={'schema':1,'compiler_or_product_started':False,'native_instances_started':False,'UI_or_capture_started':False,
       'native_cleanup_needed':False,'global_process_inventory':False,'other_projects_processes_preserved':True,
       'Git_root_metadata_source_frozen_input_writes':False,'only_owned_packet_written':True,
       'PYTHONDONTWRITEBYTECODE':'1','retained_failures':True,'no_runtime_or_GA_gate_closed':True}
    (D/'cleanup.json').write_text(json.dumps(cleanup,indent=2,sort_keys=True)+'\n')
    members=[]
    for p in sorted(D.rglob('*')):
        if not p.is_file() or p.name=='seal.json':continue
        b=p.read_bytes();members.append({'path':str(p.relative_to(D)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen-independent-return-for-correction',
       'candidate_seal_sha256':'b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f',
       'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
       'members':members,'member_count':len(members),'bytes':sum(x['bytes'] for x in members),
       'member_tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
       'candidate_accepted':False,'L_str_selected':False,'source_closure_selected':False,'whole_bound_selected':False,
       'operational_grant':False,'runtime_native_OTA_GA':False,'root_selection_required':True}
    output=json.dumps({'status':seal['status'],'member_count':seal['member_count'],'bytes':seal['bytes']},sort_keys=True)+'\n'
    seal['seal_command']={'argv':[sys.executable,'-B',str(pathlib.Path(__file__).resolve())],
        'python_version':sys.version,'python_executable_sha256':hashlib.sha256(pathlib.Path(sys.executable).read_bytes()).hexdigest(),
        'source_revision':'frozen-source146-exacttree-'+seal['source_tree_sha256'],'stdout':output,'stderr':'',
        'scope':'write only owned cleanup and seal; no child process or runtime','child_started':False,'PYTHONDONTWRITEBYTECODE':'1'}
    (D/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
    print(output,end='')
if __name__=='__main__':main()
