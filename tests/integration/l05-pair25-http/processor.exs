# Fixture only. Boot the stock restricted processor and drain one job under pause.
alias MixerHosted.{Repo, RuntimeConfig}
alias MixerHosted.Builds.{Dispatch, ProcessorAdmission, Storage}

root = System.fetch_env!("PAIR25_RUN")
path = &Path.join(root, &1)

publish = fn name, data ->
  File.write!(path.(name <> ".tmp"), Jason.encode!(data), [:exclusive])
  File.rename!(path.(name <> ".tmp"), path.(name))
end

settings = RuntimeConfig.load!(System.get_env())
true = settings.role == :processor and settings.processor_profile == :builds_v1
true = settings.build_operation_intent == :durable_intent_v1
true = settings.repo[:hostname] == "127.0.0.1"
true = settings.repo[:database] == "browser_ordinary_installation_r1422"
true = settings.repo[:username] == "mixer_build_processor"

repo =
  Keyword.merge(settings.repo,
    port: String.to_integer(System.fetch_env!("MIXER_BROWSER_STORAGE_PORT")),
    ssl: false
  )

settings = %{settings | repo: repo}

for {key, value} <- [
      {:startup, {settings, :disabled}},
      {:role, settings.role},
      {:identity_startup, settings.identity_startup},
      {Repo, repo},
      {Oban, settings.oban},
      {MixerHostedWeb.Endpoint, settings.endpoint}
    ],
    do: Application.put_env(:mixer_hosted, key, value)

{:ok, _} = Application.ensure_all_started(:mixer_hosted)

{:ok, :ok} =
  Repo.transaction(fn ->
    ProcessorAdmission.check!(fn sql, args -> Repo.query!(sql, args).rows end, :required)
  end)

%{rows: [["mixer_build_processor", false, false]]} =
  Repo.query!(
    "SELECT current_user::text, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"
  )

await = fn again, fun, end_ms ->
  case fun.() do
    nil ->
      true = System.monotonic_time(:millisecond) < end_ms
      Process.sleep(50)
      again.(again, fun, end_ms)

    result ->
      result
  end
end

wait = fn fun, ms -> await.(await, fun, System.monotonic_time(:millisecond) + ms) end

try do
  :ok =
    wait.(
      fn ->
        case Oban.pause_queue(queue: :builds, local_only: true) do
          :ok -> :ok
          {:error, %RuntimeError{message: "processor notifier is not admitted and ready"}} -> nil
        end
      end,
      8_000
    )

  true =
    wait.(
      fn ->
        if match?(%{paused: true, running: []}, Oban.check_queue(queue: :builds)), do: true
      end,
      5_000
    )

  publish.("processor.ready", %{role: settings.repo[:username], paused: true})

  command = fn name ->
    wait.(
      fn ->
        cond do
          File.regular?(path.("processor.done")) -> :done
          File.regular?(path.(name)) -> :go
          true -> nil
        end
      end,
      1_250_000
    )
  end

  if command.("build.selection") == :go do
    scope = path.("build.selection") |> File.read!() |> Jason.decode!()
    %{"platform" => "android"} = scope

    if System.get_env("PAIR25_BROWSER") do
      %{"created_job_id" => job_id} = scope
      true = is_integer(job_id) and job_id > 0
      %{paused: true, running: []} = Oban.check_queue(queue: :builds)

      %{rows: [[^job_id, "created", "available", 0]]} =
        Repo.query!("SELECT id, args->>'kind', state::text, attempt FROM oban_jobs")
    end

    scope =
      for key <- ~w(organization_id project_id application_id build_id)a,
          into: %{platform: :android},
          do: {key, Map.fetch!(scope, Atom.to_string(key))}

    %{success: 1, failure: 0, snoozed: 0} =
      Oban.drain_queue(queue: :builds, with_limit: 1, with_recursion: false, with_safety: false)

    %{paused: true, running: []} = Oban.check_queue(queue: :builds)

    {:ok, %{record: %{id: record, revision: 1}, build: %{state: :running} = build}} =
      Storage.read(scope)

    %{rows: [["created", "completed", 1], ["start", "available", 0]]} =
      Repo.query!("SELECT args->>'kind', state::text, attempt FROM oban_jobs ORDER BY id")

    publish.("build.binding", %{
      record_id: record,
      operation_id: Dispatch.operation_id(record, build.active_ref),
      ref: Map.from_struct(build.active_ref),
      spec: Map.from_struct(build.spec),
      deadline_ms: build.deadline,
      started_at_ms: build.started_at
    })

    if command.("processor.run") == :go do
      :ok = Oban.resume_queue(queue: :builds, local_only: true)
      :done = command.("processor.done")
    end
  end
after
  :ok = Application.stop(:mixer_hosted)
end
