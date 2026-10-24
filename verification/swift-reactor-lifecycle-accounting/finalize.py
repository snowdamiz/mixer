"""Freeze source/isolation/limits/coverage and observed compiler cleanup evidence."""
import collect as c
from pathlib import Path
import json,gzip,datetime,subprocess,difflib

def main():
 baseline=json.loads((c.HERE/'baseline-manifest.json').read_text());candidate=c.manifest(c.HERE/'candidate');closure=c.sha(c.enc(candidate))
 assert len(baseline)==130 and len(candidate)==132
 assert closure=='0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f'
 changed=[name for name,pin in candidate.items()if baseline.get(name)!=pin]
 assert set(changed)=={'src/experimental_swift_reactor/lifecycle.rs','src/experimental_swift_reactor/lifecycle_tests.rs','src/experimental_swift_reactor/memory_growth_operations.rs'}
 assert all(c.sha((c.ROOT/'vm'/name).read_bytes())==pin for name,pin in baseline.items())
 old=(c.HERE/'baseline/src/experimental_swift_reactor/memory_growth_operations.rs').read_text();new=(c.HERE/'candidate/src/experimental_swift_reactor/memory_growth_operations.rs').read_text()
 a=old[old.index('// ACCOUNTING_START'):old.index('pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES')]
 b=new[new.index('// ACCOUNTING_START'):new.index('pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES')]
 assert a==b
 c.save(c.HERE/'original-accounting-preservation.json',{'schema':'mixer.swift-lifecycle.original-accounting-preservation.1','originalGrowthPositionStructTextSHA256':c.sha(a.encode()),'candidateGrowthPositionStructTextSHA256':c.sha(b.encode()),'exactBytesPreserved':True,'allOther129BaselineFilesExact':True,'noPriorRoleCredit':True,'executionHeaderFormulaUnchanged':True,'frameFormulaUnchanged':True,'originalFrameCompletionFileUnchanged':True})
 c.save(c.HERE/'candidate-final-manifest.json',candidate)
 diff=[]
 for name in changed:
  before=(c.HERE/'baseline'/name).read_text().splitlines(True)if name in baseline else[]
  after=(c.HERE/'candidate'/name).read_text().splitlines(True)
  diff.extend(difflib.unified_diff(before,after,fromfile='baseline/'+name,tofile='candidate/'+name))
 c.save(c.HERE/'candidate-final.diff',''.join(diff).encode())
 selections=['AGENTS.md','mixer-product-plan.md','docs/swift-reactor-lifecycle-contract.md','verification/swift-reactor-lifecycle-contract/seal.json','verification/swift-reactor-lifecycle-contract/matrix.json','verification/swift-reactor-lifecycle-implementation/seal.json','verification/swift-reactor-lifecycle-contract-root-review/selection.json','verification/swift-reactor-lifecycle-contract-root-review/preparation-seam-amendment.json','verification/swift-reactor-lifecycle-contract-root-review/accounting-selection.json','verification/swift-reactor-lifecycle-contract-root-review/compiler-component-selection.json','verification/swift-reactor-lifecycle-contract-root-review/finite-position-selection.json','verification/swift-reactor-lifecycle-contract-root-review/additional-finite-position-selection.json']
 inputs={}
 for name in selections:
  data=(c.ROOT/name).read_bytes();c.save(c.HERE/'inputs'/name,data);inputs[name]=c.sha(data)
 c.save(c.HERE/'input-bindings.json',inputs)
 commands=[];cleanups=[];failed=[]
 for folder in sorted((c.HERE/'attempts').iterdir()):
  if not(folder/'command.json').exists():continue
  row=json.loads((folder/'command.json').read_text());cleanup=json.loads((folder/'cleanup.json').read_text())
  assert row['sourceUnchanged']and not row['remainingGroup']and cleanup['removed']and cleanup['holderCheckEmpty']and not cleanup['remainingGroup']
  entry={'attempt':str(folder.relative_to(c.HERE)),**row};commands.append(entry);cleanups.append({'attempt':entry['attempt'],'kind':'command-target',**cleanup})
  if row['exitCode']!=0:failed.append({'attempt':entry['attempt'],'argv':row['argv'],'exitCode':row['exitCode'],'stderrSHA256':row['stderrSHA256']})
  for name in ['overlay-cleanup.json','list-cleanup.json']:
   if(folder/name).exists():
    extra=json.loads((folder/name).read_text());assert extra['removed']and extra['holderCheckEmpty'];cleanups.append({'attempt':entry['attempt'],'kind':name,**extra})
 session=json.loads((c.HERE/'layout-tool-session.json').read_text());tool_cleanup=json.loads((c.HERE/session['preparation']/'final-cleanup.json').read_text());assert tool_cleanup['removed']and tool_cleanup['holderCheckEmpty']
 cleanups.append({'attempt':session['preparation'],'kind':'official-component-tool',**tool_cleanup})
 c.save(c.HERE/'command-index.json',commands);c.save(c.HERE/'failed-compiler-attempts.json',failed);c.save(c.HERE/'cleanup-summary.json',{'allOwnedScratchRemoved':True,'immediateCommandGroupsAllEmpty':True,'checks':cleanups,'logicalBytesRemoved':sum(r.get('logicalBytesRemoved',0)for r in cleanups),'filesRemoved':sum(r.get('filesRemoved',r.get('logicalFilesRemoved',0))for r in cleanups),'byteAccountingNote':'Logical file bytes removed, including read-only hard links; not measured recovered physical disk space.'})
 inventories=json.loads((c.HERE/'test-inventories.json').read_text());assert len(inventories)==4 and all(len(r['lifecycleTests'])==23 and r['testBodiesExecuted']==0 for r in inventories)
 layouts=json.loads((c.HERE/'paired-layouts.json').read_text());assert len(layouts)==8
 summary=json.loads((c.HERE/'reconciliation-summary.json').read_text());coverage=json.loads((c.HERE/'authored-coverage.json').read_text())
 limits={'State':134217728,'Combined':268435456,'ticketMaximum':86,'FrozenLogicalByteBoundUnchanged':2912}
 totals=[{'context':row['context'],'baseline':row['baseline']['totals'],'candidate':row['candidate']['totals']}for row in layouts]
 c.save(c.HERE/'limits-and-totals.json',{'originalByteCeilings':limits,'actualCompilerFormulaTotals':totals,'scope':'Exact formula component totals only. Retained source/metadata/cache/WASI, six arenas, growth overlap and runtime admission/peaks still require runtime evidence. No aggregate headroom/admission success is claimed.'})
 doc='''# Private Swift lifecycle accounting and authored test candidate

October 24, 2026. This isolated 132-file candidate has fresh compiler/accounting
and compile/list evidence. **accountingAccepted=false; runtimeSelected=false;
testsExecuted=0; GA accepted=false.** Root's independent accounting review is the
next gate. Full `mixer-product-plan.md` scope remains binding.

## Exact source and changed positions

The baseline live130 closure is
`3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3`.
The final candidate closure is
`0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f`.
The original compiler-only packet remains sealed at
`9ffa6cec71330bbad583340054add8dc0752ddaf85867deff71de09fe70ac72e`.
This packet is `verification/swift-reactor-lifecycle-accounting/`.

Only the isolated growth module and two new child modules differ from baseline.
The growth module retains the selected shared preparation/completion helpers,
adds the private lifecycle child, and adds the named lifecycle components to its
existing `PERMANENT_BYTES`/`ACTIVE_BYTES`. Every byte of both original growth
position structs is preserved. All other129 baseline files are exact, including
execution header/frame formulas, owner declarations/fields, original frame
completion, all prior V7 roles and shared Frozen source. No outside fixture,
feature/dependency, ceiling, ticket, public API or C ABI changes.

The lifecycle's `execute_phase` frame performs actual entry/run/final observed
check/release/drain and ends before consuming completion. Its new positions are
active. Request/precondition and shared preparation/completion frames span
admission/restoration and have permanent coverage, including bootstrap,
retained/full-return and final caller wrappers. Every compiler local including
return/arguments, authored/captured alias and constant operand receives four
disjoint source/argument/returned/caller roles. Positions from all eight compiler
contexts form a conservative named union; they are new positive positions, with
no prior-row reuse, optimizer/peak subtraction, pointer/type surrogate, padding
credit or extra ticket. Bounds are logical named objects, not physical stack/RSS.

Discovery and final inventories both contain21,364 roles over268 runtime bodies:
21,076 exact-typed,32 inferred-never and256 exact selected finite positions.
The original248 numeric rows and supplemental8 private RawVecInner-borrow rows
were independently selected by root before installation. Each numeric row binds
its exact actual type identity/full layout, config, body/local/capture/operand,
role and query. Checked aligned disjoint offsets remain separate from typed
compiler witnesses. No generic private/closure fallback is accepted.

Final compiler reconciliation records96 changed full-body SHA values and7,216
changed sourceInfo positions, preserving every before/after binding. There are
zero added/removed runtime positions and zero actual type/layout changes. The
only method changes are the8 specifically selected private RawVecInner borrows.
21,416 exact typed/never witnesses bind final actual compiler field identities;
whole retained-source carriers are checked in each context. Complete function
item records retain exact FnDef identities and actual zero-byte layouts; no
function-pointer surrogate is substituted.

Generation adds384 compiler-only anonymous array-length bodies beneath exact
`LifecyclePermanentPositions` parent fields. Every full body is retained and
matched to the actual compiler declaration, exact field, reference-to-Array type
graph, length6, sole usize return/operand, and absence of any FnDef or call.
These are type annotations, with zero runtime byte credit; there is no generic
suffix-only exemption. See `annotation-const-proofs.json.gz`.

## Compiler-observed additions and unchanged limits

All16 baseline/candidate owner/formula layout contexts pass. Original owners and
original growth position sizes/fields/offsets remain unchanged in every pair.
Swift/all and Debug/Release agree on these exact logical formula totals:

| Context | Baseline header | Added permanent | Final header | Baseline frame | Added active | Final frame |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Production | 3,000,136 | 3,464,856 | 6,464,992 | 15,357,688 | 489,744 | 15,847,432 |
| Unit | 4,867,456 | 6,826,664 | 11,694,120 | 30,028,176 | 1,250,632 | 31,278,808 |

State remains134,217,728 bytes (128MiB); Combined remains268,435,456 bytes
(256MiB); the maximum remains86 tickets. The2912-byte Frozen contract remains
unchanged;39 expanded Frozen methods are byte-identical in fresh baseline and
candidate compiler outputs. Those are unchanged contracts and compiler evidence,
not a newly executed Frozen or physical-device regression.

These totals are individual formula components. Other retained categories, six
arenas and maximum growth overlap still consume their original budgets. This
packet makes no measured current/peak, aggregate headroom, runtime admission,
allocator-success, deadline/performance, or release-size claim. A subsequent
runtime failure must retain its actual exhausted dimension and existing ceilings.

## Observed compiler/list evidence and preserved failures

Fresh final production/unit MIR and exact type/layout queries pass for Swift/all
× Debug/Release. Sixteen compiler-only overlays append an uninstantiated formula
declaration, with exact prefix/source projections; they run no metadata binary
or test. Both scoped production Clippy commands pass with `-D warnings` and both
new files pass rustfmt check. Two fresh official compiler expansions preserve all
39 Frozen methods exactly. Original unit Copy-drop warnings in unchanged
control fixtures remain visible in captured output; they were not edited.

Four exact fresh unit binaries list the23 named `swift_lifecycle_sl01_` through
`swift_lifecycle_sl23_` identities. Swift binaries list335 total tests; all-feature
binaries list365. Each binary hash, source closure, Cargo artifact and literal
`--list` argv/output is retained. **No test body or VM has executed.** Listing
proves inventory, not assertions or behavior.

Failures are preserved: initial test-enum spelling (Trap→GuestTrap), a metadata
reader's unsupported dyn Debug graph, unit-only inferred-never generic scoping,
and8 unnameable private RawVecInner typed declarations. The metadata reader now
uses actual compiler dynamic-trait definitions/arguments; the unit-only never
class/inference helper is cfg(test), with no phantom surrogate; the8 private
borrows use only root's exact supplemental selection. No discarded failure is
reported as a successful run.

Official Rust/Cargo1.99.0, LLVM23.1.1 and Python3.14.8 on aarch64-apple-darwin are
bound by executable/compiler-library hashes, versions, exact commands, source
archives/manifests, raw compressed outputs and cleanup. The same exact official
rustc-dev component was hash-verified and used in an isolated read-only-linked
sysroot. No shared installation changed. The owned component, driver, command
targets, layout overlays and list-only binary copies were removed after empty
holder/group checks. Logical removed bytes include hard links and do not claim
measured physical disk recovery.

The private constructor precondition remains
`control.as_mut().expect("constructed control")`. Missing unique control is not
converted into a fabricated diagnostic or replacement authority. Other original
preparation failures retain their actual cause and terminalize only through the
selected closed lifecycle preparation goal.

## Entire authored coverage ledger and remaining planned cases

The original sealed matrix is copied byte-for-byte as
`planned-matrix-unchanged.json`. Each row below describes authored subcases and
all remaining limitations from `authored-coverage.json`. **None is passed.** A
later scoped runtime success cannot mark an entire planned SL row complete.

| Row | Authored subcases, unrun | Remaining cases/limitations |
| --- | --- | --- |
'''
 for row in coverage['rows']:
  esc=lambda text:text.replace('|','\\|')
  doc+=f"| {row['id']} | {esc(row['authored'])} | {esc(row['remaining'])} |\n"
 doc+='''
SL12 explicitly proves only authored memory/global persistence and repeated
indirect reads through an unchanged original table. Guest table mutation remains
unsupported/unrun by the selected engine. The full commercial product scope has
not been narrowed. SL24 exact-target work is unselected; the retained full reactor
was never read, hashed or run.

## Replay and pending acceptance

```sh
python3 -B verification/swift-reactor-lifecycle-accounting/verify.py --live
```

Archive-only replay omits `--live`; neither route compiles or runs guest code.
Exact future runtime commands must bind these concrete binaries and authored
subcases, select a nonzero exact set, and preserve the complete remaining ledger.
The full libraries/default/span/Frozen runtime regressions, allocation/failure
permutations, unsupported table mutation and other planned cases remain open.

There is no live integration, VM/test execution, full-target read/hash/run,
native/device run, publication, customer message, migration, credential or
provider action. Physical phones stay disconnected and deferred to final
acceptance. Simulator/emulator authorization is not exercised here. FieldLog
still needs immutable published packages from a separate repository. No D3,
G07/G08, dogfood-release, store, customer/operations or GA gate is accepted.
'''
 doc_path=c.ROOT/'docs/swift-reactor-lifecycle-accounting.md';c.save(doc_path,doc.encode())
 receipt={'schema':'mixer.swift-lifecycle.accounting-compiler-slice.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevisionContextSuppliedByRoot':'fdf59652a603d854facdde4550e0fd9e73a8516e','baselineClosure':c.sha(c.enc(baseline)),'candidateClosure':closure,'candidateFileCount':132,'changedFiles':changed,'priorCompilerPacketSealSHA256':inputs['verification/swift-reactor-lifecycle-implementation/seal.json'],'freshCompilerContexts':8,'pairedCompilerLayouts':16,'exactPositionRoles':21364,'runtimeBodies':268,'actualTypeOrLayoutChanges':0,'bodySHA256Changes':96,'sourceInfoPositionChanges':7216,'exactSupplementalMethodChanges':8,'typedAndNeverWitnesses':21416,'finitePositions':256,'fullCTFEAnnotationProofs':384,'freshListOnlyBinaries':4,'namedLifecycleTestsPerBinary':23,'testBodiesExecuted':0,'vmExecutions':0,'fullTargetReadHashedOrRun':False,'nativeInstancesCreated':0,'liveVMModified':False,'accountingAccepted':False,'runtimeSelected':False,'gaAccepted':False,'originalByteCeilings':limits,'formulaTotals':totals,'commands':len(commands),'preservedFailedCompilerAttempts':len(failed),'allOwnedScratchRemoved':True,'coverageLedger':coverage,'coverageLedgerSHA256':c.sha((c.HERE/'authored-coverage.json').read_bytes()),'completeOriginalPlannedMatrixSHA256':coverage['originalMatrixSHA256'],'documentSHA256':c.sha(doc.encode()),'limitations':['Compiler/list proof only; all runtime assertions and aggregate headroom remain unverified','Many authored SL groups cover only subsets; entire coverageLedger is binding','Guest table mutation unsupported/unrun','No final phone/device, published separate-repo FieldLog, store/operational/GA acceptance']}
 c.save(c.HERE/'receipt.json',receipt)
 print(json.dumps({k:receipt[k]for k in ['candidateClosure','commands','preservedFailedCompilerAttempts','freshCompilerContexts','pairedCompilerLayouts','freshListOnlyBinaries','testBodiesExecuted']},indent=2))
if __name__=='__main__':main()
