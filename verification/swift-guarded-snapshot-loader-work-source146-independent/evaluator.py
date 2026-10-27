"""Independent bottom-up checked graph evaluator; no product/file execution."""
from collections import defaultdict, deque
MAX = (1 << 64)-1
CAPS = {'source':67108864,'build':131072,'session':65536,'executable':67108864,'metadata':16777216,'scratch':1048576,'credits':512000000,'deadline':120000}


class Refused(ValueError):
    pass


def u64(n):
    if type(n) is not int or not 0 <= n <= MAX:
        raise Refused('unknown/non-u64/overflow')
    return n


def add(a, b):
    return u64(u64(a)+u64(b))


def mul(a, b):
    return u64(u64(a)*u64(b))


def evaluate(geometry, ledger):
    if set(geometry) != set(CAPS)|{'validator_source'}:
        raise Refused('geometry keys')
    for k, v in geometry.items():
        if u64(v) > CAPS.get(k, CAPS['source']):
            raise Refused('cap')
    if geometry['source'] > geometry['validator_source']:
        raise Refused('validator source')
    if ledger.get('schema') != 1:
        raise Refused('schema')
    maximum = max(geometry[k] for k in ('source','executable','build','session'))
    variables = dict(source=geometry['source'], validator_source=geometry['validator_source'], maximum_file=maximum, allocation_cap=max(geometry['metadata'],geometry['scratch']), retained_visits=add(maximum//4096+int(maximum%4096!=0),1), read_buffer=4096)
    nodes = ledger['nodes']
    def expanded(root, mode):
        selected, todo = set(), [root]
        cut = ledger['roots']['validator'] if mode == 'wrapper' else None
        while todo:
            n = todo.pop()
            if n in selected:
                continue
            if n not in nodes:
                raise Refused('unknown callee')
            selected.add(n)
            if n != cut:
                todo += [e['callee'] for e in nodes[n]['calls']]
        users, remaining = defaultdict(set), {}
        for n in selected:
            dependencies = set() if n == cut else {e['callee'] for e in nodes[n]['calls']}
            remaining[n] = len(dependencies)
            for dep in dependencies:
                users[dep].add(n)
        ready, values = deque(n for n in selected if remaining[n] == 0), {}
        while ready:
            n = ready.popleft()
            if n == cut:
                value = 0
            else:
                node = nodes[n]
                required = {'owner','mir_sha256','local_actions','parts','calls','standard_calls','callback_bound','repeat','native'}
                if set(node)-required-{'validator_fixed_repeat'} or required-set(node):
                    raise Refused('node schema')
                local = 2
                for amount in node['parts'].values():
                    local = add(local, amount)
                if local != node['local_actions']:
                    raise Refused('local omission')
                value = local
                for term in node['native']:
                    extent = variables[term['extent']] if isinstance(term['extent'],str) else term['extent']
                    value = add(value,mul(term['count'],extent))
                for edge in node['calls']:
                    if type(edge['multiplicity']) is not int or edge['multiplicity'] < 1:
                        raise Refused('unpriced callback')
                    value = add(value,mul(edge['multiplicity'],values[edge['callee']]))
                repeat = node['repeat'] if mode == 'wrapper' else node.get('validator_fixed_repeat',1)
                value = mul(value,variables[repeat] if isinstance(repeat,str) else repeat)
            values[n] = value
            for parent in users[n]:
                remaining[parent] -= 1
                if remaining[parent] == 0:
                    ready.append(parent)
        if set(values) != selected:
            raise Refused('cycle')
        return values[root], selected
    wrapper, a = expanded(ledger['roots']['loader'],'wrapper')
    coefficient, b = expanded(ledger['roots']['validator'],'validator')
    total = add(wrapper,mul(add(geometry['credits'],1),coefficient))
    return {'wrapper':wrapper,'coefficient':coefficient,'W_loader':total,'visited':len(a|b),'operational_grant':False}


def type_width(target):
    """Only the accepted concrete Type equality families; unknowns refuse."""
    compact = ''.join(target.split())
    for method in ('eq','ne'):
        if compact == '<TypeasPartialEq>::'+method:
            return 1
        if compact == '<Option<Type>asPartialEq>::'+method:
            return 1
        if compact == '<&[Type]asPartialEq>::'+method:
            return 128
        if compact == '<&[Type]asPartialEq<[Type;1]>>::'+method:
            return 1
    raise Refused('unknown Type receiver/RHS')
