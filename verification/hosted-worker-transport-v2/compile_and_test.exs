{:ok, _} = Mix.State.start_link([])
Mix.env(:test)
Application.ensure_all_started(:ssl)
Application.ensure_all_started(:mint)
Application.ensure_all_started(:jason)
root = Path.dirname(__ENV__.file)
build = Path.join(root, "build/test")
File.mkdir_p!(build)

files =
  Path.wildcard(Path.join(root, "candidate/context/**/*.ex")) ++
    Path.wildcard(Path.join(root, "candidate/lib/**/*.ex"))

case Kernel.ParallelCompiler.compile_to_path(files, build, return_diagnostics: true) do
  {:ok, _, %{compile_warnings: [], runtime_warnings: []}} -> :ok
  _ -> System.halt(1)
end

Code.prepend_path(build)
Code.require_file(Path.join(root, "candidate/test/support/worker_tls_fixture.ex"))
ExUnit.start(autorun: false, seed: 0, capture_log: true)

case System.argv() do
  [] ->
    Path.wildcard(Path.join(root, "candidate/test/mixer_hosted/builds/*_test.exs"))
    |> Enum.each(&Code.require_file/1)

  ["fault", name] ->
    allowed = Path.wildcard(Path.join(root, "candidate/test/fault_cases/*_test.exs"))
    selected = Path.join(root, "candidate/test/fault_cases/" <> name <> "_test.exs")
    if selected not in allowed, do: System.halt(2)
    Code.require_file(Path.join(root, "candidate/test/support/worker_v2_case.exs"))
    Code.require_file(selected)

  _ ->
    System.halt(2)
end

result = ExUnit.run()

IO.puts(
  Jason.encode!(%{
    scope: "isolated-client-candidate-real-synthetic-TLS-only",
    tests: result.total,
    failures: result.failures,
    skipped: result.skipped,
    excluded: result.excluded,
    frozen_modules_loaded:
      Enum.filter(:code.all_loaded(), fn {m, _} ->
        name = Atom.to_string(m)
        String.contains?(name, "Authority") or String.contains?(name, "Catalog")
      end)
      |> Enum.map(fn {m, _} -> Atom.to_string(m) end)
  })
)

System.halt(if result.failures == 0, do: 0, else: 1)
