# Standalone frozen-input runner. No Mix project, application, router or endpoint.
true = System.version() == "1.20.4"
true = System.otp_release() == "29"
{:ok, mix_state} = Mix.State.start_link([])
true = Mix.env() == :test
[source_manifest, test_source, compile_output, dependency_manifest] = System.argv()
sources = File.read!(source_manifest) |> Jason.decode!()
false = Enum.any?(:code.get_path(), &String.contains?(to_string(&1), "_build"))
for %{"name" => name, "version" => version, "ebin" => ebin} <- File.read!(dependency_manifest) |> Jason.decode!() do
  app = String.to_atom(name)
  :ok = Application.load(app)
  true = to_string(Application.spec(app, :vsn)) == version
  for file <- Path.wildcard(Path.join(ebin, "*.beam")) do
    {:ok, {module, _}} = :beam_lib.chunks(String.to_charlist(file), [:exports])
    false = String.starts_with?(Atom.to_string(module), "Elixir.MixerHosted")
  end
end
Application.put_env(:jose, :json_module, :jose_json_jason)
Application.put_env(:jose, :unsecured_signing, false)
Application.put_env(:jose, :crypto_fallback, false)
Logger.configure(level: :warning)
case Kernel.ParallelCompiler.compile_to_path(sources, compile_output, return_diagnostics: true) do
  {:ok, modules, %{runtime_warnings: [], compile_warnings: []} = warnings} when map_size(warnings) == 2 ->
    IO.puts("COMPILED " <> Integer.to_string(length(modules)) <> " frozen ordinary modules; warnings=0")
  _ ->
    IO.puts("COMPILE_REJECTED")
    System.halt(2)
end
true = is_nil(Process.whereis(MixerHosted.Repo))
true = is_nil(Process.whereis(MixerHosted.Identity.KeyOwner))
ExUnit.start(autorun: false, seed: 0, max_cases: 1, timeout: 10_000, colors: [enabled: false])
Code.require_file(test_source)
result = ExUnit.run()
true = is_nil(Process.whereis(MixerHosted.Repo))
true = is_nil(Process.whereis(MixerHosted.Identity.KeyOwner))
:absent = :persistent_term.get({MixerHosted.Identity.Admission, MixerHosted.Identity.KeyOwner}, :absent)
false = List.keymember?(Application.started_applications(), :mixer_hosted, 0)
File.write!(Path.join(System.fetch_env!("MIXER_DISPATCHER_DEFAULT_EVIDENCE"), "exunit-result.json"), Jason.encode!(result, pretty: true))
GenServer.stop(mix_state)
IO.puts("RESULT " <> Jason.encode!(result))
System.halt(if(result.total == 7 and result.failures == 0 and result.skipped == 0 and result.excluded == 0, do: 0, else: 1))
