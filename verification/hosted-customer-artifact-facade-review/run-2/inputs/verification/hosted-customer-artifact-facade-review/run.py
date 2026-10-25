#!/usr/bin/env python3
"""Independent facade checks; snapshots ordinary producer inputs, never Mix."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/hosted-customer-artifact-facade/run-1"
LIBS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]
EXPECTED = {
    "hosted/lib/mixer_hosted/customer_artifacts.ex": "8b099b45745c8705ab3f9da7216ea9ba011f1bfff7352eda1d5e76253a01a516",
    "hosted/test/mixer_hosted/customer_artifacts_test.exs": "83eefefd88c7dc2efead13f9f138f011ac81032aaa63d670a4d8580f74f80c9d",
    "docs/hosted-customer-artifact-facade.md": "df55bd1c4c9811c95dbac5a294cc90d054e14dd761c250df68fd44ef87dea306",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = 1
    while (HERE / f"run-{index}").exists():
        index += 1
    out = HERE / f"run-{index}"
    out.mkdir()
    scratch = Path(tempfile.mkdtemp(prefix="mixer-facade-review-"))
    receipt = {
        "started_unix": time.time(),
        "source_revision": "9662eda186e3beee084f92ac25c4116c92f2cebc",
        "revision_provenance": "root-supplied context; no Git command",
        "scope": "independent public CustomerArtifacts facade checks on frozen producer ordinary sources with synthetic restricted local PostgreSQL runtime; no HTTP, provider, native, cloud, or GA qualification",
        "dependency_scope": "producer run-1 storage b6e9fcd0c3df4f28b6da90589eb2d3c465780c4f8ec484ace74f893aeb216340; does not qualify later repaired storage",
        "commands": [], "cleanup": {}, "input_sha256": {}, "scratch": str(scratch),
    }
    started = False
    pg = None

    def run(name, argv, env=None, check=True):
        proc = subprocess.run(argv, cwd=scratch, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, env=env, timeout=90)
        (out / f"{name}.log").write_text(proc.stdout)
        receipt["commands"].append({"name": name, "argv": [str(a) for a in argv],
                                    "exit_code": proc.returncode, "output": f"{name}.log"})
        if check and proc.returncode:
            raise RuntimeError(f"{name} failed ({proc.returncode}); preserved in {out}")
        return proc.stdout.strip()

    try:
        producer_receipt = json.loads((PRODUCER / "receipt.json").read_text())
        for rel, expected in EXPECTED.items():
            if sha(ROOT / rel) != expected:
                raise RuntimeError(f"root source changed before review snapshot: {rel}")
        paths = list(producer_receipt["input_sha256"])
        paths.remove("verification/hosted-customer-artifact-facade/run.py")
        for rel in paths:
            src = PRODUCER / "inputs" / rel
            actual = sha(src)
            if actual != producer_receipt["input_sha256"][rel]:
                raise RuntimeError(f"producer snapshot hash mismatch: {rel}")
            dst = out / "inputs" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            receipt["input_sha256"][rel] = actual
        for local in [Path(__file__), HERE / "review_test.exs"]:
            rel = str(local.relative_to(ROOT))
            dst = out / "inputs" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local, dst)
            receipt["input_sha256"][rel] = sha(local)
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(receipt["input_sha256"], sort_keys=True).encode()).hexdigest()
        deps = {}
        dep_args = []
        for lib in LIBS:
            source = ROOT / "hosted/_build/test/lib" / lib / "ebin"
            dest = scratch / "dependencies" / lib / "ebin"
            shutil.copytree(source, dest)
            dep_args.extend(["-pa", str(dest)])
            for source_file in sorted(source.iterdir()):
                if source_file.is_file():
                    deps[str(source_file.relative_to(ROOT))] = sha(source_file)
        (out / "dependency-beams.json").write_text(json.dumps(deps, indent=2, sort_keys=True) + "\n")
        receipt["dependency_manifest_sha256"] = sha(out / "dependency-beams.json")
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        pg = Path(run("postgres-bindir", ["pg_config", "--bindir"]))
        run("postgres-version", [pg / "postgres", "--version"])
        run("platform", ["uname", "-a"])
        sources = sorted(str(out / "inputs" / rel) for rel in paths
                         if rel.endswith((".ex", ".exs")) and "/test/" not in rel and rel != "hosted/mix.exs")
        beams = scratch / "beams"
        beams.mkdir()
        run("compile", ["elixirc", "--warnings-as-errors", *dep_args, "-o", str(beams), *sources])
        run("postgres-init", [pg / "initdb", "-D", scratch / "pg", "-U", "review_admin", "-A", "trust", "--no-locale", "-E", "UTF8"])
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        with (scratch / "pg/postgresql.conf").open("a") as config:
            config.write(f"\nlisten_addresses='127.0.0.1'\nport={port}\nunix_socket_directories='{scratch}'\nmax_connections=20\n")
        receipt["postgres_endpoint"] = {"host": "127.0.0.1", "port": port, "database": "facade_review", "disposable": True}
        run("postgres-start", [pg / "pg_ctl", "-D", scratch / "pg", "-l", scratch / "postgres.log", "-w", "start"])
        started = True
        conn = ["-h", "127.0.0.1", "-p", str(port), "-U", "review_admin"]
        run("create-database", [pg / "createdb", *conn, "facade_review"])
        run("roles-schema", [pg / "psql", *conn, "-d", "facade_review", "-v", "ON_ERROR_STOP=1", "-c",
            "CREATE ROLE review_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE review_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; REVOKE CREATE ON SCHEMA public FROM PUBLIC; ALTER SCHEMA public OWNER TO review_owner; GRANT USAGE ON SCHEMA public TO review_runtime;"])
        env = dict(os.environ, FACADE_REVIEW_PORT=str(port), FACADE_REVIEW_INPUTS=str(out / "inputs"))
        run("tests", ["elixir", *dep_args, "-pa", str(beams), str(out / "inputs/verification/hosted-customer-artifact-facade-review/review_test.exs")], env=env)
        receipt["success"] = True
    except Exception as error:
        receipt["success"] = False
        receipt["failure"] = str(error)
    finally:
        if started:
            run("postgres-stop", [pg / "pg_ctl", "-D", scratch / "pg", "-m", "immediate", "-w", "stop"], check=False)
            status = run("postgres-status", [pg / "pg_ctl", "-D", scratch / "pg", "status"], check=False)
            receipt["cleanup"]["postgres_stopped"] = "no server running" in status
        else:
            receipt["cleanup"]["postgres_stopped"] = True
        if (scratch / "postgres.log").exists():
            shutil.copy2(scratch / "postgres.log", out / "postgres.log")
        shutil.rmtree(scratch)
        receipt["cleanup"]["scratch_removed"] = not scratch.exists()
        receipt["finished_unix"] = time.time()
        receipt["output_sha256"] = {p.name: sha(p) for p in sorted(out.glob("*.log"))}
        receipt["root_freeze_unchanged"] = {rel: sha(ROOT / rel) == expected for rel, expected in EXPECTED.items()}
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"success": receipt["success"], "receipt": str(out / "receipt.json"), "cleanup": receipt["cleanup"]}))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
