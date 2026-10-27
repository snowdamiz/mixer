"""Pure finite source-work proposal. Does not load, validate, compile or grant."""
from dataclasses import dataclass
import json
from pathlib import Path

U64 = (1 << 64) - 1
CAPS = dict(source=67108864, build=131072, session=65536, executable=67108864,
            metadata=16777216, scratch=1048576, credits=512000000, deadline=120000)
P, K, N, A, BLOCK = 16384, 4096, 64, 32, 4096
ROOT = Path(__file__).resolve().parent

class Refused(ValueError): pass

def natural(x):
    if type(x) is not int or not 0 <= x <= U64: raise Refused('not-u64')
    return x

def add(*xs):
    result = 0
    for x in xs:
        natural(x)
        if result > U64 - x: raise Refused('add-overflow')
        result += x
    return result

def mul(x, y):
    natural(x); natural(y)
    if x and y > U64 // x: raise Refused('mul-overflow')
    return x * y

def ceil_blocks(x):
    natural(x)
    return add(x // BLOCK, int(x % BLOCK != 0))

@dataclass(frozen=True)
class Geometry:
    source: int
    build: int
    session: int
    executable: int
    validator_source: int
    metadata: int
    scratch: int
    credits: int
    deadline: int

    def checked(self):
        for name in ('source','build','session','executable','metadata','scratch','credits','deadline'):
            value = natural(getattr(self, name))
            if value > CAPS[name]: raise Refused('cap:' + name)
        natural(self.validator_source)
        if self.validator_source > CAPS['source'] or self.source > self.validator_source:
            raise Refused('validator-source')
        return self

# Local parts are source logical actions only. Native byte extents are separate.
# An expanded node contains each written branch/callback once, not just success.
# All loop multiplicities live in the ledger; missing/unknown nodes refuse.
def expanded(ledger, node, variables, active=()):
    if node in active: raise Refused('cycle')
    row = ledger['nodes'].get(node)
    if row is None or row.get('status') != 'priced': raise Refused('unpriced:' + node)
    required = {'status','source','parts','calls','bytes'}
    if set(row) != required: raise Refused('row-schema:' + node)
    result = add(*row['parts'].values())
    for term in row['bytes']:
        extent = variables[term['extent']] if isinstance(term['extent'],str) else term['extent']
        result = add(result, mul(term['count'], extent))
    for call in row['calls']:
        count = variables[call['count']] if isinstance(call['count'], str) else call['count']
        result = add(result, mul(count, expanded(ledger, call['node'], variables, active+(node,))))
    return result

def quote(g, ledger=None):
    g.checked()
    if ledger is None: ledger = json.loads((ROOT/'token-candidate-ledger.json').read_text())
    if ledger.get('schema') != 1: raise Refused('ledger-schema')
    variables = dict(retained_bytes=add(g.source,g.build,g.session,g.executable),
        read_requests=add(*(add(ceil_blocks(getattr(g,n)),1) for n in ('source','build','session','executable'))),
        source=g.source, build=g.build, session=g.session, executable=g.executable,
        build_sections=max(0,g.build-512), session_sections=max(0,g.session-512),
        allocation_cap=max(g.metadata,g.scratch), transfer_chunk=16384,
        buffer_item=32, name_compare=8192, import_name_compare=8192)
    variables['read_attempts_extra'] = mul(A,variables['read_requests'])
    wrapper = expanded(ledger,'loader',variables)
    # Cut theorem applies to scalar/call/Copy work and requested bytes in this
    # fully expanded DAG, not to the original meter's semantic work counter.
    sweep = expanded(ledger,'validator_entry',variables)
    validator = mul(add(g.credits,1),sweep)
    return dict(schema=1, component='P1LoaderV1', status='rejected-token-count-representation-not-fundable',
        wrapper_logical_actions=wrapper, validator_original_credit_limit=g.credits,
        validator_acyclic_expanded_ceiling=sweep, validator_host_logical_actions=validator,
        W_loader=add(wrapper,validator), geometry=g.__dict__,
        read_requests_max=variables['read_requests'], read_calls_max=mul(A,variables['read_requests']),
        read_requested_native_bytes_max=mul(A,add(variables['retained_bytes'],4)),
        operational_grant=False, actual_fixture_bound=False)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2: raise SystemExit('expected explicit geometry JSON path')
    value = Geometry(**json.loads(Path(sys.argv[1]).read_text()))
    print(json.dumps(quote(value),sort_keys=True,indent=2))
