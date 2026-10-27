"""Fast read-only custody/artifact/receipt checks after the separate replays."""
from common import *
def main():
 current=custody();require(current==load(D/'input-custody.json'),'fresh complete immutable input closure')
 source_tables()
 compiler=load(V/'swift-guarded-snapshot-owned-provider-work-storage/commands/capture-layout/receipt.json')
 for artifact in compiler['artifacts']:
  if artifact['path']=='query.rmeta':continue
  archive=(V/'swift-guarded-snapshot-owned-provider-work-storage/commands/capture-layout'/(artifact['path']+'.gz')).read_bytes();raw=gzip.decompress(archive)
  require(len(archive)==artifact['gzip_bytes'] and sha(archive)==artifact['gzip_sha256'],'retained current compiler compressed artifact')
  require(len(raw)==artifact['bytes'] and sha(raw)==artifact['sha256'],'retained current compiler raw artifact')
 summary=load(D/'replay-summary.json');census=load(D/'constant-census.json')['stages'][-1]
 require(summary['conditional_envelope']==census['production']['conditional_conservative_envelope'],'current graph/census envelope agrees')
 require(not census['production']['unresolved_ids'] and not census['query_suffix']['unresolved_ids'],'zero unresolved IDs')
 require(load(D/'caller-contract.json')['source_tree_sha256']==TREES[3],'current caller tree')
 receipts=[]
 for folder in sorted((D/'commands').glob('host-*')):
  receipt=load(folder/'receipt.json');before=load(folder/'inputs-before.json');after=load(folder/'inputs-after.json')
  indexed={r['path']:r for r in current['members']}
  require(before==after and all(indexed.get(r['path'])==r for r in before['members']) and receipt['input_custody_unchanged'],'receipt input before/after custody; historical inventory is a preserved subset')
  require(receipt['child_reaped'] and receipt['owned_group_absent'],'owned cleanup observed:'+folder.name)
  require(receipt['compiler_invocations']==receipt['runtime_native_UI_capture_global_inventory_invocations']==0,'paused scope respected')
  for output in receipt['outputs']:require(row(output['path'],(folder/output['path']).read_bytes())==output,'receipt output:'+folder.name)
  for script in receipt['scripts']:require(row(script['path'],(folder/('source-'+script['path'])).read_bytes())==script,'exact archived script:'+folder.name)
  receipts.append({'path':str(folder.relative_to(D)),'success':receipt['success'],'exit_code':receipt['exit_code'],'elapsed_seconds':receipt['elapsed_seconds']})
 # Qualifying commands bind final dependencies. Successful preparations against
 # older script bytes remain history and cannot qualify the final checker.
 required={'rebind.py --check','replay.py --check','origins.py --check'}|{'test_rebind.py '+g for g in ('finite','identity','receiver','types','callbacks','census','local','literal','edge')}
 observed={}
 dependencies={'rebind.py':('common.py','rebind.py','run.py'),
  'replay.py':('common.py','rebind.py','replay.py','run.py'),
  'origins.py':('common.py','rebind.py','replay.py','origins.py','run.py'),
  'test_rebind.py':('common.py','rebind.py','replay.py','origins.py','test_rebind.py','run.py')}
 for folder in sorted((D/'commands').glob('host-*')):
  receipt=load(folder/'receipt.json');command=Path(receipt['argv'][2]).name+' '+ ' '.join(receipt['argv'][3:]);command=command.rstrip()
  if not receipt['success'] or command not in required:continue
  scripts={r['path']:r for r in receipt['scripts']}
  if all(scripts.get(n)==row(n,(D/n).read_bytes()) for n in dependencies[Path(receipt['argv'][2]).name]) and load(folder/'inputs-before.json')==current:observed[command]=folder.name
 require(set(observed)==required,'all final exact-script qualifying command groups:'+str(sorted(required-observed.keys())))
 print(json.dumps({'status':'read-only-input-artifact-receipt-check-pass','qualifying_groups':observed,'historical_failures_preserved':sum(not r['success'] for r in receipts),'current_summary':summary,'operational_grant':False},sort_keys=True))
if __name__=='__main__':main()
