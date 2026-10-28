# Expected-defect control: exact preserved original production bytes, ordinary supervisor.
%{mix_state: mix_state, evidence: evidence} =
  Code.eval_file(Path.join(__DIR__, "compile-common.exs")) |> elem(0)

alias MixerHosted.Identity.{Admission, ConfiguredVerifier, KeyOwnerSupervisor}
name = MixerLifecycleOriginalOwner
workers = Module.concat(name, FetchSupervisor)
binding = "lifecycle-disabled"
entry = %{
  profile: %{
    profile_id: binding, profile_version: 1, issuer: "https://issuer.lifecycle.invalid/oauth",
    audience: "mixer-api", client_id: "lifecycle-test", identity_class: :human, enabled: false
  },
  jwks_endpoint: %{host: "jwks.lifecycle.invalid", port: 443, path: "/keys"},
  transport: :hosted_https
}
[{:Certificate, der, :not_encrypted}] =
  System.fetch_env!("MIXER_KEY_OWNER_LIFECYCLE_ROOT_PEM") |> File.read!() |> :public_key.pem_decode()

{:ok, component} = KeyOwnerSupervisor.start_link(
  name: name, manifest: [entry], generation: 1, binding: binding, ca_roots: [der],
  resolvers: [{{127, 0, 0, 1}, 9}]
)
Process.unlink(component)
owner = Process.whereis(name)
worker_pid = Process.whereis(workers)
state = :sys.get_state(owner)

try do
  {:trap_exit, false} = Process.info(owner, :trap_exit)
  {:ok, permit} = Admission.acquire(name, :configured)
  :ok = Admission.release(permit)
  0 = DynamicSupervisor.count_children(workers).active
  :ok = Supervisor.stop(component, :normal, 1_000)
  {:error, :identity_unavailable} = Admission.acquire(name, :configured)
  {:error, :identity_unavailable} =
    ConfiguredVerifier.authenticate(name, :configured, "synthetic", System.system_time(:second))

  observation = %{
    original_defect_reproduced:
      :persistent_term.get({Admission, name}, :absent) == state.table,
    component_stopped: not Process.alive?(component),
    owner_stopped: not Process.alive?(owner),
    workers_stopped: not Process.alive?(worker_pid),
    table_gone: :ets.info(state.table) == :undefined,
    public_denial: true,
    product_application_not_started:
      not List.keymember?(Application.started_applications(), :mixer_hosted, 0)
  }

  File.write!(Path.join(evidence, "original-regression.json"), Jason.encode!(observation))
  true = Enum.all?(observation, fn {_key, value} -> value == true end)
  IO.puts("ORIGINAL DEFECT REPRODUCED: graceful parent stop leaves a dead, fail-closed pointer")
after
  if Process.alive?(component), do: Supervisor.stop(component, :normal, 1_000)
  File.write!(Path.join(evidence, "original-cleanup.json"), Jason.encode!(%{
    component_stopped: not Process.alive?(component),
    owner_stopped: not Process.alive?(owner),
    workers_stopped: not Process.alive?(worker_pid),
    table_gone: :ets.info(state.table) == :undefined,
    dead_pointer_intentionally_retained_until_vm_exit:
      :persistent_term.get({Admission, name}, :absent) == state.table
  }))
end

GenServer.stop(mix_state)
System.halt(0)
