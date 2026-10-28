%{mix_state: mix_state, evidence: evidence} =
  Code.eval_file(Path.join(__DIR__, "compile-common.exs")) |> elem(0)

true = Mix.env() == :test
{:ok, _} = Application.ensure_all_started(:jose)
{:ok, _} = Application.ensure_all_started(:mint)
{:ok, _} = Application.ensure_all_started(:ssl)

# Read-only formatting runs before OpenSSL version or any TLS fixture.
files = [
  "hosted/lib/mixer_hosted/identity/admission.ex",
  "hosted/lib/mixer_hosted/identity/key_owner.ex",
  "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex",
  "hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs",
  "hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs"
]

formatted = Enum.all?(files, fn relative ->
  path = Path.join(__DIR__, "inputs/" <> relative)
  File.read!(path) == (Code.format_string!(File.read!(path), file: path) |> IO.iodata_to_binary()) <> "\n"
end)

File.write!(Path.join(evidence, "format-check.json"), Jason.encode!(%{total: 5, unchanged: formatted}))
if not formatted, do: raise("read-only formatting equality failed; use separately released format-only plan")

{version, 0} = System.cmd("openssl", ["version"], stderr_to_stdout: true)
File.write!(Path.join(evidence, "openssl-version.json"), Jason.encode!(%{output: String.trim(version), exit_code: 0}))

ExUnit.start(autorun: false, seed: 0, max_cases: 1, timeout: 10_000, colors: [enabled: false])

test_sources = [
  "hosted/test/support/identity_tls_fixture.ex",
  "hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs",
  "hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs"
] |> Enum.map(&Path.join(__DIR__, "inputs/" <> &1))

case Kernel.ParallelCompiler.compile(test_sources, return_diagnostics: true) do
  {:ok, modules, %{runtime_warnings: [], compile_warnings: []} = warnings}
  when map_size(warnings) == 2 and length(modules) == 4 ->
    IO.puts("COMPILED 4 fixture/test modules; warnings=0; nine methods")

  result ->
    IO.inspect(result, label: "TEST_COMPILE_REJECTED", limit: 50)
    System.halt(2)
end

result = ExUnit.run()
File.write!(Path.join(evidence, "exunit-result.json"), Jason.encode!(result, pretty: true))

names = MixerHosted.Identity.KeyOwnerLifecycleTest.owner_names() ++ MixerHosted.Identity.KeyOwnerInflightLifecycleTest.owner_names()
admission_names = MixerHosted.Identity.KeyOwnerLifecycleTest.admission_names() ++ MixerHosted.Identity.KeyOwnerInflightLifecycleTest.owner_names()

observations = %{
  test_owners_absent: Enum.all?(names, &(Process.whereis(&1) == nil)),
  test_workers_absent: Enum.all?(names, &(Process.whereis(Module.concat(&1, FetchSupervisor)) == nil)),
  test_admission_absent: Enum.all?(admission_names, &(:persistent_term.get({MixerHosted.Identity.Admission, &1}, :absent) == :absent)),
  default_owner_absent: Process.whereis(MixerHosted.Identity.KeyOwner) == nil,
  default_repo_absent: Process.whereis(MixerHosted.Repo) == nil,
  product_application_not_started: not List.keymember?(Application.started_applications(), :mixer_hosted, 0),
  ordinary_cleanup_receipts: length(Path.wildcard(Path.join(evidence, "*-cleanup.json"))),
  inflight_observation_receipts: length(Path.wildcard(Path.join(evidence, "KOL*-observation.json")))
}

File.write!(Path.join(evidence, "postconditions.json"), Jason.encode!(observations, pretty: true))
calls = File.read!(System.fetch_env!("MIXER_OPENSSL_AUDIT")) |> String.split("\n", trim: true) |> Enum.map(&Jason.decode!/1)
starts = File.read!(System.fetch_env!("MIXER_OPENSSL_STARTED")) |> String.split("\n", trim: true) |> Enum.map(&Jason.decode!/1)
File.write!(Path.join(evidence, "openssl-invocations.json"), Jason.encode!(%{starts: starts, invocations: calls}, pretty: true))
GenServer.stop(mix_state)
IO.puts("RESULT " <> Jason.encode!(result))

passed = result.total == 9 and result.failures == 0 and result.skipped == 0 and result.excluded == 0 and
  observations.ordinary_cleanup_receipts == 7 and observations.inflight_observation_receipts == 2 and
  Enum.all?(Map.drop(observations, [:ordinary_cleanup_receipts, :inflight_observation_receipts]), fn {_, value} -> value == true end)

System.halt(if(passed, do: 0, else: 1))
