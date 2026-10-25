Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Logger.configure(level: :error)

Code.require_file("verification/hosted-browser-begin-login-review/synthetic_runtime_fixture.exs")

defmodule MixerBeginReview do
  alias MixerHosted.BrowserAuth.{LifecycleRepo, PreauthDraft, Protocol, RuntimeOwner, Store}
  alias MixerHosted.BrowserAuth.{StoredSnapshot, Vault}

  def check(name, fun) do
    result =
      try do
        fun.() === true
      rescue
        _ -> false
      catch
        _, _ -> false
      end

    records = Process.get(:begin_review_checks, [])
    Process.put(:begin_review_checks, records ++ [%{control: name, invariant_passed: result}])
    if not result, do: raise("independent component control failed: " <> name)
    IO.puts("PASS " <> name)
  end

  def ok!({:ok, value}), do: value
  def ok!(_), do: raise("independent fixture unavailable")
  def require!(true), do: :ok
  def require!(_), do: raise("independent fixture invariant unavailable")
  def denied?({:error, %Store.Failure{code: :session_unavailable}}), do: true
  def denied?(_), do: false
  def metadata, do: %{request_id: String.duplicate("c", 32)}

  def own(label, {:ok, pid}) when is_pid(pid) do
    Process.put(:begin_review_processes, [{label, pid} | Process.get(:begin_review_processes, [])])

    pid
  end

  def own(_, _), do: raise("independent fixture start unavailable")

  def query(admin, sql, params \\ []),
    do: Postgrex.query!(admin, sql, params, timeout: 2000, log: false)

  def headers(created) do
    [
      {"Cookie", "__Host-mixer-session=" <> created.cookie},
      {"Origin", "https://console.mixer-review.invalid"},
      {"X-Mixer-CSRF", created.csrf}
    ]
  end

  def bootstrap, do: ok!(RuntimeOwner.bootstrap(metadata()))

  def begin(created, headers \\ nil),
    do:
      RuntimeOwner.begin_login(
        created.cookie,
        headers || headers(created),
        :workspace,
        metadata()
      )

  def state(admin, cookie) do
    digest = :crypto.hash(:sha256, cookie)

    result =
      query(
        admin,
        """
        SELECT jsonb_build_object(
          'browser',to_jsonb(b),
          'vault',(SELECT to_jsonb(v) FROM public.mixer_browser_session_vault v WHERE v.browser_id=b.id),
          'attempts',(SELECT coalesce(jsonb_agg(to_jsonb(a) ORDER BY a.state_digest),'[]'::jsonb) FROM public.mixer_browser_oidc_attempts a WHERE a.browser_id=b.id),
          'events',(SELECT coalesce(jsonb_agg(to_jsonb(e) ORDER BY e.sequence),'[]'::jsonb) FROM public.mixer_browser_session_events e WHERE e.browser_id=b.id))
        FROM public.mixer_browser_sessions b WHERE b.cookie_digest=$1::bytea
        """,
        [digest]
      )

    case result.rows do
      [[value]] -> value
      _ -> raise("independent fixture observation unavailable")
    end
  end

  def snapshot(admin, cookie, runtime) do
    result =
      query(admin, "SELECT public.mixer_browser_load($1::bytea,$2::bytea)", [
        :crypto.hash(:sha256, cookie),
        runtime.configuration_digest
      ])

    case result.rows do
      [[raw]] -> ok!(StoredSnapshot.decode(raw))
      _ -> raise("independent fixture snapshot unavailable")
    end
  end

  def reserve do
    ok!(
      GenServer.call(
        RuntimeOwner,
        {:reserve, System.monotonic_time(:millisecond) + 5000, System.system_time(:second)}
      )
    )
  end

  def release(lease), do: GenServer.call(RuntimeOwner, {:release, lease})

  def discover(lease, cookie),
    do:
      ok!(
        Store.discover_begin(%PreauthDraft.Load{
          lease: lease,
          cookie_digest: :crypto.hash(:sha256, cookie)
        })
      )

  # Independent trusted fixture construction uses the actual committed discovery,
  # fixed Protocol, platform CSPRNG and Vault. No callback enters product code.
  def draft(lease, source, csrf) do
    runtime = lease.runtime
    config = runtime.browser_config
    previous = source.session_envelope.context

    context = %{
      previous
      | epoch: previous.epoch + 1,
        revision: previous.revision + 1,
        vault_generation: previous.vault_generation + 1
    }

    state = Protocol.random_token()
    nonce = Protocol.random_token()
    verifier = Protocol.random_token()

    expiry =
      min(
        lease.started_at + 300,
        min(source.browser["idle_expires_at"], source.browser["absolute_expires_at"])
      )

    attempt_context = %{
      purpose: :attempt,
      state_digest: :crypto.hash(:sha256, state),
      browser_id: context.browser_id,
      cookie_digest: context.cookie_digest,
      epoch: context.epoch,
      revision: context.revision,
      generation: context.generation,
      config_digest: runtime.configuration_digest,
      profile_id: config.profile_id,
      profile_version: config.profile_version,
      issuer: config.issuer,
      client_id: config.client_id,
      redirect_uri: config.redirect_uri,
      expires_at: expiry
    }

    sealed = ok!(Vault.seal(runtime.custody.key, context, %Vault.Preauth{csrf: csrf}))

    attempt_sealed =
      ok!(Vault.seal(runtime.custody.key, attempt_context, %Vault.Verifier{verifier: verifier}))

    url =
      ok!(Protocol.authorization_url(config, %{state: state, nonce: nonce, verifier: verifier}))

    struct!(PreauthDraft.Begin,
      lease: lease,
      source: source,
      context: context,
      sealed: sealed,
      attempt_context: attempt_context,
      attempt_sealed: attempt_sealed,
      state: state,
      nonce: nonce,
      verifier: verifier,
      csrf: csrf,
      url: url
    )
  end

  def url_agrees?(authorization, snapshot, runtime, csrf) do
    config = runtime.browser_config
    values = URI.decode_query(URI.parse(authorization.url).query)

    verifier =
      ok!(
        Vault.open(
          runtime.custody.key,
          snapshot.attempt_envelope.context,
          snapshot.attempt_envelope.sealed
        )
      ).verifier

    expected_url =
      ok!(
        Protocol.authorization_url(config, %{
          state: values["state"],
          nonce: values["nonce"],
          verifier: verifier
        })
      )

    expected_csrf =
      ok!(
        Vault.open(
          runtime.custody.key,
          snapshot.session_envelope.context,
          snapshot.session_envelope.sealed
        )
      ).csrf

    a = snapshot.attempt

    byte_size(authorization.url) <= 8192 and authorization.url === expected_url and
      Enum.sort(Map.keys(values)) ===
        ~w(client_id code_challenge code_challenge_method nonce redirect_uri response_mode response_type scope state) and
      values["response_type"] === "code" and values["response_mode"] === "query" and
      values["client_id"] === config.client_id and values["redirect_uri"] === config.redirect_uri and
      values["scope"] === "openid mixer.workspace.read" and
      values["code_challenge_method"] === "S256" and
      values["code_challenge"] === ok!(Protocol.pkce_challenge(verifier)) and
      Protocol.token?(values["state"]) and Protocol.token?(values["nonce"]) and
      Protocol.token?(verifier) and
      a["state_digest"] === :crypto.hash(:sha256, values["state"]) and
      a["nonce_digest"] === :crypto.hash(:sha256, values["nonce"]) and
      authorization.expires_at === a["expires_at"] and
      System.system_time(:second) < authorization.expires_at and expected_csrf === csrf
  end

  def raw_begin(admin, created, runtime, expires) do
    lease = reserve()

    try do
      source = discover(lease, created.cookie)
      d = draft(lease, source, created.csrf)
      context = %{d.attempt_context | expires_at: expires}

      sealed =
        ok!(Vault.seal(runtime.custody.key, context, %Vault.Verifier{verifier: d.verifier}))

      s = d.sealed
      c = source.session_envelope.context
      config = runtime.browser_config

      result =
        query(
          admin,
          """
          SELECT public.mixer_browser_begin($1::bytea,$2::bytea,$3::bytea,$4::bigint,
            ROW($5::bytea,$6::bytea,$7::text,$8::integer,$9::text,$10::text,$11::text,$12::bigint,
              ROW($13::text,$14::bytea,$15::bytea,$16::bytea)::public.mixer_browser_cipher)::public.mixer_browser_attempt,
            ROW($17::text,$18::bytea,$19::bytea,$20::bytea)::public.mixer_browser_cipher,$21::text)
          """,
          [
            c.cookie_digest,
            c.csrf_digest,
            runtime.configuration_digest,
            source.browser["revision"],
            context.state_digest,
            :crypto.hash(:sha256, d.nonce),
            config.profile_id,
            config.profile_version,
            config.issuer,
            config.client_id,
            config.redirect_uri,
            expires,
            sealed.key_id,
            sealed.iv,
            sealed.tag,
            sealed.ciphertext,
            s.key_id,
            s.iv,
            s.tag,
            s.ciphertext,
            metadata().request_id
          ]
        )

      case result.rows do
        [[raw]] -> ok!(StoredSnapshot.decode(raw))
        _ -> raise("independent direct SQL fixture unavailable")
      end
    after
      release(lease)
    end
  end

  # Official BEAM tracing observes one private finish return, holds only this
  # fixture's request, and discards all trace values. The high priority tracer
  # must actually suspend the live target before the action is allowed to run.
  def held_finish(operation, action) do
    previous_schedulers = :erlang.system_flag(:schedulers_online, 1)
    parent = self()

    target =
      spawn(fn ->
        receive do
          :go -> send(parent, {:held_result, self(), operation.()})
        end
      end)

    tracer =
      spawn(fn ->
        Process.flag(:priority, :high)

        receive do
          :arm ->
            receive do
              {:trace, ^target, :return_from, {RuntimeOwner, :finish_receipt, 3}, _private} -> :ok
            after
              8000 -> exit(:missing_owned_finish_trace)
            end

            :erlang.suspend_process(target)
            barrier = :erlang.trace_delivered(target)
            status_returned = drain_trace_barrier(target, barrier, false)
            send(parent, {:held_ready, self(), target, status_returned})

            receive do
              :resume -> :erlang.resume_process(target)
            after
              8000 -> :erlang.resume_process(target)
            end
        end
      end)

    Process.put(:begin_review_transients, [
      {:request, target},
      {:tracer, tracer} | Process.get(:begin_review_transients, [])
    ])

    :erlang.trace_pattern({RuntimeOwner, :finish_receipt, 3}, [{:_, [], [{:return_trace}]}], [
      :local
    ])

    :erlang.trace_pattern({RuntimeOwner, :call, 2}, [{:_, [], [{:return_trace}]}], [:local])
    :erlang.trace(target, true, [:call, {:tracer, tracer}])
    send(tracer, :arm)
    send(target, :go)

    try do
      try do
        receive do
          {:held_ready, ^tracer, ^target, status_returned} ->
            Process.put(:begin_review_trace_fences, [
              %{
                status_returned_before_action: status_returned,
                observed_trace_barrier: true,
                schedulers_online: 1
              }
              | Process.get(:begin_review_trace_fences, [])
            ])

            require!(status_returned === false)
            require!(Process.info(target, :status) === {:status, :suspended})
            {:current_stacktrace, stack} = Process.info(target, :current_stacktrace)

            require!(
              Enum.any?(stack, fn {module, _fun, _arity, _location} -> module === RuntimeOwner end)
            )

            receive do
              {:held_result, ^target, _} -> raise("owned request already published before hold")
            after
              0 -> :ok
            end

            action.()
        after
          8500 -> raise("owned finish trace unavailable")
        end
      after
        send(tracer, :resume)
        :erlang.trace_pattern({RuntimeOwner, :finish_receipt, 3}, false, [:local])
        :erlang.trace_pattern({RuntimeOwner, :call, 2}, false, [:local])
      end

      receive do
        {:held_result, ^target, result} -> result
      after
        8500 -> raise("owned held operation unavailable")
      end
    after
      Enum.each([target, tracer], &stop_transient/1)
      :erlang.system_flag(:schedulers_online, previous_schedulers)
    end
  end

  # trace_delivered fences all prior target trace events after suspension. A
  # returned final owner-status call would prove this hold arrived too late.
  # Holding before that return also proves local publication time/PID samples
  # remain ahead; it does not claim owner-side status was not already sampled.
  def drain_trace_barrier(target, barrier, returned) do
    receive do
      {:trace_delivered, ^target, ^barrier} ->
        returned

      {:trace, ^target, :return_from, {RuntimeOwner, :call, 2}, %{phase: _, generation: _}} ->
        drain_trace_barrier(target, barrier, true)

      {:trace, ^target, _event, _mfa} ->
        drain_trace_barrier(target, barrier, returned)

      {:trace, ^target, _event, _mfa, _private} ->
        drain_trace_barrier(target, barrier, returned)
    after
      2000 -> raise("owned trace barrier unavailable")
    end
  end

  def stop_transient(pid) do
    monitor = Process.monitor(pid)
    if Process.alive?(pid), do: Process.exit(pid, :kill)

    receive do
      {:DOWN, ^monitor, :process, ^pid, _} -> :ok
    after
      1000 -> raise("owned transient cleanup unavailable")
    end
  end

  def claim(admin, source, runtime) do
    result =
      query(
        admin,
        "SELECT public.mixer_browser_claim($1::bytea,$2::bytea,$3::bytea,$4::bigint,$5::bytea,$6::bigint,$7::text)",
        [
          source.browser["cookie_digest"],
          source.attempt["state_digest"],
          runtime.configuration_digest,
          source.browser["revision"],
          :crypto.strong_rand_bytes(32),
          min(System.system_time(:second) + 30, source.attempt["expires_at"]),
          metadata().request_id
        ]
      )

    require!(result.num_rows === 1)
  end
end

alias MixerBeginReview, as: Review
alias MixerHosted.BrowserAuth.{LifecycleRepo, PreauthDraft, RuntimeOwner, Store, Vault}
alias MixerHosted.Identity.KeyOwner

fixture =
  MixerBeginLoginReview.SyntheticRuntimeFixture.build(
    String.to_integer(System.fetch_env!("PREAUTH_REVIEW_PORT")),
    "review_browser"
  )

runtime = fixture.runtime
Process.put(:begin_review_processes, [])

try do
  admin =
    Review.own(
      :admin,
      Postgrex.start_link(
        hostname: "127.0.0.1",
        port: String.to_integer(System.fetch_env!("PREAUTH_REVIEW_PORT")),
        database: "review_browser",
        username: "review_admin",
        backoff_type: :stop
      )
    )

  Application.put_env(:mixer_hosted, MixerHosted.Repo, fixture.ordinary_repo)
  Review.own(:ordinary, MixerHosted.Repo.start_link(fixture.ordinary_repo))
  Review.own(:lifecycle, LifecycleRepo.start_link(runtime.lifecycle_repo))

  Review.own(
    :workers,
    DynamicSupervisor.start_link(strategy: :one_for_one, name: BeginReviewFetchWorkers)
  )

  roots =
    Enum.map(:public_key.cacerts_get(), fn
      {:cert, der, _} -> der
      der when is_binary(der) -> der
    end)

  Review.own(
    :identity,
    KeyOwner.start_link(
      manifest: fixture.identity_manifest,
      generation: 1,
      binding: fixture.identity_binding,
      ca_roots: roots,
      resolvers: [{{1, 1, 1, 1}, 53}],
      worker_supervisor: BeginReviewFetchWorkers
    )
  )

  owner = Review.own(:owner, RuntimeOwner.start_link(runtime))

  Review.check("fixed manual owner and actual pool binding", fn ->
    RuntimeOwner.status() === %{phase: :storage_ready, generation: 1} and
      LifecycleRepo.bound?(runtime.lifecycle_repo)
  end)

  created = Review.bootstrap()

  Review.check("shared publication preserves bootstrap and committed load", fn ->
    loaded = Review.ok!(RuntimeOwner.load(created.cookie))

    loaded.cookie === created.cookie and loaded.csrf === created.csrf and
      loaded.source.browser === created.source.browser
  end)

  Review.check("shared publication preserves canonical absent load", fn ->
    RuntimeOwner.load(MixerHosted.BrowserAuth.Protocol.random_token()) === {:ok, nil}
  end)

  authorization = Review.ok!(Review.begin(created))
  pending = Review.snapshot(admin, created.cookie, runtime)

  Review.check("public begin exact URL state nonce PKCE and authenticated envelopes", fn ->
    Review.url_agrees?(authorization, pending, runtime, created.csrf)
  end)

  Review.check("public begin exact full browser increment and identity absence", fn ->
    expected =
      Map.merge(created.source.browser, %{"epoch" => 2, "revision" => 2, "audit_sequence" => 2})

    pending.browser === expected and pending.session_envelope.context.vault_generation === 2 and
      pending.attempt["status"] === "pending" and
      Enum.all?(
        ~w(claim_digest claimed_at claim_expires_at completion_reason),
        &is_nil(pending.attempt[&1])
      ) and
      Enum.all?(
        ~w(profile_id profile_version principal_id family_id credential_ref credential_revision),
        &is_nil(pending.browser[&1])
      )
  end)

  Review.check("authorization and owner status Inspect expose no sensitive fields", fn ->
    private =
      inspect(authorization, limit: :infinity) <>
        inspect(:sys.get_status(owner), limit: :infinity)

    map_size(authorization) === 3 and
      Enum.all?(
        [authorization.url, created.cookie, created.csrf, runtime.custody.key.bytes],
        fn secret -> not String.contains?(private, secret) end
      )
  end)

  Review.check("ordinary load still rejects projected pending attempt", fn ->
    match?(
      {:error, %Store.Failure{phase: :decode, outcome: :rolled_back}},
      RuntimeOwner.load(created.cookie)
    )
  end)

  second = Review.ok!(Review.begin(created))
  replaced = Review.snapshot(admin, created.cookie, runtime)
  durable = Review.state(admin, created.cookie)
  old = Enum.find(durable["attempts"], &(&1["status"] === "superseded"))

  Review.check("pending replacement rotates state nonce verifier and clears old cipher", fn ->
    Review.url_agrees?(second, replaced, runtime, created.csrf) and
      authorization.url !== second.url and
      pending.attempt["state_digest"] !== replaced.attempt["state_digest"] and
      pending.attempt["nonce_digest"] !== replaced.attempt["nonce_digest"] and
      Review.ok!(
        Vault.open(
          runtime.custody.key,
          pending.attempt_envelope.context,
          pending.attempt_envelope.sealed
        )
      ).verifier !==
        Review.ok!(
          Vault.open(
            runtime.custody.key,
            replaced.attempt_envelope.context,
            replaced.attempt_envelope.sealed
          )
        ).verifier and
      is_map(old) and Enum.all?(~w(key_id iv tag ciphertext), &is_nil(old[&1])) and
      old["completion_reason"] === "superseded"
  end)

  for {label, headers} <- [
        {"wrong Origin",
         List.keyreplace(
           Review.headers(created),
           "Origin",
           0,
           {"Origin", "https://other.invalid"}
         )},
        {"wrong CSRF",
         List.keyreplace(
           Review.headers(created),
           "X-Mixer-CSRF",
           0,
           {"X-Mixer-CSRF", MixerHosted.BrowserAuth.Protocol.random_token()}
         )},
        {"cookie argument mismatch",
         List.keyreplace(
           Review.headers(created),
           "Cookie",
           0,
           {"Cookie", "__Host-mixer-session=" <> MixerHosted.BrowserAuth.Protocol.random_token()}
         )},
        {"duplicate cookie headers",
         Review.headers(created) ++ [{"cookie", "__Host-mixer-session=" <> created.cookie}]},
        {"duplicate Origin headers",
         Review.headers(created) ++ [{"origin", runtime.browser_config.public_origin}]},
        {"duplicate CSRF headers", Review.headers(created) ++ [{"x-mixer-csrf", created.csrf}]},
        {"Authorization header",
         Review.headers(created) ++ [{"Authorization", "Bearer synthetic"}]}
      ] do
    Review.check(label <> " denies without durable mutation", fn ->
      before = Review.state(admin, created.cookie)

      Review.denied?(Review.begin(created, headers)) and
        before === Review.state(admin, created.cookie)
    end)
  end

  Review.check("closed metadata route and malformed cookie reject without mutation", fn ->
    before = Review.state(admin, created.cookie)

    Enum.all?(
      [
        RuntimeOwner.begin_login(created.cookie, Review.headers(created), :workspace, %{
          request_id: String.duplicate("A", 32)
        }),
        RuntimeOwner.begin_login(
          created.cookie,
          Review.headers(created),
          :workspace,
          Map.put(Review.metadata(), :extra, 1)
        ),
        RuntimeOwner.begin_login(
          created.cookie,
          Review.headers(created),
          :other,
          Review.metadata()
        ),
        RuntimeOwner.begin_login("bad", Review.headers(created), :workspace, Review.metadata())
      ],
      &Review.denied?/1
    ) and before === Review.state(admin, created.cookie)
  end)

  Review.check("canonical absent browser yields failure and never authorization", fn ->
    absent = %{created | cookie: MixerHosted.BrowserAuth.Protocol.random_token()}
    Review.denied?(Review.begin(absent))
  end)

  # Each mutation uses one retained real lease and committed exact discovery.
  # All inputs are trusted local fixture data; no product file is rewritten.
  lease = Review.reserve()

  try do
    source = Review.discover(lease, created.cookie)
    d = Review.draft(lease, source, created.csrf)

    broken_source = %{
      source
      | session_envelope: %{
          source.session_envelope
          | sealed: %{source.session_envelope.sealed | tag: :crypto.strong_rand_bytes(16)}
        }
    }

    broken_pending = %{
      source
      | attempt_envelope: %{
          source.attempt_envelope
          | sealed: %{source.attempt_envelope.sealed | tag: :crypto.strong_rand_bytes(16)}
        }
    }

    for {label, bad} <- [
          {"source session AEAD", %{d | source: broken_source}},
          {"old projected verifier AEAD", %{d | source: broken_pending}},
          {"new session AEAD", %{d | sealed: %{d.sealed | tag: :crypto.strong_rand_bytes(16)}}},
          {"new verifier AEAD",
           %{d | attempt_sealed: %{d.attempt_sealed | tag: :crypto.strong_rand_bytes(16)}}},
          {"new attempt context",
           %{d | attempt_context: %{d.attempt_context | epoch: d.attempt_context.epoch + 1}}},
          {"fixed URL", %{d | url: d.url <> "&unexpected=value"}},
          {"overlong URL", %{d | url: String.duplicate("a", 8193)}},
          {"source audit sequence",
           %{
             d
             | source: %{
                 source
                 | browser: Map.update!(source.browser, "audit_sequence", &(&1 + 1))
               }
           }}
        ] do
      Review.check(label <> " mutation denies without durable change", fn ->
        before = Review.state(admin, created.cookie)

        Review.denied?(Store.begin_login(bad, Review.metadata())) and
          before === Review.state(admin, created.cookie)
      end)
    end
  after
    Review.release(lease)
  end

  Review.check("revision CAS admits one draft and rejects stale draft without retry", fn ->
    fresh = Review.bootstrap()
    lease = Review.reserve()

    try do
      source = Review.discover(lease, fresh.cookie)
      first = Review.draft(lease, source, fresh.csrf)
      loser = Review.draft(lease, source, fresh.csrf)
      result = Store.begin_login(first, Review.metadata())
      after_first = Review.state(admin, fresh.cookie)
      Review.require!(match?({:ok, %MixerHosted.BrowserAuth.StoredSnapshot{}}, result))
      denied = Store.begin_login(loser, Review.metadata())

      Review.denied?(denied) and after_first === Review.state(admin, fresh.cookie) and
        length(after_first["attempts"]) === 1
    after
      Review.release(lease)
    end
  end)

  Review.check("revision stable claim audit race rolls back exact browser mismatch", fn ->
    fresh = Review.bootstrap()
    Review.ok!(Review.begin(fresh))
    lease = Review.reserve()

    try do
      source = Review.discover(lease, fresh.cookie)
      d = Review.draft(lease, source, fresh.csrf)
      Review.claim(admin, source, runtime)
      after_claim = Review.state(admin, fresh.cookie)

      Review.require!(
        after_claim["browser"]["revision"] === source.browser["revision"] and
          after_claim["browser"]["audit_sequence"] === source.browser["audit_sequence"] + 1
      )

      result = Store.begin_login(d, Review.metadata())

      match?({:error, %Store.Failure{phase: :decode, outcome: :rolled_back}}, result) and
        after_claim === Review.state(admin, fresh.cookie)
    after
      Review.release(lease)
    end
  end)

  Review.check("hidden claimed attempt can be superseded without observation claim", fn ->
    fresh = Review.bootstrap()
    Review.ok!(Review.begin(fresh))
    source = Review.snapshot(admin, fresh.cookie, runtime)
    Review.claim(admin, source, runtime)
    hidden = Review.snapshot(admin, fresh.cookie, runtime)
    Review.require!(hidden.attempt === nil)
    result = Review.ok!(Review.begin(fresh))
    current = Review.snapshot(admin, fresh.cookie, runtime)

    old =
      Enum.find(Review.state(admin, fresh.cookie)["attempts"], &(&1["status"] === "superseded"))

    Review.url_agrees?(result, current, runtime, fresh.csrf) and is_map(old) and
      not is_nil(old["claim_digest"])
  end)

  Review.check("expired authenticated pending is replaced while browser remains live", fn ->
    fresh = Review.bootstrap()
    previous = Review.raw_begin(admin, fresh, runtime, System.system_time(:second) + 2)
    Process.sleep(2100)

    Review.require!(
      System.system_time(:second) >= previous.attempt["expires_at"] and
        System.system_time(:second) < fresh.expires_at
    )

    result = Review.ok!(Review.begin(fresh))
    Review.url_agrees?(result, Review.snapshot(admin, fresh.cookie, runtime), runtime, fresh.csrf)
  end)

  Review.check("foreign caller cannot spend copied begin lease", fn ->
    fresh = Review.bootstrap()
    lease = Review.reserve()

    try do
      d = Review.draft(lease, Review.discover(lease, fresh.cookie), fresh.csrf)
      parent = self()

      pid =
        spawn(fn ->
          send(
            parent,
            {:foreign_begin, self(), Review.denied?(Store.begin_login(d, Review.metadata()))}
          )
        end)

      denied =
        receive do
          {:foreign_begin, ^pid, value} -> value
        after
          1500 -> false
        end

      denied and RuntimeOwner.checkpoint(lease) === :ok and
        Map.has_key?(:sys.get_state(owner).operations, lease.reference)
    after
      Review.release(lease)
    end
  end)

  Review.check("Publication Inspect redacts nested private authorization", fn ->
    packet = %PreauthDraft.Publication{
      checked_wall: System.system_time(:second),
      expires_at: authorization.expires_at,
      value: {:ok, authorization}
    }

    inspected = inspect(packet, limit: :infinity)

    not String.contains?(inspected, authorization.url) and
      not String.contains?(inspected, "expires_at") and not String.contains?(inspected, "value")
  end)

  Review.check("post-finish original deadline withholds known committed URL without retry", fn ->
    fresh = Review.bootstrap()

    result =
      Review.held_finish(fn -> Review.begin(fresh) end, fn ->
        Process.put(:known_committed_begin, Review.state(admin, fresh.cookie))
        Process.sleep(5100)
      end)

    committed = Process.get(:known_committed_begin)

    match?({:error, %Store.Failure{phase: :commit, outcome: :committed}}, result) and
      committed["browser"]["revision"] === 2 and length(committed["attempts"]) === 1 and
      committed === Review.state(admin, fresh.cookie)
  end)

  Review.check("same-generation registered owner replacement withholds committed URL", fn ->
    fresh = Review.bootstrap()
    original = Process.whereis(RuntimeOwner)
    generation = RuntimeOwner.status().generation

    result =
      Review.held_finish(fn -> Review.begin(fresh) end, fn ->
        Process.put(:owner_replacement_committed_begin, Review.state(admin, fresh.cookie))
        GenServer.stop(original, :normal, 2000)
        replacement = Review.own(:replacement_owner, RuntimeOwner.start_link(runtime))

        Process.put(
          :replacement_preserved_generation,
          replacement !== original and
            RuntimeOwner.status() === %{phase: :storage_ready, generation: generation}
        )
      end)

    committed = Process.get(:owner_replacement_committed_begin)

    match?({:error, %Store.Failure{phase: :commit, outcome: :committed}}, result) and
      Process.get(:replacement_preserved_generation) === true and
      committed["browser"]["revision"] === 2 and
      committed === Review.state(admin, fresh.cookie)
  end)

  owner = Process.whereis(RuntimeOwner)

  Review.check("complete begin operations release original permit", fn ->
    map_size(:sys.get_state(owner).operations) === 0 and
      RuntimeOwner.status().phase === :storage_ready
  end)
after
  transients = Process.get(:begin_review_transients, [])
  for {_label, pid} <- transients, do: Review.stop_transient(pid)
  processes = Process.get(:begin_review_processes, [])

  for {_label, pid} <- processes do
    if Process.alive?(pid), do: GenServer.stop(pid, :normal, 2000)
  end

  cleanup =
    Map.new(processes, fn {label, pid} ->
      {Atom.to_string(label) <> "_absent", not Process.alive?(pid)}
    end)

  cleanup =
    Map.put(
      cleanup,
      "transients_absent",
      Enum.all?(transients, fn {_label, pid} -> not Process.alive?(pid) end)
    )

  out = System.fetch_env!("PREAUTH_REVIEW_OUTPUT")

  File.write!(
    Path.join(out, "checks.json"),
    Jason.encode!(Process.get(:begin_review_checks, []), pretty: true)
  )

  File.write!(Path.join(out, "beam-cleanup.json"), Jason.encode!(cleanup, pretty: true))

  File.write!(
    Path.join(out, "trace-fences.json"),
    Jason.encode!(Process.get(:begin_review_trace_fences, []), pretty: true)
  )
end

IO.puts(Jason.encode!(%{component_methods: length(Process.get(:begin_review_checks, []))}))

