#!/usr/bin/env python3
"""Replay against a fresh loopback PostgreSQL cluster and the ordinary Phoenix endpoint."""
import argparse
import contextlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

FIXTURE_ORIGIN = "https://console.fixture.invalid"
ROLES = """
CREATE ROLE browser_admin LOGIN SUPERUSER NOINHERIT;
CREATE ROLE browser_schema_owner NOLOGIN NOINHERIT;
CREATE ROLE browser_writer NOLOGIN NOINHERIT;
CREATE ROLE browser_lifecycle LOGIN NOINHERIT;
CREATE ROLE browser_ordinary LOGIN NOINHERIT;
CREATE ROLE mixer_customer_build_catalog_definer_v1 NOLOGIN NOINHERIT;
CREATE ROLE mixer_build_create LOGIN NOINHERIT;
"""
TEST = "test/mixer_hosted/browser_auth/application_registration_proof_test.exs"
LEGACY_TEST = "test/mixer_hosted/browser_auth/workspace_support_http_test.exs"


class UnknownCustody(RuntimeError):
    pass


@contextlib.contextmanager
def scratch(parent):
    path = Path(tempfile.mkdtemp(prefix="registration-run-", dir=parent))
    preserve = False
    try:
        yield path
    except UnknownCustody:
        preserve = True
        print(f"Preserve owned scratch pending cleanup verification: {path}", flush=True)
        raise
    finally:
        if not preserve:
            shutil.rmtree(path)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_until(check, process, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Owned process exited {process.returncode} before becoming ready")
        if value := check():
            return value
        time.sleep(0.1)
    raise TimeoutError("Local proof prerequisite did not become ready")


@contextlib.contextmanager
def owned(argv, cwd, env=None, output=None):
    process = subprocess.Popen(argv, cwd=cwd, env=env, start_new_session=True,
                               stdout=output, stderr=subprocess.STDOUT if output else None)
    try:
        yield process
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            print(f"Owned group {process.pid} absent. Direct exit {process.returncode}.", flush=True)
        except PermissionError as error:
            raise UnknownCustody(f"Owned group {process.pid}: {error}") from error
        else:
            raise UnknownCustody(f"Owned group {process.pid} was not observed absent")


def bridge(server_options, dist, handoff):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            # Request paths can include one-use fixture credentials.
            pass

        def do_GET(self):
            path = urlsplit(self.path)
            if path.path == "/__fixture_session" and path.query == handoff["nonce"]:
                if handoff["used"]:
                    self.send_error(410)
                    return
                handoff["used"] = True
                self.send_response(303)
                self.send_header("Set-Cookie", "__Host-mixer-session=" + handoff["cookie"] +
                                 "; Path=/; Secure; HttpOnly; SameSite=Lax")
                self.send_header("Location", "/workspace")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
            elif path.path.startswith(("/auth/", "/console-api/")):
                self.forward()
            else:
                asset = (dist / path.path.lstrip("/")).resolve()
                if not asset.is_relative_to(dist):
                    self.send_error(404)
                    return
                if path.path in ("/", "/workspace", "/builds", "/releases"):
                    asset = dist / "index.html"
                if not asset.is_file():
                    self.send_error(404)
                    return
                media = {
                    ".html": "text/html; charset=utf-8", ".js": "text/javascript",
                    ".css": "text/css", ".png": "image/png", ".webp": "image/webp",
                }
                self.reply(200, [("Content-Type", media.get(asset.suffix, "application/octet-stream"))], asset.read_bytes())

        def do_POST(self):
            if self.path == "/__fixture_done" and self.headers.get("Origin") == f"http://localhost:{self.server.server_port}":
                Path(handoff["done"]).touch()
                self.reply(204, [], b"")
                return
            if not urlsplit(self.path).path.startswith("/console-api/"):
                self.send_error(404)
                return
            if self.headers.get("Origin") != f"http://localhost:{self.server.server_port}":
                self.send_error(403)
                return
            self.forward()

        def forward(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4096:
                self.send_error(413)
                return
            headers = {key: value for key, value in self.headers.items()
                       if key.lower() in {"accept", "cookie", "content-type", "x-mixer-csrf"}}
            if self.command == "POST":
                headers["Origin"] = FIXTURE_ORIGIN
            backend = http.client.HTTPConnection("127.0.0.1", server_options["phoenix"], timeout=8)
            try:
                backend.request(self.command, self.path, self.rfile.read(length) if length else None, headers)
                response = backend.getresponse()
                self.reply(response.status, response.getheaders(), response.read(300_000))
            finally:
                backend.close()

        def reply(self, status, headers, body):
            self.send_response(status)
            for key, value in headers:
                if key.lower() not in {"content-length", "connection", "transfer-encoding", "date", "server"}:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


def run_migration_spec(host, pg, port, psql, env):
    names = json.loads((host / "test/support/reviewed_migrations.json").read_text())
    found = sorted(path.name for path in (host / "priv/repo/migrations").iterdir() if path.is_file())
    if names != found:
        raise RuntimeError("Unexpected migration directory entry")
    roles = """
    CREATE ROLE migration_owner NOLOGIN NOINHERIT;
    CREATE ROLE migration_operator LOGIN NOINHERIT;
    GRANT migration_owner TO migration_operator;
    CREATE ROLE migration_runtime LOGIN NOBYPASSRLS NOCREATEDB NOCREATEROLE;
    """
    subprocess.run(psql + ["-c", roles], check=True, timeout=10)
    subprocess.run([pg / "createdb", "-h", "127.0.0.1", "-p", str(port),
                    "-U", "fixture_admin", "-O", "migration_owner", "browser_migrations"],
                   check=True, timeout=10)
    dependencies = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql",
                    "postgrex", "jason", "oban", "mixer_hosted"]
    argv = ["elixir"]
    for dep in dependencies:
        ebin = host / "_build/test/lib" / dep / "ebin"
        if not ebin.is_dir():
            raise RuntimeError("Run the HTTP proof first to prepare the locked Test runtime beams")
        argv.extend(["-pa", ebin])
    argv += ["-e", """
    ExUnit.start(autorun: false, seed: 0, trace: true)
    Code.require_file("test/mixer_hosted/browser_auth/migration_spec.exs")
    result = ExUnit.run()
    System.halt(if result.total == 1 and result.failures == 0 and result.skipped == 0, do: 0, else: 1)
    """]
    with owned(argv, host, dict(env, MIXER_BROWSER_MIGRATION_PORT=str(port))) as migrations:
        if migrations.wait(timeout=60):
            raise RuntimeError("Closed-list migration fixture failed")
    print("PASS. Closed-list migration integration.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="Private checkout containing the product patch and proof fixtures")
    parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--browser", action="store_true", help="Serve the console and run the Chrome browser proof")
    mode.add_argument("--migration", action="store_true", help="Run the closed-list migration integration against the Test runtime beams")
    mode.add_argument("--legacy-workspace", action="store_true", help="Exercise the existing workspace-only HTTP fixture")
    mode.add_argument("--android-starter", action="store_true", help="Exercise Android starter selection with inert tools")
    parser.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    args = parser.parse_args()
    checkout = args.checkout.resolve(strict=True)
    host = checkout / "hosted"
    pg = args.pg_bin.resolve(strict=True)
    port = free_port()
    # Keep generated fixtures and test data in this unique disposable checkout namespace.
    with scratch(checkout.parent) as tmp:
        subprocess.run([pg / "initdb", "-D", tmp / "pg", "-U", "fixture_admin",
                        "--locale=C", "--encoding=UTF8", "--auth=trust", "--no-sync"],
                       cwd=tmp, check=True, timeout=20, stdout=subprocess.DEVNULL)
        with owned([pg / "postgres", "-D", tmp / "pg", "-h", "127.0.0.1", "-p", str(port),
                    "-k", "", "-c", "fsync=off", "-c", "jit=off"], tmp) as postgres:
            psql = [pg / "psql", "-XqAt", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1",
                    "-p", str(port), "-U", "fixture_admin", "-d", "postgres"]
            wait_until(lambda: subprocess.run(psql + ["-c", "SELECT 1"], capture_output=True, timeout=2).returncode == 0,
                       postgres, 12)
            subprocess.run(psql + ["-c", ROLES], check=True, timeout=10)
            env = dict(os.environ, MIX_ENV="test", MIXER_BROWSER_STORAGE_PORT=str(port),
                       MIXER_BROWSER_CATALOG_FIXTURE_ROOT=str(tmp), TMPDIR=str(tmp))
            if args.migration:
                run_migration_spec(host, pg, port, psql, env)
                return
            live = tmp / "live.json"
            if args.browser:
                env["MIXER_REGISTRATION_LIVE"] = str(live)
                with owned(["node_modules/.bin/vite", "build", "--mode", "local-workspace-builds",
                            "--configLoader", "runner", "--outDir", str(tmp / "dist")], checkout / "console", env) as vite:
                    if vite.wait(timeout=35):
                        raise RuntimeError("Console bundling failed")
            else:
                env.pop("MIXER_REGISTRATION_LIVE", None)
            test = LEGACY_TEST if args.legacy_workspace else TEST
            filters = []
            if args.android_starter:
                test = "test/mixer_hosted/browser_auth/local_starter_http_sql_spec.exs"
                filters = ["--only", "android_starter"]
            with owned(["mix", "test", "--seed", "0", "--trace", *filters, test], host, env) as phoenix:
                if args.browser:
                    metadata = wait_until(lambda: json.loads(live.read_text()) if live.exists() else None, phoenix, 100)
                    handoff = {"cookie": metadata.pop("cookie"), "nonce": os.urandom(16).hex(), "used": False, "done": str(live) + ".complete"}
                    with bridge(metadata, tmp / "dist", handoff) as server:
                        url = f"http://localhost:{server.server_port}/__fixture_session?{handoff['nonce']}"
                        server.timeout = 0.5
                        deadline = time.monotonic() + 85
                        completed = live.with_suffix(".json.complete")
                        profile = tmp / "chrome"
                        with (tmp / "chrome.log").open("w") as chrome_log:
                            chrome = [args.chrome, "--headless", "--no-first-run", "--no-default-browser-check",
                                      "--disable-crash-reporter", "--disable-crashpad", "--disable-breakpad",
                                      "--disable-background-networking",
                                      "--disable-component-update", "--disable-sync",
                                      "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost",
                                      "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"]
                            try:
                                with owned(chrome, tmp, env, output=chrome_log) as browser:
                                    endpoint = profile / "DevToolsActivePort"
                                    wait_until(endpoint.is_file, browser, 12)
                                    driver = Path(__file__).with_name("browser-proof.mjs")
                                    browser_env = dict(env, MIXER_REGISTRATION_BROWSER_URL=url)
                                    with owned(["node", driver, endpoint], tmp, browser_env) as check:
                                        while check.poll() is None and time.monotonic() < deadline:
                                            server.handle_request()
                                        browser_result = check.wait(timeout=5)
                                    browser.wait(timeout=8)
                                    if browser_result or not completed.exists():
                                        raise RuntimeError("Browser fixture failed")
                            except Exception:
                                print((tmp / "chrome.log").read_text(errors="replace")[-4000:], flush=True)
                                raise
                if phoenix.wait(timeout=240):
                    raise RuntimeError("Phoenix fixture failed")
            remaining = subprocess.check_output(psql + ["-c",
                "SELECT count(*) FROM pg_database WHERE datname='browser_ordinary_installation_r1422'"],
                text=True, timeout=5).strip()
            if remaining != "0":
                raise RuntimeError("Fixture database did not close")
    print("PASS. Fixture services closed and transient data removed.", flush=True)


if __name__ == "__main__":
    main()
