defmodule BeginControls do
  alias MixerHosted.BrowserAuth.{
    PreauthDraft,
    Protocol,
    RuntimeOwner,
    Store,
    StoredSnapshot,
    Vault
  }

  alias PreauthFixture.Admin

  def headers(p, origin \\ "https://console.example.invalid"),
    do: [
      {"cookie", "__Host-mixer-session=" <> p.cookie},
      {"origin", origin},
      {"x-mixer-csrf", p.csrf}
    ]

  def snapshot(p) do
    %{rows: [[raw]]} =
      PreauthFixture.sql(
        Admin,
        "SELECT public.mixer_browser_snapshot($1::bytea,(SELECT state_digest FROM public.mixer_browser_oidc_attempts WHERE browser_id=$1 AND status='pending' ORDER BY state_digest LIMIT 1))",
        [p.source.browser["id"]]
      )

    {:ok, s} = StoredSnapshot.decode(raw)
    s
  end

  def durable do
    %{rows: [[raw]]} =
      PreauthFixture.sql(
        Admin,
        "SELECT jsonb_build_object('browser',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY id),'[]'::jsonb) FROM public.mixer_browser_sessions x),'vault',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY browser_id),'[]'::jsonb) FROM public.mixer_browser_session_vault x),'attempt',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY state_digest),'[]'::jsonb) FROM public.mixer_browser_oidc_attempts x),'audit',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY browser_id,sequence),'[]'::jsonb) FROM public.mixer_browser_session_events x))"
      )

    raw
  end

  # Independent synthetic draft construction drives only the fixed internal
  # Store API. The live RuntimeOwner path is tested separately; no production
  # function accepts this fixture, clock or provider implementation.
  def draft(lease, source, csrf) do
    runtime = lease.runtime
    config = runtime.browser_config
    c = source.session_envelope.context

    c = %{
      c
      | epoch: c.epoch + 1,
        revision: c.revision + 1,
        vault_generation: c.vault_generation + 1
    }

    state = Protocol.random_token()
    nonce = Protocol.random_token()
    verifier = Protocol.random_token()

    expires =
      min(
        lease.started_at + 300,
        min(source.browser["idle_expires_at"], source.browser["absolute_expires_at"])
      )

    a = %{
      purpose: :attempt,
      state_digest: :crypto.hash(:sha256, state),
      browser_id: c.browser_id,
      cookie_digest: c.cookie_digest,
      epoch: c.epoch,
      revision: c.revision,
      generation: c.generation,
      config_digest: runtime.configuration_digest,
      profile_id: config.profile_id,
      profile_version: config.profile_version,
      issuer: config.issuer,
      client_id: config.client_id,
      redirect_uri: config.redirect_uri,
      expires_at: expires
    }

    {:ok, sealed} = Vault.seal(runtime.custody.key, c, %Vault.Preauth{csrf: csrf})

    {:ok, attempt_sealed} =
      Vault.seal(runtime.custody.key, a, %Vault.Verifier{verifier: verifier})

    {:ok, url} =
      Protocol.authorization_url(config, %{state: state, nonce: nonce, verifier: verifier})

    %PreauthDraft.Begin{
      lease: lease,
      source: source,
      context: c,
      sealed: sealed,
      attempt_context: a,
      attempt_sealed: attempt_sealed,
      state: state,
      nonce: nonce,
      verifier: verifier,
      csrf: csrf,
      url: url
    }
  end

  def discover(p) do
    {:ok, lease} = PreauthFixture.lease()

    {:ok, source} =
      Store.discover_begin(%PreauthDraft.Load{
        lease: lease,
        cookie_digest: :crypto.hash(:sha256, p.cookie)
      })

    {lease, source}
  end

  # Trace values stay solely in this synthetic VM. They are never printed or
  # written. Only an observed nth return suspends the owned request.
  def held_n(module, function, arity, nth, operation, action) do
    previous = :erlang.system_flag(:schedulers_online, 1)

    try do
      held_single(module, function, arity, nth, operation, action, nil)
    after
      :erlang.system_flag(:schedulers_online, previous)
    end
  end

  def held_finish(operation, action) do
    previous = :erlang.system_flag(:schedulers_online, 1)
    owner = Process.whereis(RuntimeOwner)

    try do
      held_single(RuntimeOwner, :finish_receipt, 3, 1, operation, action, owner)
    after
      :erlang.system_flag(:schedulers_online, previous)
    end
  end

  defp held_single(module, function, arity, nth, operation, action, held_owner) do
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
            Enum.each(1..nth, fn _ ->
              receive do
                {:trace, ^target, :return_from, {^module, ^function, ^arity}, _} -> :ok
              after
                8500 -> raise "trace return missing"
              end
            end)

            :erlang.suspend_process(target)

            try do
              if held_owner, do: :erlang.suspend_process(held_owner)
              send(parent, {:held_ready, self(), target})

              receive do
                :resume -> :ok
              after
                9000 -> send(parent, {:hold_expired, self()})
              end
            after
              if held_owner and Process.alive?(held_owner), do: :erlang.resume_process(held_owner)
              if Process.alive?(target), do: :erlang.resume_process(target)
            end
        end
      end)

    :erlang.trace_pattern({module, function, arity}, [{:_, [], [{:return_trace}]}], [:local])
    :erlang.trace(target, true, [:call, {:tracer, tracer}])
    send(tracer, :arm)
    send(target, :go)

    try do
      receive do
        {:held_ready, ^tracer, ^target} ->
          receive do
            {:held_result, ^target, _} -> raise "owned operation completed before hold"
          after
            0 -> :ok
          end

          if held_owner do
            {:messages, messages} = Process.info(held_owner, :messages)

            pending =
              Enum.count(messages, fn
                {:"$gen_call", {^target, _}, :status} -> true
                _ -> false
              end)

            observation = %{
              owned_request_suspended: Process.info(target, :status) === {:status, :suspended},
              owned_owner_suspended: Process.info(held_owner, :status) === {:status, :suspended},
              exact_final_status_requests_queued: pending,
              no_result_already_delivered: true
            }

            File.write!(
              Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "finish-fence.json"),
              Jason.encode!(observation, pretty: true)
            )

            PreauthFixture.assert(
              observation.owned_request_suspended and observation.owned_owner_suspended and
                pending === 1
            )
          end

          action.()
      after
        9000 -> raise "trace hold missing"
      end
    after
      send(tracer, :resume)
      :erlang.trace_pattern({module, function, arity}, false, [:local])
    end

    receive do
      {:held_result, ^target, result} -> result
    after
      8500 -> raise "held operation missing"
    end
  end

  def concurrent(p, metadata) do
    parent = self()

    targets =
      for _ <- 1..2,
          do:
            spawn(fn ->
              receive do
                :go ->
                  send(
                    parent,
                    {:pair_result, self(),
                     RuntimeOwner.begin_login(p.cookie, headers(p), :workspace, metadata)}
                  )
              end
            end)

    tracer =
      spawn(fn ->
        Process.flag(:priority, :high)

        receive do
          {:arm, targets} ->
            Enum.each(1..2, fn _ ->
              receive do
                {:trace, pid, :return_from, {Store, :discover_begin, 1}, _} ->
                  :erlang.suspend_process(pid)
                  send(parent, {:pair_held, pid})
              after
                8500 -> raise "pair trace missing"
              end
            end)

            receive do
              :resume -> Enum.each(targets, &:erlang.resume_process/1)
            end
        end
      end)

    :erlang.trace_pattern({Store, :discover_begin, 1}, [{:_, [], [{:return_trace}]}], [:local])
    for target <- targets, do: :erlang.trace(target, true, [:call, {:tracer, tracer}])
    send(tracer, {:arm, targets})
    for target <- targets, do: send(target, :go)

    try do
      for _ <- targets do
        receive do
          {:pair_held, pid} -> PreauthFixture.assert(pid in targets)
        after
          9000 -> raise "pair hold missing"
        end
      end
    after
      send(tracer, :resume)
      :erlang.trace_pattern({Store, :discover_begin, 1}, false, [:local])
    end

    for _ <- targets do
      receive do
        {:pair_result, pid, result} -> {pid, result}
      after
        8500 -> raise "pair result missing"
      end
    end
  end

  def install_deferred(body) do
    PreauthFixture.sql(
      Admin,
      "CREATE FUNCTION public.begin_fixture_deferred() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN " <>
        body <> "; RETURN NEW; END $$"
    )

    PreauthFixture.sql(
      Admin,
      "CREATE CONSTRAINT TRIGGER begin_fixture_deferred AFTER UPDATE ON public.mixer_browser_sessions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.begin_fixture_deferred()"
    )
  end

  def remove_deferred do
    PreauthFixture.sql(
      Admin,
      "DROP TRIGGER IF EXISTS begin_fixture_deferred ON public.mixer_browser_sessions"
    )

    PreauthFixture.sql(Admin, "DROP FUNCTION IF EXISTS public.begin_fixture_deferred()")
  end

  def fixture_transaction(fun) do
    {:ok, result} =
      MixerHosted.BrowserAuth.LifecycleRepo.transaction(
        fn ->
          PreauthFixture.policy()
          fun.()
        end,
        log: false
      )

    result
  end

  def raw_begin(d) do
    a = d.attempt_context
    x = d.attempt_sealed
    c = d.context
    v = d.sealed

    fixture_transaction(fn ->
      %{rows: [[raw]]} =
        PreauthFixture.sql(
          MixerHosted.BrowserAuth.LifecycleRepo,
          "SELECT public.mixer_browser_begin($1::bytea,$2::bytea,$3::bytea,$4::bigint,ROW($5::bytea,$6::bytea,$7::text,$8::integer,$9::text,$10::text,$11::text,$12::bigint,ROW($13::text,$14::bytea,$15::bytea,$16::bytea)::public.mixer_browser_cipher)::public.mixer_browser_attempt,ROW($17::text,$18::bytea,$19::bytea,$20::bytea)::public.mixer_browser_cipher,$21::text)",
          [
            c.cookie_digest,
            c.csrf_digest,
            c.config_digest,
            d.source.browser["revision"],
            a.state_digest,
            :crypto.hash(:sha256, d.nonce),
            a.profile_id,
            a.profile_version,
            a.issuer,
            a.client_id,
            a.redirect_uri,
            a.expires_at,
            x.key_id,
            x.iv,
            x.tag,
            x.ciphertext,
            v.key_id,
            v.iv,
            v.tag,
            v.ciphertext,
            String.duplicate("b", 32)
          ]
        )

      {:ok, s} = StoredSnapshot.decode(raw)
      s
    end)
  end

  def short_browser(runtime) do
    csrf = Protocol.random_token()
    cookie = Protocol.random_token()

    c = %{
      purpose: :preauth,
      browser_id: :crypto.strong_rand_bytes(16),
      cookie_digest: :crypto.hash(:sha256, cookie),
      csrf_digest: :crypto.hash(:sha256, csrf),
      epoch: 1,
      revision: 1,
      generation: Protocol.random_token(),
      vault_generation: 1,
      config_digest: runtime.configuration_digest,
      profile_id: runtime.browser_config.profile_id,
      profile_version: runtime.browser_config.profile_version,
      principal_id: nil,
      family_id: nil,
      credential_ref: nil,
      credential_revision: nil
    }

    {:ok, v} = Vault.seal(runtime.custody.key, c, %Vault.Preauth{csrf: csrf})
    expires = System.system_time(:second) + 2

    source =
      fixture_transaction(fn ->
        %{rows: [[raw]]} =
          PreauthFixture.sql(
            MixerHosted.BrowserAuth.LifecycleRepo,
            "SELECT public.mixer_browser_bootstrap($1::bytea,$2::bytea,$3::text,$4::bytea,$5::bytea,$6::text,$7::integer,$8::bigint,ROW($9::text,$10::bytea,$11::bytea,$12::bytea)::public.mixer_browser_cipher,$13::text)",
            [
              c.browser_id,
              c.cookie_digest,
              c.generation,
              c.csrf_digest,
              c.config_digest,
              c.profile_id,
              c.profile_version,
              expires,
              v.key_id,
              v.iv,
              v.tag,
              v.ciphertext,
              String.duplicate("c", 32)
            ]
          )

        {:ok, s} = StoredSnapshot.decode(raw)
        s
      end)

    %PreauthDraft.Preauth{cookie: cookie, csrf: csrf, expires_at: expires, source: source}
  end
end
