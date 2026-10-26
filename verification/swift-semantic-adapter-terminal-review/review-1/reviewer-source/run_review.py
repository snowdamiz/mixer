"""Independent finite/source review. Producer files are JSON/text data only."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from itertools import product
import hashlib
import json
import sys
from oracle import (MAX, WORDS, ReadTrace, accepted_child_source, base_request,
                    evaluate, header_problem, normalize_public, project,
                    snapshot_problem)

OUT = Path(__file__).resolve().parents[1]
REVIEW = OUT.parent
ROOT = OUT.parents[2]
PRE = REVIEW / "preaccess"
CAND = OUT / "candidate-snapshot/verification/swift-semantic-adapter-terminal-correction"
MODE = "optimized" if sys.flags.optimize else "normal"
RESULT = OUT / "results" / MODE
RESULT.mkdir(parents=True, exist_ok=True)
CHECKS=[]
METHODS=[]


def dump(name, value):
    (RESULT/name).write_text(json.dumps(value, indent=2, sort_keys=True)+"\n")


def check(label, condition):
    if not condition: raise AssertionError(label)
    CHECKS.append(label)


def sha(data): return hashlib.sha256(data).hexdigest()


def method(function):
    function()
    METHODS.append(function.__name__)


def custody_and_declarations():
    seals=[(PRE,PRE/"seal.json","b71097292535a76631d787121c60e315f91343ed6da8c71fec9303cf9328e681"),
           (ROOT,ROOT/"verification/swift-semantic-adapter-terminal-correction/seal.json","efa9288096a692780e195ac519ffb7ed0be1280a974e830d80fc9932d194aef7"),
           (ROOT,ROOT/"verification/swift-semantic-adapter-prerequisite/seal.json","d145cda8cdde0915493f5c75102ae0dc11adb577891b1b773322b5c4d0f32cba"),
           (ROOT/"verification/swift-semantic-adapter-contract-review/preaccess",ROOT/"verification/swift-semantic-adapter-contract-review/preaccess/seal.json","7ae911b982f2bf96f596969c2c282bd5bbdd7302033a6d1404278f1df23d9ae9"),
           (ROOT/"verification/swift-semantic-adapter-contract-review/review-1",ROOT/"verification/swift-semantic-adapter-contract-review/review-1/seal.json","d44b2edd19961ebeda7e197f549433e7a0d7f0630ce7d501e5465044340c6c02")]
    audit=[]
    for base,path,expected in seals:
        raw=path.read_bytes();check("seal:"+str(path.relative_to(ROOT)),sha(raw)==expected)
        seal=json.loads(raw);total=0
        for member in seal["members"]:
            candidate=(base/member["path"]).resolve()
            check("member-within-root:"+member["path"],candidate.is_relative_to(ROOT))
            data=candidate.read_bytes()
            check("member:"+member["path"],len(data)==member["bytes"] and sha(data)==member["sha256"])
            total+=len(data)
        audit.append({"seal":str(path.relative_to(ROOT)),"sha256":expected,"members":len(seal["members"]),"bytes":total})
    frozen=json.loads((OUT/"candidate-snapshot-manifest.json").read_text())
    for member in frozen:
        data=(OUT/member["snapshot"]).read_bytes()
        check("owned-correction-snapshot:"+member["path"],len(data)==member["bytes"] and sha(data)==member["sha256"])
    original=json.loads((PRE/"original-inputs/verification/swift-semantic-adapter-prerequisite/contract.json").read_text())
    corrected=json.loads((CAND/"terminal-contract.json").read_text())
    check("word-order-independent-literal",WORDS==original["observation"]["words"]==corrected["observation_words"])
    for before,after in [("global_caps","unchanged_global_caps"),("memory","unchanged_memory"),("work","unchanged_work")]:
        check("unchanged-"+before,original[before]==corrected[after])
    check("boundary-ids-unchanged",original["observation"]["boundaries"]==corrected["boundaries"])
    check("reason-ids-unchanged",original["observation"]["reason_ids"]==corrected["reasons"])
    source_rows=json.loads((PRE/"source-obligations.json").read_text())
    for row in source_rows:
        data=(ROOT/row["path"]).read_bytes()
        excerpt=b"".join(data.splitlines(keepends=True)[row["first_line"]-1:row["last_line"]])
        check("frozen-independent-source:"+row["id"],sha(data)==row["source_sha256"] and sha(excerpt)==row["excerpt_sha256"])
    source_claims=json.loads((CAND/"source-bindings.json").read_text())["rows"]
    for row in source_claims:
        copy_path=CAND/row["snapshot"]
        copy_path=copy_path.with_name(copy_path.name+".txt")
        data=copy_path.read_bytes()
        original_name="13-analyzer.rs.txt" if "analyzer" in row["path"] else "14-envelope.rs.txt"
        accepted=(PRE/"original-inputs/verification/swift-semantic-adapter-prerequisite/inputs"/original_name).read_bytes()
        excerpt=b"".join(data.splitlines(keepends=True)[row["first"]-1:row["last"]])
        check("producer-source-identity:"+row["name"],data==accepted and sha(data)==row["source_sha256"])
        check("producer-source-excerpt:"+row["name"],excerpt.decode()==row["excerpt"] and sha(excerpt)==row["excerpt_sha256"])
    dump("custody.json",{"seals":audit,"independent_source_ranges":len(source_rows),"correction_source_ranges":len(source_claims),"all_unchanged_declarations":True})


def source_normalization():
    counts=Counter();rows=Counter();total=0;witnesses={}
    for complete,limited,ok in [(True,False,True),(False,True,False),(True,True,True),(False,False,False)]:
      for flags,valid,status,reason,stage,readable in product([0,1,2],[0,1,2],[0,1,2,3],range(17),[0,1,10,11],[False,True]):
        raw={"input_error":None,"complete":complete,"limited":limited,"input_ok":ok,
             "flags":flags,"reply_valid":valid,"status":status,"reason":reason,"stage":stage,
             "phase":5,"mask":33,"pin_failure":0,"terminal_failure":0,"expected_readable":readable,"expected_mask":33}
        decision,framed,eb,er,branch=accepted_child_source(raw)
        loop="complete" if complete and not limited and ok else "limited" if limited and not complete and not ok else "contradictory"
        facts={"loop":loop,"flags":flags,"framing_decision":decision,"framed":framed,
               "envelope_boundary":eb,"envelope_reason":er,"error_code":0}
        expected={"loop-incoherent":"Unsupported","no-reply":"EnvelopeUnavailable","invalid-validity":"EnvelopeUnavailable",
                  "poison":"EnvelopePoison","reply-malformed":"EnvelopeUnavailable","limited-refusal":"EnvelopeRefused",
                  "limited-observed":"Limited","refusal":"EnvelopeRefused","CAP":"Cap","expected-read-failed":"EnvelopePoison",
                  "closed":"Closed","incomplete":"EnvelopeRefused"}[branch]
        actual=normalize_public(facts)
        check("raw-child-normalization-"+str(total),actual==expected)
        total+=1;counts[actual]+=1;rows[branch]+=1;witnesses.setdefault(branch,{"raw":raw,"public":facts,"normalized":actual})
    # Input errors run before loop/reply poison and ignore invalid flags/state.
    for code,flags in product(range(1,18),[0,1,511]):
        raw={"input_error":code}
        decision,framed,eb,er,branch=accepted_child_source(raw)
        facts={"loop":"input_error","flags":flags,"framing_decision":decision,"framed":framed,
               "envelope_boundary":eb,"envelope_reason":er,"error_code":code}
        expected="InputBinding" if code==15 else "InputBudget" if code==4 else "InputInvalid"
        check("source-input-code-"+str(code)+"-"+str(flags),normalize_public(facts)==expected)
        total+=1;counts[expected]+=1;rows[branch]+=1;witnesses.setdefault(branch,{"raw":raw,"public":facts,"normalized":expected})
    # Additional poison-shape, phase, mask and terminal-bit source guards.
    baseline={"input_error":None,"complete":True,"limited":False,"input_ok":True,"flags":0,
              "reply_valid":1,"status":1,"reason":0,"stage":0,"phase":5,"mask":33,
              "pin_failure":0,"terminal_failure":0,"expected_readable":True,"expected_mask":33}
    for field,bad in [("phase",6),("mask",64),("pin_failure",2),("terminal_failure",2)]:
        raw=dict(baseline);raw[field]=bad
        values=accepted_child_source(raw)
        check("source-shape-"+field,values[2:]==(0,20,"reply-malformed"))
    claimed=json.loads((CAND/"source-normalization-cases.json").read_text())["cases"]
    for row in claimed:
        check("untrusted-literal-normalization:"+row["id"],normalize_public(row["facts"])==row["expected"])
    check("every-child-source-branch-covered",len(rows)==13)
    check("every-closed-child-class-covered",set(counts)=={"InputBinding","InputBudget","InputInvalid","EnvelopePoison","EnvelopeUnavailable","EnvelopeRefused","Limited","Cap","Closed","Unsupported"})
    dump("source-normalization.json",{"finite_raw_source_cases":total,"raw_source_branch_counts":rows,"normalization_counts":counts,
           "source_branch_witnesses":witnesses,"producer_literal_cases_checked_as_data":len(claimed),"Rust_product_tests":0})


def all_terminal_rows_and_shadows():
    cases={}
    r=base_request();r["outer_error"]=[6,8,19,0,0];cases["T00"]=r
    for row,child in [("T01","InputBinding"),("T02","InputBudget"),("T03","InputInvalid"),("T04","EnvelopePoison"),("T06","EnvelopeUnavailable"),("T07","EnvelopeRefused")]:
        r=base_request();r["child"]=child;cases[row]=r
    r=base_request();r["progress"]="Unreadable";cases["T05"]=r
    r=base_request();r.update(progress="Absent",calls=0);cases["T08"]=r
    r=base_request();r["snapshot"]["nonce"]=0;cases["T09"]=r
    for row,latch in [("T10","Refusal"),("T11","Failure"),("T12","Limit")]:cases[row]=base_request(8,latch)
    for row,child in [("T13","Limited"),("T14","Cap"),("T15","Closed")]:cases[row]=base_request(0,"None",child)
    results=[]
    for row,r in sorted(cases.items()):
        actual=evaluate(r);check("branch-witness:"+row,actual["row"]==row)
        if int(row[1:])<9:
            r["snapshot"]=ReadTrace({},WORDS+["M","stage","work","nonce"])
            check("no-Q-read:"+row,evaluate(r)==actual and not r["snapshot"].reads)
        # Every non-outer branch is shadowed by an earlier actual outer error.
        shadow=deepcopy(r);shadow["outer_error"]=[4,8,0,0,0]
        check("earlier-shadow:"+row,evaluate(shadow)=={"kind":"Err","row":"T00","error":[4,8,0,0,0],"words":None})
        results.append({"row":row,"witness":cases[row] if not isinstance(cases[row]["snapshot"],ReadTrace) else {k:v for k,v in cases[row].items() if k!="snapshot"},"expected":actual})
    # All closed classes x progress tags x latches; conflicts and prior latch are
    # constructed separately from a first-applicable implementation chain.
    counts=Counter();total=0
    children=["InputBinding","InputBudget","InputInvalid","EnvelopePoison","EnvelopeUnavailable","EnvelopeRefused","Limited","Cap","Closed","Unsupported"]
    for child,progress,latch,outer,stage in product(children,["Absent","Valid","Poison","Unreadable","Stale","Malformed"],["None","Refusal","Failure","Limit"],[False,True],[0,2,3,6,7,8,10]):
        r=base_request(stage,latch,child);r["progress"]=progress
        if progress=="Absent":r["calls"]=0
        if outer:r["outer_error"]=[14,8,49_152,0,0]
        answer=evaluate(r);counts[answer["row"]]+=1;total+=1
        check("closed-total-"+str(total),answer["row"] in cases)
        if answer["kind"]=="Ok":
            w=answer["words"]
            check("closed32-"+str(total),len(w)==32 and w[26:]==[0]*6 and w[21:24]==[238848,1,1])
            if int(answer["row"][1:])<10:check("closed-Z-"+str(total),w[2:21]==[0]*19 and w[24:26]==[0,0])
        else:check("closed-null-"+str(total),answer["words"] is None)
    check("all16rows",set(counts)==set(cases))
    # Pairwise terminal competition retained for all first semantic latches.
    overlaps=[]
    for latch,child in product(["Refusal","Failure","Limit"],children):
        r=base_request(8,latch,child);result=evaluate(r)
        overlaps.append({"latch":latch,"later_child":child,"result":result})
    dump("terminal-coverage.json",{"row_witnesses":results,"cartesian_cases":total,"row_counts":counts,"pairwise_terminal_overlaps":overlaps,"all16rows":True})


def full_word_projection_and_read_sets():
    expected_flags=[(0,0,0,0),(1,0,0,0),(1,0,0,0),(1,1,0,0),(1,1,0,0),(1,1,0,0),
                    (1,1,1,0),(1,1,1,1),(1,1,1,1),(1,1,1,0),(1,1,1,0)]
    rows=[];coverage={word:[] for word in WORDS}
    for stage,flags in enumerate(expected_flags):
        r=base_request(stage);active,miss,planned,pending=flags
        forbidden=set()
        if not active:forbidden|={"op","function"}
        if not planned:forbidden|={"selected","taken","committed","feasible","destination"}
        if not pending:forbidden.add("pending")
        q=ReadTrace(r["snapshot"],forbidden);r["snapshot"]=q
        actual=evaluate(r)
        # Independent literal field-order fixture; discriminator values are
        # frozen above per source stage rather than computed by oracle branches.
        expected=[2,0,27,27,0,27,211,233,7 if active else 0,529 if active else MAX,
                  2,95,1,9,17 if miss else MAX,3 if planned else 0,
                  1 if planned else 0,0,0 if pending else MAX,1 if planned else MAX,
                  0,238848,1,1,1,1,0,0,0,0,0,0]
        check("full32-stage-"+str(stage),actual=={"kind":"Ok","row":"T14","words":expected})
        check("inactive-read-set-"+str(stage),not q.forbidden.intersection(q.reads))
        for index,word in enumerate(WORDS):
            altered=expected.copy();altered[index]^=1
            check("individual-word-control-"+str(stage)+"-"+word,altered!=actual["words"])
            coverage[word].append("stage"+str(stage))
        rows.append({"stage":stage,"expected32":expected,"allowed_reads_used":sorted(set(q.reads)),"forbidden_reads":sorted(forbidden)})
    for stage in [6,9,10]:
        r=base_request(stage);r["snapshot"].update(feasible=False,destination="poison-unread")
        r["snapshot"]=ReadTrace(r["snapshot"],{"pending","destination"})
        actual=evaluate(r)
        check("obstructed-destination-"+str(stage),actual["row"]=="T14" and actual["words"][19]==MAX)
    for latch in ["Refusal","Failure","Limit"]:
        r=base_request(0,latch);r["snapshot"].update(M=0,seq=0,work=0,instructions=0,residents=0,bytes=0,pins=0,nonce=1)
        r.update(calls=1,stop=1,N=3,NC=3)
        result=evaluate(r);check("actual-first-call-initial-"+latch,result["words"][3]==0 and result["words"][13]==1 and result["words"][24]==1)
    pre=json.loads((PRE/"cases.json").read_text());frozen=[]
    for row in pre["projection_vectors"]:
        r=base_request()
        if row["mode"]=="suppressed":
            r.update(SS=row["setup_paid"],SF=row["finish_paid"],NC=row["charged_records"])
            got=project(r,0,3,False)
            scope="parameterized projector only; partial paid receipts are not returned aggregates"
        elif row["mode"]=="live-idle":
            r=base_request(0,"None","Closed");r.update(NC=27);r["snapshot"]["pins"]=0
            got=evaluate(r)["words"];scope="source-constructible typed fixture shape"
        else:
            r=base_request(8);r.update(NC=27);r["snapshot"].update(function=17,committed=1,pending=1,destination=0)
            got=evaluate(r)["words"];scope="source-constructible typed fixture shape"
        check("frozen-preaccess-projection-"+row["id"],got==row["expected32"])
        frozen.append({"id":row["id"],"scope":scope,"matched":True})
    for row in pre["rejected_full32_counterexamples"]:
        check("frozen-rejected-full32-"+row["id"],row["bad32"]!=row["expected32"])
    dump("field-coverage.json",{"all32words":coverage,"stage_projection_rows":rows,"frozen_projection_disposition":frozen,
         "frozen_full32_counterexamples_rejected":len(pre["rejected_full32_counterexamples"]),"Rust_product_tests":0})


def malformed_snapshot_and_header_controls():
    mutations=[]
    for key in ["M","seq","work","instructions","stage","residents","bytes","pins","nonce"]:
        for value in [-1,MAX+1,False,None]:mutations.append(("type-"+key+"-"+str(value),key,value))
    mutations += [("stage11","stage",11),("M>N","M",28),("seq-drift","seq",26),
                  ("residents-over-limit","residents",4),("pins-over-limit","pins",5),
                  ("nonce0","nonce",0),("zero-bytes-occupied","bytes",0),
                  ("function80000","function",80000),("active-op0","op",0),
                  ("selected-one-past","selected",8),("taken-not-selected","taken",4),
                  ("committed-not-taken","committed",2),("feasible-not-bool","feasible",1),
                  ("destination-one-past","destination",3),("pending-one-past","pending",3),
                  ("pending-not-selected","pending",2),("pending-obstructed","feasible",False)]
    records=[];guard_counts=Counter()
    for name,key,value in mutations:
        r=base_request(8);r["snapshot"][key]=value
        problem=snapshot_problem(r);answer=evaluate(r)
        check("snapshot-rejection-"+name,problem is not None and answer["row"]=="T09")
        guard_counts[problem]+=1;records.append({"id":name,"guard":problem,"result":answer})
    request_mutations=[("N-negative","N",-1),("N-one-past","N",4_194_305),("NC-under-N","NC",26),
                       ("slots0","slots",0),("slots65","slots",65),("pin-slots0","pin_slots",0),
                       ("noLatch-calls","calls",26),("noLatch-reason","latch_reason",1),("noLatch-stop","stop",1)]
    for name,key,value in request_mutations:
        r=base_request(8);r[key]=value;problem=snapshot_problem(r)
        check("request-rejection-"+name,problem is not None and evaluate(r)["row"]=="T09")
        guard_counts[problem]+=1;records.append({"id":name,"guard":problem})
    for latch in ["Refusal","Failure","Limit"]:
        for field,value in [("stop",29),("calls",27),("latch_reason",17)]:
            r=base_request(8,latch);r[field]=value;problem=snapshot_problem(r)
            check("latch-shape-"+latch+field,problem is not None and evaluate(r)["row"]=="T09")
            guard_counts[problem]+=1
    for key,value in [("progress","unsupported"),("calls",0),("calls",MAX),("after_latch_calls",1),("second_terminal",True),("latch","second")]:
        r=base_request();r[key]=value;r["snapshot"]=ReadTrace({},WORDS+["stage","M"])
        check("header-before-Q-"+key+str(value),evaluate(r)["row"]=="T05" and not r["snapshot"].reads)
    # The special initialized-empty guard and pins/residents relation need
    # isolated witnesses avoiding an earlier count/byte rejection.
    r=base_request(0,"Failure");r.update(N=3,NC=3,calls=1,stop=1)
    r["snapshot"].update(M=0,seq=0,work=1,instructions=0,residents=0,bytes=0,pins=0,nonce=1)
    check("Q5-first-call-nonzero-work",snapshot_problem(r)=="Q5-initial" and evaluate(r)["row"]=="T09")
    r=base_request();r["snapshot"].update(residents=0,bytes=0,pins=1)
    check("Q2-pins-with-no-resident",snapshot_problem(r)=="Q2-pins" and evaluate(r)["row"]=="T09")
    r=base_request(2,"None","Closed")
    check("Q3-closed-open-stage",snapshot_problem(r)=="Q3-closed" and evaluate(r)["row"]=="T09")
    dump("malformed-controls.json",{"independent_mutations":records,"named_guard_counts":guard_counts,
         "header_controls":6,"special_guards":["Q5-initial","Q2-pins","Q3-closed"],"inactive_Q10_read_guards":"field-coverage.json"})


def outer_errors_and_preaccess_disposition():
    source_errors=json.loads((PRE/"accepted-child-error-partition.json").read_text())["rows"]
    errors=[]
    values={"position":19,"output_position":19,"done":19,"call_stage":6,
            "offset+done":531,"512+128*zero_based_index":512,"index+1":1,
            "length-512":896,"length-512+72":968}
    for row in source_errors:
        error=[values.get(value,value) if isinstance(value,str) else value for value in row["error"]]
        for latch in ["None","Refusal","Failure"]:
            r=base_request(8,latch)
            if row["child_core_partition"]=="outer-Err":
                r["outer_error"]=error;r["snapshot"]=ReadTrace({},WORDS+["stage","M"])
                expected={"kind":"Err","row":"T00","error":error,"words":None}
                check("source-exact-outer-"+row["id"]+latch,evaluate(r)==expected and not r["snapshot"].reads)
            else:
                r["child"]="InputBinding" if error[0]==15 else "InputBudget" if error[0]==4 else "InputInvalid"
                r["progress"]="Poison";r["snapshot"]=ReadTrace({},WORDS+["stage","M"])
                actual=evaluate(r)
                expected_row={"InputBinding":"T01","InputBudget":"T02","InputInvalid":"T03"}[r["child"]]
                check("source-caught-before-poison-"+row["id"]+latch,actual["row"]==expected_row and not r["snapshot"].reads)
        errors.append(dict(row,instantiated_error=error))
    corpus=json.loads((PRE/"cases.json").read_text())
    dispositions=[]
    for case in corpus["terminal_scenarios"]:
        r=base_request(0);name=case["id"];family=case["family"];note=""
        if family=="early-funding":
            stage=case["given"]["failure_at"];r.update(N=0,NC=0,calls=0,progress="Absent")
            caught={"context":(15,3),"profile":(10,4),"header":(10,5),"envelope-setup534":(4,2),"envelope-finish47":(4,8),"G112":(4,8),"semantic-guard128":(4,8)}
            if stage in caught:
                code,errstage=caught[stage];r["child"]="InputBinding" if code==15 else "InputBudget" if code==4 else "InputInvalid"
                note="caught source error code/stage="+str((code,errstage))+"; semantic debit768, no loan"
            else:
                code,errstage={"Budget":(4,1),"T42":(4,2),"F42":(4,8),"semantic-finish256":(4,8),"semantic-setup512":(4,2),"output-safety":(6,8),"arena-allocation":(2,1),"arena-capacity":(3,1)}[stage]
                r["outer_error"]=[code,errstage,0,0,0];note="exact original error preserved; no aggregate or returned payment words"
        elif family=="state-normalization":
            state=case["given"]["state"];finish=case["given"]["finish"]
            r["child"]={"coherent-complete":"Closed","coherent-limited":"Limited","CAP":"Cap"}[finish]
            if state=="invalid-paid-flags":
                dispositions.append({"id":name,"disposition":"unreachable in declared trusted private paid-receipt domain; actual receipt-construction proof remains pending", "Rust_product_tests":0});continue
            tags={"empty-admitted-stream":"Absent","zero-leaf-reply":"Absent","absent-private-state":"Absent","unreadable-private-state":"Unreadable","stale-private-state":"Stale","malformed-status":"Malformed","contradictory-status-reason":"Malformed","invalid-reply-debit":"Poison","nonzero-reserved":"Malformed","invalid-private-budget":"Poison"}
            r["progress"]=tags[state]
            if r["progress"]=="Absent":
                r.update(calls=0,NC=0,N=0);r["child"]="EnvelopeUnavailable"
            note="canonical unreadable guard is Poison; raw unreadable/stale/malformed tags also suppress identically beforeQ"
        elif family=="terminal-overlap":
            first=case["given"]["first_terminal"];tail=case["given"]["tail"]
            latch="Refusal" if first=="ordinary-refusal" else "Failure"
            r=base_request(8,latch,"Closed")
            if tail=="successful-looking-later-reply":r["progress"]="Stale"
            elif tail in ["envelope-refusal","envelope-unavailable","envelope-poison","envelope-invalid-reply-debit"]:
                r["child"]={"envelope-refusal":"EnvelopeRefused","envelope-unavailable":"EnvelopeUnavailable","envelope-poison":"EnvelopePoison","envelope-invalid-reply-debit":"EnvelopePoison"}[tail]
            elif tail=="framing-replay-limit":r["child"]="Limited"
            elif tail in ["framing-IO-limit","late-footer-error","late-read-error","late-input-drift"]:r["child"]="InputInvalid"
            elif tail=="CAP":r["child"]="Cap"
            elif tail=="report-write-error":r["outer_error"]=[6,8,19,0,0]
            if tail=="repeated-Failure":note="legal subsequent envelope Failure is not dispatched semantically; an invalid repeat normalizes EnvelopeRefused, while injected second semantic terminal is T05"
            if tail=="framing-IO-limit":note="actual IO_EXHAUSTED7 invalidates; reserved-I/O budget4 instead maps InputBudget/T02"
        elif family=="outer-error-partition":
            error=case["given"]["error"];r=base_request(8,"Failure")
            if error.startswith(("read-","footer-","EOF-")) or error in ["stream-drift","profile-drift","context-drift"]:
                r["child"]="InputInvalid";note="caught actual source input error; three old member diagnostics remain available"
            else:
                code=8 if error=="write-zero" else 9 if error=="write-overreported" else 7 if error=="write-exhausted" else 14 if "drift" in error else 4 if error in ["report-reserve","postreport-used-exceeds-limit"] else 1 if error=="report-arena-access" else 16 if error=="output-precheck" else 6
                r["outer_error"]=[code,1 if error=="report-arena-access" else 8,0 if error in ["report-reserve","postreport-used-exceeds-limit","output-precheck"] else 19,0,0]
                note="source fixed tuple scoped in accepted-child-error-partition.json; no returned observation after partial or full physical output"
        else:
            state=case["given"]["state"]
            if name.startswith("CAP-"):
                stage={"open-acquire":1,"open-plan":4,"open-Take":8,"open-build":9,"live-pins":0}[state];r=base_request(stage)
            elif state=="Idle-closed":r=base_request(0,"None","Closed")
            elif state=="nonIdle-closed":r=base_request(2,"None","Closed")
            elif state=="expected-mask-read-fails":r["child"]="EnvelopePoison"
            else:r["child"]="Unsupported"
        answer=evaluate(r)
        check("frozen-scenario-resolved-"+name,answer["kind"]=="Err" or len(answer["words"])==32)
        dispositions.append({"id":name,"result":answer,"resolution":note or "explicit ordered row, full32projection and paid receipts fixed by admitted amendment", "implementation_behavior_unproved":True})
    check("all114-preaccess-scenarios-retained",len(dispositions)==114 and len({row["id"] for row in dispositions})==114)
    dump("preaccess-disposition.json",{"scenarios":dispositions,"resolved_as_finite_contract_cases":sum("result" in row for row in dispositions),
         "private_paid_domain_exclusions":sum("disposition" in row for row in dispositions),"Rust_product_tests":0})
    dump("exact-error-partition.json",{"source_cases":errors,"prior_semantic_states_per_error":3,"outer_Err_observation":None,"Rust_product_tests":0})


def producer_literals_as_untrusted_data():
    cases=json.loads((CAND/"expected-cases.json").read_text())["cases"]
    for row in cases:
        check("producer-literal-independent-oracle-"+row["id"],evaluate(row["request"])==row["expected"])
    # Independent model deliberately does not import or execute classifier.py.
    imported=[str(value.__file__) for value in sys.modules.values() if getattr(value,"__file__",None)]
    check("no-producer-model-import",not any("candidate-snapshot" in name or "terminal-correction" in name for name in imported))
    dump("producer-data-comparison.json",{"literal_expected_cases":len(cases),"independent_model_matches":len(cases),
         "producer_classifier_imported_or_executed":False,"old_source_models_harnesses_executed":False})


def funding_and_latch_source_controls():
    records=[]
    # Independently derive the three distinct Budget error sites from the
    # accepted source. Amounts are the proposed extra reservations; this does
    # not establish a source-work bound for missing Rust.
    for amount in [512,534,42]:
        for left,setup_spent,expected in [(amount-1,0,[4,6,0,0,0]),
                                          (amount,65536-amount+1,[4,2,0,0,0]),
                                          (amount,65536-amount,None)]:
            actual=[4,2,0,0,0] if setup_spent+amount>65536 else [4,6,0,0,0] if left<amount else None
            check("setup-method-error-"+str((amount,left,setup_spent)),actual==expected)
            records.append({"kind":"setup","amount":amount,"left":left,"setup_spent":setup_spent,"error":actual})
    for amount in [256,128,112,47,42]:
        for report_spent,expected in [(3_000_000-amount,None),(3_000_000-amount+1,[4,8,0,0,0])]:
            actual=[4,8,0,0,0] if report_spent+amount>3_000_000 else None
            check("report-method-error-"+str((amount,report_spent)),actual==expected)
            records.append({"kind":"report","amount":amount,"spent":report_spent,"error":actual})
    for limit,expected in [(3_263_583,[4,1,0,0,0]),(3_263_584,None),
                           (268_435_456,None),(268_435_457,[4,1,0,0,0])]:
        actual=[4,1,0,0,0] if limit>268_435_456 or limit<3_263_584 else None
        check("new-budget-method-"+str(limit),actual==expected)
    # Source-derived reply-debit and pending predicates at envelope.rs284..297.
    debit_cases=[(425,0,425,1,0,True),(425,1,425,1,0,False),
                 (425,0,0,1,0,False),(0,424,0,2,1,True),
                 (0,425,0,2,1,False),(0,0,0,3,15,True),
                 (0,0,1,3,15,False),(1,0,0,3,15,False)]
    for spent,remaining,debit,status,reason,expected in debit_cases:
        if spent==425:actual=remaining==0 and debit==425
        elif spent!=0 or debit!=0:actual=False
        else:actual=status==3 if reason==15 else reason==1 and status==2 and remaining<425
        check("accepted-source-reply-debit-"+str((spent,remaining,debit,status,reason)),actual==expected)
    for valid,status,reason,expected in [(0,0,0,True),(1,1,0,True),(2,1,0,False),
                                         (1,3,15,False),(1,1,15,False),(1,2,1,False)]:
        actual=valid==0 or (valid==1 and status!=3 and reason!=15 and status==1)
        check("accepted-source-pending-latch-"+str((valid,status,reason)),actual==expected)
    r=base_request();r.update(child="InputInvalid",progress="Absent",calls=0,N=0,NC=1)
    expected=[0]*32;expected[0:2]=[0,3];expected[21:24]=[8448,1,1]
    r["snapshot"]=ReadTrace({},WORDS+["stage","M"])
    check("actual-charge-before-read-no-loan",evaluate(r)["words"]==expected and not r["snapshot"].reads)
    r=base_request();r.update(NC=4_194_304,child="InputBudget")
    check("paid-u64-domain-no-overflow",evaluate(r)["words"][21]==32_212_255_488<2**64)
    for child in ["Closed","Cap","Limited"]:
        for latch,expected_row in [("Refusal","T10"),("Failure","T11"),("Limit","T12")]:
            r=base_request(8,latch,child)
            check("first-latch-before-later-closure-"+child+latch,evaluate(r)["row"]==expected_row)
    dump("funding-latch-controls.json",{"budget_cases":records,"reply_debit_cases":len(debit_cases),"source_pending_cases":6,
         "paid_before_read_fixture32":expected,"source_work_bound_proved":False,"Rust_product_tests":0})


def main():
    for function in [custody_and_declarations,source_normalization,all_terminal_rows_and_shadows,
                     full_word_projection_and_read_sets,malformed_snapshot_and_header_controls,
                     outer_errors_and_preaccess_disposition,producer_literals_as_untrusted_data,
                     funding_and_latch_source_controls]:
        method(function)
    result={"schema":1,"mode":MODE,"scope":"independent source-contract finite-model and custody review only",
            "methods_passed":len(METHODS),"methods":METHODS,"checks_passed":len(CHECKS),
            "checks_sha256":sha("\n".join(CHECKS).encode()),"Rust_product_tests":0,
            "producer_classifier_imported_or_executed":False,"native_device_GA":False,
            "live_VM_read_or_run":False,"root_selection":False}
    dump("result.json",result);print(json.dumps(result,indent=2))


if __name__=="__main__":main()
