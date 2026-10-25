{:ok, _} = Mix.State.start_link([])
Mix.env(:prod)
root = Path.dirname(__ENV__.file)
build = Path.join(root, "build/prod")
File.mkdir_p!(build)

files =
  Path.wildcard(Path.join(root, "candidate/context/**/*.ex")) ++
    Path.wildcard(Path.join(root, "candidate/lib/**/*.ex"))

case Kernel.ParallelCompiler.compile_to_path(files, build, return_diagnostics: true) do
  {:ok, modules, %{compile_warnings: [], runtime_warnings: []}} ->
    false = Enum.any?(modules, &String.contains?(Atom.to_string(&1), ".Test."))

  _ ->
    System.halt(1)
end

Code.prepend_path(build)
module = MixerHosted.Builds.WorkerTransport
Code.ensure_loaded!(module)
false = function_exported?(module, :start_fixture, 3)

exports =
  Map.new(
    [
      MixerHosted.Builds.WorkerConfig,
      MixerHosted.Builds.WorkerWire,
      MixerHosted.Builds.WorkerTransport,
      MixerHosted.Builds.WorkerTransport.RoleGuard,
      MixerHosted.Builds.WorkerTransport.Flight,
      MixerHosted.Builds.WorkerHTTPAdapter
    ],
    fn m ->
      Code.ensure_loaded!(m)

      {Atom.to_string(m),
       Enum.map(m.__info__(:functions), fn {f, n} -> [Atom.to_string(f), n] end)}
    end
  )

frozen =
  Enum.filter(:code.all_loaded(), fn {m, _} ->
    name = Atom.to_string(m)
    String.contains?(name, "Authority") or String.contains?(name, "Catalog")
  end)

[] = frozen

IO.puts(
  Jason.encode!(%{
    scope: "isolated-production-compile-and-export-check-not-full-release",
    fixture_start_absent: true,
    test_helpers_not_compiled: true,
    frozen_modules_loaded: [],
    exports: exports
  })
)
