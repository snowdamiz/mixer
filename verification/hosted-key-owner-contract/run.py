#!/usr/bin/env python3
"""One isolated loopback TLS feasibility fixture; not product implementation."""
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tarfile
import tempfile
import threading
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
OUTPUT = BASE / "probe-output"
OUTPUT.mkdir(exist_ok=True)
commands = []
observations = []


def run(argv, *, cwd=ROOT, env=None, timeout=30):
    result = subprocess.run(argv, cwd=cwd, env=env, timeout=timeout, text=True, capture_output=True)
    name = f"{len(commands):02d}"
    (OUTPUT / f"{name}.stdout").write_text(result.stdout)
    (OUTPUT / f"{name}.stderr").write_text(result.stderr)
    commands.append({"argv": list(map(str, argv)), "cwd": str(cwd), "exitCode": result.returncode,
                     "stdout": f"probe-output/{name}.stdout", "stderr": f"probe-output/{name}.stderr"})
    if result.returncode:
        raise RuntimeError(f"command failed {argv}: {result.stderr[-2000:]} {result.stdout[-2000:]}")
    return result.stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


started = datetime.datetime.now(datetime.timezone.utc).isoformat()
scratch = Path(tempfile.mkdtemp(prefix="mixer-key-owner-contract-")).resolve()
listener = None
thread = None
stopping = threading.Event()
success = False
try:
    run(["git", "rev-parse", "HEAD"])
    run(["elixir", "--version"])
    run(["mix", "--version"])
    run(["python3", "--version"])
    run(["openssl", "version"])
    run(["erl", "-noshell", "-eval", 'application:load(ssl),application:load(inets),io:format("root=~s~nerts=~s~nssl=~p~ninets=~p~n",[code:root_dir(),erlang:system_info(version),application:get_key(ssl,vsn),application:get_key(inets,vsn)]),halt().'])
    for name in ["ca", "wrong-ca"]:
        run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(scratch / f"{name}.key"),
             "-out", str(scratch / f"{name}.pem"), "-days", "1", "-subj", f"/CN=Mixer Isolated Probe {name}"], timeout=15)
    run(["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout", str(scratch / "leaf.key"),
         "-out", str(scratch / "leaf.csr"), "-subj", "/CN=jwks.contract.invalid"], timeout=15)
    (scratch / "leaf.ext").write_text("subjectAltName=DNS:jwks.contract.invalid\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n")
    run(["openssl", "x509", "-req", "-in", str(scratch / "leaf.csr"), "-CA", str(scratch / "ca.pem"),
         "-CAkey", str(scratch / "ca.key"), "-CAcreateserial", "-out", str(scratch / "leaf.pem"), "-days", "1",
         "-extfile", str(scratch / "leaf.ext")], timeout=15)
    mint = scratch / "mint"
    mint.mkdir()
    with tarfile.open(BASE / "mint-1.11.0.tar") as outer:
        compressed = outer.extractfile("contents.tar.gz").read()
    with tarfile.open(fileobj=io.BytesIO(compressed)) as archive:
        archive.extractall(mint, filter="data")
    # Keep exact inspected dependency source in the supplied package tarball.
    (BASE / "mint-source-manifest.json").write_text(json.dumps({str(p.relative_to(mint)): digest(p) for p in sorted(mint.rglob("*")) if p.is_file()}, indent=2) + "\n")
    project = scratch / "harness"
    project.mkdir()
    (project / "mix.exs").write_text('''defmodule MixerTransportProbe.MixProject do
  use Mix.Project
  def project, do: [app: :mixer_transport_probe, version: "0.0.0", deps: [
    {:mint, path: %s}, {:hpax, path: %s, override: true}]]
  def application, do: [extra_applications: [:ssl, :inets]]
end
''' % (json.dumps(str(mint)), json.dumps(str(ROOT / "hosted/deps/hpax"))))
    env = dict(os.environ, MIX_ENV="prod", MIX_BUILD_PATH=str(scratch / "build"), MIX_DEPS_PATH=str(scratch / "deps"))
    run(["mix", "deps.get"], cwd=project, env=env, timeout=30)
    run(["mix", "compile"], cwd=project, env=env, timeout=30)
    (BASE / "harness.mix.exs").write_text((project / "mix.exs").read_text())
    (BASE / "harness.mix.lock").write_text((project / "mix.lock").read_text() if (project / "mix.lock").exists() else "%{}\n")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(scratch / "leaf.pem", scratch / "leaf.key")
    context.set_servername_callback(lambda sock, name, _ctx: observations.append({"event": "sni", "name": name}))
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(4)
    listener.settimeout(0.1)
    port = listener.getsockname()[1]

    def serve():
        while not stopping.is_set():
            try:
                raw, peer = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            raw.settimeout(3)
            try:
                with context.wrap_socket(raw, server_side=True) as stream:
                    received = b""
                    while b"\r\n\r\n" not in received and len(received) < 10_240:
                        part = stream.recv(2048)
                        if not part:
                            break
                        received += part
                    lines = received.decode("ascii").split("\r\n")
                    path = lines[0].split(" ")[1]
                    observations.append({"event": "request", "peer": list(peer), "path": path, "headers": lines[1:-2]})
                    if path in ["/slow", "/kill"]:
                        before = time.monotonic()
                        stream.recv(1)
                        observations.append({"event": "peer_closed", "path": path, "elapsedMs": round((time.monotonic() - before) * 1000)})
                        continue
                    if path == "/ok":
                        response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nCache-Control: max-age=60\r\nConnection: close\r\n\r\n{}"
                    else:
                        code = b"200 OK" if path == "/oversize200" else b"500 Error"
                        response = b"HTTP/1.1 " + code + b"\r\nConnection: close\r\n\r\n" + b"x" * 393_216
                    try:
                        for offset in range(0, len(response), 16_384):
                            stream.sendall(response[offset:offset + 16_384])
                        if path in ["/large500", "/oversize200"]:
                            stream.recv(1)
                            observations.append({"event": "peer_closed", "path": path})
                    except (ssl.SSLError, BrokenPipeError, ConnectionResetError):
                        observations.append({"event": "peer_closed_during_send", "path": path})
            except ssl.SSLError as error:
                observations.append({"event": "tls_rejected", "reason": error.reason})
                raw.close()
            except Exception as error:
                observations.append({"event": "fixture_error", "type": type(error).__name__, "message": str(error)})
                raw.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    env.update(MIXER_PROBE_PORT=str(port), MIXER_PROBE_CA=str(scratch / "ca.pem"), MIXER_PROBE_WRONG_CA=str(scratch / "wrong-ca.pem"))
    output = run(["mix", "run", str(BASE / "probe.exs")], cwd=project, env=env, timeout=20)
    print(output)
    paths = {o["path"] for o in observations if o["event"] == "request"}
    assert paths == {"/ok", "/large500", "/oversize200", "/slow", "/kill", "/httpc500"}, paths
    assert not any(o["event"] == "fixture_error" for o in observations), observations
    for path in ["/kill", "/slow"]:
        assert any(o["event"] == "peer_closed" and o["path"] == path for o in observations), observations
    ok = next(o for o in observations if o.get("path") == "/ok")
    assert f"host: jwks.contract.invalid:{port}" in [v.lower() for v in ok["headers"]], ok
    assert all(not h.lower().startswith(("cookie:", "authorization:", "proxy-authorization:")) for o in observations if o["event"] == "request" for h in o["headers"])
    success = True
finally:
    stopping.set()
    if listener:
        listener.close()
    if thread:
        thread.join(timeout=4)
    scratch_path = str(scratch)
    shutil.rmtree(scratch)
    source_paths = [ROOT / p for p in ["AGENTS.md", "mixer-product-plan.md", "docs/hosted-identity-contract.md", "docs/hosted-token-verifier.md", "verification/hosted-token-verifier-root-review/acceptance.json", "hosted/mix.exs", "hosted/mix.lock", "hosted/lib/mixer_hosted/identity/trust_snapshot.ex", "hosted/lib/mixer_hosted/identity/access_token_verifier.ex", "hosted/lib/mixer_hosted/identity/verifier.ex"]]
    source_paths.extend(sorted((ROOT / "hosted/deps/hpax/lib").rglob("*.ex")))
    source_paths.append(ROOT / "hosted/deps/hpax/mix.exs")
    source_manifest = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    (BASE / "input-manifest.json").write_text(json.dumps(source_manifest, indent=2) + "\n")
    receipt = {"schema": 1, "status": "passed-feasibility-only" if success else "failed", "observedUTC": started,
               "command": ["python3", str(BASE / "run.py")], "commands": commands, "observations": observations,
               "inputAggregateSHA256": hashlib.sha256(json.dumps(source_manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
               "artifacts": {str(p.relative_to(BASE)): digest(p) for p in sorted(BASE.rglob("*")) if p.is_file() and p.name not in ["receipt.json", "run.py"] and "mint-1.11.0/" not in str(p.relative_to(BASE))},
               "cleanup": {"temporaryDirectory": scratch_path, "removed": not Path(scratch_path).exists(),
                           "listenerClosed": listener is None or listener.fileno() == -1,
                           "fixtureThreadStopped": thread is None or not thread.is_alive(),
                           "syntheticPrivateKeysPersisted": False, "simulatorsEmulatorsDevicesUI": "not used; host-only lane, physical phones disconnected"},
               "scope": "One synthetic loopback TLS server. Transport API feasibility only; no product owner/cache/adapter/provider qualification or GA acceptance."}
    (BASE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
