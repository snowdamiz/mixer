#!/usr/bin/env python3
"""Independent finite audit and selected clean-source fixture; no runtime admission.

Producer collectors/installers are inspected subjects/helpers. Neither producer
validate() nor canonical() supplies this review's semantic oracle. A fresh source
install is compared with both retained majors using a separate semantic join.
"""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import base64
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/hosted-browser-relation-representation"
PG = Path("/opt/homebrew/Cellar/postgresql@17/17.11/bin")
EXPECTED_RECEIPT = "5f106ca994ba40d24e64d95c9f3889d0c783573d088f935272279c4c7e5fd6d8"
EXPECTED_TREE = "d22a9fb6f442207f0e78c2ce83c1c0386d26ba3966817fb6e50eb655b9987cf5"
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason", "oban"]
B, A = "public.mixer_browser_", "public.mixer_authz_"
NAMES = [B+x for x in ("sessions", "session_vault", "oidc_attempts", "session_events")] + [A+x for x in ("profiles", "principals", "bindings", "families", "credentials")]
COUNTS = dict(relations=9, columns=124, constraints=109, indexes=14, triggers=53, policies=32, table_effective=27, column_effective=372)
CAPS = dict(COUNTS, acl=512)
COMMANDS, CHECKS = [], []
ENV = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test", PYTHONDONTWRITEBYTECODE="1")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n")

def load(path):
    return json.loads(path.read_text())

def digest_map(values):
    return hashlib.sha256("".join(k+"\t"+v+"\n" for k,v in sorted(values.items())).encode()).hexdigest()

def check(name, condition):
    CHECKS.append(dict(name=name, passed=bool(condition)))
    if not condition:
        raise AssertionError(name)

def run(label, argv, data=None, cwd=ROOT, check_exit=True, timeout=30):
    entry = dict(label=label, argv=list(map(str, argv)), cwd=str(cwd), timeout_seconds=timeout)
    COMMANDS.append(entry)
    p = subprocess.Popen(entry["argv"], cwd=cwd, env=ENV, stdin=subprocess.PIPE if data is not None else None,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = p.communicate(None if data is None else data.encode(), timeout=timeout)
        entry["timed_out"] = False
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate(timeout=5)
        entry["timed_out"] = True
    entry["exit_code"] = p.returncode
    for suffix, content in (("stdout", out), ("stderr", err)):
        (HERE/(label+"."+suffix)).write_bytes(content)
    if data is not None:
        (HERE/(label+".stdin.sql")).write_text(data)
    if check_exit and (p.returncode or entry["timed_out"]):
        raise RuntimeError(label+" failed")
    return p.returncode, out.decode()

def rel(name):
    return name if name is None or name.startswith("public.") else "public."+name

def bag(rows):
    return Counter(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)

def independent_semantics(snapshot, cross_major=False):
    """Resolve all diagnostic identifiers to structural objects, preserving bags.

    The three admitted equivalences are automatic names, two actual bigint
    fast-default forms and (only in cross-major comparison) owner MAINTAIN.
    This is fixture comparison, not a production catalog decoder.
    """
    s = deepcopy(snapshot)
    s.pop("environment")
    index_ids = {}
    for row in s["indexes"]:
        index_ids["public."+row["name"]] = [rel(row["relation"]), row["columns"], row["predicate"], row["backing"]]
    constraint_ids = {(rel(c["relation"]), c["conname"]):
                      [rel(c["relation"]), c["contype"], c["columns"], rel(c["target"]), c["target_columns"], c["expression"], c["confmatchtype"], c["confupdtype"], c["confdeltype"]]
                      for c in s["constraints"]}
    for family, rows in s.items():
        for row in rows:
            for field in ("relation", "target", "opposite", "constraint_relation"):
                if field in row:
                    row[field] = rel(row[field])
            if "index" in row and row["index"] is not None:
                row["index"] = index_ids.get(row["index"], ["UNRESOLVED", row["index"]])
            if family == "columns" and (row["relation"], row["attname"]) in {(A+"profiles", "state_revision"), (A+"bindings", "revision")}:
                if (row["atthasmissing"], row["attmissingval"], row["type"]) in ((True, "{1}", "pg_catalog.int8"), (False, None, "pg_catalog.int8")):
                    row["atthasmissing"], row["attmissingval"] = "approved", "one-or-rewritten"
            if family == "constraints":
                row.pop("conname")
                row.pop("definition")
            if family == "indexes" and row["name"] != "mixer_browser_one_attempt":
                row.pop("name")
            if family == "triggers":
                key = (row["constraint_relation"], row.pop("constraint_name"))
                row["resolved_constraint"] = constraint_ids.get(key, ["UNRESOLVED", key]) if row["constraint_type"] else None
                row.pop("definition")
                if row["tgisinternal"]:
                    row.pop("tgname")
            if cross_major and family == "relations":
                row.pop("raw_acl")
            if cross_major and family == "table_effective":
                row.pop("maintain", None)
        if cross_major and family == "acl":
            rows[:] = [r for r in rows if not (r["grantee"] == r["grantor"] == "browser_schema_owner" and r["privilege_type"] == "MAINTAIN" and r["column_name"] is None and not r["is_grantable"])]
    return {family: bag(rows) for family, rows in s.items()}

def assert_source_shape(s, source, major):
    check(f"pg{major} exact complete family counts", all(len(s[k]) == v for k,v in COUNTS.items()) and len(s["acl"]) == (132 if major == 17 else 123))
    check(f"pg{major} nine exact identities", Counter(rel(r["relation"]) for r in s["relations"]) == Counter(NAMES))
    types = dict(text="text", bytea="bytea", integer="int4", bigint="int8", boolean="bool")
    for name in NAMES:
        cols = [r for r in s["columns"] if rel(r["relation"]) == name]
        expected = source["relations"][name]["columns"]
        check(f"pg{major} {name} independent source ordered columns", [(r["attnum"], r["attname"], r["type"], r["attnotnull"], r["default_expr"]) for r in cols] == [(i+1,c["name"],"pg_catalog."+types[c["type"]],not c["nullable"],c["default"]) for i,c in enumerate(expected)])
        keys = [r for r in s["constraints"] if rel(r["relation"]) == name and r["contype"] in ("p", "u")]
        t = source["relations"][name]
        check(f"pg{major} {name} independent source key multiset", Counter((r["contype"], tuple(r["columns"])) for r in keys) == Counter([("p",tuple(t["primary_key"]))]+[("u",tuple(x)) for x in t["unique"]]))
    fk_expected = []
    for name, table in source["relations"].items():
        fk_expected += [(name, tuple(f["columns"]), f["relation"], tuple(f["referenced_columns"])) for f in table["foreign_keys"]]
    fk_expected += [(f["source_relation"],tuple(f["columns"]),f["relation"],tuple(f["referenced_columns"])) for f in source["incoming_foreign_keys"]]
    fk_actual = [r for r in s["constraints"] if r["contype"] == "f"]
    check(f"pg{major} exact twelve independent source FKs with two incoming", Counter((rel(r["relation"]),tuple(r["columns"]),rel(r["target"]),tuple(r["target_columns"])) for r in fk_actual) == Counter(fk_expected) and len([r for r in fk_actual if rel(r["relation"]) not in NAMES]) == 2)
    check(f"pg{major} constraint flags and type multiplicities", Counter(r["contype"] for r in s["constraints"]) == dict(c=80,p=9,u=4,f=12,t=4) and all(r["connoinherit"] == (r["contype"] != "c") and r["conislocal"] and r["convalidated"] and r["coninhcount"] == 0 and r["conparentid"] == r["contypid"] == "0" and r["condeferrable"] == r["condeferred"] == (r["contype"] == "t") for r in s["constraints"]))
    by_name = {(rel(c["relation"]),c["attname"]): c for c in s["columns"]}
    sqltypes = {"pg_catalog.text":"text", "pg_catalog.bytea":"bytea", "pg_catalog.int4":"integer", "pg_catalog.int8":"bigint"}
    check(f"pg{major} FK equality operator three-vector builtin identities", all(all(r[vector] == ["=("+sqltypes[by_name[(rel(r["target"]),c)]["type"]]+","+sqltypes[by_name[(rel(r["target"]),c)]["type"]]+")" for c in r["target_columns"]] for vector in ("pfeq","ppeq","ffeq")) for r in fk_actual))
    indexes = {"public."+r["name"]:r for r in s["indexes"]}
    check(f"pg{major} all key and FK index backlinks", all(r["index"] in indexes and rel(indexes[r["index"]]["relation"]) == rel(r["target"] if r["contype"] == "f" else r["relation"]) and indexes[r["index"]]["columns"] == (r["target_columns"] if r["contype"] == "f" else r["columns"]) and indexes[r["index"]]["backing"] == (["p"] if r["contype"] == "p" else ["u"] if r["contype"] == "u" else indexes[r["index"]]["backing"]) for r in s["constraints"] if r["contype"] in ("p","u","f")))
    expected_ops = dict(text="text_ops:text:pg_catalog.text_ops", bytea="bytea_ops:bytea:pg_catalog.bytea_ops", int4="int4_ops:integer:pg_catalog.integer_ops", int8="int8_ops:bigint:pg_catalog.integer_ops")
    check(f"pg{major} every builtin btree opclass input family and collation", all(r["amname"] == "btree" and r["opclasses"] == ["pg_catalog."+expected_ops[by_name[(rel(r["relation"]),c)]["type"].split(".")[1]] for c in r["columns"]] and r["collations"] == ["pg_catalog.default" if by_name[(rel(r["relation"]),c)]["type"] == "pg_catalog.text" else None for c in r["columns"]] for r in s["indexes"]))
    fks = {(rel(c["relation"]),c["conname"]):c for c in fk_actual}
    builtin = {'"RI_FKey_check_ins"()':(5,False),'"RI_FKey_check_upd"()':(17,False),'"RI_FKey_noaction_del"()':(9,True),'"RI_FKey_noaction_upd"()':(17,True)}
    ris = [r for r in s["triggers"] if r["tgisinternal"]]
    check(f"pg{major} exact RI four-function groups", len(ris)==48 and all(Counter(t["function"] for t in ris if (rel(t["constraint_relation"]),t["constraint_name"])==key) == Counter(list(builtin)) for key in fks))
    for t in ris:
        c = fks[(rel(t["constraint_relation"]),t["constraint_name"])]
        typ,parent = builtin[t["function"]]
        check(f"pg{major} RI semantic endpoint {t['tgname']}", t["tgtype"]==typ and t["function_namespace"]=="pg_catalog" and rel(t["relation"])==rel(c["target"] if parent else c["relation"]) and rel(t["opposite"])==rel(c["relation"] if parent else c["target"]) and t["index"]==c["index"] and t["constraint_type"]=="f")
    check(f"pg{major} all trigger enforcement metadata", all(t["tgenabled"]=="O" and t["tgnargs"]==0 and t["args"]==t["tgattr"]=="" and t["qual"] is t["tgoldtable"] is t["tgnewtable"] is None and t["tgparentid"]=="0" and t["tgdeferrable"]==t["tginitdeferred"]==(not t["tgisinternal"] and t["constraint_type"]=="t") for t in s["triggers"]))
    user = [t for t in s["triggers"] if not t["tgisinternal"]]
    expected_user = [(t["relation"],t["name"],t["function"],1+(2 if t["timing"]=="BEFORE" else 0)+sum(dict(INSERT=4,UPDATE=16,DELETE=8)[e] for e in t["events"]),t["constraint"],t["deferrable"]) for t in source["user_triggers"]]
    check(f"pg{major} exact five explicit user trigger names and source functions", Counter((rel(t["relation"]),t["tgname"],t["function"],t["tgtype"],t["constraint_type"]=="t",t["tgdeferrable"]) for t in user)==Counter(expected_user))
    commands = dict(SELECT="r",INSERT="a",UPDATE="w",DELETE="d",ALL="*")
    expected_policy = [(name,p["name"],commands[p["command"]],tuple("browser_writer" if x=="$writer" else x for x in p["roles"]),p["permissive"]) for name,ps in source["policies"].items() for p in ps]
    check(f"pg{major} exact policy names commands PUBLIC writer and permissiveness", Counter((rel(p["relation"]),p["polname"],p["polcmd"],tuple(p["roles"]),p["polpermissive"]) for p in s["policies"])==Counter(expected_policy))
    table = {(name, role):source["writer_grants"][name]["table"] if role=="browser_writer" else ["SELECT"] if role=="browser_ordinary" and name.startswith(A) else [] for name in NAMES for role in ("browser_lifecycle","browser_writer","browser_ordinary")}
    privileges = {"sel":"SELECT","ins":"INSERT","upd":"UPDATE","del":"DELETE","trunc":"TRUNCATE","refs":"REFERENCES","trig":"TRIGGER","maintain":"MAINTAIN"}
    check(f"pg{major} exact effective table rights", all(all(v==(privileges[k] in table[(rel(r["relation"]),r["role"])]) for k,v in r.items() if k in privileges) for r in s["table_effective"]))
    check(f"pg{major} exact effective column rights", all(all(r[k]==(p in table[(rel(r["relation"]),r["role"])] or (p=="UPDATE" and r["role"]=="browser_writer" and r["attname"] in source["writer_grants"][rel(r["relation"])]["update_columns"])) for k,p in privileges.items() if k in ("sel","ins","upd","refs")) for r in s["column_effective"]))
    acl = []
    for name in NAMES:
        acl += [(name,None,"browser_schema_owner","browser_schema_owner",p,False) for p in ["SELECT","INSERT","UPDATE","DELETE","TRUNCATE","REFERENCES","TRIGGER"]+(["MAINTAIN"] if major==17 else [])]
        acl += [(name,None,role,"browser_schema_owner",p,False) for role in ("browser_lifecycle","browser_writer","browser_ordinary") for p in table[(name,role)]]
        acl += [(name,c,"browser_writer","browser_schema_owner","UPDATE",False) for c in source["writer_grants"][name]["update_columns"]]
    check(f"pg{major} exact raw ACL grants grantors grant options", Counter((rel(r["relation"]),r["column_name"],r["grantee"],r["grantor"],r["privilege_type"],r["is_grantable"]) for r in s["acl"])==Counter(acl))
    check(f"pg{major} explicit column ACL nullness", all((r["raw_acl"] is not None)==(r["attname"] in source["writer_grants"][rel(r["relation"])]["update_columns"]) for r in s["columns"]))
    check(f"pg{major} exact baseline defaults and fast-default representation", all((r["atthasmissing"],r["attmissingval"],r["type"])==(True,"{1}","pg_catalog.int8") if (rel(r["relation"]),r["attname"]) in {(A+"profiles","state_revision"),(A+"bindings","revision")} else not r["atthasmissing"] and r["attmissingval"] is None for r in s["columns"]))
    e=s["environment"]
    check(f"pg{major} selected C libc UTF8 origin environment", e["server_version_num"]==str(170011 if major==17 else 160015) and e["lc_collate"]==e["lc_ctype"]=="C" and e["encoding"]=="UTF8" and e["replication_role"]=="origin" and e["datlocprovider"]=="c" and e["datcollversion"] is e["actual_collation_version"] is None)

def main():
    started = False
    scratch = None
    formatter = None
    receipt = dict(schema=1, started_epoch=time.time(), scope="Independent bounded relation-representation review; one fresh PG17 clean source installation, offline both-major semantic/catalog mutation audit. No runtime admission or GA.", cleanup={})
    inputs = {}
    try:
        check("producer exact requested receipt freeze", sha(PRODUCER/"receipt.json")==EXPECTED_RECEIPT)
        p = load(PRODUCER/"receipt.json")
        old_source = load(ROOT/"verification/hosted-browser-relation-admission-contract-review/receipt.json")
        source = load(ROOT/"verification/hosted-browser-relation-admission-contract-review/independent-derived-baseline.json")
        baseline = {}
        for major in (16,17):
            attempt=ROOT/p["final_attempts"][str(major)]["attempt"]
            r=load(attempt/"receipt.json")
            check(f"pg{major} attempt receipt binding", sha(attempt/"receipt.json")==p["final_attempts"][str(major)]["receipt_sha256"])
            check(f"pg{major} every retained output bound", all(sha(attempt/k)==h for k,h in r["outputs_sha256"].items()))
            bindings=load(attempt/"source-bindings.json")
            check(f"pg{major} exact immutable source tree", digest_map(bindings)==EXPECTED_TREE and all(sha(attempt/"inputs"/k)==h for k,h in bindings.items()))
            drift={k:dict(frozen=h,current=sha(ROOT/k)) for k,h in bindings.items() if sha(ROOT/k)!=h}
            receipt.setdefault("coordinator_context_drift",{})[str(major)]=drift
            check(f"pg{major} ordinary sources helpers and contract continuity", all(k=="PLAN.md" for k in drift))
            inputs.update({str((attempt/k).relative_to(ROOT)):h for k,h in r["outputs_sha256"].items()})
            inputs.update({str((attempt/"inputs"/k).relative_to(ROOT)):h for k,h in bindings.items()})
            inputs.update({k:sha(ROOT/k) for k in bindings})
            check(f"pg{major} locked beam continuity", all(sha(ROOT/k)==h for k,h in load(attempt/"dependency-beams.json").items()))
            check(f"pg{major} baseline frozen before all attacked commands", [c["label"] for c in r["commands"]].index("clean-baseline") < min(i for i,c in enumerate(r["commands"]) if c["label"].startswith("mutation-")))
            baseline[major]=load(attempt/"clean-baseline.json")
            assert_source_shape(baseline[major],source,major)
        check("prior independent ordinary source/delegate/Oban bindings unchanged", all(sha(ROOT/k)==h for k,h in old_source["input_sha256"].items() if k.startswith("hosted/")))
        check("both majors identical except nine owner MAINTAIN rows", independent_semantics(baseline[16],True)==independent_semantics(baseline[17],True))
        # Import ONLY as a subject under test, after deriving our source/oracle data.
        spec=importlib.util.spec_from_file_location("representation_subject",PRODUCER/"qualify.py")
        subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
        for major in (16,17):
            attempt=ROOT/p["final_attempts"][str(major)]["attempt"]
            frozen=independent_semantics(baseline[major])
            mutations=load(attempt/"mutation-results.json")
            for m in mutations:
                attacked=load(attempt/("mutation-"+m["name"]+".stdout"))
                check(f"pg{major} retained real attack independently differs {m['name']}", independent_semantics(attacked)!=frozen)
                check(f"pg{major} retained attack transaction rollback {m['name']}", (attempt/("mutation-"+m["name"]+".stdin.sql")).read_text().startswith("BEGIN;") and (attempt/("mutation-"+m["name"]+".stdin.sql")).read_text().rstrip().endswith("ROLLBACK;"))
            check(f"pg{major} fresh post-attack retained baseline restored", independent_semantics(load(attempt/"restored-baseline.stdout"))==frozen)
            check(f"pg{major} automatic rename source equivalence", independent_semantics(load(attempt/"automatic-name-control.stdout"))==frozen)
            check(f"pg{major} real fast-default rewrite source equivalence", independent_semantics(load(attempt/"fast-default-rewrite-control.stdout"))==frozen)
        # Small precise in-memory probes ensure normalization cannot erase links.
        s=baseline[17]
        mutations=[]
        def attack(name,family,select,field,value):
            a=deepcopy(s);row=next(r for r in a[family] if select(r))
            if row[field]==value:
                raise AssertionError("ineffective review probe: "+name)
            row[field]=value
            mutations.append((name,a))
        attack("FK parent endpoint","constraints",lambda r:r["contype"]=="f" and rel(r["target"])!=A+"principals","target",A+"principals")
        attack("FK ordered target keys","constraints",lambda r:len(r["target_columns"])>1,"target_columns",["id"])
        attack("FK builtin equality identity","constraints",lambda r:r["contype"]=="f","pfeq",["public.=(text,text)"])
        attack("FK referenced index linkage","constraints",lambda r:r["contype"]=="f","index","public.mixer_browser_sessions_pkey")
        attack("index opfamily","indexes",lambda r:True,"opclasses",["pg_catalog.int4_ops:integer:public.integer_ops"])
        attack("partial explicit name","indexes",lambda r:r["name"]=="mixer_browser_one_attempt","name","other")
        attack("user trigger explicit name","triggers",lambda r:not r["tgisinternal"],"tgname","other")
        attack("RI constraint relation linkage","triggers",lambda r:r["tgisinternal"],"constraint_relation",A+"principals")
        attack("RI constraint definition linkage","triggers",lambda r:r["tgisinternal"],"constraint_definition","FOREIGN KEY (id) REFERENCES public.mixer_authz_principals(id)")
        attack("RI opposite endpoint","triggers",lambda r:r["tgisinternal"],"opposite",A+"credentials")
        attack("RI referenced index linkage","triggers",lambda r:r["tgisinternal"],"index","public.mixer_browser_sessions_pkey")
        attack("policy NULL versus TRUE","policies",lambda r:r["using_expr"] is None,"using_expr","true")
        attack("policy PUBLIC versus writer","policies",lambda r:r["roles"]==["PUBLIC"],"roles",["browser_writer"])
        attack("ACL grantor","acl",lambda r:r["grantee"]=="browser_writer","grantor","browser_writer")
        attack("ACL grant option","acl",lambda r:r["grantee"]=="browser_writer","is_grantable",True)
        attack("fast default malformed one","columns",lambda r:r["atthasmissing"],"attmissingval","{01}")
        attack("ciphertext default","columns",lambda r:r["attname"]=="ciphertext_version" and rel(r["relation"])==B+"oidc_attempts","default_expr","2")
        for name,a in mutations:
            check("independent semantic negative: "+name,independent_semantics(a)!=independent_semantics(s))
            check("producer normalization subject negative: "+name,subject.canonical(a)!=subject.canonical(s))
        a=deepcopy(s);a["constraints"].append(deepcopy(a["constraints"][0]))
        check("duplicate constraint multiplicity preserved",independent_semantics(a)!=independent_semantics(s) and subject.canonical(a)!=subject.canonical(s))
        receipt["independent_semantic_negative_controls"]=len(mutations)+1
        # Bounds observed in fixture output are not pre-deparse/runtime guards.
        for major in (16,17):
            attempt=ROOT/p["final_attempts"][str(major)]["attempt"]
            check(f"pg{major} output under 2MiB clean bound",(attempt/"clean-baseline.stdout").stat().st_size<2*1024*1024)
            for family,cap in CAPS.items():
                check(f"pg{major} {family} sentinel in SQL", "LIMIT "+str(cap+1) in (PRODUCER/"snapshot.sql").read_text())
        # Source capture is a copied, already-reviewed inert source evaluator.
        _,capture=run("ordinary-source-capture",["elixir",HERE/"capture_ordinary_source.exs"])
        check("fresh independent inert capture identical to reviewed source evaluation",capture==(ROOT/"verification/hosted-browser-relation-admission-contract-review/source-capture.stdout").read_text())
        functions={}
        for line in capture.splitlines():
            kind,origin,encoded=line.split("\t")
            if kind=="function_source": functions[origin]=base64.b64decode(encoded,validate=True).decode()
        run("python-version",["python3","--version"])
        run("elixir-version",["elixir","--version"])
        run("psql-version",[PG/"psql","--version"])
        _,revision=run("source-revision",["git","rev-parse","HEAD"]);receipt["source_revision"]=revision.strip()
        formatter=Path(tempfile.mkdtemp(prefix="mixer-relation-review-format-"))
        for name,path in (("capture.exs",HERE/"capture_ordinary_source.exs"),("install.exs",PRODUCER/"install.exs")):
            shutil.copy2(path,formatter/name)
        run("projectless-format",["mix","format","--check-formatted","capture.exs","install.exs"],cwd=formatter)
        shutil.rmtree(formatter);receipt["cleanup"]["owned_formatter_removed"]=not formatter.exists()
        scratch=Path(tempfile.mkdtemp(prefix="mixer-relation-review-pg17-"));receipt["owned_scratch"]=str(scratch)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
        run("initdb",[PG/"initdb","-D",scratch/"data","-U","browser_admin","-A","trust","--no-locale","-E","UTF8"])
        started=True
        run("start",[PG/"pg_ctl","-D",scratch/"data","-l",HERE/"server.log","-o",f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC","-w","start"])
        db=[PG/"psql","-X","-q","-A","-t","-h","127.0.0.1","-p",port,"-U","browser_admin","-d","postgres","-v","ON_ERROR_STOP=1"]
        run("roles",db,data=";".join("CREATE ROLE "+role+" "+login+" NOSUPERUSER NOBYPASSRLS NOINHERIT" for role,login in (("browser_schema_owner","NOLOGIN"),("browser_writer","NOLOGIN"),("browser_lifecycle","LOGIN"),("browser_ordinary","LOGIN"),("representation_extra","NOLOGIN")))+";")
        run("database",db,data="CREATE DATABASE browser_storage OWNER browser_schema_owner;")
        db[db.index("postgres")]="browser_storage"
        ENV["REPRESENTATION_PORT"]=str(port)
        run("install-all-nine-source",["elixir"]+[arg for dep in DEPS for arg in ("-pa",ROOT/"hosted/_build/test/lib"/dep/"ebin")]+[PRODUCER/"install.exs"],timeout=60)
        sql=(PRODUCER/"snapshot.sql").read_text().replace("__MAINTAIN__",",has_table_privilege(role,c.oid,'MAINTAIN') AS maintain")
        _,out=run("fresh-source-snapshot",db,data=sql)
        clean=json.loads(out);dump(HERE/"fresh-source-baseline.json",clean)
        assert_source_shape(clean,source,17)
        check("fresh independently installed source agrees with producer pg17 frozen semantics",independent_semantics(clean)==independent_semantics(s))
        check("fresh independently installed source agrees with producer pg16 expressions and semantics",independent_semantics(clean,True)==independent_semantics(baseline[16],True))
        # Numeric linkage and exact prosrc join are collected separately below.
        linksql=(HERE/"linkage.sql").read_text()
        _,out=run("independent-numeric-linkage",db,data=linksql);links=json.loads(out)
        dump(HERE/"independent-numeric-linkage.json",links)
        fklinks=links["foreign_keys"]
        check("fresh numeric exact 12 FK 48 RI edge closure",len(fklinks)==12 and all(r["trigger_count"]==4 and r["linked_count"]==4 and r["operator_count"]==r["key_count"]*3 and r["builtin_operators"] for r in fklinks))
        check("fresh numeric same tgfoid as exact ordinary noarg admitted functions",len(links["user_functions"])==4 and all(r["namespace"]=="public" and r["prosrc"]==functions[r["name"]] and r["noarg"] and r["returns_trigger"] and r["security_definer"] and r["owner"]=="browser_writer" for r in links["user_functions"]))
        # Additional real attacks isolate TRUE/NULL and role-zero distinctions.
        _,out=run("live-policy-true-to-null",db,data="BEGIN; ALTER POLICY mixer_browser_read ON public.mixer_browser_sessions USING (NULL::boolean);\n"+sql+"\nROLLBACK;")
        check("fresh live policy TRUE versus NULL independently rejected",independent_semantics(json.loads(out))!=independent_semantics(clean))
        _,out=run("live-policy-writer-to-public",db,data="BEGIN; ALTER POLICY mixer_browser_read ON public.mixer_browser_sessions TO PUBLIC;\n"+sql+"\nROLLBACK;")
        attacked=json.loads(out)
        check("fresh live policy role change independently rejected",independent_semantics(attacked)!=independent_semantics(clean))
        _,out=run("fresh-restored-snapshot",db,data=sql)
        check("fresh rollback restores frozen independent source baseline",independent_semantics(json.loads(out))==independent_semantics(clean))
        receipt["passed"]=True
    except Exception as error:
        receipt["failure"]=type(error).__name__+": "+str(error)
    finally:
        if formatter and formatter.exists():
            shutil.rmtree(formatter);receipt["cleanup"]["owned_formatter_removed"]=not formatter.exists()
        if scratch:
            if started and (scratch/"data/postmaster.pid").exists():
                run("stop",[PG/"pg_ctl","-D",scratch/"data","-m","immediate","-w","stop"],check_exit=False)
            receipt["cleanup"]["owned_postmaster_pid_absent"]=not (scratch/"data/postmaster.pid").exists()
            if receipt["cleanup"]["owned_postmaster_pid_absent"]:
                shutil.rmtree(scratch)
            receipt["cleanup"]["owned_scratch_removed"]=not scratch.exists()
        receipt["input_sha256"]=inputs
        receipt["input_tree_sha256"]=digest_map(inputs)
        receipt["producer_receipt_sha256"]=EXPECTED_RECEIPT
        receipt["producer_source_tree_sha256"]=EXPECTED_TREE
        receipt["commands"]=COMMANDS
        receipt["checks_passed"]=sum(x["passed"] for x in CHECKS)
        receipt["success"]=receipt.get("passed",False) and all(receipt["cleanup"].values())
        dump(HERE/"checks.json",CHECKS)
        receipt["finished_epoch"]=time.time()
        dump(HERE/"run-receipt.json",receipt)
        print(json.dumps({k:receipt.get(k) for k in ("success","failure","checks_passed","cleanup")}))
    return 0 if receipt["success"] else 1

if __name__=="__main__":
    raise SystemExit(main())
