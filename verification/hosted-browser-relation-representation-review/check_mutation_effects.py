#!/usr/bin/env python3
"""Prove retained real attacks affect their named catalog facts, independently."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PRODUCER=ROOT/"verification/hosted-browser-relation-representation"
RESULTS=[]

def load(path): return json.loads(path.read_text())
def bag(rows): return Counter(json.dumps(r,sort_keys=True) for r in rows)
def col(s,relation,name): return next(r for r in s["columns"] if r["relation"]==relation and r["attname"]==name)
def check(name,value):
    RESULTS.append(dict(name=name,passed=bool(value)))
    if not value: raise AssertionError(name)

p=load(PRODUCER/"receipt.json")
for major in (16,17):
    attempt=ROOT/p["final_attempts"][str(major)]["attempt"]
    base=load(attempt/"clean-baseline.json")
    for m in load(attempt/"mutation-results.json"):
        path=attempt/("mutation-"+m["name"]+".stdout")
        s=load(path)
        name=m["name"]
        check(f"pg{major} attack output hash {name}",hashlib.sha256(path.read_bytes()).hexdigest()==m["sha256"])
        if name in ("extra-check","check-noinherit","extra-incoming-fk"):
            effect=len(s["constraints"])==110
            if name=="extra-check": effect=effect and any(r["contype"]=="c" and r["expression"]=="true" for r in s["constraints"])
            if name=="check-noinherit": effect=effect and any(r["contype"]=="c" and r["connoinherit"] and r["expression"]=="true" for r in s["constraints"])
            if name=="extra-incoming-fk": effect=effect and len(s["triggers"])==54 and any(r["relation"]=="public.representation_incoming" and r["contype"]=="f" for r in s["constraints"])
        elif name=="extra-column": effect=len(s["columns"])==125 and any(r["attname"]=="surprise" for r in s["columns"])
        elif name=="extra-index": effect=len(s["indexes"])==15 and any(r["name"]=="representation_extra_index" for r in s["indexes"])
        elif name=="corrupt-fast-default": effect=col(s,"public.mixer_authz_profiles","state_revision")["attmissingval"]=="{2}" and col(s,"public.mixer_authz_profiles","state_revision")["atthasmissing"]
        elif name=="missing-incoming-fk": effect=len(s["constraints"])==108 and len(s["triggers"])==49 and not any(r["relation"]=="public.mixer_customer_idempotency" for r in s["constraints"])
        elif name in ("disable-user-trigger","disable-child-ri","disable-parent-ri"):
            disabled=[r for r in s["triggers"] if r["tgenabled"]!="O"]
            effect=len(disabled)==1 and disabled[0]["tgenabled"]=="D" and disabled[0]["relation"]=="public.mixer_browser_sessions"
            effect=effect and (not disabled[0]["tgisinternal"] if name=="disable-user-trigger" else disabled[0]["tgisinternal"] and disabled[0]["tgtype"]==(5 if name=="disable-child-ri" else 9))
        elif name=="extra-policy": effect=len(s["policies"])==33 and any(r["polname"]=="representation_extra" and r["roles"]==["PUBLIC"] for r in s["policies"])
        elif name=="alter-policy": effect=next(r for r in s["policies"] if r["relation"]=="public.mixer_authz_profiles" and r["polname"]=="scoped_lock")["check_expr"]=="true" and bag(s["policies"])!=bag(base["policies"])
        elif name.startswith("grant-"):
            extra=bag(s["acl"])-bag(base["acl"])
            rows=[json.loads(r) for r in extra]
            if name=="grant-table-update": effect=any(r["grantee"]=="browser_writer" and r["privilege_type"]=="UPDATE" and r["column_name"] is None for r in rows)
            elif name=="grant-immutable-column": effect=any(r["grantee"]=="browser_writer" and r["privilege_type"]=="UPDATE" and r["column_name"]=="id" for r in rows)
            elif name=="grant-public": effect=any(r["grantee"]=="PUBLIC" and r["privilege_type"]=="SELECT" for r in rows)
            elif name=="grant-extra-role": effect=any(r["grantee"]=="representation_extra" and r["privilege_type"]=="SELECT" for r in rows)
            elif name=="grant-option": effect=any(r["grantee"]=="browser_writer" and r["privilege_type"]=="SELECT" and r["is_grantable"] for r in rows)
            elif name=="grant-maintain": effect=major==17 and any(r["grantee"]=="browser_writer" and r["privilege_type"]=="MAINTAIN" for r in rows)
            else: raise AssertionError("unreviewed grant mutation")
        elif name=="alter-default": effect=col(s,"public.mixer_authz_profiles","state_revision")["default_expr"]=="2" and col(s,"public.mixer_authz_profiles","state_revision")["attmissingval"]=="{1}"
        elif name=="drop-default": effect=col(s,"public.mixer_browser_oidc_attempts","ciphertext_version")["default_expr"] is None and not col(s,"public.mixer_browser_oidc_attempts","ciphertext_version")["atthasdef"]
        elif name=="extra-browser-relation": effect=len(s["relations"])==10 and any(r["relation"]=="representation_escape.mixer_browser_shadow" and r["relkind"]=="v" for r in s["relations"])
        elif name=="disable-rls": effect=next(r for r in s["relations"] if r["relation"]=="public.mixer_browser_sessions")["relforcerowsecurity"] is False
        elif name=="drop-partial-index": effect=len(s["indexes"])==13 and not any(r["name"]=="mixer_browser_one_attempt" for r in s["indexes"])
        elif name=="alter-check":
            checks=[r for r in s["constraints"] if r["contype"]=="c"]
            effect=len(checks)==80 and any("extra" in r["expression"] and "preauth" in r["expression"] for r in checks)
        else: raise AssertionError("unreviewed mutation "+name)
        check(f"pg{major} exact intended real effect {name}",effect)
    check(f"pg{major} attack list bounded exact count",len(load(attempt/"mutation-results.json"))==(24 if major==17 else 23))

(HERE/"mutation-effect-checks.json").write_text(json.dumps(RESULTS,indent=2,sort_keys=True)+"\n")
print(json.dumps(dict(passed=True,assertions=len(RESULTS),real_mutations=47)))
