#!/usr/bin/env python3
"""Run the private source-selection proof using the registration handoff's loopback helpers."""
import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

TEST = "test/mixer_hosted/browser_auth/local_starter_http_sql_spec.exs"


def remove_closed_tree(path):
    for parent, _, _ in os.walk(path, followlinks=False):
        Path(parent).chmod(0o700)
    shutil.rmtree(path)


@contextmanager
def scratch(parent, unknown_custody):
    path = Path(tempfile.mkdtemp(prefix="source-selection-run-", dir=parent))
    preserve = False
    try:
        yield path
    except unknown_custody:
        preserve = True
        print(f"Preserve {path} pending owner custody verification", flush=True)
        raise
    finally:
        if not preserve:
            remove_closed_tree(path)


def chrome_proof(fixture, bridge, url, target, root, delivery, env):
    profile = root / "chrome"
    chrome = [str(env["MIXER_SOURCE_CHROME"]), "--headless", "--no-first-run",
              "--no-default-browser-check", "--disable-crash-reporter", "--disable-crashpad",
              "--disable-breakpad", "--disable-background-networking", "--disable-component-update",
              "--disable-sync", "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost",
              "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"]
    with (root / "chrome.log").open("w") as log:
        with fixture.owned(chrome, root, env, output=log) as browser:
            port_file = profile / "DevToolsActivePort"
            fixture.wait_until(port_file.is_file, browser, 12)
            driver_env = dict(env, MIXER_SOURCE_BROWSER_URL=url, MIXER_SOURCE_TARGET=json.dumps(target))
            with fixture.owned(["node", delivery / "browser-proof.mjs", port_file], root, driver_env) as driver:
                deadline = time.monotonic() + 65
                while driver.poll() is None and time.monotonic() < deadline:
                    bridge.handle_request()
                if driver.wait(timeout=5):
                    raise RuntimeError("Chrome driver failed")
            if browser.wait(timeout=8):
                raise RuntimeError("Chrome returned an error")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("registration_runner", type=Path)
    parser.add_argument("export", type=Path)
    parser.add_argument("cli", type=Path)
    parser.add_argument("export_sha256")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--browser", action="store_true", help="Start a bounded browser handoff")
    mode.add_argument("--chrome", type=Path, help="Run the isolated Chrome proof using this executable")
    args = parser.parse_args()
    checkout = args.checkout.resolve(strict=True)
    host = checkout / "hosted"
    delivery = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("registration_handoff", args.registration_runner)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    pg = Path("/opt/homebrew/opt/postgresql@17/bin")
    port = fixture.free_port()

    with scratch(checkout.parent, fixture.UnknownCustody) as tmp:
        env = dict(os.environ, MIX_ENV="test", TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE="1",
                   MIXER_BROWSER_STORAGE_PORT=str(port), MIXER_BROWSER_CATALOG_FIXTURE_ROOT=str(tmp),
                   MIXER_STARTER_PROOF_ROOT=str(tmp), MIXER_STARTER_EXPORT=str(args.export.resolve(strict=True)),
                   MIXER_STARTER_CLI=str(args.cli.resolve(strict=True)),
                   MIXER_STARTER_PREPARE=str(delivery / "prepare-starter.py"),
                   MIXER_STARTER_EXPORT_SHA256=args.export_sha256,
                   MIXER_STARTER_DISPATCH_ID="l06-local-proof-worker",
                   MIXER_STARTER_DISPATCH_PORT=str(fixture.free_port()),
                   MIXER_STARTER_WORKER_PROOF=str(delivery / "worker-proof.py"))

        if args.chrome:
            env["MIXER_SOURCE_CHROME"] = str(args.chrome.resolve(strict=True))
        live = tmp / "source-live.json"
        if args.browser or args.chrome:
            env["MIXER_STARTER_LIVE"] = str(live)
            with fixture.owned(["node_modules/.bin/vite", "build", "--mode", "local-workspace-builds",
                                "--configLoader", "runner", "--outDir", str(tmp / "dist")],
                               checkout / "console", env) as vite:
                if vite.wait(timeout=45):
                    raise RuntimeError("Console bundling failed")
        else:
            env.pop("MIXER_STARTER_LIVE", None)

        subprocess.run([pg / "initdb", "-D", tmp / "pg", "-U", "fixture_admin", "--locale=C",
                        "--encoding=UTF8", "--auth=trust", "--no-sync"], cwd=tmp, env=env,
                       check=True, timeout=20, stdout=subprocess.DEVNULL)
        with fixture.owned([pg / "postgres", "-D", tmp / "pg", "-h", "127.0.0.1", "-p", str(port),
                            "-k", "", "-c", "fsync=off", "-c", "jit=off"], tmp, env) as postgres:
            psql = [pg / "psql", "-XqAt", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1",
                    "-p", str(port), "-U", "fixture_admin", "-d", "postgres"]
            fixture.wait_until(lambda: subprocess.run(psql + ["-c", "SELECT 1"], capture_output=True,
                                                       timeout=2).returncode == 0, postgres, 12)
            subprocess.run(psql + ["-c", fixture.ROLES], check=True, timeout=10)
            with fixture.owned(["mix", "test", "--seed", "0", "--trace", TEST], host, env) as phoenix:
                if args.browser or args.chrome:
                    meta = fixture.wait_until(lambda: json.loads(live.read_text()) if live.exists() else None,
                                              phoenix, 100)
                    handoff = {"cookie": meta.pop("cookie"), "nonce": os.urandom(16).hex(),
                               "used": False, "done": str(live) + ".complete"}
                    with fixture.bridge(meta, tmp / "dist", handoff) as bridge:
                        url = f"http://localhost:{bridge.server_port}/__fixture_session?{handoff['nonce']}"
                        bridge.timeout = 0.25
                        if args.chrome:
                            chrome_proof(fixture, bridge, url, meta, tmp, delivery, env)
                        else:
                            print("Browser proof URL " + url, flush=True)
                            print("Browser proof target " + json.dumps(meta, sort_keys=True), flush=True)
                            deadline = time.monotonic() + 185
                            while phoenix.poll() is None and time.monotonic() < deadline:
                                bridge.handle_request()
                        if not Path(handoff["done"]).is_file():
                            raise RuntimeError("Browser did not finish")
                if phoenix.wait(timeout=240):
                    raise RuntimeError("HTTP/SQL proof failed")
            remaining = subprocess.check_output(psql + ["-c",
                "SELECT count(*) FROM pg_database WHERE datname='browser_ordinary_installation_r1422'"],
                text=True, timeout=5).strip()
            if remaining != "0":
                raise RuntimeError("Fixture database did not close")
    print("PASS. Proof groups closed and transient data removed.", flush=True)


if __name__ == "__main__":
    main()
