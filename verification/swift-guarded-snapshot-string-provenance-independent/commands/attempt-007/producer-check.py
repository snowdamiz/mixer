#!/usr/bin/env python3
"""Strict offline candidate binder and alternate-caller length obligation.

There is no product account/token constructor, policy validator or OTA grant.
"""
import copy,json,sys
from pathlib import Path
from mir_graph import Refused,require,sha
D=Path(__file__).resolve().parent
U64=(1<<64)-1
SOURCE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def natural(value):
    require(type(value) is int and 0<=value<=U64,'u64-required');return value

def bound_text(value,bound):
    """Checks actual UTF-8 bytes, never a caller's claimed length or lifetime."""
    require(type(value) is str,'actual-string-required');natural(bound)
    try:raw=value.encode('utf-8',errors='strict')
    except UnicodeError:raise Refused('invalid-Unicode-value')
    require(len(raw)<=bound,'caller-string-exceeds-UTF8-byte-bound')
    return {'utf8_bytes':len(raw),'scalar_leaves':len(value),'sha256':sha(raw)}

def bind_exact(proposed,expected):
    require(type(proposed) is dict and set(proposed)==set(expected),'candidate-schema')
    require(canonical(proposed)==canonical(expected),'candidate-source-or-scope-mismatch')
    require(proposed['source_tree_sha256']==SOURCE and proposed['host_tree_sha256']==HOST,'exact-source-and-host')
    require(natural(proposed['L_str'])==5080,'exact-string-bound')
    for key in ('accepted_bound','whole_host_funding','policy_or_work_grant','runtime_or_native_test','OTA_authority','GA'):
        require(proposed[key] is False,'authority-forbidden:'+key)
    require(proposed['source_closure_conditional_on_exact_caller_contract'] is True,'caller-condition-required')
    return {'status':'exact-source-candidate-bound','L_str':5080,'independent_review_required':True,'accepted_bound':False,'operational_grant':False,'OTA_authority':False}

def bind_artifact(value,expected,role):
    require(type(value) is type(expected),'artifact-type:'+role)
    require(canonical(value)==canonical(expected),'artifact-omission-or-rebinding:'+role)
    return True

def alternate_caller_obligation(port_values,graph,contract,bound):
    """Length evidence only. Even exhaustive values cannot qualify a new caller.

    Every exact direct str-bearing parameter is enumerated. Nested public failure,
    Fault, first_failure and Frozen policy inputs need a new graph, not an extra
    numeric/string value admitted by this interface.
    """
    require(type(port_values) is dict,'port-map-required')
    exact={row['function']+':'+row['parameter'] for row in graph['direct_str_parameters']}
    require(set(port_values)==exact,'every-exact-direct-str-port-required')
    observations={}
    for key,values in port_values.items():
        require(type(values) is list and len(values)>0,'all-values-required:'+key)
        observations[key]=[bound_text(value,bound) for value in values]
    require(contract['root_incoming_authored_str_ports']==[],'selected-root-has-no-input-str')
    return {'status':'alternate-caller-length-evidence-only','ports':observations,
        'complete_provenance':False,'new_caller_qualified':False,'accepted_bound':False,
        'operational_grant':False,'remaining':'Nested carrier and complete new caller graph provenance still required.'}

def main():
    # Re-derive before reading the candidate; no self-certified JSON can replace
    # the complete pinned compiler/source graph or expand the allowed scope.
    import derive
    expected=derive.main(check=True)
    value=json.loads((D/'candidate.json').read_text())
    print(json.dumps(bind_exact(value,expected),sort_keys=True))
if __name__=='__main__':main()
