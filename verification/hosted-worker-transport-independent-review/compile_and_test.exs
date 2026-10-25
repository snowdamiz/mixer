{:ok, _} = Mix.State.start_link([])
Mix.env(:test)
Application.ensure_all_started(:ssl)
Application.ensure_all_started(:mint)
Application.ensure_all_started(:jason)
here = Path.dirname(__ENV__.file)
candidate = Path.join(here, "inputs/verification/hosted-worker-transport/candidate")
mode = hd(System.argv())
build = Path.join(here, "build/" <> mode)
File.mkdir_p!(build)
files = Path.wildcard(Path.join(candidate, "context/**/*.ex")) ++ Path.wildcard(Path.join(candidate, "lib/**/*.ex"))
true = length(files) == 10
compiled = case Kernel.ParallelCompiler.compile_to_path(files, build, return_diagnostics: true) do
  {:ok, modules, %{compile_warnings: [], runtime_warnings: []}} -> modules
  _ -> System.halt(1)
end
Code.prepend_path(build)
Code.require_file(Path.join(candidate, "test/support/worker_tls_fixture.ex"))
ExUnit.start(autorun: false, seed: 0, capture_log: true, trace: mode == "independent", timeout: 10_000)
if mode == "baseline" do
  Path.wildcard(Path.join(candidate, "test/mixer_hosted/builds/*_test.exs")) |> Enum.each(&Code.require_file/1)
else
  Code.require_file(Path.join(here, "independent_tls_fixture.exs"))
  Code.require_file(Path.join(here, "independent_test.exs"))
end
result = ExUnit.run()
frozen = Enum.filter(:code.all_loaded(), fn {m, _} ->
  name = Atom.to_string(m)
  String.contains?(name, "Authority") or String.contains?(name, "Catalog")
end) |> Enum.map(fn {m, _} -> Atom.to_string(m) end)
true = frozen == []
allowed = Enum.map(compiled, &Atom.to_string/1) ++ ~w(Elixir.MixerHosted.Test.WorkerTLSFixture Elixir.MixerHosted.Test.WorkerData Elixir.MixerHosted.Builds.WorkerConfigTest Elixir.MixerHosted.Builds.WorkerWireTest Elixir.MixerHosted.Builds.WorkerTransportTest)
loaded = Enum.filter(:code.all_loaded(), fn {m, _} -> String.starts_with?(Atom.to_string(m), "Elixir.MixerHosted.") end) |> Enum.map(fn {m, _} -> Atom.to_string(m) end) |> Enum.sort()
true = loaded -- allowed == []
IO.puts(Jason.encode!(%{scope: "isolated-frozen-worker-client-" <> mode, tests: result.total, failures: result.failures, skipped: result.skipped, excluded: result.excluded, frozen_modules_loaded: frozen, loaded_mixer_modules: loaded}))
System.halt(if result.failures == 0, do: 0, else: 1)
