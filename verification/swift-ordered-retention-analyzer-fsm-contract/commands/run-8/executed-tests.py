"""Independent expected paths/matrix; imports only this finite model."""
import unittest
from dataclasses import replace
from model import (State, Reply, observe, finish, initial, shape, FixtureEnvelope,
                   MAX, MAX32, RECORD_DEBIT, CANDIDATE_SETUP_DEBIT,
                   CELLS, ARENA_BASE)

def event(k, s, **kw):
    # Test data construction is not used by the model or as a validity oracle.
    op = 0 if k in (12,13) else (s.operation + 1 if k == 1 else s.active_op)
    f = 34 if k == 1 else s.function
    w = [s.accepted+1,k,s.phase,op,s.work+1,s.instructions+2,f,100,7,2,MAX,MAX,0,0,0,0]
    if k == 1:
        w[7:10] = [MAX]*3
    elif k == 2:
        pass  # Miss form, overwritten explicitly in hit paths.
    elif k == 3:
        w[15] = f & 511
    elif k == 4:
        w[14:16] = [MAX,f & 511]
    elif k == 5:
        w[13:16] = [8,16,64]
    elif k in (6,7,8):
        w[10],w[13] = 1,8
    elif k in (9,10):
        w[13] = 8
    elif k == 11:
        w[10:16] = [1,2,3,1 if s.state == 10 else 0,8,1]
    elif k == 12:
        w[6:16] = [72,200,MAX,4,1,2,3,8,0,0]
    elif k == 13:
        w[2],w[6:10],w[13] = 4,[MAX]*4,4
    elif k == 14:
        w[3] = 0 if s.state == 0 else s.active_op
        w[6:10],w[13:16] = [MAX]*4,[2,1,2]
    indexes = dict(seq=0,kind=1,phase=2,op=3,work=4,ins=5,function=6,
                   offset=7,length=8,type=9,slot=10,pin=11,nonce=12,a=13,b=14,c=15)
    for key,value in kw.items():
        w[indexes[key]] = value
    return tuple(w)

def run_path(path):
    s = State()
    seen = [s]
    for kind,kwargs in path:
        r = observe(s,event(kind,s,**kwargs))
        assert r.reason == 'Observed', (kind,r.reason,s)
        s = r.state
        seen.append(s)
    return seen

HIT = [(1,{}),(2,dict(a=1,slot=0)),(11,dict(a=0))]
MISS = [(1,{}),(2,{}),(3,{}),(4,{}),(5,{}),(9,{}),(10,{}),(11,dict(a=1))]
EVICT = [(1,{}),(2,{}),(3,{}),(4,dict(a=1,b=77)),(5,{}),
         (6,{}),(7,{}),(8,{}),(6,{}),(7,{}),(8,{}),(9,{}),(10,{}),(11,dict(a=1))]

def states():
    gathered = run_path(HIT)+run_path(EVICT)
    return {s.state:s for s in gathered}

class EnvelopeTests(unittest.TestCase):
    def test_source_u32_type_width_all_full_forms_and_release(self):
        contexts=((1,2),(3,3),(4,4),(5,5),(6,6),(7,7),(8,8),
                  (6,9),(9,10),(2,11),(0,12))
        for stage,kind in contexts:
            s=states()[stage]
            for typ,ok in ((0,True),(MAX32,True),(MAX32+1,False),(MAX-1,False),(MAX,False)):
                w=event(kind,s,type=typ)
                with self.subTest(stage=stage,kind=kind,type=typ):
                    self.assertEqual(shape(w),ok)
                    self.assertEqual(observe(s,w).reason=='Observed',ok)

    def test_exact_independent_width_reproductions_now_refused(self):
        for typ in (4294967296,18446744073709551614):
            lookup=(1,2,0,7,0,0,34,100,7,typ,MAX,MAX,0,0,0,0)
            release=(1,12,0,0,0,0,34,100,MAX,typ,0,0,1,8,0,0)
            s=State(state=1,active_op=7,function=34)
            self.assertEqual(observe(s,lookup).reason,'Shape')
            self.assertEqual(observe(State(),release).reason,'Shape')

    def test_retained_candidate_initialized_once_and_borrowed_across_calls(self):
        owner=FixtureEnvelope.create()
        identity=id(owner._candidate)
        self.assertEqual(len(owner._candidate),2048)
        self.assertEqual(owner._candidate,bytes(2048))
        self.assertEqual(owner._remaining,268435456-534)
        for kind,kwargs in MISS:
            r=owner.step(event(kind,owner._state,**kwargs))
            self.assertEqual(r.reason,'Observed')
            self.assertEqual(id(owner._candidate),identity)
            self.assertEqual(owner._candidate[:888],bytes(888))
            self.assertEqual(owner._candidate[984:],bytes(2048-984))
        self.assertEqual(owner._remaining,268435456-534-128*len(MISS))
        before=bytes(owner._candidate)
        self.assertEqual(owner.step(event(1,owner._state,type=0)).reason,'Shape')
        self.assertEqual(id(owner._candidate),identity)
        self.assertEqual(bytes(owner._candidate),before)
        owner.close()
        self.assertIsNone(owner._candidate)
        with self.assertRaises(ValueError):owner.step((0,)*16)

    def test_candidate_setup_admission_and_disjoint_phase_accounting(self):
        self.assertEqual(CANDIDATE_SETUP_DEBIT,256+256+12+2+4+4)
        for remaining in (0,533):
            self.assertIsNone(FixtureEnvelope.create(49,remaining))
        self.assertIsNone(FixtureEnvelope.create(0,534))
        owner=FixtureEnvelope.create(49,534)
        r=owner.step(event(1,owner._state))
        self.assertEqual((r.reason,r.steps),('Steps',0))
        self.assertEqual(owner._candidate,bytes(2048))
        # No helper return/source/copy owner overlaps the retained candidate.
        self.assertEqual(4520+8+8,4536)
        self.assertEqual(4096+16+32+16+16+8+8+8+16+384+128,4728)
        self.assertLessEqual(max(4536,4728),5120)

    def test_poison_propagates_through_cap_and_noncap_finish(self):
        s=states()[1]
        r=observe(s,event(2,s),fault='commit')
        for cap in (False,True):
            self.assertEqual(finish(r.state,cap),'InternalPoisoned')
            self.assertEqual(finish(r,cap),'InternalPoisoned')
            self.assertEqual(finish(Reply('InternalPoisoned',State(),128),cap),'InternalPoisoned')
            self.assertEqual(finish(object(),cap),'UnavailableState')
        owner=FixtureEnvelope.create()
        owner.step(event(1,owner._state))
        owner.step(event(2,owner._state),fault='commit')
        for cap in (False,True):self.assertEqual(owner.finish(cap),'InternalPoisoned')
        again=owner.step((0,)*16)
        self.assertEqual((again.reason,again.state,again.steps),('InternalPoisoned',None,0))
        self.assertFalse(again.fullReplayAccepted or again.storedPrefixValidated or again.semanticMetricsValid)

    def test_closed_or_invalid_fixture_owner_never_has_normal_finish(self):
        for cap in (False,True):
            self.assertEqual(finish(None,cap),'InternalPoisoned')
            self.assertEqual(finish('Idle',cap),'UnavailableState')
            owner=FixtureEnvelope.create()
            owner.close()
            self.assertEqual(owner.finish(cap),'UnavailableState')

    def test_initial_expected_mask_admission(self):
        for mask in range(65):
            self.assertEqual(initial(mask) is not None,mask<64 and mask&33==33)
        for value in (-1,MAX,True,1.0):
            self.assertIsNone(initial(value))

    def test_independent_11_by_14_matrix(self):
        # Literal accepted-kind sets, authored separately from model transitions.
        legal = {0:{1,12,13,14},1:{2,14},2:{11,14},3:{3,14},
                 4:{4,14},5:{5,14},6:{6,9,14},7:{7,14},8:{8,14},
                 9:{10,14},10:{11,14}}
        current = states()
        self.assertEqual(set(current),set(range(11)))
        for stage in range(11):
            for kind in range(1,15):
                s = current[stage]
                r = observe(s,event(kind,s))
                with self.subTest(stage=stage,kind=kind):
                    self.assertEqual(r.reason == 'Observed',kind in legal[stage])
                    self.assertFalse(r.fullReplayAccepted or r.storedPrefixValidated or r.semanticMetricsValid)
                    if kind not in legal[stage]:
                        self.assertEqual(r.state,s)

    def test_independent_legal_paths_and_every_cap_cut(self):
        for path in (HIT,MISS,EVICT):
            for s in run_path(path):
                self.assertEqual(finish(s,True),'CapCutUnknownTail')
            s = run_path(path)[-1]
            for p in (4,5):
                s = observe(s,event(13,s,phase=p,a=p)).state
            self.assertEqual(finish(s,False),'ClosedEnvelopeObserved')
        for s in states().values():
            if s.state:
                self.assertEqual(finish(s,False),'IncompleteEnvelope')

    def test_lookup_discriminator_forms(self):
        s = states()[1]
        for a,slot,expected in ((0,MAX,3),(1,0,2),(0,0,None),(1,MAX,None),
                                (2,0,None),(MAX,MAX,None)):
            r = observe(s,event(2,s,a=a,slot=slot))
            self.assertEqual(r.state.state if r.reason == 'Observed' else None,expected)

    def test_plan_end_discriminator_forms(self):
        s = states()[4]
        for a,b,ok in ((0,MAX,True),(1,77,True),(2,MAX,True),(1,34,False),
                       (1,MAX,False),(0,0,False),(2,0,False),(3,MAX,False),(MAX,MAX,False)):
            self.assertEqual(observe(s,event(4,s,a=a,b=b)).reason == 'Observed',ok)

    def test_publication_discriminator_cross_product(self):
        for stage,s in states().items():
            for a in (0,1,2,MAX):
                expected = (stage,a) in ((2,0),(10,1))
                self.assertEqual(observe(s,event(11,s,a=a)).reason == 'Observed',expected)

    def test_wrong_operation_and_function_for_every_normal_stage(self):
        for stage,kind in ((1,2),(2,11),(3,3),(4,4),(5,5),(6,6),(6,9),(7,7),(8,8),(9,10),(10,11)):
            s=states()[stage]
            for field in ('op','function'):
                r=observe(s,event(kind,s,**{field:77}))
                self.assertNotEqual(r.reason,'Observed')
                self.assertEqual(r.state,s)
        s=State()
        for op in (0,2,MAX):
            self.assertNotEqual(observe(s,event(1,s,op=op)).reason,'Observed')

    def test_failure_forms_all_stages_and_original_cursor_exception(self):
        for stage,s in states().items():
            for op in (0,s.active_op,77):
                for cursor in (MAX,34,72):
                    r=observe(s,event(14,s,op=op,function=cursor))
                    expected=(stage==0 and op==0) or (stage!=0 and op==s.active_op)
                    self.assertEqual(r.reason=='Observed',expected)
        # Header/check failures precede meter adoption; absent/different cursors
        # cannot be refused by a fabricated requested-function policy.
        s=states()[1]
        self.assertEqual(observe(s,event(14,s,function=72)).reason,'Observed')
        self.assertEqual(observe(s,event(14,s,function=MAX)).reason,'Observed')

    def test_failure_ranges_are_observations_not_applicability(self):
        s=states()[9]
        for a,b,c in ((1,24,6),(21,1,1),(2,1,2)):
            self.assertEqual(observe(s,event(14,s,a=a,b=b,c=c)).reason,'Observed')
        for field,values in (('a',(0,22,MAX)),('b',(0,25,MAX)),('c',(0,7,MAX)),('function',(80000,MAX-1))):
            for value in values:
                self.assertEqual(observe(s,event(14,s,**{field:value})).reason,'Shape')

    def test_failure_closes_and_forbids_all_resumption(self):
        for s in states().values():
            if not s.state:
                continue
            failed=observe(s,event(14,s)).state
            self.assertEqual(failed.state,0)
            for kind in range(1,12):
                self.assertNotEqual(observe(failed,event(kind,failed)).reason,'Observed')
            self.assertNotEqual(observe(failed,event(14,failed,op=failed.active_op)).reason,'Observed')
            self.assertEqual(observe(failed,event(12,failed)).reason,'Observed')
            terminal=observe(failed,event(14,failed,op=0)).state
            self.assertEqual(terminal.terminal,1)
            self.assertEqual(observe(terminal,event(12,terminal)).reason,'Observed')
            self.assertNotEqual(observe(terminal,event(14,terminal,op=0)).reason,'Observed')
        terminal=observe(State(),event(14,State())).state
        self.assertNotEqual(observe(terminal,event(1,terminal)).reason,'Observed')

    def test_release_every_open_stage_and_every_phase(self):
        for stage,s in states().items():
            for phase in range(6):
                s=replace(s,phase=phase)
                self.assertEqual(observe(s,event(12,s)).reason=='Observed',stage==0 and phase<5)
        s=State()
        for op in (1,MAX):
            self.assertEqual(observe(s,event(12,s,op=op)).reason,'Shape')

    def test_phase_strict_idle_no_inferred_traversal(self):
        for old in range(6):
            for new in range(7):
                s=State(phase=old,mask=1 << old)
                r=observe(s,event(13,s,phase=new,a=new))
                self.assertEqual(r.reason=='Observed',old<new<=5)
        s=observe(State(),event(13,State(),phase=5,a=5)).state
        self.assertEqual(s.mask,33)
        self.assertEqual(finish(s,False),'IncompleteEnvelope')  # expected49
        s=replace(s,expected=33)
        self.assertEqual(finish(s,False),'ClosedEnvelopeObserved')
        for stage,s in states().items():
            if stage:
                self.assertNotEqual(observe(s,event(13,s)).reason,'Observed')

    def test_phase4_and_phase5_terminality(self):
        s=State(phase=4,mask=17)
        self.assertNotEqual(observe(s,event(1,s)).reason,'Observed')
        self.assertEqual(observe(s,event(12,s)).reason,'Observed')
        self.assertEqual(observe(s,event(14,s)).reason,'Observed')
        s=State(phase=5,mask=49)
        for kind in range(1,15):
            self.assertNotEqual(observe(s,event(kind,s)).reason,'Observed')

    def test_sequence_work_instruction_and_overflow_atomic_refusal(self):
        s=states()[1]
        for field,value in (('seq',0),('seq',s.accepted+2),('work',0),('ins',0)):
            r=observe(s,event(2,s,**{field:value}))
            self.assertEqual(r.reason,'Coordinate')
            self.assertEqual(r.state,s)
        s=replace(s,accepted=MAX)
        self.assertEqual(observe(s,event(2,s,seq=MAX)).reason,'Coordinate')
        s=State(operation=MAX)
        self.assertNotEqual(observe(s,event(1,s,op=1)).reason,'Observed')

    def test_all_raw_words_closed_scalar_forms(self):
        s=states()[1]
        for i in range(16):
            for value in (-1,MAX+1,True):
                w=list(event(2,s));w[i]=value
                self.assertEqual(observe(s,tuple(w)).reason,'Shape')
        for length in (0,15,17):
            self.assertEqual(observe(s,(0,)*length).reason,'Shape')

    def test_atomic_budget_and_checked_access_refusal(self):
        for s in states().values():
            w=event(14,s)
            for left in (0,1,RECORD_DEBIT-1):
                r=observe(s,w,left)
                self.assertEqual((r.reason,r.state,r.steps),('Steps',s,0))
            r=observe(s,w,RECORD_DEBIT,fault='preflight')
            self.assertEqual((r.reason,r.state,r.steps),('CheckedAccess',s,128))
            r=observe(s,w,RECORD_DEBIT,fault='commit')
            self.assertEqual((r.reason,r.state,r.steps),('InternalPoisoned',None,128))
            self.assertFalse(r.fullReplayAccepted or r.storedPrefixValidated or r.semanticMetricsValid)

    def test_exact_cells_candidate_and_fixed_budget(self):
        self.assertEqual(len(CELLS),12)
        self.assertEqual(len(set(CELLS.values())),12)
        self.assertEqual(CELLS['terminal'],160)
        self.assertEqual(ARENA_BASE+8*CELLS['failed'],7731048)
        self.assertEqual(12*8,96)
        fixed=1048576+640000+65536+263584+3000000
        self.assertEqual(fixed,5017696)
        self.assertGreater(128*2889656+fixed,268435456)
        self.assertEqual((268435456-fixed)//128,2057951)
        self.assertEqual(sum((16,12,12,24,12,12,12,12,4,12)),128)
        self.assertEqual(sum((2048,136,32,32,16,96,96,128,128,128,128,128,32,384,256,768)),4536)

    def test_semantic_authority_always_withheld(self):
        s=State()
        for path in (HIT,MISS,EVICT):
            for state in run_path(path):
                r=observe(state,event(14,state))
                self.assertFalse(r.fullReplayAccepted or r.storedPrefixValidated or r.semanticMetricsValid)
        # Structurally plausible token or victim data intentionally has no
        # semantic endorsement; this documents unavailable policy checks.
        self.assertEqual(observe(s,event(12,s)).reason,'Observed')

if __name__ == '__main__':
    unittest.main(verbosity=2)
