"""Independent source-contract oracle. No producer source is imported/executed.

The accepted-child function below is a handwritten finite source model of the
frozen Rust finalizer/core, not execution of Rust or a product test. The semantic
selector uses the corrected contract; this module does not implement semantics.
"""
from collections.abc import Mapping

MAX = (1 << 64) - 1
WORDS = ("boundary reason observed_records cache_state_records stop_record "
         "last_sequence last_work last_instructions active_operation requested_function "
         "resident_count resident_bytes held_pins next_nonce active_plan_cell "
         "selected_mask taken_mask committed_mask pending_victim destination "
         "failure_coordinate semantic_debit semantic_setup_paid semantic_finish_paid "
         "fixture_state_observed tail_unknown stored_prefix_validated full_replay_accepted "
         "semantic_metrics_valid real_binding_verified reserved0 reserved1").split()


def u64(value):
    return type(value) is int and 0 <= value <= MAX


class ReadTrace(dict):
    def __init__(self, values, forbidden=()):
        super().__init__(values)
        self.forbidden = set(forbidden)
        self.reads = []

    def __getitem__(self, key):
        if key in self.forbidden:
            raise RuntimeError("forbidden snapshot read: " + key)
        self.reads.append(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        self.reads.append(key)
        return default


def snapshot_problem(receipt):
    """Named independent predicates, evaluated only at the eligible read gate."""
    q = receipt["snapshot"]
    if not isinstance(q, Mapping): return "Q0-object"
    for key in ("M", "seq", "work", "instructions", "stage", "residents", "bytes", "pins", "nonce"):
        if not u64(q.get(key)): return "Q0-" + key
    stage, m, n = q["stage"], q["M"], receipt["N"]
    if stage not in range(11): return "Q0-stage"
    if not u64(n) or n > 4_194_304 or m > n or q["seq"] != m: return "Q1-coordinate"
    if n > receipt["NC"] or receipt["calls"] > receipt["NC"]: return "Q1-paid"
    if not 1 <= receipt["slots"] <= 64 or not 1 <= receipt["pin_slots"] <= 64: return "Q1-limits"
    if q["residents"] > receipt["slots"] or q["pins"] > receipt["pin_slots"] or q["nonce"] < 1: return "Q2-counts"
    if (q["residents"] == 0) != (q["bytes"] == 0): return "Q2-bytes"
    if q["pins"] and not q["residents"]: return "Q2-pins"
    latch = receipt["latch"]
    if latch == "None":
        if (receipt["latch_reason"], receipt["stop"], m, receipt["calls"]) != (0, 0, n, m) or m == 0:
            return "Q3-none"
        if receipt["child"] == "Closed" and stage != 0: return "Q3-closed"
    else:
        if receipt["stop"] != m + 1 or receipt["stop"] > n or receipt["calls"] != m + 1:
            return "Q4-coordinate"
        allowed = {"Refusal": set(range(6, 14)), "Failure": {14}, "Limit": {1}}[latch]
        if type(receipt["latch_reason"]) is not int or receipt["latch_reason"] not in allowed:
            return "Q4-reason"
    if not m and tuple(q[key] for key in ("work", "instructions", "stage", "residents", "bytes", "pins", "nonce")) != (0,0,0,0,0,0,1):
        return "Q5-initial"
    if stage:
        if not u64(q.get("op")) or q["op"] == 0 or not u64(q.get("function")) or q["function"] >= 80_000:
            return "Q6-active"
    if stage >= 6:
        for key in ("selected", "taken", "committed"):
            if not u64(q.get(key)): return "Q7-" + key
        if q["selected"] >> receipt["slots"] or q["taken"] & ~q["selected"] or q["committed"] & ~q["taken"]:
            return "Q7-subsets"
        if type(q.get("feasible")) is not bool: return "Q7-feasible"
        if q["feasible"] and (not u64(q.get("destination")) or q["destination"] >= receipt["slots"]):
            return "Q8-destination"
        if stage in (7,8):
            if not q["feasible"] or not u64(q.get("pending")) or q["pending"] >= receipt["slots"]:
                return "Q9-pending"
            if q["selected"] & (1 << q["pending"]) == 0: return "Q9-selected"
    return None


def header_problem(r):
    if r["progress"] not in {"Absent","Valid","Poison","Unreadable","Stale","Malformed"}: return "tag"
    if r["latch"] not in {"None","Refusal","Failure","Limit"}: return "latch"
    if not u64(r["calls"]) or r["calls"] > 4_194_304: return "calls"
    if r["after_latch_calls"] != 0 or r["second_terminal"] is not False: return "resume"
    if r["progress"] == "Absent" and (r["calls"] or r["latch"] != "None"): return "absent"
    if r["progress"] == "Valid" and not r["calls"]: return "valid-without-call"
    return None


def project(r, boundary, reason, visible, stop=0, failure=0, tail=0):
    # A name-to-value projection differs from the producer's positional array.
    fields = dict.fromkeys(WORDS, 0)
    fields.update(boundary=boundary, reason=reason,
                  semantic_debit=512*r["SS"] + 256*r["SF"] + 7680*r["NC"],
                  semantic_setup_paid=r["SS"], semantic_finish_paid=r["SF"])
    if visible:
        q = r["snapshot"]
        stage = q["stage"]
        fields.update(observed_records=r["N"], cache_state_records=q["M"],
                      stop_record=stop, last_sequence=q["M"], last_work=q["work"],
                      last_instructions=q["instructions"], resident_count=q["residents"],
                      resident_bytes=q["bytes"], held_pins=q["pins"], next_nonce=q["nonce"],
                      active_operation=0, requested_function=MAX, active_plan_cell=MAX,
                      pending_victim=MAX, destination=MAX, failure_coordinate=failure,
                      fixture_state_observed=1, tail_unknown=tail)
        if stage:
            fields.update(active_operation=q["op"], requested_function=q["function"])
        if stage >= 3: fields["active_plan_cell"] = q["function"] % 512
        if stage >= 6:
            for output, key in (("selected_mask","selected"),("taken_mask","taken"),("committed_mask","committed")):
                fields[output] = q[key]
            if q["feasible"]: fields["destination"] = q["destination"]
        if stage in (7,8): fields["pending_victim"] = q["pending"]
    return [fields[word] for word in WORDS]


def evaluate(r):
    """Evaluate hazard layers, then the visible terminal product table."""
    if r["outer_error"] is not None:
        return {"kind":"Err","row":"T00","error":r["outer_error"],"words":None}
    c = r["child"]
    if c not in {"InputBinding","InputBudget","InputInvalid","EnvelopePoison","EnvelopeUnavailable","EnvelopeRefused","Limited","Cap","Closed","Unsupported"}:
        c = "Unsupported"
    failures = {"InputBinding":("T01",0,2),"InputBudget":("T02",4,1),"InputInvalid":("T03",0,3)}
    selected = failures.get(c)
    if selected is None and (c == "EnvelopePoison" or r["progress"] == "Poison"):
        selected = ("T04",5,16)
    if selected is None and (r["progress"] in {"Unreadable","Stale","Malformed"} or header_problem(r)):
        selected = ("T05",5,16)
    if selected is None:
        selected = {"EnvelopeUnavailable":("T06",0,5),"Unsupported":("T06",0,5),"EnvelopeRefused":("T07",3,4)}.get(c)
    if selected is None and r["progress"] == "Absent": selected = ("T08",0,5)
    if selected is not None:
        row,boundary,reason=selected
        return {"kind":"Ok","row":row,"words":project(r,boundary,reason,False)}
    problem = snapshot_problem(r)
    if problem:
        return {"kind":"Ok","row":"T09","words":project(r,5,16,False)}
    # Table composition rather than a copy of the producer's terminal chain.
    latch = r["latch"]
    m = r["snapshot"]["M"]
    terminals = {"Refusal":("T10",3,r["latch_reason"],m+1,0,1),
                 "Failure":("T11",6,14,m+1,m+1,1),
                 "Limit":("T12",4,1,m+1,0,1)}
    final = terminals.get(latch)
    if final is None:
        final = {"Limited":("T13",4,1,r["N"]+1,0,1),
                 "Cap":("T14",2,0,0,0,1),"Closed":("T15",1,0,0,0,0)}[c]
    row,boundary,reason,stop,failure,tail=final
    return {"kind":"Ok","row":row,"words":project(r,boundary,reason,True,stop,failure,tail)}


def normalize_public(f):
    """Independent allowed-pair relation, derived from accepted Rust branches."""
    pair = f["envelope_boundary"], f["envelope_reason"]
    if f["loop"] == "input_error":
        code=f["error_code"]
        if type(code) is not int or code not in range(1,18): return "Unsupported"
        expected = (5,0,16,"InputBinding") if code == 15 else (4,0,18,"InputBudget") if code == 4 else (3,0,17,"InputInvalid")
        return expected[3] if (f["framing_decision"],f["framed"],*pair)==(expected[0],False,expected[1],expected[2]) else "Unsupported"
    if f["flags"] not in (0,1): return "Unsupported"
    mode = {("complete",5,True):"complete",("limited",4,False):"limited"}.get((f["loop"],f["framing_decision"],f["framed"]))
    if mode is None: return "Unsupported"
    pairs={(0,19):"EnvelopeUnavailable",(0,20):"EnvelopeUnavailable"}
    if mode == "limited":
        pairs.update({(4,reason):"EnvelopeRefused" for reason in range(1,15)})
        pairs.update({(4,15):"EnvelopePoison",(4,18):"Limited"})
    else:
        pairs.update({(3,reason):"EnvelopeRefused" for reason in list(range(1,15))+[21]})
        pairs[(5,15)]="EnvelopePoison"
        pairs[(2,0) if f["flags"] else (1,0)] = "Cap" if f["flags"] else "Closed"
    return pairs.get(pair,"Unsupported")


def accepted_child_source(raw):
    """Finite handwritten old finalize/core abstraction from original source.

    Return the exact boundary/reason/framing quartet and named source branch.
    This deliberately accepts raw private source atoms, unlike the correction's
    public normalization model. It executes no copied Rust or old harness.
    """
    error=raw["input_error"]
    if error is not None:
        decision=5 if error==15 else 4 if error==4 else 3
        reason=16 if error==15 else 18 if error==4 else 17
        return (decision,False,0,reason,"input-error")
    decision=4 if raw["limited"] else 5
    framed=False if raw["limited"] else raw["input_ok"]
    coherent=((raw["complete"] and not raw["limited"] and raw["input_ok"] is True)
              or (raw["limited"] and not raw["complete"] and raw["input_ok"] is False))
    if raw["flags"]>1 or not coherent: return (decision,framed,0,20,"loop-incoherent")
    valid=raw["reply_valid"]
    if valid==0: return (decision,framed,0,19,"no-reply")
    if valid!=1: return (decision,framed,0,20,"invalid-validity")
    status,reason=raw["status"],raw["reason"]
    if status==3 or reason==15:
        return (decision,framed,4 if raw["limited"] else 5,15,"poison")
    malformed=(status not in (1,2) or reason>14 or (status==1 and reason!=0)
               or (status==2 and reason==0) or raw["stage"]>10 or raw["phase"]>5
               or raw["mask"]>=64 or raw["pin_failure"]>1 or raw["terminal_failure"]>1)
    if malformed: return (decision,framed,0,20,"reply-malformed")
    if raw["limited"]: return (decision,framed,4,reason if status==2 else 18,"limited-refusal" if status==2 else "limited-observed")
    if status==2: return (decision,framed,3,reason,"refusal")
    if raw["flags"]==1: return (decision,framed,2,0,"CAP")
    if not raw["expected_readable"]: return (decision,framed,5,15,"expected-read-failed")
    if raw["stage"]==0 and raw["phase"]==5 and raw["mask"]==raw["expected_mask"]:
        return (decision,framed,1,0,"closed")
    return (decision,framed,3,21,"incomplete")


def base_request(stage=0, latch="None", child="Cap"):
    m=27
    return {"outer_error":None,"child":child,"progress":"Valid","calls":m+(latch!="None"),
            "after_latch_calls":0,"second_terminal":False,"latch":latch,
            "latch_reason":{"None":0,"Refusal":7,"Failure":14,"Limit":1}[latch],
            "stop":0 if latch=="None" else m+1,"N":m if latch=="None" else 31,
            "NC":31,"SS":1,"SF":1,"slots":3,"pin_slots":4,
            "snapshot":{"M":m,"seq":m,"work":211,"instructions":233,"stage":stage,
                        "op":7,"function":529,"residents":2,"bytes":95,"pins":1,"nonce":9,
                        "selected":3,"taken":1,"committed":0,"pending":0,
                        "destination":1,"feasible":True}}
