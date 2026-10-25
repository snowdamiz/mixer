"""Reconcile measured full owners with the frozen logical phase formulae."""
from pathlib import Path
import hashlib,json,re
P=Path(__file__).resolve().parent;F=P.parent/'swift-ordered-retention-diagnostic-completion'
def sha(raw):return hashlib.sha256(raw).hexdigest()
original=json.loads((F/'logical-inventory.json').read_bytes())
text=(P/'commands/layout-probe/stdout.txt').read_text()
values={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',text.splitlines()[0])}
assert values=={'path_buf':24,'string':24,'os_string':24,'option_os_string':24,'path_ref':16,'path_buf_align':8,'file':4,'file_result':16,'open_options':12,'path_construction':416}
path_counts={'path-construction':0,'initial-metadata-receipt':2,'header-construction':1,'writer-new-and-return':1,'begin-and-failed-begin-disposal':1,'callback':1,'release-result-and-returned-error':1,'consuming-cleanup-return':1,'footer':1,'retirement':1,'output-assembly':1,'final-custody-serialization':2,'serialization':2,'formatter-boundary-control':2,'abnormal-guard-drop':1,'after-drop-refusal-and-file-comparison':1,'post-retirement-row-reader':2,'post-retirement-parity-reader':4}
phases={}
for name,total in original['phases'].items():
    additions={'fullPathBufHeaders':path_counts[name]*values['path_buf']}
    if name=='path-construction':additions.update(fullConstructorOwnerAndBorrowGroup=values['path_construction'],secondFormattedNameAllocation=128)
    if name=='header-construction':additions['initialFileOwner']=values['file']
    if name=='writer-new-and-return':additions['completeSinkArgumentTransfer']=values['file']
    if name in ['initial-metadata-receipt','final-custody-serialization','serialization','formatter-boundary-control']:
        additions.update(receiptCreateFileResult=values['file_result'],receiptCreateOpenOptions=values['open_options'])
    if name=='after-drop-refusal-and-file-comparison':additions.update(twoFileOwners=2*values['file'],twoOpenResults=2*values['file_result'])
    if name=='post-retirement-row-reader':additions.update(fileOwner=values['file'],openResult=values['file_result'])
    if name=='post-retirement-parity-reader':additions.update(twoFileOwners=2*values['file'])
    corrected=total+sum(additions.values());assert corrected<=16384
    phases[name]={'frozenProvisional':total,'additions':additions,'corrected':corrected}
common=original['layout']['tls']+original['layout']['atomics']+502
open_roles={'common':common,'pathCapacityAndHeader':512+values['path_buf'],'beginRoleGroup':original['layout']['begin'],'threeFileTransferOwners':3*values['file'],'twoFileResults':2*values['file_result'],'twoOpenOptions':2*values['open_options'],'receiptLiteralCap':1024}
phases['initial-exclusive-file-open']={'frozenProvisional':0,'additions':open_roles,'corrected':sum(open_roles.values())}
assert phases['initial-exclusive-file-open']['corrected']<=16384
union_additions={'fullPathConstructionGroup':values['path_construction'],'twoFormattedNameCapacities':256,'twoOuterReturnedPathHeaders':2*values['path_buf'],'twoDerivedReceiptPathHeaders':2*values['path_buf'],'threeInitialFileTransferOwners':3*values['file'],'twoInitialFileResults':2*values['file_result'],'twoInitialOpenOptions':2*values['open_options'],'receiptCreateFileResult':values['file_result'],'receiptCreateOpenOptions':values['open_options'],'rowFileOwner':values['file'],'rowFileResult':values['file_result'],'twoParityFileOwners':2*values['file'],'twoParityFileResults':2*values['file_result'],'twoHeaderReaderFileOwners':2*values['file'],'twoHeaderReaderFileResults':2*values['file_result']}
peak=max(v['corrected'] for v in phases.values())
result={'scope':'six completion fixture paths and named logical source values only; opaque compiler/runtime internals unqualified','producerInventorySHA256':sha((F/'logical-inventory.json').read_bytes()),'probeSourceSHA256':sha((P/'layout-probe.rs').read_bytes()),'measuredOwnerLayouts':values,'phases':phases,'ceiling':16384,'correctedPeak':peak,'correctedMargin':16384-peak,'frozenProvisionalPeak':original['peak'],'frozenAllPhaseUnion':original['allPhaseNamedUnion'],'unionAdditions':union_additions,'correctedAllPhaseNamedRoleUnion':original['allPhaseNamedUnion']+sum(union_additions.values()),'unionIsSimultaneousPeak':False,'writerFileOwnersIncludedInCompleteWriter':True,'receiptFileOwnersIncludedInThreeCompleteReceiptWriters':True,'debugMaximumHelperDepth':7,'chargedDebugHelperLevels':8}
assert peak==16142 and result['correctedMargin']==242
(P/'inventory-supplement.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps({'correctedPeak':peak,'margin':16384-peak,'correctedAllPhaseNamedRoleUnion':result['correctedAllPhaseNamedRoleUnion'],'phases':len(phases)}))
