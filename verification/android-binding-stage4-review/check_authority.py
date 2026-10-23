#!/usr/bin/env python3
"""Original compile-negative clients for the unchanged copied-source module."""
import argparse,hashlib,json,pathlib,subprocess,os
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--build',default='release');parser.add_argument('--name',default='authority-candidate-1');args=parser.parse_args()
OUT=HERE/args.name;OUT.mkdir(exist_ok=False)
build=HERE/'builds'/args.build; receipt=json.loads((build/'receipt.json').read_text())
argv=next(x['argv'] for x in receipt['commands'] if x['name']=='probe-link')
argv=argv[:argv.index(str(HERE/'ReviewProbes.swift'))]
argv=[x for x in argv if x not in ['-parse-as-library','-enable-testing','-O','-g']]
argv.insert(2,'-typecheck')
argv=[str(OUT/'swift-cache') if 'swift-cache' in x else x for x in argv]
cases={
 'readback-control':'func readback(_ value: CapabilityAndroidHostInstallation) -> CapabilityAndroidHostJoinStatus { value.status }',
 'host-to-common-installation':'func bad(_ host: CapabilityAndroidHostInstallation) { let _: CapabilityPresentationInstallation = host }',
 'host-to-common-status':'func bad(_ host: CapabilityAndroidHostJoinStatus) { let _: CapabilityPresentationJoinStatus = host }',
 'host-to-common-receipt':'func bad(_ host: CapabilityAndroidHostLifetimeReceipt) { let _: CapabilityPresentationLifetimeReceipt = host }',
 'host-to-common-gate':'func bad(_ host: CapabilityAndroidHostInstallation, _ gate: CapabilityPresentationBindingGate) { _ = gate.accept(host) }',
 'extract-lifetime':'func bad(_ host: CapabilityAndroidHostInstallation) { _ = host.lifetime }',
 'extract-permit':'func bad(_ host: CapabilityAndroidHostInstallation) { _ = host.permit }',
 'construct-key':'func bad(_ id: CapabilityPresentationLifetimeID) { _ = CapabilityAndroidHostLifetimeKey(facade: 1, lifetime: id, endpoint: 1) }',
 'construct-capsule':'func bad(_ key: CapabilityAndroidHostLifetimeKey, _ task: Task<Void, Never>, _ control: CapabilityAndroidLifetimeControl) { _ = CapabilityAndroidHostLifetimeCapsule(key: key, task: task, control: control) }',
 'construct-task-evidence':'func bad(_ key: CapabilityAndroidHostLifetimeKey) { _ = CapabilityAndroidHostTaskReturnEvidence(key: key) }',
 'construct-cleanup':'func bad(_ key: CapabilityAndroidHostLifetimeKey) { _ = CapabilityAndroidHostFacadeCleanupEvidence(key: key, cleanupSerial: 1, finalEntrySerial: 1, bridgeSlotGeneration: 1, clearedExchangeGeneration: nil, clearedResourceStageRevision: 1) }',
 'private-host-finish':'func bad(_ lifetime: CapabilityGuestUIPresentationLifetime, _ permit: CapabilityPresentationJoinPermit) async { _ = await lifetime.finishAndroidHost(using: permit) }'
}
result={'source_tree_sha256':receipt['source_tree_sha256'],'module':str(build/'MixerCapabilityActivation.swiftmodule'),'module_sha256':hashlib.sha256((build/'MixerCapabilityActivation.swiftmodule').read_bytes()).hexdigest(),'scope':'Original ordinary and @testable typecheck clients only. These do not authorize OTA or native execution. Guard audit remains a separate source review.','commands':[]}
for testable in [False,True]:
 for name,body in cases.items():
  if not testable and name=='readback-control':continue
  label=('testable-' if testable else 'ordinary-')+name
  source=OUT/(label+'.swift');source.write_text('import Foundation\n@_spi(GuestUIV1) import MixerGuest\n'+('@testable import ' if testable else 'import ')+'MixerCapabilityActivation\n'+body+'\n')
  command=argv+[str(source)]
  run=subprocess.run(command,cwd=ROOT,env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  log=OUT/(label+'.log');log.write_bytes(run.stdout)
  expected=0 if name=='readback-control' else 'nonzero'
  result['commands'].append({'name':label,'argv':command,'cwd':str(ROOT),'exit':run.returncode,'expected_exit':expected,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'log':str(log.relative_to(ROOT)),'log_sha256':hashlib.sha256(run.stdout).hexdigest()})
  if (expected==0)!=(run.returncode==0):raise RuntimeError(label+': '+run.stdout.decode())
  print(label,run.returncode)
result['result']='22 ordinary/testable rejection clients and one valid readback control behaved as required'
(OUT/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
