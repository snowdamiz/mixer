Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Logger.configure(level: :error)

Code.require_file(
  "verification/hosted-browser-preauth-store-review/synthetic_runtime_fixture.exs"
)

defmodule MixerPreauthRootReview do
  alias MixerHosted.BrowserAuth.{LifecycleRepo, RuntimeOwner, Store}

  def check(name, fun) do
    true = fun.()
    records = Process.get(:root_review_checks, [])
    Process.put(:root_review_checks, records ++ [%{control: name, invariant_passed: true}])
  end

  def denied?({:error, %Store.Failure{code: :session_unavailable}}), do: true
  def denied?(_), do: false

  def foreign_control(owner, action) do
    parent = self()

    caller =
      spawn(fn ->
        {:ok, lease} =
          GenServer.call(
            owner,
            {:reserve, System.monotonic_time(:millisecond) + 5000, System.system_time(:second)}
          )

        send(parent, {:reserved, self(), lease})

        receive do
          :checkpoint ->
            result = RuntimeOwner.checkpoint(lease)
            released = GenServer.call(owner, {:release, lease})
            send(parent, {:original, self(), result, released})
        after
          3000 -> :ok
        end
      end)

    lease =
      receive do
        {:reserved, ^caller, value} -> value
      after
        2000 -> raise "missing component reservation"
      end

    case action do
      :finish ->
        GenServer.call(owner, {:finish, lease, nil})

      :failed ->
        GenServer.call(owner, {:failed, lease, Store.failure(:effect, :rolled_back)})

      :release ->
        GenServer.call(owner, {:release, lease})

      :old_cast ->
        GenServer.cast(owner, {:release, caller, lease.reference})

      :copied_expiry ->
        send(owner, {:expire, lease.reference})

      :malformed_finish ->
        GenServer.call(owner, {:finish, Map.from_struct(lease), nil})

      :malformed_failed ->
        GenServer.call(
          owner,
          {:failed, Map.from_struct(lease), Store.failure(:effect, :rolled_back)}
        )
    end

    # Status is an ordered same-sender barrier; private state is fixture-only observation.
    true = RuntimeOwner.status().phase === :storage_ready
    true = Map.has_key?(:sys.get_state(owner).operations, lease.reference)
    send(caller, :checkpoint)

    receive do
      {:original, ^caller, result, released} ->
        true = result === :ok and released === :ok
    after
      2000 -> raise "original component caller lost its reservation"
    end

    not Map.has_key?(:sys.get_state(owner).operations, lease.reference)
  end

  def query(sql, params \\ []) do
    Ecto.Adapters.SQL.query!(LifecycleRepo, sql, params,
      queue: false,
      timeout: 1000,
      log: false,
      telemetry_event: nil
    )
  end
end

alias MixerHosted.BrowserAuth.{LifecycleRepo, RuntimeOwner, PreauthDraft, Store}
alias MixerHosted.Identity.KeyOwner
alias MixerPreauthRootReview, as: Review

fixture =
  MixerPreauthStoreReview.SyntheticRuntimeFixture.build(
    String.to_integer(System.fetch_env!("PREAUTH_REVIEW_PORT")),
    "review_browser"
  )

Application.put_env(:mixer_hosted, MixerHosted.Repo, fixture.ordinary_repo)
{:ok, ordinary} = MixerHosted.Repo.start_link(fixture.ordinary_repo)
{:ok, lifecycle} = LifecycleRepo.start_link(fixture.runtime.lifecycle_repo)
{:ok, workers} = DynamicSupervisor.start_link(strategy: :one_for_one, name: ReviewFetchWorkers)

roots =
  Enum.map(:public_key.cacerts_get(), fn
    {:cert, der, _} -> der
    der when is_binary(der) -> der
  end)

{:ok, identity} =
  KeyOwner.start_link(
    manifest: fixture.identity_manifest,
    generation: 1,
    binding: fixture.identity_binding,
    ca_roots: roots,
    resolvers: [{{1, 1, 1, 1}, 53}],
    worker_supervisor: ReviewFetchWorkers
  )

{:ok, owner} = RuntimeOwner.start_link(fixture.runtime)

try do
  Review.check("fixed registered storage startup", fn ->
    RuntimeOwner.status() === %{phase: :storage_ready, generation: 1} and
      LifecycleRepo.bound?(fixture.runtime.lifecycle_repo)
  end)

  for action <- [
        :finish,
        :failed,
        :release,
        :old_cast,
        :copied_expiry,
        :malformed_finish,
        :malformed_failed
      ] do
    Review.check("original caller retained after #{action}", fn ->
      Review.foreign_control(owner, action)
    end)
  end

  {:ok, %PreauthDraft.Preauth{} = created} =
    RuntimeOwner.bootstrap(%{request_id: String.duplicate("a", 32)})

  Review.check("real private preauth create and committed load", fn ->
    {:ok, loaded} = RuntimeOwner.load(created.cookie)

    created.cookie === loaded.cookie and created.csrf === loaded.csrf and
      created.source.browser["id"] === loaded.source.browser["id"] and
      loaded.source.browser["status"] === "preauth" and
      created.expires_at === loaded.expires_at and loaded.source.attempt === nil
  end)

  Review.check("only canonical absent cookie returns nil", fn ->
    absent = Base.url_encode64(:crypto.strong_rand_bytes(32), padding: false)
    RuntimeOwner.load(absent) === {:ok, nil} and Review.denied?(RuntimeOwner.load("bad"))
  end)

  Review.check("closed bootstrap metadata rejects extra and wrong fields", fn ->
    Review.denied?(RuntimeOwner.bootstrap(%{request_id: String.duplicate("a", 32), extra: 1})) and
      Review.denied?(RuntimeOwner.bootstrap(%{request_id: String.duplicate("A", 32)}))
  end)

  Review.check("direct startup and draft calls lack owner authority", fn ->
    Review.denied?(Store.admit(fixture.runtime, System.monotonic_time(:millisecond) + 1000)) and
      Review.denied?(Store.load(%{})) and Review.denied?(Store.bootstrap(%{}, %{}))
  end)

  Review.check("ordinary authorization context denies lifecycle use", fn ->
    key = {MixerHosted.Authorization.Transaction.Context, :active}
    Process.put(key, true)

    try do
      Review.denied?(RuntimeOwner.load(created.cookie))
    after
      Process.delete(key)
    end
  end)

  Review.check("ordinary transaction denies nested lifecycle use", fn ->
    {:ok, denied} =
      MixerHosted.Repo.transaction(
        fn ->
          Review.denied?(RuntimeOwner.load(created.cookie))
        end,
        timeout: 1000,
        queue: false,
        log: false
      )

    denied
  end)

  Review.check("dedicated transaction denies nesting", fn ->
    {:ok, denied} =
      LifecycleRepo.transaction(
        fn ->
          Review.denied?(RuntimeOwner.load(created.cookie))
        end,
        timeout: 1000,
        queue: false,
        log: false
      )

    denied
  end)

  Review.check("changed dynamic Repo is rejected", fn ->
    old = LifecycleRepo.get_dynamic_repo()
    LifecycleRepo.put_dynamic_repo(:missing_component_repo)

    try do
      Review.denied?(RuntimeOwner.load(created.cookie))
    after
      LifecycleRepo.put_dynamic_repo(old)
    end
  end)

  Review.check("private Inspect and real owner status redact values", fn ->
    inspected = inspect(created)
    status = inspect(:sys.get_status(owner), limit: :infinity)

    Enum.all?([created.cookie, created.csrf, fixture.runtime.custody.key.bytes], fn value ->
      not String.contains?(inspected, value) and not String.contains?(status, value)
    end)
  end)

  Review.check("running pool binding ignores changed environment options", fn ->
    before = Application.get_env(:mixer_hosted, LifecycleRepo)
    altered = Keyword.put(fixture.runtime.lifecycle_repo, :pool_size, 3)
    Application.put_env(:mixer_hosted, LifecycleRepo, altered)

    try do
      LifecycleRepo.bound?(fixture.runtime.lifecycle_repo) and not LifecycleRepo.bound?(altered)
    after
      if is_nil(before),
        do: Application.delete_env(:mixer_hosted, LifecycleRepo),
        else: Application.put_env(:mixer_hosted, LifecycleRepo, before)
    end
  end)

  Review.check("no retained operations after completed component requests", fn ->
    map_size(:sys.get_state(owner).operations) === 0
  end)
after
  for pid <- [owner, lifecycle, ordinary, identity, workers] do
    if Process.alive?(pid), do: GenServer.stop(pid, :normal, 2000)
  end

  records = Process.get(:root_review_checks, [])

  File.write!(
    Path.join(System.fetch_env!("PREAUTH_REVIEW_OUTPUT"), "checks.json"),
    Jason.encode!(records, pretty: true)
  )
end

IO.puts(
  Jason.encode!(%{
    component_methods: length(Process.get(:root_review_checks, [])),
    fixed_owned_processes_absent:
      Enum.all?(
        [owner, lifecycle, ordinary, identity, workers],
        &(not Process.alive?(&1))
      )
  })
)
