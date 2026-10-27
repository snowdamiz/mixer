"""Read-only review, receipt, input and (when present) seal verification."""
import json
from common import *
def main():
 observed=inventory();recorded=json.loads((D/'custody.json').read_text())['files'];need(observed==recorded,'final input inventory')
 report=json.loads((D/'review.json').read_text())
 for command,path in report['qualifying_receipts'].items():
  out=D/Path(path).parent;r=json.loads((D/path).read_text());need(r['exit_code']==0 and r['owned_child_waited'] and r['inputs_unchanged'] and not r['timeout_occurred'],'qualifying outcome')
  need(sha((out/'inputs-before.json').read_bytes())==r['inputs_before_sha256'] and sha((out/'inputs-after.json').read_bytes())==r['inputs_after_sha256'],'receipt inventories')
  for stream in ('stdout','stderr'):need(sha((out/stream).read_bytes())==r[stream+'_sha256'],'qualifying output')
  # Only imported review modules authorize this receipt. Adding a different
  # independent checker never retroactively changes a completed test child.
  local_target=command.split()[0]
  deps=['common.py']+([local_target] if local_target in ('adverse.py','audit.py','custody.py') else [])
  for name in deps:need(sha((D/name).read_bytes())==r['review_scripts'][name]['sha256'],'same executed review dependency:'+name)
 for flag in ('L_str_selected','actual_P0_caller_selected','whole_host_budget_selected','policy_or_operational_grant_or_OTA_or_GA'):need(report[flag] is False,'scope flag')
 seal_path=D/'seal.json'
 if seal_path.exists():
  seal=json.loads(seal_path.read_text());names=[]
  for m in seal['members']:
   q=Path(m['path']);need(not q.is_absolute() and '..' not in q.parts,'member path');p=D/q;need(not p.is_symlink(),'symlink member');raw=p.read_bytes();need(len(raw)==m['bytes'] and sha(raw)==m['sha256'],'review member digest');names.append(str(q))
  need(len(names)==len(set(names))==seal['member_count'] and sum(m['bytes'] for m in seal['members'])==seal['bytes'],'review counts')
  need({str(p.relative_to(D)) for p in D.rglob('*') if p.is_file()}==set(names)|{'seal.json'},'review complete membership')
  need(all(p.stat().st_mode&0o222==0 for p in D.rglob('*') if p.is_file()),'read-only packet')
 print(json.dumps({'review_status':report['status'],'complete_input_files':len(observed),'qualifying_receipts':len(report['qualifying_receipts']),'seal_present':seal_path.exists(),'read_only':True,'authority':False},sort_keys=True))
if __name__=='__main__':main()
