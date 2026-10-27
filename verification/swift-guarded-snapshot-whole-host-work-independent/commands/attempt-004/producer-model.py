"""Checked conditional logical work algebra. No policy or execution authority.

Known constants are frozen source-interface prices. Unresolved terms are typed
symbols; assigning positive test numbers does not qualify their bounds.
"""
from __future__ import annotations
from dataclasses import dataclass

U64 = (1 << 64) - 1
PHASES = ('P1_setup', 'P1_loader', 'P2_arguments', 'P3_before_store',
          'P4_selected_route', 'P5_payload_teardown')

class Refused(ValueError): pass

def natural(n):
    if type(n) is not int or not 0 <= n <= U64: raise Refused('not-u64')
    return n

def add(*values):
    out = 0
    for value in values:
        value = natural(value)
        if value > U64 - out: raise Refused('add-overflow')
        out += value
    return out

def mul(a, b):
    natural(a); natural(b)
    if a and b > U64 // a: raise Refused('mul-overflow')
    return a * b

@dataclass(frozen=True)
class Symbol:
    name: str
    unit: str
    reason: str
    positive: bool = True

@dataclass(frozen=True)
class Linear:
    fixed: int
    terms: tuple[tuple[str, int], ...] = ()

    def __post_init__(self):
        natural(self.fixed)
        if tuple(sorted(self.terms)) != self.terms: raise Refused('unordered-terms')
        if len({k for k, v in self.terms}) != len(self.terms): raise Refused('duplicate-symbol')
        for key, value in self.terms:
            if type(key) is not str or not key or natural(value) == 0: raise Refused('bad-term')

    def plus(self, other):
        terms = dict(self.terms)
        for key, value in other.terms: terms[key] = add(terms.get(key, 0), value)
        return Linear(add(self.fixed, other.fixed), tuple(sorted(terms.items())))

    def times(self, count):
        natural(count)
        return Linear(mul(self.fixed, count), tuple((k, mul(v, count)) for k, v in self.terms if count))

    def json(self): return {'fixed': self.fixed, 'terms': dict(self.terms)}

    @classmethod
    def parse(cls, value):
        if set(value) != {'fixed', 'terms'}: raise Refused('expression-schema')
        return cls(value['fixed'], tuple(sorted(value['terms'].items())))

def term(name, count=1): return Linear(0, ((name, count),))

def total(expressions):
    out = Linear(0)
    for expression in expressions: out = out.plus(expression)
    return out

@dataclass(frozen=True)
class SyntheticAssumptions:
    """Test-only values, deliberately unavailable as accepted bound receipts."""
    values: dict
    label: str

def evaluate_synthetic(interface, assumptions):
    if not isinstance(assumptions, SyntheticAssumptions) or not assumptions.label:
        raise Refused('explicit-synthetic-context-required')
    symbols = interface['symbols']; values = assumptions.values
    if set(symbols) != set(values): raise Refused('missing-or-unknown-symbol')
    for key, definition in symbols.items():
        if natural(values[key]) == 0 and definition['positive']: raise Refused('required-positive:' + key)
    if tuple(interface['child']) != PHASES: raise Refused('six-exact-ordered-child-components-required')
    def calc(expression):
        expression = Linear.parse(expression)
        return add(expression.fixed, *(mul(n, values[k]) for k, n in expression.terms))
    parts = {key: calc(value) for key, value in interface['child'].items()}
    if any(value == 0 for value in parts.values()): raise Refused('unpriced-child')
    child = add(*parts.values()); p0 = calc(interface['P0'])
    if add(child, p0) != calc(interface['whole_host']): raise Refused('composition-omission')
    return {'synthetic_label': assumptions.label, 'parts': parts, 'child': child,
            'P0': p0, 'whole_host': add(child, p0), 'accepted_bound': False,
            'root_policy_selected': False, 'operational_grant': False}

def qualification(interface):
    """No arithmetic operation mints root policy, receipts or an account."""
    return {'status': 'conditional-work-interface-only',
            'missing': tuple(interface['qualification_conditions']),
            'complete_host_funding': False, 'operational_grant': False,
            'physical_CPU_or_native_runtime': False, 'GA': False}

@dataclass
class RetentionModel:
    """Finite model of actual source ordering, not a product account replay."""
    p0_provisioned: bool
    child_work: int
    child_storage: int
    committed: bool = False
    dispatched: bool = False
    payload_destroyed: bool = False
    token_returned: bool = False
    work_consumed: int = 0
    storage_retained: int = 0

    def commit(self):
        if not self.p0_provisioned or self.committed: raise Refused('preexisting-P0-and-once-only-required')
        if not natural(self.child_work) or not natural(self.child_storage): raise Refused('unpriced-child')
        self.work_consumed = self.child_work; self.storage_retained = self.child_storage; self.committed = True

    def dispatch(self):
        if not self.committed or self.dispatched: raise Refused('not-prepaid-or-double-dispatch')
        self.dispatched = True

    def destroy(self, completes=True):
        if not self.dispatched or self.payload_destroyed: raise Refused('wrong-destruction-order')
        if completes: self.payload_destroyed = True; self.token_returned = True

    def release(self):
        if not self.token_returned or not self.payload_destroyed: raise Refused('early-or-missing-token-release')
        self.storage_retained = 0; self.token_returned = False
