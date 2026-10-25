defmodule MixerHosted.BrowserAuth.Store do
  @moduledoc """
  Fixed preauthentication storage operations on the dedicated lifecycle pool.

  No request-selected Repo, clock, callback, SQL name or provider is accepted.
  The internal owner must still authenticate ciphertext and fence private release
  after the transaction. A decoded snapshot alone grants no authentication.
  """
  alias MixerHosted.BrowserAuth.{Catalog, LifecycleRepo, PreauthDraft, RelationCatalog}
  alias MixerHosted.BrowserAuth.{RuntimeConfig, RuntimeOwner, StoredSnapshot, Vault}

  defmodule Failure do
    @moduledoc "Closed private failure without database, identity or secret details."
    @enforce_keys [:code, :phase, :outcome]
    defstruct @enforce_keys
  end

  @phase {__MODULE__, :phase}
  @owned {__MODULE__, :owned}
  @entered {__MODULE__, :entered}
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
            log: false
          )

        case result do
          {:ok, value} ->
            # DBConnection's absolute deadline also covers COMMIT. This final
            # check can withhold a known committed result, never resurrect it.
            try do
              checkpoint!(lease, deadline)
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
          # A PostgreSQL error response to COMMIT is a definite rejected commit.
          # Driver/disconnect exceptions have no such durable receipt.
          outcome = if is_map(error.postgres), do: :rolled_back, else: :unknown
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
        log: false
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

  defp effect!({:load, input}, deadline) do
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
    b = s.browser
    config = input.lease.runtime.browser_config
    true = b["status"] === "preauth"
    true = b["cookie_digest"] === input.cookie_digest
    true = b["config_digest"] === input.lease.runtime.configuration_digest
    true = b["initial_config_digest"] === input.lease.runtime.configuration_digest
    true = b["expected_profile_id"] === config.profile_id
    true = b["expected_profile_version"] === config.profile_version

    if s.attempt != nil do
      true = s.attempt["issuer"] === config.issuer and s.attempt["client_id"] === config.client_id
      true = s.attempt["redirect_uri"] === config.redirect_uri
    end

    s
  end

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
end
