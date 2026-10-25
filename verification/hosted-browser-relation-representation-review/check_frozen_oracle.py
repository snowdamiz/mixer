#!/usr/bin/env python3
"""Bind each frozen baseline and source-compiled expression to fresh ordinary DDL.

canonical() is invoked only as the reviewed subject whose saved output is being
audited. The semantic expectation is the independently installed source result.
"""
from collections import Counter
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PRODUCER=ROOT/"verification/hosted-browser-relation-representation"
def load(path): return json.loads(path.read_text())
def bag(rows): return Counter(json.dumps(r,sort_keys=True) for r in rows)
spec=importlib.util.spec_from_file_location("reviewed_subject",PRODUCER/"qualify.py")
subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
fresh=load(HERE/"fresh-source-baseline.json")
checks=[]
def check(name,passed):
    checks.append(dict(name=name,passed=bool(passed)))
    if not passed: raise AssertionError(name)
for major in (16,17):
    attempt=ROOT/load(PRODUCER/"receipt.json")["final_attempts"][str(major)]["attempt"]
    source=load(attempt/"source-compiled-oracle.json")
    baseline=load(attempt/"clean-baseline.json")
    check(f"pg{major} exact saved frozen canonical baseline",subject.canonical(baseline)==load(attempt/"frozen-expectation.json"))
    identities=[(r["relation"],tuple(r["columns"]),r["predicate"]) for r in baseline["indexes"]]
    check(f"pg{major} all fourteen diagnostic index mappings collision free",len(identities)==len(set(identities))==14)
    fk_names=[r["conname"] for r in baseline["constraints"] if r["contype"]=="f"]
    check(f"pg{major} diagnostic FK group names unique within selected fixture",len(fk_names)==len(set(fk_names))==12)
    for key,actual,expected in (
        ("eighty CHECK expressions",[(r["relation"],r["expression"]) for r in fresh["constraints"] if r["contype"]=="c"],[(r["relation"],r["expression"]) for r in source["checks"]]),
        ("thirty-two policy NULL TRUE exact deparses",[(r["relation"],r["polname"],r["using_expr"],r["check_expr"]) for r in fresh["policies"]],[(r["relation"],r["polname"],r["using_expr"],r["check_expr"]) for r in source["policies"]]),
        ("three exact source defaults",[(r["relation"],r["attname"],r["default_expr"]) for r in fresh["columns"] if r["default_expr"] is not None],[(r["relation"],r["attname"],r["expression"]) for r in source["defaults"]]),
        ("exact partial-index source predicate",[(r["relation"],r["predicate"]) for r in fresh["indexes"] if r["predicate"] is not None],[(r["relation"],r["expression"]) for r in source["predicates"]]),
    ):
        check(f"pg{major} fresh ordinary source agrees with independent producer compilation: {key}",bag(actual)==bag(expected))
(HERE/"frozen-oracle-checks.json").write_text(json.dumps(checks,indent=2,sort_keys=True)+"\n")
print(json.dumps(dict(passed=True,assertions=len(checks))))
