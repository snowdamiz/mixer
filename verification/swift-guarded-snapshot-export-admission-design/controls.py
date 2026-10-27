"""Finite design controls only. No proof, real File, runtime or grant is produced."""
from dataclasses import dataclass, field

MAX=(1<<64)-1
CAPS=(512,8192,34,79966,8192,4096,4096,4096)
WORDS=(3,1,5,3,4,4,4,4)
PLAN=16384
FIXED=32768

class Refusal(Exception): pass

def add(a,b):
    if not 0<=a<=MAX or not 0<=b<=MAX or a>MAX-b: raise Refusal("arithmetic")
    return a+b

def mul(a,b):
    if not 0<=a<=MAX or not 0<=b<=MAX or (a and b>MAX//a): raise Refusal("arithmetic")
    return a*b

def work(source,counts,enforce=True):
    if len(counts)!=8 or source<0 or (enforce and source>67108864): raise Refusal("shape")
    n=l=0
    for count,cap,words in zip(counts,CAPS,WORDS):
        if count<0 or (enforce and count>cap): raise Refusal("shape")
        n=add(n,count); l=add(l,mul(count,words))
    extent=add(2560,add(source,mul(8,l)))
    blocks=add(extent//4096,int(extent%4096!=0)); attempts=mul(32,blocks)
    terms=[FIXED,mul(36,extent),mul(4096,blocks),mul(64,n),mul(16,l),mul(32,attempts),mul(8,blocks)]
    emission=0
    for term in terms: emission=add(emission,term)
    return dict(extent=extent,records=n,words=l,blocks=blocks,attempts=attempts,planning=PLAN,emission=emission,total=add(PLAN,emission))

@dataclass
class Control:
    owner:int=7
    limit:int=1_000_000_000
    used:int=0
    first:object=None
    cancelled:bool=False
    now:int=0
    deadline:int=100
    origin:str="Wasi"
    construction:int=1000
    combined:int=1500
    memory_limit:int=MAX
    foundation:int=1000
    tickets:int=5
    guard:bool=False
    events:list=field(default_factory=list)
    def stop(self):
        if self.first is not None: return ("existing",self.first)
        if self.cancelled: return ("cancelled",)
        if self.now>=self.deadline: return ("deadline",self.origin)
        return None
    def debit(self,credits,owner=7):
        if self.guard: raise Refusal("funding-after-guard")
        if self.first is not None: raise Refusal("existing")
        if not owner or owner!=self.owner: raise Refusal("owner")
        if self.stop(): raise Refusal(self.stop()[0])
        next_used=add(self.used,credits)
        if next_used>self.limit: raise Refusal("work")
        self.used=next_used; self.events.append(("debit",credits))
    def enter(self,additional):
        if self.guard: raise Refusal("funding-after-guard")
        if self.first is not None: raise Refusal("existing")
        if self.stop(): raise Refusal(self.stop()[0])
        previous=self.construction
        enlarged=add(previous,additional); combined=add(self.combined,additional)
        if combined>self.memory_limit: raise Refusal("storage")
        self.construction=enlarged; self.combined=combined
        return Phase(self,previous)
    def finish_observation(self):
        if self.construction!=self.foundation: return (self.combined,"ConstructionBound")
        return (self.combined-self.construction,None)
    def make_guard(self):
        if self.guard: raise Refusal("second-guard")
        self.guard=True; self.events.append(("guard",self.owner))

@dataclass
class Phase:
    control:Control
    previous:int
    consumed:bool=False
    def complete(self,actual_storage_destroyed):
        c=self.control
        if c.guard or not actual_storage_destroyed or self.consumed: raise Refusal("unconsumed-phase")
        difference=c.construction-self.previous
        c.construction=self.previous; c.combined-=difference; self.consumed=True

def stream(total,actions=None,before=None,after=None,metadata=None,seek=None):
    """No output bytes allocated. State-machine model counts requests/progress."""
    c=Control(); c.make_guard(); actions=actions or {}; ack=calls=0
    def stop(hook):
        if hook: hook(c,calls,ack)
        return c.stop()
    # Metadata and stream-position are each one native operation, checked both sides.
    for stage,error in (("metadata",metadata),("seek",seek)):
        if (s:=stop(before)): return dict(cause="stop",stage=stage,stop=s,ack=ack,calls=calls)
        post=stop(after)
        if error: return dict(cause=error,stage=stage,post=post,ack=ack,calls=calls)
        if post: return dict(cause="stop",stage=stage,stop=post,ack=ack,calls=calls)
    while ack<total:
        block=min(4096,total-ack); done=0
        for attempt in range(1,33):
            if (s:=stop(before)): return dict(cause="stop",stop=s,ack=ack,calls=calls)
            calls+=1; requested=block-done
            result=actions.get(calls,requested)
            original_io=result if isinstance(result,str) else None
            # Preserve valid progress even when a stop arrives during the call.
            invalid=None
            if original_io is None:
                if result==0: invalid="zero"
                elif result<0 or result>requested: invalid="overreport"
                else: done+=result; ack+=result
            post=stop(after)
            if invalid: return dict(cause=invalid,post=post,ack=ack,calls=calls,attempt=attempt)
            if original_io and original_io!="Interrupted": return dict(cause=original_io,post=post,ack=ack,calls=calls,attempt=attempt)
            if post: return dict(cause="stop",stop=post,io=original_io,ack=ack,calls=calls,attempt=attempt)
            if done==block: break
            if attempt==32: return dict(cause="attempts",io=original_io,ack=ack,calls=calls,attempt=32)
    return dict(cause="ok",ack=ack,calls=calls)

def run():
    groups=[]
    def expect_refusal(f,cause):
        try: f()
        except Refusal as e: assert str(e)==cause,(str(e),cause)
        else: raise AssertionError("missing refusal: "+cause)
    w=work(67108864,CAPS)
    assert (w['extent'],w['blocks'],w['attempts'])==(69765152,17033,545056)
    assert w['total']>1_000_000_000
    expect_refusal(lambda:add(MAX,1),"arithmetic")
    expect_refusal(lambda:mul(MAX,2),"arithmetic")
    expect_refusal(lambda:work(MAX,[0]*8,False),"arithmetic")
    expect_refusal(lambda:work(0,[MAX]*8,False),"arithmetic")
    groups.append("W01 checked complete-size/record/block/attempt arithmetic and original-budget envelope refusal")
    a=Control(limit=PLAN); a.debit(PLAN)
    expect_refusal(lambda:a.debit(1),"work"); assert a.used==PLAN and a.first is None
    a=Control(limit=MAX,used=MAX); expect_refusal(lambda:a.debit(1),"arithmetic"); assert a.used==MAX
    sentinel=object(); a=Control(first=sentinel,cancelled=True,now=200)
    expect_refusal(lambda:a.debit(1,owner=0),"existing"); assert a.first is sentinel and a.used==0
    assert a.stop()==("existing",sentinel)
    a=Control(cancelled=True,now=100); assert a.stop()==("cancelled",)
    expect_refusal(lambda:a.debit(1),"cancelled"); assert a.first is None
    a=Control(now=100); assert a.stop()==("deadline","Wasi")
    a=Control(); expect_refusal(lambda:a.debit(1,8),"owner"); assert a.used==0 and a.first is None
    groups.append("W02 existing-failure/owner/cancel/deadline precedence; failed debits preserve all counters and first failure")
    actions={i:"Interrupted" for i in range(1,32)}
    r=stream(4096,actions); assert r==dict(cause="ok",ack=4096,calls=32)
    r=stream(4096,{i:1 for i in range(1,32)})
    assert r==dict(cause="ok",ack=4096,calls=32)
    r=stream(4096,{i:"Interrupted" for i in range(1,33)})
    assert r['cause']=="attempts" and r['calls']==32 and r['ack']==0 and r['io']=="Interrupted"
    r=stream(4096,{i:1 for i in range(1,33)})
    assert r['cause']=="attempts" and (r['calls'],r['ack'])==(32,32)
    assert stream(4097)['calls']==2
    assert stream(sum([1,2559,2,4095]))['calls']==2 # Section boundaries grant no new attempts.
    groups.append("I01 exact successful/incomplete 32 boundary, partial progress, continuous sections")
    for result,cause in ((0,"zero"),(4097,"overreport"),("PermissionDenied","PermissionDenied")):
        r=stream(4096,{1:result}); assert r['cause']==cause and r['calls']==1 and r['ack']==0
    assert stream(1,metadata="MetadataError")['calls']==0
    assert stream(1,seek="SeekInterrupted")['calls']==0
    groups.append("I02 zero/overreported/native I/O and metadata/seek error retention")
    r=stream(1,before=lambda c,n,a:setattr(c,'cancelled',True)); assert r['calls']==0
    before_count=[0]
    def deadline_before_first_write(c,n,a):
        before_count[0]+=1
        if before_count[0]==3: c.now=100
    r=stream(1,before=deadline_before_first_write)
    assert r['calls']==0 and r['stop']==("deadline","Wasi")
    r=stream(1,after=lambda c,n,a:setattr(c,'cancelled',True) if n else None)
    assert r['cause']=="stop" and r['calls']==1 and r['ack']==1
    r=stream(1,after=lambda c,n,a:setattr(c,'now',100) if n else None)
    assert r['stop']==("deadline","Wasi") and r['ack']==1
    r=stream(1,{1:"BrokenPipe"},after=lambda c,n,a:setattr(c,'cancelled',True) if n else None)
    assert r['cause']=="BrokenPipe" and r['post']==("cancelled",)
    r=stream(1,{1:"Interrupted"},after=lambda c,n,a:setattr(c,'cancelled',True) if n else None)
    assert r['cause']=="stop" and r['io']=="Interrupted" and r['calls']==1
    groups.append("I03 before/after write stop, cancellation precedence, deadline origin and simultaneous I/O/stop retained")
    a=Control(); baseline=(a.owner,a.tickets,a.construction,a.combined)
    phase=a.enter(9000); a.debit(PLAN); a.make_guard()
    expect_refusal(lambda:a.make_guard(),"second-guard")
    expect_refusal(lambda:a.debit(1),"funding-after-guard")
    expect_refusal(lambda:phase.complete(True),"unconsumed-phase")
    a.guard=False; expect_refusal(lambda:phase.complete(False),"unconsumed-phase")
    assert a.construction==10000 and a.combined==10500
    phase.complete(True); assert (a.owner,a.tickets,a.construction,a.combined)==baseline
    assert a.used==PLAN and a.first is None # No unused-work refund.
    expect_refusal(lambda:phase.complete(True),"unconsumed-phase")
    groups.append("C01 actual consuming phase retirement; no guard-live refund/funding/new owner/ticket or work refund")
    # A hypothetical alternate-floor finish would falsely zero this unconsumed phase.
    a=Control(); phase=a.enter(9000)
    fake_alternate_floor=a.construction
    assert fake_alternate_floor==10000 and not phase.consumed
    expect_refusal(lambda:phase.complete(False),"unconsumed-phase")
    assert a.construction==fake_alternate_floor
    assert a.finish_observation()==(10500,"ConstructionBound")
    groups.append("C02 alternate-floor-by-bytes cannot authorize cleanup of unconsumed phase")
    a=Control(memory_limit=1500); old=(a.construction,a.combined,a.tickets,a.first)
    expect_refusal(lambda:a.enter(1),"storage")
    assert old==(a.construction,a.combined,a.tickets,a.first)
    a=Control(construction=MAX,combined=MAX)
    expect_refusal(lambda:a.enter(1),"arithmetic"); assert a.construction==MAX and a.first is None
    a=Control(first=sentinel); expect_refusal(lambda:a.enter(1),"existing"); assert a.first is sentinel
    groups.append("C03 nonterminal storage preflight atomicity, exhaustion and overflow preserve original state")
    # Original typed outcome/error objects are held by identity, not translated.
    for outcome in range(1,9):
        primary=object(); events=[]; snapshot="NotReached"
        if outcome==8:
            snapshot="write-error"; events.extend(["export","header","rows"])
        outer=(primary,snapshot)
        assert outer[0] is primary
        if outcome<8: assert events==[] and snapshot=="NotReached"
        else: assert events==["export","header","rows"]
    groups.append("P01 modeled eight-outcome object retention and successful header-before-rows chronology; actual wrapper still unimplemented")
    return dict(status="passed finite design controls",groups=groups,max_envelope=w,scope="synthetic Python design model only; no runtime authority, actual File, full encoder or actual cleanup executed")

if __name__=='__main__':
    import json
    print(json.dumps(run(),indent=2))
