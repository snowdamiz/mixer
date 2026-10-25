"""Independent tiny support oracle; never imports the writer or production code.

Finite lists/dicts are fixture storage only, not the proposed arena implementation.
"""
from dataclasses import dataclass

MAX = (1 << 64) - 1

@dataclass(frozen=True)
class Resident:
    function: int
    bytes: int
    pins: int
    timestamp: int

def plan(slots, base, capacity, requested):
    """Source-exact selection, ascending emission, and last-selected destination."""
    assert 0 < len(slots) <= 64 and base + requested <= capacity
    remaining = sum(r.bytes for r in slots if r is not None)
    empty = next((i for i, r in enumerate(slots) if r is None), None)
    selected = []
    while empty is None or base + remaining + requested > capacity:
        eligible = [i for i, r in enumerate(slots)
                    if r is not None and not r.pins and i not in selected]
        if not eligible:
            raise ValueError("all-pinned")
        victim = min(eligible, key=lambda i: (slots[i].timestamp, i))
        selected.append(victim)
        remaining -= slots[victim].bytes
        empty = victim
    return tuple(selected), tuple(sorted(selected)), empty

class Replay:
    def __init__(self, slots):
        self.slots = list(slots)
        self.pins = {}
        self.pending = None
        self.taken = 0
        self.completed = 0
        self.closed = False

    def begin(self, slot, size):
        assert self.pending is None
        r = self.slots[slot]
        assert r is not None and r.pins == 0 and r.bytes == size
        self.pending = (slot, r, False)

    def take(self):
        slot, resident, taken = self.pending
        assert not taken
        self.slots[slot] = None
        self.pending = (slot, resident, True)
        self.taken += 1

    def commit(self):
        slot, resident, taken = self.pending
        assert taken and self.slots[slot] is None
        self.pending = None
        self.completed += 1

    def fail(self):
        self.closed = True  # Preserve pending Begin or Taken, never synthesize Commit.

    def publish(self, pin_slot, nonce, entry, operation, work):
        assert pin_slot not in self.pins and nonce > 0
        r = self.slots[entry]
        assert r is not None
        self.pins[pin_slot] = (nonce, entry, operation, r.function)
        self.slots[entry] = Resident(r.function, r.bytes, r.pins + 1, work)

    def release(self, pin_slot, nonce, entry, function, body_len=MAX):
        assert body_len == MAX
        token = self.pins[pin_slot]
        assert token[0] == nonce and token[1] == entry and token[3] == function
        r = self.slots[entry]
        assert r is not None and r.function == function and r.pins > 0
        del self.pins[pin_slot]
        self.slots[entry] = Resident(r.function, r.bytes, r.pins - 1, r.timestamp)

def classify(flags, stored, cap, attempted, dropped, bytes_len, replay_ok=True,
             bindings=True, lifecycle=True, original=True, budget_complete=True):
    if not all((replay_ok, bindings, lifecycle, original, budget_complete)):
        return "invalid"
    if not (0 < cap <= 4194304 and 0 <= stored <= cap and
            attempted == stored + dropped and bytes_len == 1024 + 128 * stored):
        return "invalid"
    if flags == 0 and dropped == 0:
        return "complete-records"
    if flags == 1 and stored == cap and attempted > stored and dropped > 0:
        return "truncated-prefix"
    return "invalid"

class Budget:
    def __init__(self, total, report_reserve, record_reserve):
        assert 0 <= report_reserve <= total and record_reserve > 0
        self.remaining = total - report_reserve
        self.record_reserve = record_reserve
        self.accepted = 0
        self.state = 0

    def record(self, cost, next_state):
        assert 0 <= cost <= self.record_reserve
        if self.remaining < self.record_reserve:
            return False
        # Candidate validation and all mutation fit the reserved maximum; the
        # model's atomic assignment stands for no-fail fixed delta application.
        self.remaining -= cost
        self.state = next_state
        self.accepted += 1
        return True

def reuse(trace):
    recent, seen, out = [], set(), []
    for function in trace:
        out.append("first" if function not in seen else
                   recent.index(function) if function in recent else ">=64")
        seen.add(function)
        if function in recent:
            recent.remove(function)
        recent.insert(0, function)
        del recent[64:]
    return out

class Plans:
    def __init__(self):
        self.cells = {}

    def finish(self, function, identity, outcome, prior=MAX):
        index = function & 511
        old = self.cells.get(index)
        if outcome == 2:
            assert old == (function, identity) and prior == MAX
        elif outcome == 0:
            assert old is None and prior == MAX
            self.cells[index] = (function, identity)
        elif outcome == 1:
            assert old is not None and old[0] == prior and prior != function
            self.cells[index] = (function, identity)
        else:
            raise AssertionError("closed-plan-outcome")

def interval(begin, end=None, failure=None):
    assert (end is None) != (failure is None)
    stop = end if end is not None else failure
    assert stop >= begin
    return {"completed": stop - begin if end is not None else 0,
            "partial": stop - begin if failure is not None else 0}
