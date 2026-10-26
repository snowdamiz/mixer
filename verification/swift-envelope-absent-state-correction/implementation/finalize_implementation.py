#!/usr/bin/env python3
"""Close exact source/test/model and command custody without rerunning tests."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PACKET=HERE.parent
OLD=ROOT/"verification/swift-ordered-retention-analyzer-envelope-correction"
SOURCE="2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef"
PARENT="1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b"
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def desc(p):
    return {"path":str(p.relative_to(ROOT)),"bytes":p.stat().st_size,"sha256":sha(p)}
def save(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def load(name):
    return json.loads((HERE/name).read_text())
def checked(item):
    assert desc(ROOT/item["path"])==item,item["path"]
    return item
def seal_checked(p,expected):
    assert sha(p)==expected,str(p)
    data=json.loads(p.read_text())
    for m in data["members"]:checked(m)
    return {**desc(p),"member_count":len(data["members"]),"member_bytes":sum(m["bytes"] for m in data["members"])}

def main():
    first=load("run-1/receipt.json");second=load("run-2/receipt.json")
    assert first["status"]=="failed" and second["status"]=="passed"
    assert first["unchanged_framing_methods_passed"]==44 and first["unchanged_envelope_methods_passed"]==26
    assert second["methods_executed_this_attempt"]==8 and second["focused_methods_passed"]==8
    assert len(second["regression_references"])==2
    assert second["api_positive_compiles"]==1 and second["api_expected_negative_compiles"]==8
    assert second["focused_control_counts"]=={
        "absent_cases":15,"present_underfunded_cases":1700,"normal_funded_cases":2,
        "invalid_entry_spent_cases":125,"poststate_matrix_cases":18144,"guard_dispatch_cases":6,
        "caller_rejection_and_poison_cases":12,"actual_public_counter_cases":3}
    commands=[];timed_out=0;expected_rejections=0
    for name,value in [("run-1",first),("run-2",second)]:
        assert value["candidate_source_sha256"]==SOURCE and value["parent_source_sha256"]==PARENT
        assert value["source_and_frozen_inputs_preserved"] and value["owned_scratch_removed"] and value["all_children_reaped"]
        assert value["direct_immutable_inputs_before"]==value["direct_immutable_inputs_after"]
        assert value["compiled_owned_inputs_before"]==value["compiled_owned_inputs_after"]
        for item in value["direct_immutable_inputs_after"]+value["compiled_owned_inputs_after"]:checked(item)
        for row in value["commands"]:
            stdout=HERE/name/row["stdout"];stderr=HERE/name/row["stderr"]
            assert sha(stdout)==row["stdout_sha256"] and sha(stderr)==row["stderr_sha256"]
            assert row["child_reaped"] and not row["timed_out"]
            assert row["immediate_inputs_before"]==row["immediate_inputs_after"]
            if row["returncode"]!=0:
                if name=="run-1":assert row["name"]=="focused-absence8" and row["returncode"]==101
                else:assert row["name"].startswith("api-negative-") and not row["expected_success"];expected_rejections+=1
            commands.append({"attempt":name,**row})
        for binary in value["binaries_hashed_then_removed"]:assert not (ROOT/binary["path"]).exists()
        for item in value["temporary_owned_links_removed"]:assert not (ROOT/item["path"]).exists()
        assert not (HERE/name/"owned-scratch").exists()
        assert sha(HERE/name/"src/envelope.rs")==SOURCE
        assert sha(HERE/name/"build/inputs/envelope.rs")==SOURCE
        assert sha(HERE/name/"src/analyzer.rs")==PARENT
    assert len(commands)==27 and expected_rejections==8
    original=(HERE/"run-1/focused_controls.rs").read_text()
    corrected=(HERE/"run-2/focused_controls.rs").read_text()
    before="assert_eq!(calls,1); assert_eq!(main.replay_spent,4*471);"
    after="assert_eq!(calls,1); assert_eq!(main.replay_spent,534+4*471);"
    assert original.count(before)==1 and original.replace(before,after)==corrected
    assert corrected==(HERE/"focused_controls.rs").read_text()
    finding=load("failure-analysis-run-1.json")
    assert finding["test_before_sha256"]==sha(HERE/"run-1/focused_controls.rs")
    assert finding["test_after_sha256"]==sha(HERE/"run-2/focused_controls.rs")
    proposal=seal_checked(PACKET/"proposal-1/seal.json","3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c")
    account=seal_checked(ROOT/"verification/swift-envelope-absent-state-accounting-review/seal.json","c9191a26ed0c5081e9c2ad97082fc61cee3f6eeb94ea49c4be5028b0f54536e4")
    select=ROOT/"verification/swift-ordered-retention-analyzer-envelope-root-review/absence-correction-selection.json"
    assert sha(select)=="ae90b289519d0588a27cae4db0a7ce4a74ce3016c9c2f790fd962775ec4fd2e0"
    assert first["direct_immutable_inputs_after"]==second["direct_immutable_inputs_after"]
    producer=json.loads((OLD/"seal.json").read_text())
    assert sha(OLD/"seal.json")=="4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1"
    layout_labels=desc(OLD/"actual-complete-layouts.json")
    assert next(m for m in producer["members"] if m["path"]==layout_labels["path"])==layout_labels
    layouts=load("run-1/actual-complete-layouts.json")
    assert len(layouts["layouts"])==32 and layouts["source_sha256"]==SOURCE
    for name in ["run-1","run-2"]:
        manifest=load(name+"/compiled-input-manifest.json")
        canonical=json.dumps(sorted(manifest["members"],key=lambda d:d["path"]),sort_keys=True,separators=(",",":")).encode()
        assert hashlib.sha256(canonical).hexdigest()==manifest["sha256"]
        for member in manifest["members"]:checked(member)
    model_refs=[m for m in first["direct_immutable_inputs_before"] if "/inputs/oracle" in m["path"] or m["path"].endswith("fsm-model-425.py")]
    test_refs=[m for m in first["direct_immutable_inputs_before"] if "/tests/" in m["path"]]
    save("source-test-model-binding.json",{"schema":1,"candidate_source_sha256":SOURCE,"parent_source_sha256":PARENT,
        "root_selection":desc(select),"proposal":proposal,"accounting":account,
        "product_source_pair":[desc(HERE/"run-2/src/analyzer.rs"),desc(HERE/"run-2/src/envelope.rs")],
        "compiled_input_manifests":[desc(HERE/"run-1/compiled-input-manifest.json"),desc(HERE/"run-2/compiled-input-manifest.json")],
        "original_test_sources_directly_referenced":test_refs,
        "new_test_before":desc(HERE/"run-1/focused_controls.rs"),"new_test_after":desc(HERE/"run-2/focused_controls.rs"),
        "test_only_difference":finding,"unchanged_model_oracle_inputs_directly_referenced":model_refs,
        "model_execution":"No Python model code was imported/executed; reused immutable selected425 expected bytes. New candidate comparisons execute in run-1.",
        "layout_label_metadata":layout_labels,
        "test_shim":"Actual test framing input is the exact parent prefix plus only an include of the unchanged private-IO test module. Actual test envelope input is byte-identical to selected source. Owned wrappers directly include unchanged six fixture test sources and add the new child test module.",
        "all_source_test_model_bindings_unchanged_after_commands":True})
    save("cleanup.json",{"schema":1,"all_27_owned_children_reaped":True,"timed_out":0,
        "attempts":[{"attempt":n,"owned_scratch_removed":v["owned_scratch_removed"],
            "binaries_hashed_then_removed":v["binaries_hashed_then_removed"],
            "temporary_owned_links_removed":v["temporary_owned_links_removed"],
            "retained_reports_or_failure_files":v["retained_reports_or_failure_files"]} for n,v in [("run-1",first),("run-2",second)]],
        "scope":"Only attempt-owned children, binaries, temporary links and scratch. All removal occurred after child return/reap. No device, simulator, UI, capture or process discovery/changes.",
        "unowned_process_changes":False})
    final={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status":"host-producer-controls-passed-independent-behavior-acceptance-pending",
        "candidate_source_sha256":SOURCE,"parent_source_sha256":PARENT,"root_selection":desc(select),
        "proposal":proposal,"independent_preexecution_accounting":account,
        "host_tools":{"rust":first["rust_version"].strip(),
            "python":(HERE/"run-1/commands/python-version.stdout").read_text().strip(),
            "git":(HERE/"run-1/commands/git-version.stdout").read_text().strip()},
        "revision_contexts":[(HERE/n/"commands/revision.stdout").read_text().strip() for n in ["run-1","run-2"]],
        "attempts":[desc(HERE/"run-1/receipt.json"),desc(HERE/"run-2/receipt.json")],
        "fresh_unchanged_methods":{"framing":44,"envelope":26,"total":70,"executed_in":"run-1","passed":70,"failed":0,"ignored":0},
        "fresh_candidate_oracle_comparisons":{"complete":16170,"threshold":5544,"total":21714,"executed_in":"run-1",
            "oracle":"immutable previously selected425 expected bytes directly bound, not copied raw archives","fresh_model_evaluation":False},
        "fresh_complete_layouts":{"count":32,"executed_in":"run-1","receipt":desc(HERE/"run-1/actual-complete-layouts.json")},
        "focused_controls":{"methods":8,"passed":8,"executed_in":"run-2","counts":second["focused_control_counts"],
            "guard_main_B_events":24,"guard_actual_leaf_calls":6,"guard_finalizer_branches":24,
            "predicate_scope":"Poststate debit coherence; no before-budget input, no general shape/authority qualification of fabricated paid replies"},
        "API":{"positive":1,"expected_negative":8,"executed_in":"run-2","controls":second["api_controls"]},
        "distinct_final_host_method_bodies_passed":78,"claim_of_one_all_green_attempt":False,
        "first_failure":{"attempt":"run-1","suite":"focused-absence8","passed":7,"failed":1,"exit":101,
            "classification":"new test expected-counter omission; actual2418 equals534 setup plus4*471",
            "repair":"exact one-line test expectation1884->2418; selected source unchanged",
            "retained":desc(HERE/"failure-analysis-run-1.json")},
        "child_commands":27,"expected_API_compile_rejections":8,"unexpected_first_test_failures_retained":1,
        "timeouts":0,"source_test_model_binding":desc(HERE/"source-test-model-binding.json"),
        "cleanup":desc(HERE/"cleanup.json"),"source_and_historical_packets_unchanged":True,
        "selected_amounts":{"leaf":425,"W":24,"B":471,"G":112,"T":42,"finish":47,"F":42,"setup":534},
        "guard_scope":"Root-selected at most one terminal absent/invalid-entry-spent/present-underfunded path7/7/112; main-paid W24 independently owns caller work",
        "public_counter":"534*S_paid+47*F_paid+425*N_B; every successful main B retains425 even when private debit0",
        "public_API_ABI_report_and_parent_changed":False,"product_or_engine_integration":False,"committed_or_pushed":False,
        "implementation_accepted":False,"independent_behavior_accepted":False,"fullReplayAccepted":False,
        "storedPrefixValidated":False,"semanticMetricsValid":False,"GA_qualified":False,
        "pending":["root independent behavior review and final acceptance","semantic replay/custody/OTA release/product qualification",
            "native/UI/capture/device checks paused; phones disconnected","signing/store/FieldLog/customer/operations/GA gates"],
        "finalize_command":{"argv":[sys.executable,"-B",str(Path(__file__).resolve())],"python":sys.version,
            "source_sha256":sha(Path(__file__)),"scope":"standard-library custody/hash/arithmetic only; no new candidate execution"}}
    save("final-receipt.json",final)
    doc="""# Selected absent-state correction: host implementation evidence

Fresh isolated host qualification passes for the exact root-selected envelope source2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef and unchanged parent1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b. This is producer evidence pending root's independent behavior review and final acceptance. No product, replay, release or GA gate is promoted.

The immutable35-member proposal seal remains3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c. Independent accounting sealc9191a26ed0c5081e9c2ad97082fc61cee3f6eeb94ea49c4be5028b0f54536e4 supports121 rows,108 unchanged copy edges and the selected amounts. Root selectionae90b289519d0588a27cae4db0a7ce4a74ce3016c9c2f790fd962775ec4fd2e0 explicitly selects G112 ownership for one terminal absent/invalid-entry-spent/present-underfunded path bounded7/7/112. Main-paid W24 owns caller handling independently of private debit0. Every successful main B471 retains public425; the public formula remains534*S_paid+47*F_paid+425*N_B.

The authoritative evidence is [final-receipt.json](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/implementation/final-receipt.json) and [source-test-model-binding.json](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/implementation/source-test-model-binding.json).

## Results and first failure

Run-1 freshly executes all70 unchanged method bodies:44 framing and26 envelope, all passed, none ignored. The same run makes21,714 new-source comparisons against directly referenced immutable selected425 oracle inputs (16,170 complete and5,544 threshold cases). The Python model is not reevaluated. All32 actual complete layouts match the fixed declarations; public128, reply128, Progress144, aggregate/Result232 and complete unit Result40 remain unchanged.

The first focused run passes7/8 and retains one failure. Its new test expected replay_spent1884 after four B471 charges, omitting that the actual Budget::setup(534) also invokes replay(534); actual2418 is correct. The exact one-line new-test expectation becomes534+4*471. Both test snapshots, the failing stdout/stderr and the source-backed analysis remain in run-1 and failure-analysis-run-1.json. No selected source, fixture, expected semantic reply, contract or production debit changed.

Run-2 recompiles the identical selected source with the corrected new assertion, freshly passes all8 focused methods and one positive plus8 expected-negative public API compiles. The unchanged70 results are directly verified from run-1, rather than replayed for this isolated new-test expectation fix. There is no claim that run-1 was entirely green.

| Focused control | Executed cases |
| --- | ---: |
| Length0/32/7,731,055 across credits0/1/424/425/426; poison0 and no budget/arena/candidate mutation | 15 |
| All credits0..424, first/later prior states, lengths7,731,056 and8,388,608; actual Steps0 projection before malformed record | 1,700 |
| Normal funded425 exact reply and whole arena/candidate mutation canaries | 2 |
| Nonzero entry spent across absent/readable lengths; private no mutation and caller rejection | 125 |
| Finite caller poststate debit matrix including reserved/extent canaries | 18,144 |
| Actual guard result installation/validator/latch seams;24 successful B events,6 actual leaves,24 finalizer branches | 6 |
| Incoherent zero replies and paid mixed-poison marker terminal handling | 12 |
| Actual framing counter: decode/coordinate failure and latched skip retain paid425 | 3 |

The caller predicate is a poststate debit check for the selected private helper reply forms. It has no historical before-budget input and does not validate arbitrary state shape or give fabricated paid replies authority. The existing paid425/remaining0/spent425 predicate is preserved. Coherent zero poison accepts any remaining, while zero Steps requires remaining below425; inconsistent debit forms become terminal poison. Existing poison priority, state checks, private constructors and false acceptance flags remain fixed. The disclosed fabricated paid status1/nonzero nonpoison reason scheduling limit remains outside this qualification.

## Source, command and cleanup custody

Rust1.99.0 (aarch64-apple-darwin, LLVM23.1.1), Python3.14.8 and Apple Git2.54.0 are recorded with exact paths, hashes and version output. Both product source copies and the compiled test envelope are exact selected bytes. The test framing shim is the exact parent prefix plus an include of the unchanged private-IO test module. Owned wrappers directly include the six immutable original fixture sources and add the focused child module. Forty-four immutable fixture/model/historical inputs are hashed before and after each attempt; raw upstream archives are not duplicated. Actual source/input manifests, exact argv, dedicated owned process groups, deadlines and file-backed stdout/stderr are retained.

All27 qualification child commands returned and were reaped. The separate bounded offline finalizer has its own receipt. There were no timeouts; the eight expected API compiler rejections are successful negative controls. Owned binaries are hashed then removed, temporary oracle links and scratch are removed after child completion, and reports/first-failure files are retained as described in [cleanup.json](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-correction/implementation/cleanup.json). No unowned process or data was changed.

Historical R2 remains a confirmed failure of the old source. Original producer, review and proposal packets remain byte-identical; this new implementation evidence does not rewrite them. No frozen collector, forbidden hosted inspector or broad harness was imported/executed. No engine/CLI/CI/root metadata was edited and no commit/push was made. Native/UI/capture/process discovery and physical-device runs remain paused, phones remain disconnected, and no Swift/native device, signing, store, FieldLog or GA receipt is claimed.
"""
    (PACKET/"implementation.md").write_text(doc)
    print(json.dumps({"status":final["status"],"candidate_source_sha256":SOURCE,
        "methods_passed_across_receipts":78,"oracle_comparisons":21714,
        "focused_methods":8,"API_positive":1,"API_expected_negative":8,
        "first_failure_preserved":True,"cleanup":True,"final_receipt":desc(HERE/"final-receipt.json")},sort_keys=True))

if __name__=="__main__":main()
