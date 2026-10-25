#!/usr/bin/env python3
"""Data-only snapshot review. No app, SQL execution, native runtime or frozen lanes."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = ["hosted/lib/mixer_hosted/browser_auth/vault.ex",
           "hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex"]
SQL = "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex"
FROZEN = {
    SOURCES[0]: "e376cdd7305a520c61e716e3f4fcd3f5493e280ff5424ba822516f9a6f4281b2",
    SOURCES[1]: "ce92f99c3990bf9ddd0fbf5d8c7d329ea63bb5dc31ec3df4922907b19986cd3e",
    "hosted/test/mixer_hosted/browser_auth/stored_snapshot_test.exs": "bf814937391e70305f853ed5710920b3d7f54587a2497646cb025e03d8c68f2e",
}
OWNED = ["verification/hosted-browser-stored-snapshot-review/run.py",
         "verification/hosted-browser-stored-snapshot-review/review.exs"]
FILES = SOURCES + [SQL, "AGENTS.md", "docs/hosted-browser-stored-snapshot.md",
                   "verification/hosted-browser-stored-snapshot/run.py",
                   "hosted/test/mixer_hosted/browser_auth/stored_snapshot_test.exs"] + OWNED


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def columns(source: str, table: str) -> list[tuple[str, str]]:
    """Read only: balanced SQL clauses identify ordinary to_jsonb row columns."""
    start = source.index(f"CREATE TABLE public.mixer_browser_{table} (")
    start = source.index("(", start) + 1
    depth, quoted, clauses, mark, index = 0, False, [], start, start
    while index < len(source):
        char = source[index]
        if char == "'":
            if quoted and source[index:index + 2] == "''":
                index += 2
                continue
            quoted = not quoted
        if not quoted:
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    clauses.append(source[mark:index].strip())
                    break
                depth -= 1
            elif char == "," and depth == 0:
                clauses.append(source[mark:index].strip())
                mark = index + 1
        index += 1
    else:
        raise ValueError("unterminated ordinary SQL table")
    result = []
    for clause in clauses:
        words = clause.split()
        if words[0] in ["CHECK", "FOREIGN", "CONSTRAINT", "PRIMARY", "UNIQUE"]:
            continue
        if not re.fullmatch(r"[a-z_]+", words[0]) or words[1] not in ["bytea", "text", "bigint", "integer"]:
            raise ValueError("unsupported column shape")
        result.append((words[0], words[1]))
    return result


def main() -> int:
    attempt = HERE / "attempts" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-stored-snapshot-review-"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("MIXER_")}
    env.update(ERL_FLAGS="+S 2:2 +SDcpu 1 +SDio 1", ERL_CRASH_DUMP=str(scratch / "erl.dump"),
               SNAPSHOT_REVIEW_COLUMNS=str(attempt / "sql-columns.tsv"))
    manifest = {name: sha(ROOT / name) for name in FILES}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (attempt / "source-inputs.json").write_text(json.dumps(dict(files=manifest, tree_sha256=digest), indent=2) + "\n")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    commands = []

    def run(label: str, argv: list[str]) -> str:
        try:
            result = subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=True, timeout=90)
            out, err, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as expired:
            out, err, code = expired.stdout or b"", expired.stderr or b"", -1
            out = out.decode() if isinstance(out, bytes) else out
            err = err.decode() if isinstance(err, bytes) else err
        (attempt / f"{label}.stdout").write_text(out)
        (attempt / f"{label}.stderr").write_text(err)
        commands.append(dict(label=label, argv=argv, cwd=str(ROOT), exit_code=code, timeout_seconds=90,
                             stdout=str((attempt / f"{label}.stdout").relative_to(ROOT)),
                             stderr=str((attempt / f"{label}.stderr").relative_to(ROOT)),
                             stdout_sha256=sha(attempt / f"{label}.stdout"), stderr_sha256=sha(attempt / f"{label}.stderr")))
        print(f"{label}: exit {code}", flush=True)
        if code:
            print(out, err)
            raise RuntimeError(f"{label} failed")
        return out

    status, counts, shape = "failed", {}, {}
    try:
        if any(manifest[name] != value for name, value in FROZEN.items()):
            raise RuntimeError("coordinated frozen snapshot or Vault changed")
        sql = (ROOT / SQL).read_text()
        shape = {kind: columns(sql, table) for kind, table in
                 [("browser", "sessions"), ("vault", "session_vault"), ("attempt", "oidc_attempts")]}
        (attempt / "sql-shape.json").write_text(json.dumps(shape, indent=2) + "\n")
        (attempt / "sql-columns.tsv").write_text("".join(kind + "\t" + ",".join(name for name, _ in values) + "\n"
                                                        for kind, values in shape.items()))
        run("elixir-version", ["elixir", "--version"])
        run("crypto-version", ["elixir", "-e", 'Application.load(:crypto); IO.inspect(%{otp: :erlang.system_info(:otp_release), crypto: Application.spec(:crypto, :vsn), backend: :crypto.info_lib()})'])
        run("compile", ["elixirc", "--warnings-as-errors", "-o", str(scratch)] + SOURCES)
        code = 'ExUnit.start(autorun: false, seed: 0); Code.require_file(hd(System.argv())); r = ExUnit.run(); IO.puts("independent_result:" <> Enum.map_join([:total, :failures, :skipped, :excluded], ",", &Integer.to_string(Map.fetch!(r, &1)))); System.halt(if r.failures == 0, do: 0, else: 1)'
        run("independent-tests", ["elixir", "-pa", str(scratch), "-e", code, str(HERE / "review.exs")])
        run("owned-whitespace", [sys.executable, "-c", 'import pathlib,sys; bad=[f"{p}:{n}" for p in sys.argv[1:] for n,line in enumerate(pathlib.Path(p).read_text().splitlines(),1) if line != line.rstrip(" \\t")]; print(bad);sys.exit(bool(bad))'] + OWNED)
        if any(manifest[name] != sha(ROOT / name) for name in SOURCES + list(FROZEN)):
            raise RuntimeError("frozen source changed during review")
        # SQL implementation may be changing in its separate lane: bind the exact
        # read input and verify only the public column shape remains unchanged.
        current = (ROOT / SQL).read_text()
        if shape != {kind: columns(current, table) for kind, table in
                     [("browser", "sessions"), ("vault", "session_vault"), ("attempt", "oidc_attempts")]}:
            raise RuntimeError("SQL public column shape changed during review")
        status = "passed"
    except Exception as error:
        (attempt / "failure.txt").write_text(str(error) + "\n")
    finally:
        shutil.rmtree(scratch)
        output = attempt / "independent-tests.stdout"
        if output.exists():
            for line in output.read_text().splitlines():
                if line.startswith("independent_result:"):
                    counts = dict(zip(["total", "failures", "skipped", "excluded"], map(int, line.split(":", 1)[1].split(","))))
        report = ROOT / "docs/hosted-browser-stored-snapshot-review.md"
        receipt = dict(status=status, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                       source_revision=revision, source_tree_sha256=digest,
                       source_inputs=str((attempt / "source-inputs.json").relative_to(ROOT)),
                       coordinated_frozen_inputs=FROZEN, python_version=sys.version, commands=commands,
                       independent_exunit=counts, public_column_counts={k: len(v) for k, v in shape.items()},
                       sql_source_sha256_at_finish=sha(ROOT / SQL),
                       cleanup=dict(owned_scratch_removed=not scratch.exists(), owned_scratch_path=str(scratch),
                                    started_shared_app_network_database_browser_capture_native_or_phone=False,
                                    preserved_other_projects_processes_and_data=True),
                       scope="Data-only independent public SQL row-column comparison and selected Vault+StoredSnapshot host probes. SQL text is read only; no SQL module, statements or database are executed. No whole app, frozen lanes, provider, native runtime or capture.",
                       pending=["actual SQL JSONB composition and canonical bytea_output connection setting",
                                "database body/role/RLS/topology review and durable owner integration",
                                "current request/config/time/verifier admission and atomic claim",
                                "external runtime key custody and provider exchange",
                                "HTTP/console/browser/deployment/security/native/customer/GA acceptance"])
        if report.exists():
            receipt.update(review_report=str(report.relative_to(ROOT)), review_report_sha256=sha(report))
        receipt["outputs"] = {str(p.relative_to(ROOT)): sha(p) for p in sorted(attempt.iterdir()) if p.is_file()}
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"receipt: {attempt.relative_to(ROOT)}/receipt.json", flush=True)
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
