"""Recover complete compiler callee expressions and every owned callback edge."""
from pathlib import Path
from collections import defaultdict
import copy, json, re
from correct import ROOT, PRODUCER, save, sha, body_catalog

def parse_call(statement):
    text = statement.split(' -> [return:',1)[0].strip()
    m = re.match(r'(_\d+) = (.*)',text)
    if not m:return None
    expression=m[2]
    assert expression.endswith(')'), statement
    # Find the outer invocation pair at the end of the entire callee expression.
    # Parentheses in tuple/unit/function-pointer generic types are target syntax.
    stack=[];pairs={};quoted=False;escaped=False
    for i,ch in enumerate(expression):
        if quoted:
            if escaped:escaped=False
            elif ch=='\\':escaped=True
            elif ch=='"':quoted=False
            continue
        if ch=='"':quoted=True
        elif ch=='(':stack.append(i)
        elif ch==')':
            assert stack
            pairs[i]=stack.pop()
    assert not stack and not quoted
    start=pairs[len(expression)-1]
    return m[1],expression[:start],expression[start+1:-1]

def build_calls():
    raw=json.loads((PRODUCER/'raw-inventory.json').read_text())
    old=json.loads((PRODUCER/'call-boundaries.json').read_text())
    bodies=body_catalog(PRODUCER/'function-bodies.mir')
    indexed={(r['caller'],r['source_statement']):r for r in old['calls']}
    assert len(indexed)==len(old['calls'])==627
    callbacks={}
    for f in raw['functions']:
        if '{closure#' in f['name']:
            closure=re.search(r'\{closure@source/[^}]+\}',f['header'])
            assert closure
            callbacks[closure[0]]=f['id']
    calls=[];changes=[];edges=[]
    for f in raw['functions']:
        for line in bodies[f['id']].splitlines():
            if not re.match(r'\s+_\d+ = .* -> \[return:',line):continue
            statement=line.strip();local,target,arguments=parse_call(statement)
            oldrow=indexed[(f['id'],statement)]
            row=copy.deepcopy(oldrow)
            assert row['call_result_role']==f['id']+'::'+local
            assert target.startswith(row['target'])
            row['target']=target;row['arguments']=arguments
            row['target_parse_rule']='outer invocation pair at end of full compiler call expression; balanced parentheses with string handling'
            row['owned_callbacks']=[v for k,v in callbacks.items() if k in target]
            row['source_statement_sha256']=sha(statement.encode())
            if target!=oldrow['target'] or row['owned_callbacks']!=oldrow['owned_callbacks']:
                changes.append({'caller':f['id'],'call_result_role':row['call_result_role'],
                    'before_target':oldrow['target'],'after_target':target,
                    'before_owned_callbacks':oldrow['owned_callbacks'],
                    'after_owned_callbacks':row['owned_callbacks'],
                    'source_statement_sha256':row['source_statement_sha256']})
            for callback in row['owned_callbacks']:
                edges.append({'from':f['id'],'to':callback,'call_result':row['call_result_role'],
                              'via':'actual std/direct closure call type'})
            for callee in row.get('callee_role_templates',[]):
                edges.append({'from':f['id'],'to':callee,'call_result':row['call_result_role']})
            calls.append(row)
    assert len(calls)==627
    nodes={f['id'] for f in raw['functions']};graph=defaultdict(list)
    for e in edges:
        if e['to'] in nodes:graph[e['from']].append(e['to'])
    visited=set();active=set()
    def visit(node):
        assert node not in active,'recursive owned callback graph'
        if node in visited:return
        active.add(node)
        for child in graph[node]:visit(child)
        active.remove(node);visited.add(node)
    for node in nodes:visit(node)
    assert len(visited)==81
    before={json.dumps(e,sort_keys=True) for e in old['edges']}
    after={json.dumps(e,sort_keys=True) for e in edges}
    assert before<=after
    added=[json.loads(e) for e in sorted(after-before)]
    result={**old,'calls':calls,'edges':edges,
            'correction':{'complete_target_changes':sum(c['before_target']!=c['after_target'] for c in changes),
                          'added_owned_callback_edges':added,'graph_acyclic':True,
                          'all_callback_templates_already_in_inventory':all(e['to'] in nodes for e in added),
                          'added_storage_bytes':0,'source_layout_changes':False},
            'parser_controls_scope':'compiler MIR call boundaries only; no runtime or OTA authority'}
    return result,changes

if __name__=='__main__':
    d,changes=build_calls()
    save('call-boundaries.json',d)
    save('call-delta.json',{'schema':1,'changed_calls':changes,**d['correction']})
    print(json.dumps(d['correction']))
