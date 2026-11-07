%{mix_state: mix_state, evidence: evidence} =
  Code.eval_file(Path.join(__DIR__, "compile-common.exs")) |> elem(0)

alias MixerHosted.Identity.{Admission, KeyOwner, KeyOwnerSupervisor, JWKSTransport}
true = Mix.env() == :prod

tuple_rejected =
  try do
    KeyOwnerSupervisor.init({:fixture, []})
    false
  rescue
    FunctionClauseError -> true
    ArgumentError -> true
  end

name = MixerHosted.Identity.InflightProdExcludedOwner
[{_, root, _}] = :public_key.pem_decode(File.read!(Path.join(__DIR__, "root.pem")))

options = [
  name: name,
  manifest: [%{
    profile: %{profile_id: "disabled", profile_version: 1, issuer: "https://issuer.fixture.invalid/oauth",
      audience: "mixer-api", client_id: "inflight-prod-exclusion", identity_class: :human, enabled: false},
    jwks_endpoint: %{host: "jwks.fixture.invalid", port: 443, path: "/keys"}, transport: :hosted_https
  }],
  generation: 1, binding: "disabled", ca_roots: [root], resolvers: [{{127, 0, 0, 1}, 9}],
  fixture: %{ip: {127, 0, 0, 1}, port: 9}
]

Process.flag(:trap_exit, true)
result = KeyOwnerSupervisor.start_link(options)
if match?({:ok, _}, result), do: Supervisor.stop(elem(result, 1), :normal, 1_000)

rejected = match?({:error, {:shutdown, {:failed_to_start_child, KeyOwner, :invalid_identity_configuration}}}, result)

observation = %{
  supervisor_fixture_export_absent: not function_exported?(KeyOwnerSupervisor, :start_fixture, 1),
  owner_fixture_export_absent: not function_exported?(KeyOwner, :start_fixture, 1),
  transport_fixture_export_absent: not function_exported?(JWKSTransport, :fetch_fixture, 6),
  fixture_tuple_init_rejected: tuple_rejected,
  ordinary_fixture_option_rejected: rejected,
  owner_absent: Process.whereis(name) == nil,
  workers_absent: Process.whereis(Module.concat(name, FetchSupervisor)) == nil,
  admission_absent: :persistent_term.get({Admission, name}, :absent) == :absent,
  loopback_denied: not MixerHosted.Identity.GlobalAddress.global?({127, 0, 0, 1}),
  product_application_not_started: not List.keymember?(Application.started_applications(), :mixer_hosted, 0)
}

File.write!(Path.join(evidence, "production-exclusion.json"), Jason.encode!(observation, pretty: true))
GenServer.stop(mix_state)
System.halt(if(Enum.all?(observation, fn {_, value} -> value == true end), do: 0, else: 1))
