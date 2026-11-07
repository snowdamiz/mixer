#!/usr/bin/env python3
"""Source-only candidate preparation. Does not invoke runtimes or open sockets."""
import sys


def deny_children_and_sockets(event, args):
    if event.startswith("socket.") or event in {
        "subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.fork",
        "os.forkpty", "pty.spawn",
    }:
        raise RuntimeError("Forbidden source-only action: " + event)


sys.addaudithook(deny_children_and_sockets)
import difflib
import hashlib
import json
import platform
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RAW = ROOT / "verification/github-delivery-positive-timestamp/ci-review/network"
FIXTURE = "hosted/test/support/identity_tls_fixture.ex"
STARTUP = "hosted/test/mixer_hosted/identity/startup_linux_network_test.exs"
K03 = "hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs"
CONTROL = "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs"
PATHS = [
    FIXTURE, STARTUP, K03,
    "hosted/lib/mixer_hosted/identity/key_owner.ex",
    "hosted/lib/mixer_hosted/identity/fetch_flight.ex",
    "hosted/lib/mixer_hosted/identity/bounded_tcp.ex",
    "hosted/lib/mixer_hosted/identity/jwks_transport.ex",
    "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex",
    "hosted/lib/mixer_hosted/application.ex",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


manifest = json.loads((RAW / "product-source-manifest.json").read_bytes())
sources = {}
archive = RAW / "prepared-source-dependencies-tools.tar"
with tarfile.open(archive) as tar:
    for path in PATHS:
        member = tar.getmember(path)
        assert member.isfile()
        data = tar.extractfile(member).read()
        assert digest(data) == manifest[path]["sha256"]
        assert len(data) == manifest[path]["bytes"]
        assert data == (ROOT / path).read_bytes(), path
        sources[path] = data

old = sources[FIXTURE].decode()
new = old
edits = [
    (
        "        send(owner, {:accepted, pid, socket})\n",
        "        # Record ownership before this handler can report an early EOF.\n"
        "        :ok = GenServer.call(owner, {:accepted, pid, socket})\n",
    ),
    (
        "       closed: 0,\n",
        "       closed: 0,\n       terminal_results: [],\n",
    ),
    (
        '''    try do
      with {:ok, socket} <- :ssl.handshake(socket, 3_000),
           {:ok, request} <- request(socket, "") do
        {:ok, info} = :ssl.connection_information(socket, [:sni_hostname, :protocol])
        response = GenServer.call(owner, {:request, request, info})
        respond(socket, response)
        # Observe client close even for keepalive/stall responses.
        :ssl.recv(socket, 0, 3_000)
      end
    after
      :ssl.close(socket)
      send(owner, {:closed, self()})
    end
''',
        '''    result =
      try do
        with {:handshake, {:ok, socket}} <- {:handshake, :ssl.handshake(socket, 3_000)},
             {:request, {:ok, request}} <- {:request, request(socket, "")} do
          {:ok, info} = :ssl.connection_information(socket, [:sni_hostname, :protocol])
          response = GenServer.call(owner, {:request, request, info})
          respond(socket, response)
          # Withhold a stall response while still observing client EOF immediately.
          {:peer_close, :ssl.recv(socket, 0, 3_000)}
        end
      after
        :ssl.close(socket)
      end

    send(owner, {:finished, self(), terminal_result(result)})
''',
    ),
    (
        '  defp request(socket, acc) do\n',
        '''  defp terminal_result({stage, result}) do
    {outcome, bytes} =
      case result do
        {:error, :closed} -> {:peer_closed, 0}
        {:error, :timeout} -> {:timeout, 0}
        {:ok, data} when is_binary(data) -> {:unexpected_data, byte_size(data)}
        {:error, _} -> {:transport_error, 0}
        _ -> {:unexpected_result, 0}
      end

    %{stage: stage, outcome: outcome, unexpected_bytes: bytes}
  end

  defp request(socket, acc) do
''',
    ),
    (
        "  defp respond(_, :stall), do: Process.sleep(3_000)\n",
        "  defp respond(_, :stall), do: :ok\n",
    ),
    (
        "  def handle_info({:accepted, pid, socket}, s) do\n",
        "  def handle_call({:accepted, pid, socket}, _, s) do\n",
    ) if "  def handle_info({:accepted, pid, socket}, s) do\n" in old else (
        "  def handle_info({:accepted, pid, socket}, s),\n    do:\n      {:noreply,\n",
        "  def handle_call({:accepted, pid, socket}, _, s),\n    do:\n      {:reply, :ok,\n",
    ),
    (
        '''  def handle_info({:closed, pid}, s),
    do: {:noreply, %{s | sockets: Map.delete(s.sockets, pid), closed: s.closed + 1}}
''',
        '''  def handle_info({:finished, pid, terminal}, s) do
    # Handler cleanup is not proof of peer closure: local timeouts must not pass
    # shutdown assertions. EOF may also arrive before TLS or HTTP completes.
    peer_closed = terminal.outcome == :peer_closed

    {:noreply,
     %{
       s
       | sockets: Map.delete(s.sockets, pid),
         closed: s.closed + if(peer_closed, do: 1, else: 0),
         terminal_results: Enum.take([terminal | s.terminal_results], 16)
     }}
  end
''',
    ),
    (
        "  def terminate(_, s) do\n    :ssl.close(s.listener)\n",
        '''  def terminate(_, s) do
    # Preserve bounded failure diagnostics before cleanup; never print requests,
    # certificates, key material, sockets, or unexpected application data.
    summary = %{
      accepted: s.accepted,
      peer_closed: s.closed,
      active: map_size(s.sockets),
      requests: length(s.requests),
      terminal_results: s.terminal_results
    }

    try do
      IO.puts("TLSFixture lifecycle: #{inspect(summary, limit: 200, printable_limit: 256)}")
    catch
      _, _ -> :ok
    end

    :ssl.close(s.listener)
''',
    ),
]
for before, after in edits:
    assert new.count(before) == 1, before
    new = new.replace(before, after)

candidate = OUT / "candidate" / FIXTURE
candidate.parent.mkdir(parents=True, exist_ok=True)
candidate.write_text(new)
(OUT / "fixture-candidate.patch").write_text("".join(difflib.unified_diff(
    old.splitlines(keepends=True), new.splitlines(keepends=True),
    fromfile="a/" + FIXTURE, tofile="b/" + FIXTURE,
)))
candidate_manifest = dict(manifest)
candidate_manifest[FIXTURE] = {"bytes": len(new.encode()), "sha256": digest(new.encode())}
control_bytes = (OUT / "tls_fixture_lifecycle_control_test.exs").read_bytes()
control_candidate = OUT / "candidate" / CONTROL
control_candidate.parent.mkdir(parents=True, exist_ok=True)
control_candidate.write_bytes(control_bytes)
control_patch = "".join(difflib.unified_diff(
    [], control_bytes.decode().splitlines(keepends=True),
    fromfile="/dev/null", tofile="b/" + CONTROL,
))
(OUT / "integration-candidate.patch").write_text(
    (OUT / "fixture-candidate.patch").read_text() + control_patch
)
assert CONTROL not in manifest
candidate_manifest[CONTROL] = {"bytes": len(control_bytes), "sha256": digest(control_bytes)}
canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
assert digest(canonical(manifest)) == "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e"
(OUT / "candidate-product-source-manifest.json").write_text(
    json.dumps(candidate_manifest, indent=2, sort_keys=True) + "\n"
)
evidence = {
    "schema": 1,
    "status": "source-candidate-only-runtime-unrun",
    "baseline_revision": "e9fc0e7d984c79bf2d3493f5d5d16a0b167b3af7",
    "baseline_run": 40770270255,
    "baseline_source_snapshot_sha256": "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e",
    "baseline_prepared_archive_sha256": digest(archive.read_bytes()),
    "baseline_source_count": len(manifest),
    "inspected_sources": {p: manifest[p] for p in PATHS},
    "inspected_sources_match_frozen_and_workspace": True,
    "changed_source": FIXTURE,
    "candidate_source": candidate_manifest[FIXTURE],
    "candidate_source_count": len(candidate_manifest),
    "added_test_source": {"path": CONTROL, **candidate_manifest[CONTROL]},
    "candidate_source_snapshot_sha256": digest(canonical(candidate_manifest)),
    "unchanged_startup_test": manifest[STARTUP],
    "unchanged_k03_test": manifest[K03],
    "failure_log": {
        "path": str((RAW / "logs/0101.stdout").relative_to(ROOT)),
        "sha256": digest((RAW / "logs/0101.stdout").read_bytes()),
    },
    "command": "python3 -B verification/identity-startup-socket-close-investigation/prepare_candidate.py",
    "tool_version": platform.python_version(),
    "audit": "Python audit denies child processes and every socket event",
    "runtime_tests": "not run; remote CI selection and independent review required",
    "processes_or_sockets_started": 0,
    "protected_files": {
        p: digest((ROOT / p).read_bytes()) for p in [
            "hosted/lib/mixer_hosted/browser_auth/store.ex",
            ".github/workflows/hosted.yml",
        ]
    },
}
(OUT / "source-inspection.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
print(json.dumps({
    "sources_verified": len(PATHS), "baseline_source_count": len(manifest),
    "candidate_source_count": len(candidate_manifest),
    "candidate_fixture_sha256": digest(new.encode()),
    "candidate_source_snapshot_sha256": digest(canonical(candidate_manifest)),
    "startup_test_unchanged": True, "runtime_tests": "unrun",
}))
