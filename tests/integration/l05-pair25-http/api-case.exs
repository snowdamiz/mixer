# Included in the pinned LocalStarterHTTPSQLTest module by run.py. Reuse its private HTTP helpers.
@tag :pair25_http
@tag timeout: 1_300_000
test "serve one ordinary Android build for the Pair25 fixture", c do
  owner = login(c)
  org = create(c, owner, "/console-api/v1/orgs", %{display_name: "Pair25 owner"})
  scope = register_app(c, owner, org, "Pair25 project")
  outsider = pair25_outsider(c)
  other_org = create(c, outsider, "/console-api/v1/orgs", %{display_name: "Pair25 outsider"})
  assert org != other_org
  register_app(c, outsider, other_org, "Other project")

  pins =
    Path.join(System.fetch_env!("PAIR25_RUN"), "inputs.json") |> File.read!() |> Jason.decode!()

  source = pins["source_tree_sha256"]
  reference = "starter-" <> source

  {build, starter} =
    cond do
      System.get_env("PAIR25_BROWSER") ->
        assert RuntimeOwner.status().phase == :storage_ready
        assert c.hosted.oban[:queues] == false
        pair25_register_starter!(c, owner, scope, pins, reference)

      System.get_env("PAIR25_SELECT_STARTER") == "1" ->
        pair25_select_starter!(c, owner, outsider, scope, pins, reference)

      true ->
        {pair25_seed_input!(scope, pins, reference), nil}
    end

  {cookie, csrf} = login(c)

  pair25_publish!("api.ready", %{
    port: c.http_port,
    issuer: c.provider_port,
    jwks: GenServer.call(c.fixture, :authority).port,
    origin: c.config.public_origin,
    build: build,
    source_reference: reference,
    starter: starter,
    cookie: cookie,
    csrf: csrf
  })

  pair25_wait!(c, false, System.monotonic_time(:millisecond) + 1_240_000)
end

defp pair25_seed_input!(scope, pins, reference) do
  source = pins["source_tree_sha256"]
  lock = pins["linux_lock_sha256"]
  recipe = pins["recipe_sha256"]
  input = "pair25-" <> source

  assert %{num_rows: 1} =
           DB.q!(
             Migration,
             """
             INSERT INTO public.mixer_customer_build_inputs
               (organization_id,project_id,application_id,platform,input_id,source_kind,
                source_reference,source_sha256,toolchain_lock_sha256,build_definition_sha256,
                max_attempts,timeout_ms,retry_backoff_ms)
             VALUES($1,$2,$3,'android',$4,'revision',$5,$6,$7,$8,1,1200000,0)
             """,
             [
               scope.organization_id,
               scope.project_id,
               scope.application_id,
               input,
               reference,
               source,
               lock,
               recipe
             ]
           )

  Map.merge(scope, %{
    platform: "android",
    source_input_id: input,
    source_sha256: source,
    toolchain_lock_sha256: lock,
    build_definition_sha256: recipe
  })
end

defp pair25_register_starter!(c, owner, scope, pins, reference) do
  [migration] = Path.wildcard("priv/local_managed_linux_source_selection/20261120000000_*.exs")
  [{module, _}] = Code.require_file(migration)
  assert :ok = Ecto.Migrator.up(Migration, 20_261_120_000_000, module, log: false)
  assert input_rows() == []

  spec =
    Map.merge(stringify(scope), %{
      "platform" => "android",
      "source" => %{
        "kind" => "revision",
        "reference" => reference,
        "sha256" => pins["source_tree_sha256"]
      },
      "toolchain_lock_sha256" => pins["linux_lock_sha256"],
      "build_definition_sha256" => pins["recipe_sha256"]
    })

  profile = "managed-linux-pair25-v1"

  manifest = %{
    "profile" => profile,
    "spec" => spec,
    "projection_sha256" => pins["projection_sha256"],
    "rendered_driver_sha256" => pins["rendered_driver_sha256"]
  }

  raw = Jason.encode!(manifest)
  pin = sha256(raw)
  id = "starter-" <> pin
  path = pair25_path("starter-registration.json")
  File.write!(path, raw, [:exclusive])
  File.chmod!(path, 0o400)

  settings =
    LocalStarter.runtime_config!(%{
      "MIXER_LOCAL_STARTER_PROFILE" => profile,
      "MIXER_LOCAL_STARTER_ORGANIZATION" => scope.organization_id,
      "MIXER_LOCAL_STARTER_PROJECT" => scope.project_id,
      "MIXER_LOCAL_STARTER_APPLICATION" => scope.application_id,
      "MIXER_LOCAL_STARTER_REGISTRATION" => path,
      "MIXER_LOCAL_STARTER_SHA256" => pin
    })

  Application.put_env(:mixer_hosted, LocalStarter, settings)
  assert starter_list(c, owner, scope) == Map.put(public_scope(scope), "starter", nil)

  assert %{num_rows: 1} =
           DB.q!(
             Migration,
             """
             INSERT INTO public.mixer_managed_linux_pair25_starters
               (organization_id, project_id, application_id, input_id, registration_pin, spec,
                projection_sha256, rendered_driver_sha256)
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
             """,
             [
               scope.organization_id,
               scope.project_id,
               scope.application_id,
               id,
               pin,
               spec,
               manifest["projection_sha256"],
               manifest["rendered_driver_sha256"]
             ]
           )

  assert starter_list(c, owner, scope) == Map.put(public_scope(scope), "starter", %{"id" => id})
  assert input_rows() == []

  build =
    Map.merge(scope, %{
      platform: "android",
      source_input_id: id,
      source_sha256: pins["source_tree_sha256"],
      toolchain_lock_sha256: pins["linux_lock_sha256"],
      build_definition_sha256: pins["recipe_sha256"]
    })

  {build,
   %{
     id: id,
     manifest_sha256: pin,
     projection_sha256: manifest["projection_sha256"],
     rendered_driver_sha256: manifest["rendered_driver_sha256"]
   }}
end

defp pair25_select_starter!(c, owner, outsider, scope, pins, reference) do
  {expected, registration} = pair25_register_starter!(c, owner, scope, pins, reference)
  id = registration.id
  payload = Map.put(scope, :starter_id, id)
  assert post(c, outsider, @starters, payload).status == 404
  assert post(c, owner, @starters, %{payload | starter_id: "unregistered-starter"}).status == 404
  assert input_rows() == []
  before = side_effect_rows()

  selected = response_json!(post(c, owner, @starters, payload), 200)
  assert response_json!(post(c, owner, @starters, payload), 200) == selected

  assert selected ==
           Map.merge(public_scope(scope), %{
             "platform" => "android",
             "sourceInputId" => id,
             "sourceSha256" => pins["source_tree_sha256"],
             "toolchainLockSha256" => pins["linux_lock_sha256"],
             "buildDefinitionSha256" => pins["recipe_sha256"]
           })

  assert input_rows() == [
           [
             scope.organization_id,
             scope.project_id,
             scope.application_id,
             "android",
             id,
             "revision",
             reference,
             pins["source_tree_sha256"],
             pins["linux_lock_sha256"],
             pins["recipe_sha256"],
             1,
             1_200_000,
             0
           ]
         ]

  build = Map.new(selected, fn {key, value} -> {Macro.underscore(key), value} end)
  assert build == stringify(expected)
  wrong = %{build | "source_sha256" => sha256("wrong Pair25 input")}

  assert post(c, owner, "/console-api/v1/builds", wrong, [{"idempotency-key", "pair25-bad-input"}]).status ==
           409

  assert side_effect_rows() == before

  {build,
   Map.merge(registration, %{
     verified_input_rows: 1,
     selection_http: [200, 200],
     outsider_http: 404,
     unregistered_starter_http: 404,
     mismatched_build_http: 409
   })}
end

defp pair25_outsider(c) do
  :ok = GenServer.call(c.provider, {:pair25_subject, "subject-2"})

  try do
    login(c)
  after
    :ok = GenServer.call(c.provider, {:pair25_subject, "subject-1"})
  end
end

defp pair25_wait!(c, renewed, deadline) do
  assert System.monotonic_time(:millisecond) < deadline

  cond do
    File.regular?(pair25_path("api.done")) ->
      :ok

    File.regular?(pair25_path("api.cancel-auth.request")) and
        not File.regular?(pair25_path("api.cancel-auth")) ->
      {cookie, csrf} = login(c)
      pair25_publish!("api.cancel-auth", %{cookie: cookie, csrf: csrf})
      pair25_wait!(c, renewed, deadline)

    File.regular?(pair25_path("api.checkout.request")) and
        not File.regular?(pair25_path("api.checkout.closed")) ->
      pair25_checkout_outage!()
      pair25_wait!(c, renewed, deadline)

    not renewed and File.regular?(pair25_path("api.refresh")) ->
      {owner, owner_csrf} = login(c)
      {outsider, _} = pair25_outsider(c)
      pair25_publish!("api.sessions", %{owner: owner, owner_csrf: owner_csrf, outsider: outsider})
      pair25_wait!(c, true, deadline)

    true ->
      Process.sleep(50)
      pair25_wait!(c, renewed, deadline)
  end
end

@checkout_event [:mixer_hosted, :browser_auth, :store, :transaction]

def pair25_checkout_event(
      @checkout_event,
      %{queue_time: duration, total_time: duration} = measurements,
      %{
        repo: MixerHosted.BrowserAuth.LifecycleRepo,
        query: "begin",
        result:
          {:error,
           %DBConnection.ConnectionError{
             reason: :error,
             message: "connection not available and queuing is disabled"
           }}
      },
      test
    )
    when is_integer(duration) and duration >= 0 and map_size(measurements) == 2 do
  send(test, {:checkout_refused_before_begin, duration})
end

def pair25_checkout_event(_, _, _, _), do: :ok

defp pair25_checkout_outage! do
  alias MixerHosted.BrowserAuth.LifecycleRepo

  lifecycle = RuntimeOwner.status()
  assert lifecycle.phase == :storage_ready
  assert Process.whereis(MixerHostedWeb.Endpoint)
  %{pid: pool} = Ecto.Adapter.lookup_meta(LifecycleRepo)

  assert [%{ready_conn_count: 2, checkout_queue_length: 0}] =
           DBConnection.get_connection_metrics(pool)

  parent = self()
  observer = make_ref()
  :ok = :telemetry.attach(observer, @checkout_event, &__MODULE__.pair25_checkout_event/4, parent)

  tasks =
    for _ <- 1..2 do
      Task.async(fn ->
        LifecycleRepo.checkout(
          fn ->
            send(parent, {:checkout_held, self()})

            receive do
              :release_checkout -> :released
            after
              5_000 -> raise "Pair25 checkout hold expired"
            end
          end,
          queue: false,
          timeout: 6_000
        )
      end)
    end

  try do
    for task <- tasks do
      holder = task.pid
      assert_receive {:checkout_held, ^holder}, 1_000
    end

    assert [%{ready_conn_count: 0, checkout_queue_length: 0}] =
             DBConnection.get_connection_metrics(pool)

    pair25_publish!("api.checkout.ready", %{held: 2, queue: 0})
    assert_receive {:checkout_refused_before_begin, duration}, 3_000
    pair25_publish!("api.checkout.refused", %{before_begin: true, queue_ns: duration})
  after
    :telemetry.detach(observer)
    for task <- tasks, do: send(task.pid, :release_checkout)
    for task <- tasks, do: assert(Task.await(task, 1_000) == :released)
  end

  assert RuntimeOwner.status() == lifecycle

  assert [%{ready_conn_count: 2, checkout_queue_length: 0}] =
           DBConnection.get_connection_metrics(pool)

  pair25_publish!("api.checkout.closed", %{checked_in: 2, generation: lifecycle.generation})
end

defp pair25_publish!(name, data) do
  File.write!(pair25_path(name <> ".tmp"), Jason.encode!(data), [:exclusive])
  File.rename!(pair25_path(name <> ".tmp"), pair25_path(name))
end

defp pair25_path(name), do: Path.join(System.fetch_env!("PAIR25_RUN"), name)

defp pair25_processor!(c) do
  alias MixerHosted.Builds.ProcessorProfile

  for version <- [20_261_110_000_498, 20_261_110_000_499, 20_261_110_000_500] do
    [path] = Path.wildcard("priv/unselected_operation_admission/#{version}_*.exs")
    [{module, _}] = Code.require_file(path)
    assert :ok = Ecto.Migrator.up(Migration, version, module, log: false)
  end

  for sql <- ProcessorProfile.statements(:builds_v1) do
    DB.q!(
      Admin,
      String.replace(sql, ~s(:"processor_database"), "browser_ordinary_installation_r1422")
    )
  end

  for sql <- ProcessorProfile.operation_intent_statements(:durable_intent_v1),
      do: DB.q!(Admin, sql)

  for sql <- SelfServiceSchema.processor_policy_statements(), do: DB.q!(Migration, sql)

  DB.q!(Admin, "INSERT INTO public.mixer_authz_principals VALUES('person-2','human',true,0,1)")

  DB.q!(
    Admin,
    "INSERT INTO public.mixer_authz_bindings VALUES('humans',1,'subject-2','human','person-2',true,1)"
  )

  DB.q!(
    Admin,
    ~s(UPDATE mixer_build_fleet_capacity SET configured=true,"limit"=1,revision=1 WHERE id='fleet')
  )

  DB.q!(
    Admin,
    ~s(UPDATE mixer_build_fleet_platform_capacities SET configured=true,"limit"=1,revision=1 WHERE platform='android')
  )

  c
  |> put_in([:hosted, Access.key(:processor_profile)], :builds_v1)
  |> put_in([:hosted, Access.key(:native)], %{retained_root: pair25_path("worker")})
  |> then(fn c ->
    if System.get_env("PAIR25_CANCEL") == "1" do
      for sql <- MixerHosted.CustomerBuilds.CancelSchema.statements(), do: DB.q!(Migration, sql)
      put_in(c, [:hosted, Access.key(:build_cancel)], true)
    else
      c
    end
  end)
end
