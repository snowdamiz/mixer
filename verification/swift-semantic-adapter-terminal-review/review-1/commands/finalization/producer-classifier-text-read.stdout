"""Finite R1 contract model, not a Rust implementation or product analyzer."""
MAX = 2**64-1
CHILDREN = {"InputBinding","InputBudget","InputInvalid","EnvelopePoison",
            "EnvelopeUnavailable","EnvelopeRefused","Limited","Cap","Closed","Unsupported"}
PROGRESS = {"Absent","Valid","Poison","Unreadable","Stale","Malformed"}
LATCHES = {"None","Refusal","Failure","Limit"}

def uint(value):
    return type(value) is int and 0 <= value <= MAX

def normalize_child(f):
    """Closed source/public-result normalization; never call any old code."""
    loop = f["loop"]
    eb, er = f["envelope_boundary"], f["envelope_reason"]
    decision, framed = f["framing_decision"], f["framed"]
    if loop == "input_error":
        code = f["error_code"]
        if type(code) is not int or not 1<=code<=17: return "Unsupported"
        if code == 15:
            return "InputBinding" if (decision,framed,eb,er)==(5,False,0,16) else "Unsupported"
        if code == 4:
            return "InputBudget" if (decision,framed,eb,er)==(4,False,0,18) else "Unsupported"
        return "InputInvalid" if (decision,framed,eb,er)==(3,False,0,17) else "Unsupported"
    if f["flags"] not in (0,1):
        return "Unsupported"
    if loop == "complete" and (decision,framed)==(5,True):
        if (eb,er)==(5,15): return "EnvelopePoison"
        if eb==0 and er in (19,20): return "EnvelopeUnavailable"
        if eb==3 and (1<=er<=14 or er==21): return "EnvelopeRefused"
        if f["flags"]==0 and (eb,er)==(1,0): return "Closed"
        if f["flags"]==1 and (eb,er)==(2,0): return "Cap"
    if loop == "limited" and (decision,framed)==(4,False):
        if (eb,er)==(4,15): return "EnvelopePoison"
        if eb==0 and er in (19,20): return "EnvelopeUnavailable"
        if eb==4 and 1<=er<=14: return "EnvelopeRefused"
        if (eb,er)==(4,18): return "Limited"
    return "Unsupported"

def header_bad(r):
    p, calls, latch = r["progress"], r["calls"], r["latch"]
    if p not in PROGRESS or latch not in LATCHES: return True
    if not uint(calls) or calls>4_194_304: return True
    if r["after_latch_calls"] != 0 or r["second_terminal"] is not False: return True
    if p=="Absent" and (calls!=0 or latch!="None"): return True
    if p=="Valid" and calls==0: return True
    return False

def snapshot_valid(r):
    q = r["snapshot"]
    if not isinstance(q,dict): return False
    required = ("M","seq","work","instructions","stage","residents","bytes","pins","nonce")
    if any(not uint(q.get(k)) for k in required): return False
    m, n, stage = q["M"],r["N"],q["stage"]
    if stage>10 or not uint(n) or n>4_194_304 or m>n or q["seq"]!=m: return False
    if n>r["NC"] or r["calls"]>r["NC"]: return False
    if not (1<=r["slots"]<=64 and 1<=r["pin_slots"]<=64): return False
    if q["residents"]>r["slots"] or q["pins"]>r["pin_slots"] or q["nonce"]==0: return False
    if (q["residents"]==0)!=(q["bytes"]==0) or (q["pins"]>0 and q["residents"]==0): return False
    latch = r["latch"]
    reason = r["latch_reason"]
    if latch=="None":
        if reason!=0 or r["stop"]!=0 or m!=n or r["calls"]!=m or m==0: return False
        if r["child"]=="Closed" and stage!=0: return False
    else:
        if r["stop"]!=m+1 or r["stop"]>n or r["calls"]!=m+1: return False
        if latch=="Refusal" and not (type(reason) is int and 6<=reason<=13): return False
        if latch=="Failure" and reason!=14: return False
        if latch=="Limit" and reason!=1: return False
    if m==0 and (q["work"],q["instructions"],stage,q["residents"],q["bytes"],q["pins"],q["nonce"])!=(0,0,0,0,0,0,1): return False
    if stage!=0 and (not uint(q.get("op")) or q["op"]==0 or not uint(q.get("function")) or q["function"]>=80_000): return False
    if 6<=stage<=10:
        if any(not uint(q.get(k)) for k in ("selected","taken","committed")): return False
        selected,taken,committed=q["selected"],q["taken"],q["committed"]
        if selected>>r["slots"] or taken & ~selected or committed & ~taken: return False
        if type(q.get("feasible")) is not bool: return False
        if q["feasible"] and (not uint(q.get("destination")) or q["destination"]>=r["slots"]): return False
        if stage in (7,8):
            if not q["feasible"] or not uint(q.get("pending")) or q["pending"]>=r["slots"]: return False
            if not (selected & (1<<q["pending"])): return False
    return True

def paid(r):
    # Trusted private paid-receipt domain; not an arbitrary public model input.
    return 512*r["SS"]+256*r["SF"]+7680*r["NC"]

def suppressed(r,row,boundary,reason):
    out=[0]*32
    out[0:2]=[boundary,reason]
    out[21:24]=[paid(r),r["SS"],r["SF"]]
    return {"kind":"Ok","row":row,"words":out}

def visible(r,row,boundary,reason,stop,failure,tail):
    q=r["snapshot"];stage=q["stage"]
    active=stage!=0;miss=3<=stage<=10;planned=6<=stage<=10;pending=stage in (7,8)
    out=[boundary,reason,r["N"],q["M"],stop,q["M"],q["work"],q["instructions"],
         q["op"] if active else 0,q["function"] if active else MAX,
         q["residents"],q["bytes"],q["pins"],q["nonce"],
         q["function"]&511 if miss else MAX,
         q["selected"] if planned else 0,q["taken"] if planned else 0,
         q["committed"] if planned else 0,q["pending"] if pending else MAX,
         q["destination"] if planned and q["feasible"] else MAX,
         failure,paid(r),r["SS"],r["SF"],1,tail,0,0,0,0,0,0]
    return {"kind":"Ok","row":row,"words":out}

def classify(r):
    if r["outer_error"] is not None:
        return {"kind":"Err","row":"T00","error":r["outer_error"],"words":None}
    c=r["child"] if r["child"] in CHILDREN else "Unsupported"
    if c=="InputBinding": return suppressed(r,"T01",0,2)
    if c=="InputBudget": return suppressed(r,"T02",4,1)
    if c=="InputInvalid": return suppressed(r,"T03",0,3)
    if c=="EnvelopePoison" or r["progress"]=="Poison": return suppressed(r,"T04",5,16)
    if r["progress"] in ("Unreadable","Stale","Malformed") or header_bad(r): return suppressed(r,"T05",5,16)
    if c in ("EnvelopeUnavailable","Unsupported"): return suppressed(r,"T06",0,5)
    if c=="EnvelopeRefused": return suppressed(r,"T07",3,4)
    if r["progress"]=="Absent": return suppressed(r,"T08",0,5)
    if not snapshot_valid(r): return suppressed(r,"T09",5,16)
    if r["latch"]=="Refusal": return visible(r,"T10",3,r["latch_reason"],r["stop"],0,1)
    if r["latch"]=="Failure": return visible(r,"T11",6,14,r["stop"],r["stop"],1)
    if r["latch"]=="Limit": return visible(r,"T12",4,1,r["stop"],0,1)
    if c=="Limited": return visible(r,"T13",4,1,r["N"]+1,0,1)
    if c=="Cap": return visible(r,"T14",2,0,0,0,1)
    # Residual closed domain has coherent Closed child and no latch.
    return visible(r,"T15",1,0,0,0,0)
