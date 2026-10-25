"""Independent finite FSM oracle, authored before producer contract access.

Inputs are already-framed symbolic records. This does not frame Files, verify
profiles or bind callers; production integration must use internal framed values.
No semantic counters, resident/token/plan state or real replay validity exists.
"""
from dataclasses import dataclass, replace
from enum import IntEnum

MAX = (1 << 64) - 1


class Stage(IntEnum):
    Idle = 0
    Acquire = 1
    Hit = 2
    Miss = 3
    Scan = 4
    Plan = 5
    Ready = 6
    EvictBegin = 7
    EvictTaken = 8
    Build = 9
    Built = 10


@dataclass(frozen=True)
class Symbol:
    kind: int
    phase: int
    operation: int
    function: int
    variant: int = 0  # Lookup a / PinPublished a, ignored otherwise.
    sequence: int = 1
    work: int = 0
    instructions: int = 0


@dataclass(frozen=True)
class Envelope:
    stage: Stage = Stage.Idle
    phase: int = 0
    mask: int = 1
    operation: int = 0
    requested: int = MAX
    sequence: int = 0
    work: int = 0
    instructions: int = 0
    pin_failed: bool = False
    terminal_failed: bool = False


class Refused(ValueError):
    pass


# This oracle uses predecessor sets, independently of a producer switch/table.
PREDECESSORS = {
    2: frozenset({Stage.Acquire}),
    3: frozenset({Stage.Miss}),
    4: frozenset({Stage.Scan}),
    5: frozenset({Stage.Plan}),
    6: frozenset({Stage.Ready}),
    7: frozenset({Stage.EvictBegin}),
    8: frozenset({Stage.EvictTaken}),
    9: frozenset({Stage.Ready}),
    10: frozenset({Stage.Build}),
    11: frozenset({Stage.Hit, Stage.Built}),
}
DESTINATIONS = {3: Stage.Scan, 4: Stage.Plan, 5: Stage.Ready,
                6: Stage.EvictBegin, 7: Stage.EvictTaken,
                8: Stage.Ready, 9: Stage.Build, 10: Stage.Built,
                11: Stage.Idle}


def step(old: Envelope, event: Symbol, *, budget: int = 4096,
         required: int = 1, candidate_ok: bool = True) -> Envelope:
    """Return a fresh candidate only after every envelope check succeeds.

    The abstract budget check exercises atomic refusal; these are not claimed
    authored Rust steps or the producer's future schedule.
    """
    if budget < required or not candidate_ok:
        raise Refused("precommit")
    if old.stage not in Stage or not 1 <= event.kind <= 14:
        raise Refused("kind/state")
    if any(type(v) is not int or not 0 <= v <= MAX for v in (
            event.phase, event.operation, event.function, event.sequence,
            event.work, event.instructions, event.variant)):
        raise Refused("scalar")
    if event.sequence != old.sequence + 1 or old.sequence == MAX:
        raise Refused("sequence")
    if event.work < old.work or event.instructions < old.instructions:
        raise Refused("coordinates")
    if old.phase == 5 or event.phase > 5:
        raise Refused("phase5")
    if event.kind == 13:
        if (old.stage != Stage.Idle or event.operation != 0
                or event.function != MAX or event.phase <= old.phase
                or old.mask & (1 << event.phase)):
            raise Refused("phase")
        new = replace(old, phase=event.phase, mask=old.mask | (1 << event.phase))
    else:
        if event.phase != old.phase:
            raise Refused("ordinary phase")
        if event.kind == 12:
            if old.stage != Stage.Idle or event.operation != 0:
                raise Refused("release")
            # Token/resident joins intentionally unavailable in this oracle.
            new = old
        elif event.kind == 14:
            # Source cursor is independent, even in an open attempted pin:
            # AcquireBegin precedes check_header and M::meter cursor adoption.
            if event.function != MAX and event.function >= 80_000:
                raise Refused("failure cursor")
            if event.operation == 0:
                if old.stage != Stage.Idle or old.terminal_failed:
                    raise Refused("terminal failure")
                new = replace(old, terminal_failed=True)
            else:
                if (old.stage == Stage.Idle or old.pin_failed
                        or event.operation != old.operation):
                    raise Refused("pin failure")
                new = replace(old, stage=Stage.Idle, pin_failed=True)
        elif event.kind == 1:
            if (old.stage != Stage.Idle or old.phase >= 4
                    or old.pin_failed or old.terminal_failed
                    or old.operation == MAX or event.operation != old.operation + 1
                    or event.function >= 80_000):
                raise Refused("acquire")
            new = replace(old, stage=Stage.Acquire,
                          operation=event.operation, requested=event.function)
        else:
            if (old.pin_failed or old.terminal_failed
                    or event.operation == 0 or event.operation != old.operation
                    or event.function != old.requested
                    or old.stage not in PREDECESSORS[event.kind]):
                raise Refused("stage/join")
            if event.kind == 2:
                if event.variant not in (0, 1):
                    raise Refused("lookup variant")
                destination = (Stage.Miss, Stage.Hit)[event.variant]
            else:
                destination = DESTINATIONS[event.kind]
                if event.kind == 11 and event.variant != int(old.stage == Stage.Built):
                    raise Refused("publication variant")
            new = replace(old, stage=destination)
    return replace(new, sequence=event.sequence, work=event.work,
                   instructions=event.instructions)


def observation(state: Envelope, *, cap_tail: bool) -> dict:
    """Separate fixture observation; no fixed report schema or bit is assigned."""
    return {"schema": "IndependentFixtureEnvelopeExpectationV1",
            "last_fully_applied_sequence": state.sequence,
            "acquisition_state": int(state.stage),
            "stored_phase": state.phase, "stored_mask": state.mask,
            "stored_operation": state.operation,
            "pin_failure_observed": state.pin_failed,
            "terminal_failure_observed": state.terminal_failed,
            "omitted_tail_unknown": cap_tail,
            "storedPrefixValidated": False, "fullReplayAccepted": False,
            "semantic_counters_valid": False}
