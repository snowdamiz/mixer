"""Independent bounded protocol controls, not Android/product-source execution.

All object() values are abstract exact identities; B is an abstract already-held
external claim, never a claim that the real EditorLease was exercised here.
"""
import itertools
import json


class Refusal(Exception):
    pass


class Renderer:
    def __init__(self, external=0):
        self.input = object()
        self.fence = object()
        self.count = external
        self.external = external
        self.events = []


class Candidate:
    def __init__(self, renderer, attached=True):
        self.owner = renderer
        self.journal = object()
        self.token = object()
        self.original = object() if attached else None
        self.scopes = []
        self.held = 0
        self.progress = "OPEN"
        self.failure_invoked = False
        self.first_fatal = None


class Scope:
    def __init__(self, candidate):
        self.candidate = candidate
        self.renderer = candidate.owner
        self.journal = candidate.journal
        self.record = object()
        self.view = object()
        self.input = candidate.owner.input
        self.fence = candidate.owner.fence
        self.token = candidate.token
        self.original = candidate.original
        self.member = True
        self.registered = True
        self.entered = self.counted = self.ended = self.released = False
        self.callbacks = 0
        self.phase = "CAPTURED"
        candidate.scopes.append(self)


def snapshot(renderer, candidate):
    return (renderer.count, candidate.held, candidate.progress,
            candidate.failure_invoked, candidate.first_fatal,
            tuple((s.registered, s.entered, s.counted, s.ended, s.released,
                   s.phase, s.callbacks) for s in candidate.scopes),
            tuple(renderer.events))


def candidate_owned(renderer, candidate):
    return candidate.owner is renderer


def owned(renderer, candidate, scope):
    return (candidate_owned(renderer, candidate)
            and scope.renderer is renderer and scope.candidate is candidate
            and scope.journal is candidate.journal and scope in candidate.scopes
            and scope.member and scope.input is renderer.input
            and scope.fence is renderer.fence and scope.token is candidate.token
            and scope.original is candidate.original and scope.original is not None)


def begin(renderer, candidate, scope, input_receiver):
    if (not owned(renderer, candidate, scope)
            or input_receiver is not renderer.input or not scope.registered
            or scope.entered or scope.counted or scope.ended
            or renderer.count < 0 or renderer.count >= 2**31 - 1
            or candidate.held != sum(s.counted for s in candidate.scopes)):
        raise Refusal()
    # No call/validation follows this nonthrowing synchronous scalar tail.
    scope.entered = scope.counted = True
    scope.phase = "ATTACHING"
    candidate.held += 1
    renderer.count += 1


def terminal_end(renderer, candidate, scope, input_receiver):
    if (not owned(renderer, candidate, scope)
            or input_receiver is not renderer.input or not scope.entered
            or not scope.counted or scope.released or not scope.ended
            or scope.registered or scope.callbacks or candidate.held <= 0
            or renderer.count < candidate.held):
        raise Refusal()
    scope.counted = False
    scope.released = True
    scope.phase = "RELEASED"
    candidate.held -= 1
    renderer.count -= 1


def finish(renderer, candidate):
    if (not candidate_owned(renderer, candidate)
            or candidate.progress != "OPEN" or candidate.failure_invoked
            or candidate.held != sum(s.counted for s in candidate.scopes)
            or renderer.count < candidate.held
            or any(not owned(renderer, candidate, s) or not s.entered
                   or not s.counted or s.ended or not s.registered
                   or s.callbacks or s.phase != "PRECOMMIT_READY"
                   for s in candidate.scopes)):
        raise Refusal()
    # All supported synchronous refusals precede all success effects.
    candidate.progress = "SUCCESS_IN_PROGRESS"
    for scope in candidate.scopes:
        scope.registered = False
        scope.ended = True
    # Existing prepared swaps are abstracted by this scalar marker.
    renderer.events.append("prepared-swaps")
    for scope in candidate.scopes:
        # In production this must be a direct, no-throw scalar tail; no Input.
        scope.counted = False
        scope.released = True
        scope.phase = "COMMITTED"
        candidate.held -= 1
        renderer.count -= 1
    candidate.progress = "SUCCESS_DONE"


def complete_failed(renderer, candidate, fatal=None, report_fatal=None):
    if (not candidate_owned(renderer, candidate) or candidate.failure_invoked
            or candidate.progress == "SUCCESS_DONE"):
        raise Refusal()
    # Entire endpoint is inert on a foreign/malformed identity before claiming.
    if any(not owned(renderer, candidate, s) for s in candidate.scopes):
        raise Refusal()
    candidate.failure_invoked = True
    if candidate.first_fatal is None:
        candidate.first_fatal = fatal
    # Pre-attach with no captured scope requires no fabricated Mutation.
    funded = (candidate.held == sum(s.counted for s in candidate.scopes)
              and renderer.count >= candidate.held)
    # Reporting phase must precede every release. No native authority queried.
    for scope in candidate.scopes:
        if scope.released:
            continue
        scope.registered = False
        scope.ended = True
        scope.phase = "FAILED_HELD" if scope.counted else "RELEASED"
        if scope.entered or scope.counted:
            renderer.events.append(("report", renderer.count))
        if candidate.first_fatal is None:
            candidate.first_fatal = report_fatal
    for scope in candidate.scopes:
        if not scope.counted:
            continue
        if not scope.entered or scope.callbacks or not funded:
            continue
        terminal_end(renderer, candidate, scope, renderer.input)
    candidate.progress = "FAILED_DONE"
    return candidate.first_fatal


results = []


def check(name, function):
    function()
    results.append({"name": name, "passed": True})


def refusal_unchanged(operation, pairs):
    before = [snapshot(*pair) for pair in pairs]
    try:
        operation()
    except Refusal:
        pass
    else:
        raise AssertionError("expected exact refusal")
    assert before == [snapshot(*pair) for pair in pairs]


def cohort(external=1, n=2):
    r = Renderer(external)
    c = Candidate(r)
    for _ in range(n):
        s = Scope(c)
        begin(r, c, s, r.input)
        s.phase = "PRECOMMIT_READY"
    return r, c


def triple_success():
    r, c = cohort()
    assert r.count == 3
    finish(r, c)
    assert r.count == 1 and c.held == 0
    refusal_unchanged(lambda: finish(r, c), [(r, c)])
    refusal_unchanged(lambda: complete_failed(r, c), [(r, c)])
    r.count -= r.external
    assert r.count == 0


check("abstract-three-field-success-3-to-1-to-0", triple_success)


def known_rejection():
    r, c = cohort()
    original = c.original
    for s in c.scopes:
        assert s.original is original and not s.ended and r.count == 3
        s.phase = "RESTORED_HELD"
        s.ended = True
        s.registered = False
    assert r.count == 3
    complete_failed(r, c)
    assert r.count == 1 and all(s.released for s in c.scopes)
    assert all(e[1] == 3 for e in r.events if isinstance(e, tuple))
    r.count -= 1
    assert r.count == 0


check("abstract-known-rejection-retains-original-through-reporting", known_rejection)


def captured_and_partial():
    r, c = cohort(n=1)
    captured = Scope(c)
    assert not captured.entered and not captured.counted
    complete_failed(r, c)
    assert r.count == 1 and not captured.registered and captured.ended
    assert not captured.counted and c.held == 0
    refusal_unchanged(lambda: complete_failed(r, c), [(r, c)])


check("partial-begin-revokes-exact-uncounted-registration-without-decrement", captured_and_partial)


def preattach_and_empty():
    for attached, success in itertools.product([False, True], repeat=2):
        r = Renderer(1)
        c = Candidate(r, attached)
        if success and attached:
            finish(r, c)
        else:
            complete_failed(r, c)
        assert r.count == 1 and c.held == 0 and c.scopes == []


check("preattach-no-original-and-zero-preservation-cohort", preattach_and_empty)


def all_identity_endpoints():
    for field in ["renderer", "candidate", "journal", "record", "view", "input",
                  "fence", "token", "original", "member"]:
        # Record/View are immutable model identities; corrupting the endpoint's
        # arguments is represented separately below. Other edges are compared.
        if field in ("record", "view"):
            continue
        for endpoint in ("begin", "end", "finish", "failure"):
            r, c = cohort(n=0)
            s = Scope(c)
            if endpoint != "begin":
                begin(r, c, s, r.input)
                s.phase = "PRECOMMIT_READY"
            if endpoint == "end":
                s.ended = True
                s.registered = False
            setattr(s, field, False if field == "member" else object())
            operation = {
                "begin": lambda: begin(r, c, s, r.input),
                "end": lambda: terminal_end(r, c, s, r.input),
                "finish": lambda: finish(r, c),
                "failure": lambda: complete_failed(r, c),
            }[endpoint]
            refusal_unchanged(operation, [(r, c)])
    r, c = cohort()
    f, d = cohort()
    s = c.scopes[0]
    refusal_unchanged(lambda: begin(f, c, s, f.input), [(r, c), (f, d)])
    refusal_unchanged(lambda: terminal_end(f, c, s, f.input), [(r, c), (f, d)])
    refusal_unchanged(lambda: finish(f, c), [(r, c), (f, d)])
    refusal_unchanged(lambda: complete_failed(f, c), [(r, c), (f, d)])


check("abstract-exact-identity-and-foreign-replay-refusal-before-effects", all_identity_endpoints)


def count_and_imbalance():
    for bad_count in (-1, 2**31 - 1):
        r, c = cohort(n=0)
        s = Scope(c)
        r.count = bad_count
        refusal_unchanged(lambda: begin(r, c, s, r.input), [(r, c)])
    r, c = cohort()
    r.count = 1
    complete_failed(r, c)
    assert c.held == 2 and all(s.counted for s in c.scopes) and r.count == 1
    r, c = cohort()
    first = object()
    later = object()
    c.scopes[0].callbacks = 1
    assert complete_failed(r, c, first, later) is first
    assert r.count == 2 and c.scopes[0].counted and c.scopes[1].released
    assert all(e[1] == 3 for e in r.events)
    r.count -= 1
    assert r.count == 1  # Exact imbalanced A keeps disposal busy after external B.


check("underfunded-cohort-and-first-fatal-do-not-block-other-balanced-scope", count_and_imbalance)


def success_refusal_before_effects():
    r, c = cohort()
    c.scopes[1].callbacks = 1
    refusal_unchanged(lambda: finish(r, c), [(r, c)])
    complete_failed(r, c)
    assert r.count == 2 and c.scopes[0].released and c.scopes[1].counted


check("late-preflight-mismatch-after-abstract-commit-has-no-success-prefix", success_refusal_before_effects)


def partial_release_state_is_not_replay():
    # Hostile state construction only, not a reachable synchronous execution
    # witness: healthy success tail has no call/throw boundary between releases.
    r, c = cohort()
    c.progress = "SUCCESS_IN_PROGRESS"
    for s in c.scopes:
        s.registered = False
        s.ended = True
    terminal_end(r, c, c.scopes[0], r.input)
    assert r.count == 2 and c.held == 1
    complete_failed(r, c)
    assert r.count == 1 and c.held == 0
    refusal_unchanged(lambda: complete_failed(r, c), [(r, c)])


check("synthetic-progress-state-distinct-from-true-endpoint-replay", partial_release_state_is_not_replay)


def shared_boolean_counterinterpretation():
    # Counterinterpretation admitted by ambiguous prose, not product execution.
    r, c = cohort()
    shared_claimed = True  # success preclaims as currently worded
    for s in c.scopes:
        s.registered = False
        s.ended = True
    terminal_end(r, c, c.scopes[0], r.input)
    if shared_claimed:
        cleanup_refuses_as_replay = True
    assert cleanup_refuses_as_replay and c.scopes[1].counted and r.count == 2


check("counterinterpretation-shared-once-boolean-cannot-represent-progress", shared_boolean_counterinterpretation)

print(json.dumps({"schema": 1, "scope": "Independent abstract protocol model only",
                  "product_source_executed": False, "native_executed": False,
                  "controls": results, "control_count": len(results),
                  "all_passed": all(r["passed"] for r in results)}, indent=2))
