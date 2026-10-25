"""Authored finite fixture envelope, independent of framing/product code.

Python collections and fixtures are test storage. This is not Rust layout,
runtime memory, source failure applicability, semantic replay or a custodian.
"""
from dataclasses import dataclass, replace

MAX = (1 << 64) - 1
MAX32 = (1 << 32) - 1
LIMIT = 268435456
RECORD_DEBIT = 128
CANDIDATE_SETUP_DEBIT = 534
CANDIDATE_BYTES = 2048
CANDIDATE_PAYLOAD_BASE = 888
REASONS = dict(Observed=0, Steps=1, Shape=2, Coordinate=3, TerminalPhase=4,
               Phase=5, ReleaseOpen=6, TerminalFailure=7, PinFailure=8,
               ForbiddenResume=9, Acquire=10, Identity=11, Stage=12,
               PublicationForm=13, CheckedAccess=14, InternalPoisoned=15)
ARENA_BASE = 7729760
# Only already named cells from accepted interface_schema; no reserved cells.
CELLS = dict(accepted=7, work=9, instructions=10, operation=11, phase=12,
             mask=13, expected=14, state=64, active_op=65, function=66,
             terminal=160, failed=161)
NORMAL = {3: (3, 4), 4: (4, 5), 5: (5, 6), 6: (6, 7),
          7: (7, 8), 8: (8, 6), 9: (6, 9), 10: (9, 10)}

@dataclass(frozen=True)
class State:
    accepted: int = 0
    work: int = 0
    instructions: int = 0
    operation: int = 0
    phase: int = 0
    mask: int = 1
    expected: int = 49
    state: int = 0
    active_op: int = 0
    function: int = 0  # Inactive at Idle; not a cursor or profile assertion.
    terminal: int = 0
    failed: int = 0

@dataclass(frozen=True)
class Reply:
    reason: str
    state: State
    steps: int
    fullReplayAccepted: bool = False
    storedPrefixValidated: bool = False
    semanticMetricsValid: bool = False

def initial(expected):
    if type(expected) is not int or not 0 < expected < 64 or expected & 33 != 33:
        return None
    return State(expected=expected)

def shape(w):
    """Closed wire ranges only; no code/kind/stage/resource applicability."""
    if len(w) != 16 or any(type(n) is not int or not 0 <= n <= MAX for n in w):
        return False
    _, k, p, op, _, _, f, off, length, typ, slot, pin, nonce, a, b, c = w
    if not 1 <= k <= 14 or p > 5:
        return False
    absent = (off, length, typ) == (MAX, MAX, MAX)
    no_slots = (slot, pin, nonce) == (MAX, MAX, 0)
    full = f < 80000 and off < MAX and length < MAX and typ <= MAX32 and off + length <= MAX
    if k == 1:
        return op > 0 and f < 80000 and absent and no_slots and (a,b,c) == (0,0,0)
    if k == 2:
        return op > 0 and full and pin == MAX and nonce == 0 and b == c == 0 and (
            a == 0 and slot == MAX or a == 1 and slot < 64)
    if k == 3:
        return op > 0 and full and no_slots and a == b == 0 and c == (f & 511)
    if k == 4:
        return op > 0 and full and no_slots and c == (f & 511) and (
            a in (0,2) and b == MAX or a == 1 and b < 80000 and b != f)
    if k == 5:
        return op > 0 and full and no_slots and a > 0 and b + a <= c
    if k in (6,7,8):
        return op > 0 and full and slot < 64 and pin == MAX and nonce == 0 and a > 0 and b == c == 0
    if k in (9,10):
        return op > 0 and full and no_slots and a > 0 and b == c == 0
    if k == 11:
        return op > 0 and full and slot < 64 and pin < 64 and nonce > 0 and a in (0,1) and b > 0 and 1 <= c <= 64
    if k == 12:
        return op == 0 and f < 80000 and off < MAX and length == MAX and typ <= MAX32 and slot < 64 and pin < 64 and nonce > 0 and a > 0 and b == 0 and c < 64
    if k == 13:
        return op == 0 and f == MAX and absent and no_slots and a == p and b == c == 0
    return absent and (f == MAX or f < 80000) and no_slots and 1 <= a <= 21 and 1 <= b <= 24 and 1 <= c <= 6

def observe(s, w, remaining=LIMIT, fault=None):
    """Atomic pure preflight; refused candidates never replace semantic cells.

    fault models failed checked access before commit or an unexpected partial
    commit fault. The latter poisons output: it cannot claim prior state valid.
    """
    if s is None:
        return Reply('InternalPoisoned', None, 0)
    if remaining < RECORD_DEBIT:
        return Reply('Steps', s, 0)
    def refuse(reason):
        return Reply(reason, s, RECORD_DEBIT)
    if not shape(w):
        return refuse('Shape')
    seq,k,p,op,work,ins,f,off,length,typ,slot,pin,nonce,a,b,c = w
    if s.accepted == MAX or seq != s.accepted + 1 or work < s.work or ins < s.instructions:
        return refuse('Coordinate')
    if s.phase == 5:
        return refuse('TerminalPhase')
    if k == 13:
        if s.state or not s.phase < p <= 5 or s.mask & (1 << p):
            return refuse('Phase')
        delta = replace(s, phase=p, mask=s.mask | (1 << p))
    else:
        if p != s.phase:
            return refuse('Phase')
        if k == 12:
            if s.state:
                return refuse('ReleaseOpen')
            delta = s  # No token/resident semantic assertion.
        elif k == 14:
            if op == 0:
                if s.state or s.terminal:
                    return refuse('TerminalFailure')
                delta = replace(s, terminal=1)
            else:
                if not s.state or s.failed or s.terminal or op != s.active_op:
                    return refuse('PinFailure')
                delta = replace(s, state=0, failed=1)
        else:
            if s.failed or s.terminal:
                return refuse('ForbiddenResume')
            if k == 1:
                if s.state or s.phase >= 4 or s.operation == MAX or op != s.operation + 1:
                    return refuse('Acquire')
                delta = replace(s, state=1, operation=op, active_op=op, function=f)
            else:
                if op != s.active_op or f != s.function:
                    return refuse('Identity')
                if k == 2:
                    if s.state != 1:
                        return refuse('Stage')
                    delta = replace(s, state=2 if a == 1 else 3)
                elif k == 11:
                    if (s.state, a) not in ((2,0),(10,1)):
                        return refuse('PublicationForm')
                    delta = replace(s, state=0)
                else:
                    before, after = NORMAL[k]
                    if s.state != before:
                        return refuse('Stage')
                    delta = replace(s, state=after)
    delta = replace(delta, accepted=seq, work=work, instructions=ins)
    if fault == 'preflight':
        return refuse('CheckedAccess')
    if fault == 'commit':
        # Deliberately no previous-state-valid claim or normal observation.
        return Reply('InternalPoisoned', None, RECORD_DEBIT)
    return Reply('Observed', delta, RECORD_DEBIT)

def finish(s, cap):
    """Fixture-only boundary; poison precedes either CAP/non-CAP branch.

    Future Rust passes only its private initialized projector/reply. Python
    accepts explicit State/Reply fixture values to exercise negative controls;
    neither those values nor cap is actual File-framing authority.
    """
    if isinstance(s, Reply):
        if s.reason == 'InternalPoisoned':
            return 'InternalPoisoned'
        s = s.state
    if s is None:
        return 'InternalPoisoned'
    if type(s) is not State:
        return 'UnavailableState'
    if cap:
        return 'CapCutUnknownTail'
    return 'ClosedEnvelopeObserved' if not s.state and s.phase == 5 and s.mask == s.expected else 'IncompleteEnvelope'

class FixtureEnvelope:
    """Finite owner-lifecycle model, not a Rust implementation or public API.

    Its single candidate remains local to this model instance across calls.
    Python allocation/identity checks are fixture support, not Rust memory
    qualification. Rust construction/moves remain separately reviewed.
    """
    @classmethod
    def create(cls, expected=49, remaining=LIMIT):
        s=initial(expected)
        if s is None or remaining < CANDIDATE_SETUP_DEBIT:
            return None
        instance=cls.__new__(cls)
        instance._state=s
        instance._candidate=bytearray(CANDIDATE_BYTES)
        instance._remaining=remaining-CANDIDATE_SETUP_DEBIT
        instance._closed=False
        return instance

    def step(self, words, fault=None):
        if self._closed:
            raise ValueError('closed fixture owner')
        r=observe(self._state,words,self._remaining,fault)
        self._remaining-=r.steps
        if r.reason == 'Observed':
            # Exactly the 12 scalar payload slots; no per-call zero or owner move.
            for i,name in enumerate(CELLS):
                start=CANDIDATE_PAYLOAD_BASE+8*i
                self._candidate[start:start+8]=getattr(r.state,name).to_bytes(8,'little')
            self._state=r.state
        elif r.reason == 'InternalPoisoned':
            self._state=None
        return r

    def finish(self, cap):
        return 'UnavailableState' if self._closed else finish(self._state,cap)

    def close(self):
        # Finite model of dropping the one local owner after its borrows return.
        self._closed=True
        self._candidate=None
        self._state=None
