"""Independent complete member rehash plus original failed-receipt preservation."""
import json
from common import *
def main():
 files=inventory();s=json.loads((C/'seal.json').read_text());qualified=[]
 for command,path in s['qualifying_receipts'].items():
  r=json.loads((C/path).read_text());need(r['exit_code']==0 and r['owned_child_waited'] and not r['timeout_occurred'],'qualifying receipt')
  for row in r['script_members']:need(sha((C/row['path']).read_bytes())==row['sha256'],'same-script qualification')
  for suffix in ('stdout','stderr'):need(sha((C/Path(path).parent/suffix).read_bytes())==r[suffix+'_sha256'],'qualifying output')
  qualified.append(command)
 need(len(qualified)==15,'15 final qualifying commands')
 failures=json.loads((C/'correction-summary.json').read_text())
 for f in failures['current_failed_attempts_preserved']:
  r=json.loads((C/f['path']).read_text());need(r['exit_code']!=0 if 'exit_code' in r else r.get('status','')!='passed','failed attempt preserved')
 save('custody.json',{'schema':1,'packets':[{'path':n,'seal_sha256':h,'members':c,'bytes':b} for n,h,c,b in PACKETS],'files':files,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'qualifying_same_script_commands':sorted(qualified),'historical_and_current_failures_preserved':True,'compiler_or_runtime_or_native_reran':False,'L_str_or_policy_or_GA_selected':False})
 print(json.dumps({'complete_member_inputs':len(files),'frozen_packets':5,'same_script_qualifying_commands':len(qualified),'all_match':True}))
if __name__=='__main__':main()
