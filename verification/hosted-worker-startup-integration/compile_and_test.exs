{:ok, _} = Mix.State.start_link([])
Mix.env(:prod)
Application.ensure_all_started(:ssl)
Application.ensure_all_started(:mint)
Application.ensure_all_started(:jason)

base = __DIR__
build = Path.join(base, "build")
File.mkdir_p!(build)

# This isolated collection deliberately does not compile/start the HTTP endpoint,
# database, Oban or identity owners. The only excluded call is config_change/2;
# all startup configuration and transport code below is the actual candidate.
Code.compiler_options(no_warn_undefined: [{MixerHostedWeb.Endpoint, :config_change, 2}])

files =
  Path.wildcard(Path.join(base, "context/**/*.ex")) ++
    Path.wildcard(Path.join(base, "transport/candidate/context/**/*.ex")) ++
    Path.wildcard(Path.join(base, "transport/candidate/lib/**/*.ex")) ++
    Path.wildcard(Path.join(base, "candidate/hosted/lib/**/*.ex"))

case Kernel.ParallelCompiler.compile_to_path(files, build, return_diagnostics: true) do
  {:ok, _, %{compile_warnings: [], runtime_warnings: []}} ->
    :ok

  result ->
    IO.inspect(result, label: "compilation_failure")
    System.halt(1)
end

Code.prepend_path(build)
ExUnit.start(autorun: false, seed: 0, capture_log: true)
Code.require_file(Path.join(base, "context/runtime_config_test.exs"))
Code.require_file(Path.join(base, "startup_test.exs"))
result = ExUnit.run()

forbidden =
  Enum.filter(:code.all_loaded(), fn {m, _} ->
    name = Atom.to_string(m)
    String.contains?(name, "Authority") or String.contains?(name, "Catalog")
  end)
  |> Enum.map(fn {m, _} -> Atom.to_string(m) end)

facts = %{
  scope: "isolated-production-startup-config-and-transport-supervision",
  tests: result.total,
  failures: result.failures,
  skipped: result.skipped,
  excluded: result.excluded,
  frozen_modules_loaded: forbidden,
  fixture_start_absent:
    not function_exported?(MixerHosted.Builds.WorkerTransport, :start_fixture, 3),
  actual_full_application_started: false,
  actual_oban_or_database_started: false,
  identity_owner_or_endpoint_started: false,
  transport_owner_gone: Process.whereis(MixerHosted.Builds.WorkerTransport) == nil,
  transport_guard_gone: Process.whereis(MixerHosted.Builds.WorkerTransport.RoleGuard) == nil,
  generation_marker_absent:
    :persistent_term.get({MixerHosted.Builds.WorkerTransport, :ownership_v2}, :absent) == :absent
}

IO.puts(Jason.encode!(facts))

System.halt(
  if result.failures == 0 and forbidden == [] and facts.fixture_start_absent and
       facts.transport_owner_gone and facts.transport_guard_gone and
       facts.generation_marker_absent, do: 0, else: 1
)
