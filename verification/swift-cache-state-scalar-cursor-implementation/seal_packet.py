#!/usr/bin/env python3
"""Seal this finite owned packet after fresh successful host qualification."""
import datetime,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=ROOT/'seal.json'
if seal.exists():raise SystemExit('existing seal is immutable; create another owned packet')
proof=json.loads((ROOT/'proofs/fresh-qualification.json').read_text());audit=json.loads((ROOT/'proofs/execution-product-audit.json').read_text())
if not proof['all_fresh_expected_host_dispositions_passed']or not audit['all_children_reaped']:raise SystemExit('fresh qualification incomplete')
members=[]
for p in sorted(ROOT.rglob('*')):
 if p.is_symlink():raise SystemExit('symlinks forbidden')
 if p.is_file()and p!=seal:members.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
d={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(ROOT/'seal_packet.py')],'python':sys.version,'builder_sha256':sha(ROOT/'seal_packet.py'),'member_base':'packet-relative','members':members,'member_count':len(members),'total_bytes':sum(r['bytes']for r in members),'source_sha256':sha(ROOT/'source/library/cache_state.rs'),'source_tree_digest':proof['source_tree_digest'],'status':'finite actual Rust host qualification complete; independent implementation review and root integration pending','fresh_qualified':True,'original_failures_and_timeout_preserved':True,'private_test_amendment_explicit':True,'compiler_version':'rustc 1.99.0 (b940084d7 2026-09-28)','modes':['debug','optimized'],'method_counts':[84,108,98],'distinct_methods_per_mode':122,'additional_private_methods_per_mode':3,'API_dispositions_per_mode':25,'actual_public_File_per_mode':29,'actual_private_poison_File_per_mode':2,'layouts_per_mode':23,'source_work_and_lifetime_selection_carried_by_exact_source':True,'independent_implementation_accepted':False,'canonical_integration_selected':False,'full_target_native_runtime_or_GA_qualified':False,'native_UI_capture_or_process_inventory_started':False}
seal.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'seal_sha256':sha(seal),'members':len(members),'bytes':d['total_bytes'],'source_tree_digest':d['source_tree_digest']},indent=2))
