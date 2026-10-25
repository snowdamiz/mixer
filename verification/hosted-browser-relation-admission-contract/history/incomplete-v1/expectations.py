"""Hand-transcribed expectations from accepted source, never from a database.

This is documentation/completeness data, not a production catalog comparator.
SQL strings are original-source spellings; PG16/17 deparse forms remain pending.
"""

MAX = "9007199254740991"
B = "public.mixer_browser_"
A = "public.mixer_authz_"
S = "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex"
M3 = "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs"
M4 = "hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs"
M6 = "hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs"
M7 = "hosted/priv/repo/migrations/20261025000007_add_browser_sessions.exs"
SESSION = "hosted/lib/mixer_hosted/authorization/postgres/session.ex"


def columns(spec):
    """name:type; ? nullable; =1 the only installed default."""
    out = []
    for item in spec.split():
        name, kind = item.split(":")
        default = "1" if kind.endswith("=1") else None
        kind = kind.removesuffix("=1")
        nullable = kind.endswith("?")
        kind = kind.removesuffix("?")
        out.append(dict(name=name, type=kind, nullable=nullable, default=default,
                        identity="", generated="", typmod=-1, dimensions=0))
    return out


def fk(keys, target, referenced):
    return dict(columns=keys.split(","), relation=target,
                referenced_columns=referenced.split(","), match="s",
                on_update="a", on_delete="a", deferrable=False, initially_deferred=False)


def table(spec, checks, pk, unique=(), fks=(), indexes=(), sources=()):
    return dict(columns=columns(spec), checks=checks, primary_key=pk.split(","),
                unique=[x.split(",") for x in unique], foreign_keys=list(fks),
                extra_indexes=list(indexes), sources=list(sources))


TABLES = {
    B + "sessions": table(
        "id:bytea cookie_digest:bytea status:text epoch:bigint revision:bigint generation:text "
        "csrf_digest:bytea created_at:bigint last_seen_at:bigint absolute_expires_at:bigint "
        "idle_expires_at:bigint expected_profile_id:text expected_profile_version:integer "
        "initial_config_digest:bytea config_digest:bytea profile_id:text? profile_version:integer? "
        "principal_id:text? family_id:text? credential_ref:text? credential_revision:bigint? audit_sequence:bigint",
        ["octet_length(id)=16", "octet_length(cookie_digest)=32",
         "status IN('preauth','active','revoked','expired')", f"epoch BETWEEN 1 AND {MAX}",
         f"revision BETWEEN 1 AND {MAX}", "generation ~ '^[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$'",
         "octet_length(csrf_digest)=32", f"created_at BETWEEN 0 AND {MAX}",
         "last_seen_at >= created_at", f"absolute_expires_at > created_at AND absolute_expires_at <={MAX}",
         "idle_expires_at > created_at AND idle_expires_at <=absolute_expires_at",
         "octet_length(expected_profile_id) BETWEEN 1 AND 128", "expected_profile_version > 0",
         "octet_length(initial_config_digest)=32", "octet_length(config_digest)=32",
         f"audit_sequence BETWEEN 1 AND {MAX}",
         "(profile_id IS NULL AND profile_version IS NULL AND principal_id IS NULL AND family_id IS NULL AND credential_ref IS NULL AND credential_revision IS NULL AND status<>'active') OR "
         f"(profile_id IS NOT NULL AND profile_version IS NOT NULL AND principal_id IS NOT NULL AND family_id IS NOT NULL AND credential_ref IS NOT NULL AND credential_revision IS NOT NULL AND credential_revision BETWEEN 1 AND {MAX} AND status<>'preauth')"],
        "id", ["cookie_digest"],
        [fk("profile_id,profile_version,credential_ref", A+"credentials", "profile_id,profile_version,reference"),
         fk("family_id,profile_id,profile_version,principal_id", A+"families", "id,profile_id,profile_version,principal_id")],
        sources=[dict(path=S, start=302, end=324)]),
    B + "session_vault": table(
        "browser_id:bytea epoch:bigint session_revision:bigint vault_generation:bigint ciphertext_version:integer "
        "envelope_kind:text key_id:text? iv:bytea? tag:bytea? ciphertext:bytea?",
        [f"epoch BETWEEN 1 AND {MAX}", f"session_revision BETWEEN 1 AND {MAX}",
         f"vault_generation BETWEEN 1 AND {MAX}", "ciphertext_version=1", "envelope_kind IN('preauth','active','erased')",
         "(envelope_kind='erased' AND key_id IS NULL AND iv IS NULL AND tag IS NULL AND ciphertext IS NULL) OR "
         "(envelope_kind IN('preauth','active') AND key_id IS NOT NULL AND key_id ~ '^[A-Za-z0-9._-]{1,128}$' AND iv IS NOT NULL AND octet_length(iv)=12 AND tag IS NOT NULL AND octet_length(tag)=16 AND ciphertext IS NOT NULL AND octet_length(ciphertext) BETWEEN 1 AND 8192)"],
        "browser_id", fks=[fk("browser_id", B+"sessions", "id")],
        sources=[dict(path=S, start=327, end=337)]),
    B + "oidc_attempts": table(
        "state_digest:bytea browser_id:bytea browser_epoch:bigint browser_revision:bigint cookie_digest:bytea "
        "generation:text config_digest:bytea profile_id:text profile_version:integer issuer:text client_id:text "
        "redirect_uri:text return_route:text nonce_digest:bytea created_at:bigint expires_at:bigint status:text "
        "claim_digest:bytea? claimed_at:bigint? claim_expires_at:bigint? completion_reason:text? "
        "ciphertext_version:integer=1 key_id:text? iv:bytea? tag:bytea? ciphertext:bytea?",
        ["octet_length(state_digest)=32", f"browser_epoch BETWEEN 1 AND {MAX}", f"browser_revision BETWEEN 1 AND {MAX}",
         "octet_length(cookie_digest)=32", "generation ~ '^[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$'",
         "octet_length(config_digest)=32", "octet_length(profile_id) BETWEEN 1 AND 128", "profile_version > 0",
         "octet_length(issuer) BETWEEN 1 AND 2048", "octet_length(client_id) BETWEEN 1 AND 256",
         "octet_length(redirect_uri) BETWEEN 1 AND 2048", "return_route='workspace'", "octet_length(nonce_digest)=32",
         f"created_at BETWEEN 0 AND {MAX}", f"expires_at > created_at AND expires_at<=created_at+300 AND expires_at<={MAX}",
         "status IN('pending','claimed','provider_rejected','completed','failed','superseded')", "octet_length(claim_digest)=32",
         "completion_reason IN('provider_rejected','exchange_failed','oidc_failed','identity_failed','session_failed','completed','superseded','expired','logout')",
         "ciphertext_version=1",
         "(status='pending' AND claim_digest IS NULL AND claimed_at IS NULL AND claim_expires_at IS NULL AND completion_reason IS NULL AND key_id IS NOT NULL AND key_id ~ '^[A-Za-z0-9._-]{1,128}$' AND iv IS NOT NULL AND octet_length(iv)=12 AND tag IS NOT NULL AND octet_length(tag)=16 AND ciphertext IS NOT NULL AND octet_length(ciphertext) BETWEEN 1 AND 8192) OR "
         "(status<>'pending' AND key_id IS NULL AND iv IS NULL AND tag IS NULL AND ciphertext IS NULL AND "
         "((status='claimed' AND completion_reason IS NULL AND claim_digest IS NOT NULL AND claimed_at IS NOT NULL AND claim_expires_at IS NOT NULL AND claimed_at>=created_at AND claim_expires_at>claimed_at AND claim_expires_at<=expires_at) OR "
         "(completion_reason IS NOT NULL AND ((status='provider_rejected' AND completion_reason='provider_rejected') OR (status='completed' AND completion_reason='completed' AND claim_digest IS NOT NULL) OR (status='failed' AND completion_reason IN('exchange_failed','oidc_failed','identity_failed','session_failed') AND claim_digest IS NOT NULL) OR (status='superseded' AND completion_reason IN('superseded','expired','logout'))))))"],
        "state_digest", fks=[fk("browser_id", B+"sessions", "id")],
        indexes=[dict(name="mixer_browser_one_attempt", unique=True, columns=["browser_id", "browser_epoch"],
                      predicate="status IN('pending','claimed')")],
        sources=[dict(path=S, start=340, end=369)]),
    B + "session_events": table(
        "browser_id:bytea sequence:bigint audit_schema:integer operation:text outcome:text request_id:text recorded_at:bigint "
        "old_revision:bigint? new_revision:bigint old_epoch:bigint? new_epoch:bigint old_status:text? new_status:text "
        "config_digest:bytea attempt_state_digest:bytea? profile_id:text? profile_version:integer? principal_id:text? family_id:text? "
        "issuer_hash:bytea? subject_hash:bytea? client_hash:bytea? credential_hash:bytea? profile_revision:bigint? "
        "binding_revision:bigint? principal_revision:bigint? family_revision:bigint? credential_revision:bigint? token_issued_at:bigint? token_expires_at:bigint?",
        [f"sequence BETWEEN 1 AND {MAX}", "audit_schema=1",
         "operation IN('bootstrap','begin','claim','provider_reject','fail_claim','activate','replace','logout','expire')",
         "outcome IN('created','pending','claimed','provider_rejected','failed','active','revoked','expired')",
         "request_id ~ '^[0-9a-f]{32}$'", f"recorded_at BETWEEN 0 AND {MAX}",
         f"new_revision BETWEEN 1 AND {MAX}", f"new_epoch BETWEEN 1 AND {MAX}",
         "new_status IN('preauth','active','revoked','expired')", "octet_length(config_digest)=32",
         "octet_length(attempt_state_digest)=32", "octet_length(issuer_hash)=32", "octet_length(subject_hash)=32",
         "octet_length(client_hash)=32", "octet_length(credential_hash)=32",
         "(sequence=1 AND operation='bootstrap' AND old_revision IS NULL AND old_epoch IS NULL AND old_status IS NULL AND new_revision=1 AND new_epoch=1 AND new_status='preauth' AND outcome='created') OR "
         f"(sequence>1 AND old_revision IS NOT NULL AND old_revision BETWEEN 1 AND {MAX} AND old_epoch IS NOT NULL AND old_epoch BETWEEN 1 AND {MAX} AND old_status IS NOT NULL AND old_status IN('preauth','active') AND "
         "((operation='begin' AND outcome='pending' AND new_status=old_status AND new_revision=old_revision+1 AND new_epoch=old_epoch+1) OR "
         "(operation='claim' AND outcome='claimed' AND new_status=old_status AND new_revision=old_revision AND new_epoch=old_epoch) OR "
         "(operation='provider_reject' AND outcome='provider_rejected' AND new_status=old_status AND new_revision=old_revision AND new_epoch=old_epoch) OR "
         "(operation='fail_claim' AND outcome='failed' AND new_status=old_status AND new_revision=old_revision AND new_epoch=old_epoch) OR "
         "(operation='activate' AND outcome='active' AND old_status='preauth' AND new_status='active' AND new_revision=old_revision+1 AND new_epoch=old_epoch+1) OR "
         "(operation='replace' AND outcome='active' AND old_status='active' AND new_status='active' AND new_revision=old_revision+1 AND new_epoch=old_epoch+1) OR "
         "(operation='logout' AND outcome='revoked' AND new_status='revoked' AND new_revision=old_revision+1 AND new_epoch=old_epoch+1) OR "
         "(operation='expire' AND outcome='expired' AND new_status='expired' AND new_revision=old_revision+1 AND new_epoch=old_epoch+1)))",
         "(operation IN('activate','replace') AND token_issued_at IS NOT NULL AND token_expires_at>token_issued_at AND issuer_hash IS NOT NULL AND subject_hash IS NOT NULL AND client_hash IS NOT NULL AND credential_hash IS NOT NULL) OR "
         "(operation NOT IN('activate','replace') AND token_issued_at IS NULL AND token_expires_at IS NULL AND issuer_hash IS NULL AND subject_hash IS NULL AND client_hash IS NULL AND credential_hash IS NULL)"],
        "browser_id,sequence", fks=[fk("browser_id", B+"sessions", "id")],
        sources=[dict(path=S, start=371, end=400)]),
    A + "profiles": table(
        "id:text version:integer issuer:text client_id:text identity_class:text active:boolean state_revision:bigint=1",
        ["octet_length(id) BETWEEN 1 AND 128", "version > 0", "octet_length(issuer) BETWEEN 1 AND 2048",
         "octet_length(client_id) BETWEEN 1 AND 256", "identity_class IN ('human','service')", f"state_revision BETWEEN 1 AND {MAX}"],
        "id,version", ["id,version,identity_class"],
        sources=[dict(path=M3, start=8, end=16), dict(path=M4, start=8, end=10)]),
    A + "principals": table(
        "id:text identity_class:text active:boolean not_before:bigint revision:bigint",
        ["octet_length(id) BETWEEN 1 AND 128", "identity_class IN ('human','service')",
         f"not_before BETWEEN 0 AND {MAX}", f"revision BETWEEN 1 AND {MAX}"],
        "id", ["id,identity_class"], sources=[dict(path=M3, start=17, end=24)]),
    A + "bindings": table(
        "profile_id:text profile_version:integer subject:text identity_class:text principal_id:text active:boolean revision:bigint=1",
        ["octet_length(subject) BETWEEN 1 AND 256", f"revision BETWEEN 1 AND {MAX}"],
        "profile_id,profile_version,subject", fks=[
            fk("profile_id,profile_version,identity_class", A+"profiles", "id,version,identity_class"),
            fk("principal_id,identity_class", A+"principals", "id,identity_class")],
        sources=[dict(path=M3, start=25, end=35), dict(path=M4, start=14, end=16)]),
    A + "families": table(
        "id:text profile_id:text profile_version:integer principal_id:text active:boolean not_before:bigint expires_at:bigint? revision:bigint",
        ["octet_length(id) BETWEEN 1 AND 128", f"not_before BETWEEN 0 AND {MAX}",
         f"expires_at BETWEEN 0 AND {MAX} AND expires_at > not_before", f"revision BETWEEN 1 AND {MAX}"],
        "id", ["id,profile_id,profile_version,principal_id"],
        [fk("principal_id", A+"principals", "id"), fk("profile_id,profile_version", A+"profiles", "id,version")],
        sources=[dict(path=M3, start=36, end=46)]),
    A + "credentials": table(
        "profile_id:text profile_version:integer reference:text principal_id:text family_id:text active:boolean "
        "not_before:bigint expires_at:bigint? revision:bigint",
        ["octet_length(reference) BETWEEN 1 AND 256", f"not_before BETWEEN 0 AND {MAX}",
         f"expires_at BETWEEN 0 AND {MAX} AND expires_at > not_before", f"revision BETWEEN 1 AND {MAX}"],
        "profile_id,profile_version,reference", fks=[
            fk("family_id,profile_id,profile_version,principal_id", A+"families", "id,profile_id,profile_version,principal_id")],
        sources=[dict(path=M3, start=47, end=58)])
}

# Every privilege set is exact, with no grant option. Column UPDATE is distinct
# from table UPDATE. Table SELECT/INSERT imply effective per-column rights.
WRITER = {
    B+"sessions": ("SELECT INSERT", "cookie_digest status epoch revision generation csrf_digest last_seen_at absolute_expires_at idle_expires_at profile_id profile_version principal_id family_id credential_ref credential_revision audit_sequence"),
    B+"session_vault": ("SELECT INSERT", "epoch session_revision vault_generation ciphertext_version envelope_kind key_id iv tag ciphertext"),
    B+"oidc_attempts": ("SELECT INSERT", "status claim_digest claimed_at claim_expires_at completion_reason key_id iv tag ciphertext"),
    B+"session_events": ("SELECT INSERT", ""),
    A+"profiles": ("SELECT", "state_revision"), A+"principals": ("SELECT", "revision"),
    A+"bindings": ("SELECT", ""), A+"families": ("SELECT INSERT", "active revision"),
    A+"credentials": ("SELECT INSERT", "active revision")
}

LINKED = "EXISTS (SELECT 1 FROM public.mixer_authz_bindings b WHERE b.principal_id = current_setting('mixer.authz.principal_id', true))"
ACTOR = "principal_id = current_setting('mixer.authz.principal_id', true) AND (" + LINKED + ")"
ORDINARY_PREDICATES = {
    A+"profiles": "id = current_setting('mixer.authz.profile_id', true) AND version::text = current_setting('mixer.authz.profile_version', true) AND issuer = current_setting('mixer.authz.issuer', true) AND client_id = current_setting('mixer.authz.client_id', true) AND identity_class = current_setting('mixer.authz.identity_class', true)",
    A+"bindings": "profile_id = current_setting('mixer.authz.profile_id', true) AND profile_version::text = current_setting('mixer.authz.profile_version', true) AND subject = current_setting('mixer.authz.subject', true) AND identity_class = current_setting('mixer.authz.identity_class', true) AND EXISTS (SELECT 1 FROM public.mixer_authz_profiles p WHERE p.id = profile_id AND p.version = profile_version)",
    A+"principals": "id = current_setting('mixer.authz.principal_id', true) AND ("+LINKED+")",
    A+"families": ACTOR+" AND profile_id = current_setting('mixer.authz.profile_id', true) AND profile_version::text = current_setting('mixer.authz.profile_version', true) AND id = current_setting('mixer.authz.family_id', true)",
    A+"credentials": ACTOR+" AND profile_id = current_setting('mixer.authz.profile_id', true) AND profile_version::text = current_setting('mixer.authz.profile_version', true) AND reference = current_setting('mixer.authz.credential_ref', true)"
}


def policy(name, command, roles, using, check):
    return dict(name=name, command=command, roles=roles, permissive=True, using=using, check=check)


POLICIES = {}
for rel in TABLES:
    rows = []
    if rel in ORDINARY_PREDICATES:
        p = ORDINARY_PREDICATES[rel]
        rows += [policy("scoped_read", "SELECT", ["PUBLIC"], p, None),
                 policy("scoped_lock", "UPDATE", ["PUBLIC"], p, "false")]
    rows += [policy("mixer_browser_read", "SELECT", ["$writer"], "true", None)]
    if "INSERT" in WRITER[rel][0]:
        rows += [policy("mixer_browser_insert", "INSERT", ["$writer"], None, "true")]
    if WRITER[rel][1]:
        lock = rel in (A+"profiles", A+"principals")
        rows += [policy("mixer_browser_lock" if lock else "mixer_browser_update", "UPDATE", ["$writer"], "true", "false" if lock else "true")]
    POLICIES[rel] = rows

TRIGGERS = [
    dict(relation=B+"sessions", name="mixer_browser_integrity", function="public.mixer_browser_integrity()", timing="AFTER", events=["INSERT", "UPDATE"], constraint=True, deferrable=True, initially_deferred=True, source=[487,527]),
    dict(relation=B+"session_vault", name="mixer_browser_integrity", function="public.mixer_browser_integrity()", timing="AFTER", events=["INSERT", "UPDATE"], constraint=True, deferrable=True, initially_deferred=True, source=[487,527]),
    dict(relation=B+"oidc_attempts", name="mixer_browser_integrity", function="public.mixer_browser_attempt_integrity()", timing="AFTER", events=["INSERT", "UPDATE"], constraint=True, deferrable=True, initially_deferred=True, source=[528,554]),
    dict(relation=B+"session_events", name="mixer_browser_integrity", function="public.mixer_browser_event_integrity()", timing="AFTER", events=["INSERT"], constraint=True, deferrable=True, initially_deferred=True, source=[558,570]),
    dict(relation=B+"session_events", name="mixer_browser_immutable", function="public.mixer_browser_event_immutable()", timing="BEFORE", events=["UPDATE", "DELETE"], constraint=False, deferrable=False, initially_deferred=False, source=[555,557])
]

# Incoming RI enforcement crosses the exact-nine boundary once. This is a
# boundary constraint/trigger check, not complete memberships relation admission.
INCOMING_FOREIGN_KEYS = [dict(source_relation=A+"memberships", **fk("principal_id", A+"principals", "id"),
                              source=dict(path=M3, start=91, end=104))]

SURFACE_DEFAULTS = dict(schema="public", relkind="r", relpersistence="p", rls=True,
                        force_rls=True, owner="$relation_owner", partition=False,
                        inheritance=False, typed_table=False, replica_identity="d",
                        rules=[], user_trigger_enabled="O", user_trigger_row=True,
                        user_trigger_arguments=[], user_trigger_when=None,
                        user_trigger_transition_tables=None)

CONSTRAINT_DEFAULTS = dict(validated=True, local=True, inheritance_count=0,
                           parent_constraint=None, domain=None,
                           check_no_inherit=False, key_fk_trigger_no_inherit=True,
                           ordinary_deferrable=False, ordinary_initially_deferred=False,
                           exclusion_operators=None, fk_delete_set_columns=None)
INDEX_DEFAULTS = dict(access_method="pg_catalog.btree", unique=True,
                      valid=True, ready=True, live=True, immediate=True,
                      exclusion=False, nulls_not_distinct=False,
                      include=[], expressions=None, direction="ASC", null_order="LAST",
                      owner="$relation_owner", partition=False, inheritance=False,
                      opclass_by_type={"bytea":"pg_catalog.bytea_ops", "text":"pg_catalog.text_ops",
                                       "integer":"pg_catalog.int4_ops", "bigint":"pg_catalog.int8_ops"},
                      text_collation="pg_catalog.default", other_collation=None)
RI_TRIGGER_SHAPES = [
    dict(function="pg_catalog.RI_FKey_check_ins", endpoint="referencing", timing="AFTER", events=["INSERT"]),
    dict(function="pg_catalog.RI_FKey_check_upd", endpoint="referencing", timing="AFTER", events=["UPDATE"]),
    dict(function="pg_catalog.RI_FKey_noaction_del", endpoint="referenced", timing="AFTER", events=["DELETE"]),
    dict(function="pg_catalog.RI_FKey_noaction_upd", endpoint="referenced", timing="AFTER", events=["UPDATE"])
]


def manifest():
    return dict(version=1, scope="source_contract_only", relation_defaults=SURFACE_DEFAULTS,
                constraint_defaults=CONSTRAINT_DEFAULTS, index_defaults=INDEX_DEFAULTS,
                ri_trigger_shapes=RI_TRIGGER_SHAPES,
                relations=TABLES, writer_grants={r: dict(table=p.split(), update_columns=c.split()) for r,(p,c) in WRITER.items()},
                policies=POLICIES, user_triggers=TRIGGERS, incoming_foreign_keys=INCOMING_FOREIGN_KEYS,
                lifecycle_direct_grants=[], ordinary_browser_grants=[],
                ordinary_authz_grants=["SELECT"], public_direct_grants=[])
