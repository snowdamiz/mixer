# Test-only entry point for the ordinary loopback replay.
alias MixerHosted.{Repo, RuntimeConfig}
alias MixerHosted.Builds.ProcessorAdmission

root = System.fetch_env!("MIXER_L07_ROOT")
true = System.fetch_env!("MIXER_L07_REPLAY") in ["full", "fixture"]
settings = RuntimeConfig.load!(System.get_env())
true = settings.role == :processor and settings.processor_profile == :builds_v1
true = settings.build_operation_intent == :durable_intent_v1
true = settings.repo[:hostname] == "127.0.0.1"
true = settings.repo[:database] == "browser_ordinary_installation_r1422"

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

%{rows: [["mixer_build_processor", false, false, true, false]]} =
  Repo.query!("""
  SELECT current_user::text, rolsuper, rolbypassrls,
    has_function_privilege(current_user, 'public.mixer_build_operation_intent_v1(text,text,bytea,bytea,bigint,uuid,bigint,bigint,text,timestamptz,jsonb,jsonb)', 'EXECUTE'),
    has_table_privilege(current_user, 'public.mixer_build_operation_admissions', 'SELECT')
  FROM pg_roles WHERE rolname=current_user
  """)

pause = fn again, attempts ->
  case Oban.pause_queue(queue: :builds, local_only: true) do
    :ok ->
      :ok

    {:error, %RuntimeError{message: "processor notifier is not admitted and ready"}}
    when attempts > 0 ->
      Process.sleep(100)
      again.(again, attempts - 1)

    error ->
      raise "restricted Oban pause failed: #{inspect(error)}"
  end
end

:ok = pause.(pause, 75)

await_pause = fn again, attempts ->
  case Oban.check_queue(queue: :builds) do
    %{paused: true} ->
      :ok

    _ when attempts == 0 ->
      raise "builds queue did not acknowledge pause"

    _ ->
      Process.sleep(50)
      again.(again, attempts - 1)
  end
end

:ok = await_pause.(await_pause, 80)
ready = %{role: "mixer_build_processor", queue: "builds", durableIntent: true, paused: true}
path = Path.join(root, "processor.ready")
File.write!(path <> ".tmp", Jason.encode!(ready), [:exclusive])
File.rename!(path <> ".tmp", path)

wait = fn again, resumed ->
  cond do
    File.regular?(Path.join(root, "processor.done")) ->
      :ok

    not resumed and File.regular?(Path.join(root, "processor.run")) ->
      "full" = System.fetch_env!("MIXER_L07_REPLAY")
      :ok = Oban.resume_queue(queue: :builds, local_only: true)
      again.(again, true)

    true ->
      Process.sleep(50)
      again.(again, resumed)
  end
end

wait.(wait, false)
:ok = Application.stop(:mixer_hosted)
