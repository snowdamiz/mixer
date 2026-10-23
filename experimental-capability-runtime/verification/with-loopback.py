#!/usr/bin/env python3
"""Run a command with a real untrusted loopback TLS fixture; never changes trust."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import socket
import ssl
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command[1:] if args.command[:1] == ["--"] else args.command
assert command
out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
scratch_root = ROOT / "experimental-capability-runtime/.build"; scratch_root.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="untrusted-loopback-", dir=scratch_root) as scratch_name:
    scratch = Path(scratch_name)
    certificate, key = scratch / "certificate.pem", scratch / "ephemeral-key.pem"
    gen = ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(certificate), "-days", "1", "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1"]
    generated = subprocess.run(gen, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)
    (out / "certificate-generation.log").write_bytes(generated.stdout)
    assert generated.returncode == 0
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(certificate, key)
    listener = socket.socket(); listener.bind(("127.0.0.1", 0)); listener.listen(16); listener.settimeout(0.1)
    port = listener.getsockname()[1]
    stopped = threading.Event()
    observations = {"tcp_accepts": 0, "tls_failures": 0, "application_requests": 0, "errors": []}
    def serve():
        while not stopped.is_set():
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            observations["tcp_accepts"] += 1
            connection.settimeout(2)
            try:
                with context.wrap_socket(connection, server_side=True) as tls:
                    data = tls.recv(4096)
                    if data: observations["application_requests"] += 1
            except (ssl.SSLError, OSError) as error:
                observations["tls_failures"] += 1
                observations["errors"].append(type(error).__name__ + ":" + str(error))
            finally:
                connection.close()
    thread = threading.Thread(target=serve, daemon=True); thread.start()
    environment = {"MIXER_EXPERIMENTAL_TLS_URL": "https://127.0.0.1:" + str(port) + "/"}
    try:
        result = subprocess.run(command, cwd=ROOT, env=os.environ | environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    finally:
        stopped.set(); listener.close(); thread.join(timeout=3)
    (out / "command.log").write_bytes(result.stdout)
    receipt = {"command": command, "environment": environment, "exit_code": result.returncode,
               "output_sha256": hashlib.sha256(result.stdout).hexdigest(), "certificate_generation": gen,
               "certificate_sha256": hashlib.sha256(certificate.read_bytes()).hexdigest(),
               "observations": observations, "server_stopped": not thread.is_alive(),
               "scope": "Actual normal-trust loopback TLS rejection, no trust/keychain/credential change; not HTTPS success or device evidence"}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(result.stdout.decode(errors="replace")[-18000:])
    print(json.dumps(observations))
    assert observations["tcp_accepts"] >= 1 and observations["tls_failures"] >= 1 and observations["application_requests"] == 0
    assert not thread.is_alive()
    raise SystemExit(result.returncode)
