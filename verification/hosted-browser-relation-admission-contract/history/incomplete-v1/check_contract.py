#!/usr/bin/env python3
"""Offline structure and source binding only. This cannot authorize any runtime."""
import copy
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
from expectations import A, B, TABLES, WRITER, POLICIES, TRIGGERS, INCOMING_FOREIGN_KEYS, S, M3, M4, M6, M7, SESSION, manifest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = [S, M3, M4, M6, M7, SESSION, "docs/hosted-browser-lifecycle-runtime-contract.md"]


def norm(sql):
    # Whitespace outside quoted literals only. No boolean/SQL semantic rewrite.
    return "".join(re.findall(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|\S", sql))


def split_top(sql, delimiter=","):
    chunks, start, depth, quote, i = [], 0, 0, None, 0
    while i < len(sql):
        c = sql[i]
        if quote:
            if c == quote:
                if i+1 < len(sql) and sql[i+1] == quote:
                    i += 1
                else:
                    quote = None
        elif c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced source SQL")
        elif c == delimiter and depth == 0:
            chunks.append(sql[start:i].strip())
            start = i+1
        i += 1
    if quote or depth:
        raise ValueError("unbalanced source SQL")
    chunks.append(sql[start:].strip())
    return chunks


def parenthesized(sql, position):
    assert sql[position] == "("
    depth, quote, i = 0, None, position
    while i < len(sql):
        c = sql[i]
        if quote:
            if c == quote:
                if i+1 < len(sql) and sql[i+1] == quote:
                    i += 1
                else:
                    quote = None
        elif c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return sql[position+1:i], i+1
        i += 1
    raise ValueError("missing closing parenthesis")


def parse_table(sql):
    head = re.match(r"CREATE TABLE (public\.\w+)\s*\(", sql)
    assert head, sql
    body, end = parenthesized(sql, head.end()-1)
    assert not sql[end:].strip(" ;\n")
    result = dict(columns=[], checks=[], primary_key=[], unique=[], foreign_keys=[], extra_indexes=[])
    for fragment in split_top(body):
        column = re.match(r"(\w+) (text|bytea|integer|bigint|boolean)\b(.*)", fragment, re.S)
        if column:
            name, kind, rest = column.groups()
            result["columns"].append(dict(name=name, type=kind,
                nullable="NOT NULL" not in rest and "PRIMARY KEY" not in rest,
                default="1" if "DEFAULT 1" in rest else None, identity="", generated="", typmod=-1, dimensions=0))
            if "PRIMARY KEY" in rest:
                result["primary_key"] = [name]
            if "UNIQUE" in rest:
                result["unique"].append([name])
            if "REFERENCES" in rest:
                fragment = "FOREIGN KEY(" + name + ") " + rest[rest.index("REFERENCES"):]
        elif fragment.startswith("PRIMARY KEY"):
            keys, _ = parenthesized(fragment, fragment.index("("))
            result["primary_key"] = [k.strip() for k in keys.split(",")]
        elif fragment.startswith("UNIQUE"):
            keys, _ = parenthesized(fragment, fragment.index("("))
            result["unique"].append([k.strip() for k in keys.split(",")])
        elif not fragment.startswith(("CHECK", "FOREIGN KEY")):
            raise ValueError("unrecognized accepted source fragment: " + fragment)
        if fragment.startswith("FOREIGN KEY"):
            keys, offset = parenthesized(fragment, fragment.index("("))
            target = re.match(r"\s*REFERENCES (public\.\w+)\s*\(", fragment[offset:])
            assert target, fragment
            referenced, _ = parenthesized(fragment[offset:], target.end()-1)
            result["foreign_keys"].append(dict(columns=[x.strip() for x in keys.split(",")],
                relation=target[1], referenced_columns=[x.strip() for x in referenced.split(",")],
                match="s", on_update="a", on_delete="a", deferrable=False, initially_deferred=False))
        for check in re.finditer(r"\bCHECK\s*\(", fragment):
            expression, _ = parenthesized(fragment, check.end()-1)
            result["checks"].append(expression)
    return head[1], result


def capture():
    run = subprocess.run(["elixir", str(HERE/"extract_accepted_ddl.exs")], cwd=ROOT,
                         text=True, capture_output=True, timeout=30, check=True)
    assert not run.stderr, run.stderr
    return json.loads(run.stdout)


def source_surface(captured):
    statements = [s.strip() for ss in captured["ordinary"].values() for s in ss] + captured["browser"]
    out = {}
    for sql in statements:
        if sql.startswith("CREATE TABLE "):
            rel, value = parse_table(sql)
            if rel in TABLES:
                assert rel not in out
                out[rel] = value
        add = re.match(r"ALTER TABLE (public\.\w+)\s+ADD COLUMN (.*)", sql, re.S)
        if add and add[1] in TABLES:
            _, partial = parse_table("CREATE TABLE public.synthetic ("+add[2]+")")
            out[add[1]]["columns"] += partial["columns"]
            out[add[1]]["checks"] += partial["checks"]
        index = re.match(r"CREATE UNIQUE INDEX (\w+) ON (public\.\w+)\(([^)]+)\) WHERE (.*)", sql, re.S)
        if index and index[2] in TABLES:
            out[index[2]]["extra_indexes"].append(dict(name=index[1], unique=True,
                columns=[x.strip() for x in index[3].split(",")], predicate=index[4]))
    return out


def canonical_shape(surface):
    out = copy.deepcopy(surface)
    for row in out.values():
        row.pop("sources", None)
        # Multiset retained: sorting never erases duplicates.
        row["checks"] = sorted(norm(c) for c in row["checks"])
        row["unique"] = sorted(row["unique"])
        row["foreign_keys"] = sorted(row["foreign_keys"], key=lambda x: json.dumps(x, sort_keys=True))
        for index in row["extra_indexes"]:
            index["predicate"] = norm(index["predicate"])
    return out


def source_policies(captured):
    statements = [s.strip() for ss in captured["ordinary"].values() for s in ss] + captured["provisioning"]
    out = {r: [] for r in TABLES}
    for sql in statements:
        found = re.match(r"CREATE POLICY (\w+) ON (public\.\w+) FOR (SELECT|INSERT|UPDATE)(.*)", sql, re.S)
        if not found or found[2] not in TABLES:
            continue
        name, rel, command, rest = found.groups()
        target = re.search(r"\bTO (\w+)", rest)
        roles = ["$writer"] if target and target[1] == "relation_contract_writer" else ["PUBLIC"]
        assert target is None or roles == ["$writer"]
        using_match = re.search(r"\bUSING\s*\(", rest)
        check_match = re.search(r"\bWITH CHECK\s*\(", rest)
        using = parenthesized(rest, using_match.end()-1)[0] if using_match else None
        check = parenthesized(rest, check_match.end()-1)[0] if check_match else None
        out[rel].append(dict(name=name, command=command, roles=roles, permissive=True, using=using, check=check))
    return out


def canonical_policies(surface):
    out = copy.deepcopy(surface)
    for rows in out.values():
        for p in rows:
            for key in ("using", "check"):
                if p[key] is not None:
                    p[key] = norm(p[key])
        rows.sort(key=lambda p: json.dumps(p, sort_keys=True))
    return out


def writer_grants(captured):
    out = {r: dict(table=[], update_columns=[]) for r in TABLES}
    for sql in captured["provisioning"]:
        match = re.match(r"GRANT (.+) ON (public\.\w+) TO relation_contract_writer$", sql)
        if not match or match[2] not in TABLES:
            continue
        for priv in split_top(match[1]):
            update = re.fullmatch(r"UPDATE\(([^)]+)\)", priv)
            if update:
                out[match[2]]["update_columns"] += update[1].split(",")
            else:
                out[match[2]]["table"].append(priv)
    return out


def source_triggers(captured):
    out = []
    for sql in captured["browser"]:
        m = re.match(r"CREATE (CONSTRAINT )?TRIGGER (\w+) (AFTER|BEFORE) (.+?) ON (public\.\w+) (.*?)FOR EACH ROW EXECUTE FUNCTION (public\.\w+\(\))$", sql)
        if m:
            constraint, name, timing, events, rel, attrs, function = m.groups()
            out.append(dict(relation=rel, name=name, function=function, timing=timing,
                events=events.split(" OR "), constraint=bool(constraint),
                deferrable="DEFERRABLE" in attrs, initially_deferred="INITIALLY DEFERRED" in attrs))
    return out


class ContractChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.captured = capture()

    def test_01_source_bindings(self):
        pinned = json.loads((HERE/"source-bindings.json").read_text())
        self.assertEqual(set(pinned["inputs"]), set(INPUTS))
        for path, digest in pinned["inputs"].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), digest, path)

    def test_02_all_nine_complete_column_constraint_index_shapes(self):
        self.assertEqual(canonical_shape(source_surface(self.captured)), canonical_shape(TABLES))
        self.assertEqual(len(TABLES), 9)
        self.assertEqual(sum(len(t["columns"]) for t in TABLES.values()), 124)
        self.assertEqual(sum(len(t["checks"]) for t in TABLES.values()), 80)
        self.assertEqual(sum(len(t["unique"]) for t in TABLES.values()), 4)
        self.assertEqual(sum(len(t["foreign_keys"]) for t in TABLES.values()), 10)
        self.assertEqual(sum(1+len(t["unique"])+len(t["extra_indexes"]) for t in TABLES.values()), 14)

    def test_03_exact_policy_multisets_and_public_targets(self):
        self.assertEqual(canonical_policies(source_policies(self.captured)), canonical_policies(POLICIES))
        self.assertEqual(sum(map(len, POLICIES.values())), 32)
        self.assertEqual(sum(p["roles"] == ["PUBLIC"] for rows in POLICIES.values() for p in rows), 10)

    def test_04_exact_writer_table_and_column_grants(self):
        self.assertEqual(writer_grants(self.captured), manifest()["writer_grants"])
        for rel, row in manifest()["writer_grants"].items():
            self.assertNotIn("UPDATE", row["table"])
            self.assertTrue(set(row["update_columns"]) <= {c["name"] for c in TABLES[rel]["columns"]})

    def test_05_exact_user_triggers(self):
        expected = [{k:v for k,v in x.items() if k != "source"} for x in TRIGGERS]
        self.assertEqual(source_triggers(self.captured), expected)

    def test_06_touched_tables_have_no_directory_policies(self):
        self.assertFalse(any(p["name"] == "directory_read" for rows in source_policies(self.captured).values() for p in rows))
        directory = [s for s in self.captured["ordinary"][pathlib.Path(M6).name] if "CREATE POLICY directory_read" in s]
        self.assertEqual(len(directory), 3)
        self.assertTrue(all(any(A+r in s for r in ("memberships", "organizations", "projects")) for s in directory))

    def test_07_negative_controls_reject_missing_extra_and_weakened_source(self):
        baseline = canonical_shape(TABLES)
        mutations = []
        for field in ("columns", "checks", "foreign_keys", "extra_indexes"):
            target = next(r for r,t in TABLES.items() if t[field])
            for extra in (False, True):
                changed = copy.deepcopy(TABLES)
                if extra:
                    changed[target][field].append(copy.deepcopy(changed[target][field][0]))
                else:
                    changed[target][field].pop()
                mutations.append(changed)
        for field, value in (("nullable", True), ("type", "text"), ("default", "0"), ("generated", "s"), ("identity", "a")):
            changed = copy.deepcopy(TABLES)
            changed[B+"sessions"]["columns"][0][field] = value
            mutations.append(changed)
        changed = copy.deepcopy(TABLES)
        changed[B+"sessions"]["checks"][0] = "true"
        mutations.append(changed)
        changed = copy.deepcopy(TABLES)
        changed[B+"sessions"]["foreign_keys"][0]["on_delete"] = "c"
        mutations.append(changed)
        changed = copy.deepcopy(TABLES)
        changed[B+"oidc_attempts"]["extra_indexes"][0]["predicate"] = "true"
        mutations.append(changed)
        self.assertEqual(len(mutations), 16)
        for mutation in mutations:
            self.assertNotEqual(canonical_shape(mutation), baseline)

    def test_08_policy_negative_controls_preserve_null_false_roles_and_duplicates(self):
        baseline = canonical_policies(POLICIES)
        for edit in ("extra", "role", "permissive", "check", "using", "command"):
            changed = copy.deepcopy(POLICIES)
            p = changed[A+"profiles"][0]
            if edit == "extra":
                changed[A+"profiles"].append(copy.deepcopy(p))
            elif edit == "role":
                p["roles"] = ["$ordinary_runtime_login"]
            elif edit == "permissive":
                p["permissive"] = False
            elif edit == "check":
                p["check"] = "false"
            elif edit == "using":
                p["using"] = "true"
            else:
                p["command"] = "ALL"
            self.assertNotEqual(canonical_policies(changed), baseline)

    def test_09_manifest_is_current_and_contains_no_live_oracle(self):
        self.assertEqual(json.loads((HERE/"relation-matrix.json").read_text()), manifest())
        self.assertEqual(set(manifest()["relations"]), set(manifest()["writer_grants"]))
        self.assertEqual(set(manifest()["relations"]), set(POLICIES))
        for rel, t in TABLES.items():
            for ptr in t["sources"]:
                lines = (ROOT/ptr["path"]).read_text().splitlines()
                self.assertIn(rel, "\n".join(lines[ptr["start"]-1:ptr["end"]]))
        for trig in TRIGGERS:
            start,end = trig["source"]
            self.assertIn('function("'+trig["function"].removeprefix("public.").removesuffix("()")+'"', "\n".join((ROOT/S).read_text().splitlines()[start-1:end]))

    def test_10_runtime_cases_are_pending_and_cover_each_dimension(self):
        cases = json.loads((HERE/"runtime-adversity-matrix.json").read_text())
        self.assertGreaterEqual(len(cases), 40)
        self.assertTrue(all(c["status"] == "pending_runtime" for c in cases))
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        self.assertEqual({c["dimension"] for c in cases}, {"transaction", "relation", "column", "constraint", "index", "trigger", "policy", "acl", "canonicalization", "composition"})

    def test_11_incoming_fk_boundary_is_complete(self):
        incoming = []
        for statements in self.captured["ordinary"].values():
            for sql in statements:
                if sql.strip().startswith("CREATE TABLE "):
                    rel, parsed = parse_table(sql.strip())
                    if rel not in TABLES:
                        incoming += [dict(source_relation=rel, **f) for f in parsed["foreign_keys"] if f["relation"] in TABLES]
        expected = [{k:v for k,v in row.items() if k != "source"} for row in INCOMING_FOREIGN_KEYS]
        # For boundary rows relation is the referenced target in fk(), whereas
        # source_relation identifies the referencing relation unambiguously.
        self.assertEqual(incoming, expected)

    def test_12_exact_trigger_function_source_bindings(self):
        pinned = json.loads((HERE/"trigger-function-source-bindings.json").read_text())
        self.assertEqual(pinned, self.captured["trigger_function_source_hashes"])
        self.assertEqual(len(pinned), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
