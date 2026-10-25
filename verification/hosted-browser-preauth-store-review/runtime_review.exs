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

  Review.check("valid projected pending attempt is a load error, never absence", fn ->
    alias MixerHosted.BrowserAuth.{Vault, StoredSnapshot}
    runtime = fixture.runtime
    config = runtime.browser_config
    previous = created.source.session_envelope.context

    session_context = %{
      previous
      | epoch: previous.epoch + 1,
        revision: previous.revision + 1,
        vault_generation: previous.vault_generation + 1
    }

    state = :crypto.strong_rand_bytes(32)
    nonce = :crypto.strong_rand_bytes(32)
    expiry = min(System.system_time(:second) + 90, created.expires_at)
    verifier = Base.url_encode64(:crypto.strong_rand_bytes(32), padding: false)

    attempt_context = %{
      purpose: :attempt,
      state_digest: state,
      browser_id: previous.browser_id,
      cookie_digest: previous.cookie_digest,
      epoch: session_context.epoch,
      revision: session_context.revision,
      generation: previous.generation,
      config_digest: runtime.configuration_digest,
      profile_id: config.profile_id,
      profile_version: config.profile_version,
      issuer: config.issuer,
      client_id: config.client_id,
      redirect_uri: config.redirect_uri,
      expires_at: expiry
    }

    {:ok, session} =
      Vault.seal(runtime.custody.key, session_context, %Vault.Preauth{csrf: created.csrf})

    {:ok, attempt} =
      Vault.seal(runtime.custody.key, attempt_context, %Vault.Verifier{verifier: verifier})

    {:ok, raw} =
      LifecycleRepo.transaction(
        fn ->
          Review.query("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")

          Review.query(
            "SELECT set_config('search_path','pg_catalog',true),set_config('jit','off',true),set_config('statement_timeout','5s',true),set_config('lock_timeout','500ms',true),set_config('idle_in_transaction_session_timeout','5s',true),set_config('bytea_output','hex',true)"
          )

          %{rows: [[value]]} =
            Review.query(
              """
              SELECT public.mixer_browser_begin($1::bytea,$2::bytea,$3::bytea,$4::bigint,
                ROW($5::bytea,$6::bytea,$7::text,$8::integer,$9::text,$10::text,$11::text,$12::bigint,
                  ROW($13::text,$14::bytea,$15::bytea,$16::bytea)::public.mixer_browser_cipher)::public.mixer_browser_attempt,
                ROW($17::text,$18::bytea,$19::bytea,$20::bytea)::public.mixer_browser_cipher,$21::text)
              """,
              [
                previous.cookie_digest,
                previous.csrf_digest,
                runtime.configuration_digest,
                created.source.browser["revision"],
                state,
                nonce,
                config.profile_id,
                config.profile_version,
                config.issuer,
                config.client_id,
                config.redirect_uri,
                expiry,
                attempt.key_id,
                attempt.iv,
                attempt.tag,
                attempt.ciphertext,
                session.key_id,
                session.iv,
                session.tag,
                session.ciphertext,
                String.duplicate("b", 32)
              ]
            )

          value
        end,
        timeout: 5000,
        queue: false,
        log: false,
        telemetry_event: nil
      )

    {:ok, projected} = StoredSnapshot.decode(raw)
    true = projected.attempt["status"] === "pending"

    true =
      Vault.open(
        runtime.custody.key,
        projected.session_envelope.context,
        projected.session_envelope.sealed
      ) === {:ok, %Vault.Preauth{csrf: created.csrf}}

    true =
      Vault.open(
        runtime.custody.key,
        projected.attempt_envelope.context,
        projected.attempt_envelope.sealed
      ) === {:ok, %Vault.Verifier{verifier: verifier}}

    result = RuntimeOwner.load(created.cookie)

    match?({:error, %Store.Failure{phase: :decode, outcome: :rolled_back}}, result) and
      RuntimeOwner.status().phase === :storage_ready and
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
