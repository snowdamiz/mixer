#!/usr/bin/env python3
"""Deterministic source/model controls; never imports engine or test runners."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
BASE=ROOT/'verification/swift-guarded-snapshot-scope-authority-correction'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def main():
 checks=[]
 def check(name,ok,detail=None):
  assert ok,(name,detail);checks.append({'name':name,'detail':detail})
 manifest=json.loads((HERE/'source-manifest.json').read_text())
 for row in manifest['members']:
  overlay=HERE/'overlay/vm'/row['path']
  raw=(overlay if overlay.exists() else BASE/'source/vm'/row['path']).read_bytes()
  check('source-member-custody',len(raw)==row['bytes'] and sha(raw)==row['sha256'],row['path'])
 helper_path=HERE/'overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
 helper=helper_path.read_text();body=helper[helper.index('pub(super) fn '):]
 # Counts merely bind this manually expanded source-action convention; they
 # do not authorize admission or establish physical instruction counts.
 check('helper-four-checked-operations',body.count('.checked_mul(')==2 and body.count('.checked_add(')==2)
 check('helper-error-and-Result-actions',body.count('.ok_or(AError::Arithmetic)')==4 and body.count('?')==3)
 check('helper-two-field-fetches-three-bindings',body.count('shape.blocks')==1 and body.count('shape.extent')==1 and body.count('let ')==3)
 deriv=json.loads((HERE/'derivation.json').read_text())
 check('helper-price29',sum(v for k,v in deriv['helper_source_action_bound'].items() if k!='total')==deriv['helper_source_action_bound']['total']==29)
 check('encoder-ceiling-rederived',26+68*515+39*9*515+139*513+4096==291214)
 check('fixed-and-block-algebra',14224+1217+4096==19537 and 291214+4259+32*122==299377)
 caps=[67108864,512,8192,34,79966,8192,4096,4096,4096]
 widths=[0,3,1,5,3,4,4,4,4]
 for mask in range(512):
  counts=[caps[i] if mask&(1<<i) else 0 for i in range(9)]
  extent=2560+counts[0]+8*sum(n*w for n,w in zip(counts,widths))
  blocks=(extent+4095)//4096
  decomposed=14224+291214*blocks+1217+4259*blocks+122*(32*blocks)+32*extent+4096
  collapsed=19537+299377*blocks+32*extent
  check('component-algebra-cap-corner',decomposed==collapsed,[mask,extent,blocks])
 # Nonempty encoder/fill/attempt prefixes terminate on first error. The
 # candidate prices the whole planned E/B, not a fictitious repeated stream.
 for blocks,extent in [(1,2560),(2,4097),(3,8193),(17,65537),(17033,69765152)]:
  prefixes=sorted(set(range(0,min(blocks,32)+1))|{blocks})
  for prefix in prefixes:
   for attempts_per_block in (0,1,31,32):
    attempts=prefix*attempts_per_block
    for requested_fraction in (0,1,32):
     requested=requested_fraction*extent
     actual_upper=14224+291214*prefix+1217+4259*prefix+122*attempts+requested+4096
     check('first-error-prefix-envelope',prefix<=blocks and attempts<=32*blocks and requested<=32*extent and
        actual_upper<=19537+299377*blocks+32*extent,[blocks,prefix,attempts,requested_fraction])
 for residue in range(4096):
  extent=2560+residue;blocks=(extent+4095)//4096
  check('source-ending-alignment-envelope',19537+299377*blocks+32*extent==
    14224+1217+4096+blocks*(291214+4259+32*122)+32*extent,residue)
 run=json.loads((HERE/'run-results.json').read_text())
 check('recorded-host-and-metadata-expectations',run['all_expectations_met'] and len(run['cases'])==9)
 check('scratch-cleanup',run['all_owned_scratch_removed'] and not (HERE/'owned-work').exists())
 for case in run['cases']:
  folder=HERE/'commands'/case['case'];receipt=json.loads((folder/'receipt.json').read_text())
  check('command-receipt-custody',receipt['expectation_met'] and sha((folder/'stdout').read_bytes())==receipt['stdout_sha256'] and
     sha((folder/'stderr').read_bytes())==receipt['stderr_sha256'],case['case'])
 parent=(HERE/'overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text()
 base_parent=(BASE/'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs').read_text()
 inserted='// Additive unused candidate; WorkAuditPending below is unchanged.\nmod emission_bound_v1;\n\n'
 check('only-unused-module-added-to-parent',parent.replace(inserted,'')==base_parent and 'checked_snapshot_emission_bound_v1' not in parent)
 check('WorkAuditPending-kept',parent.count('Err(AError::WorkAuditPending)')==1)
 base_control=(BASE/'source/vm/src/experimental_swift_reactor/control.rs').read_bytes()
 control_row=next(x for x in manifest['members'] if x['path']=='src/experimental_swift_reactor/control.rs')
 check('entire-control-and-budget-literals-unchanged',sha(base_control)==control_row['sha256'] and b'execution_work: 1_000_000_000' in base_control)
 loader=(BASE/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs').read_text()
 check('loader-descriptor-mismatch-explicitly-pending','word(b, 32) != 144' in loader and 'word(b, 40) != 11' in loader and
    json.loads((HERE/'input-custody.json').read_text())['loader_descriptor_count_mismatch_pending']['candidate_source_members']==145)
 check('no-terminal-None-assumption', 'if final_block{break;}' in parent and parent.count('cursor.next_block(transfer)')==1)
 families={}
 for row in checks:families[row['name']]=families.get(row['name'],0)+1
 result={'schema':1,'checks_passed':len(checks),'checks_sha256':sha(canonical(checks)),
  'families':families,'source_members':145,'source_tree_sha256':manifest['source_tree_sha256'],
  'helper_sha256':sha(helper_path.read_bytes()),'candidate':'19537+299377B+32E','helper_actions':29,
  'source_integration':'unused private module only; actual WorkAuditPending body unchanged',
  'actual_writer_or_encoder_executed':False,'operational_emission_selected':False,
  'remaining':['independent emission review','new helper/callsite storage closure','exact planning/shell/inherited/caller/cleanup selection','final native and product gates']}
 path=HERE/'verification-results.json'
 if '--verify' in sys.argv:assert json.loads(path.read_text())==result
 else:path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'checks_passed':len(checks),'source_tree_sha256':manifest['source_tree_sha256'],
   'helper_sha256':result['helper_sha256'],'operational_emission_selected':False},sort_keys=True))
if __name__=='__main__':main()
