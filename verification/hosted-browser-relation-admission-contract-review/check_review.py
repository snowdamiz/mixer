#!/usr/bin/env python3
"""Independent source-to-document checks; never a PostgreSQL admission check.

This script does not import producer expectations or run its extraction/checker.
It evaluates only explicitly approved ordinary source through an inert stub,
derives the baseline first, then compares the producer's exported JSON data.
Tokenization is for static transcription review only. It is not a proposed live
expression canonicalizer and cannot authorize a session or release.
"""
from __future__ import annotations

import base64
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/hosted-browser-relation-admission-contract"
B = "public.mixer_browser_"
A = "public.mixer_authz_"
# Independently selected from the requested baseline, not the producer manifest.
NAMES = [B + x for x in ("sessions", "session_vault", "oidc_attempts", "session_events")] + [
    A + x for x in ("profiles", "principals", "bindings", "families", "credentials")]
EXPECTED_COUNTS = {
    B + "sessions": (22, 17, 1, 1, 2, 2, 1, 3),
    B + "session_vault": (10, 6, 1, 0, 1, 1, 1, 3),
    B + "oidc_attempts": (26, 20, 1, 0, 1, 2, 1, 3),
    B + "session_events": (30, 17, 1, 0, 1, 1, 2, 2),
    A + "profiles": (7, 6, 1, 1, 0, 2, 0, 4),
    A + "principals": (5, 4, 1, 1, 0, 2, 0, 4),
    A + "bindings": (7, 2, 1, 0, 2, 1, 0, 3),
    A + "families": (8, 4, 1, 1, 2, 2, 0, 5),
    A + "credentials": (9, 4, 1, 0, 1, 1, 0, 5),
}
TOKEN = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|[A-Za-z_][A-Za-z_0-9$]*|[0-9]+|::|<>|<=|>=|!=|\S")


def tokens(text):
    # Strip no parentheses, casts, qualifiers, aliases, literals or operands.
    # Only ordinary-source SQL token whitespace and unquoted case differ.
    return [x if x.startswith(("'", '"')) else x.lower() for x in TOKEN.findall(text)]


def enclosed(ts, start):
    assert ts[start] == "(", (ts, start)
    depth = 0
    for i in range(start, len(ts)):
        depth += (ts[i] == "(") - (ts[i] == ")")
        if depth == 0:
            return ts[start + 1:i], i + 1
    raise AssertionError("unbalanced static SQL source")


def split_top(ts):
    groups, last, depth = [], 0, 0
    for i, t in enumerate(ts):
        depth += (t == "(") - (t == ")")
        if t == "," and depth == 0:
            groups.append(ts[last:i])
            last = i + 1
    groups.append(ts[last:])
    assert all(groups)
    return groups


def names(ts):
    return ["".join(x) for x in split_top(ts)]


def qualified(ts, start):
    assert ts[start + 1] == "."
    return ".".join(ts[start:start + 3:2]), start + 3


def expression_at(ts, key):
    try:
        pos = ts.index(key)
    except ValueError:
        return None
    return enclosed(ts, pos + 1)[0]


def fk(ts, columns):
    target, pos = qualified(ts, ts.index("references") + 1)
    cols, end = enclosed(ts, pos)
    assert not any(x in ts[end:] for x in ("match", "cascade", "restrict"))
    return dict(columns=columns, relation=target, referenced_columns=names(cols),
                match="s", on_update="a", on_delete="a", deferrable="deferrable" in ts[end:],
                initially_deferred="deferred" in ts[end:])


def read_column(ts):
    assert ts[1] in ("text", "integer", "bigint", "boolean", "bytea", "smallint", "jsonb")
    return dict(name=ts[0], type=ts[1], nullable=not ("not" in ts and "null" in ts) and "primary" not in ts,
                default=ts[ts.index("default") + 1] if "default" in ts else None,
                identity="", generated="", typmod=-1, dimensions=0)


def read_table(ts):
    relation, start = qualified(ts, 2)
    body, end = enclosed(ts, start)
    assert not ts[end:] or ts[end:] == [";"]
    table = dict(columns=[], checks=[], primary_key=[], unique=[], foreign_keys=[], extra_indexes=[])
    for part in split_top(body):
        if part[:2] == ["primary", "key"]:
            table["primary_key"] = names(enclosed(part, 2)[0])
        elif part[0] == "unique":
            table["unique"].append(names(enclosed(part, 1)[0]))
        elif part[:2] == ["foreign", "key"]:
            table["foreign_keys"].append(fk(part, names(enclosed(part, 2)[0])))
        elif part[0] != "check":
            table["columns"].append(read_column(part))
            if "primary" in part:
                table["primary_key"] = [part[0]]
            if "unique" in part:
                table["unique"].append([part[0]])
            if "references" in part:
                table["foreign_keys"].append(fk(part, [part[0]]))
        # CHECK words inside SQL string literals remain a single token.
        for i, t in enumerate(part):
            if t == "check":
                table["checks"].append(enclosed(part, i + 1)[0])
    for col in table["columns"]:
        if col["name"] in table["primary_key"]:
            col["nullable"] = False
    return relation, table


def read_policy(ts):
    relation, pos = qualified(ts, ts.index("on") + 1)
    command = ts[ts.index("for") + 1].upper()
    roles = ["$writer"] if "to" in ts and ts[ts.index("to") + 1] == "review_writer" else ["PUBLIC"]
    return relation, dict(name=ts[2], command=command, roles=roles, permissive=True,
                         using=expression_at(ts, "using"), check=expression_at(ts, "check"))


def read_grant(ts):
    end = ts.index("on")
    relation, pos = qualified(ts, end + 1)
    assert ts[pos:] == ["to", "review_writer"]
    table, update_columns = [], []
    for entry in split_top(ts[1:end]):
        if len(entry) > 1:
            assert entry[0] == "update"
            update_columns += names(enclosed(entry, 1)[0])
        else:
            table.append(entry[0].upper())
    return relation, table, update_columns


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def multiset(value):
    return Counter(map(canonical, value))


def derive(rows):
    tables, policies, grants, triggers, alterations = {}, {}, {}, [], []
    for origin, sql in rows:
        ts = tokens(sql)
        if ts[:2] == ["create", "table"]:
            relation, table = read_table(ts)
            assert relation not in tables
            tables[relation] = table
        elif ts[:2] == ["alter", "table"] and "add" in ts and "column" in ts:
            relation, pos = qualified(ts, 2)
            col_tokens = ts[ts.index("column") + 1:]
            tables[relation]["columns"].append(read_column(col_tokens))
            if "check" in col_tokens:
                tables[relation]["checks"].append(expression_at(col_tokens, "check"))
        elif ts[:3] == ["create", "unique", "index"]:
            relation, pos = qualified(ts, ts.index("on") + 1)
            cols, end = enclosed(ts, pos)
            assert ts[end] == "where"
            tables[relation]["extra_indexes"].append(dict(name=ts[3], unique=True, columns=names(cols), predicate=ts[end + 1:]))
        elif ts[:2] == ["create", "policy"]:
            relation, policy = read_policy(ts)
            policies.setdefault(relation, []).append(policy)
        elif ts[:2] == ["alter", "policy"]:
            relation, _ = qualified(ts, ts.index("on") + 1)
            alterations.append(relation)
        elif ts[:2] == ["grant", "select"] or (ts[:2] == ["grant", "insert"]) or ts[:2] == ["grant", "update"]:
            relation, table, update_columns = read_grant(ts)
            g = grants.setdefault(relation, dict(table=[], update_columns=[]))
            g["table"] += table
            g["update_columns"] += update_columns
        elif ts[:2] == ["create", "trigger"] or ts[:3] == ["create", "constraint", "trigger"]:
            constraint = ts[1] == "constraint"
            offset = 3 if constraint else 2
            name, timing = ts[offset:offset + 2]
            event_end = ts.index("on")
            events = [x.upper() for x in ts[offset + 2:event_end] if x != "or"]
            relation, _ = qualified(ts, event_end + 1)
            if relation not in NAMES:
                continue
            function, pos = qualified(ts, ts.index("function") + 1)
            assert ts[pos:] == ["(", ")"]
            triggers.append(dict(relation=relation, name=name, function=function + "()", timing=timing.upper(),
                                 events=events, constraint=constraint, deferrable="deferrable" in ts,
                                 initially_deferred="deferred" in ts))
    return dict(tables=tables, policies=policies, grants=grants, triggers=triggers, policy_alterations=alterations)


def manifest_subset(m):
    out = deepcopy(m)
    for r, table in out["relations"].items():
        table["checks"] = [tokens(x) for x in table["checks"]]
        for index in table["extra_indexes"]:
            index["predicate"] = tokens(index["predicate"])
    for policies in out["policies"].values():
        for p in policies:
            for key in ("using", "check"):
                p[key] = tokens(p[key]) if p[key] is not None else None
    return out


def compare_relations(derived, matrix):
    assert set(matrix["relations"]) == set(NAMES)
    for name in NAMES:
        actual = derived["tables"][name]
        expected = matrix["relations"][name]
        assert actual["columns"] == expected["columns"], (name, "ordered column mismatch")
        assert actual["primary_key"] == expected["primary_key"], (name, "PK mismatch")
        for key in ("checks", "unique", "foreign_keys", "extra_indexes"):
            assert multiset(actual[key]) == multiset(expected[key]), (name, key)


def compare_policies(derived, matrix):
    assert set(matrix["policies"]) == set(NAMES)
    for name in NAMES:
        assert multiset(derived["policies"][name]) == multiset(matrix["policies"][name]), (name, "policies")


def capture():
    command = ["elixir", "verification/hosted-browser-relation-admission-contract-review/capture_ordinary_source.exs"]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    (HERE / "source-capture.stdout").write_text(result.stdout)
    (HERE / "source-capture.stderr").write_text(result.stderr)
    (HERE / "source-capture-command.json").write_text(json.dumps(dict(argv=command, exit_code=result.returncode, scope="inert ordinary-source evaluation only"), indent=2) + "\n")
    assert result.returncode == 0, "ordinary inert source evaluation failed"
    rows, functions = [], {}
    for line in result.stdout.splitlines():
        kind, origin, encoded = line.split("\t")
        source = base64.b64decode(encoded, validate=True).decode()
        if kind == "sql":
            rows.append((origin, source))
        else:
            assert kind == "function_source"
            assert origin not in functions
            functions[origin] = source
    return rows, functions


ROWS, FUNCTIONS = capture()
D = derive(ROWS)
M = manifest_subset(json.loads((PRODUCER / "relation-matrix.json").read_text()))
DOC = (ROOT / "docs/hosted-browser-relation-admission-contract.md").read_text()


class IndependentContractReview(unittest.TestCase):
    def test_01_independent_exact_counts(self):
        observed = {}
        for name in NAMES:
            t = D["tables"][name]
            observed[name] = (len(t["columns"]), len(t["checks"]), bool(t["primary_key"]), len(t["unique"]),
                              len(t["foreign_keys"]), 1 + len(t["unique"]) + len(t["extra_indexes"]),
                              sum(x["relation"] == name for x in D["triggers"]), len(D["policies"][name]))
        self.assertEqual(observed, EXPECTED_COUNTS)
        self.assertEqual(tuple(map(sum, zip(*observed.values()))), (124, 80, 9, 4, 10, 14, 5, 32))

    def test_02_all_ordered_columns_defaults_nullability_types_and_checks(self):
        compare_relations(D, M)
        defaults = {(r, c["name"], c["type"], c["default"]) for r in NAMES for c in D["tables"][r]["columns"] if c["default"] is not None}
        self.assertEqual(defaults, {(B + "oidc_attempts", "ciphertext_version", "integer", "1"),
                                    (A + "profiles", "state_revision", "bigint", "1"),
                                    (A + "bindings", "revision", "bigint", "1")})

    def test_03_both_incoming_fks_and_full_boundary_counts(self):
        incoming = [dict(source_relation=r, **f) for r, t in D["tables"].items() if r not in NAMES
                    for f in t["foreign_keys"] if f["relation"] in NAMES]
        # Source/migration location records are provenance, not FK semantics.
        expected = [{k: v for k, v in x.items() if k not in ("source", "migration")}
                    for x in M["incoming_foreign_keys"]]
        self.assertEqual(multiset(incoming), multiset(expected))
        self.assertEqual(len(incoming), 2)
        self.assertEqual({f["source_relation"] for f in incoming}, {A + "memberships", "public.mixer_customer_idempotency"})
        self.assertTrue(all(f["columns"] == ["principal_id"] and f["relation"] == A + "principals"
                            and f["referenced_columns"] == ["id"] for f in incoming))
        groups = 10 + len(incoming)
        self.assertEqual(groups * 4 + len(D["triggers"]), 53)
        self.assertEqual(80 + 9 + 4 + groups + 4, 109)

    def test_04_all_writer_table_and_column_grants_exact(self):
        self.assertEqual(set(D["grants"]), set(NAMES))
        for name in NAMES:
            for kind in ("table", "update_columns"):
                self.assertEqual(Counter(D["grants"][name][kind]), Counter(M["writer_grants"][name][kind]))
            self.assertNotIn("UPDATE", D["grants"][name]["table"])
        self.assertEqual(M["lifecycle_direct_grants"], [])
        self.assertEqual(M["ordinary_browser_grants"], [])
        self.assertEqual(M["public_direct_grants"], [])
        self.assertEqual(M["ordinary_authz_grants"], ["SELECT"])
        self.assertIn("MAINTAIN", DOC)
        self.assertIn("grantor", DOC)
        self.assertIn("is_grantable", DOC)
        self.assertIn("has_any_column_privilege", (ROOT / "hosted/lib/mixer_hosted/authorization/postgres/session.ex").read_text())

    def test_05_complete_ordinary_public_and_writer_policy_sets(self):
        compare_policies(D, M)
        policies = [p for r in NAMES for p in D["policies"][r]]
        self.assertEqual(Counter(tuple(p["roles"]) for p in policies), {("PUBLIC",): 10, ("$writer",): 22})
        self.assertTrue(all(p["permissive"] for p in policies))
        self.assertEqual(set(D["policy_alterations"]), {A + x for x in ("memberships", "organizations", "projects")})
        self.assertFalse(set(NAMES) & set(D["policy_alterations"]))
        self.assertTrue(all(p["name"] != "directory_read" for p in policies))

    def test_06_all_five_user_triggers_and_exact_source_bindings(self):
        expected = [{k: v for k, v in t.items() if k != "source"} for t in M["user_triggers"]]
        self.assertEqual(multiset(D["triggers"]), multiset(expected))
        self.assertEqual(len(D["triggers"]), 5)
        self.assertEqual(sum(x["constraint"] for x in D["triggers"]), 4)
        bindings = json.loads((PRODUCER / "trigger-function-source-bindings.json").read_text())
        actual = {name: dict(bytes=len(body.encode()), sha256=hashlib.sha256(body.encode()).hexdigest()) for name, body in FUNCTIONS.items()}
        self.assertEqual(actual, bindings)

    def test_07_source_transcription_mutations_rejected_without_collapsing_duplicates(self):
        attacks = []
        for label, change in [
            ("nullable changed", lambda x: x["relations"][B+"sessions"]["columns"][0].update(nullable=True)),
            ("default added", lambda x: x["relations"][B+"session_vault"]["columns"][1].update(default="1")),
            ("type widened", lambda x: x["relations"][A+"profiles"]["columns"][1].update(type="bigint")),
            ("column extra", lambda x: x["relations"][A+"profiles"]["columns"].append(deepcopy(x["relations"][A+"profiles"]["columns"][0]))),
            ("CHECK missing", lambda x: x["relations"][B+"session_events"]["checks"].pop()),
            ("CHECK duplicate", lambda x: x["relations"][B+"oidc_attempts"]["checks"].append(deepcopy(x["relations"][B+"oidc_attempts"]["checks"][0]))),
            ("FK target changed", lambda x: x["relations"][B+"sessions"]["foreign_keys"][0].update(relation=A+"families")),
            ("FK duplicate", lambda x: x["relations"][B+"sessions"]["foreign_keys"].append(deepcopy(x["relations"][B+"sessions"]["foreign_keys"][0]))),
            ("index predicate widened", lambda x: x["relations"][B+"oidc_attempts"]["extra_indexes"][0].update(predicate=["true"])),
            ("unique duplicate", lambda x: x["relations"][A+"profiles"]["unique"].append(deepcopy(x["relations"][A+"profiles"]["unique"][0]))),
        ]:
            clone = deepcopy(M)
            change(clone)
            with self.subTest(label=label), self.assertRaises(AssertionError):
                compare_relations(D, clone)
            attacks.append(label)
        self.assertEqual(len(attacks), 10)

    def test_08_policy_mutations_rejected_with_null_false_public_distinction(self):
        changes = [
            lambda p: p.update(roles=["$writer"]),
            lambda p: p.update(permissive=False),
            lambda p: p.update(command="ALL"),
            lambda p: p.update(using=["true"]),
            lambda p: p.update(check=["false"]),
        ]
        for change in changes:
            clone = deepcopy(M)
            change(clone["policies"][A+"profiles"][0])
            with self.assertRaises(AssertionError):
                compare_policies(D, clone)
        clone = deepcopy(M)
        clone["policies"][A+"profiles"].append(deepcopy(clone["policies"][A+"profiles"][0]))
        with self.assertRaises(AssertionError):
            compare_policies(D, clone)

    def test_09_every_runtime_case_stays_pending(self):
        matrix = json.loads((PRODUCER / "runtime-adversity-matrix.json").read_text())
        cases = matrix if isinstance(matrix, list) else matrix["cases"]
        self.assertGreaterEqual(len(cases), 48)
        self.assertTrue(all(x["status"] == "pending_runtime" for x in cases))
        self.assertIn("not a runtime implementation", DOC)
        self.assertIn(":relation_surface_verified", DOC)
        self.assertIn("original_monotonic_deadline_ms", DOC)
        self.assertIn("separate clean PG16 and PG17 fixtures", DOC)

    def test_10_exact_source_bindings_still_current(self):
        bindings = json.loads((PRODUCER / "source-bindings.json").read_text())["inputs"]
        for path, digest in bindings.items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path)

    def test_11_four_ri_shapes_and_cross_endpoint_linkage_are_explicit(self):
        # Proposed topology only. The source specifies ordinary MATCH SIMPLE /
        # NO ACTION FKs; actual major-specific generated catalogs remain unrun.
        expected = [
            dict(function="pg_catalog.RI_FKey_check_ins", endpoint="referencing", timing="AFTER", events=["INSERT"]),
            dict(function="pg_catalog.RI_FKey_check_upd", endpoint="referencing", timing="AFTER", events=["UPDATE"]),
            dict(function="pg_catalog.RI_FKey_noaction_del", endpoint="referenced", timing="AFTER", events=["DELETE"]),
            dict(function="pg_catalog.RI_FKey_noaction_upd", endpoint="referenced", timing="AFTER", events=["UPDATE"]),
        ]
        self.assertEqual(multiset(M["ri_trigger_shapes"]), multiset(expected))
        for fragment in ("tgconstraint", "tgconstrrelid", "tgconstrindid", "opposite endpoint",
                         "session replication role", "nondeferrable/not-initially-deferred",
                         "empty arguments/filter/WHEN/transition tables", "no parent clone",
                         "each of twelve", "48 internal RI"):
            self.assertTrue(fragment.lower() in DOC.lower(), fragment)
        self.assertIn("complete multiset", DOC)
        self.assertIn("Never collapse", DOC)

    def test_12_all_nine_rls_forced_and_public_revoked_in_source(self):
        for name in NAMES:
            expected = [tokens(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY"),
                        tokens(f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY"),
                        tokens(f"REVOKE ALL ON {name} FROM PUBLIC")]
            actual = [tokens(sql) for _, sql in ROWS]
            for statement in expected:
                self.assertEqual(actual.count(statement), 1, (name, statement))
        self.assertEqual(M["relation_defaults"]["relkind"], "r")
        self.assertTrue(M["relation_defaults"]["rls"])
        self.assertTrue(M["relation_defaults"]["force_rls"])
        self.assertEqual(M["relation_defaults"]["owner"], "$relation_owner")

    def test_13_frozen_producer_packet_hashes_match_declared_handoff(self):
        receipt_bytes = (PRODUCER / "receipt.json").read_bytes()
        handoff = json.loads((HERE / "reviewed-producer-freeze.json").read_text())
        self.assertEqual(hashlib.sha256(receipt_bytes).hexdigest(),
                         handoff["receipt_sha256"])
        receipt = json.loads(receipt_bytes)
        for path, digest in receipt["artifact_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path)
        self.assertEqual(receipt["input_tree_sha256"], handoff["input_tree_sha256"])

    def test_14_retained_original_freeze_rejects_missing_idempotency_boundary(self):
        old = json.loads((HERE / "before-incoming-fk-correction-relation-matrix.json").read_text())
        incoming = [dict(source_relation=r, **f) for r, t in D["tables"].items() if r not in NAMES
                    for f in t["foreign_keys"] if f["relation"] in NAMES]
        old_boundary = [{k: v for k, v in f.items() if k != "source"} for f in old["incoming_foreign_keys"]]
        self.assertEqual(len(old_boundary), 1)
        self.assertNotEqual(multiset(old_boundary), multiset(incoming))
        missing = multiset(incoming) - multiset(old_boundary)
        self.assertEqual(sum(missing.values()), 1)
        self.assertEqual(json.loads(next(iter(missing)))["source_relation"], "public.mixer_customer_idempotency")

    def test_15_column_and_table_grants_are_distinct_exact_multisets(self):
        # Prove that table UPDATE, column duplication, or a wider exact update
        # column set cannot be mistaken for the accepted source transcription.
        for field, value in (("table", "UPDATE"), ("table", "DELETE"),
                             ("table", "MAINTAIN"), ("update_columns", "id"),
                             ("update_columns", "cookie_digest")):
            changed = deepcopy(M["writer_grants"])
            changed[B + "sessions"][field].append(value)
            self.assertNotEqual(Counter(changed[B + "sessions"][field]),
                                Counter(D["grants"][B + "sessions"][field]))

    def test_16_reviewed_migration_dependency_closure_includes_artifact_schema(self):
        closure = json.loads((HERE / "reviewed-migration-source-closure.json").read_text())
        paths = {x["path"] for x in closure["inputs"]}
        migrations = {str(x.relative_to(ROOT)) for x in (ROOT / "hosted/priv/repo/migrations").glob("*.exs")}
        self.assertEqual(len(migrations), 9)
        self.assertTrue(migrations <= paths)
        self.assertIn("hosted/lib/mixer_hosted/customer_artifacts/schema.ex", paths)
        self.assertIn("public.mixer_customer_idempotency", D["tables"])
        self.assertTrue(any(origin.endswith("20261025000005_add_customer_artifact_storage.exs") for origin, _ in ROWS))
        oban_files = [x["path"] for x in closure["inputs"] if x["path"].startswith("hosted/deps/oban/")]
        self.assertEqual(len(oban_files), 16)
        for path in oban_files:
            source = (ROOT / path).read_text()
            self.assertNotIn("mixer_authz_", source)
            self.assertNotIn("mixer_browser_", source)
            self.assertNotIn("references(", source)
            self.assertNotIn("REFERENCES", source)
        for row in closure["inputs"]:
            self.assertEqual(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(), row["sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
