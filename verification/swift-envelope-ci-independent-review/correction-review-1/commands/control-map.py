#!/usr/bin/env python3
"""Map the original obligations honestly; this is not a 52-pass test report."""
import json
from pathlib import Path

ROUND=Path(__file__).resolve().parents[1]
data={
'C01':('exercised-current','input-audit.json; raw-evidence-audit.json','Admitted corrected bytes and current immutable pack closure.'),
'C02':('prior-faults-plus-current-success','round1 missing-member; current byte audit','Pack verification implementation unchanged; missing-member failure not redundantly rerun.'),
'C03':('prior-faults-plus-current-success','round1 extra-hidden-member; current byte audit','Hidden-extra refusal inherited against unchanged verification code.'),
'C04':('prior-faults-plus-current-success','round1 mutated-library/overlay/manifest; current byte audit','All selected source bytes unchanged.'),
'C05':('partial-and-static','round1 symlink-member; unchanged no_symlinks/inventory','Member links exercised; ancestor-link variant remains static-only.'),
'C06':('partial-and-static','round1 mutated manifest; unchanged member_path/verify_pack','Pinned manifest refuses mutation; exhaustive canonical-path variants not newly exercised.'),
'C07':('exercised-current','input-audit.json; actual-clean','60 originals, exact unmodified library/independent pairs and fresh host execution.'),
'C08':('exercised-current','input-audit.json; actual-clean','Both complete derived files reconstructed from exact prefix and suffix.'),
'C09':('prior-and-current-exercised','round1 unknown source/flags/filter options; response attempt2','Unknown interface unchanged; current injection environment scrubbed.'),
'C10':('partial-and-static','round1 existing/frozen output; current fresh portable outputs','Fresh owned output exercised; symlink-ancestor output variant remains static-only.'),
'C11':('exercised-current','parser-optimized.json; api-refusal-optimized; response attempt2','346 parser cases and selected actual subprocess response refusals under -O; prior optimized pack refusal retained.'),
'C12':('exercised-current','actual-clean-command.json; raw-evidence-audit.json','One clean actual1.99 full78+14/API1+8/21714/32 invocation.'),
'C13':('exercised-current','response-attempt2-matrix.json','Empty/missing/extra/duplicate/substituted listings for both lanes.'),
'C14':('exercised-current','response-attempt2-matrix.json','Empty/missing/duplicate/substituted/ignored/failed/measured/filtered executions for both lanes under -O.'),
'C15':('exercised-current','actual-clean; response layout controls','All32 fresh named values plus missing/wrong/duplicate layout refusals; actual1.98 remains unqualified.'),
'C16':('exercised-current','actual-clean; response positive-fails','Fresh positive probe precedes negatives; failed positive stops before negatives.'),
'C17':('exercised-current','parser-normal/optimized; api-refusal-optimized','All8 real probes/23 exact spans, mixed and malformed inputs; old wrong-span blocker independently closed.'),
'C18':('exercised-current-with-timing-limit','parser-normal/optimized; response negative controls','Missing-library/JSON/crash/success/executable and abnormal metadata refused; actual60-second negative timeout not forced.'),
'C19':('partial-and-static','actual-clean compiler selection; identity-refusal; unchanged select_compiler','Actual explicit compiler and complete identity exercised; local symlink rustup-dispatch variant not independently rerun.'),
'C20':('prior-and-current-exercised','round1 PATH-missing; current identity/parser faults','No installation/fetch; invalid or missing identity fails closed.'),
'C21':('partial-and-static','round1 PATH-missing; current explicit compiler; static select_compiler','Valid PATH/rustup symlink launcher variant remains deferred.'),
'C22':('exercised-current','actual-clean raw commands; response attempt2','Fixed argv/cwd and injection-variable scrubbing reconciled from command receipts.'),
'C23':('partial-and-static','round1 owned15-second timeout; current serial command receipts','Fixed480/60 and15/60/120 policies retained; whole-deadline and all timeout classes not separately forced.'),
'C24':('exercised-prior-unchanged-code','round1 owned-descendant-timeout','Real concurrent owned descendant/partial logs/direct-child reap/group disappearance retained; Commands unchanged.'),
'C25':('exercised-prior-unchanged-code','round1 missing-binary-spawn','Spawn error and failed receipt retained; Commands unchanged.'),
'C26':('partial-and-static','round1 retention-interrupted','SIGTERM during retention exercised; active-phase interruption variant deferred.'),
'C27':('exercised-prior-unchanged-code','round1 marker/inode-change','Changed ownership preserves scratch; cleanup implementation unchanged.'),
'C28':('exercised-prior-unchanged-code','round1 scratch-link/FIFO','Special-object refusal retained with reviewer cleanup journal; cleanup implementation unchanged.'),
'C29':('exercised-current','raw-evidence-audit.json','92 retained files in clean run, all79 independent files/25 actual reports, all identity/gzip bytes verified.'),
'C30':('exercised-prior-unchanged-code','round1 retention-interrupted sparse source','Complete64MiB recoverable source preserved; retention implementation unchanged.'),
'C31':('current-audit-and-static','raw-evidence-audit.json; unchanged preserve_and_cleanup','Executed snapshots and product hash cross-record consistency verified; removed product bytes were hashed by runner before deletion.'),
'C32':('prior-faults-plus-current-success','round1 snapshot/runner/compiler-change; current postflight','Mutations previously detected; unchanged postflight code and current clean/API-failure checks reconciled.'),
'C33':('prior-and-current-exercised','round1 failures; current parser/response/refusal receipts','Both prior false-pass blockers closed; observed failures remain failed with phase evidence.'),
'C34':('exercised-current','raw-evidence-audit.json','Complete raw streams, exact named independent actual-File set and retained hashes reconciled.'),
'C35':('current-audit-and-static','raw-evidence-audit.json; unchanged product source pack','All semantic/GA flags false, selected debit/bounds/source unchanged.'),
'C36':('current-audit-and-static','raw-evidence-audit.json','Existing framing runner/tests/workflow match HEAD; code changes limited to selected parser/constants.'),
'C37':('exercised-current','actual-clean receipt; input-audit.json','Actual1.99 Applearm identity recorded; no remoteCI/other-host/device inference.'),
'C38':('exercised-current','independent commands and source snapshots','Producer tests never loaded; expressly permitted independent pure parser evidence is separate from black-box evidence.'),
'C39':('exercised-current','all preaccess seals and root admission bindings','Correction preaccess frozen before corrected candidate access.'),
'C40':('exercised-current','review.md; seal.json; raw-evidence-audit.json','Bounded handoff with original failures and partial/deferred scope preserved.'),
'L01':('exercised-current','actual-clean compiler argv','Exact ordered -Dwarnings/-A/non_snake_case only on independent --test.'),
'L02':('exercised-current','actual-clean compiler argv','Library/producer/allAPI compile argv retain-Dwarnings and no allowance.'),
'L03':('prior-and-current-exercised','round1 unknown flags; current response argv/environment','No caller flag/filter override or injection reached child commands.'),
'L04':('exercised-current','response independent-other-warning; API abnormal controls','Other compile refusal remains failure; allowance cannot become blanket warning tolerance.'),
'L05':('exercised-current','input-audit.json; fresh inventories','86-member pack,60 originals,two overlays and78/14 names unchanged.'),
'L06':('exercised-current','actual-clean; preserved prior seals','Fresh corrected full closure; old strict-compile/PATH failure and invalid reviewer fixture attempt remain historical failures.'),
'T01':('exercised-current-parser-only-for-1.98','parser-normal/optimized.json','Exact two tuple parser selection tested; actual host qualification is1.99 only.'),
'T02':('exercised-current','parser-normal/optimized; identity-refusal','Complete/duplicate/missing/incoherent fields refused as selected; old identity blocker independently closed.'),
'T03':('partial-actual-host-scope','actual-clean; response layout controls','Unchanged32-layout inventory passes actual1.99; actual1.98 layouts pendingCI.'),
'T04':('partial-actual-host-scope','actual-clean','Full fresh1.99 closure passes; no actual1.98 envelope qualification.'),
'T05':('exercised-current','raw-evidence-audit.json','Actual compiler/launcher identities and mutation checks; fixed pack and lint custody retained.'),
'T06':('pending-environment','root compiler selection and review.md','Actual1.98 CI envelope qualification pending delivered revision and retainedCI evidence; no install/fetch.'),
}
expected=[f'C{n:02d}' for n in range(1,41)]+[f'L{n:02d}' for n in range(1,7)]+[f'T{n:02d}' for n in range(1,7)]
if set(data)!=set(expected):raise RuntimeError('original52 mapping incomplete')
result={'schema':1,'scope':'Disposition of original52 planned obligations; not52 passed tests. Prior evidence remains bound to rejected round1 and is reused only for unchanged functions/pack checks.','original_plan_inventory':52,'rows':[{'id':key,'status':data[key][0],'evidence':data[key][1],'scope_limit':data[key][2]} for key in expected],'counted_52_pass_claim':False,'CI_1_98_1_envelope_qualified':False}
with (ROUND/'original-52-control-map.json').open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'mapped_original_obligations':len(result['rows']),'claim_52_passed':False},sort_keys=True))
