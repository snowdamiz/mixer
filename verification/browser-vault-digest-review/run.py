#!/usr/bin/env python3
"""Bounded independent review. Compile only seven explicit ordinary modules."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = [
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/identity/manifest.ex",
    "hosted/lib/mixer_hosted/identity/startup_config.ex",
    "hosted/lib/mixer_hosted/browser_auth/config.ex",
    "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
    "hosted/lib/mixer_hosted/browser_auth/vault.ex",
]
PRODUCER = [
    "hosted/test/mixer_hosted/browser_auth/configuration_digest_test.exs",
    "hosted/test/mixer_hosted/browser_auth/vault_test.exs",
    "docs/hosted-browser-configuration-digest.md",
    "docs/hosted-browser-session-vault.md",
    "verification/hosted-browser-configuration-digest/run.py",
    "verification/hosted-browser-session-vault/run.py",
    "verification/hosted-browser-session-vault/interoperability.exs",
    "verification/hosted-browser-session-vault/interoperability.swift",
    "verification/hosted-browser-session-vault/nist-gcm-vector.json",
]
OWNED = ["verification/browser-vault-digest-review/" + name for name in
         ["run.py", "independent.mjs", "review.exs"]]
CONTEXT = ["AGENTS.md", "hosted/mix.exs", "hosted/mix.lock", "THIRD_PARTY.yml",
           "docs/hosted-browser-session-storage-contract.md"]
FROZEN = {
    "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex": "a2166f04006293598fcb073a2f8e90170a839c2b5d0cc3ecb754bfd8c4d41532",
    "hosted/test/mixer_hosted/browser_auth/configuration_digest_test.exs": "c4ac7480f668a08ed25ef4f9de2a705f5df7a501ddb04710f698858515226ed6",
    "hosted/lib/mixer_hosted/browser_auth/vault.ex": "e376cdd7305a520c61e716e3f4fcd3f5493e280ff5424ba822516f9a6f4281b2",
    "hosted/test/mixer_hosted/browser_auth/vault_test.exs": "133dc8e8aeeec19a4a6020baa83e3badc021832360ca3a9048c88a3318a8ab38",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def fixture() -> dict:
    config = dict(
        mode="configured", public_origin="https://console.example.test", profile_id="human-main",
        profile_version=7, issuer="https://id.example.test", client_id="console-client",
        api_audience="mixer-api", authorization_endpoint="https://id.example.test/authorize",
        token_endpoint="https://id.example.test/token", id_token_jwks_endpoint="https://id.example.test/jwks",
        redirect_uri="https://console.example.test/auth/callback", client_auth_method="client_secret_basic",
        client_credential_ref="secret://browser/client-v1", session_vault_ref="vault://browser/session-v1",
        scope="openid mixer.workspace.read", response_mode="query", response_iss_required=True,
        transaction_seconds=300, session_idle_seconds=900, return_path="/workspace", failure_path="/login")
    configs = [{"name": "constructor-shaped-baseline", "values": config}]
    for name, value in [
        ("json-escaping", 'quote" slash/ backslash\\ controls\n\r\t\b\f\0'),
        ("unicode-composed", "é"), ("unicode-decomposed", "e\u0301"),
        ("unicode-separators", "line\u2028paragraph\u2029"), ("astral", "🦊"),
        ("client-byte-maximum", "é" * 128),
    ]:
        configs.append({"name": name, "values": dict(config, client_id=value)})
    csrf = base64.urlsafe_b64encode(bytes(32)).decode().rstrip("=")
    verifier = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
    generation = base64.urlsafe_b64encode(bytes(range(31, -1, -1))).decode().rstrip("=")
    session = dict(purpose="preauth", browser_id=b64(bytes(range(16))),
                   cookie_digest=b64(bytes([121]) * 32), csrf_digest=b64(hashlib.sha256(csrf.encode()).digest()),
                   epoch=11, revision=19, generation=generation, vault_generation=23,
                   config_digest=b64(bytes([123]) * 32), profile_id="human/é", profile_version=7,
                   principal_id=None, family_id=None, credential_ref=None, credential_revision=None)
    active = dict(session, purpose="active", principal_id="principal/1", family_id="browser_" + generation,
                  credential_ref="external/jti/42", credential_revision=29)
    attempt = {k: session[k] for k in ["browser_id", "cookie_digest", "epoch", "revision", "generation",
                                      "config_digest", "profile_id", "profile_version"]}
    attempt.update(purpose="attempt", state_digest=b64(bytes([125]) * 32), issuer=config["issuer"],
                   client_id=config["client_id"], redirect_uri=config["redirect_uri"], expires_at=1_800_000_300)
    return dict(configs=configs, contexts=[session, active, attempt], csrf=csrf, verifier=verifier,
                access_token="AZaz09._~+/-==", key={"id": "review-key.v1", "bytes": b64(bytes(range(32)))})


def main() -> int:
    attempt = HERE / "attempts" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-vault-digest-review-"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("MIXER_")}
    env.update(ERL_FLAGS="+S 2:2 +SDcpu 1 +SDio 1", ERL_CRASH_DUMP=str(scratch / "erl.dump"),
               BROWSER_REVIEW_FIXTURE=str(attempt / "independent-fixture.json"),
               BROWSER_REVIEW_OUTPUT=str(attempt / "product-vectors.json"))
    dependency = ROOT / "hosted/_build/test/lib/jason/ebin"
    manifest = {name: sha(ROOT / name) for name in SOURCES + PRODUCER + OWNED + CONTEXT}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    beams = {str(path.relative_to(ROOT)): sha(path) for path in sorted(dependency.glob("*.beam"))}
    (attempt / "source-inputs.json").write_text(json.dumps(dict(files=manifest, tree_sha256=digest,
                                                              jason_beams=beams), indent=2) + "\n")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    commands = []

    def run(label: str, argv: list[str]) -> str:
        try:
            result = subprocess.run(argv, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=90)
            output, error, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as expired:
            output, error, code = expired.stdout or b"", expired.stderr or b"", -1
            output = output.decode() if isinstance(output, bytes) else output
            error = error.decode() if isinstance(error, bytes) else error
        (attempt / f"{label}.stdout").write_text(output)
        (attempt / f"{label}.stderr").write_text(error)
        commands.append(dict(label=label, argv=argv, cwd=str(ROOT), exit_code=code, timeout_seconds=90,
                             stdout=str((attempt / f"{label}.stdout").relative_to(ROOT)),
                             stderr=str((attempt / f"{label}.stderr").relative_to(ROOT)),
                             stdout_sha256=sha(attempt / f"{label}.stdout"),
                             stderr_sha256=sha(attempt / f"{label}.stderr")))
        print(f"{label}: exit {code}", flush=True)
        if code:
            print(output)
            print(error)
            raise RuntimeError(f"{label} failed")
        return output

    status = "failed"
    counts = {}
    try:
        if any(manifest[name] != expected for name, expected in FROZEN.items()):
            raise RuntimeError("coordinated producer freeze changed; re-review before binding")
        if not beams:
            raise RuntimeError("preexisting pinned Jason dependency unavailable")
        run("elixir-version", ["elixir", "--version"])
        run("node-version", ["node", "-p", "JSON.stringify(process.versions)"])
        run("crypto-version", ["elixir", "-e", 'Application.load(:crypto); IO.inspect(%{otp: :erlang.system_info(:otp_release), crypto: Application.spec(:crypto, :vsn), crypto_backend: :crypto.info_lib()})'])
        run("format-review", ["elixir", "-e", 'p = hd(System.argv()); true = File.read!(p) == IO.iodata_to_binary(Code.format_string!(File.read!(p))) <> "\\n"', str(HERE / "review.exs")])
        run("compile", ["elixirc", "--warnings-as-errors", "-pa", str(dependency), "-o", str(scratch)] + SOURCES)
        (attempt / "fixture-input.json").write_text(json.dumps(fixture(), ensure_ascii=False, indent=2) + "\n")
        output = run("node-independent-generation", ["node", str(HERE / "independent.mjs"), "generate",
                                                     str(attempt / "fixture-input.json"), env["BROWSER_REVIEW_FIXTURE"]])
        counts.update(json.loads(output))
        code = 'ExUnit.start(autorun: false, seed: 0); Code.require_file(hd(System.argv())); result = ExUnit.run(); IO.puts("independent_review_result:" <> Jason.encode!(result)); System.halt(if result.failures == 0, do: 0, else: 1)'
        output = run("independent-tests", ["elixir", "-pa", str(dependency), "-pa", str(scratch), "-e", code,
                                           str(HERE / "review.exs")])
        for line in output.splitlines():
            if line.startswith("independent_review_result:"):
                counts["independent_exunit"] = json.loads(line.split(":", 1)[1])
        output = run("node-independent-verification", ["node", str(HERE / "independent.mjs"), "verify",
                                                        env["BROWSER_REVIEW_FIXTURE"], env["BROWSER_REVIEW_OUTPUT"]])
        counts.update(json.loads(output))
        run("owned-whitespace", [sys.executable, "-c",
            'import pathlib,sys; bad=[f"{name}:{n}" for name in sys.argv[1:] for n,line in enumerate(pathlib.Path(name).read_text().splitlines(),1) if line != line.rstrip(" \\t")]; print(bad);sys.exit(bool(bad))'] + OWNED)
        if manifest != {name: sha(ROOT / name) for name in manifest}:
            raise RuntimeError("source inputs changed during review")
        status = "passed"
    except Exception as error:
        (attempt / "failure.txt").write_text(str(error) + "\n")
    finally:
        shutil.rmtree(scratch)
        receipt = dict(status=status, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                       source_revision=revision, source_tree_sha256=digest,
                       source_inputs=str((attempt / "source-inputs.json").relative_to(ROOT)),
                       coordinated_frozen_inputs=FROZEN,
                       python_version=sys.version, commands=commands, counts=counts,
                       cleanup=dict(owned_scratch_removed=not scratch.exists(), owned_scratch_path=str(scratch),
                                    started_browser_capture_native_ui_emulator_or_phone_processes=False,
                                    started_shared_application_provider_network_or_database=False,
                                    preserved_other_projects_processes_and_data=True),
                       scope="Independent local-only Node/OpenSSL byte/hash/AES256GCM review plus selected ExUnit. Seven explicitly named ordinary modules; preexisting Jason BEAM dependency only. No producer runner is executed. Frozen catalog-inspector, authority-driver and outbound Worker transportV2 are never read/imported/compiled/executed.",
                       pending=["trusted Config constructor provenance and current immutable owner context",
                                "durable session owner and SQL storage join/fencing",
                                "external reviewed runtime key custody/rotation/recovery/per-key usage limits",
                                "provider exchange and current independent OIDC/API verification",
                                "shared application startup and HTTP/console/ingress/deployment integration",
                                "browser/native runtime/physical device/security/customer/GA acceptance"])
        report = ROOT / "docs/browser-vault-digest-review.md"
        if report.exists():
            receipt["review_report"] = str(report.relative_to(ROOT))
            receipt["review_report_sha256"] = sha(report)
        receipt["prior_attempts"] = [
            {"receipt": str(path.relative_to(ROOT)), "status": json.loads(path.read_text())["status"]}
            for path in sorted((HERE / "attempts").glob("*/receipt.json"))]
        receipt["outputs"] = {str(path.relative_to(ROOT)): sha(path) for path in sorted(attempt.iterdir())
                              if path.is_file()}
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"receipt: {attempt.relative_to(ROOT)}/receipt.json", flush=True)
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
