"""Independent finite semantic controls, not an implementation of Mixer Rust."""
from dataclasses import dataclass
import os
import stat

MAX64 = (1 << 64) - 1
BLOCK = 4096
CALLS = 32


class Refusal(Exception):
    def __init__(self, code, acknowledged=0, attempts=0):
        self.code, self.acknowledged, self.attempts = code, acknowledged, attempts
        super().__init__(code)


def checked_add(a, b):
    if min(a, b) < 0 or a > MAX64 - b:
        raise Refusal("arithmetic")
    return a + b


def checked_mul(a, b):
    if min(a, b) < 0 or max(a, b) > MAX64 or b and a > MAX64 // b:
        raise Refusal("arithmetic")
    return a * b


def blocks(total):
    if not 0 <= total <= MAX64:
        raise Refusal("arithmetic")
    return checked_add(total // BLOCK, int(total % BLOCK != 0))


def work_bound(total, fixed, record_visits, per_block, per_attempt,
               checkpoints, per_checkpoint):
    """Add independently enumerated nonnegative source-role units without wrap.

    Coefficients/visits are synthetic model inputs. Future source must justify
    its actual formula and every coefficient; this function grants no credits.
    One total term represents encoded-byte visits; repeated passes need added
    terms in fixed/record_visits or a separately checked source calculation.
    """
    count = blocks(total)
    attempts = checked_mul(count, CALLS)
    terms = [total, fixed, *record_visits, checked_mul(count, per_block),
             checked_mul(attempts, per_attempt),
             checked_mul(checkpoints, per_checkpoint)]
    result = 0
    for term in terms:
        result = checked_add(result, term)
    return result, attempts


@dataclass
class Control:
    base: int
    combined: int
    limit: int
    work: int
    work_limit: int
    first_failure: object = None
    cancelled: bool = False
    expired: bool = False
    ticket_owner: int = 1
    actual_owner: int = 1
    category: str = "construction"
    ticket_bytes: int = 0

    def __post_init__(self):
        if not self.ticket_bytes:
            self.ticket_bytes = self.base

    def probe(self):
        if self.first_failure is not None:
            raise Refusal("already_terminal")
        if self.cancelled:
            raise Refusal("cancelled")
        if self.expired:
            raise Refusal("deadline")

    def predebit(self, credits):
        self.probe()
        attempted = checked_add(self.work, credits)
        if attempted > self.work_limit:
            raise Refusal("work")
        self.work = attempted

    def enlarge(self, required):
        self.probe()
        if not self.actual_owner or self.ticket_owner != self.actual_owner:
            raise Refusal("owner")
        if self.category != "construction":
            raise Refusal("category")
        if required < self.ticket_bytes:
            raise Refusal("shrink")
        combined = checked_add(self.combined, required - self.ticket_bytes)
        if combined > self.limit:
            raise Refusal("storage")
        self.combined, self.ticket_bytes = combined, required

    def finish_original(self):
        if self.ticket_bytes != self.base:
            return {"charged": self.ticket_bytes, "invariant": "construction_bound"}
        return {"charged": 0, "invariant": None}


@dataclass
class Storage:
    size: int
    alive: bool = True


class SelectedScope:
    """Finite owning-scope model; Python privacy is not Rust enforcement."""
    def __init__(self, control, early_bytes):
        self._control = control
        self._captured_base = control.base
        # Must succeed before actual early storage exists.
        control.enlarge(checked_add(self._captured_base, early_bytes))
        self._early = Storage(early_bytes)
        self._phase = None
        self.finished = False

    def predebit(self, credits):
        self._control.predebit(credits)

    def admit_phase(self, extra):
        if self._phase is not None:
            raise Refusal("phase_live")
        self._control.enlarge(checked_add(self._control.ticket_bytes, extra))
        self._phase = Storage(extra)
        return self._phase

    def retire_phase(self, actual):
        if actual is not self._phase or not actual.alive:
            raise Refusal("foreign_storage")
        actual.alive = False
        self._control.ticket_bytes -= actual.size
        self._control.combined -= actual.size
        self._phase = None

    def finish(self, actual_early):
        if actual_early is not self._early or not actual_early.alive:
            raise Refusal("foreign_storage")
        if self._phase is not None:
            raise Refusal("phase_live")
        actual_early.alive = False
        self._control.ticket_bytes -= actual_early.size
        self._control.combined -= actual_early.size
        if self._control.ticket_bytes != self._captured_base:
            raise Refusal("captured_base_mismatch")
        self.finished = True
        return self._control.finish_original()


def original_order(primary, snapshot="ok", header_refuses=False):
    """Preserve opaque original payload objects and fixed primary event order."""
    if primary[0] != 8:
        return primary, "NotReached", []
    events = ["inspect_success", "work_predebit", "storage_admission", "sole_guard",
              "snapshot", "header"]
    if header_refuses:
        return (6, primary[1]), snapshot, events
    events.append("rows")
    return primary, snapshot, events


def distinct_regular_outputs(snapshot_fd, row_fd):
    # Real kernel metadata from both owners, never path/object/descriptor claims.
    left, right = os.fstat(snapshot_fd), os.fstat(row_fd)
    if not stat.S_ISREG(left.st_mode) or not stat.S_ISREG(right.st_mode):
        raise Refusal("file_type")
    if (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino):
        raise Refusal("alias")
    if left.st_size or os.lseek(snapshot_fd, 0, os.SEEK_CUR):
        raise Refusal("output_state")


def counted_write(total, write, probe=lambda: None):
    """Private synthetic seam for 32-call and late interruption controls only."""
    acknowledged, attempts, remaining_total = 0, 0, total

    def check():
        try:
            probe()
        except Refusal as error:
            raise Refusal(error.code, acknowledged, attempts)

    check()
    while remaining_total:
        width = min(BLOCK, remaining_total)
        done, calls = 0, 0
        check()
        while done < width:
            if calls == CALLS:
                raise Refusal("attempts", acknowledged, attempts)
            check()
            calls += 1
            attempts += 1
            remaining = width - done
            result = write(remaining)
            if isinstance(result, int) and 0 < result <= remaining:
                acknowledged += result
                done += result
            # Progress is retained before post-call interruption observation.
            check()
            if result == "interrupted":
                continue
            if result == "io":
                raise Refusal("io", acknowledged, attempts)
            if result == 0:
                raise Refusal("zero", acknowledged, attempts)
            if not isinstance(result, int) or result < 0 or result > remaining:
                raise Refusal("overreport", acknowledged, attempts)
        remaining_total -= width
    check()
    return acknowledged, attempts
