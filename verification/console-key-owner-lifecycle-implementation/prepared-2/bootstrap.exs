# Corrected ordinary supervisor and Admission lifecycle tests; no Mix project or app.
%{mix_state: mix_state, test_source: test_source, evidence: evidence} =
  Code.eval_file(Path.join(__DIR__, "compile-common.exs")) |> elem(0)

ExUnit.start(autorun: false, seed: 0, max_cases: 1, timeout: 5_000, colors: [enabled: false])

case Kernel.ParallelCompiler.compile([test_source], return_diagnostics: true) do
  {:ok, [_module], %{runtime_warnings: [], compile_warnings: []} = warnings}
  when map_size(warnings) == 2 ->
    IO.puts("COMPILED 1 lifecycle test module; warnings=0")

  result ->
    IO.inspect(result, label: "TEST_COMPILE_REJECTED", limit: 50)
    System.halt(2)
end

result = ExUnit.run()
File.write!(Path.join(evidence, "exunit-result.json"), Jason.encode!(result, pretty: true))

observations = %{
  test_owners_absent:
    Enum.all?(MixerHosted.Identity.KeyOwnerLifecycleTest.owner_names(), &(Process.whereis(&1) == nil)),
  test_workers_absent:
    Enum.all?(MixerHosted.Identity.KeyOwnerLifecycleTest.owner_names(), fn name ->
      Process.whereis(Module.concat(name, FetchSupervisor)) == nil
    end),
  test_admission_absent:
    Enum.all?(MixerHosted.Identity.KeyOwnerLifecycleTest.admission_names(), fn name ->
      :persistent_term.get({MixerHosted.Identity.Admission, name}, :absent) == :absent
    end),
  default_owner_absent: Process.whereis(MixerHosted.Identity.KeyOwner) == nil,
  default_repo_absent: Process.whereis(MixerHosted.Repo) == nil,
  product_application_not_started:
    not List.keymember?(Application.started_applications(), :mixer_hosted, 0),
  cleanup_receipts: length(Path.wildcard(Path.join(evidence, "*-cleanup.json")))
}

File.write!(Path.join(evidence, "postconditions.json"), Jason.encode!(observations, pretty: true))
GenServer.stop(mix_state)
IO.puts("RESULT " <> Jason.encode!(result))

# Read-only formatting qualification for the three authored canonical files.
# hosted/.formatter.exs contains only inputs, so these are its default options.
for relative <- [
      "hosted/lib/mixer_hosted/identity/admission.ex",
      "hosted/lib/mixer_hosted/identity/key_owner.ex",
      "hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs"
    ] do
  path = Path.join(__DIR__, "inputs/" <> relative)
  original = File.read!(path)
  formatted = Code.format_string!(original, file: path) |> IO.iodata_to_binary()

  if original != formatted <> "\n",
    do: raise("read-only formatting equality failed: " <> relative)
end

IO.puts("FORMAT CHECK 3 authored canonical files; unchanged=3")

passed =
  result.total == 7 and result.failures == 0 and result.skipped == 0 and result.excluded == 0 and
    observations.cleanup_receipts == 7 and
    Enum.all?(Map.drop(observations, [:cleanup_receipts]), fn {_key, value} -> value == true end)

System.halt(if(passed, do: 0, else: 1))
