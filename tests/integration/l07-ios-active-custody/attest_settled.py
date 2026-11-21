#!/usr/bin/env python3
"""Sign and attach a root-owned, settled v74 iOS Simulator build."""

import argparse
import base64
from contextlib import closing
import hashlib
from http.client import HTTPConnection
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import tarfile
from urllib.parse import parse_qsl, urlencode, urlsplit

from live import require

BASE = "44aecbeb6a82a4a93321cff6a8ab86c5aa421900"
REPO = Path(__file__).resolve().parents[3]
IDS = ("organization_id", "project_id", "application_id", "build_id", "platform")
PINS = ("source_sha256", "toolchain_lock_sha256", "build_definition_sha256")
WIRE = ("organizationId", "projectId", "applicationId", "buildId", "platform",
        "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256")
KINDS = ("unsigned_native_binary", "debug_symbols", "resource_inventory")
PROFILE = "mixer.native-build.ios-simulator.development.v2"
HEX = re.compile(r"[0-9a-f]{64}")
ARCHIVE_LIMIT = 256 << 20
INVENTORY_LIMIT = 8 << 20


def sha(data):
    return hashlib.sha256(data).hexdigest()


def private_path(path, mode=None):
    info = path.lstat()
    require(path.is_absolute() and path == path.resolve() and info.st_uid == os.getuid()
            and (mode is None or info.st_mode == (stat.S_IFREG | mode)),
            "expected a canonical, operator-owned input path")
    return info


def settlement(args):
    root = args.run_root
    require(private_path(root).st_mode == (stat.S_IFDIR | 0o700), "expected a private run root")
    require(not os.path.lexists(root / "HOLD.json"), "run root has unresolved custody")
    receipt = root / "settlement.json"
    private_path(receipt, 0o600)
    raw = receipt.read_bytes()
    require(sha(raw) == args.settlement_sha256, "settlement receipt digest differs")
    proof = json.loads(raw)
    require(proof["base"] == BASE and proof["xcodeInvocations"] == 1
            and proof["liveCustodyPending"] is False and not proof.get("custodyHold"),
            "expected a fresh v74 compile with closed custody")
    for name in ("processor", "worker"):
        closed = proof["commands"][name]
        require(closed["exit"] == 0 and closed["groupAbsent"] is True, f"{name} did not close")
    closure = proof["liveClosure"]
    require(closure["xcodeExit"] == 0 and HEX.fullmatch(closure["xcodeReceiptSHA256"]),
            "successful Xcode closure is missing")
    selected = proof["binding"]
    record, operation, ref, spec = (selected[k] for k in ("record_id", "operation_id", "ref", "spec"))
    require(re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", record)
            and HEX.fullmatch(operation), "invalid build record or worker operation")
    scope = {key: spec[key] for key in (*IDS, *PINS[1:])}
    scope["source_sha256"] = spec["source"]["sha256"]
    require(scope["platform"] == "ios" and all(HEX.fullmatch(scope[key]) for key in PINS)
            and all(re.fullmatch(r"[A-Za-z0-9._-]{1,128}", scope[key])
                    and scope[key] not in (".", "..") for key in IDS)
            and ref == {key: scope[key] for key in IDS} | {"attempt": 1, "fence": 1},
            "expected one exact first-attempt iOS selection")
    identity = ["mixer-build-operation-v1", record, *(scope[k] for k in IDS), 1, 1]
    require(operation == sha(json.dumps(identity, separators=(",", ":")).encode()),
            "worker operation differs from the stock dispatch identity")

    settled = proof["settled"]
    subjects = settled["artifacts"]
    require([item["kind"] for item in subjects] == list(KINDS), "expected three retained products")
    for subject in subjects:
        limit = INVENTORY_LIMIT if subject["kind"] == KINDS[2] else ARCHIVE_LIMIT
        require(set(subject) == {"kind", "sizeBytes", "sha256"} and HEX.fullmatch(subject["sha256"])
                and type(subject["sizeBytes"]) is int and 0 < subject["sizeBytes"] <= limit,
                "invalid retained product identity")
    start, completed = settled["journal"]
    require(0 < start["now_ms"] <= completed["now_ms"] <= selected["deadline_ms"]
            and start["event"] == {"type": "start", "ref": ref}
            and completed["event"] == {"type": "completed", "ref": ref, "result": {
                "outcome": "native_succeeded",
                "artifacts": [{"kind": a["kind"], "sha256": a["sha256"], "size_bytes": a["sizeBytes"]}
                              for a in subjects],
            }}, "journal did not settle the exact subjects")
    return proof, scope, record, operation, subjects


def admit_worker(root, proof, operation, subjects):
    ledger = root / "worker/operations.sqlite"
    require(stat.S_ISREG(private_path(ledger).st_mode), "invalid fresh worker ledger")
    with closing(sqlite3.connect(ledger.as_uri() + "?mode=ro", uri=True, timeout=1)) as database:
        database.execute("BEGIN")
        [(raw,)] = database.execute("SELECT value FROM operations WHERE id=?", (operation,)).fetchall()
        row = json.loads(raw)
    closure = row["closure"]
    selected = proof["binding"]
    compiler = [item for item in closure["commands"] if item["command"] == "/usr/bin/xcodebuild"]
    require(row["binding"] == {key: selected[key] for key in ("spec", "ref", "deadline_ms")}
            and row["status"] == "native_ready" and row["starts"] == 1 and not row.get("tombstone")
            and row["artifacts"] == subjects and row["manifest_sha256"] == proof["settled"]["manifestSHA256"]
            and closure["closed"] is True and closure["exit"] == 0
            and closure["cli_reaped"] is True and closure["cli_group_absent"] is True
            and len(compiler) == 1 and compiler[0]["stop_reason"] is None
            and compiler[0]["group_terminate_sent"] is False
            and compiler[0]["receipt_sha256"] == proof["liveClosure"]["xcodeReceiptSHA256"],
            "worker ledger differs from the closed compile")

    manifest = root / "worker" / operation / "native/native-build.json"
    require(stat.S_ISREG(private_path(manifest).st_mode), "invalid fresh native report")
    raw = manifest.read_bytes()
    require(sha(raw) == row["manifest_sha256"], "retained native report digest differs")
    report = json.loads(raw)
    binding, spec = report["binding"], selected["spec"]
    command = binding["command"]
    require(report["formatVersion"] == 2 and report["scope"] == "unsigned-simulator/local-development"
            and report["commandResult"]["exitCode"] == 0
            and binding["authoritativeSourceDigest"] == spec["source"]["sha256"]
            and binding["lockSHA256"] == spec["toolchain_lock_sha256"]
            and command[0] == "/usr/bin/xcodebuild" and command[-1] == "build"
            and command[command.index("-destination") + 1] == "generic/platform=iOS Simulator"
            and command[command.index("-sdk") + 1] == "iphonesimulator"
            and "CODE_SIGNING_ALLOWED=NO" in command, "expected an unsigned generic Simulator compile")


def inspect_postgres(args, record):
    # record has already been restricted to the canonical UUID grammar.
    statement = f"""
    SELECT json_build_object(
      'dataDirectory', current_setting('data_directory'),
      'scope', json_build_array(b.organization_id,b.project_id,b.application_id,b.build_id,b.platform),
      'revision', b.revision, 'journal', b.journal,
      'reservation', json_build_array(r.attempt,r.worker_fence,r.held,r.terminal_event_id),
      'leaseClosed', l.owner_id IS NULL AND l.expires_at IS NULL,
      'attachments', (SELECT coalesce(json_agg(json_build_array(
        a.journal_revision,a.attempt,a.worker_operation_id,a.native_binding_sha256,
        a.signer_key_sha256,a.signing_origin,encode(a.envelope,'hex')
      )), '[]'::json) FROM public.mixer_native_development_attestations a
        WHERE a.build_record_id=b.id))
    FROM public.mixer_builds b
    JOIN public.mixer_build_reservations r ON r.build_record_id=b.id
    JOIN public.mixer_build_coordinator_leases l ON l.build_record_id=b.id
    WHERE b.id='{record}'::uuid
    """
    env = {"PGCONNECT_TIMEOUT": "3",
           "PGOPTIONS": "-c default_transaction_read_only=on -c statement_timeout=3000"}
    output = subprocess.check_output(
        [args.psql, "-XqAtw", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(args.pg_port),
         "-U", args.pg_user, "-d", args.pg_database, "-c", statement],
        env=env, stdin=subprocess.DEVNULL, timeout=8,
    )
    return json.loads(output)


def get(port, path, token, media, limit):
    with closing(HTTPConnection("127.0.0.1", port, timeout=10)) as connection:
        connection.request("GET", path, headers={"Cookie": "__Host-mixer-session=" + token})
        with connection.getresponse() as response:
            require(response.status == 200 and response.getheader("Content-Type") == media
                    and response.getheader("Cache-Control") == "no-store"
                    and response.getheader("Content-Encoding") is None,
                    "authorized completion or download refused")
            return response.read(limit + 1)


def observe_products(port, query, scope, session, operation, subjects):
    path = "/console-api/v1/build-attestation-completion?" + query
    raw = get(port, path, session, "application/json; charset=utf-8", 16384)
    require(len(raw) <= 16384, "oversized completion detail")
    detail = json.loads(raw)["build"]
    selection = dict(zip(WIRE, (scope[k] for k in (*IDS, *PINS)), strict=True))
    require({k: detail[k] for k in WIRE} == selection
            and (detail["state"], detail["revision"], detail["attempt"], detail["workerOperationId"])
            == ("native_succeeded", 2, 1, operation) and detail["workerCompletionPending"] is False,
            "authorized completion differs from the settled operation")
    for descriptor, subject in zip(detail["artifacts"], subjects, strict=True):
        route = urlsplit(descriptor["downloadPath"])
        expected_path = "/console-api/v1/build-artifacts/" + subject["kind"]
        require({k: descriptor[k] for k in subject} == subject
                and descriptor["downloadPath"] == expected_path + "?" + route.query
                and sorted(parse_qsl(route.query, strict_parsing=True)) == sorted(scope.items()),
                "authorized descriptor differs from the settled product")
        body = get(port, expected_path + "?" + query, session, "application/octet-stream",
                   subject["sizeBytes"])
        require(len(body) == subject["sizeBytes"] and sha(body) == subject["sha256"],
                "authorized download differs from the settled product")
    inventory = json.loads(body)
    binding = inventory["bindingSHA256"]
    require(inventory["version"] == 1 and inventory["kind"] == KINDS[2] and HEX.fullmatch(binding)
            and inventory["parentApp"] == subjects[0]
            and inventory["parentSymbols"] == subjects[1], "resource inventory binding differs")
    return selection, binding


def build_signer(work):
    paths = ("services/go.mod", "services/go.sum", "services/cmd/mixer-native-attest")
    archive = subprocess.check_output(
        ["git", "--no-lazy-fetch", "--no-replace-objects", "archive", BASE, *paths],
        cwd=REPO, stdin=subprocess.DEVNULL, timeout=10,
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(work, filter="data")
    for name in ("home", "cache", "modules", "tmp", "state"):
        (work / name).mkdir(mode=0o700)
    env = dict(PATH=os.environ["PATH"], HOME=str(work / "home"), CGO_ENABLED="1", CC="/usr/bin/clang",
               GOTOOLCHAIN="local", GOENV="off", GOWORK="off", GOPROXY="off", GOSUMDB="off",
               GOTELEMETRY="off", GOCACHE=str(work / "cache"), GOMODCACHE=str(work / "modules"),
               GOTMPDIR=str(work / "tmp"), TMPDIR=str(work / "tmp"))
    tool = work / "mixer-native-attest"
    version = subprocess.check_output(["go", "version"], env=env, text=True).strip()
    subprocess.run(["go", "-C", work / "services", "build", "-mod=readonly", "-buildvcs=false",
                    "-trimpath", "-o", tool, "./cmd/mixer-native-attest"],
                   check=True, env=env, stdin=subprocess.DEVNULL)
    return tool, version


def prove(args):
    proof, scope, record, operation, subjects = settlement(args)
    root = args.run_root
    work = root / "attestation"
    require(not os.path.lexists(work), "expected fresh attestation state")
    admit_worker(root, proof, operation, subjects)
    before = inspect_postgres(args, record)
    journal = before["journal"]
    require(before["dataDirectory"] == str(root / "pg")
            and before["scope"] == [scope[k] for k in IDS]
            and before["revision"] == 2 and journal["events"] == proof["settled"]["journal"]
            and journal["creation"]["spec"] == proof["binding"]["spec"]
            and before["reservation"] == [1, 1, False, journal["events"][-1]["id"]]
            and before["leaseClosed"] is True and before["attachments"] == [],
            "PostgreSQL does not show the same unattested settlement")

    for path in (args.session, args.bearer, args.private_key, args.public_key):
        private_path(path, 0o600)
        require(not path.is_relative_to(root), "keep credentials and keys outside the build root")
    session = args.session.read_text().removesuffix("\n")
    bearer = args.bearer.read_text().removesuffix("\n")
    require(re.fullmatch(r"[A-Za-z0-9_-]{43}", session)
            and base64.urlsafe_b64encode(base64.urlsafe_b64decode(session + "=")).decode() == session + "="
            and re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", bearer) and len(bearer) <= 4089,
            "expected fresh synthetic session and bearer tokens")
    pem = args.public_key.read_bytes().splitlines()
    require(len(pem) == 3 and pem[0] == b"-----BEGIN PUBLIC KEY-----"
            and pem[2] == b"-----END PUBLIC KEY-----", "expected a public SPKI PEM")
    spki = base64.b64decode(pem[1], validate=True)
    key_id = sha(spki)
    require(len(spki) == 44 and spki.startswith(bytes.fromhex("302a300506032b6570032100"))
            and key_id == args.enrolled_spki_sha256, "public key differs from the enrolled Ed25519 key")

    query = urlencode({key: scope[key] for key in (*IDS, *PINS)})
    origin = f"http://127.0.0.1:{args.api_port}"
    selection, binding = observe_products(args.api_port, query, scope, session, operation, subjects)
    work.mkdir(mode=0o700)
    tool, go_version = build_signer(work)
    state = work / "state"

    def call(action, key, token):
        return subprocess.check_output(
            [tool, action, "-origin", origin, "-selection", query, "-state", state, "-key", key],
            input=(token + "\n").encode(), env={"PATH": "/usr/bin:/bin"}, timeout=135,
        ).decode().strip()

    filename = sha("\0".join(scope[k] for k in (*IDS[:3], "platform", "build_id")).encode()) + ".json"
    require(call("sign", args.private_key, session) == filename, "unexpected signed envelope name")
    envelope = (state / filename).read_bytes()
    statement = json.loads(envelope)["statement"]
    require(statement == dict(profile=PROFILE, origin=origin, keyId=key_id, selection=selection,
                              provenance=dict(journalRevision=2, attempt=1, nativeBindingSha256=binding,
                                              workerOperationId=operation),
                              subjects=subjects), "signed statement differs from the admitted completion")
    stored = before | {"attachments": [[2, 1, operation, binding, key_id, origin, envelope.hex()]]}
    for status in ("attached", "duplicate"):
        require(call("attach", args.public_key, bearer) == status, f"expected {status} from ordinary Phoenix")
        require(inspect_postgres(args, record) == stored and (state / filename).read_bytes() == envelope,
                "attachment bytes, cardinality, or settled build changed")
    return dict(base=BASE, go=go_version, signerSHA256=sha(tool.read_bytes()), origin=origin,
                settlementSHA256=args.settlement_sha256, recordId=record, workerOperationId=operation,
                journalRevision=2, attempt=1, subjects=subjects, signerKeySHA256=key_id,
                nativeBindingSHA256=binding, attachmentHTTP=[201, 200], persistedRows=1,
                byteExact=True, journalUnchanged=True, envelopeSHA256=sha(envelope),
                envelopeSizeBytes=len(envelope), buildPOSTs=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run-root", "session", "bearer", "private-key", "public-key"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("settlement-sha256", "enrolled-spki-sha256"):
        parser.add_argument("--" + name, required=True)
    for name in ("api-port", "pg-port"):
        parser.add_argument("--" + name, required=True, type=int)
    parser.add_argument("--pg-user", default="fixture_admin")
    parser.add_argument("--pg-database", default="browser_ordinary_installation_r1422")
    parser.add_argument("--psql", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin/psql"))
    args = parser.parse_args()
    if (not all(1024 <= port <= 65535 for port in (args.api_port, args.pg_port))
            or args.api_port == args.pg_port or not args.psql.is_absolute()
            or not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value)
                       for value in (args.pg_user, args.pg_database))
            or not all(HEX.fullmatch(value) for value in (args.settlement_sha256, args.enrolled_spki_sha256))):
        parser.error("expected distinct loopback fixture ports, a psql path, fixture identifiers and SHA-256 pins")
    os.umask(0o077)
    print(json.dumps(prove(args), indent=2))


if __name__ == "__main__":
    main()
