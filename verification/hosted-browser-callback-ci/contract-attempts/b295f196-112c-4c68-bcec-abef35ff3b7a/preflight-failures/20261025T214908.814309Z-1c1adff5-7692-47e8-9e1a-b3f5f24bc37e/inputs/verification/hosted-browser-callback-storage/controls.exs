defmodule CallbackControls do
  alias CallbackFixture, as: F
  alias CallbackFixture.Admin

  alias MixerHosted.BrowserAuth.{
    CallbackDraft,
    LifecycleRepo,
    PreauthDraft,
    Protocol,
    RelationCatalog,
    RuntimeOwner,
    Store,
    StoredSnapshot,
    Vault
  }

  defp assert(value), do: F.assert(value)
  defp record(name, fun), do: F.record(name, fun)
  defp sql(statement, params \\ []), do: F.sql(Admin, statement, params)
  defp hash(value), do: :crypto.hash(:sha256, value)

  defp headers(p),
    do: [
      {"cookie", "__Host-mixer-session=" <> p.cookie},
      {"origin", "https://console.example.invalid"},
      {"x-mixer-csrf", p.csrf}
    ]

  defp pending(metadata) do
    {:ok, p} = RuntimeOwner.bootstrap(metadata)
    {:ok, result} = RuntimeOwner.begin_login(p.cookie, headers(p), :workspace, metadata)

    state =
      result.url |> URI.parse() |> Map.fetch!(:query) |> URI.decode_query() |> Map.fetch!("state")

    %{preauth: p, state: state}
  end

  defp reserve do
    {:ok, lease} = F.lease()
    lease
  end

  defp discovery(p, lease),
    do: %CallbackDraft.Discovery{
      lease: lease,
      cookie_digest: hash(p.preauth.cookie),
      state_digest: hash(p.state)
    }

  defp discover(p) do
    lease = reserve()
    {:ok, source} = Store.discover_callback(discovery(p, lease))
    assert(RuntimeOwner.checkpoint(lease) === :ok)
    {lease, source}
  end

  defp claim(lease, source) do
    e = source.attempt_envelope

    {:ok, %Vault.Verifier{verifier: verifier}} =
      Vault.open(lease.runtime.custody.key, e.context, e.sealed)

    %CallbackDraft.Claim{
      lease: lease,
      source: source,
      verifier: verifier,
      claim_secret: :crypto.strong_rand_bytes(32),
      claim_expires_at:
        Enum.min([
          lease.started_at + 60,
          source.attempt["expires_at"],
          source.browser["idle_expires_at"],
          source.browser["absolute_expires_at"]
        ])
    }
  end

  defp reject(lease, source), do: %CallbackDraft.Reject{lease: lease, source: source}

  defp finish(lease, expires) do
    result =
      GenServer.call(
        lease.owner,
        {:finish, lease, expires},
        max(1, lease.deadline - System.monotonic_time(:millisecond))
      )

    assert(match?({:ok, wall} when is_integer(wall), result))
    assert(not Map.has_key?(:sys.get_state(lease.owner).operations, lease.reference))
  end

  defp failure(result, phase \\ nil, outcome \\ nil) do
    F.unavailable(result)
    {:error, error} = result
    if phase, do: assert(error.phase === phase)
    if outcome, do: assert(error.outcome === outcome)
    result
  end

  defp released(lease),
    do: assert(not Map.has_key?(:sys.get_state(lease.owner).operations, lease.reference))

  defp durable do
    %{rows: [[raw]]} =
      sql(
        "SELECT jsonb_build_object('browser',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY id),'[]'::jsonb) FROM public.mixer_browser_sessions x),'vault',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY browser_id),'[]'::jsonb) FROM public.mixer_browser_session_vault x),'attempt',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY state_digest),'[]'::jsonb) FROM public.mixer_browser_oidc_attempts x),'audit',(SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY browser_id,sequence),'[]'::jsonb) FROM public.mixer_browser_session_events x))"
      )

    raw
  end

  defp raw_snapshot(id, state) do
    %{rows: [[raw]]} =
      sql("SELECT public.mixer_browser_snapshot($1::bytea,$2::bytea)", [id, state])

    {:ok, snapshot} = StoredSnapshot.decode(raw)
    snapshot
  end

  defp change(nil), do: "altered"
  defp change(value) when is_integer(value), do: value + 1
  defp change(value) when is_atom(value), do: :altered
  defp change(<<head, rest::binary>>), do: <<Bitwise.bxor(head, 1), rest::binary>>
  defp change(_), do: nil

  defp paths(map, prefix \\ []) do
    Enum.flat_map(Map.to_list(map), fn
      {:__struct__, _} -> []
      {key, value} when is_map(value) -> paths(value, prefix ++ [key])
      {key, _} -> [prefix ++ [key]]
    end)
  end

  defp alter(map, [key]), do: Map.update!(map, key, &change/1)
  defp alter(map, [key | rest]), do: Map.update!(map, key, &alter(&1, rest))

  defp corrupt_attempt(id, statement, params) do
    {:ok, _} =
      Admin.transaction(
        fn ->
          sql(
            "ALTER TABLE public.mixer_browser_oidc_attempts DISABLE TRIGGER mixer_browser_integrity"
          )

          sql(
            "UPDATE public.mixer_browser_oidc_attempts SET " <>
              statement <> " WHERE browser_id=$1",
            [id | params]
          )

          sql(
            "ALTER TABLE public.mixer_browser_oidc_attempts ENABLE TRIGGER mixer_browser_integrity"
          )
        end,
        log: false
      )
  end

  defp deferred(body) do
    sql(
      "CREATE FUNCTION public.callback_fixture_deferred() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN " <>
        body <> "; RETURN NEW; END $$"
    )

    sql(
      "CREATE CONSTRAINT TRIGGER callback_fixture_deferred AFTER UPDATE ON public.mixer_browser_sessions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.callback_fixture_deferred()"
    )
  end

  defp remove_deferred do
    sql("DROP TRIGGER IF EXISTS callback_fixture_deferred ON public.mixer_browser_sessions")
    sql("DROP FUNCTION IF EXISTS public.callback_fixture_deferred()")
  end

  # Tracing observes unchanged private returns only inside this synthetic VM.
  # One scheduler makes suspension precede the following owner checkpoint yield.
  # No traced argument, value, return tag or private message is serialized.
  defp held(module, function, arity, nth, operation, action) do
    schedulers = :erlang.system_flag(:schedulers_online, 1)
    parent = self()

    target =
      spawn(fn ->
        receive do
          :go -> send(parent, {:callback_result, self(), operation.()})
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
                6000 -> raise "selected trace checkpoint missing"
              end
            end)

            :erlang.suspend_process(target)
            send(parent, {:held, self(), target})

            try do
              receive do
                :resume -> :ok
              after
                7000 -> :ok
              end
            after
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
        {:held, ^tracer, ^target} ->
          assert(Process.info(target, :status) === {:status, :suspended})

          receive do
            {:callback_result, ^target, _} -> raise "operation completed before fence"
          after
            0 -> :ok
          end

          action.()
      after
        6500 -> raise "selected hold not reached"
      end
    after
      send(tracer, :resume)
      :erlang.trace_pattern({module, function, arity}, false, [:local])
      :erlang.system_flag(:schedulers_online, schedulers)
    end

    receive do
      {:callback_result, ^target, result} -> result
    after
      6500 -> raise "selected result missing"
    end
  end

  defp audit_result(source, result, operation, secret \\ nil, expires \\ nil) do
    b = source.browser
    assert(result.browser === %{b | "audit_sequence" => b["audit_sequence"] + 1})

    assert(
      result.session_envelope === source.session_envelope and result.attempt_envelope === nil
    )

    a = source.attempt
    a = %{a | "key_id" => nil, "iv" => nil, "tag" => nil, "ciphertext" => nil}

    expected =
      case operation do
        :claim ->
          %{
            a
            | "status" => "claimed",
              "claim_digest" => hash(secret),
              "claimed_at" => result.attempt["claimed_at"],
              "claim_expires_at" => expires
          }

        :reject ->
          %{a | "status" => "provider_rejected", "completion_reason" => "provider_rejected"}
      end

    assert(result.attempt === expected)
    assert(raw_snapshot(b["id"], a["state_digest"]) === result)

    %{rows: [[event, reason, sequence]]} =
      sql(
        "SELECT operation,outcome,sequence FROM public.mixer_browser_session_events WHERE browser_id=$1 ORDER BY sequence DESC LIMIT 1",
        [b["id"]]
      )

    assert(event === if(operation === :claim, do: "claim", else: "provider_reject"))
    assert(reason === if(operation === :claim, do: "claimed", else: "provider_rejected"))
    assert(sequence === b["audit_sequence"] + 1)
  end

  defp crypto_trace(operation) do
    schedulers = :erlang.system_flag(:schedulers_online, 1)
    parent = self()

    target =
      spawn(fn ->
        receive do
          :go ->
            operation.()
            send(parent, {:crypto_done, self()})
        end

        receive do
          :stop -> :ok
        end
      end)

    tracer =
      spawn(fn ->
        Process.flag(:priority, :high)
        crypto_events(target, parent, 0)
      end)

    :erlang.trace_pattern({Vault, :open, 3}, true, [:local])
    :erlang.trace(target, true, [:call, {:tracer, tracer}])
    send(target, :go)

    try do
      receive do
        {:crypto_done, ^target} -> send(tracer, :finish)
      after
        4000 -> raise "crypto probe missing"
      end

      receive do
        {:crypto_count, ^tracer, count} -> count
      after
        2000 -> raise "crypto trace barrier missing"
      end
    after
      :erlang.trace(target, false, [:call])
      :erlang.trace_pattern({Vault, :open, 3}, false, [:local])
      send(target, :stop)
      :erlang.system_flag(:schedulers_online, schedulers)
    end
  end

  defp crypto_events(target, parent, count) do
    receive do
      {:trace, ^target, :call, {Vault, :open, _private_arguments}} ->
        {:dictionary, dictionary} = Process.info(target, :dictionary)

        assert(
          not Enum.any?(dictionary, fn {key, value} ->
            key === {Store, :owned} and value === true
          end)
        )

        crypto_events(target, parent, count + 1)

      :finish ->
        ref = :erlang.trace_delivered(target)
        crypto_drain(target, parent, count, ref)
    end
  end

  defp crypto_drain(target, parent, count, ref) do
    receive do
      {:trace, ^target, :call, {Vault, :open, _private_arguments}} ->
        {:dictionary, dictionary} = Process.info(target, :dictionary)

        assert(
          not Enum.any?(dictionary, fn {key, value} ->
            key === {Store, :owned} and value === true
          end)
        )

        crypto_drain(target, parent, count + 1, ref)

      {:trace_delivered, ^target, ^ref} ->
        send(parent, {:crypto_count, self(), count})
    end
  end

  defp output_corruption(path, replacement, status) do
    sql(
      "ALTER FUNCTION public.mixer_browser_snapshot(bytea,bytea) RENAME TO callback_fixture_snapshot_original"
    )

    encoded = Jason.encode!(replacement)
    literal_path = "'{" <> Enum.join(path, ",") <> "}'"

    sql(
      "CREATE FUNCTION public.mixer_browser_snapshot(p_browser bytea,p_state bytea) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $callback$ DECLARE r jsonb; BEGIN r:=public.callback_fixture_snapshot_original(p_browser,p_state); IF r#>>'{attempt,status}'='" <>
        status <>
        "' THEN RETURN pg_catalog.jsonb_set(r," <>
        literal_path <>
        ",$callbackvalue$" <>
        encoded <> "$callbackvalue$::jsonb,false); END IF; RETURN r; END $callback$"
    )
  end

  defp restore_snapshot do
    sql("DROP FUNCTION public.mixer_browser_snapshot(bytea,bytea)")

    sql(
      "ALTER FUNCTION public.callback_fixture_snapshot_original(bytea,bytea) RENAME TO mixer_browser_snapshot"
    )
  end

  defp output_controls(operation, metadata) do
    p = pending(metadata)
    {lease, source} = discover(p)
    d = claim(lease, source)
    {:ok, exemplar} = Store.claim(d, metadata)
    finish(lease, d.claim_expires_at)

    %{rows: [[raw]]} =
      sql("SELECT public.mixer_browser_snapshot($1,$2)", [
        exemplar.browser["id"],
        exemplar.attempt["state_digest"]
      ])

    # Individual operator DDL after catalog admission exercises post-state
    # comparison, outside any malicious coherent owner guarantee.
    leaves = paths(raw)

    for path <- leaves do
      p = pending(metadata)
      before = durable()
      original = get_in(raw, path)
      value = if is_integer(original), do: original + 1_000_000, else: change(original)
      status = if operation === :claim, do: "claimed", else: "provider_rejected"

      result =
        held(
          RelationCatalog,
          :check_relation_surface!,
          3,
          2,
          fn ->
            {own, source} = discover(p)

            if operation === :claim,
              do: Store.claim(claim(own, source), metadata),
              else: Store.provider_reject(reject(own, source), metadata)
          end,
          fn -> output_corruption(path, value, status) end
        )

      restore_snapshot()
      failure(result, :decode, :rolled_back)
      assert(durable() === before)
      assert(:sys.get_state(RuntimeOwner).operations === %{})
    end

    length(leaves)
  end

  defp concurrent(p, metadata) do
    previous_schedulers = :erlang.system_flag(:schedulers_online, 1)
    parent = self()

    targets =
      for operation <- [:claim, :reject] do
        spawn(fn ->
          {lease, source} = discover(p)
          draft = if operation === :claim, do: claim(lease, source), else: reject(lease, source)
          send(parent, {:prepared, self()})

          receive do
            :mutate -> :ok
          after
            2000 -> raise "concurrent mutation not released"
          end

          result =
            if operation === :claim,
              do: Store.claim(draft, metadata),
              else: Store.provider_reject(draft, metadata)

          if match?({:ok, _}, result), do: finish(lease, source.attempt["expires_at"])
          send(parent, {:concurrent_result, self(), result})
        end)
      end

    for target <- targets do
      receive do
        {:prepared, ^target} -> :ok
      after
        2000 -> raise "concurrent discovery missing"
      end
    end

    tracer =
      spawn(fn ->
        Process.flag(:priority, :high)

        receive do
          :arm ->
            held =
              for _ <- targets do
                receive do
                  {:trace, target, :return_from, {Store, :decode!, 2}, _private_source} ->
                    :erlang.suspend_process(target)
                    send(parent, {:share_held, target})
                    target
                after
                  3000 -> raise "concurrent rediscovery not observed"
                end
              end

            try do
              receive do
                :resume -> :ok
              after
                3500 -> :ok
              end
            after
              # Stagger the already-held upgrades so one lock timeout clears
              # before the other's identical 500ms lock budget expires.
              Enum.each(held, fn target ->
                if Process.alive?(target), do: :erlang.resume_process(target)
                Process.sleep(20)
              end)
            end
        end
      end)

    :erlang.trace_pattern({Store, :decode!, 2}, [{:_, [], [{:return_trace}]}], [:local])
    for target <- targets, do: :erlang.trace(target, true, [:call, {:tracer, tracer}])
    send(tracer, :arm)
    for target <- targets, do: send(target, :mutate)

    try do
      for _ <- targets do
        receive do
          {:share_held, target} ->
            assert(target in targets and Process.info(target, :status) === {:status, :suspended})
            {:dictionary, dictionary} = Process.info(target, :dictionary)

            assert(
              Enum.any?(dictionary, fn {key, value} ->
                key === {Store, :owned} and value === true
              end)
            )
        after
          3500 -> raise "concurrent share checkpoint missing"
        end
      end

      %{rows: [[count]]} =
        sql(
          "SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE usename='browser_lifecycle' AND state='idle in transaction'"
        )

      assert(count === 2)

      File.write!(
        Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "concurrent-share-fence.json"),
        Jason.encode!(%{
          both_current_source_decodes_held: true,
          actual_owned_checkouts: count,
          no_result_delivered: true
        })
      )
    after
      send(tracer, :resume)
      :erlang.trace_pattern({Store, :decode!, 2}, false, [:local])
      :erlang.system_flag(:schedulers_online, previous_schedulers)
    end

    results =
      for target <- targets do
        receive do
          {:concurrent_result, ^target, result} -> result
        after
          3000 -> raise "concurrent callback missing"
        end
      end

    assert(Enum.count(results, &match?({:ok, %StoredSnapshot{}}, &1)) === 1)

    assert(
      Enum.count(results, &match?({:error, %Store.Failure{outcome: :rolled_back}}, &1)) === 1
    )

    assert(:sys.get_state(RuntimeOwner).operations === %{})
  end

  defp active(runtime, metadata) do
    p = pending(metadata)
    {lease, source} = discover(p)
    d = claim(lease, source)
    {:ok, _} = Store.claim(d, metadata)
    finish(lease, d.claim_expires_at)
    c = runtime.browser_config

    sql(
      "INSERT INTO public.mixer_authz_profiles(id,version,issuer,client_id,identity_class,active) VALUES($1,$2,$3,$4,'human',true)",
      [c.profile_id, c.profile_version, c.issuer, c.client_id]
    )

    sql(
      "INSERT INTO public.mixer_authz_principals(id,identity_class,active,not_before,revision) VALUES('callback-principal','human',true,0,1)"
    )

    sql(
      "INSERT INTO public.mixer_authz_bindings(profile_id,profile_version,subject,identity_class,principal_id,active) VALUES($1,$2,'callback-subject','human','callback-principal',true)",
      [c.profile_id, c.profile_version]
    )

    cookie = Protocol.random_token()
    csrf = Protocol.random_token()
    generation = Protocol.random_token()
    family = "browser_" <> Protocol.random_token()

    context = %{
      source.session_envelope.context
      | purpose: :active,
        cookie_digest: hash(cookie),
        csrf_digest: hash(csrf),
        generation: generation,
        epoch: source.browser["epoch"] + 1,
        revision: source.browser["revision"] + 1,
        vault_generation: source.session_envelope.context.vault_generation + 1,
        principal_id: "callback-principal",
        family_id: family,
        credential_ref: "callback-credential",
        credential_revision: 1
    }

    {:ok, sealed} =
      Vault.seal(runtime.custody.key, context, %Vault.Active{
        csrf: csrf,
        access_token: "synthetic-access"
      })

    now = System.system_time(:second)

    sql(
      "SELECT public.mixer_browser_activate($1::bytea,$2::bytea,$3::bytea,$4::bytea,$5::bigint,ROW('human-main',7,$6::text,'callback-subject',$7::text,'callback-credential',$8::bigint,$9::bigint,ARRAY['mixer.workspace.read']::text[],1::bigint,1::bigint,1::bigint)::public.mixer_browser_verified,$10::bytea,$11::bytea,$12::text,$13::text,$14::bigint,ROW($15::text,$16::bytea,$17::bytea,$18::bytea)::public.mixer_browser_cipher,$19::text)",
      [
        source.browser["cookie_digest"],
        source.attempt["state_digest"],
        source.browser["config_digest"],
        hash(d.claim_secret),
        source.browser["revision"],
        c.issuer,
        c.client_id,
        now,
        now + 600,
        hash(cookie),
        hash(csrf),
        generation,
        family,
        now + 300,
        sealed.key_id,
        sealed.iv,
        sealed.tag,
        sealed.ciphertext,
        metadata.request_id
      ]
    )

    snapshot = raw_snapshot(source.browser["id"], nil)

    assert(
      snapshot.browser["status"] === "active" and snapshot.session_envelope.context === context
    )

    {:ok, %Vault.Active{csrf: ^csrf}} =
      Vault.open(runtime.custody.key, context, snapshot.session_envelope.sealed)

    %{p | preauth: %{p.preauth | cookie: cookie, csrf: csrf, source: snapshot}}
  end

  def run(runtime, metadata, identity_pid) do
    record(
      "live callback discovery commits exact encrypted pending source and retains actual caller slot",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        assert(s === raw_snapshot(s.browser["id"], hash(p.state)))

        assert(
          s.attempt["status"] === "pending" and s.session_envelope.context.purpose === :preauth
        )

        finish(lease, s.attempt["expires_at"])
      end
    )

    record("claim consumes exact source raw32 SHA256 fixed expiry and only audit plus one", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)
      d = claim(lease, s)
      {:ok, result} = Store.claim(d, metadata)
      audit_result(s, result, :claim, d.claim_secret, d.claim_expires_at)

      assert(
        result.attempt["claimed_at"] >= lease.started_at and
          result.attempt["claimed_at"] <= System.system_time(:second)
      )

      assert(
        d.claim_secret !== s.browser["cookie_digest"] and
          d.claim_secret !== s.attempt["state_digest"]
      )

      finish(lease, d.claim_expires_at)
    end)

    record(
      "provider rejection authenticates session retains cipher and exact nil claim terminal deltas",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        {:ok, result} = Store.provider_reject(reject(lease, s), metadata)
        audit_result(s, result, :reject)
        finish(lease, s.attempt["expires_at"])
      end
    )

    record(
      "missing browser wrong cookie state and nonpending nil attempt reject with unchanged durable state",
      fn ->
        {:ok, bare} = RuntimeOwner.bootstrap(metadata)
        p = pending(metadata)

        for input <- [
              %{preauth: bare, state: Protocol.random_token()},
              %{p | state: Protocol.random_token()},
              %{p | preauth: %{p.preauth | cookie: Protocol.random_token()}}
            ] do
          before = durable()
          lease = reserve()
          failure(Store.discover_callback(discovery(input, lease)), :decode, :rolled_back)
          released(lease)
          assert(durable() === before)
        end
      end
    )

    record(
      "hidden durable claimed and provider rejected records do not resume or rediscover",
      fn ->
        for operation <- [:claim, :reject] do
          p = pending(metadata)
          {lease, s} = discover(p)

          result =
            if operation === :claim,
              do: Store.claim(claim(lease, s), metadata),
              else: Store.provider_reject(reject(lease, s), metadata)

          assert(match?({:ok, %StoredSnapshot{}}, result))
          finish(lease, s.attempt["expires_at"])
          before = durable()
          lease = reserve()
          failure(Store.discover_callback(discovery(p, lease)), :decode, :rolled_back)
          released(lease)
          assert(durable() === before)
        end
      end
    )

    record(
      "expired pending equality is rejected while live begin replacement remains possible",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        finish(lease, s.attempt["expires_at"])
        created = s.attempt["created_at"]
        Process.sleep(max(1, (created + 1 - System.system_time(:second)) * 1000 + 20))
        now = System.system_time(:second)
        envelope = s.attempt_envelope
        {:ok, verifier} = Vault.open(runtime.custody.key, envelope.context, envelope.sealed)

        {:ok, sealed} =
          Vault.seal(runtime.custody.key, %{envelope.context | expires_at: now}, verifier)

        corrupt_attempt(s.browser["id"], "expires_at=$2,key_id=$3,iv=$4,tag=$5,ciphertext=$6", [
          now,
          sealed.key_id,
          sealed.iv,
          sealed.tag,
          sealed.ciphertext
        ])

        before = durable()
        lease = reserve()
        failure(Store.discover_callback(discovery(p, lease)), :decode, :rolled_back)
        assert(durable() === before)

        assert(
          match?(
            {:ok, %PreauthDraft.Authorization{}},
            RuntimeOwner.begin_login(p.preauth.cookie, headers(p.preauth), :workspace, metadata)
          )
        )
      end
    )

    record(
      "all browser attempt session and verifier leaf mutations deny without durable changes",
      fn ->
        p = pending(metadata)
        {lease, source} = discover(p)
        finish(lease, source.attempt["expires_at"])
        before = durable()
        leaf_paths = paths(Map.from_struct(source))

        for path <- leaf_paths do
          lease = reserve()
          d = claim(lease, source)
          failure(Store.claim(%{d | source: alter(source, path)}, metadata))
          released(lease)
          assert(durable() === before)
        end

        File.write!(
          Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "source-leaf-controls.json"),
          Jason.encode!(%{
            leaf_count: length(leaf_paths),
            every_mutation_denied: true,
            unchanged_durable: true
          })
        )
      end
    )

    record("exact draft metadata verifier secret and fixed expiry grammar fail closed", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)
      finish(lease, s.attempt["expires_at"])
      before = durable()

      for change <- [
            fn d -> Map.put(d, :extra, nil) end,
            fn d -> %{d | verifier: Protocol.random_token()} end,
            fn d -> %{d | verifier: String.duplicate("!", 43)} end,
            fn d -> %{d | claim_secret: <<0>>} end,
            fn d -> %{d | claim_expires_at: d.claim_expires_at + 1} end,
            fn d -> %{d | claim_expires_at: d.claim_expires_at - 1} end,
            fn d -> %{d | claim_expires_at: d.claim_expires_at * 1.0} end
          ] do
        lease = reserve()
        failure(Store.claim(change.(claim(lease, s)), metadata), :admission, :not_started)
        released(lease)
      end

      for meta <- [
            nil,
            %{},
            %{request_id: "a"},
            %{request_id: String.duplicate("A", 32)},
            Map.put(metadata, :extra, nil)
          ] do
        lease = reserve()
        failure(Store.provider_reject(reject(lease, s), meta), :admission, :not_started)
        released(lease)
      end

      lease = reserve()

      failure(
        Store.discover_callback(Map.put(discovery(p, lease), :extra, nil)),
        :admission,
        :not_started
      )

      released(lease)
      lease = reserve()

      failure(
        Store.provider_reject(Map.put(reject(lease, s), :extra, nil), metadata),
        :admission,
        :not_started
      )

      released(lease)
      assert(durable() === before)
    end)

    record(
      "foreign actual caller and every altered or extra key lease preserve original slot",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        d = claim(lease, s)
        parent = self()
        pid = spawn(fn -> send(parent, {:foreign, self(), Store.claim(d, metadata)}) end)

        receive do
          {:foreign, ^pid, result} -> failure(result, :admission, :not_started)
        after
          1500 -> raise "foreign result missing"
        end

        F.preserved(lease)

        for key <- Map.keys(Map.from_struct(lease)) do
          bad = Map.update!(lease, key, &change/1)
          failure(Store.claim(%{d | lease: bad}, metadata), :admission, :not_started)
          F.preserved(lease)
        end

        failure(
          Store.claim(%{d | lease: Map.put(lease, :extra, nil)}, metadata),
          :admission,
          :not_started
        )

        F.preserved(lease)
        finish(lease, s.attempt["expires_at"])
      end
    )

    record("reject authenticates session CSRF digest and does not require verifier opening", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)
      finish(lease, s.attempt["expires_at"])
      corrupt_attempt(s.browser["id"], "tag=$2", [:binary.copy(<<0>>, 16)])
      {lease, bad_verifier} = discover(p)
      {:ok, result} = Store.provider_reject(reject(lease, bad_verifier), metadata)
      audit_result(bad_verifier, result, :reject)
      finish(lease, bad_verifier.attempt["expires_at"])
      p = pending(metadata)
      {lease, s} = discover(p)
      before = durable()
      e = s.session_envelope
      bad = %{s | session_envelope: %{e | sealed: %{e.sealed | tag: :binary.copy(<<0>>, 16)}}}
      failure(Store.provider_reject(reject(lease, bad), metadata), :admission, :not_started)
      released(lease)
      assert(durable() === before)
    end)

    record("claim independently authenticates exact current verifier before mutation", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)
      d = claim(lease, s)
      before = durable()

      failure(
        Store.claim(%{d | verifier: Protocol.random_token()}, metadata),
        :admission,
        :not_started
      )

      assert(durable() === before)
      released(lease)
    end)

    record(
      "discovery opens no Vault and every claim reject open precedes owned transaction",
      fn ->
        for operation <- [:discovery, :claim, :reject] do
          p = pending(metadata)

          count =
            crypto_trace(fn ->
              {lease, source} = discover(p)

              result =
                case operation do
                  :discovery -> {:ok, source}
                  :claim -> Store.claim(claim(lease, source), metadata)
                  :reject -> Store.provider_reject(reject(lease, source), metadata)
                end

              assert(match?({:ok, %StoredSnapshot{}}, result))
              finish(lease, source.attempt["expires_at"])
            end)

          expected =
            case operation do
              :discovery -> 0
              :claim -> 3
              :reject -> 1
            end

          assert(count === expected)
        end
      end
    )

    record("claim audit only race rejects full source despite unchanged browser revision", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)
      stale = claim(lease, s)

      sql("SELECT public.mixer_browser_claim($1,$2,$3,$4,$5,$6,$7)", [
        s.browser["cookie_digest"],
        s.attempt["state_digest"],
        s.browser["config_digest"],
        s.browser["revision"],
        :crypto.strong_rand_bytes(32),
        stale.claim_expires_at,
        metadata.request_id
      ])

      before = durable()
      failure(Store.claim(stale, metadata), :decode, :rolled_back)
      assert(durable() === before)
      released(lease)
    end)

    record("rejection audit only race rejects full source despite unchanged revision", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)

      sql("SELECT public.mixer_browser_provider_reject($1,$2,$3,$4,$5)", [
        s.browser["cookie_digest"],
        s.attempt["state_digest"],
        s.browser["config_digest"],
        s.browser["revision"],
        metadata.request_id
      ])

      before = durable()
      failure(Store.provider_reject(reject(lease, s), metadata), :decode, :rolled_back)
      assert(durable() === before)
    end)

    record(
      "complete rediscovery rejects stored session ciphertext race without mutation",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        d = claim(lease, s)
        F.corrupt_tag(s.browser["id"], :binary.copy(<<1>>, 16))
        before = durable()
        failure(Store.claim(d, metadata), :decode, :rolled_back)
        assert(durable() === before)
        released(lease)
      end
    )

    record(
      "known deferred COMMIT rejection rolls back and releases without invalidating readiness",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        before = durable()
        d = claim(lease, s)
        # The trigger is introduced only after both current catalogs pass.
        result =
          held(
            RelationCatalog,
            :check_relation_surface!,
            3,
            1,
            fn ->
              own = reserve()

              draft = %{
                d
                | lease: own,
                  claim_expires_at: min(own.started_at + 60, s.attempt["expires_at"])
              }

              Store.claim(draft, metadata)
            end,
            fn ->
              deferred(
                "RAISE EXCEPTION 'synthetic callback commit rejection' USING ERRCODE='23514'"
              )
            end
          )

        remove_deferred()
        failure(result, :commit, :rolled_back)
        assert(durable() === before)
        assert(RuntimeOwner.status().phase === :storage_ready)
        finish(lease, s.attempt["expires_at"])
        F.await_idle_pool(150)
      end
    )

    record("unknown COMMIT loss reports owner invalidation and never publishes snapshot", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)
      finish(lease, s.attempt["expires_at"])
      before = durable()

      result =
        held(
          RelationCatalog,
          :check_relation_surface!,
          3,
          1,
          fn ->
            own = reserve()
            Store.provider_reject(reject(own, s), metadata)
          end,
          fn ->
            deferred("PERFORM pg_catalog.pg_terminate_backend(pg_catalog.pg_backend_pid())")
          end
        )

      remove_deferred()
      failure(result, :commit, :unknown)
      assert(durable() === before)
      assert(RuntimeOwner.status() === %{phase: :unavailable, generation: 2})
      assert(:sys.get_state(RuntimeOwner).operations === %{})
      F.await_idle_pool(150)
      F.owner(runtime)
    end)

    record(
      "catalog admission failure uses acknowledged failed path generation invalidation",
      fn ->
        p = pending(metadata)
        lease = reserve()
        sql("GRANT SELECT ON public.mixer_browser_sessions TO browser_lifecycle")

        try do
          failure(Store.discover_callback(discovery(p, lease)), :admission, :rolled_back)
          assert(RuntimeOwner.status() === %{phase: :unavailable, generation: 2})
          assert(:sys.get_state(RuntimeOwner).operations === %{})
        after
          sql("REVOKE SELECT ON public.mixer_browser_sessions FROM browser_lifecycle")
        end

        F.owner(runtime)
      end
    )

    record(
      "original absolute deadline includes discovery and crypto work with no extension",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        d = claim(lease, s)
        before = durable()
        Process.sleep(max(1, lease.deadline - System.monotonic_time(:millisecond) + 15))
        failure(Store.claim(d, metadata), :admission, :not_started)
        assert(durable() === before)
        assert(RuntimeOwner.status().phase === :unavailable)
        assert(:sys.get_state(RuntimeOwner).operations === %{})
        F.owner(runtime)
      end
    )

    record(
      "deferred COMMIT wait obeys original deadline and reports exact known or unknown outcome",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        finish(lease, s.attempt["expires_at"])
        started = System.monotonic_time(:millisecond)

        result =
          held(
            RelationCatalog,
            :check_relation_surface!,
            3,
            1,
            fn ->
              own = reserve()
              Store.provider_reject(reject(own, s), metadata)
            end,
            fn -> deferred("PERFORM pg_catalog.pg_sleep(6)") end
          )

        remove_deferred()
        failure(result, :commit)
        {:error, error} = result
        assert(error.outcome in [:unknown, :rolled_back])

        File.write!(
          Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "deferred-wait-outcome.json"),
          Jason.encode!(%{
            phase: error.phase,
            outcome: error.outcome,
            owner_phase: RuntimeOwner.status().phase,
            elapsed_ms: System.monotonic_time(:millisecond) - started
          })
        )

        assert(System.monotonic_time(:millisecond) - started < 5600)
        if error.outcome === :unknown, do: assert(RuntimeOwner.status().phase === :unavailable)
        assert(:sys.get_state(RuntimeOwner).operations === %{})
        F.await_idle_pool(150)
        F.owner(runtime)
      end
    )

    record("acknowledged COMMIT then owner loss withholds discovery claim and rejection", fn ->
      observations =
        for operation <- [:discovery, :claim, :reject] do
          p = pending(metadata)
          {lease, source} = discover(p)
          finish(lease, source.attempt["expires_at"])

          result =
            held(
              LifecycleRepo,
              :transaction,
              2,
              1,
              fn ->
                own = reserve()

                case operation do
                  :discovery -> Store.discover_callback(discovery(p, own))
                  :claim -> Store.claim(claim(own, source), metadata)
                  :reject -> Store.provider_reject(reject(own, source), metadata)
                end
              end,
              fn ->
                pid = Process.whereis(RuntimeOwner)
                monitor = Process.monitor(pid)
                Process.exit(pid, :kill)

                receive do
                  {:DOWN, ^monitor, :process, ^pid, :killed} -> :ok
                after
                  1000 -> raise "owned owner death not confirmed"
                end
              end
            )

          observed =
            case result do
              {:error, %Store.Failure{} = error} ->
                %{
                  operation: operation,
                  returned_failure: true,
                  phase: error.phase,
                  outcome: error.outcome
                }

              {:ok, %StoredSnapshot{} = snapshot} ->
                %{
                  operation: operation,
                  returned_snapshot: true,
                  status: snapshot.attempt["status"]
                }

              _ ->
                %{operation: operation, unexpected_shape: true}
            end

          failure(result, :commit, :committed)

          status =
            case operation do
              :discovery -> "pending"
              :claim -> "claimed"
              :reject -> "provider_rejected"
            end

          assert(
            raw_snapshot(source.browser["id"], source.attempt["state_digest"]).attempt["status"] ===
              status
          )

          F.owner(runtime)
          observed
        end

      File.write!(
        Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "known-commit-owner-loss.json"),
        Jason.encode!(observations, pretty: true)
      )
    end)

    record("ordinary load continues rejecting projected pending and begin remains usable", fn ->
      p = pending(metadata)
      before = durable()
      failure(RuntimeOwner.load(p.preauth.cookie))
      assert(durable() === before)

      assert(
        match?(
          {:ok, %PreauthDraft.Authorization{}},
          RuntimeOwner.begin_login(p.preauth.cookie, headers(p.preauth), :workspace, metadata)
        )
      )
    end)

    record(
      "foreign lifecycle ordinary and authorization transactions deny callback without mutation",
      fn ->
        p = pending(metadata)

        for repo <- [LifecycleRepo, MixerHosted.Repo] do
          lease = reserve()
          before = durable()

          {:ok, result} =
            repo.transaction(fn -> Store.discover_callback(discovery(p, lease)) end, log: false)

          failure(result, :admission, :not_started)
          released(lease)
          assert(durable() === before)
        end

        lease = reserve()
        Process.put({MixerHosted.Authorization.Transaction.Context, :active}, true)

        try do
          failure(Store.discover_callback(discovery(p, lease)), :admission, :not_started)
        after
          Process.delete({MixerHosted.Authorization.Transaction.Context, :active})
        end

        released(lease)
      end
    )

    record(
      "Inspect and failure fields reveal no token ciphertext PKCE claim secret or runtime",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        d = claim(lease, s)

        for value <- [discovery(p, lease), d, reject(lease, s), s, lease] do
          inspected = inspect(value, limit: :infinity, printable_limit: :infinity)

          for secret <- [
                p.preauth.cookie,
                p.preauth.csrf,
                p.state,
                d.verifier,
                d.claim_secret,
                Base.encode16(s.session_envelope.sealed.ciphertext),
                runtime.custody.key.bytes
              ] do
            assert(not String.contains?(inspected, secret))
          end
        end

        result = Store.claim(%{d | verifier: "malformed"}, metadata)
        {:error, error} = failure(result)
        assert(Map.keys(Map.from_struct(error)) |> Enum.sort() === [:code, :outcome, :phase])
      end
    )

    record("callback failures and success do not emit sensitive SQL telemetry", fn ->
      p = pending(metadata)
      parent = self()
      id = "callback-sensitive-sql"

      :ok =
        :telemetry.attach(
          id,
          [:mixer_hosted, :browser_auth, :lifecycle_repo, :query],
          fn _, _, meta, _ ->
            if String.contains?(Map.get(meta, :query, ""), "SELECT public.mixer_browser_"),
              do: send(parent, :sensitive_query_event)
          end,
          nil
        )

      try do
        {lease, s} = discover(p)
        {:ok, _} = Store.claim(claim(lease, s), metadata)
        finish(lease, s.attempt["expires_at"])

        receive do
          :sensitive_query_event -> raise "sensitive SQL telemetry emitted"
        after
          0 -> :ok
        end
      after
        :telemetry.detach(id)
      end
    end)

    record(
      "exclusive browser expiry withholds callback even if copied pending source remains",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        d = claim(lease, s)
        # Simulated untrusted copied source only: equality at the local wall is denied
        # before SQL. Durable expiry is tested by fixed discovery in the next method.
        b = %{s.browser | "idle_expires_at" => System.system_time(:second)}
        before = durable()
        failure(Store.claim(%{d | source: %{s | browser: b}}, metadata), :admission, :not_started)
        assert(durable() === before)
      end
    )

    record("all Discovery digest and input shape denials leave durable source unchanged", fn ->
      p = pending(metadata)
      before = durable()

      for field <- [:cookie_digest, :state_digest],
          value <- [nil, <<0>>, String.duplicate("a", 43)] do
        lease = reserve()

        failure(
          Store.discover_callback(Map.put(discovery(p, lease), field, value)),
          :admission,
          :not_started
        )

        released(lease)
      end

      for value <- [nil, %{}, %{lease: nil}, :callback] do
        failure(Store.discover_callback(value), :admission, :not_started)
      end

      assert(durable() === before)
    end)

    record("current function catalog checked independently before each callback effect", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)
      before = durable()

      sql(
        "REVOKE EXECUTE ON FUNCTION public.mixer_browser_claim(bytea,bytea,bytea,bigint,bytea,bigint,text) FROM browser_lifecycle"
      )

      try do
        failure(Store.claim(claim(lease, s), metadata), :admission, :rolled_back)
        assert(RuntimeOwner.status().phase === :unavailable)
        assert(durable() === before)
      after
        sql(
          "GRANT EXECUTE ON FUNCTION public.mixer_browser_claim(bytea,bytea,bytea,bigint,bytea,bigint,text) TO browser_lifecycle"
        )
      end

      F.owner(runtime)
    end)

    record("current relation catalog checked independently on mutation checkout", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)
      before = durable()
      sql("GRANT SELECT ON public.mixer_browser_session_vault TO browser_lifecycle")

      try do
        failure(Store.provider_reject(reject(lease, s), metadata), :admission, :rolled_back)
        assert(RuntimeOwner.status().phase === :unavailable)
        assert(durable() === before)
      after
        sql("REVOKE SELECT ON public.mixer_browser_session_vault FROM browser_lifecycle")
      end

      F.owner(runtime)
    end)

    record(
      "every browser vault and attempt output leaf corruption rolls back claim before COMMIT",
      fn ->
        count = output_controls(:claim, metadata)

        File.write!(
          Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "claim-output-leaf-controls.json"),
          Jason.encode!(%{leaf_count: count, every_mutation_denied: true, rolled_back: true})
        )
      end
    )

    record(
      "every browser vault and attempt output leaf corruption rolls back rejection before COMMIT",
      fn ->
        count = output_controls(:reject, metadata)

        File.write!(
          Path.join(System.fetch_env!("PREAUTH_OUTPUT"), "reject-output-leaf-controls.json"),
          Jason.encode!(%{leaf_count: count, every_mutation_denied: true, rolled_back: true})
        )
      end
    )

    record(
      "valid durable active session from unchanged activation SQL is rejected by callback discovery",
      fn ->
        p = active(runtime, metadata)
        before = durable()
        lease = reserve()
        failure(Store.discover_callback(discovery(p, lease)), :decode, :rolled_back)
        released(lease)
        assert(durable() === before)
      end
    )

    record("concurrent claim rejection consumes once and loser has rolled back full source", fn ->
      p = pending(metadata)
      concurrent(p, metadata)
      assert(RuntimeOwner.status().phase === :storage_ready)
    end)

    record(
      "exact lease wall record survives discovery and every terminal exit restores guard",
      fn ->
        p = pending(metadata)
        {lease, s} = discover(p)
        key = {Store, :callback_walls}
        active_key = {Store, :callback_active}
        record = Process.get(key)[lease.reference]
        assert(record.lease === lease and record.wall >= lease.started_at)
        assert(Process.get(active_key) === nil)
        before = Process.get(key)
        bad = %{lease | started_at: lease.started_at - 1}
        failure(Store.claim(%{claim(lease, s) | lease: bad}, metadata), :admission, :not_started)
        assert(Process.get(key) === before and Process.get(active_key) === nil)
        F.preserved(lease)

        failure(
          Store.claim(%{claim(lease, s) | verifier: "malformed"}, metadata),
          :admission,
          :not_started
        )

        assert(not Map.has_key?(Process.get(key), lease.reference))
        assert(Process.get(active_key) === nil)
        released(lease)
      end
    )

    record("actual lost default KeyOwner invalidates pending lease without consumption", fn ->
      p = pending(metadata)
      {lease, s} = discover(p)
      d = claim(lease, s)
      before = durable()
      GenServer.stop(identity_pid)
      failure(Store.claim(d, metadata), :admission, :not_started)
      assert(durable() === before)
      assert(RuntimeOwner.status().phase === :unavailable)
      assert(:sys.get_state(RuntimeOwner).operations === %{})
    end)
  end
end
