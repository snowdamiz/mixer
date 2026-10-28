# Standalone closure shared only by the two exact lifecycle processes.
true = System.version() == "1.20.4"
true = System.otp_release() == "29"
{:ok, mix_state} = Mix.State.start_link([])
true = Mix.env() == :test
[source_manifest, test_source, compile_output, dependency_manifest] = System.argv()
sources = File.read!(source_manifest) |> Jason.decode!()
18 = length(sources)
false = Enum.any?(:code.get_path(), &String.contains?(to_string(&1), "_build"))

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

{:ok, _} = Application.ensure_all_started(:public_key)
evidence = System.fetch_env!("MIXER_KEY_OWNER_LIFECYCLE_EVIDENCE")
File.write!(Path.join(evidence, "runtime.json"), Jason.encode!(%{
  elixir: System.version(),
  otp_release: System.otp_release(),
  node: Atom.to_string(node()),
  schedulers_online: :erlang.system_info(:schedulers_online),
  product_application_started: List.keymember?(Application.started_applications(), :mixer_hosted, 0)
}))

case Kernel.ParallelCompiler.compile_to_path(sources, compile_output, return_diagnostics: true) do
  {:ok, modules, %{runtime_warnings: [], compile_warnings: []} = warnings}
  when map_size(warnings) == 2 and length(modules) == 19 ->
    IO.puts("COMPILED 19 ordinary identity modules; warnings=0")

  result ->
    IO.inspect(result, label: "ORDINARY_COMPILE_REJECTED", limit: 50)
    System.halt(2)
end

true = is_nil(Process.whereis(MixerHosted.Identity.KeyOwner))
%{mix_state: mix_state, test_source: test_source, evidence: evidence}
