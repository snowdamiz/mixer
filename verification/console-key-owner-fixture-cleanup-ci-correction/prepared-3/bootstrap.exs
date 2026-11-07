# Full canonical test module; exactly seven named methods execute in one host VM.
true = System.version() == "1.20.4"
true = System.otp_release() == "29"
{:ok, mix_state} = Mix.State.start_link([])
true = Mix.env() == :test
[source_manifest, test_source, compile_output, dependency_manifest] = System.argv()
evidence = System.fetch_env!("MIXER_KEY_OWNER_FIXTURE_EVIDENCE")
write = fn name, value -> File.write!(Path.join(evidence, name), Jason.encode!(value)) end

for %{"name" => name, "version" => version, "ebin" => ebin} <-
      File.read!(dependency_manifest) |> Jason.decode!() do
  app = String.to_atom(name)
  :ok = Application.load(app)
  true = to_string(Application.spec(app, :vsn)) == version

  for file <- Path.wildcard(Path.join(ebin, "*.beam")) do
    {:ok, {module, _}} = :beam_lib.chunks(String.to_charlist(file), [:exports])
    false = String.starts_with?(Atom.to_string(module), "Elixir.MixerHosted")
  end
end

false = Enum.any?(:code.get_path(), &String.contains?(to_string(&1), "_build"))
write.("runtime.json", %{
  elixir: System.version(),
  otp_release: System.otp_release(),
  node: Atom.to_string(node()),
  schedulers_online: :erlang.system_info(:schedulers_online),
  product_application_started: List.keymember?(Application.started_applications(), :mixer_hosted, 0)
})

{openssl_version, 0} = System.cmd("openssl", ["version"], stderr_to_stdout: true)
true = String.starts_with?(openssl_version, "OpenSSL 3.6.5 ")
IO.write(openssl_version)

sources = File.read!(source_manifest) |> Jason.decode!()
18 = length(sources)

case Kernel.ParallelCompiler.compile_to_path(sources, compile_output, return_diagnostics: true) do
  {:ok, modules, %{runtime_warnings: [], compile_warnings: []} = warnings}
  when map_size(warnings) == 2 and length(modules) == 19 ->
    IO.puts("COMPILED 19 frozen accepted identity modules; warnings=0")

  result ->
    IO.inspect(result, label: "PRODUCT_COMPILE_REJECTED", limit: 50)
    System.halt(2)
end

support =
  Enum.map(
    ["identity_tls_fixture.ex", "identity_raw_fixture.ex", "identity_dns_fixture.ex", "identity_socket_probe.ex"],
    &Path.join(__DIR__, "inputs/hosted/test/support/" <> &1)
  )

case Kernel.ParallelCompiler.compile(support, return_diagnostics: true) do
  {:ok, modules, %{runtime_warnings: [], compile_warnings: []} = warnings}
  when map_size(warnings) == 2 and length(modules) == 4 ->
    IO.puts("COMPILED 4 frozen canonical support modules; warnings=0")

  result ->
    IO.inspect(result, label: "SUPPORT_COMPILE_REJECTED", limit: 50)
    System.halt(2)
end

selected = [
  :"test K01 manifest limits and immutable identity transitions",
  :"test K08 cold storm single flight, admission and FIFO negative cache",
  :"test K08b eight configured profiles cannot open a fifth owned flight",
  :"test K09 actual HTTPS rotation and invalid-candidate retention",
  :"test K01b all-or-nothing versioned replacement and bounded churn tombstones",
  :"test K01 lifetime identity history survives expired cooldown tombstones",
  :"test K07g owner shutdown waits for suspended TLS controller cleanup"
]

ExUnit.start(
  autorun: false,
  seed: 0,
  max_cases: 1,
  timeout: 8_000,
  colors: [enabled: false],
  exclude: [:test],
  include: Enum.map(selected, &{:test, &1})
)

case Kernel.ParallelCompiler.compile([test_source], return_diagnostics: true) do
  {:ok, [MixerHosted.Identity.KeyOwnerTest], %{runtime_warnings: [], compile_warnings: []} = warnings}
  when map_size(warnings) == 2 ->
    IO.puts("COMPILED 1 full canonical KeyOwnerTest module; warnings=0")

  result ->
    IO.inspect(result, label: "TEST_COMPILE_REJECTED", limit: 50)
    System.halt(2)
end

tests = MixerHosted.Identity.KeyOwnerTest.__ex_unit__().tests
29 = length(tests)
7 = length(selected)
true = length(Enum.uniq(selected)) == 7
true = Enum.all?(selected, fn name -> Enum.count(tests, &(&1.name == name)) == 1 end)
true = Enum.all?(tests, &(&1.tags.test == &1.name))
result = ExUnit.run()
write.("exunit-result.json", result)

selection = %{
  compiled_methods: length(tests),
  selected_methods: length(selected),
  unselected_methods: 22,
  executed_methods: result.total - result.excluded - result.skipped,
  exact_names_present_once: true,
  selection_is_full_suite: false
}

write.("selection.json", selection)

owner = TestKeyOwner
workers = Module.concat(owner, Workers)
observations = %{
  fixture_owner_absent: Process.whereis(owner) == nil,
  fixture_workers_absent: Process.whereis(workers) == nil,
  fixture_admission_absent:
    :persistent_term.get({MixerHosted.Identity.Admission, owner}, :absent) == :absent,
  default_owner_absent: Process.whereis(MixerHosted.Identity.KeyOwner) == nil,
  default_repo_absent: Process.whereis(MixerHosted.Repo) == nil,
  product_application_not_started:
    not List.keymember?(Application.started_applications(), :mixer_hosted, 0),
  ephemeral_fixture_key_directories_removed:
    Path.wildcard(Path.join(System.tmp_dir!(), "mixer-key-owner-tls-*")) == []
}

write.("postconditions.json", observations)
original = File.read!(test_source)
formatted = Code.format_string!(original, file: test_source) |> IO.iodata_to_binary()
true = original == formatted <> "\n"
IO.puts("FORMAT CHECK canonical KeyOwnerTest; unchanged=true")
GenServer.stop(mix_state)
IO.puts("RESULT " <> Jason.encode!(result))

passed =
  result.total == 29 and result.failures == 0 and result.skipped == 0 and result.excluded == 22 and
    selection.executed_methods == 7 and Enum.all?(observations, fn {_, value} -> value == true end)

System.halt(if(passed, do: 0, else: 1))
