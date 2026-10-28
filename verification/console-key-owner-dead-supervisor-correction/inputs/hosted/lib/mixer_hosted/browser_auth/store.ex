defmodule MixerHosted.BrowserAuth.Store do
  @moduledoc """
  Fixed preauthentication and pending callback storage operations on the dedicated lifecycle pool.

  No request-selected Repo, clock, callback, SQL name or provider is accepted.
  The internal owner must still authenticate ciphertext and fence private release
  after the transaction. A decoded snapshot alone grants no authentication.
  """
  alias MixerHosted.BrowserAuth.{
    CallbackDraft,
    Catalog,
    LifecycleRepo,
    PreauthDraft,
    RelationCatalog
  }

  alias MixerHosted.BrowserAuth.{Protocol, RuntimeConfig, RuntimeOwner, StoredSnapshot, Vault}

  defmodule Failure do
    @moduledoc "Closed private failure without database, identity or secret details."
    @enforce_keys [:code, :phase, :outcome]
    defstruct @enforce_keys
  end

  @phase {__MODULE__, :phase}
  @owned {__MODULE__, :owned}
  @entered {__MODULE__, :entered}
  @callback_walls {__MODULE__, :callback_walls}
  @callback_active {__MODULE__, :callback_active}
  @ordinary_context {MixerHosted.Authorization.Transaction.Context, :active}

  @doc false
  def admit(%RuntimeConfig{mode: :configured} = runtime, deadline) do
    if Process.whereis(RuntimeOwner) === self(),
      do: transact(runtime, deadline, nil, :admit),
      else: failure(:admission, :not_started)
  end

  def admit(_, _), do: failure(:admission, :not_started)

  def bootstrap(%PreauthDraft.Bootstrap{} = draft, metadata) do
    with true <- metadata?(metadata),
         :ok <- RuntimeOwner.checkpoint(draft.lease),
         true <- bootstrap_draft?(draft) do
      transact(
        draft.lease.runtime,
        draft.lease.deadline,
        draft.lease,
        {:bootstrap, draft, metadata}
      )
    else
      _ -> failure(:admission, :not_started)
    end
  rescue
    _ -> failure(:admission, :not_started)
  catch
    _, _ -> failure(:admission, :not_started)
  end

  def bootstrap(_, _), do: failure(:admission, :not_started)

  def load(%PreauthDraft.Load{lease: lease, cookie_digest: digest} = input) do
    with true <- map_size(input) == 3 and raw?(digest, 32),
         :ok <- RuntimeOwner.checkpoint(lease) do
      transact(lease.runtime, lease.deadline, lease, {:load, input})
    else
      _ -> failure(:admission, :not_started)
    end
  rescue
    _ -> failure(:admission, :not_started)
  catch
    _, _ -> failure(:admission, :not_started)
  end

  def load(_), do: failure(:admission, :not_started)

  def discover_begin(%PreauthDraft.Load{lease: lease, cookie_digest: digest} = input) do
    with true <- map_size(input) == 3 and raw?(digest, 32),
         :ok <- RuntimeOwner.checkpoint(lease) do
      transact(lease.runtime, lease.deadline, lease, {:discover_begin, input})
    else
      _ -> failure(:admission, :not_started)
    end
  rescue
    _ -> failure(:admission, :not_started)
  catch
    _, _ -> failure(:admission, :not_started)
  end

  def discover_begin(_), do: failure(:admission, :not_started)

  def begin_login(%PreauthDraft.Begin{} = draft, metadata) do
    with true <- metadata?(metadata),
         :ok <- RuntimeOwner.checkpoint(draft.lease),
         true <- begin_draft?(draft),
         :ok <- RuntimeOwner.checkpoint(draft.lease) do
      transact(draft.lease.runtime, draft.lease.deadline, draft.lease, {:begin, draft, metadata})
    else
      _ -> failure(:admission, :not_started)
    end
  rescue
    _ -> failure(:admission, :not_started)
  catch
    _, _ -> failure(:admission, :not_started)
  end

  def begin_login(_, _), do: failure(:admission, :not_started)

  @doc "Private committed pending callback source; no decrypted material is returned."
  def discover_callback(%CallbackDraft.Discovery{} = input),
    do: callback_call(:discover_callback, input, nil)

  def discover_callback(_), do: failure(:admission, :not_started)

  @doc "Consumes only an authenticated live pending source; returns no claim authority."
  def claim(%CallbackDraft.Claim{} = draft, metadata),
    do: callback_call(:claim, draft, metadata)

  def claim(_, _), do: failure(:admission, :not_started)

  @doc "Records a fixed provider rejection after authenticating the preauth session."
  def provider_reject(%CallbackDraft.Reject{} = draft, metadata),
    do: callback_call(:provider_reject, draft, metadata)

  def provider_reject(_, _), do: failure(:admission, :not_started)

  defp callback_call(operation, draft, metadata) do
    if Process.get(@callback_active, false) do
      callback_result(draft.lease, failure(:admission, :not_started))
    else
      Process.put(@callback_active, true)

      try do
        result = callback_result(draft.lease, callback_transaction(operation, draft, metadata))

        unless operation === :discover_callback and match?({:ok, %StoredSnapshot{}}, result),
          do: forget_callback_wall(draft.lease)

        result
      after
        Process.delete(@callback_active)
      end
    end
  end

  defp forget_callback_wall(%PreauthDraft.Lease{} = lease) do
    walls = Process.get(@callback_walls, %{})

    case Map.get(walls, lease.reference) do
      %{lease: ^lease} -> Process.put(@callback_walls, Map.delete(walls, lease.reference))
      _ -> :ok
    end
  end

  defp forget_callback_wall(_), do: :ok

  defp callback_transaction(:discover_callback, input, nil) do
    with true <- map_size(input) == 4,
         true <- raw?(input.cookie_digest, 32) and raw?(input.state_digest, 32),
         :ok <- RuntimeOwner.checkpoint(input.lease) do
      transact(
        input.lease.runtime,
        input.lease.deadline,
        input.lease,
        {:discover_callback, input}
      )
    else
      _ -> failure(:admission, :not_started)
    end
  rescue
    _ -> failure(:admission, :not_started)
  catch
    _, _ -> failure(:admission, :not_started)
  end

  defp callback_transaction(operation, draft, metadata) do
    with true <- metadata?(metadata),
         :ok <- RuntimeOwner.checkpoint(draft.lease),
         true <- callback_draft?(operation, draft),
         :ok <- RuntimeOwner.checkpoint(draft.lease) do
      transact(
        draft.lease.runtime,
        draft.lease.deadline,
        draft.lease,
        {operation, draft, metadata}
      )
    else
      _ -> failure(:admission, :not_started)
    end
  rescue
    _ -> failure(:admission, :not_started)
  catch
    _, _ -> failure(:admission, :not_started)
  end

  defp callback_result(%PreauthDraft.Lease{} = lease, {:error, %Failure{}} = error) do
    # This fixed Store call owns reporting. Only the original actual caller can
    # affect the exact retained slot. Failed acknowledgement remains unavailable;
    # no new timeout, owner replacement, retry or readiness assertion is made.
    if lease.caller === self() and Process.whereis(RuntimeOwner) === lease.owner do
      GenServer.call(lease.owner, {:failed, lease, error}, remaining!(lease.deadline))
    end

    error
  rescue
    _ -> error
  catch
    _, _ -> error
  end

  defp callback_result(_, result), do: result

  @doc false
  def failure(phase, outcome),
    do: {:error, %Failure{code: :session_unavailable, phase: phase, outcome: outcome}}

  defp transact(runtime, deadline, lease, operation) do
    with true <- not Process.get(@owned, false),
         true <- is_nil(Process.get(@ordinary_context)),
         true <- LifecycleRepo.get_dynamic_repo() === LifecycleRepo,
         true <- MixerHosted.Repo.get_dynamic_repo() === MixerHosted.Repo,
         false <- LifecycleRepo.in_transaction?(),
         false <- MixerHosted.Repo.in_transaction?(),
         remaining <- remaining!(deadline) do
      Process.put(@owned, true)
      Process.put(@phase, :admission)
      Process.put(@entered, false)

      try do
        result =
          LifecycleRepo.transaction(
            fn ->
              Process.put(@entered, true)

              try do
                policy!(deadline)

                :function_surface_verified =
                  Catalog.check_function_surface!(
                    LifecycleRepo,
                    runtime.expected_roles,
                    deadline,
                    2
                  )

                :relation_surface_verified =
                  RelationCatalog.check_relation_surface!(
                    LifecycleRepo,
                    runtime.expected_roles,
                    deadline
                  )

                checkpoint!(lease, deadline)
                Process.put(@phase, :effect)
                raw = effect!(operation, deadline)
                Process.put(@phase, :decode)
                value = decode!(operation, raw)
                checkpoint!(lease, deadline)
                Process.put(@phase, :commit)
                value
              rescue
                _ -> rollback!()
              catch
                _, _ -> rollback!()
              end
            end,
            timeout: remaining,
            deadline: deadline,
            queue: false,
            log: false,
            telemetry_event: nil
          )

        case result do
          {:ok, value} ->
            # DBConnection's absolute deadline also covers COMMIT. This final
            # check can withhold a known committed result, never resurrect it.
            try do
              checkpoint!(lease, deadline)
              callback_committed!(operation, value)
              remaining!(deadline)
              {:ok, value}
            rescue
              _ -> failure(:commit, :committed)
            catch
              _, _ -> failure(:commit, :committed)
            end

          {:error, %Failure{} = error} ->
            {:error, error}

          _ ->
            failure(:commit, :unknown)
        end
      rescue
        error in Postgrex.Error ->
          # Only an ERROR response that rejects COMMIT supplies a definite
          # rollback receipt. FATAL/PANIC can race with COMMIT acknowledgement.
          outcome = if rejected_commit?(error.postgres), do: :rolled_back, else: :unknown
          failure(Process.get(@phase, :admission), outcome)

        _ ->
          failure(Process.get(@phase, :admission), uncertain_outcome())
      catch
        _, _ -> failure(Process.get(@phase, :admission), uncertain_outcome())
      after
        Process.delete(@entered)
        Process.delete(@phase)
        Process.delete(@owned)
      end
    else
      _ -> failure(:admission, :not_started)
    end
  rescue
    _ -> failure(:admission, :not_started)
  catch
    _, _ -> failure(:admission, :not_started)
  end

  defp uncertain_outcome, do: if(Process.get(@entered, false), do: :unknown, else: :not_started)

  defp rejected_commit?(%{severity: "ERROR", pg_code: <<class::binary-size(2), _::binary>>})
       when class in ["23", "40"], do: true

  defp rejected_commit?(%{severity: "ERROR", pg_code: code}) when code in ["57014", "P0001"],
    do: true

  defp rejected_commit?(_), do: false

  defp rollback! do
    {:error, error} = failure(Process.get(@phase, :admission), :rolled_back)
    LifecycleRepo.rollback(error)
  end

  defp policy!(deadline) do
    query!("SET TRANSACTION ISOLATION LEVEL READ COMMITTED", [], deadline)

    %{rows: [["pg_catalog", "off", "5s", "500ms", "5s", "hex"]], num_rows: 1} =
      query!(
        """
        SELECT pg_catalog.set_config('search_path','pg_catalog',true),
          pg_catalog.set_config('jit','off',true),
          pg_catalog.set_config('statement_timeout','5s',true),
          pg_catalog.set_config('lock_timeout','500ms',true),
          pg_catalog.set_config('idle_in_transaction_session_timeout','5s',true),
          pg_catalog.set_config('bytea_output','hex',true)
        """,
        [],
        deadline
      )
  end

  defp query!(sql, params, deadline) do
    result =
      Ecto.Adapters.SQL.query!(LifecycleRepo, sql, params,
        timeout: remaining!(deadline),
        deadline: deadline,
        queue: false,
        log: false,
        telemetry_event: nil
      )

    remaining!(deadline)
    result
  end

  defp effect!(:admit, _deadline), do: :admitted

  defp effect!({:bootstrap, d, metadata}, deadline) do
    c = d.context
    s = d.sealed

    snapshot!(
      query!(
        """
        SELECT public.mixer_browser_bootstrap($1::bytea,$2::bytea,$3::text,$4::bytea,
          $5::bytea,$6::text,$7::integer,$8::bigint,
          ROW($9::text,$10::bytea,$11::bytea,$12::bytea)::public.mixer_browser_cipher,
          $13::text) AS snapshot
        """,
        [
          c.browser_id,
          c.cookie_digest,
          c.generation,
          c.csrf_digest,
          c.config_digest,
          c.profile_id,
          c.profile_version,
          d.expires_at,
          s.key_id,
          s.iv,
          s.tag,
          s.ciphertext,
          metadata.request_id
        ],
        deadline
      )
    )
  end

  defp effect!({operation, input}, deadline)
       when operation in [:load, :discover_begin, :discover_callback] do
    snapshot!(
      query!(
        """
        SELECT public.mixer_browser_load($1::bytea,$2::bytea) AS snapshot
        """,
        [input.cookie_digest, input.lease.runtime.configuration_digest],
        deadline
      )
    )
  end

  defp effect!({:begin, d, metadata}, deadline) do
    c = d.context
    a = d.attempt_context
    s = d.sealed
    v = d.attempt_sealed

    snapshot!(
      query!(
        """
        SELECT public.mixer_browser_begin($1::bytea,$2::bytea,$3::bytea,$4::bigint,
          ROW($5::bytea,$6::bytea,$7::text,$8::integer,$9::text,$10::text,$11::text,$12::bigint,
            ROW($13::text,$14::bytea,$15::bytea,$16::bytea)::public.mixer_browser_cipher)::public.mixer_browser_attempt,
          ROW($17::text,$18::bytea,$19::bytea,$20::bytea)::public.mixer_browser_cipher,$21::text) AS snapshot
        """,
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
          v.key_id,
          v.iv,
          v.tag,
          v.ciphertext,
          s.key_id,
          s.iv,
          s.tag,
          s.ciphertext,
          metadata.request_id
        ],
        deadline
      )
    )
  end

  defp effect!({operation, d, metadata}, deadline)
       when operation in [:claim, :provider_reject] do
    input = %CallbackDraft.Discovery{
      lease: d.lease,
      cookie_digest: d.source.browser["cookie_digest"],
      state_digest: d.source.attempt["state_digest"]
    }

    # Fixed load holds its browser SHARE lock through this transaction. Revision
    # CAS alone misses audit-only transitions, so compare the whole source first.
    raw = effect!({:discover_callback, input}, deadline)
    Process.put(@phase, :decode)
    true = decode!({:discover_callback, input}, raw) === d.source
    checkpoint!(d.lease, deadline)
    Process.put(@phase, :effect)
    callback_effect!(operation, d, metadata, deadline)
  end

  defp callback_effect!(:claim, d, metadata, deadline) do
    b = d.source.browser

    snapshot!(
      query!(
        """
        SELECT public.mixer_browser_claim($1::bytea,$2::bytea,$3::bytea,$4::bigint,
          $5::bytea,$6::bigint,$7::text) AS snapshot
        """,
        [
          b["cookie_digest"],
          d.source.attempt["state_digest"],
          b["config_digest"],
          b["revision"],
          :crypto.hash(:sha256, d.claim_secret),
          d.claim_expires_at,
          metadata.request_id
        ],
        deadline
      )
    )
  end

  defp callback_effect!(:provider_reject, d, metadata, deadline) do
    b = d.source.browser

    snapshot!(
      query!(
        """
        SELECT public.mixer_browser_provider_reject($1::bytea,$2::bytea,$3::bytea,
          $4::bigint,$5::text) AS snapshot
        """,
        [
          b["cookie_digest"],
          d.source.attempt["state_digest"],
          b["config_digest"],
          b["revision"],
          metadata.request_id
        ],
        deadline
      )
    )
  end

  defp snapshot!(%Postgrex.Result{
         command: :select,
         columns: ["snapshot"],
         rows: [[raw]],
         num_rows: 1,
         messages: []
       }),
       do: raw

  defp decode!(:admit, :admitted), do: :admitted
  defp decode!({:load, _}, nil), do: nil
  defp decode!({:discover_begin, _}, nil), do: nil

  defp decode!({:bootstrap, d, _}, raw) do
    {:ok, %StoredSnapshot{} = s} = StoredSnapshot.decode(raw)
    b = s.browser
    true = s.attempt === nil and s.attempt_envelope === nil
    true = s.session_envelope.context === d.context and s.session_envelope.sealed === d.sealed
    true = b["status"] === "preauth" and b["epoch"] === 1 and b["revision"] === 1
    true = b["audit_sequence"] === 1 and b["initial_config_digest"] === d.context.config_digest
    true = b["created_at"] === b["last_seen_at"] and b["created_at"] >= d.lease.started_at
    true = b["absolute_expires_at"] === d.expires_at and b["idle_expires_at"] === d.expires_at
    s
  end

  defp decode!({:load, input}, raw) do
    {:ok, %StoredSnapshot{} = s} = StoredSnapshot.decode(raw)
    preauth_source!(s, input)
    # Ordinary preauth load remains deliberately narrower than begin discovery.
    true = s.attempt === nil and s.attempt_envelope === nil
    s
  end

  defp decode!({:discover_begin, input}, raw) do
    {:ok, %StoredSnapshot{} = s} = StoredSnapshot.decode(raw)
    preauth_source!(s, input)
    pending_source!(s, input.lease.runtime.browser_config)
    s
  end

  defp decode!({:begin, d, _}, raw) do
    {:ok, %StoredSnapshot{} = s} = StoredSnapshot.decode(raw)
    b = d.source.browser
    # Claim/provider rejection can change audit_sequence without revision. CAS
    # alone cannot admit that race: compare every produced browser field here.
    true =
      s.browser === %{
        b
        | "epoch" => b["epoch"] + 1,
          "revision" => b["revision"] + 1,
          "audit_sequence" => b["audit_sequence"] + 1
      }

    true = s.session_envelope.context === d.context and s.session_envelope.sealed === d.sealed

    true =
      s.attempt_envelope.context === d.attempt_context and
        s.attempt_envelope.sealed === d.attempt_sealed

    true =
      s.attempt["created_at"] >= d.lease.started_at and
        s.attempt["created_at"] <= System.system_time(:second)

    true =
      s.attempt ===
        attempt_fields(
          d.attempt_context,
          d.attempt_sealed,
          :crypto.hash(:sha256, d.nonce),
          s.attempt["created_at"]
        )

    true = System.system_time(:second) < d.attempt_context.expires_at
    s
  end

  defp decode!({:discover_callback, input}, raw) do
    {:ok, %StoredSnapshot{} = s} = StoredSnapshot.decode(raw)
    callback_source!(s, input)
    s
  end

  defp decode!({operation, d, _}, raw) when operation in [:claim, :provider_reject] do
    {:ok, %StoredSnapshot{} = s} = StoredSnapshot.decode(raw)
    b = d.source.browser
    true = s.browser === %{b | "audit_sequence" => b["audit_sequence"] + 1}
    true = s.session_envelope === d.source.session_envelope and s.attempt_envelope === nil
    a = d.source.attempt
    erased = %{a | "key_id" => nil, "iv" => nil, "tag" => nil, "ciphertext" => nil}

    expected =
      case operation do
        :claim ->
          wall = callback_wall!(d.lease, d.source)
          claimed = s.attempt["claimed_at"]
          true = is_integer(claimed) and claimed >= d.lease.started_at and claimed <= wall
          true = wall < d.claim_expires_at

          %{
            erased
            | "status" => "claimed",
              "claim_digest" => :crypto.hash(:sha256, d.claim_secret),
              "claimed_at" => claimed,
              "claim_expires_at" => d.claim_expires_at
          }

        :provider_reject ->
          callback_wall!(d.lease, d.source)
          %{erased | "status" => "provider_rejected", "completion_reason" => "provider_rejected"}
      end

    true = s.attempt === expected
    s
  end

  defp callback_committed!({:discover_callback, input}, source) do
    callback_source!(source, input)
    callback_final!(input.lease, source, nil)
  end

  defp callback_committed!({operation, d, _}, _)
       when operation in [:claim, :provider_reject] do
    wall = callback_wall!(d.lease, d.source)
    if operation === :claim, do: true = wall < d.claim_expires_at
    expires = if operation === :claim, do: d.claim_expires_at, else: nil
    callback_final!(d.lease, d.source, expires)
  end

  defp callback_committed!(_, _), do: :ok

  defp callback_final!(lease, source, expires) do
    # A previous owner reply may already be queued when dependencies disappear.
    # Resample the exact lease after source/time work, then make the last local
    # expiry/PID/deadline samples. This remains a sampled check-to-return fence.
    checkpoint!(lease, lease.deadline)
    wall = callback_wall!(lease, source)
    true = is_nil(expires) or wall < expires
    true = Process.whereis(RuntimeOwner) === lease.owner
    remaining!(lease.deadline)
    :ok
  end

  defp callback_source!(source, input) do
    :ok = preauth_source!(source, input)
    true = not is_nil(source.attempt) and not is_nil(source.attempt_envelope)
    wall = callback_wall!(input.lease, source)
    :ok = pending_source!(source, input.lease.runtime.browser_config, wall)
    true = source.attempt["state_digest"] === input.state_digest
    :ok
  end

  defp callback_wall!(lease, source) do
    walls =
      Process.get(@callback_walls, %{})
      |> Map.reject(fn {_, record} ->
        System.monotonic_time(:millisecond) >= record.lease.deadline
      end)

    previous =
      case Map.get(walls, lease.reference) do
        %{lease: ^lease, wall: wall} ->
          wall

        nil ->
          true = map_size(walls) < 32
          lease.started_at
      end

    wall = System.system_time(:second)
    true = wall >= previous and wall >= lease.started_at
    true = wall < source.browser["idle_expires_at"]
    true = wall < source.browser["absolute_expires_at"]
    true = wall < source.attempt["expires_at"]
    Process.put(@callback_walls, Map.put(walls, lease.reference, %{lease: lease, wall: wall}))
    wall
  end

  defp callback_draft?(operation, d) do
    s = d.source

    input = %CallbackDraft.Discovery{
      lease: d.lease,
      cookie_digest: s.browser["cookie_digest"],
      state_digest: s.attempt["state_digest"]
    }

    :ok = callback_source!(s, input)
    envelope = s.session_envelope
    key = d.lease.runtime.custody.key

    # Never open Vault in the mutation transaction. Source authentication here
    # precedes checkout; rediscovery then proves full committed source equality.
    {:ok, %Vault.Preauth{csrf: csrf}} = Vault.open(key, envelope.context, envelope.sealed)
    true = Protocol.token?(csrf) and :crypto.hash(:sha256, csrf) === s.browser["csrf_digest"]

    case operation do
      :claim ->
        true = map_size(d) == 6 and Protocol.token?(d.verifier) and raw?(d.claim_secret, 32)

        expires =
          Enum.min([
            d.lease.started_at + 60,
            s.attempt["expires_at"],
            s.browser["idle_expires_at"],
            s.browser["absolute_expires_at"]
          ])

        true = is_integer(d.claim_expires_at) and d.claim_expires_at === expires
        true = callback_wall!(d.lease, s) < expires
        e = s.attempt_envelope
        {:ok, verifier} = Vault.open(key, e.context, e.sealed)
        verifier === %Vault.Verifier{verifier: d.verifier}

      :provider_reject ->
        map_size(d) == 3
    end
  end

  defp preauth_source!(%StoredSnapshot{} = s, input) do
    b = s.browser
    config = input.lease.runtime.browser_config
    e = s.session_envelope
    true = map_size(s) == 5
    true = b["status"] === "preauth"
    true = b["cookie_digest"] === input.cookie_digest
    true = b["config_digest"] === input.lease.runtime.configuration_digest
    true = b["initial_config_digest"] === input.lease.runtime.configuration_digest
    true = b["expected_profile_id"] === config.profile_id
    true = b["expected_profile_version"] === config.profile_version

    true =
      e.context === %{
        purpose: :preauth,
        browser_id: b["id"],
        cookie_digest: b["cookie_digest"],
        csrf_digest: b["csrf_digest"],
        epoch: b["epoch"],
        revision: b["revision"],
        generation: b["generation"],
        vault_generation: e.context.vault_generation,
        config_digest: b["config_digest"],
        profile_id: config.profile_id,
        profile_version: config.profile_version,
        principal_id: nil,
        family_id: nil,
        credential_ref: nil,
        credential_revision: nil
      }

    true =
      Enum.all?(
        ~w(profile_id profile_version principal_id family_id credential_ref credential_revision),
        &is_nil(b[&1])
      )

    :ok
  end

  defp pending_source!(%StoredSnapshot{attempt: nil, attempt_envelope: nil}, _), do: :ok

  defp pending_source!(%StoredSnapshot{} = s, config),
    do: pending_source!(s, config, System.system_time(:second))

  defp pending_source!(%StoredSnapshot{} = s, config, wall) do
    a = s.attempt
    b = s.browser
    e = s.attempt_envelope

    c = %{
      purpose: :attempt,
      state_digest: a["state_digest"],
      browser_id: b["id"],
      cookie_digest: b["cookie_digest"],
      epoch: b["epoch"],
      revision: b["revision"],
      generation: b["generation"],
      config_digest: b["config_digest"],
      profile_id: config.profile_id,
      profile_version: config.profile_version,
      issuer: config.issuer,
      client_id: config.client_id,
      redirect_uri: config.redirect_uri,
      expires_at: a["expires_at"]
    }

    true = e.context === c
    true = raw?(a["state_digest"], 32) and raw?(a["nonce_digest"], 32)
    true = a["created_at"] >= b["created_at"] and a["created_at"] <= wall
    true = a["expires_at"] > a["created_at"] and a["expires_at"] <= a["created_at"] + 300
    true = a["expires_at"] <= min(b["absolute_expires_at"], b["idle_expires_at"])
    true = a === attempt_fields(c, e.sealed, a["nonce_digest"], a["created_at"])
    :ok
  end

  defp attempt_fields(c, sealed, nonce_digest, created_at) do
    %{
      "state_digest" => c.state_digest,
      "browser_id" => c.browser_id,
      "browser_epoch" => c.epoch,
      "browser_revision" => c.revision,
      "cookie_digest" => c.cookie_digest,
      "generation" => c.generation,
      "config_digest" => c.config_digest,
      "profile_id" => c.profile_id,
      "profile_version" => c.profile_version,
      "issuer" => c.issuer,
      "client_id" => c.client_id,
      "redirect_uri" => c.redirect_uri,
      "return_route" => "workspace",
      "nonce_digest" => nonce_digest,
      "created_at" => created_at,
      "expires_at" => c.expires_at,
      "status" => "pending",
      "claim_digest" => nil,
      "claimed_at" => nil,
      "claim_expires_at" => nil,
      "completion_reason" => nil,
      "ciphertext_version" => 1,
      "key_id" => sealed.key_id,
      "iv" => bytea_hex(sealed.iv),
      "tag" => bytea_hex(sealed.tag),
      "ciphertext" => bytea_hex(sealed.ciphertext)
    }
  end

  defp begin_draft?(%PreauthDraft.Begin{} = d) do
    runtime = d.lease.runtime
    config = runtime.browser_config
    source = d.source
    input = %PreauthDraft.Load{lease: d.lease, cookie_digest: d.context.cookie_digest}
    :ok = preauth_source!(source, input)
    :ok = pending_source!(source, config)
    c = source.session_envelope.context

    expected_context = %{
      c
      | epoch: c.epoch + 1,
        revision: c.revision + 1,
        vault_generation: c.vault_generation + 1
    }

    expires =
      min(
        d.lease.started_at + 300,
        min(source.browser["idle_expires_at"], source.browser["absolute_expires_at"])
      )

    expected_attempt = %{
      purpose: :attempt,
      state_digest: :crypto.hash(:sha256, d.state),
      browser_id: c.browser_id,
      cookie_digest: c.cookie_digest,
      epoch: c.epoch + 1,
      revision: c.revision + 1,
      generation: c.generation,
      config_digest: runtime.configuration_digest,
      profile_id: config.profile_id,
      profile_version: config.profile_version,
      issuer: config.issuer,
      client_id: config.client_id,
      redirect_uri: config.redirect_uri,
      expires_at: expires
    }

    with true <-
           map_size(d) == 12 and d.context === expected_context and
             d.attempt_context === expected_attempt,
         true <- Enum.all?([d.state, d.nonce, d.verifier, d.csrf], &Protocol.token?/1),
         true <- length(Enum.uniq([d.state, d.nonce, d.verifier])) == 3,
         true <- System.system_time(:second) < expires,
         {:ok, url} <-
           Protocol.authorization_url(config, %{
             state: d.state,
             nonce: d.nonce,
             verifier: d.verifier
           }),
         true <- d.url === url and byte_size(url) <= 8192,
         {:ok, old} <- Vault.open(runtime.custody.key, c, source.session_envelope.sealed),
         true <- old === %Vault.Preauth{csrf: d.csrf},
         {:ok, new} <- Vault.open(runtime.custody.key, d.context, d.sealed),
         true <- new === old,
         {:ok, verifier} <- Vault.open(runtime.custody.key, d.attempt_context, d.attempt_sealed),
         true <- verifier === %Vault.Verifier{verifier: d.verifier},
         true <- authenticated_pending?(source, runtime.custody.key) do
      true
    else
      _ -> false
    end
  end

  defp authenticated_pending?(%StoredSnapshot{attempt: nil, attempt_envelope: nil}, _), do: true

  defp authenticated_pending?(%StoredSnapshot{attempt_envelope: e}, key),
    do: match?({:ok, %Vault.Verifier{}}, Vault.open(key, e.context, e.sealed))

  defp bootstrap_draft?(%PreauthDraft.Bootstrap{} = d) do
    c = d.context
    runtime = d.lease.runtime
    config = runtime.browser_config

    map_size(d) == 7 and is_integer(d.expires_at) and d.expires_at == d.lease.started_at + 300 and
      c.purpose === :preauth and c.epoch === 1 and c.revision === 1 and c.vault_generation === 1 and
      c.cookie_digest === :crypto.hash(:sha256, d.cookie) and
      c.csrf_digest === :crypto.hash(:sha256, d.csrf) and
      c.config_digest === runtime.configuration_digest and c.profile_id === config.profile_id and
      c.profile_version === config.profile_version and
      match?({:ok, _}, Vault.associated_data(d.sealed.key_id, c)) and
      match?({:ok, %Vault.Preauth{}}, Vault.open(runtime.custody.key, c, d.sealed))
  end

  defp checkpoint!(nil, deadline), do: remaining!(deadline)

  defp checkpoint!(lease, deadline) do
    true = lease.deadline === deadline
    :ok = RuntimeOwner.checkpoint(lease)
    remaining!(deadline)
  end

  defp remaining!(deadline) do
    remaining = deadline - System.monotonic_time(:millisecond)
    true = is_integer(deadline) and remaining > 0 and remaining <= 5_000
    remaining
  end

  defp metadata?(%{request_id: id} = metadata)
       when map_size(metadata) == 1 and is_binary(id) and byte_size(id) == 32,
       do: Enum.all?(:binary.bin_to_list(id), &(&1 in ?0..?9 or &1 in ?a..?f))

  defp metadata?(_), do: false
  defp raw?(value, size), do: is_binary(value) and byte_size(value) == size
  defp bytea_hex(value), do: "\\x" <> Base.encode16(value, case: :lower)
end
